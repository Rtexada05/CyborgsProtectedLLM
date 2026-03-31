"""Attachment text extraction utilities."""

from __future__ import annotations

from io import BytesIO
import json
from typing import Dict, List, Optional, Tuple

from ..models.schemas import AttachmentRef

try:
    import fitz
except ImportError:  # pragma: no cover - dependency may be absent in some test environments
    fitz = None

try:
    import numpy as np
except ImportError:  # pragma: no cover - dependency may be absent in some test environments
    np = None

try:
    from PIL import Image, ImageOps, UnidentifiedImageError
except ImportError:  # pragma: no cover - dependency may be absent in some test environments
    Image = None
    ImageOps = None

    class UnidentifiedImageError(Exception):
        """Fallback error when Pillow is unavailable."""


try:
    from rapidocr_onnxruntime import RapidOCR
except ImportError:  # pragma: no cover - dependency may be absent in some test environments
    RapidOCR = None


class AttachmentTextExtractor:
    """Extract analyzable text previews from supported attachment types."""

    MAX_EXTRACTED_CHARS = 8_000
    MAX_PDF_PAGES = 10
    MIN_DIRECT_PDF_TEXT_CHARS = 120

    def __init__(self):
        self._ocr_engine = None

    def extract(self, attachment: AttachmentRef, decoded_bytes: bytes) -> Dict[str, object]:
        if not decoded_bytes:
            return self._metadata_only_result("no_payload")

        mime_type = attachment.mime_type
        if mime_type in {"text/plain", "text/csv"}:
            text = decoded_bytes.decode("utf-8", errors="replace")
            return self._text_result(
                text=text,
                extraction_method="plain_text",
                extraction_reason="plain_text_extracted",
            )

        if mime_type == "application/json":
            raw_text = decoded_bytes.decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw_text)
                normalized = json.dumps(parsed, sort_keys=True, ensure_ascii=False)
                reason = "json_text_normalized"
            except Exception:
                normalized = raw_text
                reason = "json_text_fallback"
            return self._text_result(
                text=normalized,
                extraction_method="json_text",
                extraction_reason=reason,
            )

        if mime_type == "application/pdf":
            direct_text, page_count, direct_reason = self._extract_pdf_text_direct(decoded_bytes)
            if len(direct_text) >= self.MIN_DIRECT_PDF_TEXT_CHARS:
                status = "partial" if page_count > self.MAX_PDF_PAGES else "success"
                reason = "pdf_page_limit_applied" if page_count > self.MAX_PDF_PAGES else direct_reason
                return self._text_result(
                    text=direct_text,
                    extraction_method="pdf_text",
                    extraction_reason=reason,
                    extraction_status=status,
                    page_count=page_count or None,
                )

            ocr_text, ocr_page_count, ocr_reason = self._extract_pdf_text_via_ocr(decoded_bytes)
            if ocr_text:
                status = "partial" if ocr_page_count > self.MAX_PDF_PAGES else "success"
                reason = "pdf_ocr_page_limit_applied" if ocr_page_count > self.MAX_PDF_PAGES else ocr_reason
                return self._text_result(
                    text=ocr_text,
                    extraction_method="pdf_ocr",
                    extraction_reason=reason,
                    extraction_status=status,
                    ocr_used=True,
                    page_count=ocr_page_count or page_count or None,
                )

            if direct_text:
                return self._text_result(
                    text=direct_text,
                    extraction_method="pdf_text",
                    extraction_reason=f"{direct_reason};ocr_fallback_unavailable:{ocr_reason}",
                    extraction_status="partial",
                    page_count=page_count or None,
                )

            return self._failed_result(
                extraction_reason=f"{direct_reason};ocr_fallback:{ocr_reason}",
                page_count=ocr_page_count or page_count or None,
            )

        if mime_type in {"image/png", "image/jpeg", "image/webp"}:
            image_text, page_count, image_reason = self._extract_image_text(decoded_bytes)
            if image_text:
                return self._text_result(
                    text=image_text,
                    extraction_method="image_ocr",
                    extraction_reason=image_reason,
                    ocr_used=True,
                    page_count=page_count,
                )
            return self._failed_result(
                extraction_reason=image_reason,
                ocr_used=True,
                page_count=page_count,
            )

        return self._metadata_only_result("unsupported_mime_type")

    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""
        normalized = text.replace("\x00", " ")
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.strip() for line in normalized.split("\n")]
        cleaned_lines = [line for line in lines if line]
        return "\n".join(cleaned_lines).strip()

    def _text_result(
        self,
        text: str,
        extraction_method: str,
        extraction_reason: str,
        extraction_status: str = "success",
        ocr_used: bool = False,
        page_count: Optional[int] = None,
    ) -> Dict[str, object]:
        normalized = self._normalize_text(text)
        if not normalized:
            return self._metadata_only_result(
                extraction_reason=extraction_reason,
                extraction_method=extraction_method,
                extraction_status="metadata_only",
                ocr_used=ocr_used,
                page_count=page_count,
            )

        extracted_chars = len(normalized)
        truncated = extracted_chars > self.MAX_EXTRACTED_CHARS
        status = "partial" if truncated and extraction_status == "success" else extraction_status
        return {
            "text_preview": normalized[: self.MAX_EXTRACTED_CHARS],
            "metadata_only": False,
            "extraction_status": status,
            "extraction_method": extraction_method,
            "extracted_chars": extracted_chars,
            "truncated": truncated,
            "ocr_used": ocr_used,
            "page_count": page_count,
            "extraction_reason": extraction_reason,
        }

    def _failed_result(
        self,
        extraction_reason: str,
        ocr_used: bool = False,
        page_count: Optional[int] = None,
    ) -> Dict[str, object]:
        return self._metadata_only_result(
            extraction_reason=extraction_reason,
            extraction_method="none",
            extraction_status="failed",
            ocr_used=ocr_used,
            page_count=page_count,
        )

    def _metadata_only_result(
        self,
        extraction_reason: str,
        extraction_method: str = "none",
        extraction_status: str = "metadata_only",
        ocr_used: bool = False,
        page_count: Optional[int] = None,
    ) -> Dict[str, object]:
        return {
            "text_preview": "",
            "metadata_only": True,
            "extraction_status": extraction_status,
            "extraction_method": extraction_method,
            "extracted_chars": 0,
            "truncated": False,
            "ocr_used": ocr_used,
            "page_count": page_count,
            "extraction_reason": extraction_reason,
        }

    def _extract_pdf_text_direct(self, decoded_bytes: bytes) -> Tuple[str, int, str]:
        if fitz is None:
            return "", 0, "missing_pymupdf"

        try:
            with fitz.open(stream=decoded_bytes, filetype="pdf") as document:
                page_count = document.page_count
                page_limit = min(page_count, self.MAX_PDF_PAGES)
                text_chunks = [document.load_page(index).get_text("text") for index in range(page_limit)]
        except Exception:
            return "", 0, "pdf_text_extraction_failed"

        return self._normalize_text("\n".join(text_chunks)), page_count, "pdf_text_extracted"

    def _extract_pdf_text_via_ocr(self, decoded_bytes: bytes) -> Tuple[str, int, str]:
        if fitz is None:
            return "", 0, "missing_pymupdf"
        if Image is None or ImageOps is None:
            return "", 0, "missing_pillow"

        try:
            with fitz.open(stream=decoded_bytes, filetype="pdf") as document:
                page_count = document.page_count
                page_limit = min(page_count, self.MAX_PDF_PAGES)
                images: List["Image.Image"] = []
                for index in range(page_limit):
                    page = document.load_page(index)
                    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    rendered = Image.open(BytesIO(pixmap.tobytes("png")))
                    images.append(ImageOps.exif_transpose(rendered).convert("RGB"))
        except Exception:
            return "", 0, "pdf_ocr_render_failed"

        text, reason = self._ocr_images(images)
        return text, page_count, reason

    def _extract_image_text(self, decoded_bytes: bytes) -> Tuple[str, int, str]:
        if Image is None or ImageOps is None:
            return "", 1, "missing_pillow"

        try:
            with Image.open(BytesIO(decoded_bytes)) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
        except (UnidentifiedImageError, OSError):
            return "", 1, "image_decode_failed"

        text, reason = self._ocr_images([image])
        return text, 1, reason

    def _get_ocr_engine(self):
        if RapidOCR is None:
            return None
        if self._ocr_engine is None:
            self._ocr_engine = RapidOCR()
        return self._ocr_engine

    def _ocr_images(self, images: List["Image.Image"]) -> Tuple[str, str]:
        engine = self._get_ocr_engine()
        if engine is None or np is None:
            return "", "missing_rapidocr"

        lines: List[str] = []
        try:
            for image in images:
                result, _ = engine(np.array(image))
                if not result:
                    continue
                for item in result:
                    if isinstance(item, (list, tuple)) and len(item) >= 2 and item[1]:
                        lines.append(str(item[1]).strip())
        except Exception:
            return "", "ocr_execution_failed"

        normalized = self._normalize_text("\n".join(lines))
        if not normalized:
            return "", "ocr_no_text_detected"
        return normalized, "ocr_text_extracted"
