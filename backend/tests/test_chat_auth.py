"""Tests for chat endpoint API key authentication."""

import os
import sys

from fastapi.testclient import TestClient

# Add repository root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.main import app
from backend.app.core.config import settings


def _chat_payload():
    return {
        "user_id": "auth-test-user",
        "prompt": "Hello from auth test",
    }


def test_chat_auth_accepts_valid_key(chat_headers):
    client = TestClient(app)
    response = client.post("/chat/", headers=chat_headers, json=_chat_payload())
    assert response.status_code == 200


def test_chat_auth_rejects_missing_key():
    client = TestClient(app)
    response = client.post("/chat/", json=_chat_payload())
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_chat_auth_rejects_wrong_key():
    client = TestClient(app)
    response = client.post("/chat/", headers={"X-API-Key": "wrong-key"}, json=_chat_payload())
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_chat_auth_rejects_authorization_bearer_only():
    client = TestClient(app)
    response = client.post("/chat/", headers={"Authorization": "Bearer test-client-api-key"}, json=_chat_payload())
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_chat_auth_rejects_when_server_key_unset(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(settings, "CLIENT_API_KEY", None)
    response = client.post("/chat/", headers={"X-API-Key": "any-value"}, json=_chat_payload())
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"
