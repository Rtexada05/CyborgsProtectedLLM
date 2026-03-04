"""Shared pytest fixtures for backend tests."""

import os
import sys

import pytest

# Add repository root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.core.config import settings


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
