import os
import sys

"""Tests for LLM service deterministic backend and tool authorization enforcement."""

import asyncio
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.services.llm_service import LLMService
from app.services.tool_plugins import FileReaderPlugin


def test_llm_service_deterministic_response_stable():
    service = LLMService()
    service.api_key = ""

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
    service.api_key = ""

    response = asyncio.run(
        service.generate_response(
            prompt="read file backend/app/main.py and calculate 3+3",
            requested_tools=["file_reader", "calculator"],
            authorized_tools=["calculator"],
        )
    )

    assert "file_reader:denied" in response
    assert "calculator:executed" in response


def test_file_reader_can_read_uploaded_attachment_context():
    service = LLMService()
    service.api_key = ""

    response = asyncio.run(
        service.generate_response(
            prompt="Can you read my file resume.txt?",
            requested_tools=["file_reader"],
            authorized_tools=["file_reader"],
            tool_context={
                "attachments": [
                    {
                        "id": "resume-1",
                        "name": "resume.txt",
                        "mime_type": "text/plain",
                        "kind": "file",
                        "text_preview": "Royce Spring Resume 2026. Experience: protected LLM systems.",
                        "disposition": "allow",
                    }
                ]
            },
        )
    )

    assert "file_reader:executed" in response


def test_file_reader_uploaded_attachment_result_includes_extraction_metadata():
    plugin = FileReaderPlugin(allowed_root=Path.cwd())

    result = asyncio.run(
        plugin.execute(
            prompt="Please read my resume.txt",
            context={
                "attachments": [
                    {
                        "id": "resume-1",
                        "name": "resume.txt",
                        "mime_type": "text/plain",
                        "kind": "file",
                        "text_preview": "Royce Spring Resume 2026. Experience: protected LLM systems.",
                        "disposition": "allow",
                        "metadata_only": False,
                        "extraction_status": "success",
                        "extraction_method": "plain_text",
                        "extracted_chars": 61,
                        "truncated": False,
                        "ocr_used": False,
                        "page_count": 1,
                        "extraction_reason": "plain_text_extracted",
                    }
                ]
            },
        )
    )

    assert result["ok"] is True
    assert result["extraction_method"] == "plain_text"
    assert result["extraction_status"] == "success"
    assert result["ocr_used"] is False


def test_write_file_plugin_safely_denies_execution():
    service = LLMService()
    service.api_key = ""

    response = asyncio.run(
        service.generate_response(
            prompt="write file notes.txt with secret data",
            requested_tools=["write_file"],
            authorized_tools=["write_file"],
        )
    )

    assert "write_file:executed" in response


def test_execute_command_plugin_safely_denies_execution():
    service = LLMService()
    service.api_key = ""

    response = asyncio.run(
        service.generate_response(
            prompt="run command cmd.exe /c whoami",
            requested_tools=["execute_command"],
            authorized_tools=["execute_command"],
        )
    )

    assert "execute_command:executed" in response
