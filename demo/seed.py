#!/usr/bin/env python3
"""Seed a small demo vault for the OpenTSC TUI.

Builds demo/demo-vault/ with a few entities and evidence-backed events, then
lets the K7 judgment engine derive attributes from those events — so the TUI
shows real derived state (attribute bars, mood, timelines), not mock data.

Run once: python demo/seed.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "skill" / "scripts"))

from opentsc_core.vault import init_vault  # noqa: E402
from opentsc_core.world import new_player, new_human_npc  # noqa: E402
from opentsc_core.events import append_event  # noqa: E402
from opentsc_core.judgment import on_event  # noqa: E402

VAULT = HERE / "demo-vault"

# (id, name, tag, is_player)
CAST = [
    ("p_alice", "Alice", "founder", True),
    ("p_carol", "Carol", "core_team", False),
    ("p_dave", "Dave", "partner", False),
    ("p_eve", "Eve", "client", False),
    ("p_frank", "Frank", "new_hire", False),
]

# (admiralty, content, source, entity) — content hits judgment_codex triggers
EVENTS = [
    ("A1", "Carol 按时完成了报价文档的交付，质量很高，主动推进了客户对接", "周会纪要", "p_carol"),
    ("B2", "Carol 在客户临时变更需求的压力下扛住了，情绪稳定，坚持到底交付", "项目复盘", "p_carol"),
    ("C3", "Dave 在 GPU 采购的执行上拖延，迟迟未完成交付，需要反复催促", "微信记录", "p_dave"),
    ("C3", "Dave 把对接的落地工作半途而废，甩给了别人", "项目复盘", "p_dave"),
    ("B4", "Frank 快速掌握了新工具，举一反三，独立执行了第一个任务", "导师反馈", "p_frank"),
    ("B2", "Eve 确认了合作意向，但对报价仍有犹豫", "通话记录", "p_eve"),
    ("A2", "Alice 主动推进战略落地，独立执行了三条业务线", "自述", "p_alice"),
]


def main():
    init_vault(VAULT)
    for eid, name, tag, is_player in CAST:
        fn = new_player if is_player else new_human_npc
        try:
            fn(VAULT, name, entity_id=eid, tags=[tag])
        except Exception as e:
            print(f"  skip entity {eid}: {e}", file=sys.stderr)
    for adm, content, source, ent in EVENTS:
        try:
            eid = append_event(VAULT, adm, content, source, links=[ent])
            on_event(VAULT, eid)  # K7 derives attributes
        except Exception as e:
            print(f"  skip event ({ent}): {e}", file=sys.stderr)
    print(f"seeded demo vault → {VAULT}")


if __name__ == "__main__":
    main()
