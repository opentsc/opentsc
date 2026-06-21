from __future__ import annotations

import re
from pathlib import Path

from .common import read_text, scan_entities, today, write_text
from .relations import links


def detect_conflicts(root: Path) -> list[dict[str, str]]:
    conflicts: list[dict[str, str]] = []
    conflicts.extend(_alias_conflicts(root))
    conflicts.extend(_contact_conflicts(root))
    conflicts.extend(_relation_conflicts(root))
    return conflicts


def write_conflict_report(root: Path) -> Path | None:
    conflicts = detect_conflicts(root)
    if not conflicts:
        return None
    target = root / "inbox" / f"conflicts-{today()}.md"
    lines = [f"---\ntype: conflict_report\ncreated: {today()}\nstatus: draft\n---\n\n# Conflict report · {today()}\n\n"]
    for c in conflicts:
        lines.append(f"- **{c['type']}** · {c['key']} · {c['detail']}\n")
    write_text(target, "".join(lines))
    return target


def _alias_conflicts(root: Path) -> list[dict[str, str]]:
    owners: dict[str, list[str]] = {}
    for eid, ref in scan_entities(root).items():
        if "archive" in ref.path.parts:
            continue
        text = read_text(ref.path)
        # Extract only the aliases section from frontmatter
        fm = text.split("---")
        if len(fm) < 3:
            continue
        frontmatter_text = fm[1]
        # Find aliases block within names section
        # Match alias values only inside the names.aliases list
        in_aliases = False
        for line in frontmatter_text.splitlines():
            stripped = line.rstrip()
            if stripped.strip().startswith("aliases:"):
                in_aliases = True
                continue
            if in_aliases:
                # If we hit a non-list line (no leading -), we've left the aliases block
                if not stripped.strip().startswith("- ") and not stripped.strip().startswith("value:"):
                    in_aliases = False
                    continue
                m = re.match(r"\s*-\s*value:\s*(.+?)\s*$", stripped)
                if m:
                    alias_val = m.group(1).strip()
                    if alias_val:
                        owners.setdefault(alias_val, []).append(eid)
    return [{"type": "alias_conflict", "key": k, "detail": ", ".join(v)} for k, v in owners.items() if len(set(v)) > 1]


def _contact_conflicts(root: Path) -> list[dict[str, str]]:
    owners: dict[str, list[str]] = {}
    for eid, ref in scan_entities(root).items():
        if "archive" in ref.path.parts:
            continue
        text = read_text(ref.path)
        for val in re.findall(r"(?:email|phone):\s*(.+?)\s*$", text, re.MULTILINE):
            owners.setdefault(val.strip().lower(), []).append(eid)
    return [{"type": "strong_identifier_conflict", "key": k, "detail": ", ".join(v)} for k, v in owners.items() if len(set(v)) > 1]


def _relation_conflicts(root: Path) -> list[dict[str, str]]:
    rows = links(root)
    seen: dict[tuple[str, str, str], set[str]] = {}
    for r in rows:
        key = (r.get("source", ""), r.get("type", ""), r.get("target", ""))
        seen.setdefault(key, set()).add(r.get("status", ""))
    out = []
    for key, statuses in seen.items():
        if "current" in statuses and "ended" in statuses:
            out.append({"type": "relation_status_conflict", "key": "|".join(key), "detail": ", ".join(sorted(statuses))})
    return out
