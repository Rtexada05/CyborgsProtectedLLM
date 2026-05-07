"""SQLite-backed local conversation memory for red-team testing."""

from __future__ import annotations

import asyncio
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.config import settings


class ConversationMemoryError(Exception):
    """Base exception for conversation memory failures."""


class ConversationOwnershipError(ConversationMemoryError):
    """Raised when a conversation belongs to another user."""


class ConversationNotFoundError(ConversationMemoryError):
    """Raised when a conversation cannot be found."""


class InvalidConversationIdError(ConversationMemoryError):
    """Raised when a conversation id is malformed."""


class ConversationMemoryService:
    """Persist full transcripts locally while replaying only bounded recent turns."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._initialized = False
        self._db_path = Path(settings.MEMORY_DB_PATH)

    async def initialize(self) -> None:
        """Create the backing database and schema when memory is enabled."""

        if not settings.MEMORY_ENABLED or self._initialized:
            return

        async with self._lock:
            if not settings.MEMORY_ENABLED or self._initialized:
                return

            self._db_path = Path(settings.MEMORY_DB_PATH)
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(self._initialize_sync)
            self._initialized = True

    def reset(self) -> None:
        """Reset the in-process initialization state for tests."""

        self._initialized = False
        self._db_path = Path(settings.MEMORY_DB_PATH)

    async def get_or_create_conversation(self, conversation_id: Optional[str], user_id: str) -> Dict[str, Any]:
        """Create a new conversation when omitted, else validate ownership."""

        if not settings.MEMORY_ENABLED:
            generated_id = conversation_id or str(uuid.uuid4())
            return {"conversation_id": generated_id, "created": conversation_id is None}

        await self.initialize()

        if conversation_id is None:
            created_id = await asyncio.to_thread(self._create_conversation_sync, user_id)
            return {"conversation_id": created_id, "created": True}

        self._validate_conversation_id(conversation_id)
        await asyncio.to_thread(self._ensure_conversation_owned_sync, conversation_id, user_id)
        return {"conversation_id": conversation_id, "created": False}

    async def append_turn(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        *,
        decision: Optional[str] = None,
        risk_level: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Append a visible chat turn to the persisted transcript."""

        if not settings.MEMORY_ENABLED:
            return None

        await self.initialize()
        return await asyncio.to_thread(
            self._append_turn_sync,
            conversation_id,
            user_id,
            role,
            content,
            decision,
            risk_level,
            trace_id,
        )

    async def load_recent_context(
        self,
        conversation_id: str,
        user_id: str,
        *,
        exclude_latest_user_turn: bool = False,
    ) -> Dict[str, Any]:
        """Return bounded recent turns for model replay."""

        if not settings.MEMORY_ENABLED:
            return {
                "messages": [],
                "memory_used": False,
                "turns_loaded": 0,
                "chars_loaded": 0,
                "truncated": False,
            }

        await self.initialize()
        return await asyncio.to_thread(
            self._load_recent_context_sync,
            conversation_id,
            user_id,
            exclude_latest_user_turn,
        )

    async def list_conversations(self, user_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent conversations with transcript counts."""

        if not settings.MEMORY_ENABLED:
            return []

        await self.initialize()
        return await asyncio.to_thread(self._list_conversations_sync, user_id, limit)

    async def get_conversation(self, conversation_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Return one conversation and its full ordered transcript."""

        if not settings.MEMORY_ENABLED:
            raise ConversationNotFoundError("Conversation memory disabled")

        await self.initialize()
        return await asyncio.to_thread(self._get_conversation_sync, conversation_id, user_id)

    def _initialize_sync(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active'
                );

                CREATE INDEX IF NOT EXISTS conversations_user_updated_idx
                    ON conversations (user_id, updated_at DESC);

                CREATE TABLE IF NOT EXISTS conversation_turns (
                    turn_id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    sequence_number INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    decision TEXT,
                    risk_level TEXT,
                    trace_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (conversation_id)
                );

                CREATE UNIQUE INDEX IF NOT EXISTS turns_conversation_sequence_idx
                    ON conversation_turns (conversation_id, sequence_number ASC);
                """
            )
            connection.commit()

    def _create_conversation_sync(self, user_id: str) -> str:
        conversation_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO conversations (conversation_id, user_id, created_at, updated_at, status)
                VALUES (?, ?, ?, ?, 'active')
                """,
                (conversation_id, user_id, now, now),
            )
            connection.commit()
        return conversation_id

    def _ensure_conversation_owned_sync(self, conversation_id: str, user_id: str) -> None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT user_id FROM conversations WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()

        if row is None:
            raise ConversationNotFoundError("Conversation not found")
        if row["user_id"] != user_id:
            raise ConversationOwnershipError("Conversation belongs to another user")

    def _append_turn_sync(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        decision: Optional[str],
        risk_level: Optional[str],
        trace_id: Optional[str],
    ) -> Dict[str, Any]:
        with self._connection() as connection:
            self._ensure_conversation_owned_tx(connection, conversation_id, user_id)
            now = datetime.now().isoformat()
            current_max = connection.execute(
                "SELECT COALESCE(MAX(sequence_number), 0) AS max_sequence FROM conversation_turns WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
            next_sequence = int(current_max["max_sequence"]) + 1
            turn_id = str(uuid.uuid4())
            connection.execute(
                """
                INSERT INTO conversation_turns (
                    turn_id, conversation_id, sequence_number, role, content, decision, risk_level, trace_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (turn_id, conversation_id, next_sequence, role, content, decision, risk_level, trace_id, now),
            )
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE conversation_id = ?",
                (now, conversation_id),
            )
            connection.commit()

        return {
            "turn_id": turn_id,
            "conversation_id": conversation_id,
            "sequence_number": next_sequence,
            "role": role,
            "content": content,
            "decision": decision,
            "risk_level": risk_level,
            "trace_id": trace_id,
            "created_at": now,
        }

    def _load_recent_context_sync(
        self,
        conversation_id: str,
        user_id: str,
        exclude_latest_user_turn: bool,
    ) -> Dict[str, Any]:
        with self._connection() as connection:
            self._ensure_conversation_owned_tx(connection, conversation_id, user_id)
            rows = connection.execute(
                """
                SELECT sequence_number, role, content, decision
                FROM conversation_turns
                WHERE conversation_id = ?
                ORDER BY sequence_number ASC
                """,
                (conversation_id,),
            ).fetchall()

        filtered_rows = [row for row in rows if self._include_turn(row["role"], row["decision"])]
        if exclude_latest_user_turn and filtered_rows and filtered_rows[-1]["role"] == "user":
            filtered_rows = filtered_rows[:-1]
        selected: List[sqlite3.Row] = []
        total_chars = 0

        for row in reversed(filtered_rows):
            content = str(row["content"] or "")
            if settings.MEMORY_MAX_TURNS_TO_MODEL and len(selected) >= settings.MEMORY_MAX_TURNS_TO_MODEL:
                break
            if selected and settings.MEMORY_MAX_CONTEXT_CHARS and total_chars + len(content) > settings.MEMORY_MAX_CONTEXT_CHARS:
                break
            if not selected and settings.MEMORY_MAX_CONTEXT_CHARS and len(content) > settings.MEMORY_MAX_CONTEXT_CHARS:
                selected.append(row)
                total_chars = len(content)
                break

            selected.append(row)
            total_chars += len(content)

        selected.reverse()
        messages = [{"role": self._message_role(row["role"]), "content": str(row["content"] or "")} for row in selected]
        return {
            "messages": messages,
            "memory_used": bool(messages),
            "turns_loaded": len(messages),
            "chars_loaded": sum(len(message["content"]) for message in messages),
            "truncated": len(selected) < len(filtered_rows),
        }

    def _list_conversations_sync(self, user_id: Optional[str], limit: int) -> List[Dict[str, Any]]:
        query = """
            SELECT
                conversations.conversation_id,
                conversations.user_id,
                conversations.created_at,
                conversations.updated_at,
                conversations.status,
                COUNT(conversation_turns.turn_id) AS turn_count
            FROM conversations
            LEFT JOIN conversation_turns
                ON conversation_turns.conversation_id = conversations.conversation_id
        """
        params: List[Any] = []
        if user_id is not None:
            query += " WHERE conversations.user_id = ?"
            params.append(user_id)
        query += """
            GROUP BY conversations.conversation_id
            ORDER BY conversations.updated_at DESC
            LIMIT ?
        """
        params.append(limit)

        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()

        return [dict(row) for row in rows]

    def _get_conversation_sync(self, conversation_id: str, user_id: Optional[str]) -> Dict[str, Any]:
        self._validate_conversation_id(conversation_id)
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT conversation_id, user_id, created_at, updated_at, status
                FROM conversations
                WHERE conversation_id = ?
                """,
                (conversation_id,),
            ).fetchone()
            if row is None:
                raise ConversationNotFoundError("Conversation not found")
            if user_id is not None and row["user_id"] != user_id:
                raise ConversationOwnershipError("Conversation belongs to another user")

            turn_rows = connection.execute(
                """
                SELECT turn_id, sequence_number, role, content, decision, risk_level, trace_id, created_at
                FROM conversation_turns
                WHERE conversation_id = ?
                ORDER BY sequence_number ASC
                """,
                (conversation_id,),
            ).fetchall()

        payload = dict(row)
        payload["turn_count"] = len(turn_rows)
        payload["turns"] = [dict(turn_row) for turn_row in turn_rows]
        return payload

    def _ensure_conversation_owned_tx(self, connection: sqlite3.Connection, conversation_id: str, user_id: str) -> None:
        row = connection.execute(
            "SELECT user_id FROM conversations WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        if row is None:
            raise ConversationNotFoundError("Conversation not found")
        if row["user_id"] != user_id:
            raise ConversationOwnershipError("Conversation belongs to another user")

    def _include_turn(self, role: str, decision: Optional[str]) -> bool:
        if role == "user":
            return True
        if decision == "BLOCK" and not settings.MEMORY_INCLUDE_BLOCKED:
            return False
        if decision == "SANITIZE" and not settings.MEMORY_INCLUDE_SANITIZED:
            return False
        return True

    def _message_role(self, stored_role: str) -> str:
        if stored_role == "user":
            return "user"
        return "assistant"

    def _validate_conversation_id(self, conversation_id: str) -> None:
        try:
            uuid.UUID(conversation_id)
        except (ValueError, TypeError) as exc:
            raise InvalidConversationIdError("Conversation id must be a valid UUID") from exc

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()


shared_conversation_memory = ConversationMemoryService()
