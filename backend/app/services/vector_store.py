"""Qdrant-oriented vector store with an in-memory fallback backend."""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..core.config import settings


@dataclass
class VectorPoint:
    point_id: str
    vector: List[float]
    payload: Dict[str, Any]


class VectorStore:
    """Vector search backend used by secure RAG services."""

    def __init__(self) -> None:
        self.provider = settings.VECTOR_DB_PROVIDER
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self._collections: Dict[str, Dict[str, VectorPoint]] = {}
        self._lock = asyncio.Lock()

    async def ensure_collection(self, vector_size: int) -> Dict[str, Any]:
        async with self._lock:
            collection = self._collections.get(self.collection_name)
            created = False
            if collection is None:
                self._collections[self.collection_name] = {}
                created = True
            return {
                "provider": self.provider,
                "backend": "in_memory_qdrant_compatible",
                "collection_name": self.collection_name,
                "vector_size": vector_size,
                "created": created,
            }

    async def upsert(self, points: List[VectorPoint]) -> int:
        async with self._lock:
            collection = self._collections.setdefault(self.collection_name, {})
            for point in points:
                collection[point.point_id] = point
            return len(points)

    async def delete_by_document_id(self, document_id: str) -> int:
        async with self._lock:
            collection = self._collections.setdefault(self.collection_name, {})
            to_delete = [
                point_id for point_id, point in collection.items()
                if point.payload.get("document_id") == document_id
            ]
            for point_id in to_delete:
                del collection[point_id]
            return len(to_delete)

    async def search(
        self,
        query_vector: List[float],
        limit: int,
        *,
        allowed_source_types: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        async with self._lock:
            collection = list(self._collections.setdefault(self.collection_name, {}).values())

        now = datetime.now()
        scored: List[Dict[str, Any]] = []
        for point in collection:
            payload = point.payload
            if not payload.get("retrieval_allowed", True):
                continue
            if payload.get("security_label") == "quarantined":
                continue
            expires_at = payload.get("expires_at")
            if isinstance(expires_at, str):
                try:
                    if datetime.fromisoformat(expires_at) <= now:
                        continue
                except ValueError:
                    pass
            if allowed_source_types and payload.get("source_type") not in allowed_source_types:
                continue
            owner_user_id = payload.get("owner_user_id")
            if payload.get("source_type") == "upload" and owner_user_id and owner_user_id != user_id:
                continue
            if document_ids and payload.get("document_id") not in document_ids:
                continue

            score = self._cosine_similarity(query_vector, point.vector)
            if score <= 0 and not document_ids:
                continue
            scored.append(
                {
                    "id": point.point_id,
                    "score": score if score > 0 else 0.0001,
                    "payload": dict(payload),
                }
            )

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:limit]

    async def list_sources(self) -> List[Dict[str, Any]]:
        async with self._lock:
            collection = self._collections.setdefault(self.collection_name, {})
            sources: Dict[str, Dict[str, Any]] = {}
            for point in collection.values():
                payload = point.payload
                document_id = payload.get("document_id")
                if not document_id:
                    continue
                source = sources.setdefault(
                    document_id,
                    {
                        "document_id": document_id,
                        "title": payload.get("title", document_id),
                        "source_type": payload.get("source_type", "static_doc"),
                        "security_label": payload.get("security_label", "trusted"),
                        "owner_user_id": payload.get("owner_user_id"),
                        "source_path": payload.get("source_path", ""),
                        "chunk_count": 0,
                        "scan_flags": [],
                        "retrieval_allowed": payload.get("retrieval_allowed", True),
                        "ingested_at": payload.get("ingested_at"),
                        "expires_at": payload.get("expires_at"),
                    },
                )
                source["chunk_count"] += 1
                for flag in payload.get("scan_flags", []):
                    if flag not in source["scan_flags"]:
                        source["scan_flags"].append(flag)

        return sorted(sources.values(), key=lambda item: (item["source_type"], item["document_id"]))

    async def get_stats(self) -> Dict[str, Any]:
        sources = await self.list_sources()
        point_count = sum(source["chunk_count"] for source in sources)
        return {
            "provider": self.provider,
            "backend": "in_memory_qdrant_compatible",
            "collection_name": self.collection_name,
            "point_count": point_count,
            "source_count": len(sources),
            "quarantined_source_count": len([source for source in sources if source["security_label"] == "quarantined"]),
        }

    @staticmethod
    def _cosine_similarity(left: List[float], right: List[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0

        numerator = sum(l * r for l, r in zip(left, right))
        left_norm = math.sqrt(sum(l * l for l in left))
        right_norm = math.sqrt(sum(r * r for r in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)


shared_vector_store = VectorStore()
