from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from .common import ID_RE, frontmatter, read_text, resolve_entity_file, scan_entities, today, write_text
from .vault import append_jsonl

TAG_RE = re.compile(r"^tags:\s*\[(.*?)\]\s*$", re.MULTILINE)
SKILLS_RE = re.compile(r"^skills:\s*\[(.*?)\]\s*$", re.MULTILINE)


def csv_list(value: str) -> list[str]:
    value = value.strip()
    if not value:
        return []
    return [x.strip().strip('"\'') for x in value.split(",") if x.strip()]


def list_literal(items: list[str]) -> str:
    return "[" + ", ".join(dict.fromkeys([x for x in items if x])) + "]"


def entity_id_from_file(path: Path) -> str:
    text = read_text(path)
    match = ID_RE.search(frontmatter(text))
    if not match:
        raise ValueError(f"no entity id in {path}")
    return match.group(1)


def display_name(path: Path) -> str:
    text = read_text(path)
    match = re.search(r"^\s*real:\s*(.+?)\s*$", text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return entity_id_from_file(path)


def get_tags(path: Path) -> list[str]:
    match = TAG_RE.search(read_text(path))
    return csv_list(match.group(1)) if match else []


def set_tags(path: Path, tags: list[str]) -> None:
    text = read_text(path)
    replacement = f"tags: {list_literal(tags)}"
    if TAG_RE.search(text):
        text = TAG_RE.sub(replacement, text, count=1)
    else:
        text = text.replace("---\n\n", replacement + "\n---\n\n", 1)
    write_text(path, text)


def add_tag(root: Path, entity: str, tag: str) -> Path:
    path = resolve_entity_file(root, entity)
    tags = get_tags(path)
    if tag not in tags:
        tags.append(tag)
        set_tags(path, tags)
    return path


def remove_tag(root: Path, entity: str, tag: str) -> Path:
    path = resolve_entity_file(root, entity)
    set_tags(path, [t for t in get_tags(path) if t != tag])
    return path


def list_tags(root: Path, filter_text: str | None = None) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for ent, ref in scan_entities(root).items():
        if "archive" in ref.path.parts:
            continue
        for tag in get_tags(ref.path):
            if filter_text and filter_text not in tag:
                continue
            out.setdefault(tag, []).append(ent)
    return dict(sorted(out.items()))


def get_skills(path: Path) -> list[str]:
    match = SKILLS_RE.search(read_text(path))
    return csv_list(match.group(1)) if match else []


def set_skills(path: Path, skills: list[str]) -> None:
    text = read_text(path)
    replacement = f"skills: {list_literal(skills)}"
    if SKILLS_RE.search(text):
        text = SKILLS_RE.sub(replacement, text, count=1)
    else:
        text = text.replace("trust:\n", replacement + "\ntrust:\n", 1) if "trust:\n" in text else text.replace("---\n\n", replacement + "\n---\n\n", 1)
    write_text(path, text)


def set_person_fields(root: Path, entity: str, skills: list[str] | None = None, availability: str | None = None, reliability: str | None = None, cost_daily: str | None = None, project_rate: str | None = None, control_level: str | None = None) -> Path:
    path = resolve_entity_file(root, entity)
    if skills:
        current = get_skills(path)
        set_skills(path, current + skills)
    text = read_text(path)
    insert_lines: list[str] = []
    if availability:
        insert_lines.append(f"availability:\n  status: {availability}\n  reviewed: {today()}")
    if reliability:
        insert_lines.append(f"reliability:\n  value: {reliability}\n  basis: TODO(user/calibration)\n  reviewed: {today()}")
    if cost_daily or project_rate:
        insert_lines.append("cost:\n" + (f"  daily: {cost_daily}\n" if cost_daily else "") + (f"  project_rate: {project_rate}\n" if project_rate else "") + f"  reviewed: {today()}")
    if control_level:
        insert_lines.append(f"control_level:\n  value: {control_level}\n  reviewed: {today()}")
    for block in insert_lines:
        key = block.split(":", 1)[0]
        text = _replace_or_insert_block(text, key, block)
    write_text(path, text)
    return path


def _replace_or_insert_block(text: str, key: str, block: str) -> str:
    pattern = re.compile(rf"^{re.escape(key)}:\n(?:^\s+.*\n?)+", re.MULTILINE)
    if pattern.search(text):
        return pattern.sub(block + "\n", text, count=1)
    if "trust:\n" in text:
        return text.replace("trust:\n", block + "\ntrust:\n", 1)
    return text.replace("---\n\n", block + "\n---\n\n", 1)


def archive_entity(root: Path, entity: str, reason: str = "user_archived") -> Path:
    path = resolve_entity_file(root, entity)
    eid = entity_id_from_file(path)
    archive_dir = root / "archive" / eid
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / path.name
    shutil.move(str(path), str(target))
    tombstone = root / "ledger" / "archives.jsonl"
    append_jsonl(tombstone, {"date": today(), "action": "archive", "entity": eid, "from": str(path), "to": str(target), "reason": reason})
    return target


def restore_entity(root: Path, entity: str) -> Path:
    archive_root = root / "archive"
    candidates = list(archive_root.glob(f"{entity}/*.md")) + list(archive_root.glob(f"**/{entity}.md"))
    if not candidates:
        raise FileNotFoundError(f"archived entity not found: {entity}")
    src = candidates[0]
    eid = entity_id_from_file(src)
    prefix = eid.split("_", 1)[0]
    folder = {"p": "people", "o": "orgs", "op": "operations"}.get(prefix, "people")
    if prefix in {"o", "op"}:
        target = root / folder / eid / "profile.md"
        target.parent.mkdir(parents=True, exist_ok=True)
    else:
        target = root / folder / f"{eid}.md"
    shutil.move(str(src), str(target))
    append_jsonl(root / "ledger" / "archives.jsonl", {"date": today(), "action": "restore", "entity": eid, "from": str(src), "to": str(target)})
    return target


def merge_entities(root: Path, loser: str, winner: str, keep_alias: str | None = None, reason: str = "user_confirmed_same_entity") -> Path:
    loser_path = resolve_entity_file(root, loser)
    winner_path = resolve_entity_file(root, winner)
    loser_id = entity_id_from_file(loser_path)
    winner_id = entity_id_from_file(winner_path)
    loser_text = read_text(loser_path)
    winner_text = read_text(winner_path)
    alias = keep_alias or display_name(loser_path)
    if "  aliases: []" in winner_text:
        winner_text = winner_text.replace("  aliases: []", f"  aliases:\n    - value: {alias}\n      src: merge:{loser_id}\n      status: confirmed", 1)
    elif "  aliases:" in winner_text:
        winner_text = winner_text.replace("  aliases:", f"  aliases:\n    - value: {alias}\n      src: merge:{loser_id}\n      status: confirmed", 1)
    events = _section(loser_text, "## Intelligence timeline")
    if events:
        winner_text = winner_text.rstrip() + f"\n\n## Merged timeline from {loser_id}\n\n" + events.strip() + "\n"
    write_text(winner_path, winner_text)
    archive_target = archive_entity(root, loser_id, reason=f"merged_into:{winner_id}")
    append_jsonl(root / "ledger" / "identity-merges.jsonl", {"date": today(), "loser": loser_id, "winner": winner_id, "alias_kept": alias, "archived_to": str(archive_target), "reason": reason})
    return winner_path


def _section(text: str, heading: str) -> str:
    idx = text.find(heading)
    if idx == -1:
        return ""
    rest = text[idx + len(heading):]
    next_heading = re.search(r"\n## ", rest)
    return rest[: next_heading.start()] if next_heading else rest
