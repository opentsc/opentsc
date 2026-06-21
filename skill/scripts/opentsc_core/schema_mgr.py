"""K5 Field Ontology — maintain _schema.md, register new fields, prevent drift."""
from __future__ import annotations

import re
from pathlib import Path

from .common import read_text, soul_path, today, write_text


def register_field(root: Path, field_name: str, field_type: str, description: str, layer: str = "base") -> None:
    """Register a new field in soul/_schema.md before use (Invariant 5)."""
    path = soul_path(root) / "_schema.md"
    if not path.exists():
        write_text(path, f"---\ntype: schema\nupdated: {today()}\n---\n\n# Field Ontology\n\n")
    text = read_text(path)
    if f"### {field_name}" in text:
        return
    entry = f"\n### {field_name}\n- type: {field_type}\n- layer: {layer}\n- description: {description}\n- registered: {today()}\n"
    text = text.rstrip() + entry + "\n"
    text = re.sub(r"^updated:\s*.+$", f"updated: {today()}", text, count=1, flags=re.MULTILINE)
    write_text(path, text)


def known_fields(root: Path) -> list[dict]:
    """List all registered fields."""
    path = soul_path(root) / "_schema.md"
    if not path.exists():
        return []
    text = read_text(path)
    fields = []
    current = None
    for line in text.splitlines():
        match = re.match(r"^### (\w+)", line)
        if match:
            if current:
                fields.append(current)
            current = {"name": match.group(1)}
            continue
        if current and line.strip().startswith("- type:"):
            current["type"] = line.split(":", 1)[1].strip()
        elif current and line.strip().startswith("- layer:"):
            current["layer"] = line.split(":", 1)[1].strip()
        elif current and line.strip().startswith("- description:"):
            current["description"] = line.split(":", 1)[1].strip()
    if current:
        fields.append(current)
    return fields


def validate_schema(root: Path) -> list[str]:
    """Check for unregistered fields in entity files."""
    known = {f["name"] for f in known_fields(root)}
    if not known:
        return []
    issues = []
    from .common import scan_entities, parse_frontmatter
    for eid, ref in scan_entities(root).items():
        text = read_text(ref.path)
        fm = parse_frontmatter(text)
        base = fm.get("base", {})
        if isinstance(base, dict):
            for dim in base:
                if dim not in known and dim not in {"_raw"}:
                    issues.append(f"unregistered field '{dim}' in {eid}")
    return issues
