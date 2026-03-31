"""Attachment validation helpers."""

from __future__ import annotations

import base64
from typing import Dict

from ..models.schemas import AttachmentRef


class AttachmentValidator:
    """Validate attachment metadata before deeper inspection."""

    _ALLOWED_MIME_TYPES = {
        "image/png",
        "image/jpeg",
        "image/webp",
        "text/plain",
        "text/csv",
        "application/json",
        "application/pdf",
    }
    _MAX_BYTES = 1_500_000

    def validate(self, attachment: AttachmentRef) -> Dict[str, object]:
        errors = []
        size_bytes = 0

        if attachment.mime_type not in self._ALLOWED_MIME_TYPES:
            errors.append("unsupported_mime_type")

        if attachment.kind == "image" and not attachment.mime_type.startswith("image/"):
            errors.append("kind_mime_mismatch")
        if attachment.kind == "file" and attachment.mime_type.startswith("image/"):
            errors.append("kind_mime_mismatch")

        if attachment.content_b64:
            try:
                decoded = base64.b64decode(attachment.content_b64, validate=True)
                size_bytes = len(decoded)
            except Exception:
                errors.append("invalid_base64")
                decoded = b""
            if size_bytes > self._MAX_BYTES:
                errors.append("attachment_too_large")
        else:
            decoded = b""

        return {
            "valid": not errors,
            "errors": errors,
            "size_bytes": size_bytes,
            "decoded_bytes": decoded,
        }
