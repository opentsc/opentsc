"""Pluggable text embedding.

Three interchangeable backends, selected by ``Config.embedding_backend``:

* ``lite``  — a dependency-free hashing embedder over jieba/bigram tokens.
  Deterministic and instant; good enough for dedup and rough similarity. The
  default, so the index works on a bare Python install.
* ``local`` — an on-device sentence-transformer (BGE / M3E). Opt-in, offline,
  best privacy/quality trade-off.
* ``api``   — a remote embedding endpoint. Highest quality, costs tokens and
  sends text off the machine.

Every backend exposes ``dim`` and ``embed(texts) -> list[vector]`` and returns
L2-normalized vectors, so cosine similarity is just a dot product downstream.
"""

from __future__ import annotations

import hashlib
import json
import math
import urllib.request
from typing import Protocol, runtime_checkable

from .config import Config


@runtime_checkable
class EmbeddingBackend(Protocol):
    name: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]


# --- lite backend ----------------------------------------------------------


class LiteEmbedding:
    """Hashing vectorizer: tokens → fixed-dim bag, then L2-normalized.

    No model, no network, fully reproducible. Each token is hashed to a bucket
    with a signed contribution, which approximates a random projection of a
    bag-of-words vector — enough to cluster near-duplicates and resolve aliases.
    """

    name = "lite"

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def _vector(self, text: str) -> list[float]:
        from .text import segment

        vec = [0.0] * self.dim
        for tok in segment(text, drop_stopwords=True):
            h = hashlib.blake2b(tok.encode("utf-8"), digest_size=8).digest()
            idx = int.from_bytes(h[:4], "little") % self.dim
            sign = 1.0 if h[4] & 1 else -1.0
            vec[idx] += sign
        return _l2_normalize(vec)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t or "") for t in texts]


# --- local model backend ---------------------------------------------------


class LocalModelEmbedding:
    """sentence-transformers model (e.g. BAAI/bge-small-zh-v1.5). Lazy-loaded."""

    name = "local"

    def __init__(self, model: str) -> None:
        self._model_name = model
        self._model = None
        self._dim = 0

    def _ensure(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # type: ignore

            self._model = SentenceTransformer(self._model_name)
            self._dim = int(self._model.get_sentence_embedding_dimension())
        return self._model

    @property
    def dim(self) -> int:
        if not self._dim:
            self._ensure()
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._ensure()
        vecs = model.encode(list(texts), normalize_embeddings=True)
        return [list(map(float, v)) for v in vecs]


# --- api backend -----------------------------------------------------------


class APIEmbedding:
    """OpenAI-compatible embeddings endpoint. Lazy; reads key from config env."""

    name = "api"

    def __init__(self, url: str, api_key: str, dim: int = 1024) -> None:
        self._url = url
        self._key = api_key
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self._url:
            raise RuntimeError("embedding_api_url is not configured")
        req = urllib.request.Request(
            self._url,
            data=json.dumps({"input": list(texts)}).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._key}",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        vecs = [item["embedding"] for item in payload["data"]]
        if vecs:
            self.dim = len(vecs[0])
        return [_l2_normalize([float(x) for x in v]) for v in vecs]


def get_embedding_backend(config: Config) -> EmbeddingBackend:
    """Factory: build the configured embedding backend (lite fallback)."""
    choice = config.embedding_backend
    if choice == "local":
        return LocalModelEmbedding(config.embedding_model)
    if choice == "api":
        return APIEmbedding(config.embedding_api_url, config.api_key())
    return LiteEmbedding(config.embedding_dim)
