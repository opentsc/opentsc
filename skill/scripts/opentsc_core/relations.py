from __future__ import annotations

import json
from pathlib import Path

from .common import ensure_vault, resolve_entity_file, today
from .entities import display_name, entity_id_from_file
from .vault import append_jsonl

REL_FILE = "relations/edges.jsonl"


def link(root: Path, source: str, rel_type: str, target: str, since: str | None = None, source_note: str = "user", confidence: str = "medium", status: str = "current", introduced_by: str | None = None, emotion: str | None = None, notes: str | None = None) -> dict:
    ensure_vault(root)
    (root / "relations").mkdir(parents=True, exist_ok=True)
    src_path = resolve_entity_file(root, source)
    tgt_path = resolve_entity_file(root, target)
    src_id = entity_id_from_file(src_path)
    tgt_id = entity_id_from_file(tgt_path)
    row = {
        "date": today(),
        "source": src_id,
        "type": rel_type,
        "target": tgt_id,
        "status": status,
        "since": since or "",
        "evidence": source_note,
        "confidence": confidence,
        "introduced_by": introduced_by or "",
        "emotion": emotion or "",
        "notes": notes or "",
    }
    append_jsonl(root / REL_FILE, row)
    _append_edge_view(src_path, "out", rel_type, tgt_id, display_name(tgt_path), since, confidence, source_note, introduced_by, emotion)
    _append_edge_view(tgt_path, "in", rel_type, src_id, display_name(src_path), since, confidence, source_note, introduced_by, emotion)
    return row


def links(root: Path, entity: str | None = None, rel_type: str | None = None) -> list[dict]:
    rows = _read_edges(root)
    if entity:
        path = resolve_entity_file(root, entity)
        eid = entity_id_from_file(path)
        rows = [r for r in rows if r.get("source") == eid or r.get("target") == eid]
    if rel_type:
        rows = [r for r in rows if r.get("type") == rel_type]
    return rows


def _read_edges(root: Path) -> list[dict]:
    path = root / REL_FILE
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _append_edge_view(path: Path, direction: str, rel_type: str, other_id: str, other_name: str, since: str | None, confidence: str, evidence: str, introduced_by: str | None = None, emotion: str | None = None) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    arrow = "→→" if direction == "out" else "←←"
    intro = f" · introduced_by:{introduced_by}" if introduced_by else ""
    emo = f" · emotion:{emotion}" if emotion else ""
    line = f"- [现] {rel_type} {arrow} {other_id}: {other_name} · {since or 'TODO(time)'} · confidence:{confidence} · source:{evidence}{intro}{emo}\n"
    heading = "## Relationship edges"
    if heading in text:
        text = text.replace(heading, heading + "\n\n" + line, 1)
    else:
        text = text.rstrip() + "\n\n" + heading + "\n\n" + line
    path.write_text(text, encoding="utf-8")
