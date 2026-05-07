"""SQLite-backed evaluation records for labeled FPR and ASR metrics."""

from __future__ import annotations

import asyncio
import math
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from ..core.config import settings


PredictedLabel = Literal["attack", "benign"]
GroundTruthLabel = Literal["attack", "benign"]


class EvaluationStoreError(Exception):
    """Base exception for evaluation store failures."""


class EvaluationRecordNotFoundError(EvaluationStoreError):
    """Raised when an evaluation record cannot be found."""


class EvaluationStore:
    """Persist reviewable prediction records and compute labeled metrics."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._initialized = False
        self._db_path = Path(settings.EVAL_DB_PATH)

    async def initialize(self) -> None:
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            self._db_path = Path(settings.EVAL_DB_PATH)
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(self._initialize_sync)
            self._initialized = True

    def reset(self) -> None:
        """Reset in-process initialization state for tests."""

        self._initialized = False
        self._db_path = Path(settings.EVAL_DB_PATH)

    async def record_prediction(
        self,
        trace_id: str,
        user_id: str,
        decision: str,
        created_at: Optional[datetime] = None,
        conversation_id: Optional[str] = None,
        prompt_text: str = "",
        response_text: str = "",
        reason: str = "",
        risk_level: Optional[str] = None,
        security_mode: Optional[str] = None,
    ) -> None:
        await self.initialize()
        await asyncio.to_thread(
            self._record_prediction_sync,
            trace_id,
            user_id,
            conversation_id,
            decision,
            self._decision_to_predicted_label(decision),
            prompt_text,
            response_text,
            reason,
            risk_level,
            security_mode,
            (created_at or datetime.now()).isoformat(),
        )

    async def complete_review(
        self,
        trace_id: str,
        ground_truth_label: GroundTruthLabel,
        reviewer_id: Optional[str] = None,
        review_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        await self.initialize()
        return await asyncio.to_thread(
            self._complete_review_sync,
            trace_id,
            ground_truth_label,
            reviewer_id,
            review_note,
        )

    async def get_record(self, trace_id: str) -> Dict[str, Any]:
        await self.initialize()
        return await asyncio.to_thread(self._get_record_sync, trace_id)

    async def list_records(
        self,
        *,
        review_status: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
    ) -> Dict[str, Any]:
        await self.initialize()
        return await asyncio.to_thread(
            self._list_records_sync,
            review_status,
            page,
            limit,
        )

    async def get_evaluation_metrics(self) -> Dict[str, Any]:
        await self.initialize()
        return await asyncio.to_thread(self._get_evaluation_metrics_sync)

    def _initialize_sync(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS evaluation_records (
                    trace_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    conversation_id TEXT,
                    decision TEXT NOT NULL,
                    predicted_label TEXT NOT NULL,
                    prompt_text TEXT NOT NULL DEFAULT '',
                    response_text TEXT NOT NULL DEFAULT '',
                    reason TEXT NOT NULL DEFAULT '',
                    risk_level TEXT,
                    security_mode TEXT,
                    ground_truth_label TEXT,
                    review_status TEXT NOT NULL,
                    reviewed_at TEXT,
                    reviewer_id TEXT,
                    review_note TEXT
                );

                CREATE INDEX IF NOT EXISTS evaluation_review_status_idx
                    ON evaluation_records (review_status);

                CREATE INDEX IF NOT EXISTS evaluation_ground_truth_idx
                    ON evaluation_records (ground_truth_label);
                """
            )
            self._ensure_column(connection, "evaluation_records", "conversation_id", "TEXT")
            self._ensure_column(connection, "evaluation_records", "prompt_text", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "evaluation_records", "response_text", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "evaluation_records", "reason", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "evaluation_records", "risk_level", "TEXT")
            self._ensure_column(connection, "evaluation_records", "security_mode", "TEXT")
            connection.commit()

    def _record_prediction_sync(
        self,
        trace_id: str,
        user_id: str,
        conversation_id: Optional[str],
        decision: str,
        predicted_label: PredictedLabel,
        prompt_text: str,
        response_text: str,
        reason: str,
        risk_level: Optional[str],
        security_mode: Optional[str],
        created_at: str,
    ) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO evaluation_records (
                    trace_id,
                    created_at,
                    user_id,
                    conversation_id,
                    decision,
                    predicted_label,
                    prompt_text,
                    response_text,
                    reason,
                    risk_level,
                    security_mode,
                    ground_truth_label,
                    review_status,
                    reviewed_at,
                    reviewer_id,
                    review_note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 'pending', NULL, NULL, NULL)
                """,
                (
                    trace_id,
                    created_at,
                    user_id,
                    conversation_id,
                    decision,
                    predicted_label,
                    prompt_text,
                    response_text,
                    reason,
                    risk_level,
                    security_mode,
                ),
            )
            connection.commit()

    def _complete_review_sync(
        self,
        trace_id: str,
        ground_truth_label: GroundTruthLabel,
        reviewer_id: Optional[str],
        review_note: Optional[str],
    ) -> Dict[str, Any]:
        reviewed_at = datetime.now().isoformat()
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE evaluation_records
                SET ground_truth_label = ?,
                    review_status = 'completed',
                    reviewed_at = ?,
                    reviewer_id = ?,
                    review_note = ?
                WHERE trace_id = ?
                """,
                (ground_truth_label, reviewed_at, reviewer_id, review_note, trace_id),
            )
            if cursor.rowcount == 0:
                raise EvaluationRecordNotFoundError("Evaluation record not found")
            connection.commit()
        return self._get_record_sync(trace_id)

    def _get_record_sync(self, trace_id: str) -> Dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT
                    trace_id,
                    created_at,
                    user_id,
                    conversation_id,
                    decision,
                    predicted_label,
                    prompt_text,
                    response_text,
                    reason,
                    risk_level,
                    security_mode,
                    ground_truth_label,
                    review_status,
                    reviewed_at,
                    reviewer_id,
                    review_note
                FROM evaluation_records
                WHERE trace_id = ?
                """,
                (trace_id,),
            ).fetchone()

        if row is None:
            raise EvaluationRecordNotFoundError("Evaluation record not found")
        return dict(row)

    def _list_records_sync(
        self,
        review_status: Optional[str],
        page: int,
        limit: int,
    ) -> Dict[str, Any]:
        filters = []
        params: list[Any] = []
        if review_status is not None:
            filters.append("review_status = ?")
            params.append(review_status)

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        count_query = f"SELECT COUNT(*) AS count FROM evaluation_records {where_clause}"
        total_records = 0

        with self._connection() as connection:
            total_records = int(connection.execute(count_query, params).fetchone()["count"])
            offset = max(page - 1, 0) * limit
            rows = connection.execute(
                f"""
                SELECT
                    trace_id,
                    created_at,
                    user_id,
                    conversation_id,
                    decision,
                    predicted_label,
                    prompt_text,
                    response_text,
                    reason,
                    risk_level,
                    security_mode,
                    ground_truth_label,
                    review_status,
                    reviewed_at,
                    reviewer_id,
                    review_note
                FROM evaluation_records
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()

        total_pages = max(1, math.ceil(total_records / limit)) if limit > 0 else 1
        return {
            "evaluations": [dict(row) for row in rows],
            "total_evaluations": total_records,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_previous": page > 1,
            "has_next": page < total_pages,
        }

    def _get_evaluation_metrics_sync(self) -> Dict[str, Any]:
        with self._connection() as connection:
            pending_reviews = int(
                connection.execute(
                    "SELECT COUNT(*) AS count FROM evaluation_records WHERE review_status = 'pending'"
                ).fetchone()["count"]
            )
            reviewed_rows = connection.execute(
                """
                SELECT predicted_label, ground_truth_label
                FROM evaluation_records
                WHERE review_status = 'completed'
                  AND ground_truth_label IS NOT NULL
                """
            ).fetchall()

        confusion_matrix = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
        for row in reviewed_rows:
            predicted_label = row["predicted_label"]
            ground_truth_label = row["ground_truth_label"]
            if predicted_label == "attack" and ground_truth_label == "attack":
                confusion_matrix["tp"] += 1
            elif predicted_label == "attack" and ground_truth_label == "benign":
                confusion_matrix["fp"] += 1
            elif predicted_label == "benign" and ground_truth_label == "benign":
                confusion_matrix["tn"] += 1
            elif predicted_label == "benign" and ground_truth_label == "attack":
                confusion_matrix["fn"] += 1

        fpr_denominator = confusion_matrix["fp"] + confusion_matrix["tn"]
        asr_denominator = confusion_matrix["tp"] + confusion_matrix["fn"]

        return {
            "labeled_samples": len(reviewed_rows),
            "pending_reviews": pending_reviews,
            "confusion_matrix": confusion_matrix,
            "fpr": round(confusion_matrix["fp"] / fpr_denominator, 4) if fpr_denominator > 0 else None,
            "asr": round(confusion_matrix["fn"] / asr_denominator, 4) if asr_denominator > 0 else None,
            "fpr_denominator": fpr_denominator,
            "asr_denominator": asr_denominator,
        }

    def _decision_to_predicted_label(self, decision: str) -> PredictedLabel:
        if decision in {"BLOCK", "SANITIZE"}:
            return "attack"
        return "benign"

    def _ensure_column(
        self,
        connection: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_definition: str,
    ) -> None:
        existing_columns = {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        if column_name in existing_columns:
            return
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )

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


shared_evaluation_store = EvaluationStore()
