from __future__ import annotations

import datetime as dt
import re
import shutil
from pathlib import Path

from .common import now_iso, read_text, sanitize_filename, stable_suffix, template, today, write_text

ACTION_TYPES = {
    "meet_in_person", "online_meeting", "phone_call", "message", "intro_request",
    "intel_collection", "background_check", "verify_claim", "budget_probe",
    "decision_probe", "relationship_warmup", "follow_up", "remind", "delegate",
    "wait", "escalate", "deescalate", "close_loop", "review", "custom",
}
STATUSES = {"proposed", "active", "waiting", "done", "dropped"}


def new_action(root: Path, title: str, action_type: str = "custom", due: str | None = None, operation: str | None = None, target: list[str] | None = None, assignee: str | None = None, priority: str = "medium", status: str = "active", source_kind: str = "manual", reasoning: list[str] | None = None, expected: list[str] | None = None, risk: list[str] | None = None) -> Path:
    if action_type not in ACTION_TYPES:
        action_type = "custom"
    if status not in STATUSES:
        raise ValueError(f"invalid action status: {status}")
    action_id = f"act_{today().replace('-', '')}_{stable_suffix(title + (due or '') + now_iso(), 8)}"
    target_dir = root / "actions" / status
    path = target_dir / f"{action_id}-{sanitize_filename(title, 40)}.md"
    content = template("action.md")
    replacements = {
        "act_TODO": action_id,
        "status: proposed": f"status: {status}",
        "action_type: custom": f"action_type: {action_type}",
        "title: TODO(user)": f"title: {title}",
        "operation: TODO(optional op_id)": f"operation: {operation or 'TODO(optional)'}",
        "target_entities: []": "target_entities: [" + ", ".join(target or []) + "]",
        "assignee: TODO(optional entity_id or user)": f"assignee: {assignee or 'TODO(optional)'}",
        "due: TODO(YYYY-MM-DD)": f"due: {due or 'TODO(YYYY-MM-DD)'}",
        "priority: medium": f"priority: {priority}",
        "created_at: TODO(timestamp)": f"created_at: {now_iso()}",
        "kind: TODO(user_capture|system_suggestion|manual)": f"kind: {source_kind}",
        "# TODO(action title)": f"# {title}",
        "TODO(user)": title,
    }
    for old, new in replacements.items():
        content = content.replace(old, new, 1)
    content = content.replace("reasoning: []", _yaml_list("reasoning", reasoning or []), 1)
    content = content.replace("expected_output: []", _yaml_list("expected_output", expected or []), 1)
    content = content.replace("risk: []", _yaml_list("risk", risk or []), 1)
    write_text(path, content)
    return path


def capture_actions(root: Path, text: str, operation: str | None = None, default_due: str | None = None) -> Path:
    draft_id = f"draft_actions_{today().replace('-', '')}_{stable_suffix(text, 8)}"
    path = root / "inbox" / "actions" / f"{draft_id}.md"
    items = _split_action_text(text)
    lines = [f"---\nid: {draft_id}\ntype: inbox_action_batch\nstatus: draft\noperation: {operation or 'TODO(optional)'}\ncreated_at: {now_iso()}\n---\n\n# Draft Actions\n\n"]
    for i, item in enumerate(items, 1):
        due = _guess_due(item) or default_due or "TODO(YYYY-MM-DD)"
        action_type = _guess_action_type(item)
        lines.append(f"## {i}. {item}\n\n- action_type: {action_type}\n- due: {due}\n- operation: {operation or 'TODO(optional)'}\n- target_entities: TODO(user)\n- expected_output: TODO(user)\n- status: draft\n\n")
    write_text(path, "".join(lines))
    return path


def accept_action(root: Path, draft: str, item: int | None = None, all_items: bool = False, status: str = "active") -> list[Path]:
    draft_path = _find_action_draft(root, draft)
    text = read_text(draft_path)
    parsed = _parse_draft_actions(text)
    selected = parsed if all_items else [parsed[(item or 1) - 1]]
    created = [new_action(root, title=s["title"], action_type=s["action_type"], due=s["due"], operation=s.get("operation"), status=status, source_kind="user_capture", expected=[s.get("expected_output", "TODO(user)")]) for s in selected]
    if all_items or item is None:
        _archive_draft(root, draft_path, "accepted_action_draft")
    return created


def reject_action(root: Path, draft: str, reason: str) -> Path:
    draft_path = _find_action_draft(root, draft)
    text = read_text(draft_path) + f"\n\n## Reject reason\n\n{reason}\n"
    write_text(draft_path, text)
    return _archive_draft(root, draft_path, "rejected_action_draft")


def list_actions(root: Path, status: str | None = None, due: str | None = None, operation: str | None = None, entity: str | None = None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    statuses = [status] if status else sorted(STATUSES)
    cutoff = _due_cutoff(due)
    for st in statuses:
        for path in (root / "actions" / st).glob("*.md"):
            text = read_text(path)
            row = _action_row(path, text)
            if operation and row.get("operation") != operation:
                continue
            if entity and entity not in text:
                continue
            if cutoff and row.get("due") and row["due"].startswith("TODO"):
                continue
            if cutoff and row.get("due") and dt.date.fromisoformat(row["due"]) > cutoff:
                continue
            rows.append(row)
    return sorted(rows, key=lambda r: (r.get("due", "9999-99-99"), r.get("priority", ""), r.get("id", "")))


def transition_action(root: Path, action_id: str, new_status: str, note: str = "") -> Path:
    if new_status not in STATUSES:
        raise ValueError(f"invalid action status: {new_status}")
    path = _find_action(root, action_id)
    text = read_text(path)
    text = re.sub(r"^status:\s*\w+\s*$", f"status: {new_status}", text, count=1, flags=re.MULTILINE)
    text = text.rstrip() + f"\n\n## Status update · {now_iso()}\n\n- status: {new_status}\n- note: {note or 'TODO(user)'}\n"
    target = root / "actions" / new_status / path.name
    target.parent.mkdir(parents=True, exist_ok=True)
    write_text(path, text)
    if path.parent != target.parent:
        if target.exists():
            target = target.with_name(f"{target.stem}-{stable_suffix(now_iso(), 4)}{target.suffix}")
        shutil.move(str(path), str(target))
        return target
    return path


def complete_action(root: Path, action_id: str, note: str = "", create_event: bool = True, entity: str | None = None) -> tuple[Path, Path | None]:
    completed = transition_action(root, action_id, "done", note=note)
    event_path = None
    if create_event:
        draft_id = f"draft_event_from_{completed.stem}_{stable_suffix(note or completed.stem, 6)}"
        event_path = root / "inbox" / "events" / f"{draft_id}.md"
        write_text(event_path, f"---\nid: {draft_id}\ntype: inbox_event\nsource_action: {completed.stem}\nentity: {entity or 'TODO(entity_id)'}\nadmiralty: B6\nstatus: draft\ncreated_at: {now_iso()}\n---\n\n# Candidate event from completed action\n\n{note or 'TODO(user): summarize action result'}\n\n## If accepted\n\n- {today()} · B6 · {note or 'TODO(user): summarize action result'} ·〔来源: {completed.stem}; status: pending_verification〕\n")
    return completed, event_path


def suggest_actions(root: Path, goal: str | None = None, operation: str | None = None, entity: str | None = None, gap: str | None = None) -> Path:
    title = goal or gap or operation or entity or "next move"
    suggestions = _divergent_suggestions(title, operation, entity, gap)
    draft_text = "；".join(suggestions)
    return capture_actions(root, draft_text, operation=operation)


def due_actions(root: Path) -> list[dict[str, str]]:
    return list_actions(root, due="today")


def stale_actions(root: Path, days: int = 30, status: str = "active") -> list[dict[str, str]]:
    """Active actions untouched for `days` days or already past due — the
    deterministic zombie finder that replaces an LLM re-scanning actions/active/
    on every cron run. Each row gains `age_days` and `overdue`.
    """
    import time

    cutoff = time.time() - days * 86400
    today_iso = dt.date.today().isoformat()
    rows: list[dict[str, str]] = []
    for row in list_actions(root, status=status):
        try:
            mtime = Path(row["path"]).stat().st_mtime
        except OSError:
            continue
        due = row.get("due", "")
        overdue = bool(due) and not due.startswith("TODO") and due < today_iso
        if mtime < cutoff or overdue:
            rows.append({**row, "age_days": str(int((time.time() - mtime) / 86400)),
                         "overdue": "yes" if overdue else "no"})
    return sorted(rows, key=lambda r: int(r["age_days"]), reverse=True)


def _yaml_list(key: str, values: list[str]) -> str:
    if not values:
        return f"{key}: []"
    return key + ":\n" + "".join(f"  - {v}\n" for v in values).rstrip()


def _split_action_text(text: str) -> list[str]:
    parts = re.split(r"[；;\n]+|(?:，|,)(?=(?:[^，,]{0,12})(?:提醒|让|约|问|查|催|打|发|沟通|复盘))", text)
    return [p.strip(" 。.\t") for p in parts if p.strip(" 。.\t")]


def _guess_action_type(item: str) -> str:
    if any(x in item for x in ["见", "约", "面聊", "线下"]):
        return "meet_in_person"
    if any(x in item for x in ["线上", "会议", "视频"]):
        return "online_meeting"
    if any(x in item for x in ["电话", "打给", "打电话"]):
        return "phone_call"
    if any(x in item for x in ["查", "搜", "调查", "收集"]):
        return "intel_collection"
    if any(x in item for x in ["催", "跟进", "问", "提醒"]):
        return "follow_up"
    if any(x in item for x in ["发", "消息", "微信"]):
        return "message"
    if "复盘" in item:
        return "review"
    return "custom"


def _guess_due(item: str) -> str | None:
    today_date = dt.date.today()
    if "今天" in item:
        return today_date.isoformat()
    if "明天" in item:
        return (today_date + dt.timedelta(days=1)).isoformat()
    if "后天" in item:
        return (today_date + dt.timedelta(days=2)).isoformat()
    if "本周" in item or "周五" in item:
        return (today_date + dt.timedelta(days=max(1, 4 - today_date.weekday()))).isoformat()
    if "下周" in item:
        return (today_date + dt.timedelta(days=7)).isoformat()
    return None


def _parse_draft_actions(text: str) -> list[dict[str, str]]:
    blocks = re.split(r"^##\s+\d+\.\s+", text, flags=re.MULTILINE)[1:]
    out = []
    for b in blocks:
        lines = b.splitlines()
        title = lines[0].strip() if lines else "TODO(action)"
        def val(key: str) -> str:
            m = re.search(rf"^- {key}:\s*(.+?)\s*$", b, re.MULTILINE)
            return m.group(1).strip() if m else ""
        out.append({"title": title, "action_type": val("action_type") or "custom", "due": val("due") or "TODO(YYYY-MM-DD)", "operation": val("operation"), "expected_output": val("expected_output")})
    return out


def _find_action_draft(root: Path, draft: str) -> Path:
    inbox = root / "inbox" / "actions"
    exact = list(inbox.glob(f"{draft}.md"))
    if len(exact) == 1:
        return exact[0]
    candidates = list(inbox.glob(f"*{draft}*.md"))
    # Prefer user-captured draft_actions over source-generated draft_actions_from_source.
    preferred = [p for p in candidates if p.name.startswith("draft_actions_") and not p.name.startswith("draft_actions_from_source_")]
    if len(preferred) == 1:
        return preferred[0]
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        raise ValueError(f"ambiguous action draft: {draft}")
    raise FileNotFoundError(f"action draft not found: {draft}")


def _find_action(root: Path, action_id: str) -> Path:
    candidates = list((root / "actions").glob(f"**/*{action_id}*.md"))
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        raise ValueError(f"ambiguous action id: {action_id}")
    raise FileNotFoundError(f"action not found: {action_id}")


def _archive_draft(root: Path, path: Path, reason: str) -> Path:
    target = root / "archive" / "inbox" / today()[:4] / today()[5:7] / path.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(target))
    return target


def _action_row(path: Path, text: str) -> dict[str, str]:
    def val(key: str) -> str:
        m = re.search(rf"^{key}:\s*(.+?)\s*$", text, re.MULTILINE)
        return m.group(1).strip() if m else ""
    return {"id": val("id") or path.stem, "status": val("status"), "type": val("action_type"), "title": val("title") or _heading(text), "due": val("due"), "priority": val("priority"), "operation": val("operation"), "path": str(path)}


def _heading(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _due_cutoff(due: str | None) -> dt.date | None:
    if not due:
        return None
    if due == "today":
        return dt.date.today()
    return dt.date.fromisoformat(due)


def _divergent_suggestions(title: str, operation: str | None, entity: str | None, gap: str | None) -> list[str]:
    base = title
    return [
        f"约关键人线下沟通：围绕{base}确认真实意图、预算、决策链",
        f"发低压消息试探：围绕{base}获取下一步窗口，不急于压成交",
        f"安排情报收集：让可调动人员查{base}的公开案例、背景和风险信号",
        f"核实关键说法：把{base}中未证实的判断拆成2-3个可验证问题",
        f"设置跟进节点：为{base}设定下一次检查时间和预期产出",
    ]
