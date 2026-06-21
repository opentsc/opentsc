"""Central configuration for OpenTSC v2.0.

One place decides which pluggable backend powers each capability. The design
rule is *graceful by default*: the zero-dependency ``lite`` / ``lexicon``
backends always work, and the heavier ``local`` (on-device model) or ``api``
backends are opt-in. Nothing in the core hard-requires jieba, snownlp, a
sentence-transformer, or zvec — they are activated only when selected and
present.

Resolution order (last wins):
    1. dataclass defaults
    2. ``<root>/soul/_config.yaml``  (flat ``key: value`` lines)
    3. ``OPENTSC_*`` environment variables

This module has **no third-party imports** so it can always be loaded.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, fields
from pathlib import Path

# Backend identifiers (kept as plain strings so config files stay human-edited).
EMBEDDING_BACKENDS = ("lite", "local", "api")
EMOTION_BACKENDS = ("lexicon", "model", "llm")


@dataclass
class Config:
    """Resolved OpenTSC configuration.

    Attributes are intentionally flat and primitive so the same object can be
    serialized back to ``_config.yaml`` and overridden by env vars without any
    schema machinery.
    """

    # --- capability backends ---
    embedding_backend: str = "lite"      # lite | local | api
    emotion_backend: str = "lexicon"     # lexicon | model | llm

    # --- embedding tuning ---
    embedding_dim: int = 256             # used by the lite hashing embedder
    embedding_model: str = "BAAI/bge-small-zh-v1.5"  # used by local backend
    embedding_api_url: str = ""          # used by api backend
    embedding_api_key_env: str = "OPENTSC_EMBED_API_KEY"

    # --- emotion tuning ---
    emotion_model: str = "uer/roberta-base-finetuned-jd-binary-chinese"
    emotion_llm_command: str = ""        # shell command the llm backend shells out to

    # --- index ---
    index_dir: str = ".index"            # relative to soul/; holds the zvec store (derived, rebuildable)

    @classmethod
    def load(cls, root: Path) -> "Config":
        """Build a Config from defaults → soul/_config.yaml → env vars."""
        cfg = cls()
        cfg._apply_file(root / "soul" / "_config.yaml")
        cfg._apply_env()
        cfg.validate()
        return cfg

    # -- internal resolvers -------------------------------------------------

    def _apply_file(self, path: Path) -> None:
        if not path.exists():
            return
        known = {f.name for f in fields(self)}
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            key, _, value = line.partition(":")
            key, value = key.strip(), value.strip().strip("'\"")
            if key in known and value:
                self._set_coerced(key, value)

    def _apply_env(self) -> None:
        for f in fields(self):
            env_key = "OPENTSC_" + f.name.upper()
            if env_key in os.environ and os.environ[env_key]:
                self._set_coerced(f.name, os.environ[env_key])

    def _set_coerced(self, key: str, value: str) -> None:
        current = getattr(self, key)
        if isinstance(current, int) and not isinstance(current, bool):
            try:
                value = int(value)
            except ValueError:
                return
        setattr(self, key, value)

    def validate(self) -> None:
        if self.embedding_backend not in EMBEDDING_BACKENDS:
            raise ValueError(
                f"embedding_backend must be one of {EMBEDDING_BACKENDS}, got {self.embedding_backend!r}"
            )
        if self.emotion_backend not in EMOTION_BACKENDS:
            raise ValueError(
                f"emotion_backend must be one of {EMOTION_BACKENDS}, got {self.emotion_backend!r}"
            )
        if self.embedding_dim <= 0:
            raise ValueError("embedding_dim must be positive")

    def index_path(self, root: Path) -> Path:
        return root / "soul" / self.index_dir

    def api_key(self) -> str:
        return os.environ.get(self.embedding_api_key_env, "")
