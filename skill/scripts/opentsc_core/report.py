"""Report generation — monthly reports and startup briefing.

Briefing must include at least one uncomfortable item when present (Law 8).
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from .actions import due_actions
from .calibration import due_predictions
from .common import is_v1_vault, month, parse_frontmatter, read_text, soul_path, today, world_path, write_text

EVENT_LINE_RE = re.compile(r"^-\s*(\d{4}-\d{2}-\d{2})\s*·\s*([A-F][1-6])\s*·\s*(.+?)\s*·〔来源:\s*(.+?)〕")


def monthly_report(root: Path, ym: str | None = None) -> Path:
    ym = ym or month()
    target = root / "reports" / ym / "monthly.md"
    events = _events_for_month(root, ym)
    due = due_predictions(root)
    uncomfortable = _find_uncomfortable_items(root)
    expired_states = _find_expired_states(root) if is_v1_vault(root) else []

    body = [
        f"---\ntype: monthly_report\nmonth: {ym}\ncreated: {today()}\n---\n",
        f"# OpenTSC Monthly Report · {ym}\n",
        "## Executive signals\n",
        "- TODO(user): highest-signal change\n",
        "## New / notable events\n",
    ]

    if is_v1_vault(root):
        # Read from event graph
        v1_events = _v1_events_for_month(root, ym)
        if v1_events:
            for evt in v1_events[:100]:
                body.append(f"- `{','.join(evt.get('links', []))}` · {evt.get('date', '')} · {evt.get('admiralty', '')} · {evt.get('content', '')[:120]} · source:{evt.get('source', '')}\n")
        elif events:
            for event in events[:100]:
                body.append(f"- `{event['entity']}` · {event['date']} · {event['rating']} · {event['content']} · source:{event['source']}\n")
        else:
            body.append("- No events for this month.\n")
    else:
        if events:
            for event in events[:100]:
                body.append(f"- `{event['entity']}` · {event['date']} · {event['rating']} · {event['content']} · source:{event['source']}\n")
        else:
            body.append("- No indexed events for this month.\n")

    body.extend(["\n## Due calibration items\n"])
    if due:
        for item in due:
            body.append(f"- {item['due']} · {item['id']} · {item['context']} · {item['path']}\n")
    else:
        body.append("- None.\n")

    # Uncomfortable items (Law 8: must not be suppressed)
    body.extend(["\n## Contradictions / uncomfortable items\n"])
    if uncomfortable:
        for item in uncomfortable:
            body.append(f"- {item}\n")
    else:
        body.append("- TODO(user/agent): stalled operations, contradictions, or evidence against prior beliefs.\n")

    if expired_states:
        body.extend(["\n## Expired states (buff/debuff)\n"])
        for state in expired_states:
            body.append(f"- {state}\n")

    body.extend([
        "\n## Candidate knowledge to confirm\n",
        "- TODO(user/agent): candidate granules with sample size and source events.\n",
    ])

    if is_v1_vault(root):
        body.extend([
            "\n## Judgment calibration\n",
            "- TODO(agent): dimensions with low hit rate needing codex amendment.\n",
        ])

    write_text(target, "".join(body))
    return target


def startup_brief(root: Path) -> str:
    """Generate startup brief. Must include uncomfortable items (Law 8)."""
    due = due_predictions(root)
    action_due = due_actions(root)
    blocked_ops = _operations_with_status(root, "blocked")
    uncomfortable = _find_uncomfortable_items(root)

    lines = [f"# OpenTSC Startup Brief · {today()}", ""]

    lines.append("## Due predictions")
    if due:
        for item in due[:10]:
            lines.append(f"- {item['due']} · {item['id']} · {item['context']} · {item['path']}")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## Follow-up actions due")
    if action_due:
        for item in action_due[:15]:
            lines.append(f"- {item['due']} · {item['id']} · {item['title']} · {item['path']}")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## Blocked / uncomfortable items")
    if blocked_ops:
        for item in blocked_ops[:10]:
            lines.append(f"- [blocked operation] {item}")
    if uncomfortable:
        for item in uncomfortable[:10]:
            lines.append(f"- [uncomfortable] {item}")
    if not blocked_ops and not uncomfortable:
        lines.append("- None detected by static scan")
    lines.append("")

    if is_v1_vault(root):
        lines.append("## Attribute decay warnings")
        stale = _find_stale_attributes(root)
        if stale:
            for item in stale[:10]:
                lines.append(f"- {item}")
        else:
            lines.append("- No stale attributes detected")
        lines.append("")

        lines.append("## Active debuffs")
        debuffs = _find_active_debuffs(root)
        if debuffs:
            for item in debuffs[:10]:
                lines.append(f"- {item}")
        else:
            lines.append("- None")
        lines.append("")

        lines.append("## Profession gaps")
        try:
            from .professions import profession_gaps
            gaps = profession_gaps(root)
            if gaps:
                for gap in gaps[:10]:
                    lines.append(f"- {gap['display']} ({gap['vsm']}) — {gap['holder_type']}")
            else:
                lines.append("- All VSM professions assigned")
        except Exception:
            lines.append("- (unable to check)")
        lines.append("")

    return "\n".join(lines) + "\n"


# --- Event collection ---

def _events_for_month(root: Path, ym: str) -> list[dict[str, str]]:
    """Collect events from legacy inline timelines."""
    events: list[dict[str, str]] = []
    for folder in [root / "people", root / "orgs", root / "operations",
                   world_path(root) / "npcs" / "humans", world_path(root) / "npcs" / "agents",
                   world_path(root) / "players", world_path(root) / "orgs",
                   world_path(root) / "operations"]:
        if not folder.exists():
            continue
        for path in folder.glob("**/*.md"):
            text = read_text(path)
            entity = _entity_id(text) or path.stem
            for line in text.splitlines():
                match = EVENT_LINE_RE.match(line.strip())
                if match and match.group(1).startswith(ym):
                    events.append({"entity": entity, "date": match.group(1), "rating": match.group(2), "content": match.group(3), "source": match.group(4), "path": str(path)})
    return sorted(events, key=lambda e: (e["date"], e["entity"]))


def _v1_events_for_month(root: Path, ym: str) -> list[dict]:
    """Collect events from soul/events/ graph."""
    events_dir = soul_path(root) / "events" / ym
    if not events_dir.exists():
        return []
    results = []
    for path in events_dir.glob("evt_*.md"):
        text = read_text(path)
        fm = parse_frontmatter(text)
        fm_end = text.find("\n---", 4)
        content = text[fm_end + 4:].strip() if fm_end != -1 else ""
        fm["content"] = content
        results.append(fm)
    return sorted(results, key=lambda e: (e.get("date", ""), e.get("id", "")))


# --- Uncomfortable items detection (Law 8) ---

def _find_uncomfortable_items(root: Path) -> list[str]:
    """Find items that might be uncomfortable but must not be suppressed."""
    items = []

    # Overdue actions
    try:
        from .actions import list_actions
        overdue = list_actions(root, status="active", due="today")
        for a in overdue[:5]:
            if a.get("due") and not a["due"].startswith("TODO"):
                items.append(f"Overdue action: {a.get('title', a.get('id', '?'))} (due: {a['due']})")
    except Exception:
        pass

    # Stalled operations
    stalled = _operations_with_status(root, "blocked") + _operations_with_status(root, "draft")
    for op in stalled[:5]:
        items.append(f"Stalled operation: {op}")

    # Debuffs on key people
    if is_v1_vault(root):
        debuffs = _find_active_debuffs(root)
        for d in debuffs[:3]:
            items.append(f"Active debuff: {d}")

    # Unconfirmed inbox items older than 3 days
    inbox = root / "inbox"
    if inbox.exists():
        today_date = dt.date.today()
        for path in inbox.rglob("draft_*.md"):
            try:
                stat = path.stat()
                age = (today_date - dt.date.fromtimestamp(stat.st_mtime)).days
                if age > 3:
                    items.append(f"Stale inbox draft ({age}d old): {path.name}")
            except Exception:
                pass

    return items


def _find_stale_attributes(root: Path) -> list[str]:
    """Find attributes that haven't been reviewed recently."""
    stale = []
    from .common import scan_entities
    today_date = dt.date.today()
    for eid, ref in scan_entities(root).items():
        if "archive" in ref.path.parts:
            continue
        text = read_text(ref.path)
        fm = parse_frontmatter(text)
        base = fm.get("base", {})
        if not isinstance(base, dict):
            continue
        for dim, claim in base.items():
            if not isinstance(claim, dict):
                continue
            reviewed = claim.get("reviewed")
            confidence = claim.get("confidence", 0.5)
            if reviewed and reviewed != "null" and isinstance(confidence, (int, float)) and confidence < 0.3:
                stale.append(f"{eid}.{dim}: confidence={confidence} (reviewed: {reviewed})")
    return stale


def _find_active_debuffs(root: Path) -> list[str]:
    """Find active debuff states across all entities."""
    debuffs = []
    from .common import scan_entities
    for eid, ref in scan_entities(root).items():
        if "archive" in ref.path.parts:
            continue
        text = read_text(ref.path)
        fm = parse_frontmatter(text)
        states = fm.get("states", [])
        if not isinstance(states, list):
            continue
        for s in states:
            if isinstance(s, dict) and s.get("kind") == "debuff":
                expires = s.get("expires", "")
                tag = s.get("tag", "?")
                debuffs.append(f"{eid}: {tag} (expires: {expires})")
    return debuffs


def _find_expired_states(root: Path) -> list[str]:
    """Find states that have expired and should be cleaned."""
    expired = []
    from .common import scan_entities
    today_date = dt.date.today()
    for eid, ref in scan_entities(root).items():
        if "archive" in ref.path.parts:
            continue
        text = read_text(ref.path)
        fm = parse_frontmatter(text)
        states = fm.get("states", [])
        if not isinstance(states, list):
            continue
        for s in states:
            if isinstance(s, dict):
                exp = s.get("expires", "")
                if exp and exp != "permanent":
                    try:
                        if dt.date.fromisoformat(str(exp)) <= today_date:
                            expired.append(f"{eid}: {s.get('tag', '?')} expired on {exp}")
                    except (ValueError, TypeError):
                        pass
    return expired


# --- Helpers ---

def _entity_id(text: str) -> str | None:
    match = re.search(r"^id:\s*([\w-]+)", text, re.MULTILINE)
    return match.group(1) if match else None


def _operations_with_status(root: Path, status: str) -> list[str]:
    out: list[str] = []
    for ops_dir in [root / "operations", world_path(root) / "operations"]:
        if not ops_dir.exists():
            continue
        for path in ops_dir.glob("**/*.md"):
            text = read_text(path)
            if re.search(rf"^status:\s*{re.escape(status)}\s*$", text, re.MULTILINE):
                out.append(str(path))
    return out
