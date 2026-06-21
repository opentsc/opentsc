"""v0.4 → v1.0 vault migration.

Transforms the flat vault structure (people/orgs/operations) into the
soul/shell/world architecture while preserving all data.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from .common import (
    EVENT_RE,
    ID_RE,
    frontmatter,
    now_iso,
    read_text,
    soul_path,
    stable_suffix,
    today,
    world_path,
    write_text,
)


def migrate_v04_to_v10(root: Path) -> dict:
    """Full migration from v0.4 flat structure to v1.0 soul/shell/world.

    Returns a migration manifest with details of what was moved.
    """
    manifest = {
        "started_at": now_iso(),
        "source_version": "0.4",
        "target_version": "1.0",
        "moved_entities": [],
        "extracted_events": [],
        "created_dirs": [],
        "created_files": [],
        "warnings": [],
    }

    # Phase 1: Create new directory skeleton
    _create_v1_skeleton(root, manifest)

    # Phase 2: Initialize soul with seed files
    _init_soul_from_legacy(root, manifest)

    # Phase 3: Move entities to world/
    _migrate_people(root, manifest)
    _migrate_orgs(root, manifest)
    _migrate_operations(root, manifest)

    # Phase 4: Extract inline events → soul/events/
    _extract_inline_events(root, manifest)

    # Phase 5: Move feedback → soul/calibration/
    _migrate_feedback(root, manifest)

    # Phase 6: Initialize shell skeleton
    _init_shell(root, manifest)

    # Phase 7: Write migration manifest
    manifest["completed_at"] = now_iso()
    ledger_path = root / "ledger" / "migration_v04_v10.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    write_text(ledger_path, json.dumps(manifest, ensure_ascii=False, indent=2))

    return manifest


def _create_v1_skeleton(root: Path, manifest: dict) -> None:
    """Create soul/, shell/, world/ directories."""
    dirs = [
        "soul", "soul/events", "soul/calibration",
        "shell", "shell/kernel", "shell/modules", "shell/professions",
        "shell/genesis_engine", "shell/genesis_engine/templates",
        "world", "world/players", "world/npcs", "world/npcs/humans",
        "world/npcs/agents", "world/orgs", "world/operations", "world/roles",
    ]
    for d in dirs:
        path = root / d
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            manifest["created_dirs"].append(str(path))


def _init_soul_from_legacy(root: Path, manifest: dict) -> None:
    """Create soul seed files, migrating _doctrine.md content where possible."""
    sp = soul_path(root)

    # Genesis
    genesis_path = sp / "_genesis.md"
    if not genesis_path.exists():
        doctrine_path = root / "_doctrine.md"
        if doctrine_path.exists():
            doctrine_text = read_text(doctrine_path)
            write_text(genesis_path, f"""---
tsc_id: tsc_{stable_suffix(doctrine_text[:100] + today())}
created: {today()}
write_once: true
migrated_from: _doctrine.md
---

# Genesis — 创世层 (migrated from v0.4 _doctrine.md)

## 存在宣言

TODO(user): 从 _doctrine.md 提炼存在宣言

## 不可逾越的底线

TODO(user): 从 _doctrine.md 提炼底线

## 玩家

- id: TODO(user p_id)
  irrevocable_powers: [confirm_draft, declare_complete, amend_genesis]

## 初始目标

TODO(user): 定义初始目标

## 环境

TODO(user): 定义运作环境

## 原始 doctrine 内容 (供参考)

{doctrine_text[:2000]}
""")
        else:
            from .common import copy_template
            copy_template("genesis_seed.md", genesis_path)
        manifest["created_files"].append(str(genesis_path))

    # Rule codex
    rule_path = sp / "_rule_codex.md"
    if not rule_path.exists():
        from .common import copy_template
        copy_template("rule_codex_seed.md", rule_path)
        manifest["created_files"].append(str(rule_path))

    # Judgment codex
    jc_path = sp / "_judgment_codex.md"
    if not jc_path.exists():
        from .common import copy_template
        copy_template("judgment_codex_seed.md", jc_path)
        manifest["created_files"].append(str(jc_path))

    # Schema
    schema_src = root / "_schema.md"
    schema_dst = sp / "_schema.md"
    if schema_src.exists() and not schema_dst.exists():
        shutil.copy2(schema_src, schema_dst)
        manifest["created_files"].append(str(schema_dst))
    elif not schema_dst.exists():
        from .common import copy_template
        copy_template("schema.md", schema_dst)
        manifest["created_files"].append(str(schema_dst))


def _migrate_people(root: Path, manifest: dict) -> None:
    """Move people/ → world/npcs/humans/ (default to human NPC)."""
    people_dir = root / "people"
    if not people_dir.exists():
        return
    target_base = world_path(root) / "npcs" / "humans"
    for path in list(people_dir.rglob("*.md")):
        if "archive" in path.parts:
            continue
        text = read_text(path)
        fm = frontmatter(text)
        id_match = ID_RE.search(fm) if fm else None
        entity_id = id_match.group(1) if id_match else path.stem

        # Upgrade to v1 person format: add base attributes, skills, states
        text = _upgrade_person_format(text, entity_id)

        if path.name == "profile.md":
            target_dir = target_base / entity_id
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / "profile.md"
        else:
            target_dir = target_base / entity_id
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / "profile.md"

        write_text(target, text)
        manifest["moved_entities"].append({
            "id": entity_id, "from": str(path), "to": str(target), "type": "human_npc"
        })


def _migrate_orgs(root: Path, manifest: dict) -> None:
    """Move orgs/ → world/orgs/."""
    orgs_dir = root / "orgs"
    if not orgs_dir.exists():
        return
    target_base = world_path(root) / "orgs"
    for path in list(orgs_dir.rglob("*.md")):
        if "archive" in path.parts:
            continue
        text = read_text(path)
        fm = frontmatter(text)
        id_match = ID_RE.search(fm) if fm else None
        entity_id = id_match.group(1) if id_match else path.stem

        if path.name == "profile.md":
            target_dir = target_base / entity_id
        else:
            target_dir = target_base / entity_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / "profile.md"
        write_text(target, text)
        manifest["moved_entities"].append({
            "id": entity_id, "from": str(path), "to": str(target), "type": "org"
        })


def _migrate_operations(root: Path, manifest: dict) -> None:
    """Move operations/ → world/operations/."""
    ops_dir = root / "operations"
    if not ops_dir.exists():
        return
    target_base = world_path(root) / "operations"
    for path in list(ops_dir.rglob("*.md")):
        if "archive" in path.parts:
            continue
        text = read_text(path)
        fm = frontmatter(text)
        id_match = ID_RE.search(fm) if fm else None
        entity_id = id_match.group(1) if id_match else path.stem

        if path.name == "profile.md":
            target_dir = target_base / entity_id
        else:
            target_dir = target_base / entity_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / "profile.md"
        write_text(target, text)
        manifest["moved_entities"].append({
            "id": entity_id, "from": str(path), "to": str(target), "type": "operation"
        })


def _extract_inline_events(root: Path, manifest: dict) -> None:
    """Extract inline timeline events from entity files into soul/events/."""
    events_base = soul_path(root) / "events"
    index_entries = []

    # Scan all entity files in world/ for inline events
    for path in world_path(root).rglob("*.md"):
        text = read_text(path)
        fm = frontmatter(text)
        id_match = ID_RE.search(fm) if fm else None
        entity_id = id_match.group(1) if id_match else None
        if not entity_id:
            continue

        for line in text.splitlines():
            stripped = line.strip()
            if not EVENT_RE.match(stripped):
                continue

            # Parse: - YYYY-MM-DD · A1 · content ·〔来源: source; raw: raw_id; status: active〕
            match = re.match(
                r"^-\s*(\d{4}-\d{2}-\d{2})\s*·\s*([A-F][1-6])\s*·\s*(.+?)\s*·〔来源:\s*(.+?)〕",
                stripped
            )
            if not match:
                continue

            evt_date = match.group(1)
            admiralty = match.group(2)
            content = match.group(3).strip()
            source_block = match.group(4)

            # Parse source block for source and raw_id
            source = source_block
            raw_id = ""
            status = "active"
            for part in source_block.split(";"):
                part = part.strip()
                if part.startswith("raw:"):
                    raw_id = part[4:].strip()
                elif part.startswith("status:"):
                    status = part[7:].strip()
                elif not part.startswith("raw") and not part.startswith("status"):
                    source = part.strip()

            ym = evt_date[:7]
            evt_id = f"evt_{evt_date.replace('-', '')}_{stable_suffix(content + entity_id, 8)}"
            evt_dir = events_base / ym
            evt_dir.mkdir(parents=True, exist_ok=True)
            evt_path = evt_dir / f"{evt_id}.md"

            if not evt_path.exists():
                evt_content = f"""---
id: {evt_id}
date: {evt_date}
admiralty: {admiralty}
source: {source}
raw: {raw_id}
status: {status}
links: [{entity_id}]
caused_by: []
causes: []
judgment_triggered: []
migrated_from: {path.name}
---

{content}
"""
                write_text(evt_path, evt_content)
                index_entries.append({"entity": entity_id, "event": evt_id})
                manifest["extracted_events"].append({
                    "event_id": evt_id, "entity": entity_id, "date": evt_date
                })

    # Write reverse index
    if index_entries:
        index_path = events_base / "_index.jsonl"
        with index_path.open("a", encoding="utf-8") as f:
            for entry in index_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _migrate_feedback(root: Path, manifest: dict) -> None:
    """Move feedback/ → soul/calibration/."""
    feedback_dir = root / "feedback"
    if not feedback_dir.exists():
        return
    cal_dir = soul_path(root) / "calibration"
    for path in feedback_dir.rglob("*.md"):
        rel = path.relative_to(feedback_dir)
        target = cal_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(path, target)
            manifest["created_files"].append(str(target))


def _init_shell(root: Path, manifest: dict) -> None:
    """Initialize shell/ with kernel docs and profession files."""
    from .professions import init_professions
    created = init_professions(root)
    manifest["created_files"].extend(created)

    # Module registry
    registry_path = root / "shell" / "modules" / "_registry.md"
    if not registry_path.exists():
        write_text(registry_path, f"""---
type: module_registry
updated: {today()}
---

# Module Registry

Modules registered in this shell. Each module is an Agent Skill (SKILL.md).

## Active modules

(none yet — modules are created by the genesis engine as needed)
""")
        manifest["created_files"].append(str(registry_path))


def _upgrade_person_format(text: str, entity_id: str) -> str:
    """Upgrade a v0.4 person file to v1.0 format with three-layer attributes."""
    fm = frontmatter(text)
    if not fm:
        return text

    # Add type if missing
    if "type:" not in fm:
        text = text.replace(f"id: {entity_id}", f"id: {entity_id}\ntype: human_npc", 1)

    # Add source_mode
    if "source_mode:" not in text:
        text = text.replace("tags:", "source_mode: inferred\ntags:", 1)

    # Add professions if missing
    if "professions:" not in text:
        text = text.replace("tags:", "professions: []\ntags:", 1)

    # Add base attributes if missing
    if "base:" not in text:
        # Extract existing reliability value if present
        reliability_val = "0.5"
        rel_match = re.search(r"reliability:\n\s+value:\s*(\S+)", text)
        if rel_match and rel_match.group(1) not in ("TODO(0-1)", "TODO"):
            reliability_val = rel_match.group(1)

        base_block = f"""base:
  execution_ceiling: {{value: 0.5, confidence: 0.2, provenance: [], reviewed: null, decay: 0.02}}
  learning_speed: {{value: 0.5, confidence: 0.2, provenance: [], reviewed: null, decay: 0.02}}
  resilience: {{value: 0.5, confidence: 0.2, provenance: [], reviewed: null, decay: 0.02}}
  reliability: {{value: {reliability_val}, confidence: 0.2, provenance: [], reviewed: null, decay: 0.02}}
  autonomy: {{value: 0.5, confidence: 0.2, provenance: [], reviewed: null, decay: 0.02}}"""

        # Insert before skills: or tags:
        if "skills:" in text:
            text = text.replace("skills:", base_block + "\nskills:", 1)
        elif "tags:" in text:
            text = text.replace("tags:", base_block + "\ntags:", 1)

    # Convert flat skills array to skill tree format
    skills_match = re.search(r"^skills:\s*\[(.+?)\]\s*$", text, re.MULTILINE)
    if skills_match and skills_match.group(1).strip():
        old_skills = [s.strip() for s in skills_match.group(1).split(",") if s.strip()]
        new_skills = "\n".join(
            f"  - {{id: {s}, level: 1, prereq_met: true, leveled_by: []}}"
            for s in old_skills
        )
        text = re.sub(
            r"^skills:\s*\[.+?\]\s*$",
            f"skills:\n{new_skills}",
            text, count=1, flags=re.MULTILINE
        )

    # Add states if missing
    if "states:" not in text:
        text = text.replace("trust:", "states: []\ntrust:", 1)

    return text
