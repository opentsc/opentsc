"""World model — players, NPCs (human + agent), orgs, operations.

Replaces vault.py entity creation functions with soul/shell/world structure.
"""
from __future__ import annotations

from pathlib import Path

from .common import (
    ensure_vault,
    stable_suffix,
    template,
    today,
    unique_path,
    validate_entity_id,
    world_path,
    write_text,
)


def new_player(root: Path, name: str, entity_id: str | None = None,
               aliases: list[str] | None = None, tags: list[str] | None = None) -> Path:
    """Create a player entity in world/players/."""
    ensure_vault(root)
    entity_id = entity_id or f"p_{stable_suffix(name + today())}"
    validate_entity_id(entity_id, "p_")
    player_dir = world_path(root) / "players" / entity_id
    player_dir.mkdir(parents=True, exist_ok=True)
    target = player_dir / "profile.md"
    content = _build_person_content(entity_id, name, "player", aliases, tags)
    write_text(target, content)
    return target


def new_human_npc(root: Path, name: str, entity_id: str | None = None,
                  aliases: list[str] | None = None, tags: list[str] | None = None) -> Path:
    """Create a human NPC entity in world/npcs/humans/."""
    ensure_vault(root)
    entity_id = entity_id or f"p_{stable_suffix(name + today())}"
    validate_entity_id(entity_id, "p_")
    npc_dir = world_path(root) / "npcs" / "humans" / entity_id
    npc_dir.mkdir(parents=True, exist_ok=True)
    target = npc_dir / "profile.md"
    content = _build_person_content(entity_id, name, "human_npc", aliases, tags)
    write_text(target, content)
    return target


def new_agent_npc(root: Path, name: str, entity_id: str | None = None,
                  profession: str | None = None, model_tier: str = "mid",
                  tags: list[str] | None = None) -> Path:
    """Create an agent NPC entity in world/npcs/agents/."""
    ensure_vault(root)
    entity_id = entity_id or f"a_{stable_suffix(name + today())}"
    validate_entity_id(entity_id, "a_")
    agent_dir = world_path(root) / "npcs" / "agents" / entity_id
    agent_dir.mkdir(parents=True, exist_ok=True)
    target = agent_dir / "profile.md"
    tag_text = "[" + ", ".join(tags or []) + "]"
    content = f"""---
id: {entity_id}
type: agent_npc
names:
  real: {name}
  aliases: []
professions: [{profession or ''}]
model_tier: {model_tier}
base:
  execution_ceiling: {{value: 0.8, confidence: 0.9, provenance: [], reviewed: {today()}, decay: 0.01}}
  reliability: {{value: 0.9, confidence: 0.9, provenance: [], reviewed: {today()}, decay: 0.01}}
  autonomy: {{value: 0.7, confidence: 0.9, provenance: [], reviewed: {today()}, decay: 0.01}}
skills: []
states: []
source_mode: configured
tags: {tag_text}
---

## Relationship edges

## Configuration

- model_tier: {model_tier}
- profession: {profession or 'TODO(assign)'}
"""
    write_text(target, content)
    return target


def new_org(root: Path, name: str, entity_id: str | None = None,
            tags: list[str] | None = None) -> Path:
    """Create an organization entity in world/orgs/."""
    ensure_vault(root)
    entity_id = entity_id or f"o_{stable_suffix(name + today())}"
    validate_entity_id(entity_id, "o_")
    org_dir = world_path(root) / "orgs" / entity_id
    org_dir.mkdir(parents=True, exist_ok=True)
    target = org_dir / "profile.md"
    tag_text = "[" + ", ".join(tags or []) + "]"
    content = f"""---
id: {entity_id}
type: org
names:
  real: {name}
  aliases: []
base:
  execution_ceiling: {{value: 0.5, confidence: 0.2, provenance: [], reviewed: null, decay: 0.02}}
  reliability: {{value: 0.5, confidence: 0.2, provenance: [], reviewed: null, decay: 0.02}}
tags: {tag_text}
---

## Relationship edges

## Intelligence timeline
"""
    write_text(target, content)
    return target


def new_operation(root: Path, title: str, deadline: str | None = None,
                  entity_id: str | None = None) -> Path:
    """Create an operation entity in world/operations/."""
    ensure_vault(root)
    seed = f"{title}-{deadline or today()}"
    entity_id = entity_id or f"op_{stable_suffix(seed)}"
    validate_entity_id(entity_id, "op_")
    op_dir = world_path(root) / "operations" / entity_id
    op_dir.mkdir(parents=True, exist_ok=True)
    target = op_dir / "profile.md"
    content = template("operation.md")
    content = content.replace("op_TODO", entity_id)
    content = content.replace("deadline: TODO(optional)", f"deadline: {deadline or 'TODO(optional)'}")
    content = content.replace("TODO(user)", title, 1)
    write_text(target, content)
    return target


def _build_person_content(entity_id: str, name: str, entity_type: str,
                          aliases: list[str] | None, tags: list[str] | None) -> str:
    content = template("person_v1.md")
    content = content.replace("p_TODO", entity_id)
    content = content.replace("type: human_npc", f"type: {entity_type}")
    content = content.replace("real: TODO(user)", f"real: {name}")
    content = content.replace("reviewed: TODO(date)", f"reviewed: {today()}")
    if tags:
        content = content.replace("tags: []", "tags: [" + ", ".join(tags) + "]")
    if aliases:
        alias_lines = "\n".join(
            [f"    - value: {a}\n      src: TODO(user)\n      status: suspected" for a in aliases]
        )
        content = content.replace("  aliases: []", f"  aliases:\n{alias_lines}")
    return content
