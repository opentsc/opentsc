"""Vault initialization and upgrade for both legacy (v0.4) and v1.0 layouts."""
from __future__ import annotations

import re
from pathlib import Path

from .common import ID_RE, VAULT_DIRS, VAULT_DIRS_V1, copy_template, is_v1_vault, read_text, write_text

# Legacy root contract files (v0.4 compatibility)
ROOT_FILES_LEGACY = {
    "_doctrine.md": "doctrine.md",
    "_schema.md": "schema.md",
    "_filing.md": "filing.md",
    "_naming.md": "naming.md",
}
LEDGERS = ["identity-merges.jsonl", "archives.jsonl", "file-moves.jsonl", "processing-runs.jsonl", "action-runs.jsonl"]
INDEXES = {
    "actions/index.md": "# Actions Index\n\nGenerated index placeholder. Use `opentsc actions` for live listing.\n",
    "knowledge/index.md": "# Knowledge Index\n\nFacts, methods, principles, and sources live under this directory.\n",
    "relations/index.md": "# Relations Index\n\nMachine edge table: `edges.jsonl`.\n",
    "skills/registry/README.md": "# Skill Registry\n\nRecords skills OpenTSC may recommend/orchestrate from Claude, when available.\n",
}


def upgrade(root: Path) -> dict[str, list[str]]:
    """Initialize or upgrade a vault. Creates v1.0 structure by default."""
    created_dirs: list[str] = []
    created_files: list[str] = []

    # Create all v1.0 directories
    for rel in VAULT_DIRS_V1:
        path = root / rel
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created_dirs.append(str(path))

    # Legacy root files (keep for backward compat)
    for target_name, template_name in ROOT_FILES_LEGACY.items():
        if copy_template(template_name, root / target_name):
            created_files.append(str(root / target_name))

    # Soul seed files
    from .soul import init_soul
    soul_files = init_soul(root)
    created_files.extend(soul_files)

    # Shell: profession definitions
    from .professions import init_professions
    prof_files = init_professions(root)
    created_files.extend(prof_files)

    # Shell: module registry
    registry_path = root / "shell" / "modules" / "_registry.md"
    if not registry_path.exists():
        write_text(registry_path, "---\ntype: module_registry\nupdated: v1.0\n---\n\n# Module Registry\n\n")
        created_files.append(str(registry_path))

    # Ledgers
    for ledger in LEDGERS:
        path = root / "ledger" / ledger
        if not path.exists():
            write_text(path, "")
            created_files.append(str(path))

    # Index files
    for rel, content in INDEXES.items():
        path = root / rel
        if not path.exists():
            write_text(path, content)
            created_files.append(str(path))

    # Skill registry
    try:
        from .skills import init_skill_registry
        init_skill_registry(root)
    except Exception:
        pass

    return {"created_dirs": created_dirs, "created_files": created_files, "naming_issues": naming_audit(root)}


def naming_audit(root: Path) -> list[str]:
    """Audit vault naming conventions."""
    issues: list[str] = []

    if is_v1_vault(root):
        _audit_v1_structure(root, issues)
    else:
        # Legacy audit
        for required in ROOT_FILES_LEGACY:
            if not (root / required).exists():
                issues.append(f"missing root contract file: {required}")
        _audit_entities(root, issues)

    _audit_actions(root, issues)
    _audit_raw(root, issues)
    _audit_inbox(root, issues)
    return issues


def _audit_v1_structure(root: Path, issues: list[str]) -> None:
    """Audit v1.0 soul/shell/world structure."""
    # Soul files
    for required in ["_genesis.md", "_judgment_codex.md", "_rule_codex.md", "_schema.md"]:
        if not (root / "soul" / required).exists():
            issues.append(f"missing soul file: soul/{required}")

    # World entities
    checks = [
        (root / "world" / "npcs" / "humans", "p_"),
        (root / "world" / "npcs" / "agents", "a_"),
        (root / "world" / "players", "p_"),
        (root / "world" / "orgs", "o_"),
        (root / "world" / "operations", "op_"),
    ]
    for base, prefix in checks:
        if not base.exists():
            continue
        for path in base.glob("**/*.md"):
            text = read_text(path)
            match = ID_RE.search(text)
            if not match:
                issues.append(f"entity file missing id: {path}")
                continue
            eid = match.group(1)
            if not eid.startswith(prefix):
                issues.append(f"entity id prefix mismatch: {path} has {eid}, expected {prefix}")

    # Events
    events_dir = root / "soul" / "events"
    if events_dir.exists():
        for path in events_dir.rglob("evt_*.md"):
            text = read_text(path)
            if "admiralty:" not in text:
                issues.append(f"event missing admiralty: {path}")
            if "links:" not in text:
                issues.append(f"event missing links: {path}")

    # Shell: professions
    prof_dir = root / "shell" / "professions"
    if not prof_dir.exists() or not list(prof_dir.glob("*.md")):
        issues.append("missing shell/professions/ (run init to create preset professions)")


def _audit_entities(root: Path, issues: list[str]) -> None:
    """Legacy entity audit."""
    checks = [(root / "people", "p_"), (root / "orgs", "o_"), (root / "operations", "op_")]
    for base, prefix in checks:
        if not base.exists():
            continue
        for path in base.glob("**/*.md"):
            text = read_text(path)
            match = ID_RE.search(text)
            if not match:
                issues.append(f"entity file missing id: {path}")
                continue
            eid = match.group(1)
            if not eid.startswith(prefix):
                issues.append(f"entity id prefix mismatch: {path} has {eid}, expected {prefix}")
            if path.name != f"{eid}.md" and path.name != "profile.md":
                issues.append(f"entity filename should be {eid}.md or profile.md: {path}")


def _audit_actions(root: Path, issues: list[str]) -> None:
    for status in ["proposed", "active", "waiting", "done", "dropped"]:
        for path in (root / "actions" / status).glob("*.md"):
            if not path.name.startswith("act_"):
                issues.append(f"action file must start with act_: {path}")
            text = read_text(path)
            if f"status: {status}" not in text:
                issues.append(f"action status does not match folder {status}: {path}")


def _audit_raw(root: Path, issues: list[str]) -> None:
    for path in (root / "raw").glob("**/*"):
        if path.is_file() and not path.name.startswith("raw_"):
            issues.append(f"raw file must start with raw_: {path}")


def _audit_inbox(root: Path, issues: list[str]) -> None:
    for folder in ["events", "entities", "relations", "knowledge", "actions", "conflicts"]:
        for path in (root / "inbox" / folder).glob("*.md"):
            if not path.name.startswith("draft_") and folder != "conflicts":
                issues.append(f"inbox candidate should start with draft_: {path}")
