#!/usr/bin/env python3
"""Tests for the OpenTSC v2.0 modules.

Runs on a bare Python install (no jieba/snownlp/zvec) by exercising the
graceful-degradation paths, and automatically covers the heavy backends when
their optional dependencies are present. Zero third-party test deps — plain
asserts so it runs the same way the smoke test does.
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(ROOT))

from opentsc_core import text, embedding, emotion  # noqa: E402
from opentsc_core.config import Config  # noqa: E402
from opentsc_core.common import parse_frontmatter, write_frontmatter  # noqa: E402

PASS = 0


def check(label, cond):
    global PASS
    assert cond, f"FAIL: {label}"
    PASS += 1


# --- P0: YAML frontmatter round-trip (locks the drift bug) ------------------

def test_frontmatter_roundtrip():
    data = {
        "id": "p_carol",
        "type": "human_npc",
        "tags": ["core_team", "ai"],
        "reliability": 0.85,
        "note": "按时交付，靠谱",
    }
    text_md = write_frontmatter(data, body="正文内容")
    parsed = parse_frontmatter(text_md)
    check("id survives", parsed.get("id") == "p_carol")
    check("type survives", parsed.get("type") == "human_npc")
    check("list survives", list(parsed.get("tags", [])) == ["core_team", "ai"])
    check("cjk body kept", "正文内容" in text_md)


# --- config -----------------------------------------------------------------

def test_config():
    c = Config()
    check("default embed lite", c.embedding_backend == "lite")
    check("default emotion lexicon", c.emotion_backend == "lexicon")
    c.embedding_backend = "bogus"
    try:
        c.validate()
        check("validate rejects bad backend", False)
    except ValueError:
        check("validate rejects bad backend", True)


# --- text -------------------------------------------------------------------

def test_text():
    toks = text.segment("报价文档交付")
    check("segment non-empty", len(toks) > 0)
    kws = text.keywords("Carol 按时完成报价文档交付 非常靠谱 值得信任", 5)
    check("keywords <= topk", len(kws) <= 5)
    check("normalize collapses ws", text.normalize("a   b\n c") == "a b c")


# --- emotion (lexicon w/ builtin fallback) ----------------------------------

def test_emotion():
    backend = emotion.get_emotion_backend(Config())
    pos = backend.score("这件事办得太棒了非常满意")
    neg = backend.score("已读不回真让人失望生气")
    check("positive detected", pos.polarity > 0)
    check("negative detected", neg.polarity < 0)
    check("empty is neutral", backend.score("").label == "neutral")
    check("polarity bounded", -1.0 <= pos.polarity <= 1.0)


# --- embedding (lite: deterministic, similar > dissimilar) ------------------

def test_embedding_lite():
    eb = embedding.get_embedding_backend(Config(embedding_backend="lite", embedding_dim=128))
    v1, v2, v3 = eb.embed(["报价文档交付", "报价文档已交付", "今天天气很好"])
    check("lite dim", len(v1) == 128)
    dot = lambda a, b: sum(x * y for x, y in zip(a, b))
    check("similar closer than dissimilar", dot(v1, v2) > dot(v1, v3))
    check("deterministic", eb.embed(["报价文档交付"])[0] == v1)


# --- index (full test only if zvec present) ---------------------------------

def test_index_optional():
    from opentsc_core.index import ZvecIndex, zvec_available

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        idx = ZvecIndex(root, Config())
        if not zvec_available():
            check("index reports unavailable", idx.available() is False)
            return
        # Build against an empty vault should not crash.
        idx.build()
        check("index builds empty vault", idx.stats()["available"] is True)


def main():
    for fn in [
        test_frontmatter_roundtrip, test_config, test_text,
        test_emotion, test_embedding_lite, test_index_optional,
    ]:
        fn()
    print(f"OpenTSC v2 tests passed ({PASS} checks)")


if __name__ == "__main__":
    main()
