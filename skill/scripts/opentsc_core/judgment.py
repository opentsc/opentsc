"""K7 Judgment Engine — derive attributes from events via judgment_codex.

This is the heart of OpenTSC v1.0. When a new event arrives, K7 reads the
judgment_codex and automatically updates related entities' attributes.
No module may directly write attribute values (Invariant 8).
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from .common import (
    parse_frontmatter,
    read_text,
    resolve_entity_any,
    today,
    write_text,
)
from .events import mark_judgment_triggered, read_event, timeline
from .soul import read_judgment_codex


def on_event(root: Path, event_id: str) -> list[dict]:
    """Process a new event through the judgment engine.

    Reads the judgment_codex, determines which entities/dimensions are affected,
    computes updated values, writes patches. Returns list of patches applied.
    """
    evt = read_event(root, event_id)
    content = evt.get("content", "")
    linked_entities = evt.get("links", [])
    if isinstance(linked_entities, str):
        linked_entities = [linked_entities]

    try:
        codex = read_judgment_codex(root)
    except FileNotFoundError:
        return []

    patches = []

    for entity_id in linked_entities:
        try:
            entity_path = resolve_entity_any(root, entity_id)
        except FileNotFoundError:
            continue

        entity_patches = _evaluate_event_for_entity(root, codex, evt, entity_id, entity_path, content)
        patches.extend(entity_patches)

    if patches:
        triggered = [f"{p['entity']}.{p['dimension']}" for p in patches]
        mark_judgment_triggered(root, event_id, triggered)

    return patches


def attribute(root: Path, entity_id: str, dimension: str) -> dict:
    """Read current derived attribute value for an entity."""
    entity_path = resolve_entity_any(root, entity_id)
    text = read_text(entity_path)
    fm = parse_frontmatter(text)

    base = fm.get("base", {})
    if dimension in base:
        claim = base[dimension]
        if isinstance(claim, dict):
            return _normalize_claim(claim, dimension)

    skills = fm.get("skills", [])
    if isinstance(skills, list):
        for skill in skills:
            if isinstance(skill, dict) and skill.get("id") == dimension:
                return {
                    "dimension": dimension,
                    "type": "skill",
                    "level": skill.get("level", 0),
                    "leveled_by": skill.get("leveled_by", []),
                    "prereq_met": skill.get("prereq_met", False),
                }

    states = fm.get("states", [])
    if isinstance(states, list):
        for state in states:
            if isinstance(state, dict) and state.get("tag", "").startswith(dimension):
                return {
                    "dimension": dimension,
                    "type": "state",
                    "tag": state.get("tag", ""),
                    "kind": state.get("kind", ""),
                    "expires": state.get("expires", ""),
                    "source": state.get("source", ""),
                }

    return {"dimension": dimension, "type": "not_found", "value": None}


def compare(root: Path, id_a: str, id_b: str, dimension: str) -> dict:
    """Compare two entities on a dimension without re-reading event history."""
    attr_a = attribute(root, id_a, dimension)
    attr_b = attribute(root, id_b, dimension)

    val_a = _extract_comparable_value(attr_a)
    val_b = _extract_comparable_value(attr_b)

    if val_a is None or val_b is None:
        winner = "unknown"
    elif val_a > val_b:
        winner = id_a
    elif val_b > val_a:
        winner = id_b
    else:
        winner = "tie"

    return {
        "dimension": dimension,
        "entity_a": {"id": id_a, **attr_a},
        "entity_b": {"id": id_b, **attr_b},
        "winner": winner,
        "confidence": min(
            attr_a.get("confidence", 0) if isinstance(attr_a.get("confidence"), (int, float)) else 0,
            attr_b.get("confidence", 0) if isinstance(attr_b.get("confidence"), (int, float)) else 0,
        ),
    }


def explain(root: Path, entity_id: str, dimension: str) -> dict:
    """Explain which events led to the current attribute value."""
    attr = attribute(root, entity_id, dimension)
    provenance = attr.get("provenance", attr.get("leveled_by", []))
    if isinstance(provenance, str):
        provenance = [provenance]

    events = []
    for evt_id in provenance:
        try:
            evt = read_event(root, evt_id)
            events.append({
                "id": evt_id,
                "date": evt.get("date", ""),
                "content": evt.get("content", "")[:200],
                "admiralty": evt.get("admiralty", ""),
            })
        except FileNotFoundError:
            events.append({"id": evt_id, "date": "", "content": "(event not found)", "admiralty": ""})

    return {
        "entity": entity_id,
        "dimension": dimension,
        "current_value": attr,
        "evidence_events": events,
        "reasoning": f"Attribute {dimension} derived from {len(events)} events via judgment_codex",
    }


def apply_decay(root: Path) -> list[dict]:
    """Reduce confidence of stale attributes. Call periodically."""
    try:
        codex = read_judgment_codex(root)
    except FileNotFoundError:
        return []

    dims = codex.get("scoring_dimensions", {})
    decayed = []

    from .common import scan_entities
    for eid, ref in scan_entities(root).items():
        if "archive" in ref.path.parts:
            continue
        text = read_text(ref.path)
        fm = parse_frontmatter(text)
        base = fm.get("base", {})
        changed = False
        for dim_name, dim_def in dims.items():
            if dim_name in base and isinstance(base[dim_name], dict):
                claim = base[dim_name]
                reviewed = claim.get("reviewed")
                if reviewed and reviewed != "null":
                    try:
                        reviewed_date = dt.date.fromisoformat(str(reviewed))
                        months_stale = (dt.date.today() - reviewed_date).days / 30.0
                        if months_stale > 1:
                            decay_rate = dim_def.get("default_decay", 0.02)
                            old_conf = claim.get("confidence", 0.5)
                            if isinstance(old_conf, (int, float)):
                                new_conf = max(0.1, old_conf - decay_rate * months_stale)
                                if new_conf < old_conf:
                                    claim["confidence"] = round(new_conf, 3)
                                    changed = True
                                    decayed.append({"entity": eid, "dimension": dim_name, "old_confidence": old_conf, "new_confidence": new_conf})
                    except (ValueError, TypeError):
                        pass
        if changed:
            _write_base_attributes(ref.path, text, base)

    return decayed


# --- Internal: evaluate event against codex ---

def _evaluate_event_for_entity(
    root: Path, codex: dict, evt: dict, entity_id: str, entity_path: Path, content: str
) -> list[dict]:
    patches = []
    dims = codex.get("scoring_dimensions", {})
    skills = codex.get("skill_tree", [])
    state_rules = codex.get("state_rules", [])

    for dim_name, dim_def in dims.items():
        triggers = dim_def.get("triggers", [])
        if not _text_matches_any(content, triggers):
            continue
        positive = dim_def.get("positive", [])
        negative = dim_def.get("negative", [])
        is_positive = _text_matches_any(content, positive)
        is_negative = _text_matches_any(content, negative)
        if not is_positive and not is_negative:
            continue

        delta = 0.05 if is_positive else -0.05
        if is_positive and is_negative:
            delta = 0

        patch = _apply_base_attribute_patch(
            entity_path, dim_name, delta,
            evt.get("id", ""), evt.get("admiralty", "B3"),
            dim_def.get("default_decay", 0.02),
        )
        if patch:
            patch["entity"] = entity_id
            patches.append(patch)

    for skill_def in skills:
        skill_id = skill_def.get("id", "")
        upgrade_triggers = skill_def.get("upgrade_triggers", [])
        if _text_matches_any(content, upgrade_triggers):
            patch = _apply_skill_upgrade(entity_path, skill_id, evt.get("id", ""))
            if patch:
                patch["entity"] = entity_id
                patches.append(patch)

    for rule in state_rules:
        pattern = rule.get("pattern", "")
        if pattern and re.search(pattern, content):
            patch = _apply_state_change(entity_path, rule, evt.get("id", ""))
            if patch:
                patch["entity"] = entity_id
                patches.append(patch)

    return patches


def _text_matches_any(text: str, patterns: list[str]) -> bool:
    for p in patterns:
        if re.search(p, text):
            return True
    return False


def _apply_base_attribute_patch(
    entity_path: Path, dimension: str, delta: float,
    event_id: str, admiralty: str, decay: float,
) -> dict | None:
    text = read_text(entity_path)
    fm = parse_frontmatter(text)
    base = fm.get("base", {})

    current = base.get(dimension, {})
    if not isinstance(current, dict):
        current = {"value": 0.5, "confidence": 0.2, "provenance": [], "reviewed": None, "decay": decay}

    old_value = current.get("value", 0.5)
    if not isinstance(old_value, (int, float)):
        old_value = 0.5
    new_value = max(0.0, min(1.0, old_value + delta))

    old_conf = current.get("confidence", 0.2)
    if not isinstance(old_conf, (int, float)):
        old_conf = 0.2
    new_conf = min(0.95, old_conf + 0.05)

    provenance = current.get("provenance", [])
    if isinstance(provenance, str):
        provenance = [provenance]
    if event_id not in provenance:
        provenance = provenance + [event_id]
    if len(provenance) > 20:
        provenance = provenance[-20:]

    current["value"] = round(new_value, 3)
    current["confidence"] = round(new_conf, 3)
    current["provenance"] = provenance
    current["reviewed"] = today()
    current["decay"] = decay
    current["source_admiralty"] = admiralty
    base[dimension] = current

    _write_base_attributes(entity_path, text, base)

    return {
        "dimension": dimension,
        "type": "base",
        "old_value": old_value,
        "new_value": new_value,
        "delta": delta,
        "event": event_id,
    }


def _apply_skill_upgrade(entity_path: Path, skill_id: str, event_id: str) -> dict | None:
    text = read_text(entity_path)
    fm = parse_frontmatter(text)
    skills = fm.get("skills", [])
    if not isinstance(skills, list):
        skills = []

    existing = None
    for s in skills:
        if isinstance(s, dict) and s.get("id") == skill_id:
            existing = s
            break

    if existing:
        old_level = existing.get("level", 0)
        existing["level"] = old_level + 1
        leveled_by = existing.get("leveled_by", [])
        if isinstance(leveled_by, str):
            leveled_by = [leveled_by]
        if event_id not in leveled_by:
            leveled_by.append(event_id)
        existing["leveled_by"] = leveled_by
    else:
        skills.append({
            "id": skill_id,
            "level": 1,
            "prereq_met": True,
            "leveled_by": [event_id],
        })
        old_level = 0

    _write_skills(entity_path, text, skills)
    return {
        "dimension": skill_id,
        "type": "skill",
        "old_level": old_level,
        "new_level": (old_level + 1),
        "event": event_id,
    }


def _apply_state_change(entity_path: Path, rule: dict, event_id: str) -> dict | None:
    text = read_text(entity_path)
    fm = parse_frontmatter(text)
    states = fm.get("states", [])
    if not isinstance(states, list):
        states = []

    tag = rule.get("tag", "")
    duration = rule.get("duration_days", 7)
    expires = (dt.date.today() + dt.timedelta(days=duration)).isoformat()

    existing = None
    for s in states:
        if isinstance(s, dict) and s.get("tag") == tag:
            existing = s
            break

    if existing:
        on_repeat = rule.get("on_repeat", "solidify")
        if on_repeat == "solidify":
            existing["expires"] = "permanent"
            existing["on_repeat"] = "solidified"
        elif on_repeat == "extend":
            existing["expires"] = expires
        existing["source"] = event_id
        action = "repeated"
    else:
        states.append({
            "tag": tag,
            "kind": rule.get("kind", "debuff"),
            "expires": expires,
            "on_repeat": rule.get("on_repeat", "solidify"),
            "source": event_id,
        })
        action = "applied"

    _write_states(entity_path, text, states)

    for dim in rule.get("affects", []):
        delta = rule.get("delta", 0)
        if delta:
            _apply_base_attribute_patch(
                entity_path, dim, delta, event_id,
                "B3", 0.02,
            )

    return {
        "dimension": tag,
        "type": "state",
        "action": action,
        "kind": rule.get("kind", "debuff"),
        "expires": expires if action != "repeated" or rule.get("on_repeat") != "solidify" else "permanent",
        "event": event_id,
    }


def clean_expired_states(root: Path) -> list[dict]:
    """Remove expired buff/debuff states from all entities."""
    from .common import scan_entities
    cleaned = []
    today_date = dt.date.today()

    for eid, ref in scan_entities(root).items():
        if "archive" in ref.path.parts:
            continue
        text = read_text(ref.path)
        fm = parse_frontmatter(text)
        states = fm.get("states", [])
        if not isinstance(states, list) or not states:
            continue

        original_count = len(states)
        active = []
        for s in states:
            if not isinstance(s, dict):
                continue
            expires = s.get("expires", "")
            if expires == "permanent" or not expires:
                active.append(s)
                continue
            try:
                exp_date = dt.date.fromisoformat(str(expires))
                if exp_date > today_date:
                    active.append(s)
                else:
                    cleaned.append({"entity": eid, "tag": s.get("tag", ""), "expired": expires})
            except (ValueError, TypeError):
                active.append(s)

        if len(active) < original_count:
            _write_states(ref.path, text, active)

    return cleaned


# --- Write helpers (all attribute writes go through K7) ---

def _write_base_attributes(entity_path: Path, text: str, base: dict) -> None:
    from .common import write_frontmatter as wfm
    fm = parse_frontmatter(text)
    fm["base"] = base
    fm_end = text.find("\n---", 4)
    body = text[fm_end + 4:].strip() if fm_end != -1 else ""
    write_text(entity_path, wfm(fm, body))


def _write_skills(entity_path: Path, text: str, skills: list) -> None:
    fm = parse_frontmatter(text)
    fm["skills"] = skills
    fm_end = text.find("\n---", 4)
    body = text[fm_end + 4:].strip() if fm_end != -1 else ""
    from .common import write_frontmatter as wfm
    write_text(entity_path, wfm(fm, body))


def _write_states(entity_path: Path, text: str, states: list) -> None:
    fm = parse_frontmatter(text)
    fm["states"] = states
    fm_end = text.find("\n---", 4)
    body = text[fm_end + 4:].strip() if fm_end != -1 else ""
    from .common import write_frontmatter as wfm
    write_text(entity_path, wfm(fm, body))


# --- Helpers ---

def _normalize_claim(claim: dict, dimension: str) -> dict:
    return {
        "dimension": dimension,
        "type": "base",
        "value": claim.get("value"),
        "confidence": claim.get("confidence"),
        "provenance": claim.get("provenance", []),
        "reviewed": claim.get("reviewed"),
        "decay": claim.get("decay"),
        "source_admiralty": claim.get("source_admiralty"),
    }


def _extract_comparable_value(attr: dict) -> float | None:
    if attr.get("type") == "base":
        val = attr.get("value")
        return float(val) if val is not None else None
    if attr.get("type") == "skill":
        return float(attr.get("level", 0))
    return None
