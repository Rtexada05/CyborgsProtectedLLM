"""Attachment security analysis."""

from __future__ import annotations

import re
from typing import Dict, List

from ..models.schemas import AttachmentRef
from .input_content_checker import InputContentChecker


class AttachmentSignalAnalyzer:
    """Analyze extracted attachment text and metadata for adversarial intent."""

    def __init__(self):
        self.input_checker = InputContentChecker()
        self.filename_patterns = [
            re.compile(r"(?i)(ignore|bypass|override|secret|credential|prompt)"),
            re.compile(r"(?i)(payroll|internal|confidential|token)"),
        ]

    async def analyze(self, attachment: AttachmentRef, text_preview: str, metadata_only: bool) -> Dict[str, object]:
        flags: List[str] = []
        disposition = "allow"
        signals: Dict[str, object] = {}

        if any(pattern.search(attachment.name) for pattern in self.filename_patterns):
            flags.append("suspicious_filename")

        if metadata_only and attachment.kind == "image":
            flags.append("image_metadata_only")

        if text_preview:
            signals = await self.input_checker.analyze(text_preview)
            if signals.get("prompt_injection_suspected"):
                flags.append("prompt_injection_in_attachment")
            if signals.get("encoding_obfuscation"):
                flags.append("encoded_content_in_attachment")
            if signals.get("tool_abuse_suspected"):
                flags.append("tool_directive_in_attachment")

        if "prompt_injection_in_attachment" in flags or "tool_directive_in_attachment" in flags:
            disposition = "block"
        elif flags:
            disposition = "flag"

        return {
            "disposition": disposition,
            "flags": flags,
            "signals": signals,
        }
