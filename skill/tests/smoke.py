#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "opentsc.py"
TMP = ROOT / ".tmp-test-vault"
CONTACTS = ROOT / "examples" / "contacts.csv"
RAW = ROOT / "examples" / "raw-note.md"


def run(*args: str) -> str:
    cmd = [sys.executable, str(CLI), "--root", str(TMP), *args]
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode != 0:
        raise AssertionError(f"command failed: {' '.join(cmd)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    return result.stdout


def main() -> None:
    if TMP.exists():
        shutil.rmtree(TMP)
    run("init")
    run("upgrade")
    run("naming-audit")
    run("new-person", "张三", "--id", "p_demo01", "--alias", "老张", "--tag", "潜在合作", "--skill", "GEO", "--availability", "available", "--reliability", "0.8", "--control-level", "high")
    run("new-person", "李四", "--id", "p_demo02", "--skill", "SEO", "--availability", "busy")
    run("new-org", "薄壳资本", "--id", "o_demo01")
    run("link", "p_demo01", "member-of", "o_demo01", "--since", "2026-05", "--evidence", "user", "--confidence", "high", "--introduced-by", "p_demo02", "--emotion", "trust")
    run("links", "p_demo01")
    run("query", "GEO", "--scope", "people")
    run("who-can", "GEO", "--available")
    run("tag", "p_demo01", "核心")
    run("tags", "--filter", "核心")
    run("untag", "p_demo01", "核心")
    run("new-operation", "7月8日前完成 X", "--deadline", "2026-07-08", "--id", "op_demo01")
    dropbox_file = TMP / "intake" / "dropbox" / "TL战报.md"
    dropbox_file.parent.mkdir(parents=True, exist_ok=True)
    dropbox_file.write_text("TL战报：张三负责GEO，薄壳资本参与项目。", encoding="utf-8")
    run("ingest", str(dropbox_file), "--type", "battle_report", "--source", "smoke")
    run("sources")
    run("source-audit")
    run("source-derived", "raw_")
    run("skill-registry")
    run("skill-recommend", "调查 Stanley Team 背景")
    run("file-audit")
    run("accept", "draft_events", "--entity", "p_demo01", "--admiralty", "B2", "--content", "张三负责GEO", "--source", "smoke-ingest")
    run("accept", "draft_relations", "--relation", "p_demo01", "works-on", "op_demo01", "--source", "smoke-ingest")
    run("accept", "draft_knowledge", "--knowledge-layer", "methods")
    run("reject", "draft_entities", "--reason", "smoke reject candidate entities")
    run("store-raw", "5月会议记录", "我在场会议", "--file", str(RAW), "--material-type", "meeting")
    run("draft-event", "p_demo01", "B2", "当面聊，说想离开现公司单干", "我直接")
    run("add-event", "p_demo01", "B2", "当面聊，说想离开现公司单干", "我直接")
    run("stage-prediction", "recommendation", "任务找人: X", "优先找 p_demo01", "2026-07-08", "--reason", "p_demo01 有相关事件证据", "--reason", "需要使用者拍板交情成本")
    run("action-new", "Ask Zhangsan GEO status", "--type", "follow_up", "--due", "2026-07-08", "--operation", "op_demo01", "--target", "p_demo01", "--expected", "补一条进度事件")
    run("capture-actions", "明天提醒我问张三预算；本周让李四搜集竞品情报", "--operation", "op_demo01")
    run("accept-action", "draft_actions", "--item", "1")
    run("reject-action", "draft_actions", "--reason", "smoke reject remaining action draft")
    run("suggest-actions", "--goal", "推进TL项目报价", "--operation", "op_demo01")
    run("actions")
    run("action-wait", "Ask-Zhangsan", "--reason", "等对方回复")
    run("action-done", "Ask-Zhangsan", "--note", "已跟进，张三说明GEO进度正常", "--entity", "p_demo01")
    run("due", "--date", "2026-07-08")
    run("calibrate", "pred_", "--result", "partial", "--note", "烟测校准")
    run("accuracy")
    run("import-contacts", str(CONTACTS))
    run("archive", "p_demo02", "--reason", "smoke")
    run("restore", "p_demo02")
    run("new-person", "老张", "--id", "p_demo03")
    run("merge", "p_demo03", "into", "p_demo01", "--keep-alias", "老张")
    run("conflicts")
    run("brief")
    run("report-monthly", "--month", "2026-05")
    run("validate", "--check-conflicts")
    shutil.rmtree(TMP)
    print("OpenTSC smoke test passed")


if __name__ == "__main__":
    main()
