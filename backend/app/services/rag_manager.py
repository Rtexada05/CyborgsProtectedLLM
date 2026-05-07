"""Secure retrieval manager backed by a vector store."""

from __future__ import annotations

import asyncio
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from ..core.config import settings
from .embedding_service import shared_embedding_service
from .rag_content_validator import RAGContentValidator
from .vector_store import VectorPoint, shared_vector_store


class RAGManager:
    """Manage corpus ingestion and secure retrieval."""

    def __init__(self) -> None:
        self.data_root = Path(__file__).resolve().parent.parent / "data" / "rag"
        self.embedding_service = shared_embedding_service
        self.vector_store = shared_vector_store
        self.validator = RAGContentValidator()
        self._bootstrap_lock = asyncio.Lock()
        self._bootstrapped = False
        self._source_records: Dict[str, Dict[str, Any]] = {}
        self._last_indexed_at = datetime.now().isoformat()
        self._warnings: List[str] = []
        self._context_patterns = [
            re.compile(pattern)
            for pattern in (
                r"(?i)use context[:\s]+(.+)",
                r"(?i)based on[:\s]+(.+)",
                r"(?i)refer to[:\s]+(.+)",
                r"(?i)context[:\s]+(.+)",
                r"(?i)use docs[:\s]+(.+)",
                r"(?i)summarize (?:the )?(?:uploaded|attached|document|docs?)",
                r"(?i)according to (?:the )?(?:document|docs?|attachment)",
            )
        ]

    async def bootstrap(self, force: bool = False) -> Dict[str, Any]:
        """Initialize collection and ingest static corpus."""

        async with self._bootstrap_lock:
            if self._bootstrapped and not force:
                return await self.get_status()

            self._warnings = []
            self._source_records = {}
            await self.vector_store.ensure_collection(self.embedding_service.dimension)
            await self._ingest_static_directory(self.data_root / "trusted", source_label="trusted")
            await self._ingest_static_directory(self.data_root / "benign", source_label="trusted")
            await self._ingest_static_directory(self.data_root / "poisoned", source_label="quarantined")
            self._last_indexed_at = datetime.now().isoformat()
            self._bootstrapped = True
            return await self.get_status()

    async def reindex(self) -> Dict[str, Any]:
        """Rebuild the static index."""

        self._bootstrapped = False
        return await self.bootstrap(force=True)

    def reset(self) -> None:
        """Reset in-memory source metadata for tests."""

        self._bootstrapped = False
        self._source_records = {}
        self._last_indexed_at = datetime.now().isoformat()
        self._warnings = []
        self.vector_store._collections = {}

    async def get_status(self) -> Dict[str, Any]:
        if not self._bootstrapped:
            await self.bootstrap()
        stats = await self.vector_store.get_stats()
        return {
            "enabled": settings.RAG_ENABLED,
            **stats,
            "embedding": self.embedding_service.describe(),
            "indexed_at": self._last_indexed_at,
            "warnings": list(dict.fromkeys(self._warnings)),
        }

    async def list_sources(self) -> List[Dict[str, Any]]:
        if not self._bootstrapped:
            await self.bootstrap()
        store_sources = await self.vector_store.list_sources()
        for source in store_sources:
            record = self._source_records.get(source["document_id"])
            if record:
                source.update({
                    "scan_flags": list(dict.fromkeys(record.get("scan_flags", []) + source.get("scan_flags", []))),
                    "retrieval_allowed": record.get("retrieval_allowed", source.get("retrieval_allowed", True)),
                })
        return store_sources

    async def ingest_attachment_contexts(
        self,
        *,
        user_id: str,
        trace_id: str,
        attachment_results: Iterable[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Index user uploads for same-user retrieval."""

        if not settings.RAG_ENABLE_UPLOAD_INDEXING:
            return {"indexed_documents": [], "warnings": ["upload_indexing_disabled"]}

        await self.bootstrap()
        indexed_documents: List[str] = []
        warnings: List[str] = []

        for attachment in attachment_results:
            disposition = attachment.get("disposition", "allow")
            text_preview = str(attachment.get("text_preview", "")).strip()
            if disposition == "block":
                continue
            if not text_preview:
                continue

            document_id = f"upload:{user_id}:{attachment.get('id')}"
            source_title = str(attachment.get("name", document_id))
            scan_flags = list(dict.fromkeys(attachment.get("flags", [])))
            source_label = "quarantined" if self._scan_requires_quarantine(text_preview, scan_flags) else "user_supplied"

            await self._index_document(
                document_id=document_id,
                text=text_preview,
                source_type="upload",
                title=source_title,
                source_path=f"upload/{attachment.get('id')}",
                mime_type=str(attachment.get("mime_type", "application/octet-stream")),
                security_label=source_label,
                owner_user_id=user_id,
                trace_id=trace_id,
                expires_at=(datetime.now() + timedelta(seconds=settings.RAG_UPLOAD_TTL_SECONDS)).isoformat(),
                initial_scan_flags=scan_flags,
            )
            indexed_documents.append(document_id)
            if source_label == "quarantined":
                warnings.append(f"quarantined_upload:{document_id}")

        return {"indexed_documents": indexed_documents, "warnings": warnings}

    async def retrieve_context(
        self,
        *,
        prompt: str,
        user_id: str,
        rag_scope: str = "default",
        rag_document_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Retrieve, filter, and validate context for a prompt."""

        await self.bootstrap()
        explicit_document_ids = [doc_id for doc_id in (rag_document_ids or []) if doc_id]
        requested_ids = list(dict.fromkeys(explicit_document_ids + self._extract_document_ids(prompt)))
        source_types = self._resolve_source_types(rag_scope)
        cross_user_attempt = any(self._is_cross_user_document(doc_id, user_id) for doc_id in requested_ids)
        quarantined_request = any(self._source_records.get(doc_id, {}).get("security_label") == "quarantined" for doc_id in requested_ids)

        if not settings.RAG_ENABLED:
            return self._empty_retrieval(prompt, warnings=["rag_disabled"])

        query_vector = await self.embedding_service.embed_query(prompt)
        search_hits = await self.vector_store.search(
            query_vector,
            limit=max(settings.RAG_TOP_K, settings.RAG_MAX_CHUNKS_TO_MODEL),
            allowed_source_types=source_types,
            user_id=user_id,
            document_ids=requested_ids or None,
        )

        contexts = []
        warnings: List[str] = []
        candidate_sources = set()
        used_sources: List[str] = []
        per_source_counts: Dict[str, int] = {}
        dropped_chunks = 0
        sanitized_chunks = 0
        quarantine_sources: List[str] = []
        remaining_chars = settings.RAG_MAX_CONTEXT_CHARS

        for hit in search_hits:
            payload = dict(hit.get("payload", {}))
            document_id = payload.get("document_id")
            if not document_id:
                continue
            candidate_sources.add(document_id)

            if per_source_counts.get(document_id, 0) >= settings.RAG_MAX_CHUNKS_PER_SOURCE:
                dropped_chunks += 1
                warnings.append("source_chunk_cap_reached")
                continue

            payload["relevance_score"] = round(float(hit.get("score", 0.0)), 4)
            validation = await self.validator.validate_chunk(payload)
            if validation["disposition"] == "drop":
                dropped_chunks += 1
                warnings.extend(validation["issues"])
                if validation["quarantine_source"] and document_id:
                    quarantine_sources.append(document_id)
                continue

            content = validation["content"] if validation["disposition"] == "sanitize" else payload.get("content", "")
            if validation["disposition"] == "sanitize":
                sanitized_chunks += 1
                warnings.extend(validation["issues"])

            if remaining_chars <= 0:
                dropped_chunks += 1
                warnings.append("context_budget_exceeded")
                continue

            chunk_text = str(content)[:remaining_chars]
            remaining_chars -= len(chunk_text)
            if not chunk_text.strip():
                dropped_chunks += 1
                continue

            per_source_counts[document_id] = per_source_counts.get(document_id, 0) + 1
            if document_id not in used_sources:
                used_sources.append(document_id)

            contexts.append(
                {
                    "keyword": payload.get("title", document_id),
                    "document_id": document_id,
                    "content": chunk_text,
                    "source": payload.get("source_path", ""),
                    "relevance_score": payload["relevance_score"],
                    "source_type": payload.get("source_type", "static_doc"),
                    "security_label": payload.get("security_label", "user_supplied"),
                    "chunk_id": payload.get("chunk_id"),
                    "chunk_index": payload.get("chunk_index", 0),
                    "owner_user_id": payload.get("owner_user_id"),
                }
            )

            if len(contexts) >= settings.RAG_MAX_CHUNKS_TO_MODEL:
                break

        metadata = {
            "total_contexts": len(contexts),
            "retrieval_method": "local_vector_hashing",
            "keywords_used": self._extract_context_keywords(prompt),
            "candidate_count": len(search_hits),
            "sources_considered": len(candidate_sources),
            "sources_used": used_sources,
            "chunks_retrieved": len(search_hits),
            "chunks_used": len(contexts),
            "chunks_dropped": dropped_chunks,
            "chunk_sanitized_count": sanitized_chunks,
            "warnings": list(dict.fromkeys(warnings)),
            "cross_user_access_blocked": cross_user_attempt,
            "quarantined_request": quarantined_request,
            "quarantine_sources": list(dict.fromkeys(quarantine_sources)),
            "no_safe_context_found": bool(search_hits) and not contexts,
        }
        return {"contexts": contexts, "metadata": metadata}

    async def search_contexts(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search contexts directly for debug/admin purposes."""

        result = await self.retrieve_context(prompt=query, user_id="", rag_scope="static_only")
        return result["contexts"][:limit]

    async def validate_context_request(self, prompt: str) -> Dict[str, Any]:
        """Validate whether a retrieval request looks legitimate."""

        suspicious_patterns = [
            r"(?i)(all|every).*(context|data|information)",
            r"(?i)(admin|system|internal).*(context|data)",
            r"(?i)(bypass|override).*(context|security)",
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, prompt):
                return {
                    "is_valid": False,
                    "reason": "Suspicious context request pattern detected",
                    "risk_level": "HIGH",
                }

        if len(prompt) > 2000:
            return {
                "is_valid": False,
                "reason": "Context request too long",
                "risk_level": "MEDIUM",
            }

        return {
            "is_valid": True,
            "reason": "Context request appears legitimate",
            "risk_level": "LOW",
        }

    async def should_retrieve(self, prompt: str, rag_enabled: bool = True) -> bool:
        """Determine whether retrieval should run for a prompt."""

        if not settings.RAG_ENABLED or not rag_enabled:
            return False
        lowered_prompt = prompt.lower()
        if any(trigger in lowered_prompt for trigger in ("use context:", "use docs:", "from documents", "based on context", "refer to", "according to the document", "summarize the attached")):
            return True
        return any(pattern.search(prompt) for pattern in self._context_patterns)

    def _empty_retrieval(self, prompt: str, warnings: Optional[List[str]] = None) -> Dict[str, Any]:
        return {
            "contexts": [],
            "metadata": {
                "total_contexts": 0,
                "retrieval_method": "disabled",
                "keywords_used": self._extract_context_keywords(prompt),
                "candidate_count": 0,
                "sources_considered": 0,
                "sources_used": [],
                "chunks_retrieved": 0,
                "chunks_used": 0,
                "chunks_dropped": 0,
                "chunk_sanitized_count": 0,
                "warnings": warnings or [],
                "cross_user_access_blocked": False,
                "quarantined_request": False,
                "quarantine_sources": [],
                "no_safe_context_found": False,
            },
        }

    async def _ingest_static_directory(self, directory: Path, *, source_label: str) -> None:
        if not directory.exists():
            return

        for path in sorted(directory.glob("*.txt")):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                self._warnings.append(f"read_failed:{path.name}:{exc}")
                continue

            await self._index_document(
                document_id=path.stem,
                text=text,
                source_type="static_doc",
                title=path.stem,
                source_path=str(path.relative_to(self.data_root)),
                mime_type="text/plain",
                security_label=source_label,
                owner_user_id=None,
                trace_id=None,
                expires_at=None,
                initial_scan_flags=[],
            )

    async def _index_document(
        self,
        *,
        document_id: str,
        text: str,
        source_type: str,
        title: str,
        source_path: str,
        mime_type: str,
        security_label: str,
        owner_user_id: Optional[str],
        trace_id: Optional[str],
        expires_at: Optional[str],
        initial_scan_flags: List[str],
    ) -> None:
        normalized_text = self._normalize_text(text)
        deleted = await self.vector_store.delete_by_document_id(document_id)
        if deleted and document_id in self._source_records:
            self._source_records.pop(document_id, None)

        scan_flags = list(dict.fromkeys(initial_scan_flags + self._scan_document_flags(normalized_text)))
        effective_label = security_label
        if self._scan_requires_quarantine(normalized_text, scan_flags):
            effective_label = "quarantined" if settings.RAG_QUARANTINE_ON_POISON_SCAN else security_label

        chunks = self._chunk_text(normalized_text)
        if not chunks:
            self._warnings.append(f"empty_document:{document_id}")
            return

        chunk_embedding_inputs = [f"{title}\n{document_id}\n{chunk_text}" for chunk_text in chunks]
        vectors = await self.embedding_service.embed_documents(chunk_embedding_inputs)
        document_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
        ingested_at = datetime.now().isoformat()
        points: List[VectorPoint] = []

        for index, (chunk_text, vector) in enumerate(zip(chunks, vectors)):
            chunk_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
            chunk_id = f"{document_id}:{index}"
            payload = {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "source_type": source_type,
                "source_path": source_path,
                "title": title,
                "mime_type": mime_type,
                "owner_user_id": owner_user_id,
                "trace_id": trace_id,
                "security_label": effective_label,
                "chunk_index": index,
                "token_count_estimate": len(chunk_text.split()),
                "content_hash": chunk_hash,
                "document_hash": document_hash,
                "ingested_at": ingested_at,
                "retrieval_allowed": effective_label != "quarantined",
                "expires_at": expires_at,
                "scan_flags": scan_flags,
                "content": chunk_text,
            }
            points.append(VectorPoint(point_id=chunk_id, vector=vector, payload=payload))

        await self.vector_store.upsert(points)
        self._source_records[document_id] = {
            "document_id": document_id,
            "title": title,
            "source_type": source_type,
            "security_label": effective_label,
            "owner_user_id": owner_user_id,
            "source_path": source_path,
            "chunk_count": len(points),
            "scan_flags": scan_flags,
            "retrieval_allowed": effective_label != "quarantined",
            "ingested_at": ingested_at,
            "expires_at": expires_at,
        }

    def _chunk_text(self, text: str) -> List[str]:
        paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
        if not paragraphs:
            paragraphs = [text.strip()] if text.strip() else []

        chunks: List[str] = []
        current = ""
        max_chars = 900
        overlap_chars = 120

        for paragraph in paragraphs:
            if len(current) + len(paragraph) + 2 <= max_chars:
                current = f"{current}\n\n{paragraph}".strip()
                continue

            if current:
                chunks.append(current)
                overlap = current[-overlap_chars:] if len(current) > overlap_chars else current
                current = f"{overlap}\n\n{paragraph}".strip()
            else:
                current = paragraph[:max_chars]
                remainder = paragraph[max_chars:]
                while remainder:
                    chunks.append(current)
                    current = remainder[:max_chars]
                    remainder = remainder[max_chars - overlap_chars:] if len(remainder) > max_chars else ""

        if current:
            chunks.append(current)

        return chunks[: max(settings.RAG_TOP_K * 3, settings.RAG_MAX_CHUNKS_TO_MODEL * 2)]

    def _normalize_text(self, text: str) -> str:
        cleaned = text.replace("\x00", " ")
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    def _scan_document_flags(self, text: str) -> List[str]:
        flags = []
        lowered = text.lower()
        if "ignore previous instructions" in lowered:
            flags.append("prompt_override_text")
        if "developer message" in lowered or "system prompt" in lowered:
            flags.append("hidden_instruction_reference")
        if "encodedcommand" in lowered or re.search(r'\\[uU][0-9a-fA-F]{4}', text):
            flags.append("encoding_obfuscation")
        if "password" in lowered or "secret" in lowered:
            flags.append("secret_like_content")
        return flags

    def _scan_requires_quarantine(self, text: str, scan_flags: List[str]) -> bool:
        lowered = text.lower()
        high_risk_flags = {"prompt_override_text", "hidden_instruction_reference", "encoding_obfuscation"}
        return bool(high_risk_flags.intersection(scan_flags)) or "malicious_context" in lowered

    def _resolve_source_types(self, rag_scope: str) -> Optional[List[str]]:
        if rag_scope == "static_only":
            return ["static_doc"]
        if rag_scope == "user_uploads_only":
            return ["upload"]
        return None

    def _extract_context_keywords(self, prompt: str) -> List[str]:
        keywords = []
        for pattern in self._context_patterns:
            matches = pattern.findall(prompt)
            if isinstance(matches, str):
                matches = [matches]
            for match in matches:
                cleaned = re.sub(r"[^\w\s:-]", " ", str(match)).strip()
                words = [word.strip(": ").strip() for word in cleaned.split() if word.strip()]
                keywords.extend(words[:4])

        if "malicious_context" in prompt.lower():
            keywords.append("malicious_context")
        return list(dict.fromkeys(keywords))[:8]

    def _extract_document_ids(self, prompt: str) -> List[str]:
        lowered_prompt = prompt.lower()
        matched = []
        for document_id in self._source_records:
            if document_id.lower() in lowered_prompt:
                matched.append(document_id)
        return matched

    def _is_cross_user_document(self, document_id: str, user_id: str) -> bool:
        record = self._source_records.get(document_id, {})
        owner_user_id = record.get("owner_user_id")
        return bool(owner_user_id and owner_user_id != user_id)


shared_rag_manager = RAGManager()
