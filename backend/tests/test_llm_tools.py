import os
import sys

"""Tests for LLM service deterministic backend and tool authorization enforcement."""

import asyncio

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.services.llm_service import LLMService


def test_llm_service_deterministic_response_stable():
    service = LLMService()

    response_one = asyncio.run(
        service.generate_response(
            prompt="calculate 2 + 2",
            requested_tools=["calculator"],
            authorized_tools=["calculator"],
        )
    )
    response_two = asyncio.run(
        service.generate_response(
            prompt="calculate 2 + 2",
            requested_tools=["calculator"],
            authorized_tools=["calculator"],
        )
    )

    assert response_one == response_two
    assert "calculator:executed" in response_one


def test_llm_service_tool_authorization_enforced():
    service = LLMService()

    response = asyncio.run(
        service.generate_response(
            prompt="read file backend/app/main.py and calculate 3+3",
            requested_tools=["file_reader", "calculator"],
            authorized_tools=["calculator"],
        )
    )

    assert "file_reader:denied" in response
    assert "calculator:executed" in response
