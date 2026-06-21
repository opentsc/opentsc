"""Chinese-aware text processing: segmentation, keywords, normalization.

Uses ``jieba`` when available and degrades to a dependency-free regex
segmenter otherwise, so importing this module never fails. Everything here is
pure and deterministic — given the same input and the same jieba dictionary it
returns the same tokens, which is what makes the downstream index reproducible.
"""

from __future__ import annotations

import re
from functools import lru_cache

# Lazy, optional jieba. We probe once and cache the handle (or None).
_JIEBA = None
_JIEBA_PROBED = False

# A small, high-value stopword set. Kept inline (not a data file) so the module
# stays self-contained; extend via add_stopwords() at runtime if needed.
STOPWORDS: set[str] = {
    "的", "了", "和", "是", "在", "我", "你", "他", "她", "它", "们", "也",
    "都", "就", "不", "人", "这", "那", "有", "我们", "你们", "他们", "啊",
    "吧", "呢", "吗", "把", "被", "给", "对", "与", "及", "或", "而", "之",
    "着", "过", "得", "地", "上", "下", "里", "个", "一个", "没有", "可以",
    "什么", "怎么", "这个", "那个", "一些", "因为", "所以", "但是", "如果",
    "the", "a", "an", "is", "are", "to", "of", "and", "in", "on", "for",
}

# Word-ish runs: CJK chars individually grouped, plus latin/number tokens.
_TOKEN_RE = re.compile(r"[一-鿿]+|[A-Za-z0-9_]+")
_CJK_RUN = re.compile(r"[一-鿿]{2,}")


def _jieba():
    global _JIEBA, _JIEBA_PROBED
    if not _JIEBA_PROBED:
        _JIEBA_PROBED = True
        try:
            import jieba  # type: ignore

            jieba.setLogLevel(60)  # silence jieba's loader chatter
            _JIEBA = jieba
        except Exception:
            _JIEBA = None
    return _JIEBA


def has_jieba() -> bool:
    return _jieba() is not None


def add_stopwords(words) -> None:
    STOPWORDS.update(words)


def segment(text: str, drop_stopwords: bool = True) -> list[str]:
    """Split text into tokens. jieba when present, regex bigrams otherwise."""
    if not text:
        return []
    jb = _jieba()
    if jb is not None:
        tokens = [t.strip() for t in jb.lcut(text) if t.strip()]
    else:
        tokens = _fallback_segment(text)
    if drop_stopwords:
        tokens = [t for t in tokens if t.lower() not in STOPWORDS]
    return tokens


def _fallback_segment(text: str) -> list[str]:
    """Dependency-free segmenter: latin words whole, CJK as overlapping bigrams.

    Bigrams give the lite embedder and full-text matcher usable signal without
    a real tokenizer — crude but reproducible.
    """
    out: list[str] = []
    for chunk in _TOKEN_RE.findall(text):
        if chunk.isascii():
            out.append(chunk)
        elif len(chunk) == 1:
            out.append(chunk)
        else:
            out.extend(chunk[i : i + 2] for i in range(len(chunk) - 1))
    return out


@lru_cache(maxsize=2048)
def _kw_cached(text: str, topk: int) -> tuple[str, ...]:
    jb = _jieba()
    if jb is not None:
        try:
            from jieba import analyse  # type: ignore

            tags = analyse.extract_tags(text, topK=topk)
            if tags:
                return tuple(tags)
        except Exception:
            pass
    # Fallback: frequency over fallback segmentation, longer tokens win ties.
    freq: dict[str, int] = {}
    for tok in segment(text):
        freq[tok] = freq.get(tok, 0) + 1
    ranked = sorted(freq, key=lambda w: (freq[w], len(w)), reverse=True)
    return tuple(ranked[:topk])


def keywords(text: str, topk: int = 8) -> list[str]:
    """Top-k keywords (TF-IDF via jieba, frequency fallback otherwise)."""
    if not text:
        return []
    return list(_kw_cached(text, topk))


def normalize(text: str) -> str:
    """Collapse whitespace and strip — cheap canonicalization for hashing/compare."""
    return re.sub(r"\s+", " ", text or "").strip()
