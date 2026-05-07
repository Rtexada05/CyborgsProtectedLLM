"""Local embedding service for deterministic semantic retrieval."""

from __future__ import annotations

import asyncio
import hashlib
import math
import re
from typing import Iterable, List

from ..core.config import settings


class EmbeddingService:
    """Generate stable local embeddings without external dependencies."""

    def __init__(self) -> None:
        self.provider = settings.EMBEDDING_PROVIDER
        self.model_name = settings.EMBEDDING_MODEL_NAME
        self.dimension = settings.EMBEDDING_DIMENSION
        self.batch_size = settings.EMBEDDING_BATCH_SIZE
        self.timeout_seconds = settings.EMBEDDING_TIMEOUT_SECONDS

    async def embed_query(self, text: str) -> List[float]:
        """Embed a single query string."""

        return await asyncio.wait_for(asyncio.to_thread(self._embed_text, text), timeout=self.timeout_seconds)

    async def embed_documents(self, texts: Iterable[str]) -> List[List[float]]:
        """Embed a batch of document chunks."""

        text_list = list(texts)
        return await asyncio.wait_for(
            asyncio.to_thread(lambda: [self._embed_text(text) for text in text_list]),
            timeout=max(self.timeout_seconds, 1.0) * max(1, math.ceil(len(text_list) / max(self.batch_size, 1))),
        )

    def describe(self) -> dict:
        return {
            "provider": self.provider,
            "model_name": self.model_name,
            "dimension": self.dimension,
            "batch_size": self.batch_size,
            "timeout_seconds": self.timeout_seconds,
        }

    def _embed_text(self, text: str) -> List[float]:
        tokens = re.findall(r"[a-zA-Z0-9_']+", text.lower())
        vector = [0.0] * self.dimension

        if not tokens:
            return vector

        for index, token in enumerate(tokens):
            digest = hashlib.sha256(f"{token}:{index % 7}".encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            weight = 1.0 + min(len(token), 12) / 20.0
            vector[bucket] += sign * weight

            secondary_bucket = int.from_bytes(digest[5:9], "big") % self.dimension
            vector[secondary_bucket] += sign * 0.35

        norm = math.sqrt(sum(component * component for component in vector))
        if norm == 0:
            return vector
        return [component / norm for component in vector]


shared_embedding_service = EmbeddingService()
