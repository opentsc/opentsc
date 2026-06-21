"""Profession definitions and assignment (M5).

Professions are contracts defining role archetypes — what skills, attributes,
and VSM functions a role requires. They live in shell/professions/*.md.
"""
from __future__ import annotations

import re
from pathlib import Path

from .common import parse_frontmatter, read_text, shell_path, today, write_text

PRESET_PROFESSIONS = [
    {
        "profession": "founder",
        "display": "创世者/玩家",
        "vsm": "S5",
        "holder_type": "player",
        "model_tier": "high",
        "required_skills": [],
        "attribute_thresholds": {},
        "reads": ["entities", "events", "feedback", "knowledge"],
        "writes": ["entities", "events", "feedback", "knowledge"],
        "triggers": [],
        "evolves_to": [],
        "description": "持有创世层与判断法典，最高仲裁，确认草案，宣告任务终结。",
    },
    {
        "profession": "commander",
        "display": "指挥官",
        "vsm": "S3/S5",
        "holder_type": "any",
        "model_tier": "high",
        "required_skills": [],
        "attribute_thresholds": {},
        "reads": ["entities", "events", "feedback", "knowledge"],
        "writes": ["feedback"],
        "triggers": ["critical_moment"],
        "evolves_to": [],
        "description": "战略决策，调用所有底层产出，关键时刻触发。",
    },
    {
        "profession": "sentinel",
        "display": "哨兵",
        "vsm": "S2/S4",
        "holder_type": "agent",
        "model_tier": "low",
        "required_skills": [{"anomaly_detection": ">=Lv.2"}, {"deadline_tracking": ">=Lv.1"}],
        "attribute_thresholds": {"reliability": ">=0.6"},
        "reads": ["entities", "events", "feedback"],
        "writes": [],
        "triggers": ["session.created", "session.idle", "schedule.hourly"],
        "evolves_to": ["scout"],
        "description": "盯异常、盯deadline、盯模式变化。发现就在事件流里留 needs_* 标记，不直接处理。",
    },
    {
        "profession": "ingestor",
        "display": "摄入官",
        "vsm": "S4",
        "holder_type": "agent",
        "model_tier": "mid",
        "required_skills": [],
        "attribute_thresholds": {},
        "reads": ["raw"],
        "writes": ["inbox"],
        "triggers": ["raw.new"],
        "evolves_to": [],
        "description": "接收新素材、分类分段、识别参与者，多模态，产出 inbox 草案。",
    },
    {
        "profession": "distiller",
        "display": "蒸馏师",
        "vsm": "S3",
        "holder_type": "agent",
        "model_tier": "high",
        "required_skills": [],
        "attribute_thresholds": {},
        "reads": ["entities", "events", "knowledge", "inbox"],
        "writes": ["events", "knowledge"],
        "triggers": ["inbox.pending"],
        "evolves_to": [],
        "description": "从原料提取情报，更新属性，建因果边——把原料变情报的核心。",
    },
    {
        "profession": "oracle",
        "display": "预言家",
        "vsm": "S4",
        "holder_type": "agent",
        "model_tier": "high",
        "required_skills": [],
        "attribute_thresholds": {},
        "reads": ["entities", "events", "feedback", "knowledge"],
        "writes": ["feedback"],
        "triggers": ["on_demand"],
        "evolves_to": [],
        "description": "预测人/项目走向，落库带到期日，回填校准。",
    },
    {
        "profession": "herald",
        "display": "简报官",
        "vsm": "S3",
        "holder_type": "agent",
        "model_tier": "mid",
        "required_skills": [],
        "attribute_thresholds": {},
        "reads": ["entities", "events", "feedback", "knowledge", "actions"],
        "writes": ["reports"],
        "triggers": ["session.created", "schedule.daily"],
        "evolves_to": [],
        "description": "生成报告与任务分配，启动时浮出该行动的事，必含逆耳项。",
    },
    {
        "profession": "coordinator",
        "display": "协调员",
        "vsm": "S2",
        "holder_type": "agent",
        "model_tier": "low",
        "required_skills": [],
        "attribute_thresholds": {},
        "reads": ["entities", "events", "actions"],
        "writes": [],
        "triggers": ["conflict.detected"],
        "evolves_to": [],
        "description": "检测并化解资源冲突与接口冲突，不管理单元只协调接口。",
    },
    {
        "profession": "operator",
        "display": "执行者",
        "vsm": "S1",
        "holder_type": "any",
        "model_tier": "low",
        "required_skills": [],
        "attribute_thresholds": {},
        "reads": ["actions"],
        "writes": ["events"],
        "triggers": ["action.assigned"],
        "evolves_to": [],
        "description": "直接产出 TSC 核心输出，在职责内自治。",
    },
    {
        "profession": "steward",
        "display": "归因官/司库",
        "vsm": "S3",
        "holder_type": "agent",
        "model_tier": "mid",
        "required_skills": [],
        "attribute_thresholds": {},
        "reads": ["entities", "events", "actions"],
        "writes": ["feedback"],
        "triggers": ["action.done", "operation.closed"],
        "evolves_to": [],
        "description": "贡献归因、资源分配、贡献代币发放，看证据不看关系。",
    },
    {
        "profession": "recruiter",
        "display": "招募官/猎头",
        "vsm": "S4",
        "holder_type": "agent",
        "model_tier": "mid",
        "required_skills": [],
        "attribute_thresholds": {},
        "reads": ["entities", "events"],
        "writes": ["inbox"],
        "triggers": ["gap.detected"],
        "evolves_to": [],
        "description": "检测能力缺口，在能力市场搜寻人才，产出招募意图或提示玩家去找人。",
    },
]


def init_professions(root: Path) -> list[str]:
    """Write preset profession files to shell/professions/."""
    prof_dir = shell_path(root) / "professions"
    prof_dir.mkdir(parents=True, exist_ok=True)
    created = []
    for prof in PRESET_PROFESSIONS:
        path = prof_dir / f"{prof['profession']}.md"
        if path.exists():
            continue
        skills_text = "[]" if not prof["required_skills"] else "\n" + "".join(
            f"  - {s}\n" for s in prof["required_skills"]
        )
        thresholds_text = "{}" if not prof["attribute_thresholds"] else "\n" + "".join(
            f"  {k}: \"{v}\"\n" for k, v in prof["attribute_thresholds"].items()
        )
        content = f"""---
profession: {prof['profession']}
display: {prof['display']}
vsm: {prof['vsm']}
holder_type: {prof['holder_type']}
model_tier: {prof['model_tier']}
required_skills: {skills_text}
attribute_thresholds: {thresholds_text}
reads: [{', '.join(prof['reads'])}]
writes: [{', '.join(prof['writes'])}]
triggers: [{', '.join(prof['triggers'])}]
evolves_to: [{', '.join(prof['evolves_to'])}]
---

# {prof['display']}

{prof['description']}
"""
        write_text(path, content)
        created.append(str(path))
    return created


def list_professions(root: Path) -> list[dict]:
    """List all defined professions."""
    prof_dir = shell_path(root) / "professions"
    if not prof_dir.exists():
        return []
    profs = []
    for path in sorted(prof_dir.glob("*.md")):
        text = read_text(path)
        fm = parse_frontmatter(text)
        if fm.get("profession"):
            profs.append(fm)
    return profs


def profession_gaps(root: Path) -> list[dict]:
    """Detect which required professions lack assigned holders."""
    profs = list_professions(root)
    if not profs:
        init_professions(root)
        profs = list_professions(root)

    from .common import scan_entities
    entities = scan_entities(root)
    assigned_professions: set[str] = set()
    for eid, ref in entities.items():
        if "archive" in ref.path.parts:
            continue
        text = read_text(ref.path)
        fm = parse_frontmatter(text)
        for p in fm.get("professions", []):
            if isinstance(p, str):
                assigned_professions.add(p)

    gaps = []
    for prof in profs:
        name = prof.get("profession", "")
        if name not in assigned_professions:
            gaps.append({
                "profession": name,
                "display": prof.get("display", name),
                "vsm": prof.get("vsm", ""),
                "holder_type": prof.get("holder_type", "any"),
                "model_tier": prof.get("model_tier", ""),
                "fillable_by_agent": prof.get("holder_type") in ("agent", "any"),
            })
    return gaps


def assign_profession(root: Path, entity_id: str, profession: str) -> Path:
    """Assign a profession to an entity."""
    from .common import resolve_entity_any
    path = resolve_entity_any(root, entity_id)
    text = read_text(path)
    prof_match = re.search(r"^professions:\s*\[(.*?)\]\s*$", text, re.MULTILINE)
    if prof_match:
        existing = prof_match.group(1).strip()
        if existing:
            items = [i.strip() for i in existing.split(",")]
            if profession not in items:
                items.append(profession)
            new_list = ", ".join(items)
        else:
            new_list = profession
        text = re.sub(r"^professions:\s*\[.*?\]\s*$", f"professions: [{new_list}]", text, count=1, flags=re.MULTILINE)
    else:
        text = text.replace("tags:", f"professions: [{profession}]\ntags:", 1)
    write_text(path, text)
    return path
