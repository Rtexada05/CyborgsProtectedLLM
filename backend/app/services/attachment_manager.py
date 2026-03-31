"""Attachment intake, validation, and analysis pipeline."""

from __future__ import annotations

from typing import Dict, List

from ..models.schemas import AttachmentRef
from .attachment_signal_analyzer import AttachmentSignalAnalyzer
from .attachment_text_extractor import AttachmentTextExtractor
from .attachment_validator import AttachmentValidator


class AttachmentManager:
    """Orchestrate attachment validation and security analysis."""

    def __init__(self):
        self.validator = AttachmentValidator()
        self.extractor = AttachmentTextExtractor()
        self.signal_analyzer = AttachmentSignalAnalyzer()

    async def inspect(self, attachments: List[AttachmentRef]) -> Dict[str, object]:
        results = []
        flagged_names = []
        blocked_names = []
        combined_signals = {
            "attachment_risk_suspected": False,
            "attachment_pattern_hits": [],
        }

        for attachment in attachments:
            validation = self.validator.validate(attachment)
            extraction = self.extractor.extract(attachment, validation.get("decoded_bytes", b""))
            analysis = await self.signal_analyzer.analyze(
                attachment,
                extraction.get("text_preview", ""),
                bool(extraction.get("metadata_only", False)),
            )

            errors = list(validation.get("errors", []))
            flags = list(analysis.get("flags", []))
            disposition = analysis.get("disposition", "allow")
            if errors:
                disposition = "block"
                flags.extend(errors)

            if disposition != "allow":
                combined_signals["attachment_risk_suspected"] = True
                combined_signals["attachment_pattern_hits"].extend(flags)

            if disposition == "flag":
                flagged_names.append(attachment.name)
            elif disposition == "block":
                flagged_names.append(attachment.name)
                blocked_names.append(attachment.name)

            results.append(
                {
                    "id": attachment.id,
                    "name": attachment.name,
                    "mime_type": attachment.mime_type,
                    "kind": attachment.kind,
                    "size_bytes": validation.get("size_bytes", 0),
                    "disposition": disposition,
                    "flags": flags,
                    "text_preview": extraction.get("text_preview", ""),
                    "metadata_only": bool(extraction.get("metadata_only", False)),
                    "extraction_status": extraction.get("extraction_status", "metadata_only"),
                    "extraction_method": extraction.get("extraction_method", "none"),
                    "extracted_chars": int(extraction.get("extracted_chars", 0) or 0),
                    "truncated": bool(extraction.get("truncated", False)),
                    "ocr_used": bool(extraction.get("ocr_used", False)),
                    "page_count": extraction.get("page_count"),
                    "extraction_reason": extraction.get("extraction_reason", ""),
                    "signals": analysis.get("signals", {}),
                }
            )

        return {
            "results": results,
            "flagged_names": flagged_names,
            "blocked_names": blocked_names,
            "combined_signals": combined_signals,
        }
