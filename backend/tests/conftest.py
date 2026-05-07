"""Shared pytest fixtures for backend tests."""

import os
import sys

import pytest

# Add repository root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.core.config import settings
from backend.app.services.conversation_memory import shared_conversation_memory
from backend.app.services.evaluation_store import shared_evaluation_store
from backend.app.services.metrics_logger import shared_metrics_logger
from backend.app.services.rag_manager import shared_rag_manager
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

    original_db_path = settings.MEMORY_DB_PATH
    original_eval_db_path = settings.EVAL_DB_PATH
    settings.MEMORY_DB_PATH = os.path.join(os.path.dirname(__file__), "tmp", "chat_memory.sqlite")
    settings.EVAL_DB_PATH = os.path.join(os.path.dirname(__file__), "tmp", "evaluation.sqlite")
    os.makedirs(os.path.dirname(settings.MEMORY_DB_PATH), exist_ok=True)
    if os.path.exists(settings.MEMORY_DB_PATH):
        os.remove(settings.MEMORY_DB_PATH)
    if os.path.exists(settings.EVAL_DB_PATH):
        os.remove(settings.EVAL_DB_PATH)
    shared_conversation_memory.reset()
    shared_evaluation_store.reset()
    shared_metrics_logger.reset()
    shared_traffic_guard.reset()
    shared_rag_manager.reset()
    yield
    if os.path.exists(settings.MEMORY_DB_PATH):
        os.remove(settings.MEMORY_DB_PATH)
    if os.path.exists(settings.EVAL_DB_PATH):
        os.remove(settings.EVAL_DB_PATH)
    settings.MEMORY_DB_PATH = original_db_path
    settings.EVAL_DB_PATH = original_eval_db_path
    shared_conversation_memory.reset()
    shared_evaluation_store.reset()
    shared_metrics_logger.reset()
    shared_traffic_guard.reset()
    shared_rag_manager.reset()
