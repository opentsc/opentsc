"""Pluggable emotion / sentiment scoring.

Backends, selected by ``Config.emotion_backend``:

* ``lexicon`` — snownlp if installed, else a built-in lexicon. Pure, offline,
  millisecond-fast, free. Weak on short business text.
* ``model``   — an on-device transformer classifier (opt-in, heavier, accurate).
* ``llm``     — a large language model via an external command. Most accurate,
  costs tokens — so it is **batched and cached** (see below).
* ``hybrid``  — the token-smart default-when-you-have-an-LLM: the cheap lexicon
  scores everything, and **only the genuinely uncertain texts escalate to the
  LLM**. Most messages never reach the model.

Token discipline for the LLM path (this is how "wasteful but solve it" is
solved):
  1. **Cache** — every score is persisted by text hash; a re-run (e.g. the daily
     cron) pays nothing for text it has already seen.
  2. **Batch** — many texts go in one call via ``score_many``, not one call each.
  3. **Escalate** — in ``hybrid`` mode the LLM only sees what the lexicon is
     unsure about.

All backends return the same :class:`Emotion` and expose ``score`` /
``score_many`` so callers never branch on which one is active.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Protocol, runtime_checkable

from .config import Config


@dataclass(frozen=True)
class Emotion:
    """A sentiment reading.

    polarity:   -1.0 (very negative) .. +1.0 (very positive)
    label:      one of {"negative", "neutral", "positive"}
    confidence: 0.0 .. 1.0
    backend:    which backend produced it (for provenance / auditing)
    """

    polarity: float
    label: str
    confidence: float
    backend: str

    def as_dict(self) -> dict:
        return asdict(self)


def _label_for(polarity: float) -> str:
    if polarity <= -0.25:
        return "negative"
    if polarity >= 0.25:
        return "positive"
    return "neutral"


@runtime_checkable
class EmotionBackend(Protocol):
    name: str

    def score(self, text: str) -> Emotion: ...

    def score_many(self, texts: list[str]) -> list[Emotion]: ...


class _LoopMany:
    """Mixin: default score_many = score each (overridden where batching helps)."""

    def score_many(self, texts: list[str]) -> list[Emotion]:
        return [self.score(t) for t in texts]


# --- persistent score cache ------------------------------------------------


class _Cache:
    """Tiny JSON cache keyed by sha1(text). Used to never re-spend on the LLM."""

    def __init__(self, path: Path | None) -> None:
        self.path = Path(path) if path else None
        self._data: dict[str, list] = {}
        if self.path and self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self._data = {}

    @staticmethod
    def key(text: str) -> str:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()

    def get(self, text: str):
        return self._data.get(self.key(text))

    def put(self, text: str, polarity: float, confidence: float) -> None:
        self._data[self.key(text)] = [polarity, confidence]

    def flush(self) -> None:
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._data, ensure_ascii=False), encoding="utf-8")


# --- lexicon backend -------------------------------------------------------

# Curated domain lexicon — tuned for short business/relationship status text,
# where snownlp (trained on product reviews) routinely inverts. These take
# priority; snownlp is a fallback only when no domain word is present.
_POS = {"好", "棒", "赞", "喜欢", "开心", "满意", "感谢", "支持", "靠谱", "积极",
        "主动", "接了", "接下", "完成", "交付", "搞定", "推进", "答应", "确认",
        "厉害", "成功", "顺利", "期待", "爱", "强", "稳", "妥", "给力", "配合"}
_NEG = {"差", "烂", "坑", "讨厌", "生气", "失望", "不满", "投诉", "垃圾", "拖",
        "拖延", "烦躁", "焦虑", "担心", "怕", "累", "崩", "怒", "骂", "敷衍",
        "失败", "麻烦", "已读不回", "不回", "掉线", "推脱", "甩锅", "犹豫", "拒绝"}


class LexiconEmotion(_LoopMany):
    """Curated domain lexicon first; snownlp as fallback when no domain signal."""

    name = "lexicon"

    def __init__(self, use_snownlp: bool = True) -> None:
        # In hybrid mode the primary should report LOW confidence on text it has
        # no domain signal for, so the uncertain cases escalate to the LLM —
        # snownlp's overconfident guesses would otherwise block escalation.
        self._use_snownlp = use_snownlp
        try:
            from snownlp import SnowNLP  # type: ignore

            self._snow = SnowNLP if use_snownlp else None
        except Exception:
            self._snow = None

    def score(self, text: str) -> Emotion:
        text = (text or "").strip()
        if not text:
            return Emotion(0.0, "neutral", 0.0, self.name)
        domain = self._domain_score(text)
        if domain is not None:
            return domain
        if self._snow is not None:
            try:
                s = self._snow(text).sentiments
                polarity = round((s - 0.5) * 2.0, 4)
                return Emotion(polarity, _label_for(polarity), abs(polarity), self.name + ":snownlp")
            except Exception:
                pass
        return Emotion(0.0, "neutral", 0.0, self.name)

    def _domain_score(self, text: str) -> Emotion | None:
        from .text import segment

        toks = segment(text, drop_stopwords=False)
        joined = "".join(toks)
        pos = sum(1 for w in _POS if w in text or w in joined)
        neg = sum(1 for w in _NEG if w in text or w in joined)
        total = pos + neg
        if total == 0:
            return None
        polarity = round((pos - neg) / total, 4)
        confidence = round(min(1.0, total / 3.0), 4)
        return Emotion(polarity, _label_for(polarity), confidence, self.name)


# --- model backend ---------------------------------------------------------


class ModelEmotion(_LoopMany):
    """On-device transformer classifier. Lazy-loaded; opt-in."""

    name = "model"

    def __init__(self, model: str) -> None:
        self._model_name = model
        self._pipe = None

    def _pipeline(self):
        if self._pipe is None:
            from transformers import pipeline  # type: ignore

            self._pipe = pipeline("sentiment-analysis", model=self._model_name)
        return self._pipe

    def score(self, text: str) -> Emotion:
        text = (text or "").strip()
        if not text:
            return Emotion(0.0, "neutral", 0.0, self.name)
        res = self._pipeline()(text[:512])[0]
        raw = str(res.get("label", "")).lower()
        conf = float(res.get("score", 0.0))
        sign = 1.0 if ("pos" in raw or raw in {"1", "5 stars", "4 stars"}) else -1.0
        polarity = round(sign * conf, 4)
        return Emotion(polarity, _label_for(polarity), round(conf, 4), self.name)


# --- llm backend (batched + cached) ----------------------------------------

_LLM_PROMPT = (
    "你是情绪标注器。对下面 JSON 数组里的每段中文文本，判断说话者情绪极性，"
    "输出一个等长 JSON 数组，每项是 -1.0(极负) 到 1.0(极正) 的浮点数，只输出 JSON 数组本身。\n"
)


class LLMEmotion(_LoopMany):
    """Score via an external LLM command. Batched and cached for token thrift.

    Command contract: receives a JSON array of strings on stdin, prints a
    JSON array of polarities (floats in [-1, 1]) of equal length on stdout.
    A single-float stdout is also accepted (single-text convenience).
    """

    name = "llm"

    def __init__(self, command: str, cache: _Cache | None = None) -> None:
        self._command = command
        self._cache = cache or _Cache(None)

    def score(self, text: str) -> Emotion:
        return self.score_many([text])[0]

    def score_many(self, texts: list[str]) -> list[Emotion]:
        results: list[Emotion | None] = [None] * len(texts)
        ask: list[str] = []
        ask_idx: list[int] = []

        for i, t in enumerate(texts):
            t = (t or "").strip()
            if not t:
                results[i] = Emotion(0.0, "neutral", 0.0, self.name)
                continue
            cached = self._cache.get(t)
            if cached is not None:
                pol, conf = cached
                results[i] = Emotion(pol, _label_for(pol), conf, self.name + ":cache")
            else:
                ask.append(t)
                ask_idx.append(i)

        if ask and self._command:
            polarities = self._call(ask)
            for j, pol in enumerate(polarities):
                pol = max(-1.0, min(1.0, float(pol)))
                t = ask[j]
                self._cache.put(t, round(pol, 4), abs(round(pol, 4)))
                results[ask_idx[j]] = Emotion(round(pol, 4), _label_for(pol), abs(pol), self.name)
            self._cache.flush()

        # Anything still unscored (no command configured / call failed) → neutral.
        return [r or Emotion(0.0, "neutral", 0.0, self.name + ":nocmd") for r in results]

    def _call(self, texts: list[str]) -> list[float]:
        payload = json.dumps(texts, ensure_ascii=False)
        try:
            out = subprocess.run(
                self._command, shell=True, input=_LLM_PROMPT + payload,
                capture_output=True, text=True, timeout=120,
            ).stdout.strip()
            parsed = json.loads(out[out.find("[") : out.rfind("]") + 1]) if "[" in out else [float(out)]
            if len(parsed) != len(texts):
                return [0.0] * len(texts)
            return [float(x) for x in parsed]
        except Exception:
            return [0.0] * len(texts)


# --- hybrid backend (lexicon, escalate only the uncertain to the LLM) ------


class HybridEmotion:
    """Cheap lexicon for the obvious; LLM only for the uncertain. Token-smart."""

    name = "hybrid"

    def __init__(self, primary: EmotionBackend, escalate: EmotionBackend, threshold: float) -> None:
        self._primary = primary
        self._escalate = escalate
        self._threshold = threshold

    def score(self, text: str) -> Emotion:
        return self.score_many([text])[0]

    def score_many(self, texts: list[str]) -> list[Emotion]:
        base = self._primary.score_many(texts)
        uncertain_idx = [i for i, e in enumerate(base) if e.confidence < self._threshold and (texts[i] or "").strip()]
        if not uncertain_idx:
            return [Emotion(e.polarity, e.label, e.confidence, "hybrid:" + e.backend) for e in base]
        escalated = self._escalate.score_many([texts[i] for i in uncertain_idx])
        out = list(base)
        for k, i in enumerate(uncertain_idx):
            e = escalated[k]
            out[i] = Emotion(e.polarity, e.label, e.confidence, "hybrid:" + e.backend)
        return [e if e.backend.startswith("hybrid:") else Emotion(e.polarity, e.label, e.confidence, "hybrid:" + e.backend) for e in out]


def get_emotion_backend(config: Config, cache_path: Path | None = None) -> EmotionBackend:
    """Factory: build the configured backend.

    ``cache_path`` (typically ``soul/.index/emotion_cache.json``) enables the
    persistent LLM score cache. Lexicon/model don't need it.
    """
    cache = _Cache(cache_path) if (cache_path and config.emotion_cache) else _Cache(None)

    def _llm() -> LLMEmotion:
        return LLMEmotion(config.emotion_llm_command, cache)

    choice = config.emotion_backend
    if choice == "model":
        return ModelEmotion(config.emotion_model)
    if choice == "llm":
        return _llm()
    if choice == "hybrid":
        return HybridEmotion(LexiconEmotion(use_snownlp=False), _llm(), config.emotion_escalate_threshold)
    return LexiconEmotion()
