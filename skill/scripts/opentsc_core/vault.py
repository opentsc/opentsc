from __future__ import annotations

import json
from pathlib import Path

from .common import (
    append_text,
    append_under_heading,
    copy_template,
    ensure_vault,
    month,
    now_iso,
    read_text,
    resolve_entity_file,
    sanitize_filename,
    stable_suffix,
    template,
    today,
    unique_path,
    validate_entity_id,
    write_text,
)


def init_vault(root: Path) -> list[str]:
    from .upgrade import upgrade

    result = upgrade(root)
    return result["created_dirs"] + result["created_files"]


def new_person(root: Path, name: str, entity_id: str | None = None, aliases: list[str] | None = None, tags: list[str] | None = None) -> Path:
    ensure_vault(root)
    entity_id = entity_id or f"p_{stable_suffix(name + today())}"
    validate_entity_id(entity_id, "p_")
    target = unique_path(root / "people" / f"{entity_id}.md")
    content = template("person.md")
    content = content.replace("p_TODO", entity_id)
    content = content.replace("real: TODO(user)", f"real: {name}")
    content = content.replace("reviewed: TODO(date)", f"reviewed: {today()}")
    if tags:
        content = content.replace("tags: []", "tags: [" + ", ".join(tags) + "]")
    if aliases:
        alias_lines = "\n".join([f"    - value: {a}\n      src: TODO(user)\n      status: suspected" for a in aliases])
        content = content.replace("  aliases: []", f"  aliases:\n{alias_lines}")
    write_text(target, content)
    return target


def new_org(root: Path, name: str, entity_id: str | None = None, tags: list[str] | None = None) -> Path:
    ensure_vault(root)
    entity_id = entity_id or f"o_{stable_suffix(name + today())}"
    validate_entity_id(entity_id, "o_")
    org_dir = root / "orgs" / entity_id
    org_dir.mkdir(parents=True, exist_ok=False)
    target = org_dir / "profile.md"
    tag_text = "[" + ", ".join(tags or []) + "]"
    content = f"""---
id: {entity_id}
type: org
names:
  real: {name}
  aliases: []
tags: {tag_text}
---

## Relationship edges

## Intelligence timeline

"""
    write_text(target, content)
    return target


def new_operation(root: Path, title: str, deadline: str | None = None, entity_id: str | None = None) -> Path:
    ensure_vault(root)
    seed = f"{title}-{deadline or today()}"
    entity_id = entity_id or f"op_{stable_suffix(seed)}"
    validate_entity_id(entity_id, "op_")
    op_dir = root / "operations" / entity_id
    op_dir.mkdir(parents=True, exist_ok=False)
    target = op_dir / "profile.md"
    content = template("operation.md")
    content = content.replace("op_TODO", entity_id)
    content = content.replace("deadline: TODO(optional)", f"deadline: {deadline or 'TODO(optional)'}")
    content = content.replace("TODO(user)", title, 1)
    write_text(target, content)
    return target


def add_event(root: Path, entity: str, admiralty: str, content: str, source: str, date: str | None = None, raw_id: str | None = None, status: str = "active") -> Path:
    from .common import require_admiralty

    require_admiralty(admiralty)
    target = resolve_entity_file(root, entity)
    raw_part = f"; raw: {raw_id}" if raw_id else ""
    line = f"- {date or today()} · {admiralty} · {content} ·〔来源: {source}{raw_part}; status: {status}〕\n"
    append_under_heading(target, "## Intelligence timeline", line, fallback_heading="## Progress timeline")
    return target


def store_raw(root: Path, title: str, content: str, source: str, material_type: str = "note") -> Path:
    ensure_vault(root)
    raw_id = f"raw_{today().replace('-', '')}_{stable_suffix(title + content, 8)}"
    filename = f"{raw_id}-{sanitize_filename(title)}.md"
    target = root / "raw" / filename
    body = f"""---
id: {raw_id}
type: raw_material
material_type: {material_type}
title: {title}
source: {source}
source_date: TODO(user)
ingested_at: {now_iso()}
created_at: {now_iso()}
status: raw
---

# {title}

{content.rstrip()}
"""
    write_text(target, body)
    return target


def draft_inbox_event(root: Path, entity: str, admiralty: str, content: str, source: str, raw_id: str | None = None) -> Path:
    from .common import require_admiralty

    require_admiralty(admiralty)
    ensure_vault(root)
    draft_id = f"draft_{today().replace('-', '')}_{stable_suffix(entity + content, 8)}"
    target = root / "inbox" / f"{draft_id}.md"
    body = f"""---
id: {draft_id}
type: inbox_event
entity: {entity}
admiralty: {admiralty}
source: {source}
raw: {raw_id or 'TODO(optional)'}
status: draft
created: {today()}
---

# Candidate event

{content}

## If accepted

- {today()} · {admiralty} · {content} ·〔来源: {source}{'; raw: ' + raw_id if raw_id else ''}; status: pending_verification〕
"""
    write_text(target, body)
    return target


def stage_prediction(root: Path, kind: str, context: str, claim: str, due: str, reasoning: list[str]) -> Path:
    ensure_vault(root)
    pred_id = f"pred_{stable_suffix(kind + context + due, 8)}"
    target = root / "feedback" / month() / f"{pred_id}.md"
    reasoning_text = "\n".join(f"{i + 1}. {item}" for i, item in enumerate(reasoning)) or "1. TODO(user)"
    body = template("prediction.md")
    body = body.replace("pred_TODO", pred_id)
    body = body.replace("created: YYYY-MM-DD", f"created: {today()}")
    body = body.replace("due: YYYY-MM-DD", f"due: {due}")
    body = body.replace("context: TODO(short context)", f"context: {context}")
    body = body.replace("kind: recommendation", f"kind: {kind}")
    body = body.replace("TODO(content)", claim)
    body = body.replace("1. Evidence: TODO(event IDs / knowledge IDs)\n2. Interpretation: TODO(logic)\n3. Expected outcome: TODO(testable result)", reasoning_text)
    write_text(target, body)
    return target


def append_jsonl(path: Path, row: dict) -> None:
    append_text(path, json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
