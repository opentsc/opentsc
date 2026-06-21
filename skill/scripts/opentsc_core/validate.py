"""Vault validation for both legacy (v0.4) and v1.0 layouts."""
from __future__ import annotations

import re
from pathlib import Path

from .common import (
    DUE_RE,
    EVENT_MISSING_RATING_RE,
    EVENT_RE,
    ID_RE,
    REASONING_RE,
    TYPE_RE,
    frontmatter,
    is_v1_vault,
    iter_markdown,
    read_text,
    soul_path,
)
from .conflicts import detect_conflicts


def validate_vault(root: Path, check_conflicts: bool = False, include_archive: bool = False) -> list[str]:
    """Validate vault contracts. Supports both legacy and v1.0 layouts."""
    errors: list[str] = []
    seen_ids: dict[str, Path] = {}

    if is_v1_vault(root):
        _validate_v1_soul(root, errors)
        _validate_v1_events(root, errors)
        _validate_v1_world(root, errors, seen_ids, include_archive)
        _validate_v1_shell(root, errors)
    else:
        _validate_legacy(root, errors, seen_ids, include_archive)

    # Common validations
    _validate_common(root, errors, seen_ids, include_archive)

    if check_conflicts:
        for c in detect_conflicts(root):
            errors.append(f"conflict:{c['type']} {c['key']} {c['detail']}")

    return errors


def _validate_v1_soul(root: Path, errors: list[str]) -> None:
    """Validate soul/ directory (Laws 1, 2, 4, 7, 8)."""
    sp = soul_path(root)

    # Genesis must exist (Law 1)
    genesis = sp / "_genesis.md"
    if not genesis.exists():
        errors.append("missing soul/_genesis.md (Law 1: genesis required)")
    else:
        text = read_text(genesis)
        if "write_once: true" not in text:
            errors.append("soul/_genesis.md missing write_once: true marker")

    # Dual codex (Law 7)
    if not (sp / "_judgment_codex.md").exists():
        errors.append("missing soul/_judgment_codex.md (Law 7: judgment codex required)")
    if not (sp / "_rule_codex.md").exists():
        errors.append("missing soul/_rule_codex.md (Law 7: rule codex required)")

    # Schema (K5)
    if not (sp / "_schema.md").exists():
        errors.append("missing soul/_schema.md (K5: field ontology required)")


def _validate_v1_events(root: Path, errors: list[str]) -> None:
    """Validate event graph nodes (Law 4, 5)."""
    events_dir = soul_path(root) / "events"
    if not events_dir.exists():
        return

    seen_events: set[str] = set()
    for path in events_dir.rglob("evt_*.md"):
        text = read_text(path)
        fm = frontmatter(text)
        if not fm:
            errors.append(f"event missing frontmatter: {path}")
            continue

        id_match = ID_RE.search(fm)
        if not id_match:
            errors.append(f"event missing id: {path}")
            continue

        evt_id = id_match.group(1)
        if evt_id in seen_events:
            errors.append(f"duplicate event id: {evt_id}")
        seen_events.add(evt_id)

        # Law 5: evidence before judgment
        if "admiralty:" not in fm:
            errors.append(f"event missing admiralty rating (Law 5): {path}")
        if "source:" not in fm:
            errors.append(f"event missing source (Law 5): {path}")
        if "links:" not in fm:
            errors.append(f"event missing links field: {path}")


def _validate_v1_world(root: Path, errors: list[str], seen_ids: dict[str, Path], include_archive: bool) -> None:
    """Validate world/ entities (Laws 3, 9)."""
    world = root / "world"
    if not world.exists():
        errors.append("missing world/ directory")
        return

    for path in world.rglob("*.md"):
        if not include_archive and "archive" in path.parts:
            continue
        text = read_text(path)
        fm = frontmatter(text)
        if not fm:
            continue

        id_match = ID_RE.search(fm)
        if not id_match:
            if TYPE_RE.search(fm):
                errors.append(f"frontmatter type without id: {path}")
            continue

        entity_id = id_match.group(1)
        if entity_id in seen_ids:
            errors.append(f"duplicate id {entity_id}: {seen_ids[entity_id]} and {path}")
        seen_ids[entity_id] = path

        # Law 9: attributes must have provenance
        if "base:" in fm:
            _validate_attribute_claims(fm, entity_id, errors)


def _validate_v1_shell(root: Path, errors: list[str]) -> None:
    """Validate shell/ structure."""
    shell = root / "shell"
    if not shell.exists():
        errors.append("missing shell/ directory")
        return

    if not (shell / "professions").exists():
        errors.append("missing shell/professions/ directory")

    registry = shell / "modules" / "_registry.md"
    if not registry.exists():
        errors.append("missing shell/modules/_registry.md")


def _validate_attribute_claims(fm_text: str, entity_id: str, errors: list[str]) -> None:
    """Check that AttributeClaim fields have proper structure."""
    # Look for base attribute patterns without provenance
    for match in re.finditer(r"(\w+):\s*\{(.+?)\}", fm_text):
        dim_name = match.group(1)
        claim_text = match.group(2)
        if "value:" in claim_text and "provenance:" not in claim_text:
            errors.append(f"attribute {entity_id}.{dim_name} missing provenance (Law 9)")


def _validate_legacy(root: Path, errors: list[str], seen_ids: dict[str, Path], include_archive: bool) -> None:
    """Legacy v0.4 validation."""
    if not (root / "_schema.md").exists():
        errors.append("missing _schema.md")
    if not (root / "_doctrine.md").exists():
        errors.append("missing _doctrine.md")
    if not (root / "_filing.md").exists():
        errors.append("missing _filing.md")
    if not (root / "_naming.md").exists():
        errors.append("missing _naming.md")

    for path in iter_markdown(root):
        if not include_archive and "archive" in path.parts:
            continue
        text = read_text(path)
        fm = frontmatter(text)
        if fm:
            id_match = ID_RE.search(fm)
            type_match = TYPE_RE.search(fm)
            if id_match:
                entity_id = id_match.group(1)
                if entity_id in seen_ids:
                    errors.append(f"duplicate id {entity_id}: {seen_ids[entity_id]} and {path}")
                seen_ids[entity_id] = path
            elif type_match:
                errors.append(f"frontmatter type without id: {path}")


def _validate_common(root: Path, errors: list[str], seen_ids: dict[str, Path], include_archive: bool) -> None:
    """Validations common to both layouts."""
    # Inline event format checks
    for path in iter_markdown(root):
        if not include_archive and "archive" in path.parts:
            continue
        text = read_text(path)
        for line_no, line in enumerate(text.splitlines(), 1):
            stripped = line.lstrip()
            if EVENT_MISSING_RATING_RE.match(stripped):
                errors.append(f"event missing Admiralty rating at {path}:{line_no}")
            if "·〔来源:" in stripped and stripped.startswith("-") and not EVENT_RE.match(stripped):
                errors.append(f"malformed event at {path}:{line_no}")

    # Raw material checks
    for p in (root / "raw").rglob("*"):
        if p.is_file() and p.suffix.lower() in {".md", ".txt"}:
            text = read_text(p)
            if "ingested_at:" not in text and "type: raw_material" in text:
                errors.append(f"raw material missing ingested_at: {p}")

    # Prediction checks (both soul/calibration and legacy feedback/)
    for cal_dir in [root / "soul" / "calibration", root / "feedback"]:
        if not cal_dir.exists():
            continue
        for path in cal_dir.rglob("*.md"):
            text = read_text(path)
            if "kind:" not in text:
                continue
            if not DUE_RE.search(text):
                errors.append(f"prediction missing due date: {path}")
            if not REASONING_RE.search(text):
                errors.append(f"prediction missing reasoning chain: {path}")

    # Knowledge granule checks
    knowledge = root / "knowledge"
    if knowledge.exists():
        for path in knowledge.rglob("*.md"):
            text = read_text(path)
            if "source_events:" in text:
                sample = re.search(r"^sample_size:\s*(.+?)\s*$", text, re.MULTILINE)
                if not sample or sample.group(1).startswith("TODO"):
                    errors.append(f"knowledge granule missing sample_size: {path}")
