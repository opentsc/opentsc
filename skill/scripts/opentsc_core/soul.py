"""Soul management — genesis, codex, export/import.

The soul is the portable, cross-shell-surviving core:
genesis + judgment_codex + rule_codex + event_stream + calibration_memory.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from .common import (
    copy_template,
    now_iso,
    parse_frontmatter,
    read_text,
    soul_path,
    today,
    write_text,
)


def init_soul(root: Path) -> list[str]:
    """Initialize soul directory with seed files."""
    sp = soul_path(root)
    sp.mkdir(parents=True, exist_ok=True)
    (sp / "events").mkdir(exist_ok=True)
    (sp / "calibration").mkdir(exist_ok=True)
    created = []
    for name, template_name in [
        ("_genesis.md", "genesis_seed.md"),
        ("_rule_codex.md", "rule_codex_seed.md"),
        ("_judgment_codex.md", "judgment_codex_seed.md"),
        ("_schema.md", "schema.md"),
    ]:
        target = sp / name
        if copy_template(template_name, target):
            created.append(str(target))
    return created


def read_genesis(root: Path) -> dict:
    path = soul_path(root) / "_genesis.md"
    if not path.exists():
        raise FileNotFoundError("soul/_genesis.md not found — run `soul init` first")
    return parse_frontmatter(read_text(path))


def write_genesis(root: Path, declaration: str, redlines: list[str], player_id: str,
                  goal: str, environment: str, tsc_id: str | None = None) -> Path:
    """Write genesis file (write-once). Raises if already finalized."""
    path = soul_path(root) / "_genesis.md"
    if path.exists():
        existing = read_text(path)
        if "write_once: true" in existing and "TODO" not in existing:
            raise ValueError("genesis already finalized — cannot overwrite (Law 1)")
    from .common import stable_suffix
    tsc_id = tsc_id or f"tsc_{stable_suffix(declaration + today())}"
    redline_text = "\n".join(f"- {r}" for r in redlines)
    content = f"""---
tsc_id: {tsc_id}
created: {today()}
write_once: true
---

# Genesis — 创世层

## 存在宣言

{declaration}

## 不可逾越的底线

{redline_text}

## 玩家

- id: {player_id}
  irrevocable_powers: [confirm_draft, declare_complete, amend_genesis]

## 初始目标

{goal}

## 环境

{environment}
"""
    write_text(path, content)
    return path


def read_judgment_codex(root: Path) -> dict:
    path = soul_path(root) / "_judgment_codex.md"
    if not path.exists():
        raise FileNotFoundError("soul/_judgment_codex.md not found")
    text = read_text(path)
    data = parse_frontmatter(text)
    data["_raw"] = text
    data["scoring_dimensions"] = _parse_codex_dimensions(text)
    data["skill_tree"] = _parse_codex_skills(text)
    data["state_rules"] = _parse_codex_states(text)
    return data


def read_rule_codex(root: Path) -> dict:
    path = soul_path(root) / "_rule_codex.md"
    if not path.exists():
        raise FileNotFoundError("soul/_rule_codex.md not found")
    return parse_frontmatter(read_text(path))


def export_soul(root: Path, target_dir: Path) -> Path:
    """Export soul/ directory for portability (Law 2)."""
    sp = soul_path(root)
    if not sp.exists():
        raise FileNotFoundError("no soul/ directory to export")
    target = target_dir / "soul"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(sp, target)
    manifest = {
        "exported_at": now_iso(),
        "source": str(root),
        "genesis_exists": (target / "_genesis.md").exists(),
        "events_count": len(list(target.rglob("evt_*.md"))),
        "calibration_count": len(list(target.rglob("pred_*.md"))),
    }
    import json
    write_text(target / "_export_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return target


def import_soul(root: Path, source_dir: Path) -> list[str]:
    """Import a soul into this vault (Law 2 — revival)."""
    source_soul = source_dir if source_dir.name == "soul" else source_dir / "soul"
    if not source_soul.exists():
        raise FileNotFoundError(f"no soul/ in {source_dir}")
    sp = soul_path(root)
    if sp.exists():
        backup = root / f"soul_backup_{today().replace('-', '_')}"
        shutil.move(str(sp), str(backup))
    shutil.copytree(source_soul, sp)
    imported = [str(p) for p in sp.rglob("*") if p.is_file()]
    return imported


def propose_amendment(root: Path, target: str, section: str, change: str, reason: str) -> Path:
    """Propose an amendment to rule or judgment codex (Law 7 self-iteration)."""
    if target not in ("rule", "judgment"):
        raise ValueError("target must be 'rule' or 'judgment'")
    from .common import stable_suffix
    proposal_id = f"amendment_{target}_{today().replace('-', '')}_{stable_suffix(change, 6)}"
    path = root / "inbox" / f"{proposal_id}.md"
    content = f"""---
id: {proposal_id}
type: codex_amendment
target: {target}_codex
section: {section}
status: proposed
created: {today()}
---

# Proposed Amendment to {target} codex

## Section

{section}

## Change

{change}

## Reason

{reason}

## Status

Awaiting player approval.
"""
    write_text(path, content)
    return path


def _parse_codex_dimensions(text: str) -> dict:
    """Extract scoring dimensions from judgment codex markdown."""
    dims = {}
    in_section = False
    current_dim = None
    for line in text.splitlines():
        if line.strip().startswith("## 评分维度"):
            in_section = True
            continue
        if in_section and line.startswith("## ") and "评分维度" not in line:
            break
        if not in_section:
            continue
        dim_match = re.match(r"^### (\w+)\s*[—–-]\s*(.+)", line)
        if dim_match:
            current_dim = dim_match.group(1)
            dims[current_dim] = {"display": dim_match.group(2).strip(), "triggers": [], "positive": [], "negative": [], "default_decay": 0.02, "layer": "base"}
            continue
        if current_dim and line.strip().startswith("- triggers:"):
            dims[current_dim]["triggers"] = _extract_bracket_list(line)
        elif current_dim and line.strip().startswith("- positive:"):
            dims[current_dim]["positive"] = _extract_bracket_list(line)
        elif current_dim and line.strip().startswith("- negative:"):
            dims[current_dim]["negative"] = _extract_bracket_list(line)
        elif current_dim and line.strip().startswith("- default_decay:"):
            val = line.split(":", 1)[1].strip()
            try:
                dims[current_dim]["default_decay"] = float(val)
            except ValueError:
                pass
        elif current_dim and line.strip().startswith("- layer:"):
            dims[current_dim]["layer"] = line.split(":", 1)[1].strip()
    return dims


def _parse_codex_skills(text: str) -> list[dict]:
    """Extract skill tree from judgment codex."""
    skills = []
    in_section = False
    current = None
    for line in text.splitlines():
        if line.strip().startswith("## 技能树定义"):
            in_section = True
            continue
        if in_section and line.startswith("## ") and "技能树" not in line:
            break
        if not in_section:
            continue
        skill_match = re.match(r"^### (\w+)\s*[—–-]\s*(.+)", line)
        if skill_match:
            if current:
                skills.append(current)
            current = {"id": skill_match.group(1), "display": skill_match.group(2).strip(), "levels": {}, "prereqs": [], "upgrade_triggers": []}
            continue
        if current and line.strip().startswith("- prereqs:"):
            current["prereqs"] = _extract_bracket_list(line)
        elif current and line.strip().startswith("- upgrade_triggers:"):
            current["upgrade_triggers"] = _extract_bracket_list(line)
        elif current and re.match(r"^\s+\d+:", line.strip()):
            parts = line.strip().split(":", 1)
            if len(parts) == 2:
                try:
                    level = int(parts[0].strip())
                    current["levels"][level] = parts[1].strip().strip('"')
                except ValueError:
                    pass
    if current:
        skills.append(current)
    return skills


def _parse_codex_states(text: str) -> list[dict]:
    """Extract buff/debuff rules from judgment codex."""
    rules = []
    in_section = False
    current = None
    for line in text.splitlines():
        if line.strip().startswith("## Buff/Debuff"):
            in_section = True
            continue
        if in_section and line.startswith("## ") and "Buff" not in line:
            break
        if not in_section:
            continue
        rule_match = re.match(r"^### (.+)", line)
        if rule_match:
            if current:
                rules.append(current)
            current = {"name": rule_match.group(1).strip(), "pattern": "", "kind": "debuff", "tag": "", "duration_days": 7, "on_repeat": "solidify", "affects": [], "delta": 0}
            continue
        if current:
            for field in ["pattern", "kind", "tag", "on_repeat"]:
                if line.strip().startswith(f"- {field}:"):
                    current[field] = line.split(":", 1)[1].strip().strip('"')
            if line.strip().startswith("- duration_days:"):
                try:
                    current["duration_days"] = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            if line.strip().startswith("- affects:"):
                current["affects"] = _extract_bracket_list(line)
            if line.strip().startswith("- delta:"):
                try:
                    current["delta"] = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
    if current:
        rules.append(current)
    return rules


def _extract_bracket_list(line: str) -> list[str]:
    match = re.search(r"\[(.+?)\]", line)
    if not match:
        return []
    return [item.strip().strip('"\'') for item in match.group(1).split(",") if item.strip()]
