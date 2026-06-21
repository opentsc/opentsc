"""zvec-backed memory index — the derived, rebuildable retrieval layer.

Design contract (honors Law 2, soul portability):
    Markdown under ``soul/`` and ``world/`` is the **source of truth**.
    This index is a *derived* artifact: it can be dropped and rebuilt from the
    markdown at any time, and it lives under ``soul/.index/`` (git-ignored).

One flat collection ``memory`` holds every retrievable unit — events,
entities, (optionally) messages — distinguished by a ``kind`` field, so a
single semantic query can range across the whole vault and be narrowed with a
scalar filter. Vectors come from the pluggable embedding backend, so the same
index works on a bare ``lite`` install or a high-quality local/api model.

zvec is imported lazily; importing this module never fails. Callers check
:meth:`ZvecIndex.available` and fall back to the legacy file-scan when the
optional dependency is absent.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import events as events_mod
from .common import read_text, parse_frontmatter, scan_entities, today
from .config import Config
from .embedding import get_embedding_backend
from .text import normalize

COLLECTION = "memory"
_MANIFEST = "manifest.json"


def zvec_available() -> bool:
    try:
        import zvec  # noqa: F401

        return True
    except Exception:
        return False


class IndexUnavailable(RuntimeError):
    """Raised when an index operation needs zvec but it is not installed."""


class ZvecIndex:
    """Open/build/query the derived memory index for a vault."""

    def __init__(self, root: Path, config: Config | None = None) -> None:
        self.root = Path(root)
        self.config = config or Config.load(self.root)
        self.embedder = get_embedding_backend(self.config)
        self.dir = self.config.index_path(self.root)
        self._col = None
        self._emotion = None  # lazily built; scoring happens at index time

    def _emotion_backend(self):
        if self._emotion is None:
            from .emotion import get_emotion_backend

            self._emotion = get_emotion_backend(self.config)
        return self._emotion

    # -- availability / lifecycle ------------------------------------------

    def available(self) -> bool:
        return zvec_available()

    def _require(self):
        if not zvec_available():
            raise IndexUnavailable(
                "zvec is not installed — run `pip install zvec` or fall back to file-scan queries"
            )
        import zvec

        return zvec

    @property
    def dim(self) -> int:
        # Probe the backend's dimension (lite knows it cheaply; model backends
        # load on first use).
        return int(getattr(self.embedder, "dim", self.config.embedding_dim))

    def _manifest_path(self) -> Path:
        return self.dir / _MANIFEST

    def _read_manifest(self) -> dict:
        p = self._manifest_path()
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _write_manifest(self, data: dict) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self._manifest_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _schema(self):
        zvec = self._require()
        return zvec.CollectionSchema(
            name=COLLECTION,
            fields=[
                zvec.FieldSchema("kind", zvec.DataType.STRING),
                zvec.FieldSchema("ref_id", zvec.DataType.STRING),
                zvec.FieldSchema("entity_id", zvec.DataType.STRING, nullable=True),
                zvec.FieldSchema("date", zvec.DataType.STRING, nullable=True),
                zvec.FieldSchema("title", zvec.DataType.STRING, nullable=True),
                zvec.FieldSchema("emotion", zvec.DataType.STRING, nullable=True),
                zvec.FieldSchema("polarity", zvec.DataType.FLOAT, nullable=True),
                zvec.FieldSchema("text", zvec.DataType.STRING),
            ],
            vectors=[zvec.VectorSchema("embedding", zvec.DataType.VECTOR_FP32, self.dim)],
        )

    def _collection(self):
        if self._col is not None:
            return self._col
        zvec = self._require()
        store = str(self.dir / COLLECTION)
        if (self.dir / COLLECTION).exists():
            self._col = zvec.open(store)
        else:
            self.dir.mkdir(parents=True, exist_ok=True)
            self._col = zvec.create_and_open(path=store, schema=self._schema())
        return self._col

    def needs_rebuild(self) -> bool:
        """True if the stored index was built with a different backend/dim."""
        m = self._read_manifest()
        return bool(m) and (m.get("backend") != self.embedder.name or m.get("dim") != self.dim)

    def drop(self) -> None:
        import shutil

        if self.dir.exists():
            shutil.rmtree(self.dir)
        self._col = None

    # -- writing ------------------------------------------------------------

    def _doc(self, zvec, unit: dict):
        text = unit["text"]
        [vec] = self.embedder.embed([text])
        return zvec.Doc(
            id=unit["id"],
            vectors={"embedding": vec},
            fields={
                "kind": unit["kind"],
                "ref_id": unit["ref_id"],
                "entity_id": unit.get("entity_id", "") or "",
                "date": unit.get("date", "") or "",
                "title": unit.get("title", "") or "",
                "emotion": unit.get("emotion", "") or "",
                "polarity": float(unit.get("polarity", 0.0) or 0.0),
                "text": text[:4000],
            },
        )

    def upsert_units(self, units: list[dict]) -> int:
        if not units:
            return 0
        zvec = self._require()
        col = self._collection()
        col.upsert([self._doc(zvec, u) for u in units])
        col.flush()
        return len(units)

    def build(self) -> dict:
        """Full rebuild from markdown. Returns counts per kind."""
        self.drop()
        units = list(self._iter_units())
        self.upsert_units(units)
        counts: dict[str, int] = {}
        for u in units:
            counts[u["kind"]] = counts.get(u["kind"], 0) + 1
        self._write_manifest({
            "backend": self.embedder.name,
            "dim": self.dim,
            "built": today(),
            "counts": counts,
        })
        return counts

    def sync(self) -> dict:
        """Incremental update; full build if no prior manifest or backend drift."""
        if self.needs_rebuild() or not self._read_manifest():
            return self.build()
        units = list(self._iter_units())
        changed = self.upsert_units(units)
        m = self._read_manifest()
        m["synced"] = today()
        self._write_manifest(m)
        return {"upserted": changed}

    # -- source-of-truth extraction ----------------------------------------

    def _iter_units(self):
        """Yield retrievable units from the markdown source of truth.

        Two passes: events first (so each entity can be enriched with the
        narratives of the events it is linked to — an entity *is* the sum of
        its events), then entities with that aggregated text.
        """
        entity_events: dict[str, list[str]] = {}
        entity_polarity: dict[str, list[float]] = {}
        emo = self._emotion_backend()

        # Pass 1 — events (scored for emotion at index time — this is the cheap,
        # deterministic precompute that replaces a daily LLM re-read of "who is
        # upset").
        try:
            for evt in events_mod.timeline(self.root, limit=100000):
                content = normalize(evt.get("content", ""))
                if not content:
                    continue
                links = evt.get("links", [])
                if isinstance(links, str):
                    links = [links]
                e = emo.score(content)
                for ent in links:
                    entity_events.setdefault(ent, []).append(content)
                    entity_polarity.setdefault(ent, []).append(e.polarity)
                yield {
                    "id": f"event_{evt.get('id')}",
                    "kind": "event",
                    "ref_id": evt.get("id", ""),
                    "entity_id": (links[0] if links else ""),
                    "date": evt.get("date", ""),
                    "title": "",
                    "emotion": e.label,
                    "polarity": e.polarity,
                    "text": content,
                }
        except Exception:
            pass

        # Pass 2 — entities. scan_entities() matches any markdown with an `id:`
        # frontmatter (events included), so skip events / soul/events/.
        for entity_id, ref in scan_entities(self.root).items():
            # scan_entities() matches any markdown with an `id:` frontmatter —
            # events, actions, predictions, knowledge. Real entities live under
            # world/ or people/; everything else is not an entity.
            parts = set(ref.path.parts)
            if not ("world" in parts or "people" in parts):
                continue
            try:
                raw = read_text(ref.path)
            except Exception:
                continue
            fm = parse_frontmatter(raw)
            name = self._entity_name(fm, entity_id)
            event_text = " ".join(entity_events.get(entity_id, []))
            text = normalize(f"{name} {event_text}")[:4000]
            pols = entity_polarity.get(entity_id, [])
            mood = round(sum(pols) / len(pols), 4) if pols else 0.0
            from .emotion import _label_for

            yield {
                "id": f"entity_{entity_id}",
                "kind": "entity",
                "ref_id": entity_id,
                "entity_id": entity_id,
                "date": fm.get("updated", "") or "",
                "title": name,
                "emotion": _label_for(mood),
                "polarity": mood,
                "text": text or name,
            }

    @staticmethod
    def _entity_name(fm: dict, entity_id: str) -> str:
        """Resolve a display name from varied frontmatter shapes."""
        names = fm.get("names")
        if isinstance(names, dict) and names.get("real"):
            return str(names["real"])
        for key in ("name", "real", "title"):
            if fm.get(key):
                return str(fm[key])
        return entity_id

    # -- reading ------------------------------------------------------------

    @staticmethod
    def _quote(value: str) -> str:
        return "'" + value.replace("'", "") + "'"

    def _filter(self, kind: str | None, entity_id: str | None) -> str | None:
        clauses = []
        if kind:
            clauses.append(f"kind = {self._quote(kind)}")
        if entity_id:
            clauses.append(f"entity_id = {self._quote(entity_id)}")
        return " AND ".join(clauses) if clauses else None

    def search(self, query: str, kind: str | None = None, entity_id: str | None = None,
               topk: int = 10) -> list[dict]:
        """Semantic search over the vault, optionally narrowed by kind/entity."""
        zvec = self._require()
        col = self._collection()
        [vec] = self.embedder.embed([query])
        q = zvec.Query(field_name="embedding", vector=vec)
        res = col.query(
            queries=[q], topk=topk, filter=self._filter(kind, entity_id),
            output_fields=["kind", "ref_id", "entity_id", "date", "title", "emotion", "polarity", "text"],
        )
        return [self._row(d) for d in res]

    def resolve_identity(self, name: str, topk: int = 5) -> list[dict]:
        """Nearest entities to a name/description — for dedup and alias resolution.

        This is what kills unreadable hash IDs and name drift: instead of the
        LLM guessing whether "马克思" and "马斯克" are the same node, ask the
        index for the closest existing entities and let K1 decide to merge.
        """
        return self.search(name, kind="entity", topk=topk)

    def mood(self, negative_first: bool = True, limit: int = 20) -> list[dict]:
        """Entities ranked by aggregated emotional polarity.

        Deterministic answer to "谁情绪不好" — read straight off the index
        instead of re-parsing thousands of messages through an LLM each day.
        """
        zvec = self._require()
        col = self._collection()
        res = col.query(
            topk=limit, filter="kind = 'entity'",
            output_fields=["ref_id", "title", "emotion", "polarity"],
        )
        rows = [self._row(d) for d in res]
        rows.sort(key=lambda r: r.get("polarity") or 0.0, reverse=not negative_first)
        return rows

    @staticmethod
    def _row(doc) -> dict:
        f = dict(doc.fields or {})
        f["id"] = doc.id
        f["score"] = round(float(doc.score), 4) if doc.score is not None else None
        return f

    def stats(self) -> dict:
        m = self._read_manifest()
        return {
            "available": self.available(),
            "backend": self.embedder.name,
            "dim": self.dim,
            "dir": str(self.dir),
            **m,
        }
