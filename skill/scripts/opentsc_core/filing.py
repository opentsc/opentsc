from __future__ import annotations

import re
import shutil
from pathlib import Path

from .common import ensure_vault, now_iso, sanitize_filename, stable_suffix, today, write_text, year_month_parts, read_text
from .vault import append_jsonl, add_event
from .relations import link


def dated_dir(root: Path, base: str, date_text: str | None = None) -> Path:
    y, m = year_month_parts(date_text)
    return root / base / y / m


def move_with_ledger(root: Path, src: Path, dst: Path, reason: str) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    final = _unique(dst)
    shutil.move(str(src), str(final))
    append_jsonl(root / "ledger" / "file-moves.jsonl", {"at": now_iso(), "from": str(src), "to": str(final), "reason": reason})
    return final


def copy_with_ledger(root: Path, src: Path, dst: Path, reason: str) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    final = _unique(dst)
    shutil.copy2(src, final)
    append_jsonl(root / "ledger" / "file-moves.jsonl", {"at": now_iso(), "from": str(src), "to": str(final), "reason": reason})
    return final


def ingest(root: Path, source_path: Path, material_type: str = "battle_report", source: str = "user_dropbox", move: bool = True) -> dict[str, str]:
    ensure_vault(root)
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    content = read_text(source_path) if source_path.suffix.lower() in {".md", ".txt", ".csv"} else f"[binary/source file: {source_path.name}]"
    raw_id = f"raw_{today().replace('-', '')}_{stable_suffix(source_path.name + content, 8)}"
    raw_name = f"{raw_id}-{sanitize_filename(source_path.stem)}{source_path.suffix or '.md'}"
    raw_target = dated_dir(root, "raw") / raw_name
    final_raw = move_with_ledger(root, source_path, raw_target, "ingest_to_raw") if move else copy_with_ledger(root, source_path, raw_target, "copy_ingest_to_raw")
    if final_raw.suffix.lower() in {".md", ".txt"}:
        body = f"""---
id: {raw_id}
type: raw_material
material_type: {material_type}
title: {source_path.stem}
source: {source}
source_date: TODO(user)
ingested_at: {now_iso()}
created_at: {now_iso()}
status: processed
---

# {source_path.stem}

{content.rstrip()}
"""
        write_text(final_raw, body)
    candidates = create_candidates(root, raw_id, source_path.stem, content, material_type)
    candidate_log = {k: str(v) for k, v in candidates.items()}
    append_jsonl(root / "ledger" / "processing-runs.jsonl", {"at": now_iso(), "action": "ingest", "raw_id": raw_id, "raw_path": str(final_raw), "source_path": str(source_path), "candidates": candidate_log})
    return {"raw_id": raw_id, "raw_path": str(final_raw), **candidate_log}


def create_candidates(root: Path, raw_id: str, title: str, content: str, material_type: str) -> dict[str, Path]:
    suffix = stable_suffix(raw_id + content, 8)
    paths: dict[str, Path] = {}
    people = _extract_people(content)
    orgs = _extract_orgs(content)
    event_path = root / "inbox" / "events" / f"draft_events_{today().replace('-', '')}_{suffix}.md"
    entity_path = root / "inbox" / "entities" / f"draft_entities_{today().replace('-', '')}_{suffix}.md"
    relation_path = root / "inbox" / "relations" / f"draft_relations_{today().replace('-', '')}_{suffix}.md"
    knowledge_path = root / "inbox" / "knowledge" / f"draft_knowledge_{today().replace('-', '')}_{suffix}.md"
    base_fm = f"raw: {raw_id}\nsource_title: {title}\ncreated_at: {now_iso()}\nstatus: draft"
    write_text(event_path, f"---\ntype: inbox_event_batch\n{base_fm}\n---\n\n# Candidate events\n\n- TODO(entity_id) · B6 · TODO(extracted event from {title}) · source:{raw_id}\n\n## Source excerpt\n\n{content[:1200]}\n")
    write_text(entity_path, f"---\ntype: inbox_entity_batch\n{base_fm}\n---\n\n# Candidate entities\n\n## People-like mentions\n" + "".join(f"- {p}\n" for p in people[:50]) + "\n## Org-like mentions\n" + "".join(f"- {o}\n" for o in orgs[:50]))
    write_text(relation_path, f"---\ntype: inbox_relation_batch\n{base_fm}\n---\n\n# Candidate relations\n\n- TODO(source_id) TODO(relation_type) TODO(target_id) · confidence: low · evidence:{raw_id}\n")
    write_text(knowledge_path, f"---\ntype: inbox_knowledge_batch\nlayer: methods\nsample_size: 1\n{base_fm}\n---\n\n# Candidate knowledge\n\n- TODO(granule): extracted from {raw_id}; keep only if user confirms.\n")
    paths.update({"events": event_path, "entities": entity_path, "relations": relation_path, "knowledge": knowledge_path})
    return paths


def accept(root: Path, draft: str, entity: str | None = None, admiralty: str = "B6", content: str | None = None, source: str | None = None, relation: tuple[str, str, str] | None = None, knowledge_layer: str | None = None) -> Path:
    path = _find_draft(root, draft)
    text = read_text(path)
    if relation:
        src, rel_type, tgt = relation
        link(root, src, rel_type, tgt, source_note=source or path.stem, confidence="medium")
    elif knowledge_layer:
        target = root / "knowledge" / knowledge_layer / f"kg_{today().replace('-', '')}_{stable_suffix(path.stem, 8)}.md"
        write_text(target, _accepted_knowledge(text, path.stem, knowledge_layer))
    else:
        if not entity:
            raise ValueError("accept event requires --entity unless accepting relation/knowledge")
        add_event(root, entity, admiralty, content or _first_candidate_line(text), source or path.stem, status="pending_verification")
    return move_with_ledger(root, path, dated_dir(root, "archive/inbox") / path.name, "accepted_candidate")


def reject(root: Path, draft: str, reason: str) -> Path:
    path = _find_draft(root, draft)
    append_jsonl(root / "ledger" / "processing-runs.jsonl", {"at": now_iso(), "action": "reject", "draft": str(path), "reason": reason})
    return move_with_ledger(root, path, dated_dir(root, "archive/inbox") / path.name, "rejected_candidate")


def file_audit(root: Path) -> list[str]:
    issues: list[str] = []
    dropbox = root / "intake" / "dropbox"
    if dropbox.exists():
        for p in dropbox.iterdir():
            if p.is_file():
                issues.append(f"unprocessed dropbox file: {p}")
    for folder in ["events", "entities", "relations", "knowledge", "actions", "intel_gaps", "breakthroughs", "conflicts"]:
        inbox_dir = root / "inbox" / folder
        if inbox_dir.exists():
            for p in inbox_dir.glob("*.md"):
                issues.append(f"pending inbox/{folder}: {p}")
    for p in (root / "raw").glob("**/*"):
        if p.is_file() and p.suffix.lower() in {".md", ".txt"}:
            text = read_text(p)
            if "ingested_at:" not in text:
                issues.append(f"raw missing ingested_at: {p}")
    if not (root / "_filing.md").exists():
        issues.append("missing _filing.md")
    return issues


def _find_draft(root: Path, draft: str) -> Path:
    candidates = list((root / "inbox").glob(f"**/{draft}.md")) + list((root / "inbox").glob(f"**/*{draft}*.md"))
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        raise ValueError(f"ambiguous draft id {draft}: {', '.join(str(c) for c in candidates)}")
    raise FileNotFoundError(f"draft not found: {draft}")


def _first_candidate_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip().startswith("- "):
            parts = line.split("·")
            if len(parts) >= 3:
                return parts[2].strip()
            return line.strip()[2:]
    return "TODO(user): accepted candidate content"


def _accepted_knowledge(text: str, draft_id: str, layer: str) -> str:
    return f"---\nlayer: {layer}\nstatus: confirmed\nconfidence: low\nsample_size: 1\nsource_events: []\ncreated_at: {now_iso()}\nsource_draft: {draft_id}\n---\n\n# Accepted knowledge from {draft_id}\n\n{text}\n"


def _extract_people(content: str) -> list[str]:
    # Conservative heuristic: English/Chinese name-like tokens. User confirmation required.
    tokens = re.findall(r"[A-Z][a-zA-Z]{2,}|[一-鿿]{2,4}", content)
    return sorted(set(tokens))


def _extract_orgs(content: str) -> list[str]:
    tokens = re.findall(r"[A-Z][A-Za-z0-9& ]{2,}(?:Team|Capital|Studio|Inc|LLC|机构|公司|团队|项目)", content)
    return sorted(set(t.strip() for t in tokens))


def _unique(path: Path) -> Path:
    if not path.exists():
        return path
    for i in range(2, 10000):
        candidate = path.with_name(f"{path.stem}-{i}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"cannot find unique path for {path}")
