"""Tests for chat rate limiting, concurrency protection, and abuse metrics."""

import asyncio

import httpx
from fastapi.testclient import TestClient

from backend.app.api.routes import chat as chat_route_module
from backend.app.core.config import settings
from backend.app.main import app


def _payload(user_id: str = "abuse-user") -> dict:
    return {
        "user_id": user_id,
        "prompt": "hello world",
    }


def test_ip_rate_limit_rejects_with_429(chat_headers, monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(settings, "RATE_LIMIT_IP_PER_MINUTE", 1)
    monkeypatch.setattr(settings, "RATE_LIMIT_API_KEY_PER_MINUTE", 10)

    first = client.post("/chat/", headers=chat_headers, json=_payload("ip-1"))
    second = client.post("/chat/", headers=chat_headers, json=_payload("ip-2"))

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"]["code"] == "ip_rate_limit_exceeded"
    assert 1 <= int(second.headers["Retry-After"]) <= 60


def test_api_key_rate_limit_uses_forwarded_ip_when_trusted(chat_headers, monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_IP_PER_MINUTE", 10)
    monkeypatch.setattr(settings, "RATE_LIMIT_API_KEY_PER_MINUTE", 1)

    first = client.post(
        "/chat/",
        headers={**chat_headers, "X-Forwarded-For": "1.1.1.1"},
        json=_payload("key-1"),
    )
    second = client.post(
        "/chat/",
        headers={**chat_headers, "X-Forwarded-For": "2.2.2.2"},
        json=_payload("key-2"),
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"]["code"] == "api_key_rate_limit_exceeded"


def test_rate_limit_precedence_prefers_ip_before_api_key(chat_headers, monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(settings, "RATE_LIMIT_IP_PER_MINUTE", 1)
    monkeypatch.setattr(settings, "RATE_LIMIT_API_KEY_PER_MINUTE", 1)

    client.post("/chat/", headers=chat_headers, json=_payload("prec-1"))
    response = client.post("/chat/", headers=chat_headers, json=_payload("prec-2"))

    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "ip_rate_limit_exceeded"


def test_forwarded_for_ignored_when_proxy_headers_disabled(chat_headers, monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", False)
    monkeypatch.setattr(settings, "RATE_LIMIT_IP_PER_MINUTE", 1)
    monkeypatch.setattr(settings, "RATE_LIMIT_API_KEY_PER_MINUTE", 10)

    first = client.post(
        "/chat/",
        headers={**chat_headers, "X-Forwarded-For": "1.1.1.1"},
        json=_payload("proxy-1"),
    )
    second = client.post(
        "/chat/",
        headers={**chat_headers, "X-Forwarded-For": "2.2.2.2"},
        json=_payload("proxy-2"),
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"]["code"] == "ip_rate_limit_exceeded"


def test_forwarded_for_honored_when_proxy_headers_enabled(chat_headers, monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_IP_PER_MINUTE", 1)
    monkeypatch.setattr(settings, "RATE_LIMIT_API_KEY_PER_MINUTE", 10)

    first = client.post(
        "/chat/",
        headers={**chat_headers, "X-Forwarded-For": "1.1.1.1"},
        json=_payload("proxy-a"),
    )
    second = client.post(
        "/chat/",
        headers={**chat_headers, "X-Forwarded-For": "2.2.2.2"},
        json=_payload("proxy-b"),
    )

    assert first.status_code == 200
    assert second.status_code == 200


def test_user_minute_quota_can_be_enabled(chat_headers, monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(settings, "ENABLE_USER_QUOTAS", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_IP_PER_MINUTE", 10)
    monkeypatch.setattr(settings, "RATE_LIMIT_API_KEY_PER_MINUTE", 10)
    monkeypatch.setattr(settings, "USER_QUOTA_PER_MINUTE", 1)
    monkeypatch.setattr(settings, "USER_QUOTA_PER_DAY", 10)

    first = client.post("/chat/", headers=chat_headers, json=_payload("quota-user"))
    second = client.post("/chat/", headers=chat_headers, json=_payload("quota-user"))

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"]["code"] == "user_minute_quota_exceeded"


def test_user_daily_quota_can_be_enabled(chat_headers, monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(settings, "ENABLE_USER_QUOTAS", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_IP_PER_MINUTE", 10)
    monkeypatch.setattr(settings, "RATE_LIMIT_API_KEY_PER_MINUTE", 10)
    monkeypatch.setattr(settings, "USER_QUOTA_PER_MINUTE", 10)
    monkeypatch.setattr(settings, "USER_QUOTA_PER_DAY", 1)

    first = client.post("/chat/", headers=chat_headers, json=_payload("daily-user"))
    second = client.post("/chat/", headers=chat_headers, json=_payload("daily-user"))

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"]["code"] == "user_daily_quota_exceeded"


def test_admin_metrics_include_abuse_protection_sections(chat_headers):
    client = TestClient(app)

    response = client.post("/chat/", headers=chat_headers, json=_payload("metrics-user"))
    assert response.status_code == 200

    metrics = client.get("/admin/metrics")
    assert metrics.status_code == 200
    data = metrics.json()

    assert "abuse_protection" in data
    assert "alerts" in data
    assert data["abuse_protection"]["enabled"] is True
    assert "limits" in data["abuse_protection"]
    assert "rejections" in data["abuse_protection"]


def test_rejection_events_do_not_log_raw_api_key(chat_headers, monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(settings, "RATE_LIMIT_IP_PER_MINUTE", 1)
    monkeypatch.setattr(settings, "RATE_LIMIT_API_KEY_PER_MINUTE", 10)

    client.post("/chat/", headers=chat_headers, json=_payload("log-1"))
    client.post("/chat/", headers=chat_headers, json=_payload("log-2"))

    events = client.get("/admin/events?limit=20")
    assert events.status_code == 200
    payload = events.json()["events"]
    rejection_events = [event for event in payload if event["event_type"] == "rate_limit_rejected"]

    assert rejection_events
    details = rejection_events[0]["details"]
    assert details["api_key_fingerprint"]
    assert "test-client-api-key" not in str(details)


def test_spike_alert_appears_in_metrics(chat_headers, monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(settings, "RATE_LIMIT_IP_PER_MINUTE", 20)
    monkeypatch.setattr(settings, "RATE_LIMIT_API_KEY_PER_MINUTE", 20)
    monkeypatch.setattr(settings, "SPIKE_ALERT_THRESHOLD_REQUESTS", 2)
    monkeypatch.setattr(settings, "SPIKE_ALERT_COOLDOWN_SECONDS", 300)

    client.post("/chat/", headers=chat_headers, json=_payload("alert-1"))
    client.post("/chat/", headers=chat_headers, json=_payload("alert-2"))

    metrics = client.get("/admin/metrics")
    data = metrics.json()
    assert data["alerts"]["active"]
    assert data["alerts"]["recent"]
    assert data["alerts"]["active"][0]["code"] == "chat_request_spike"


def test_spike_alert_clears_after_window(chat_headers, monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(settings, "RATE_LIMIT_IP_PER_MINUTE", 20)
    monkeypatch.setattr(settings, "RATE_LIMIT_API_KEY_PER_MINUTE", 20)
    monkeypatch.setattr(settings, "SPIKE_ALERT_THRESHOLD_REQUESTS", 2)
    monkeypatch.setattr(settings, "SPIKE_ALERT_WINDOW_SECONDS", 1)
    monkeypatch.setattr(settings, "SPIKE_ALERT_COOLDOWN_SECONDS", 300)

    current_time = 1000.0
    chat_route_module.shared_traffic_guard._time = lambda: current_time

    client.post("/chat/", headers=chat_headers, json=_payload("clear-1"))
    client.post("/chat/", headers=chat_headers, json=_payload("clear-2"))

    current_time = 1002.0
    metrics = client.get("/admin/metrics")
    data = metrics.json()
    assert data["alerts"]["active"] == []
    assert data["alerts"]["recent"]


def test_timeout_returns_504_and_releases_slot(chat_headers, monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(settings, "CHAT_REQUEST_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(settings, "RATE_LIMIT_IP_PER_MINUTE", 10)
    monkeypatch.setattr(settings, "RATE_LIMIT_API_KEY_PER_MINUTE", 10)

    original_handler = chat_route_module.defense_controller.handle_request

    async def slow_handler(*args, **kwargs):
        await asyncio.sleep(0.05)

    chat_route_module.defense_controller.handle_request = slow_handler
    try:
        response = client.post("/chat/", headers=chat_headers, json=_payload("slow-user"))
        assert response.status_code == 504
        assert response.json()["detail"]["code"] == "chat_processing_timeout"

        follow_up = client.post("/chat/", headers=chat_headers, json=_payload("slow-user-2"))
        assert follow_up.status_code == 504
    finally:
        chat_route_module.defense_controller.handle_request = original_handler


def test_concurrency_limit_rejects_excess_requests(chat_headers, monkeypatch):
    monkeypatch.setattr(settings, "CHAT_MAX_IN_FLIGHT", 1)
    monkeypatch.setattr(settings, "RATE_LIMIT_IP_PER_MINUTE", 10)
    monkeypatch.setattr(settings, "RATE_LIMIT_API_KEY_PER_MINUTE", 10)

    original_handler = chat_route_module.defense_controller.handle_request

    async def run_case():
        entered = asyncio.Event()
        release = asyncio.Event()

        async def blocking_handler(*args, **kwargs):
            entered.set()
            await release.wait()
            return await original_handler(*args, **kwargs)

        chat_route_module.defense_controller.handle_request = blocking_handler
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            first_task = asyncio.create_task(client.post("/chat/", headers=chat_headers, json=_payload("conc-1")))
            await asyncio.wait_for(entered.wait(), timeout=1)
            second = await client.post("/chat/", headers=chat_headers, json=_payload("conc-2"))
            release.set()
            first = await first_task
            return first, second

    try:
        first_response, second_response = asyncio.run(run_case())
    finally:
        chat_route_module.defense_controller.handle_request = original_handler

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert second_response.json()["detail"]["code"] == "chat_capacity_exceeded"
