"""LLM Service - interfaces with language models and authorized tools."""

from __future__ import annotations

import asyncio
import hashlib
import json
import urllib.error
import urllib.request
from typing import List, Dict, Any, Optional

from ..core.config import settings
from .tool_plugins import build_default_tool_executor


class LLMService:
    """Service for interacting with language models."""

    def __init__(self):
        self.model_name = settings.HF_MODEL_NAME
        self.api_key = settings.API_KEY
        self.tool_executor = build_default_tool_executor()

    async def generate_response(
        self,
        prompt: str,
        rag_context: Optional[Dict[str, Any]] = None,
        requested_tools: Optional[List[str]] = None,
        authorized_tools: Optional[List[str]] = None,
    ) -> str:
        """Generate a response using a real backend when available, else deterministic mock."""

        requested_tools = requested_tools or []
        authorized_tools = authorized_tools or []

        tool_execution = await self.tool_executor.execute_authorized_tools(
            prompt=prompt,
            requested_tools=requested_tools,
            authorized_tools=authorized_tools,
        )

        if self.api_key:
            real_response = await self._call_hf_api(
                prompt=prompt,
                rag_context=rag_context,
                tool_results=tool_execution.get("results", {}),
            )
            if real_response:
                return real_response

        return await self._generate_deterministic_response(
            prompt=prompt,
            rag_context=rag_context,
            tool_results=tool_execution.get("results", {}),
            tool_audit=tool_execution.get("audit", []),
        )

    async def _generate_deterministic_response(
        self,
        prompt: str,
        rag_context: Optional[Dict[str, Any]],
        tool_results: Dict[str, Any],
        tool_audit: List[Dict[str, Any]],
    ) -> str:
        """Secure deterministic fallback response for evaluation stability."""

        canonical_payload = json.dumps(
            {
                "prompt": prompt,
                "rag_context": rag_context or {},
                "tool_results": tool_results,
                "tool_audit": tool_audit,
            },
            sort_keys=True,
            ensure_ascii=True,
        )
        digest = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()[:12]

        audit_summary = ", ".join(f"{entry['tool_name']}:{entry['status']}" for entry in tool_audit) or "none"
        return (
            f"[deterministic-backend:{self.model_name}] "
            f"response_id={digest}; "
            f"tools={audit_summary}; "
            f"prompt_preview={prompt[:120]}"
        )

    async def validate_model_availability(self) -> Dict[str, Any]:
        """Check if the language model backend is available."""

        return {
            "available": True,
            "model_name": self.model_name,
            "status": "real_backend" if self.api_key else "deterministic_mock",
            "message": "Hugging Face backend configured" if self.api_key else "Deterministic mock active",
        }

    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model backend."""

        return {
            "model_name": self.model_name,
            "provider": "Hugging Face Inference API" if self.api_key else "Deterministic mock",
            "status": "ready",
            "capabilities": [
                "text generation",
                "authorized tool execution",
                "audited deterministic fallback",
            ],
        }

    async def estimate_tokens(self, text: str) -> int:
        word_count = len(text.split())
        char_count = len(text)
        token_estimate = max(word_count * 1.3, char_count / 4)
        return int(token_estimate)

    async def truncate_to_max_tokens(self, text: str, max_tokens: int) -> str:
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "... (truncated)"

    async def _call_hf_api(
        self,
        prompt: str,
        rag_context: Optional[Dict[str, Any]],
        tool_results: Dict[str, Any],
    ) -> Optional[str]:
        """Make an async call to Hugging Face Inference API with timeout and safe fallback."""

        endpoint = f"https://api-inference.huggingface.co/models/{self.model_name}"
        combined_prompt = prompt
        if rag_context:
            combined_prompt = f"Context: {json.dumps(rag_context, sort_keys=True)}\n\n{prompt}"
        if tool_results:
            combined_prompt = f"{combined_prompt}\n\nTool results: {json.dumps(tool_results, sort_keys=True)}"

        payload = json.dumps({
            "inputs": combined_prompt,
            "parameters": {"max_new_tokens": 120, "return_full_text": False},
        }).encode("utf-8")

        def _request() -> Optional[str]:
            req = urllib.request.Request(
                endpoint,
                data=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                raw = json.loads(response.read().decode("utf-8"))
            if isinstance(raw, list) and raw and isinstance(raw[0], dict):
                return raw[0].get("generated_text")
            return None

        try:
            return await asyncio.to_thread(_request)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None
