"""Tests for local conversation memory behavior."""

import os
import sys

from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.core.config import settings
from backend.app.main import app
from backend.app.services.conversation_memory import shared_conversation_memory


def test_chat_returns_conversation_id_and_reuses_memory(chat_headers):
    client = TestClient(app)

    first = client.post(
        "/chat/",
        headers=chat_headers,
        json={"user_id": "memory-user", "prompt": "First turn"},
    )
    assert first.status_code == 200
    first_payload = first.json()

    assert first_payload["conversation_id"]
    assert first_payload["memory_used"] is False
    assert first_payload["memory_turns_loaded"] == 0

    second = client.post(
        "/chat/",
        headers=chat_headers,
        json={
            "user_id": "memory-user",
            "conversation_id": first_payload["conversation_id"],
            "prompt": "Second turn",
        },
    )
    assert second.status_code == 200
    second_payload = second.json()

    assert second_payload["conversation_id"] == first_payload["conversation_id"]
    assert second_payload["memory_used"] is True
    assert second_payload["memory_turns_loaded"] >= 1
    assert second_payload["memory_chars_loaded"] > 0


def test_chat_rejects_cross_user_conversation_access(chat_headers):
    client = TestClient(app)

    first = client.post(
        "/chat/",
        headers=chat_headers,
        json={"user_id": "owner-user", "prompt": "Hello"},
    )
    assert first.status_code == 200
    conversation_id = first.json()["conversation_id"]

    second = client.post(
        "/chat/",
        headers=chat_headers,
        json={
            "user_id": "other-user",
            "conversation_id": conversation_id,
            "prompt": "Reuse someone else's transcript",
        },
    )
    assert second.status_code == 403


def test_admin_conversation_endpoints_return_transcript(chat_headers):
    client = TestClient(app)

    response = client.post(
        "/chat/",
        headers=chat_headers,
        json={"user_id": "admin-memory-user", "prompt": "Inspect me"},
    )
    assert response.status_code == 200
    conversation_id = response.json()["conversation_id"]

    listing = client.get("/admin/conversations", params={"limit": 10})
    assert listing.status_code == 200
    listing_payload = listing.json()
    assert any(item["conversation_id"] == conversation_id for item in listing_payload["conversations"])

    detail = client.get(f"/admin/conversations/{conversation_id}")
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["conversation_id"] == conversation_id
    assert len(detail_payload["turns"]) >= 2
    assert detail_payload["turns"][0]["role"] == "user"


def test_memory_service_can_be_disabled(chat_headers):
    client = TestClient(app)
    original_enabled = settings.MEMORY_ENABLED
    settings.MEMORY_ENABLED = False
    shared_conversation_memory.reset()
    try:
        response = client.post(
            "/chat/",
            headers=chat_headers,
            json={"user_id": "memory-disabled-user", "prompt": "No persistence"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["memory_used"] is False
        assert payload["memory_turns_loaded"] == 0
    finally:
        settings.MEMORY_ENABLED = original_enabled
        shared_conversation_memory.reset()
