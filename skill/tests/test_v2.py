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


def test_emotion_domain_lexicon():
    # The domain lexicon must get business/relationship status text right even
    # without snownlp (CI runs with no extra deps) — this is the demo bug fix.
    lex = emotion.LexiconEmotion(use_snownlp=False)
    check("拖延烦躁 = negative", lex.score("Dave 在GPU采购上拖延，情绪烦躁").polarity < 0)
    check("主动积极 = positive", lex.score("Carol 主动接了报价，状态积极").polarity > 0)
    check("no domain word = low confidence", lex.score("下午开个会").confidence < 0.55)


def test_emotion_llm_batch_cache(tmp):
    import tempfile
    from opentsc_core.emotion import LLMEmotion, _Cache

    # Fake LLM command: counts invocations, scores by keyword.
    calls = Path(tmp) / "calls"
    cmd = (
        f"python3 -c \"import json,sys;"
        f"raw=sys.stdin.read();t=json.loads(raw[raw.find('['):]);"
        f"open(r'{calls}','a').write('x');"
        f"print(json.dumps([1.0 if '好' in x else -1.0 for x in t]))\""
    )
    cache = _Cache(Path(tmp) / "c.json")
    b = LLMEmotion(cmd, cache)
    texts = ["很好", "不好", "也好"]
    r1 = b.score_many(texts)
    check("llm batch scores all", len(r1) == 3 and r1[0].polarity == 1.0)
    r2 = b.score_many(texts)  # all cached now
    check("llm second pass cached", all(":cache" in e.backend for e in r2))
    n = len((calls).read_text()) if calls.exists() else 0
    check("llm batched into one call, cache stops re-spend", n == 1)


def test_emotion_hybrid_escalation(tmp):
    from opentsc_core.emotion import HybridEmotion, LexiconEmotion, LLMEmotion, _Cache

    calls = Path(tmp) / "hcalls"
    cmd = (
        f"python3 -c \"import json,sys;"
        f"raw=sys.stdin.read();t=json.loads(raw[raw.find('['):]);"
        f"open(r'{calls}','a').write('x');print(json.dumps([0.0]*len(t)))\""
    )
    h = HybridEmotion(LexiconEmotion(use_snownlp=False),
                      LLMEmotion(cmd, _Cache(Path(tmp) / "hc.json")), threshold=0.55)
    out = h.score_many(["主动接了很积极", "拖延烦躁", "随便聊聊没有情绪词"])
    check("confident handled by lexicon", out[0].backend == "hybrid:lexicon")
    check("uncertain escalated to llm", out[2].backend == "hybrid:llm")
    n = len((calls).read_text()) if calls.exists() else 0
    check("only uncertain escalates (1 batched call)", n == 1)


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
    no_arg = [
        test_frontmatter_roundtrip, test_config, test_text,
        test_emotion, test_emotion_domain_lexicon, test_embedding_lite,
        test_index_optional,
    ]
    needs_tmp = [test_emotion_llm_batch_cache, test_emotion_hybrid_escalation]
    for fn in no_arg:
        fn()
    with tempfile.TemporaryDirectory() as d:
        for fn in needs_tmp:
            fn(d)
    print(f"OpenTSC v2 tests passed ({PASS} checks)")


if __name__ == "__main__":
    main()
