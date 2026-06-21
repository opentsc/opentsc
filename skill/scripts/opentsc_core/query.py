from __future__ import annotations

import re
from pathlib import Path

from .common import EVENT_RE, frontmatter, iter_markdown, read_text, scan_entities
from .entities import display_name, get_skills, get_tags
from .relations import links


def query(root: Path, term: str | None = None, scope: str | None = None, tag: str | None = None, skill: str | None = None, available: bool | None = None, include_archive: bool = False) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for ent, ref in scan_entities(root).items():
        if not include_archive and "archive" in ref.path.parts:
            continue
        if scope and not _scope_match(ref.path, scope):
            continue
        if tag and tag not in get_tags(ref.path):
            continue
        if skill and skill not in get_skills(ref.path):
            continue
        text = read_text(ref.path)
        if available is not None:
            is_available = re.search(r"^availability:\n\s+status:\s*available\s*$", text, re.MULTILINE) is not None
            if available != is_available:
                continue
        if term:
            for line_no, line in enumerate(text.splitlines(), 1):
                if term.lower() in line.lower():
                    results.append(_result(ent, ref.entity_type or "entity", ref.path, line_no, line.strip()))
        else:
            results.append(_result(ent, ref.entity_type or "entity", ref.path, 0, display_name(ref.path)))
    return results


def who_can(root: Path, skill: str, available_only: bool = False) -> list[dict[str, str]]:
    people = query(root, skill=skill, available=True if available_only else None, scope="people")
    enriched: list[dict[str, str]] = []
    all_links = links(root)
    for row in people:
        eid = row["entity"]
        rels = [r for r in all_links if r.get("source") == eid or r.get("target") == eid]
        row = dict(row)
        row["relations"] = str(len(rels))
        row["name"] = display_name(Path(row["path"]))
        enriched.append(row)
    return enriched


def _scope_match(path: Path, scope: str) -> bool:
    mapping = {"people": "people", "person": "people", "orgs": "orgs", "org": "orgs", "operations": "operations", "op": "operations", "raw": "raw", "inbox": "inbox"}
    part = mapping.get(scope, scope)
    return part in path.parts


def _result(entity: str, kind: str, path: Path, line: int, text: str) -> dict[str, str]:
    rating = ""
    source = ""
    match = EVENT_RE.match(text)
    if match:
        rating_match = re.search(r"·\s*([A-F][1-6])\s*·", text)
        rating = rating_match.group(1) if rating_match else ""
        src_match = re.search(r"〔来源:\s*(.+?)〕", text)
        source = src_match.group(1) if src_match else ""
    return {"entity": entity, "type": kind, "path": str(path), "line": str(line), "rating": rating, "source": source, "text": text}
