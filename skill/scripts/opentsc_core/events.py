"""K3 Event Stream Engine — event graph with nodes, links, causes, and neighborhood queries.

Each event is an independent node in soul/events/YYYY-MM/evt_*.md.
Events link to entities and to each other via causal edges.
A reverse index maps entity_id → [event_ids] for O(1) lookups.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .common import (
    month,
    now_iso,
    parse_frontmatter,
    read_text,
    require_admiralty,
    soul_path,
    stable_suffix,
    today,
    write_frontmatter,
    write_text,
)


def append_event(
    root: Path,
    admiralty: str,
    content: str,
    source: str,
    links: list[str] | None = None,
    date: str | None = None,
    raw_id: str | None = None,
    caused_by: list[str] | None = None,
    status: str = "active",
) -> str:
    """Create a new event node and update the reverse index."""
    require_admiralty(admiralty)
    event_date = date or today()
    ym = event_date[:7]
    event_id = f"evt_{event_date.replace('-', '')}_{stable_suffix(content + source + now_iso(), 8)}"

    event_dir = soul_path(root) / "events" / ym
    event_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "id": event_id,
        "date": event_date,
        "admiralty": admiralty,
        "source": source,
        "raw": raw_id or "",
        "status": status,
        "links": links or [],
        "caused_by": caused_by or [],
        "causes": [],
        "judgment_triggered": [],
    }
    body = content
    event_path = event_dir / f"{event_id}.md"
    write_text(event_path, write_frontmatter(data, body))

    _update_index(root, event_id, links or [])

    return event_id


def link_event(root: Path, event_id: str, targets: list[str]) -> None:
    """Link an existing event to additional entities."""
    path = _find_event(root, event_id)
    text = read_text(path)
    fm = parse_frontmatter(text)
    existing = fm.get("links", [])
    if isinstance(existing, str):
        existing = [existing]
    merged = list(dict.fromkeys(existing + targets))
    text = re.sub(
        r"^links:\s*\[.*?\]\s*$",
        f"links: [{', '.join(merged)}]",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    write_text(path, text)
    _update_index(root, event_id, targets)


def cause(root: Path, from_event: str, to_event: str) -> None:
    """Add a causal edge from one event to another."""
    from_path = _find_event(root, from_event)
    to_path = _find_event(root, to_event)

    _append_to_list_field(from_path, "causes", to_event)
    _append_to_list_field(to_path, "caused_by", from_event)


def mark_judgment_triggered(root: Path, event_id: str, patches: list[str]) -> None:
    """Record which attribute patches were triggered by this event."""
    path = _find_event(root, event_id)
    for patch in patches:
        _append_to_list_field(path, "judgment_triggered", patch)


def read_event(root: Path, event_id: str) -> dict:
    """Read a single event as a dict with frontmatter + content."""
    path = _find_event(root, event_id)
    text = read_text(path)
    data = parse_frontmatter(text)
    fm_end = text.find("\n---", 4)
    if fm_end != -1:
        body = text[fm_end + 4:].strip()
    else:
        body = ""
    data["content"] = body
    data["_path"] = str(path)
    return data


def timeline(
    root: Path,
    entity: str | None = None,
    since: str | None = None,
    until: str | None = None,
    admiralty_min: str | None = None,
    status: str = "active",
    limit: int = 200,
) -> list[dict]:
    """Query events with filters. Returns list of event dicts sorted by date."""
    events = []
    if entity:
        event_ids = _index_lookup(root, entity)
        for eid in event_ids:
            try:
                evt = read_event(root, eid)
                events.append(evt)
            except FileNotFoundError:
                continue
    else:
        events_dir = soul_path(root) / "events"
        if events_dir.exists():
            for path in events_dir.rglob("evt_*.md"):
                text = read_text(path)
                evt = parse_frontmatter(text)
                fm_end = text.find("\n---", 4)
                evt["content"] = text[fm_end + 4:].strip() if fm_end != -1 else ""
                evt["_path"] = str(path)
                events.append(evt)

    if since:
        events = [e for e in events if e.get("date", "") >= since]
    if until:
        events = [e for e in events if e.get("date", "") <= until]
    if status:
        events = [e for e in events if e.get("status", "active") == status]
    if admiralty_min:
        events = [e for e in events if _admiralty_gte(e.get("admiralty", "F6"), admiralty_min)]

    events.sort(key=lambda e: (e.get("date", ""), e.get("id", "")))
    return events[:limit]


def neighborhood(root: Path, entity_id: str) -> dict:
    """Pull all events connected to an entity and their causal network."""
    event_ids = _index_lookup(root, entity_id)
    events = []
    causal_edges = []
    visited = set()

    def _collect(eid: str, depth: int = 0) -> None:
        if eid in visited or depth > 5:
            return
        visited.add(eid)
        try:
            evt = read_event(root, eid)
        except FileNotFoundError:
            return
        events.append(evt)
        for cause_id in evt.get("causes", []):
            causal_edges.append({"from": eid, "to": cause_id})
            _collect(cause_id, depth + 1)
        for caused_by_id in evt.get("caused_by", []):
            causal_edges.append({"from": caused_by_id, "to": eid})
            _collect(caused_by_id, depth + 1)

    for eid in event_ids:
        _collect(eid)

    return {
        "entity": entity_id,
        "events": sorted(events, key=lambda e: e.get("date", "")),
        "causal_edges": causal_edges,
        "event_count": len(events),
    }


def derive_view(root: Path, entity_id: str) -> dict:
    """Compute current state from event stream for an entity (Law 4)."""
    events = timeline(root, entity=entity_id, limit=10000)
    return {
        "entity": entity_id,
        "event_count": len(events),
        "first_event": events[0].get("date") if events else None,
        "last_event": events[-1].get("date") if events else None,
        "events": events,
    }


# --- Reverse Index ---

def _index_path(root: Path) -> Path:
    return soul_path(root) / "events" / "_index.jsonl"


def _update_index(root: Path, event_id: str, entity_ids: list[str]) -> None:
    path = _index_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for eid in entity_ids:
            f.write(json.dumps({"entity": eid, "event": event_id}, ensure_ascii=False) + "\n")


def _index_lookup(root: Path, entity_id: str) -> list[str]:
    path = _index_path(root)
    if not path.exists():
        return _scan_events_for_entity(root, entity_id)
    event_ids = []
    for line in read_text(path).splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            if row.get("entity") == entity_id:
                event_ids.append(row["event"])
        except json.JSONDecodeError:
            continue
    return list(dict.fromkeys(event_ids))


def _scan_events_for_entity(root: Path, entity_id: str) -> list[str]:
    """Fallback: scan all event files for links to entity."""
    events_dir = soul_path(root) / "events"
    if not events_dir.exists():
        return []
    found = []
    for path in events_dir.rglob("evt_*.md"):
        text = read_text(path)
        if entity_id in text:
            fm = parse_frontmatter(text)
            if fm.get("id"):
                found.append(fm["id"])
    return found


# --- Internal helpers ---

def _find_event(root: Path, event_id: str) -> Path:
    events_dir = soul_path(root) / "events"
    if not events_dir.exists():
        raise FileNotFoundError(f"event not found: {event_id}")
    matches = list(events_dir.rglob(f"{event_id}.md"))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        return matches[0]
    for path in events_dir.rglob("evt_*.md"):
        if event_id in path.stem:
            return path
    raise FileNotFoundError(f"event not found: {event_id}")


def _append_to_list_field(path: Path, field: str, value: str) -> None:
    text = read_text(path)
    pattern = re.compile(rf"^{field}:\s*\[(.*?)\]\s*$", re.MULTILINE)
    match = pattern.search(text)
    if match:
        existing = match.group(1).strip()
        if existing:
            items = [i.strip() for i in existing.split(",")]
            if value not in items:
                items.append(value)
            new_list = ", ".join(items)
        else:
            new_list = value
        text = pattern.sub(f"{field}: [{new_list}]", text, count=1)
    write_text(path, text)


def _admiralty_gte(rating: str, minimum: str) -> bool:
    if len(rating) != 2 or len(minimum) != 2:
        return True
    source_order = "ABCDEF"
    info_order = "123456"
    s_idx = source_order.index(rating[0]) if rating[0] in source_order else 5
    m_s_idx = source_order.index(minimum[0]) if minimum[0] in source_order else 5
    i_idx = info_order.index(rating[1]) if rating[1] in info_order else 5
    m_i_idx = info_order.index(minimum[1]) if minimum[1] in info_order else 5
    return s_idx <= m_s_idx and i_idx <= m_i_idx
