#!/usr/bin/env python3
"""OpenTSC CLI v1.0 — Soul/Shell Architecture.

Local-first helper for the OpenTSC Claude Skill.
Supports both legacy (v0.4) and v1.0 vault layouts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# --- Legacy imports (backward compatible) ---
from opentsc_core.actions import accept_action, capture_actions, complete_action, list_actions, new_action, reject_action, stale_actions, suggest_actions, transition_action
from opentsc_core.calibration import accuracy, calibrate, due_predictions
from opentsc_core.conflicts import detect_conflicts, write_conflict_report
from opentsc_core.contacts import import_contacts_csv
from opentsc_core.entities import add_tag, archive_entity, list_tags, merge_entities, remove_tag, restore_entity, set_person_fields
from opentsc_core.filing import accept, file_audit, ingest, reject
from opentsc_core.query import query, who_can
from opentsc_core.relations import link, links
from opentsc_core.report import monthly_report, startup_brief
from opentsc_core.skills import init_skill_registry, list_skill_registry, recommend_skill
from opentsc_core.sources import create_source_package, list_sources, source_audit, source_derived, source_info
from opentsc_core.upgrade import naming_audit, upgrade
from opentsc_core.validate import validate_vault
from opentsc_core.vault import add_event, draft_inbox_event, init_vault, new_operation, new_org, new_person, stage_prediction, store_raw

# --- v1.0 imports ---
from opentsc_core.soul import (
    export_soul, import_soul, init_soul, propose_amendment,
    read_genesis, read_judgment_codex, read_rule_codex, write_genesis,
)
from opentsc_core.events import (
    append_event as v1_append_event, cause, derive_view,
    link_event, neighborhood, read_event, timeline,
)
from opentsc_core.judgment import (
    apply_decay, attribute, clean_expired_states, compare, explain, on_event,
)
from opentsc_core.world import (
    new_agent_npc, new_human_npc, new_operation as v1_new_operation,
    new_org as v1_new_org, new_player,
)
from opentsc_core.identity import confirm_alias, resolve, suggest_merges
from opentsc_core.professions import assign_profession, init_professions, list_professions, profession_gaps
from opentsc_core.genesis_engine import detect_gaps, register_module, spawn_draft, sunset_module, validate_draft
from opentsc_core.schema_mgr import known_fields, register_field, validate_schema
from opentsc_core.migrate import migrate_v04_to_v10


def ok(message: str) -> None:
    print(message)


def fail(exc: Exception) -> None:
    print(f"error: {exc}", file=sys.stderr)
    raise SystemExit(1)


def print_rows(rows: list[dict], as_json: bool = False) -> None:
    if as_json:
        ok(json.dumps(rows, ensure_ascii=False, indent=2))
    elif rows:
        for r in rows:
            ok(" · ".join(f"{k}:{v}" for k, v in r.items() if v != ""))
    else:
        ok("no results")


# ═══════════════════════════════════════
# Soul commands
# ═══════════════════════════════════════

def cmd_soul_init(args):
    created = init_soul(Path(args.root).resolve())
    ok(f"initialized soul: {Path(args.root).resolve() / 'soul'}")
    if created:
        ok("created:\n" + "\n".join(f"- {p}" for p in created))


def cmd_soul_export(args):
    target = export_soul(Path(args.root).resolve(), Path(args.target).resolve())
    ok(f"exported soul to: {target}")


def cmd_soul_import(args):
    imported = import_soul(Path(args.root).resolve(), Path(args.source).resolve())
    ok(f"imported {len(imported)} files from soul")


def cmd_soul_genesis(args):
    data = read_genesis(Path(args.root).resolve())
    ok(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def cmd_soul_codex(args):
    root = Path(args.root).resolve()
    if args.target == "judgment":
        data = read_judgment_codex(root)
        data.pop("_raw", None)
        ok(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    else:
        data = read_rule_codex(root)
        ok(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def cmd_soul_amend(args):
    path = propose_amendment(Path(args.root).resolve(), args.target, args.section, args.change, args.reason)
    ok(f"proposed amendment: {path}")


# ═══════════════════════════════════════
# World commands
# ═══════════════════════════════════════

def cmd_world_new_player(args):
    path = new_player(Path(args.root).resolve(), args.name, entity_id=args.id, aliases=args.alias or [], tags=args.tag or [])
    ok(f"created player: {path}")


def cmd_world_new_npc(args):
    root = Path(args.root).resolve()
    if args.type == "agent":
        path = new_agent_npc(root, args.name, entity_id=args.id, profession=args.profession, tags=args.tag or [])
    else:
        path = new_human_npc(root, args.name, entity_id=args.id, aliases=args.alias or [], tags=args.tag or [])
    ok(f"created {args.type} NPC: {path}")


def cmd_world_new_org(args):
    path = v1_new_org(Path(args.root).resolve(), args.name, entity_id=args.id, tags=args.tag or [])
    ok(f"created org: {path}")


def cmd_world_new_operation(args):
    path = v1_new_operation(Path(args.root).resolve(), args.title, deadline=args.deadline, entity_id=args.id)
    ok(f"created operation: {path}")


# ═══════════════════════════════════════
# Event commands (K3 event graph)
# ═══════════════════════════════════════

def cmd_event_add(args):
    event_id = v1_append_event(
        Path(args.root).resolve(), args.admiralty, args.content, args.source,
        links=args.link or [], date=args.date, raw_id=args.raw,
    )
    # Auto-trigger judgment engine
    patches = on_event(Path(args.root).resolve(), event_id)
    ok(f"created event: {event_id}")
    if patches:
        ok(f"judgment triggered {len(patches)} attribute patches:")
        for p in patches:
            ok(f"  {p.get('entity', '?')}.{p.get('dimension', '?')}: {p.get('type', '')} {'Lv.' + str(p.get('new_level', '')) if p.get('type') == 'skill' else str(p.get('old_value', '?')) + ' → ' + str(p.get('new_value', '?'))}")


def cmd_event_link(args):
    link_event(Path(args.root).resolve(), args.event_id, args.entity)
    ok(f"linked {args.event_id} → {args.entity}")


def cmd_event_cause(args):
    cause(Path(args.root).resolve(), args.from_event, args.to_event)
    ok(f"causal edge: {args.from_event} → {args.to_event}")


def cmd_event_read(args):
    evt = read_event(Path(args.root).resolve(), args.event_id)
    ok(json.dumps(evt, ensure_ascii=False, indent=2, default=str))


def cmd_event_timeline(args):
    events = timeline(Path(args.root).resolve(), entity=args.entity, since=args.since, until=args.until, limit=args.limit or 50)
    print_rows([{"id": e.get("id", ""), "date": e.get("date", ""), "admiralty": e.get("admiralty", ""), "content": e.get("content", "")[:100], "links": str(e.get("links", []))} for e in events], args.json)


def cmd_event_neighborhood(args):
    graph = neighborhood(Path(args.root).resolve(), args.entity_id)
    ok(json.dumps(graph, ensure_ascii=False, indent=2, default=str))


# ═══════════════════════════════════════
# Judgment commands (K7 judgment engine)
# ═══════════════════════════════════════

def cmd_judgment_attribute(args):
    attr = attribute(Path(args.root).resolve(), args.entity_id, args.dimension)
    ok(json.dumps(attr, ensure_ascii=False, indent=2, default=str))


def cmd_judgment_compare(args):
    result = compare(Path(args.root).resolve(), args.id_a, args.id_b, args.dimension)
    ok(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def cmd_judgment_explain(args):
    result = explain(Path(args.root).resolve(), args.entity_id, args.dimension)
    ok(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def cmd_judgment_decay(args):
    decayed = apply_decay(Path(args.root).resolve())
    ok(f"decayed {len(decayed)} attributes")
    for d in decayed:
        ok(f"  {d['entity']}.{d['dimension']}: {d['old_confidence']} → {d['new_confidence']}")


def cmd_judgment_clean_states(args):
    cleaned = clean_expired_states(Path(args.root).resolve())
    ok(f"cleaned {len(cleaned)} expired states")
    for c in cleaned:
        ok(f"  {c['entity']}: {c['tag']} (expired: {c['expired']})")


# ═══════════════════════════════════════
# Profession commands (M5)
# ═══════════════════════════════════════

def cmd_profession_list(args):
    profs = list_professions(Path(args.root).resolve())
    print_rows([{"profession": p.get("profession", ""), "display": p.get("display", ""), "vsm": p.get("vsm", ""), "holder_type": p.get("holder_type", ""), "model_tier": p.get("model_tier", "")} for p in profs], args.json)


def cmd_profession_gaps(args):
    gaps = profession_gaps(Path(args.root).resolve())
    print_rows(gaps, args.json)


def cmd_profession_assign(args):
    path = assign_profession(Path(args.root).resolve(), args.entity_id, args.profession)
    ok(f"assigned {args.profession} to {args.entity_id}: {path}")


def cmd_profession_init(args):
    created = init_professions(Path(args.root).resolve())
    ok(f"initialized {len(created)} profession files")
    for p in created:
        ok(f"  {p}")


# ═══════════════════════════════════════
# Genesis commands (K8 self-creation)
# ═══════════════════════════════════════

def cmd_genesis_detect_gaps(args):
    gaps = detect_gaps(Path(args.root).resolve())
    print_rows(gaps, args.json)


def cmd_genesis_spawn(args):
    gap = {"profession": args.profession, "display": args.display or args.profession, "vsm": args.vsm or "S1", "model_tier": args.model_tier or "mid", "holder_type": "agent"}
    path = spawn_draft(Path(args.root).resolve(), gap)
    ok(f"spawned draft: {path}")


def cmd_genesis_validate(args):
    result = validate_draft(Path(args.root).resolve(), args.draft_id)
    ok(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_genesis_register(args):
    path = register_module(Path(args.root).resolve(), args.draft_id)
    ok(f"registered module: {path}")


def cmd_genesis_sunset(args):
    sunset_module(Path(args.root).resolve(), args.module_name)
    ok(f"sunset module: {args.module_name}")


# ═══════════════════════════════════════
# Schema commands (K5)
# ═══════════════════════════════════════

def cmd_schema_list(args):
    fields = known_fields(Path(args.root).resolve())
    print_rows(fields, args.json)


def cmd_schema_register(args):
    register_field(Path(args.root).resolve(), args.field_name, args.field_type, args.description, layer=args.layer or "base")
    ok(f"registered field: {args.field_name}")


def cmd_schema_validate(args):
    issues = validate_schema(Path(args.root).resolve())
    if issues:
        for i in issues:
            ok(f"- {i}")
    else:
        ok("schema validation passed")


# ═══════════════════════════════════════
# Migration commands
# ═══════════════════════════════════════

def cmd_migrate(args):
    result = migrate_v04_to_v10(Path(args.root).resolve())
    ok(json.dumps({
        "moved_entities": len(result["moved_entities"]),
        "extracted_events": len(result["extracted_events"]),
        "created_dirs": len(result["created_dirs"]),
        "created_files": len(result["created_files"]),
        "warnings": result["warnings"],
    }, ensure_ascii=False, indent=2))


# ═══════════════════════════════════════
# Legacy commands (backward compatible)
# ═══════════════════════════════════════

def cmd_init(args):
    created = init_vault(Path(args.root).resolve())
    ok(f"initialized OpenTSC vault: {Path(args.root).resolve()}")
    if created:
        ok("created:\n" + "\n".join(f"- {p}" for p in created))


def cmd_upgrade(args):
    result = upgrade(Path(args.root).resolve())
    ok(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_naming_audit(args):
    issues = naming_audit(Path(args.root).resolve())
    if args.json:
        ok(json.dumps(issues, ensure_ascii=False, indent=2))
    elif issues:
        for issue in issues:
            ok(f"- {issue}")
    else:
        ok("naming audit passed")


def cmd_new_person(args):
    root = Path(args.root).resolve()
    from opentsc_core.common import is_v1_vault
    if is_v1_vault(root):
        path = new_human_npc(root, args.name, entity_id=args.id, aliases=args.alias or [], tags=args.tag or [])
    else:
        path = new_person(root, args.name, entity_id=args.id, aliases=args.alias or [], tags=args.tag or [])
        if args.skill or args.availability or args.reliability or args.cost_daily or args.project_rate or args.control_level:
            set_person_fields(root, args.id or path.stem, skills=args.skill or [], availability=args.availability, reliability=args.reliability, cost_daily=args.cost_daily, project_rate=args.project_rate, control_level=args.control_level)
    ok(f"created person: {path}")


def cmd_new_org(args):
    root = Path(args.root).resolve()
    from opentsc_core.common import is_v1_vault
    if is_v1_vault(root):
        ok(f"created org: {v1_new_org(root, args.name, entity_id=args.id, tags=args.tag or [])}")
    else:
        ok(f"created org: {new_org(root, args.name, entity_id=args.id, tags=args.tag or [])}")


def cmd_new_operation(args):
    root = Path(args.root).resolve()
    from opentsc_core.common import is_v1_vault
    if is_v1_vault(root):
        ok(f"created operation: {v1_new_operation(root, args.title, deadline=args.deadline, entity_id=args.id)}")
    else:
        ok(f"created operation: {new_operation(root, args.title, deadline=args.deadline, entity_id=args.id)}")


def cmd_person_set(args):
    path = set_person_fields(Path(args.root).resolve(), args.entity, skills=args.skill or [], availability=args.availability, reliability=args.reliability, cost_daily=args.cost_daily, project_rate=args.project_rate, control_level=args.control_level)
    ok(f"updated person: {path}")


def cmd_add_event(args):
    root = Path(args.root).resolve()
    from opentsc_core.common import is_v1_vault
    if is_v1_vault(root):
        event_id = v1_append_event(root, args.admiralty, args.content, args.source, links=[args.entity], date=args.date, raw_id=args.raw)
        patches = on_event(root, event_id)
        ok(f"created event: {event_id}")
        if patches:
            ok(f"judgment triggered {len(patches)} patches")
    else:
        ok(f"appended event: {add_event(root, args.entity, args.admiralty, args.content, args.source, date=args.date, raw_id=args.raw, status=args.status)}")


def cmd_store_raw(args):
    content = Path(args.file).read_text(encoding="utf-8", errors="replace") if args.file else sys.stdin.read()
    ok(f"stored raw material: {store_raw(Path(args.root).resolve(), args.title, content, args.source, material_type=args.material_type)}")


def cmd_draft_event(args):
    ok(f"created inbox draft: {draft_inbox_event(Path(args.root).resolve(), args.entity, args.admiralty, args.content, args.source, raw_id=args.raw)}")


def cmd_stage_prediction(args):
    ok(f"staged prediction: {stage_prediction(Path(args.root).resolve(), args.kind, args.context, args.claim, args.due, args.reason or [])}")


def cmd_import_contacts(args):
    ok(json.dumps(import_contacts_csv(Path(args.root).resolve(), Path(args.csv), name_col=args.name_col, phone_col=args.phone_col, email_col=args.email_col), ensure_ascii=False, indent=2))


def cmd_ingest(args):
    result = create_source_package(Path(args.root).resolve(), Path(args.path), material_type=args.type, source=args.source, source_date=args.source_date, title=args.title, move=args.move, extract=not args.no_extract)
    ok(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_accept(args):
    relation = tuple(args.relation) if args.relation else None
    path = accept(Path(args.root).resolve(), args.draft, entity=args.entity, admiralty=args.admiralty, content=args.content, source=args.source, relation=relation, knowledge_layer=args.knowledge_layer)
    ok(f"accepted and archived draft: {path}")


def cmd_reject(args):
    ok(f"rejected draft: {reject(Path(args.root).resolve(), args.draft, args.reason)}")


def cmd_file_audit(args):
    issues = file_audit(Path(args.root).resolve())
    if args.json:
        ok(json.dumps(issues, ensure_ascii=False, indent=2))
    elif issues:
        for issue in issues:
            ok(f"- {issue}")
    else:
        ok("file audit passed")


def cmd_sources(args):
    print_rows(list_sources(Path(args.root).resolve(), month=args.month, material_type=args.type), args.json)


def cmd_source(args):
    ok(json.dumps(source_info(Path(args.root).resolve(), args.raw_id), ensure_ascii=False, indent=2))


def cmd_source_derived(args):
    ok(json.dumps(source_derived(Path(args.root).resolve(), args.raw_id), ensure_ascii=False, indent=2))


def cmd_source_audit(args):
    issues = source_audit(Path(args.root).resolve())
    if args.json:
        ok(json.dumps(issues, ensure_ascii=False, indent=2))
    elif issues:
        for issue in issues:
            ok(f"- {issue}")
    else:
        ok("source audit passed")


def cmd_skill_registry(args):
    init_skill_registry(Path(args.root).resolve())
    ok(json.dumps(list_skill_registry(Path(args.root).resolve()), ensure_ascii=False, indent=2))


def cmd_skill_recommend(args):
    ok(json.dumps(recommend_skill(Path(args.root).resolve(), args.task), ensure_ascii=False, indent=2))


def cmd_query(args):
    print_rows(query(Path(args.root).resolve(), term=args.term, scope=args.scope, tag=args.tag, skill=args.skill, available=args.available, include_archive=args.include_archive), args.json)


def cmd_who_can(args):
    print_rows(who_can(Path(args.root).resolve(), args.skill, available_only=args.available), args.json)


def cmd_link(args):
    ok(json.dumps(link(Path(args.root).resolve(), args.source, args.type, args.target, since=args.since, source_note=args.evidence, confidence=args.confidence, status=args.status, introduced_by=args.introduced_by, emotion=args.emotion, notes=args.notes), ensure_ascii=False, indent=2))


def cmd_links(args):
    print_rows(links(Path(args.root).resolve(), entity=args.entity, rel_type=args.type), args.json)


def cmd_tag(args):
    ok(f"tagged: {add_tag(Path(args.root).resolve(), args.entity, args.tag)}")


def cmd_untag(args):
    ok(f"untagged: {remove_tag(Path(args.root).resolve(), args.entity, args.tag)}")


def cmd_tags(args):
    data = list_tags(Path(args.root).resolve(), filter_text=args.filter)
    if args.json:
        ok(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        for tag, entities in data.items():
            ok(f"{tag}: {', '.join(entities)}")


def cmd_archive(args):
    ok(f"archived: {archive_entity(Path(args.root).resolve(), args.entity, reason=args.reason)}")


def cmd_restore(args):
    ok(f"restored: {restore_entity(Path(args.root).resolve(), args.entity)}")


def cmd_merge(args):
    ok(f"merged into winner: {merge_entities(Path(args.root).resolve(), args.loser, args.winner, keep_alias=args.keep_alias)}")


def cmd_due(args):
    items = due_predictions(Path(args.root).resolve(), on_or_before=args.date)
    print_rows(items, args.json)


def cmd_calibrate(args):
    ok(f"calibrated: {calibrate(Path(args.root).resolve(), args.pred_id, args.result, note=args.note or '')}")


def cmd_accuracy(args):
    ok(json.dumps(accuracy(Path(args.root).resolve()), ensure_ascii=False, indent=2))


def cmd_conflicts(args):
    root = Path(args.root).resolve()
    report = write_conflict_report(root) if args.write_report else None
    rows = detect_conflicts(root)
    print_rows(rows, args.json)
    if report:
        ok(f"wrote conflict report: {report}")


def cmd_action_new(args):
    path = new_action(Path(args.root).resolve(), args.title, action_type=args.type, due=args.due, operation=args.operation, target=args.target or [], assignee=args.assignee, priority=args.priority, status=args.status, reasoning=args.reason or [], expected=args.expected or [], risk=args.risk or [])
    ok(f"created action: {path}")


def cmd_capture_actions(args):
    ok(f"captured action draft: {capture_actions(Path(args.root).resolve(), args.text, operation=args.operation, default_due=args.due)}")


def cmd_accept_action(args):
    paths = accept_action(Path(args.root).resolve(), args.draft, item=args.item, all_items=args.all, status=args.status)
    for path in paths:
        ok(f"accepted action: {path}")


def cmd_reject_action(args):
    ok(f"rejected action draft: {reject_action(Path(args.root).resolve(), args.draft, args.reason)}")


def cmd_actions(args):
    print_rows(list_actions(Path(args.root).resolve(), status=args.status, due=args.due, operation=args.operation, entity=args.entity), args.json)


def cmd_action_wait(args):
    ok(f"action waiting: {transition_action(Path(args.root).resolve(), args.action, 'waiting', note=args.reason or '')}")


def cmd_action_drop(args):
    ok(f"action dropped: {transition_action(Path(args.root).resolve(), args.action, 'dropped', note=args.reason or '')}")


def cmd_action_done(args):
    done, event = complete_action(Path(args.root).resolve(), args.action, note=args.note or '', create_event=not args.no_event, entity=args.entity)
    ok(f"action done: {done}")
    if event:
        ok(f"created candidate event: {event}")


def cmd_suggest_actions(args):
    ok(f"suggested action draft: {suggest_actions(Path(args.root).resolve(), goal=args.goal, operation=args.operation, entity=args.entity, gap=args.gap)}")


def cmd_report(args):
    ok(f"wrote monthly report: {monthly_report(Path(args.root).resolve(), ym=args.month)}")


def cmd_brief(args):
    ok(startup_brief(Path(args.root).resolve()))


def cmd_validate(args):
    errors = validate_vault(Path(args.root).resolve(), check_conflicts=args.check_conflicts, include_archive=args.include_archive)
    if errors:
        print("OpenTSC validation failed:")
        for err in errors:
            print(f"- {err}")
        raise SystemExit(1)
    ok(f"OpenTSC validation passed: {Path(args.root).resolve()}")


# ═══════════════════════════════════════
# v2.0 commands — memory index / text / emotion / config
# ═══════════════════════════════════════

def _load_index(args):
    from opentsc_core.index import ZvecIndex
    from opentsc_core.config import Config
    root = Path(args.root).resolve()
    return ZvecIndex(root, Config.load(root))


def cmd_index_build(args):
    idx = _load_index(args)
    if not idx.available():
        fail(RuntimeError("zvec not installed — run `pip install zvec`"))
    ok(json.dumps({"built": idx.build()}, ensure_ascii=False, indent=2))


def cmd_index_sync(args):
    idx = _load_index(args)
    if not idx.available():
        fail(RuntimeError("zvec not installed — run `pip install zvec`"))
    ok(json.dumps(idx.sync(), ensure_ascii=False, indent=2))


def cmd_index_search(args):
    rows = _load_index(args).search(args.query, kind=args.kind, entity_id=args.entity, topk=args.topk)
    print_rows(rows, getattr(args, "json", False))


def cmd_identity_resolve(args):
    rows = _load_index(args).resolve_identity(args.name, topk=args.topk)
    print_rows(rows, getattr(args, "json", False))


def cmd_index_stats(args):
    ok(json.dumps(_load_index(args).stats(), ensure_ascii=False, indent=2))


def cmd_emotion_score(args):
    from opentsc_core.emotion import get_emotion_backend
    from opentsc_core.config import Config
    root = Path(args.root).resolve()
    ok(json.dumps(get_emotion_backend(Config.load(root)).score(args.text).as_dict(), ensure_ascii=False, indent=2))


def cmd_text_segment(args):
    from opentsc_core import text
    result = text.keywords(args.text, args.topk) if args.keywords else text.segment(args.text)
    ok(json.dumps(result, ensure_ascii=False))


def cmd_config_show(args):
    from opentsc_core.config import Config
    from dataclasses import asdict
    ok(json.dumps(asdict(Config.load(Path(args.root).resolve())), ensure_ascii=False, indent=2))


def cmd_actions_stale(args):
    rows = stale_actions(Path(args.root).resolve(), days=args.days, status=args.status)
    print_rows(rows, getattr(args, "json", False))


# ═══════════════════════════════════════
# Parser
# ═══════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenTSC v1.0 CLI — Soul/Shell Architecture")
    parser.add_argument("--root", default="opentsc", help="OpenTSC vault root, default: ./opentsc")
    sub = parser.add_subparsers(dest="command", required=True)

    # --- Init / Upgrade / Validate ---
    sub.add_parser("init").set_defaults(func=cmd_init)
    sub.add_parser("upgrade").set_defaults(func=cmd_upgrade)
    p = sub.add_parser("naming-audit"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_naming_audit)
    p = sub.add_parser("validate"); p.add_argument("--check-conflicts", action="store_true"); p.add_argument("--include-archive", action="store_true"); p.set_defaults(func=cmd_validate)

    # --- Soul commands ---
    sub.add_parser("soul-init").set_defaults(func=cmd_soul_init)
    p = sub.add_parser("soul-export"); p.add_argument("target"); p.set_defaults(func=cmd_soul_export)
    p = sub.add_parser("soul-import"); p.add_argument("source"); p.set_defaults(func=cmd_soul_import)
    sub.add_parser("soul-genesis").set_defaults(func=cmd_soul_genesis)
    p = sub.add_parser("soul-codex"); p.add_argument("target", choices=["judgment", "rule"]); p.set_defaults(func=cmd_soul_codex)
    p = sub.add_parser("soul-amend"); p.add_argument("target", choices=["judgment", "rule"]); p.add_argument("section"); p.add_argument("change"); p.add_argument("--reason", required=True); p.set_defaults(func=cmd_soul_amend)

    # --- World commands ---
    p = sub.add_parser("world-new-player"); p.add_argument("name"); p.add_argument("--id"); p.add_argument("--alias", action="append"); p.add_argument("--tag", action="append"); p.set_defaults(func=cmd_world_new_player)
    p = sub.add_parser("world-new-npc"); p.add_argument("name"); p.add_argument("--id"); p.add_argument("--type", default="human", choices=["human", "agent"]); p.add_argument("--alias", action="append"); p.add_argument("--tag", action="append"); p.add_argument("--profession"); p.set_defaults(func=cmd_world_new_npc)
    p = sub.add_parser("world-new-org"); p.add_argument("name"); p.add_argument("--id"); p.add_argument("--tag", action="append"); p.set_defaults(func=cmd_world_new_org)
    p = sub.add_parser("world-new-operation"); p.add_argument("title"); p.add_argument("--deadline"); p.add_argument("--id"); p.set_defaults(func=cmd_world_new_operation)

    # --- Event commands ---
    p = sub.add_parser("event-add"); p.add_argument("admiralty"); p.add_argument("content"); p.add_argument("source"); p.add_argument("--link", action="append"); p.add_argument("--date"); p.add_argument("--raw"); p.set_defaults(func=cmd_event_add)
    p = sub.add_parser("event-link"); p.add_argument("event_id"); p.add_argument("entity", nargs="+"); p.set_defaults(func=cmd_event_link)
    p = sub.add_parser("event-cause"); p.add_argument("from_event"); p.add_argument("to_event"); p.set_defaults(func=cmd_event_cause)
    p = sub.add_parser("event-read"); p.add_argument("event_id"); p.set_defaults(func=cmd_event_read)
    p = sub.add_parser("event-timeline"); p.add_argument("--entity"); p.add_argument("--since"); p.add_argument("--until"); p.add_argument("--limit", type=int, default=50); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_event_timeline)
    p = sub.add_parser("event-neighborhood"); p.add_argument("entity_id"); p.set_defaults(func=cmd_event_neighborhood)

    # --- Judgment commands ---
    p = sub.add_parser("judgment-attribute"); p.add_argument("entity_id"); p.add_argument("dimension"); p.set_defaults(func=cmd_judgment_attribute)
    p = sub.add_parser("judgment-compare"); p.add_argument("id_a"); p.add_argument("id_b"); p.add_argument("dimension"); p.set_defaults(func=cmd_judgment_compare)
    p = sub.add_parser("judgment-explain"); p.add_argument("entity_id"); p.add_argument("dimension"); p.set_defaults(func=cmd_judgment_explain)
    sub.add_parser("judgment-decay").set_defaults(func=cmd_judgment_decay)
    sub.add_parser("judgment-clean-states").set_defaults(func=cmd_judgment_clean_states)

    # --- Profession commands ---
    p = sub.add_parser("profession-list"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_profession_list)
    p = sub.add_parser("profession-gaps"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_profession_gaps)
    p = sub.add_parser("profession-assign"); p.add_argument("entity_id"); p.add_argument("profession"); p.set_defaults(func=cmd_profession_assign)
    sub.add_parser("profession-init").set_defaults(func=cmd_profession_init)

    # --- Genesis commands ---
    p = sub.add_parser("genesis-detect-gaps"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_genesis_detect_gaps)
    p = sub.add_parser("genesis-spawn"); p.add_argument("profession"); p.add_argument("--display"); p.add_argument("--vsm"); p.add_argument("--model-tier"); p.set_defaults(func=cmd_genesis_spawn)
    p = sub.add_parser("genesis-validate"); p.add_argument("draft_id"); p.set_defaults(func=cmd_genesis_validate)
    p = sub.add_parser("genesis-register"); p.add_argument("draft_id"); p.set_defaults(func=cmd_genesis_register)
    p = sub.add_parser("genesis-sunset"); p.add_argument("module_name"); p.set_defaults(func=cmd_genesis_sunset)

    # --- Schema commands ---
    p = sub.add_parser("schema-list"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_schema_list)
    p = sub.add_parser("schema-register"); p.add_argument("field_name"); p.add_argument("field_type"); p.add_argument("description"); p.add_argument("--layer", default="base"); p.set_defaults(func=cmd_schema_register)
    sub.add_parser("schema-validate").set_defaults(func=cmd_schema_validate)

    # --- Migration ---
    sub.add_parser("migrate").set_defaults(func=cmd_migrate)

    # --- Legacy commands (full backward compat) ---
    p = sub.add_parser("new-person")
    p.add_argument("name"); p.add_argument("--id"); p.add_argument("--alias", action="append"); p.add_argument("--tag", action="append"); p.add_argument("--skill", action="append"); p.add_argument("--availability"); p.add_argument("--reliability"); p.add_argument("--cost-daily"); p.add_argument("--project-rate"); p.add_argument("--control-level"); p.set_defaults(func=cmd_new_person)
    p = sub.add_parser("person-set")
    p.add_argument("entity"); p.add_argument("--skill", action="append"); p.add_argument("--availability"); p.add_argument("--reliability"); p.add_argument("--cost-daily"); p.add_argument("--project-rate"); p.add_argument("--control-level"); p.set_defaults(func=cmd_person_set)
    p = sub.add_parser("new-org"); p.add_argument("name"); p.add_argument("--id"); p.add_argument("--tag", action="append"); p.set_defaults(func=cmd_new_org)
    p = sub.add_parser("new-operation"); p.add_argument("title"); p.add_argument("--deadline"); p.add_argument("--id"); p.set_defaults(func=cmd_new_operation)

    p = sub.add_parser("add-event"); p.add_argument("entity"); p.add_argument("admiralty"); p.add_argument("content"); p.add_argument("source"); p.add_argument("--date"); p.add_argument("--raw"); p.add_argument("--status", default="active"); p.set_defaults(func=cmd_add_event)
    p = sub.add_parser("store-raw"); p.add_argument("title"); p.add_argument("source"); p.add_argument("--file"); p.add_argument("--material-type", default="note"); p.set_defaults(func=cmd_store_raw)
    p = sub.add_parser("draft-event"); p.add_argument("entity"); p.add_argument("admiralty"); p.add_argument("content"); p.add_argument("source"); p.add_argument("--raw"); p.set_defaults(func=cmd_draft_event)
    p = sub.add_parser("stage-prediction"); p.add_argument("kind"); p.add_argument("context"); p.add_argument("claim"); p.add_argument("due"); p.add_argument("--reason", action="append"); p.set_defaults(func=cmd_stage_prediction)

    p = sub.add_parser("query"); p.add_argument("term", nargs="?"); p.add_argument("--scope"); p.add_argument("--tag"); p.add_argument("--skill"); p.add_argument("--available", action="store_true"); p.add_argument("--include-archive", action="store_true"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_query)
    p = sub.add_parser("who-can"); p.add_argument("skill"); p.add_argument("--available", action="store_true"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_who_can)
    p = sub.add_parser("link"); p.add_argument("source"); p.add_argument("type"); p.add_argument("target"); p.add_argument("--since"); p.add_argument("--evidence", default="user"); p.add_argument("--confidence", default="medium"); p.add_argument("--status", default="current"); p.add_argument("--introduced-by"); p.add_argument("--emotion"); p.add_argument("--notes"); p.set_defaults(func=cmd_link)
    p = sub.add_parser("links"); p.add_argument("entity", nargs="?"); p.add_argument("--type"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_links)
    p = sub.add_parser("tag"); p.add_argument("entity"); p.add_argument("tag"); p.set_defaults(func=cmd_tag)
    p = sub.add_parser("untag"); p.add_argument("entity"); p.add_argument("tag"); p.set_defaults(func=cmd_untag)
    p = sub.add_parser("tags"); p.add_argument("--filter"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_tags)
    p = sub.add_parser("archive"); p.add_argument("entity"); p.add_argument("--reason", default="user_archived"); p.set_defaults(func=cmd_archive)
    p = sub.add_parser("restore"); p.add_argument("entity"); p.set_defaults(func=cmd_restore)
    p = sub.add_parser("merge"); p.add_argument("loser"); p.add_argument("into"); p.add_argument("winner"); p.add_argument("--keep-alias"); p.set_defaults(func=cmd_merge)

    p = sub.add_parser("import-contacts"); p.add_argument("csv"); p.add_argument("--name-col", default="name"); p.add_argument("--phone-col", default="phone"); p.add_argument("--email-col", default="email"); p.set_defaults(func=cmd_import_contacts)
    p = sub.add_parser("ingest"); p.add_argument("path"); p.add_argument("--type", default="battle_report"); p.add_argument("--source", default="user"); p.add_argument("--source-date"); p.add_argument("--title"); p.add_argument("--move", action="store_true"); p.add_argument("--no-extract", action="store_true"); p.set_defaults(func=cmd_ingest)
    p = sub.add_parser("accept"); p.add_argument("draft"); p.add_argument("--entity"); p.add_argument("--admiralty", default="B6"); p.add_argument("--content"); p.add_argument("--source"); p.add_argument("--relation", nargs=3, metavar=("SOURCE", "TYPE", "TARGET")); p.add_argument("--knowledge-layer", choices=["facts", "methods", "principles"]); p.set_defaults(func=cmd_accept)
    p = sub.add_parser("reject"); p.add_argument("draft"); p.add_argument("--reason", required=True); p.set_defaults(func=cmd_reject)
    p = sub.add_parser("file-audit"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_file_audit)
    p = sub.add_parser("sources"); p.add_argument("--month"); p.add_argument("--type"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_sources)
    p = sub.add_parser("source"); p.add_argument("raw_id"); p.set_defaults(func=cmd_source)
    p = sub.add_parser("source-derived"); p.add_argument("raw_id"); p.set_defaults(func=cmd_source_derived)
    p = sub.add_parser("source-audit"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_source_audit)
    p = sub.add_parser("skill-registry"); p.set_defaults(func=cmd_skill_registry)
    p = sub.add_parser("skill-recommend"); p.add_argument("task"); p.set_defaults(func=cmd_skill_recommend)
    p = sub.add_parser("due"); p.add_argument("--date"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_due)
    p = sub.add_parser("calibrate"); p.add_argument("pred_id"); p.add_argument("--result", required=True, choices=["correct", "wrong", "partial"]); p.add_argument("--note"); p.set_defaults(func=cmd_calibrate)
    sub.add_parser("accuracy").set_defaults(func=cmd_accuracy)
    p = sub.add_parser("conflicts"); p.add_argument("--write-report", action="store_true"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_conflicts)
    p = sub.add_parser("action-new"); p.add_argument("title"); p.add_argument("--type", default="custom"); p.add_argument("--due"); p.add_argument("--operation"); p.add_argument("--target", action="append"); p.add_argument("--assignee"); p.add_argument("--priority", default="medium"); p.add_argument("--status", default="active"); p.add_argument("--reason", action="append"); p.add_argument("--expected", action="append"); p.add_argument("--risk", action="append"); p.set_defaults(func=cmd_action_new)
    p = sub.add_parser("capture-actions"); p.add_argument("text"); p.add_argument("--operation"); p.add_argument("--due"); p.set_defaults(func=cmd_capture_actions)
    p = sub.add_parser("accept-action"); p.add_argument("draft"); p.add_argument("--item", type=int); p.add_argument("--all", action="store_true"); p.add_argument("--status", default="active"); p.set_defaults(func=cmd_accept_action)
    p = sub.add_parser("reject-action"); p.add_argument("draft"); p.add_argument("--reason", required=True); p.set_defaults(func=cmd_reject_action)
    p = sub.add_parser("actions"); p.add_argument("--status"); p.add_argument("--due"); p.add_argument("--operation"); p.add_argument("--entity"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_actions)
    p = sub.add_parser("action-wait"); p.add_argument("action"); p.add_argument("--reason"); p.set_defaults(func=cmd_action_wait)
    p = sub.add_parser("action-drop"); p.add_argument("action"); p.add_argument("--reason"); p.set_defaults(func=cmd_action_drop)
    p = sub.add_parser("action-done"); p.add_argument("action"); p.add_argument("--note"); p.add_argument("--entity"); p.add_argument("--no-event", action="store_true"); p.set_defaults(func=cmd_action_done)
    p = sub.add_parser("suggest-actions"); p.add_argument("--goal"); p.add_argument("--operation"); p.add_argument("--entity"); p.add_argument("--gap"); p.set_defaults(func=cmd_suggest_actions)
    p = sub.add_parser("report-monthly"); p.add_argument("--month"); p.set_defaults(func=cmd_report)
    sub.add_parser("brief").set_defaults(func=cmd_brief)

    # --- v2.0 memory index / text / emotion / config ---
    sub.add_parser("index-build").set_defaults(func=cmd_index_build)
    sub.add_parser("index-sync").set_defaults(func=cmd_index_sync)
    p = sub.add_parser("index-search"); p.add_argument("query"); p.add_argument("--kind"); p.add_argument("--entity"); p.add_argument("--topk", type=int, default=10); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_index_search)
    p = sub.add_parser("identity-resolve"); p.add_argument("name"); p.add_argument("--topk", type=int, default=5); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_identity_resolve)
    sub.add_parser("index-stats").set_defaults(func=cmd_index_stats)
    p = sub.add_parser("emotion-score"); p.add_argument("text"); p.set_defaults(func=cmd_emotion_score)
    p = sub.add_parser("text-segment"); p.add_argument("text"); p.add_argument("--keywords", action="store_true"); p.add_argument("--topk", type=int, default=8); p.set_defaults(func=cmd_text_segment)
    sub.add_parser("config-show").set_defaults(func=cmd_config_show)
    p = sub.add_parser("actions-stale"); p.add_argument("--days", type=int, default=30); p.add_argument("--status", default="active"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_actions_stale)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except Exception as exc:
        fail(exc)


if __name__ == "__main__":
    main()
