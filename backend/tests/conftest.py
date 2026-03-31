"""Shared pytest fixtures for backend tests."""

import os
import sys

import pytest

# Add repository root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.core.config import settings
from backend.app.services.metrics_logger import shared_metrics_logger
from backend.app.services.traffic_guard import shared_traffic_guard


TEST_CLIENT_API_KEY = "test-client-api-key"


@pytest.fixture(autouse=True)
def configure_client_api_key():
    """Set a default inbound API key for tests and restore after each test."""
    original_key = settings.CLIENT_API_KEY
    settings.CLIENT_API_KEY = TEST_CLIENT_API_KEY
    yield
    settings.CLIENT_API_KEY = original_key


@pytest.fixture
def chat_headers():
    """Standard authenticated headers for chat endpoint tests."""
    return {"X-API-Key": TEST_CLIENT_API_KEY}


@pytest.fixture(autouse=True)
def reset_shared_runtime_state():
    """Reset singleton runtime state between tests."""

    shared_metrics_logger.reset()
    shared_traffic_guard.reset()
    yield
    shared_metrics_logger.reset()
    shared_traffic_guard.reset()
