"""Unit tests for structured attachment extraction."""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.models.schemas import AttachmentRef
from backend.app.services.attachment_text_extractor import AttachmentTextExtractor


def _attachment(name: str, mime_type: str) -> AttachmentRef:
    return AttachmentRef(
        id=f"att-{name}",
        name=name,
        mime_type=mime_type,
        kind="image" if mime_type.startswith("image/") else "file",
    )


def test_pdf_text_extraction_prefers_direct_text(monkeypatch):
    extractor = AttachmentTextExtractor()
    attachment = _attachment("report.pdf", "application/pdf")

    monkeypatch.setattr(
        extractor,
        "_extract_pdf_text_direct",
        lambda _decoded_bytes: ("Quarterly report body " * 12, 3, "pdf_text_extracted"),
    )
    monkeypatch.setattr(
        extractor,
        "_extract_pdf_text_via_ocr",
        lambda _decoded_bytes: ("", 3, "ocr_not_needed"),
    )

    result = extractor.extract(attachment, b"%PDF")

    assert result["metadata_only"] is False
    assert result["extraction_method"] == "pdf_text"
    assert result["extraction_status"] == "success"
    assert result["ocr_used"] is False
    assert result["page_count"] == 3


def test_pdf_ocr_fallback_is_used_when_direct_text_is_too_short(monkeypatch):
    extractor = AttachmentTextExtractor()
    attachment = _attachment("scan.pdf", "application/pdf")

    monkeypatch.setattr(
        extractor,
        "_extract_pdf_text_direct",
        lambda _decoded_bytes: ("tiny", 2, "pdf_text_extracted"),
    )
    monkeypatch.setattr(
        extractor,
        "_extract_pdf_text_via_ocr",
        lambda _decoded_bytes: ("Recovered OCR invoice text " * 8, 2, "ocr_text_extracted"),
    )

    result = extractor.extract(attachment, b"%PDF")

    assert result["metadata_only"] is False
    assert result["extraction_method"] == "pdf_ocr"
    assert result["ocr_used"] is True
    assert result["page_count"] == 2
    assert "Recovered OCR invoice text" in result["text_preview"]


def test_image_ocr_extraction_returns_structured_result(monkeypatch):
    extractor = AttachmentTextExtractor()
    attachment = _attachment("badge.png", "image/png")

    monkeypatch.setattr(
        extractor,
        "_extract_image_text",
        lambda _decoded_bytes: ("Badge number 42", 1, "ocr_text_extracted"),
    )

    result = extractor.extract(attachment, b"image-bytes")

    assert result["metadata_only"] is False
    assert result["extraction_method"] == "image_ocr"
    assert result["ocr_used"] is True
    assert result["page_count"] == 1
    assert result["text_preview"] == "Badge number 42"


def test_failed_image_extraction_returns_metadata_only(monkeypatch):
    extractor = AttachmentTextExtractor()
    attachment = _attachment("scan.webp", "image/webp")

    monkeypatch.setattr(
        extractor,
        "_extract_image_text",
        lambda _decoded_bytes: ("", 1, "ocr_execution_failed"),
    )

    result = extractor.extract(attachment, b"image-bytes")

    assert result["metadata_only"] is True
    assert result["extraction_status"] == "failed"
    assert result["extraction_method"] == "none"
    assert result["extraction_reason"] == "ocr_execution_failed"


def test_plain_text_extraction_is_truncated_to_storage_budget():
    extractor = AttachmentTextExtractor()
    attachment = _attachment("notes.txt", "text/plain")

    result = extractor.extract(attachment, ("A" * 9000).encode("utf-8"))

    assert result["metadata_only"] is False
    assert result["truncated"] is True
    assert result["extraction_status"] == "partial"
    assert result["extracted_chars"] == 9000
    assert len(result["text_preview"]) == extractor.MAX_EXTRACTED_CHARS
