"""K1 Identity Service — stable IDs, alias management, entity resolution, dedup."""
from __future__ import annotations

import re
from pathlib import Path

from .common import (
    ENTITY_ID_RE,
    ID_RE,
    frontmatter,
    is_v1_vault,
    read_text,
    resolve_entity_any,
    scan_entities,
    stable_suffix,
    today,
    write_text,
)


def allocate_id(prefix: str, seed: str) -> str:
    entity_id = f"{prefix}_{stable_suffix(seed + today())}"
    return entity_id


def resolve(root: Path, name_or_id: str) -> str:
    """Resolve a name or ID to canonical entity ID."""
    if ENTITY_ID_RE.match(name_or_id):
        try:
            resolve_entity_any(root, name_or_id)
            return name_or_id
        except FileNotFoundError:
            pass
    entities = scan_entities(root)
    if name_or_id in entities:
        return name_or_id
    for eid, ref in entities.items():
        text = read_text(ref.path)
        if _name_matches(text, name_or_id):
            return eid
    raise FileNotFoundError(f"cannot resolve: {name_or_id}")


def confirm_alias(root: Path, entity_id: str, alias: str, platform: str = "", status: str = "confirmed") -> Path:
    """Add or confirm an alias for an entity."""
    path = resolve_entity_any(root, entity_id)
    text = read_text(path)
    alias_entry = f"    - value: {alias}\n      platform: {platform}\n      src: user\n      status: {status}"
    if "  aliases: []" in text:
        text = text.replace("  aliases: []", f"  aliases:\n{alias_entry}")
    elif "  aliases:" in text:
        text = text.replace("  aliases:", f"  aliases:\n{alias_entry}", 1)
    write_text(path, text)
    return path


def suggest_merges(root: Path) -> list[dict]:
    """Detect potential duplicate entities based on name/alias overlap."""
    entities = scan_entities(root)
    name_map: dict[str, list[str]] = {}
    for eid, ref in entities.items():
        if "archive" in ref.path.parts:
            continue
        text = read_text(ref.path)
        names = _extract_all_names(text)
        for name in names:
            normalized = name.lower().strip()
            if normalized and normalized != "todo(user)":
                name_map.setdefault(normalized, []).append(eid)
    suggestions = []
    seen = set()
    for name, eids in name_map.items():
        unique = list(dict.fromkeys(eids))
        if len(unique) > 1:
            key = tuple(sorted(unique))
            if key not in seen:
                seen.add(key)
                suggestions.append({"name": name, "entities": unique, "confidence": "medium"})
    return suggestions


def entity_type_from_id(entity_id: str) -> str:
    prefix = entity_id.split("_")[0]
    return {"p": "person", "a": "agent", "o": "org", "op": "operation", "tsc": "tsc"}.get(prefix, "unknown")


def _name_matches(text: str, query: str) -> bool:
    query_lower = query.lower()
    real_match = re.search(r"^\s*real:\s*(.+?)\s*$", text, re.MULTILINE)
    if real_match and query_lower in real_match.group(1).lower():
        return True
    for alias in re.findall(r"value:\s*(.+?)\s*$", text, re.MULTILINE):
        if query_lower in alias.lower():
            return True
    return False


def _extract_all_names(text: str) -> list[str]:
    names = []
    real_match = re.search(r"^\s*real:\s*(.+?)\s*$", text, re.MULTILINE)
    if real_match:
        names.append(real_match.group(1))
    for alias in re.findall(r"value:\s*(.+?)\s*$", text, re.MULTILINE):
        names.append(alias)
    return names
