"""
Admin endpoints for system configuration
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any

from ...models.schemas import (
    ConversationDetailResponse,
    ConversationsResponse,
    DecisionsResponse,
    EvaluationRecordResponse,
    EvaluationRecordsResponse,
    EvaluationReviewRequest,
    EventsResponse,
    ModeRequest,
    ModeResponse,
    RAGSourcesResponse,
    RAGStatusResponse,
)
from ...core.security_modes import SecurityMode
from ...services.conversation_memory import (
    ConversationMemoryError,
    ConversationNotFoundError,
    ConversationOwnershipError,
    shared_conversation_memory,
)
from ...services.evaluation_store import (
    EvaluationRecordNotFoundError,
    shared_evaluation_store,
)
from ...services.metrics_logger import shared_metrics_logger
from ...services.mode_manager import shared_mode_manager
from ...services.rag_manager import shared_rag_manager
from ...services.traffic_guard import shared_traffic_guard
from ..dependencies.auth import require_admin_api_key

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_api_key)],
)

# Initialize metrics logger
metrics_logger = shared_metrics_logger


@router.post("/mode", response_model=ModeResponse)
async def set_security_mode(request: ModeRequest):
    """Set the security mode for the system"""
    try:
        # Use shared mode manager to set the mode
        new_mode = shared_mode_manager.set_mode(request.mode)
        
        return ModeResponse(
            active_mode=new_mode,
            message=f"Security mode set to {new_mode.value}"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to set mode: {str(e)}")


@router.get("/mode", response_model=ModeResponse)
async def get_security_mode():
    """Get the current security mode"""
    current_mode = shared_mode_manager.get_mode()
    return ModeResponse(
        active_mode=current_mode,
        message=f"Current security mode is {current_mode.value}"
    )


@router.get("/events", response_model=EventsResponse)
async def get_events(limit: int = Query(default=50, ge=1, le=100)):
    """Get recent events"""
    try:
        events = await metrics_logger.get_events(limit)
        return EventsResponse(
            events=events,
            total_events=len(events),
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving events: {str(e)}")


@router.get("/decisions", response_model=DecisionsResponse)
async def get_decisions(page: int = Query(default=1, ge=1), limit: int = Query(default=10, ge=1, le=100)):
    """Get recent decisions"""
    try:
        decisions_page = await metrics_logger.get_decisions(page=page, limit=limit)
        return DecisionsResponse(
            decisions=decisions_page["decisions"],
            total_decisions=decisions_page["total_decisions"],
            limit=decisions_page["limit"],
            page=decisions_page["page"],
            total_pages=decisions_page["total_pages"],
            has_previous=decisions_page["has_previous"],
            has_next=decisions_page["has_next"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving decisions: {str(e)}")


@router.get("/events/old", response_model=EventsResponse)
async def get_events_old(limit: int = Query(default=50, ge=1, le=100)):
    """Get recent events (legacy endpoint)"""
    try:
        events_data = await metrics_logger.get_recent_events(limit)
        return EventsResponse(
            events=events_data,
            total_events=len(events_data),
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving events: {str(e)}")


@router.get("/metrics", response_model=Dict[str, Any])
async def get_metrics():
    """Get aggregate admin KPIs and decision/risk distributions."""
    try:
        guard_snapshot = await shared_traffic_guard.snapshot()
        payload = await metrics_logger.get_admin_metrics(guard_snapshot=guard_snapshot)
        payload["evaluation"] = await shared_evaluation_store.get_evaluation_metrics()
        payload["rag"] = await shared_rag_manager.get_status()
        return payload
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving metrics: {str(e)}")


@router.post("/reset-runtime", response_model=Dict[str, Any])
async def reset_runtime_metrics():
    """Reset in-memory runtime metrics for a fresh local test session."""

    try:
        metrics_logger.reset()
        shared_traffic_guard.reset()
        guard_snapshot = await shared_traffic_guard.snapshot()
        payload = await metrics_logger.get_admin_metrics(guard_snapshot=guard_snapshot)
        payload["evaluation"] = await shared_evaluation_store.get_evaluation_metrics()
        payload["rag"] = await shared_rag_manager.get_status()
        payload["message"] = "Runtime metrics reset"
        return payload
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting runtime metrics: {str(e)}")


@router.post("/evaluations/{trace_id}/review", response_model=EvaluationRecordResponse)
async def review_evaluation(trace_id: str, request: EvaluationReviewRequest):
    """Attach a verified ground-truth label to one evaluation record."""

    try:
        payload = await shared_evaluation_store.complete_review(
            trace_id=trace_id,
            ground_truth_label=request.ground_truth_label,
            reviewer_id=request.reviewer_id,
            review_note=request.review_note,
        )
        return EvaluationRecordResponse(**payload)
    except EvaluationRecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reviewing evaluation record: {str(e)}")


@router.get("/evaluations", response_model=EvaluationRecordsResponse)
async def list_evaluations(
    review_status: str | None = Query(default=None, pattern="^(pending|completed)$"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
):
    """List reviewable evaluation records for backend-only admin workflows."""

    try:
        payload = await shared_evaluation_store.list_records(
            review_status=review_status,
            page=page,
            limit=limit,
        )
        return EvaluationRecordsResponse(**payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving evaluation records: {str(e)}")


@router.get("/evaluations/{trace_id}", response_model=EvaluationRecordResponse)
async def get_evaluation(trace_id: str):
    """Return one evaluation record with review context."""

    try:
        payload = await shared_evaluation_store.get_record(trace_id)
        return EvaluationRecordResponse(**payload)
    except EvaluationRecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving evaluation record: {str(e)}")


@router.post("/rag/reindex", response_model=RAGStatusResponse)
async def reindex_rag():
    """Reindex the trusted local RAG corpus."""

    try:
        payload = await shared_rag_manager.reindex()
        return RAGStatusResponse(**payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reindexing RAG corpus: {str(e)}")


@router.get("/rag/status", response_model=RAGStatusResponse)
async def get_rag_status():
    """Get current RAG index status."""

    try:
        payload = await shared_rag_manager.get_status()
        return RAGStatusResponse(**payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving RAG status: {str(e)}")


@router.get("/rag/sources", response_model=RAGSourcesResponse)
async def get_rag_sources():
    """List indexed RAG sources."""

    try:
        sources = await shared_rag_manager.list_sources()
        return RAGSourcesResponse(
            sources=sources,
            total_sources=len(sources),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving RAG sources: {str(e)}")


@router.get("/conversations", response_model=ConversationsResponse)
async def get_conversations(
    user_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    """List persisted conversation summaries for local testing."""

    try:
        conversations = await shared_conversation_memory.list_conversations(user_id=user_id, limit=limit)
        return ConversationsResponse(
            conversations=conversations,
            total_conversations=len(conversations),
            limit=limit,
        )
    except ConversationMemoryError as exc:
        raise HTTPException(status_code=500, detail=f"Error retrieving conversations: {str(exc)}")


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(conversation_id: str):
    """Return one full persisted conversation transcript."""

    try:
        payload = await shared_conversation_memory.get_conversation(conversation_id)
        return ConversationDetailResponse(**payload)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ConversationOwnershipError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ConversationMemoryError as exc:
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation: {str(exc)}")
