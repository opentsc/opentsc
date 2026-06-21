from __future__ import annotations

import json
from pathlib import Path

from .common import now_iso, read_text, write_text

DEFAULT_SKILLS = [
    {"name": "opentsc", "use_for": "OpenTSC vault operations, relationship intelligence, actions, follow-up"},
    {"name": "deep-research", "use_for": "web/source research when user explicitly wants external research"},
    {"name": "verify", "use_for": "verify application behavior"},
    {"name": "code-review", "use_for": "review code changes"},
]


def init_skill_registry(root: Path) -> Path:
    path = root / "skills" / "registry" / "skills.json"
    if not path.exists():
        write_text(path, json.dumps({"updated_at": now_iso(), "skills": DEFAULT_SKILLS}, ensure_ascii=False, indent=2))
    return path


def list_skill_registry(root: Path) -> dict:
    path = init_skill_registry(root)
    return json.loads(read_text(path))


def recommend_skill(root: Path, task: str) -> dict[str, str]:
    reg = list_skill_registry(root)
    text = task.lower()
    for item in reg.get("skills", []):
        hay = (item.get("name", "") + " " + item.get("use_for", "")).lower()
        if any(tok in hay for tok in text.split()):
            return item
    if any(k in text for k in ["research", "调查", "搜集", "web", "来源"]):
        return {"name": "deep-research", "use_for": "research/investigation task"}
    return {"name": "opentsc", "use_for": "default OpenTSC reasoning/orchestration"}
