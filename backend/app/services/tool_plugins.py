"""Tool plugin interfaces and secure execution wrappers."""

from __future__ import annotations

import ast
import asyncio
import os
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ToolAuditEntry:
    """Audit record for a single tool execution attempt."""

    tool_name: str
    status: str
    reason: str
    duration_ms: int


class ToolPlugin(ABC):
    """Concrete interface for tool plugins."""

    name: str

    @abstractmethod
    async def execute(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run the tool and return a serializable result."""


class CalculatorPlugin(ToolPlugin):
    """Deterministic calculator with constrained expression evaluation."""

    name = "calculator"

    _ALLOWED_OPS = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Num,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.Mod,
        ast.USub,
        ast.UAdd,
        ast.Constant,
        ast.Load,
    )

    def _extract_expression(self, prompt: str) -> Optional[str]:
        match = re.search(r"([-+*/%()\d\s\.]{3,})", prompt)
        return match.group(1).strip() if match else None

    def _safe_eval(self, expression: str) -> float:
        tree = ast.parse(expression, mode="eval")
        for node in ast.walk(tree):
            if not isinstance(node, self._ALLOWED_OPS):
                raise ValueError("Unsupported expression")
        return float(eval(compile(tree, "<calculator>", "eval"), {"__builtins__": {}}, {}))

    async def execute(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        expression = self._extract_expression(prompt)
        if not expression:
            return {"ok": False, "error": "No arithmetic expression found"}

        try:
            value = self._safe_eval(expression)
            return {"ok": True, "expression": expression, "result": value}
        except Exception as exc:
            return {"ok": False, "expression": expression, "error": str(exc)}


class FileReaderPlugin(ToolPlugin):
    """File reader restricted to approved repository paths."""

    name = "file_reader"

    def __init__(self, allowed_root: Path):
        self.allowed_root = allowed_root.resolve()

    def _extract_path(self, prompt: str) -> Optional[Path]:
        quoted = re.search(r'["\']([^"\']+\.[\w]+)["\']', prompt)
        if quoted:
            return Path(quoted.group(1))

        match = re.search(r"(?:file|open|read)\s+([\w\-./]+)", prompt, flags=re.IGNORECASE)
        if not match:
            return None
        return Path(match.group(1))

    def _select_uploaded_attachment(self, prompt: str, context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not context:
            return None

        attachments = context.get("attachments", [])
        if not isinstance(attachments, list) or not attachments:
            return None

        prompt_lower = prompt.lower()
        for attachment in attachments:
            name = str(attachment.get("name", ""))
            if name and name.lower() in prompt_lower:
                return attachment

        # If the prompt is generic and a single safe attachment was uploaded, prefer it.
        if len(attachments) == 1:
            return attachments[0]

        return None

    async def execute(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        uploaded_attachment = self._select_uploaded_attachment(prompt, context)
        if uploaded_attachment is not None:
            text_preview = str(uploaded_attachment.get("text_preview", "")).strip()
            if text_preview:
                return {
                    "ok": True,
                    "source": "uploaded_attachment",
                    "name": uploaded_attachment.get("name", "uploaded_file"),
                    "mime_type": uploaded_attachment.get("mime_type", "application/octet-stream"),
                    "metadata_only": bool(uploaded_attachment.get("metadata_only", False)),
                    "extraction_status": uploaded_attachment.get("extraction_status", "metadata_only"),
                    "extraction_method": uploaded_attachment.get("extraction_method", "none"),
                    "extracted_chars": int(uploaded_attachment.get("extracted_chars", 0) or 0),
                    "truncated": bool(uploaded_attachment.get("truncated", False)),
                    "ocr_used": bool(uploaded_attachment.get("ocr_used", False)),
                    "page_count": uploaded_attachment.get("page_count"),
                    "extraction_reason": uploaded_attachment.get("extraction_reason", ""),
                    "content_preview": text_preview[:300],
                }
            return {
                "ok": False,
                "source": "uploaded_attachment",
                "name": uploaded_attachment.get("name", "uploaded_file"),
                "extraction_status": uploaded_attachment.get("extraction_status", "metadata_only"),
                "extraction_method": uploaded_attachment.get("extraction_method", "none"),
                "ocr_used": bool(uploaded_attachment.get("ocr_used", False)),
                "error": "Uploaded attachment could not be converted into readable text",
            }

        candidate = self._extract_path(prompt)
        if candidate is None:
            return {"ok": False, "error": "No file path found"}

        resolved = (self.allowed_root / candidate).resolve()
        if not str(resolved).startswith(str(self.allowed_root)):
            return {"ok": False, "error": "Path rejected by policy"}
        if not resolved.exists() or not resolved.is_file():
            return {"ok": False, "error": "File not found"}

        content = resolved.read_text(encoding="utf-8", errors="replace")
        return {
            "ok": True,
            "path": str(resolved.relative_to(self.allowed_root)),
            "content_preview": content[:300],
        }


class WriteFilePlugin(ToolPlugin):
    """Safe-deny plugin for file write attempts."""

    name = "write_file"

    async def execute(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "ok": False,
            "error": "File write operations are disabled by security policy",
        }


class WebFetchPlugin(ToolPlugin):
    """Network plugin with a strict domain allowlist."""

    name = "web"

    def __init__(self, allowed_domains: Optional[List[str]] = None):
        self.allowed_domains = allowed_domains or ["example.com"]

    def _extract_url(self, prompt: str) -> Optional[str]:
        match = re.search(r"https?://[^\s]+", prompt)
        return match.group(0) if match else None

    def _is_allowed(self, url: str) -> bool:
        try:
            host = urllib.parse.urlparse(url).hostname or ""
        except Exception:
            return False
        return any(host == domain or host.endswith(f".{domain}") for domain in self.allowed_domains)

    async def execute(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = self._extract_url(prompt)
        if not url:
            return {"ok": False, "error": "No URL found"}
        if not self._is_allowed(url):
            return {"ok": False, "error": "URL rejected by allowlist"}

        def _fetch() -> Dict[str, Any]:
            req = urllib.request.Request(url, headers={"User-Agent": "CyborgsProtectedLLM/1.0"})
            with urllib.request.urlopen(req, timeout=4) as response:
                body = response.read(400).decode("utf-8", errors="replace")
                return {"ok": True, "url": url, "status": response.status, "body_preview": body}

        try:
            return await asyncio.to_thread(_fetch)
        except urllib.error.URLError as exc:
            return {"ok": False, "url": url, "error": str(exc)}


class ExecuteCommandPlugin(ToolPlugin):
    """Safe-deny plugin for command execution attempts."""

    name = "execute_command"

    async def execute(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "ok": False,
            "error": "Command execution is disabled by security policy",
        }


class DatabasePlugin(ToolPlugin):
    """Read-only SQLite demo database plugin with allowlisted intents."""

    name = "database"

    def __init__(self):
        self.connection = sqlite3.connect(":memory:", check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._seed()

    def _seed(self) -> None:
        cursor = self.connection.cursor()
        cursor.executescript(
            """
            CREATE TABLE restaurant_popularity (
                brand TEXT PRIMARY KEY,
                popularity_rank INTEGER NOT NULL,
                global_locations INTEGER NOT NULL,
                notes TEXT NOT NULL
            );
            INSERT INTO restaurant_popularity (brand, popularity_rank, global_locations, notes) VALUES
                ('McDonald''s', 1, 41000, 'Globally recognized quick service restaurant with extensive footprint.'),
                ('Starbucks', 2, 38000, 'Large global coffee chain with strong brand recognition.'),
                ('Subway', 3, 36000, 'Widely distributed sandwich chain.');
            """
        )
        self.connection.commit()

    def _extract_brand(self, prompt: str) -> Optional[str]:
        prompt_lower = prompt.lower()
        for brand in ("McDonald's", "Starbucks", "Subway"):
            if brand.lower().replace("'", "") in prompt_lower.replace("'", ""):
                return brand
        return None

    async def execute(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        prompt_lower = prompt.lower()
        brand = self._extract_brand(prompt)
        cursor = self.connection.cursor()

        if brand and any(token in prompt_lower for token in ("how popular", "popularity", "popular", "rank")):
            row = cursor.execute(
                "SELECT brand, popularity_rank, global_locations, notes FROM restaurant_popularity WHERE brand = ?",
                (brand,),
            ).fetchone()
            if not row:
                return {"ok": False, "error": "Brand not found"}
            return {
                "ok": True,
                "intent": "popularity_lookup",
                "brand": row["brand"],
                "popularity_rank": row["popularity_rank"],
                "global_locations": row["global_locations"],
                "notes": row["notes"],
            }

        if any(token in prompt_lower for token in ("list restaurants", "show restaurants", "available brands")):
            rows = cursor.execute(
                "SELECT brand, popularity_rank, global_locations FROM restaurant_popularity ORDER BY popularity_rank ASC"
            ).fetchall()
            return {
                "ok": True,
                "intent": "list_brands",
                "rows": [dict(row) for row in rows],
            }

        return {
            "ok": False,
            "error": "Unsupported database request. Allowed intents are popularity lookup and listing available brands.",
        }


class ToolExecutor:
    """Executes tools with authorization checks and audited wrappers."""

    def __init__(self, plugins: List[ToolPlugin], default_timeout_s: float = 2.0):
        self.plugins = {plugin.name: plugin for plugin in plugins}
        self.default_timeout_s = default_timeout_s

    async def execute_authorized_tools(
        self,
        prompt: str,
        requested_tools: List[str],
        authorized_tools: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        audits: List[ToolAuditEntry] = []

        for tool_name in requested_tools:
            if tool_name not in authorized_tools:
                audits.append(ToolAuditEntry(tool_name=tool_name, status="denied", reason="not_authorized", duration_ms=0))
                continue

            plugin = self.plugins.get(tool_name)
            if not plugin:
                audits.append(ToolAuditEntry(tool_name=tool_name, status="denied", reason="plugin_not_registered", duration_ms=0))
                continue

            start = time.perf_counter()
            try:
                payload = await asyncio.wait_for(plugin.execute(prompt, context), timeout=self.default_timeout_s)
                duration_ms = int((time.perf_counter() - start) * 1000)
                results[tool_name] = payload
                audits.append(ToolAuditEntry(tool_name=tool_name, status="executed", reason="ok", duration_ms=duration_ms))
            except asyncio.TimeoutError:
                duration_ms = int((time.perf_counter() - start) * 1000)
                audits.append(ToolAuditEntry(tool_name=tool_name, status="blocked", reason="timeout", duration_ms=duration_ms))

        return {
            "results": results,
            "audit": [entry.__dict__ for entry in audits],
        }


def build_default_tool_executor() -> ToolExecutor:
    default_root = Path(__file__).resolve().parents[3]
    repo_root = Path(os.getenv("TOOL_FILE_ROOT", str(default_root))).resolve()
    plugins: List[ToolPlugin] = [
        CalculatorPlugin(),
        FileReaderPlugin(allowed_root=repo_root),
        WriteFilePlugin(),
        WebFetchPlugin(allowed_domains=["example.com", "www.example.com"]),
        ExecuteCommandPlugin(),
        DatabasePlugin(),
    ]
    return ToolExecutor(plugins)
