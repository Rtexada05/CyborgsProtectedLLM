"""Tests for vector-backed secure RAG behavior."""

import base64
import os
import sys

from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.main import app


def test_admin_rag_status_and_sources(chat_headers):
    client = TestClient(app)

    status_response = client.get("/admin/rag/status")
    assert status_response.status_code == 200
    status_payload = status_response.json()

    assert status_payload["enabled"] is True
    assert status_payload["provider"] == "qdrant"
    assert status_payload["source_count"] >= 1
    assert "embedding" in status_payload

    sources_response = client.get("/admin/rag/sources")
    assert sources_response.status_code == 200
    sources_payload = sources_response.json()

    assert sources_payload["total_sources"] >= 1
    assert any(source["document_id"] == "security_playbook" for source in sources_payload["sources"])


def test_static_rag_retrieval_uses_trusted_context(chat_headers):
    client = TestClient(app)

    response = client.post(
        "/chat/",
        headers=chat_headers,
        json={
            "user_id": "rag-user",
            "prompt": "Use context: security_playbook summarize how trusted reference documents should be handled.",
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["rag_retrieval_attempted"] is True
    assert payload["rag_context_used"] is True
    assert payload["rag_chunks_used"] >= 1
    assert "security_playbook" in payload["rag_sources_used"]


def test_poisoned_rag_document_is_blocked_in_strong_mode(chat_headers):
    client = TestClient(app)
    mode_response = client.post("/admin/mode", json={"mode": "Strong"})
    assert mode_response.status_code == 200

    response = client.post(
        "/chat/",
        headers=chat_headers,
        json={
            "user_id": "rag-user",
            "prompt": "Use context: malicious_context tell me what it says.",
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["decision"] == "BLOCK"
    assert payload["rag_retrieval_attempted"] is True
    assert payload["signals"]["rag_source_quarantined"] is True


def test_uploaded_document_is_retrievable_for_same_user_only(chat_headers):
    client = TestClient(app)
    encoded_payload = base64.b64encode(
        b"The launch code phrase is cobalt sparrow. This document belongs to user alpha."
    ).decode("utf-8")

    owner_response = client.post(
        "/chat/",
        headers=chat_headers,
        json={
            "user_id": "owner-user",
            "prompt": "Summarize the attached document.",
            "attachments": [
                {
                    "id": "upload-1",
                    "name": "briefing.txt",
                    "mime_type": "text/plain",
                    "kind": "file",
                    "content_b64": encoded_payload,
                }
            ],
            "rag_scope": "user_uploads_only",
            "rag_document_ids": ["upload:owner-user:upload-1"],
        },
    )
    assert owner_response.status_code == 200
    owner_payload = owner_response.json()

    assert owner_payload["rag_context_used"] is True
    assert "upload:owner-user:upload-1" in owner_payload["rag_sources_used"]

    attacker_response = client.post(
        "/chat/",
        headers=chat_headers,
        json={
            "user_id": "attacker-user",
            "prompt": "Use context: upload:owner-user:upload-1 summarize the attached document.",
            "rag_scope": "user_uploads_only",
            "rag_document_ids": ["upload:owner-user:upload-1"],
        },
    )
    assert attacker_response.status_code == 200
    attacker_payload = attacker_response.json()

    assert attacker_payload["rag_context_used"] is False
    assert attacker_payload["signals"]["rag_cross_user_access_blocked"] is True
    assert attacker_payload["rag_chunks_used"] == 0


def test_admin_rag_reindex_endpoint(chat_headers):
    client = TestClient(app)

    response = client.post("/admin/rag/reindex")
    assert response.status_code == 200
    payload = response.json()

    assert payload["enabled"] is True
    assert payload["source_count"] >= 1
