"""RAG Manager - handles retrieval-augmented generation context."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Dict, List


class RAGManager:
    """Retrieve context from a small local benign and poisoned corpus."""

    def __init__(self):
        self.data_root = Path(__file__).resolve().parent.parent / "data" / "rag"
        self.documents = self._load_documents()
        self.context_patterns = [
            r"(?i)use context[:\s]+(.+)",
            r"(?i)based on[:\s]+(.+)",
            r"(?i)refer to[:\s]+(.+)",
            r"(?i)context[:\s]+(.+)",
            r"(?i)use docs[:\s]+(.+)",
        ]
        self.compiled_patterns = [re.compile(pattern) for pattern in self.context_patterns]

    def _load_documents(self) -> List[Dict[str, str]]:
        docs: List[Dict[str, str]] = []
        for category in ("benign", "poisoned"):
            directory = self.data_root / category
            if not directory.exists():
                continue
            for path in sorted(directory.glob("*.txt")):
                docs.append(
                    {
                        "doc_id": path.stem,
                        "category": category,
                        "source": str(path.relative_to(self.data_root)),
                        "content": path.read_text(encoding="utf-8", errors="replace"),
                    }
                )
        return docs

    async def retrieve_context(self, prompt: str) -> Dict[str, Any]:
        """Retrieve context in a canonical shape with contexts + metadata."""

        context_keywords = self._extract_context_keywords(prompt)
        if not context_keywords:
            return {
                "contexts": [],
                "metadata": {
                    "total_contexts": 0,
                    "retrieval_method": "keyword_overlap",
                    "keywords_used": [],
                },
            }

        prompt_terms = {term.lower() for term in context_keywords}
        scored_docs = []
        lowered_prompt = prompt.lower()
        for doc in self.documents:
            doc_terms = set(re.findall(r"[a-zA-Z0-9_']+", doc["content"].lower()))
            overlap = len(prompt_terms & doc_terms)
            if doc["doc_id"] in lowered_prompt:
                overlap += 3
            if overlap > 0:
                scored_docs.append((overlap, doc))

        scored_docs.sort(key=lambda item: item[0], reverse=True)
        contexts = [
            {
                "keyword": doc["doc_id"],
                "content": doc["content"],
                "source": doc["source"],
                "relevance_score": round(score / max(len(prompt_terms), 1), 2),
                "category": doc["category"],
            }
            for score, doc in scored_docs[:3]
        ]

        return {
            "contexts": contexts,
            "metadata": {
                "total_contexts": len(contexts),
                "retrieval_method": "keyword_overlap",
                "keywords_used": context_keywords,
            },
        }

    def _extract_context_keywords(self, prompt: str) -> List[str]:
        """Extract context keywords from prompt."""

        keywords = []
        for pattern in self.compiled_patterns:
            matches = pattern.findall(prompt)
            for match in matches:
                cleaned = re.sub(r"[^\w\s]", " ", match).strip()
                words = [word.strip() for word in cleaned.split() if word.strip()]
                keywords.extend(words[:4])

        if "malicious_context" in prompt.lower():
            keywords.append("malicious_context")

        unique_keywords = list(dict.fromkeys(keywords))
        return unique_keywords[:6]

    async def search_contexts(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for contexts based on a query."""

        query_lower = query.lower()
        results = []
        for doc in self.documents:
            if doc["doc_id"] in query_lower or any(word in query_lower for word in doc["content"].lower().split()[:20]):
                results.append(
                    {
                        "keyword": doc["doc_id"],
                        "content": doc["content"],
                        "source": doc["source"],
                        "relevance_score": 0.7,
                    }
                )

        return results[:limit]

    async def validate_context_request(self, prompt: str) -> Dict[str, Any]:
        """Validate if context request is legitimate."""

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

    async def should_retrieve(self, prompt: str) -> bool:
        """Determine if RAG context should be retrieved."""

        rag_triggers = [
            "use context:",
            "use docs:",
            "from documents",
            "based on context",
            "refer to",
            "malicious_context",
        ]
        prompt_lower = prompt.lower()
        return any(trigger in prompt_lower for trigger in rag_triggers)
