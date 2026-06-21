"""Pluggable emotion / sentiment scoring.

Three interchangeable backends, selected by ``Config.emotion_backend``:

* ``lexicon``  — snownlp if installed, else a tiny built-in lexicon. Pure,
  offline, millisecond-fast, reproducible. The sane default.
* ``model``    — an on-device transformer classifier (opt-in, heavier).
* ``llm``      — defers to an external command/agent for the hard cases.

All backends return the same :class:`Emotion` so callers never branch on which
one is active. The point of this module is to move "谁情绪不好" out of a daily
LLM re-read and into a cheap, deterministic precompute.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, asdict
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


# --- lexicon backend -------------------------------------------------------

# Minimal fallback lexicon used only when snownlp is unavailable. Deliberately
# small; the goal is "never crash", not "win a benchmark".
_POS = {"好", "棒", "赞", "喜欢", "开心", "满意", "感谢", "支持", "靠谱",
        "厉害", "成功", "顺利", "期待", "爱", "强", "稳", "妥"}
_NEG = {"差", "烂", "坑", "讨厌", "生气", "失望", "不满", "投诉", "垃圾",
        "失败", "麻烦", "焦虑", "担心", "怕", "累", "拖", "崩", "怒", "骂"}


class LexiconEmotion:
    """snownlp-backed sentiment, with a built-in lexicon fallback."""

    name = "lexicon"

    def __init__(self) -> None:
        self._snow = None
        try:
            from snownlp import SnowNLP  # type: ignore

            self._snow = SnowNLP
        except Exception:
            self._snow = None

    def score(self, text: str) -> Emotion:
        text = (text or "").strip()
        if not text:
            return Emotion(0.0, "neutral", 0.0, self.name)
        if self._snow is not None:
            try:
                s = self._snow(text).sentiments  # 0..1
                polarity = (s - 0.5) * 2.0
                confidence = abs(polarity)
                return Emotion(round(polarity, 4), _label_for(polarity), round(confidence, 4), self.name)
            except Exception:
                pass
        return self._lexicon_score(text)

    def _lexicon_score(self, text: str) -> Emotion:
        from .text import segment

        toks = segment(text, drop_stopwords=False)
        pos = sum(1 for t in toks if t in _POS)
        neg = sum(1 for t in toks if t in _NEG)
        total = pos + neg
        if total == 0:
            return Emotion(0.0, "neutral", 0.0, self.name + ":builtin")
        polarity = (pos - neg) / total
        confidence = min(1.0, total / 5.0)
        return Emotion(round(polarity, 4), _label_for(polarity), round(confidence, 4), self.name + ":builtin")


# --- model backend ---------------------------------------------------------


class ModelEmotion:
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


# --- llm backend -----------------------------------------------------------


class LLMEmotion:
    """Defers scoring to an external command (the agent/LLM).

    The command receives the text on stdin and must print a float polarity in
    [-1, 1] on stdout. Used sparingly — for nuance the cheap backends miss.
    """

    name = "llm"

    def __init__(self, command: str) -> None:
        self._command = command

    def score(self, text: str) -> Emotion:
        text = (text or "").strip()
        if not text or not self._command:
            return Emotion(0.0, "neutral", 0.0, self.name)
        try:
            out = subprocess.run(
                self._command, shell=True, input=text, capture_output=True,
                text=True, timeout=30,
            ).stdout.strip()
            polarity = max(-1.0, min(1.0, float(out)))
        except Exception:
            return Emotion(0.0, "neutral", 0.0, self.name + ":error")
        return Emotion(round(polarity, 4), _label_for(polarity), abs(polarity), self.name)


def get_emotion_backend(config: Config) -> EmotionBackend:
    """Factory: build the configured backend, with a safe lexicon fallback."""
    choice = config.emotion_backend
    if choice == "model":
        return ModelEmotion(config.emotion_model)
    if choice == "llm":
        return LLMEmotion(config.emotion_llm_command)
    return LexiconEmotion()
