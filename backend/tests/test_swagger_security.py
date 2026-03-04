"""Swagger/OpenAPI validation and direct-injection security policy tests."""

import os
import sys

import pytest
from fastapi.testclient import TestClient

# Add repository root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.main import app
from backend.tests.attacks.corpus import iter_attack_cases
from backend.tests.attacks.swagger_policy_expectations import assert_policy_response


def _set_security_mode(client: TestClient, mode: str) -> None:
    """Set global mode before each security scenario."""
    response = client.post("/admin/mode", json={"mode": mode})
    assert response.status_code == 200
    payload = response.json()
    assert payload["active_mode"] == mode


def _assert_traceability_fields(payload: dict) -> None:
    """Ensure response contains auditability metadata."""
    assert "trace_id" in payload and isinstance(payload["trace_id"], str) and payload["trace_id"]
    assert "security_mode" in payload and payload["security_mode"] in {"Off", "Weak", "Normal", "Strong"}
    assert "signals" in payload


def test_swagger_docs_and_openapi_available():
    """Swagger/ReDoc/OpenAPI should be reachable for red-team testing."""
    client = TestClient(app)

    docs = client.get("/docs")
    assert docs.status_code == 200
    assert "text/html" in docs.headers["content-type"]

    redoc = client.get("/redoc")
    assert redoc.status_code == 200
    assert "text/html" in redoc.headers["content-type"]

    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200


def test_openapi_contains_required_paths_and_chat_schema():
    """OpenAPI should publish chat/admin contracts used by Swagger UI."""
    client = TestClient(app)
    spec = client.get("/openapi.json").json()

    assert "/chat/" in spec["paths"]
    assert "post" in spec["paths"]["/chat/"]
    assert "/admin/mode" in spec["paths"]
    assert "post" in spec["paths"]["/admin/mode"]

    chat_schema = spec["components"]["schemas"]["ChatRequest"]
    properties = chat_schema["properties"]
    required_fields = set(chat_schema["required"])

    assert {"user_id", "prompt", "attachments", "requested_tools"} <= set(properties.keys())
    assert {"user_id", "prompt"} <= required_fields
    assert "attachments" not in required_fields
    assert "requested_tools" not in required_fields


@pytest.mark.parametrize("mode", ["Off", "Weak", "Normal", "Strong"])
@pytest.mark.parametrize("attack_case", iter_attack_cases(), ids=lambda c: c.case_id)
def test_swagger_direct_injection_policy_matrix(mode, attack_case, chat_headers):
    """
    Execute direct attack payloads via API calls equivalent to Swagger Try-It-Out.

    This intentionally asserts desired policy envelopes so known gaps fail loudly.
    """
    client = TestClient(app)
    _set_security_mode(client, mode)

    payload = attack_case.to_chat_payload(user_id=f"swagger-redteam-{mode.lower()}")
    response = client.post("/chat/", headers=chat_headers, json=payload)
    assert response.status_code == 200
    response_json = response.json()

    _assert_traceability_fields(response_json)
    assert_policy_response(mode, attack_case.category, response_json)


def test_swagger_attack_requests_generate_admin_evidence(chat_headers):
    """Attack requests should be inspectable via admin events and decisions endpoints."""
    client = TestClient(app)
    _set_security_mode(client, "Strong")

    attack_case = next(case for case in iter_attack_cases() if case.category == "direct_prompt_injection")
    response = client.post(
        "/chat/",
        headers=chat_headers,
        json=attack_case.to_chat_payload(user_id="evidence-check-user"),
    )
    assert response.status_code == 200
    trace_id = response.json()["trace_id"]

    events = client.get("/admin/events", params={"limit": 100})
    assert events.status_code == 200
    event_records = events.json()["events"]
    assert any(record.get("trace_id") == trace_id for record in event_records)

    decisions = client.get("/admin/decisions", params={"limit": 100})
    assert decisions.status_code == 200
    decision_records = decisions.json()["decisions"]
    assert any(record.get("trace_id") == trace_id for record in decision_records)
