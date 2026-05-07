"""
Chat endpoint with protection mechanisms
"""

import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from ...models.schemas import ChatRequest, ChatResponse
from ..dependencies.auth import get_client_ip, require_client_api_key
from ...controller.defense_controller import DefenseController
from ...core.config import settings
from ...services.conversation_memory import (
    ConversationMemoryError,
    ConversationNotFoundError,
    ConversationOwnershipError,
    InvalidConversationIdError,
    shared_conversation_memory,
)
from ...services.metrics_logger import shared_metrics_logger
from ...services.mode_manager import shared_mode_manager
from ...services.traffic_guard import AdmissionResult, shared_traffic_guard

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize defense controller
defense_controller = DefenseController()


@router.post("", response_model=ChatResponse, include_in_schema=False)
@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request, api_key: str = Depends(require_client_api_key)):
    """Process chat request with protection mechanisms"""
    trace_id = getattr(http_request.state, "trace_id", str(uuid.uuid4()))
    client_ip = get_client_ip(http_request)
    api_key_fingerprint = shared_traffic_guard.fingerprint_api_key(api_key)
    admission: AdmissionResult | None = None
    conversation_id: str | None = None
    persist_memory = True

    try:
        # Always use the global security mode (ignore request mode)
        current_mode = shared_mode_manager.get_mode().value

        try:
            conversation = await shared_conversation_memory.get_or_create_conversation(request.conversation_id, request.user_id)
            conversation_id = conversation["conversation_id"]
            await shared_conversation_memory.append_turn(
                conversation_id,
                request.user_id,
                "user",
                request.prompt,
                trace_id=trace_id,
            )
        except (InvalidConversationIdError, ConversationNotFoundError):
            raise
        except ConversationOwnershipError:
            raise
        except ConversationMemoryError as exc:
            persist_memory = False
            conversation_id = request.conversation_id or str(uuid.uuid4())
            await shared_metrics_logger.log_event(
                event_type="conversation_memory_error",
                trace_id=trace_id,
                user_id=request.user_id,
                details={"error": str(exc), "conversation_id": request.conversation_id},
            )
            conversation_id = None

        admission = await shared_traffic_guard.admit(
            api_key=api_key,
            client_ip=client_ip,
            user_id=request.user_id,
        )
        await _log_alert_events(trace_id, request.user_id, admission.alert_events)

        if not admission.admitted:
            await _log_rejection_event(
                trace_id=trace_id,
                user_id=request.user_id,
                api_key_fingerprint=api_key_fingerprint,
                client_ip=client_ip,
                admission=admission,
            )
            raise HTTPException(
                status_code=429,
                detail={
                    "code": admission.reason_code,
                    "message": admission.message,
                    "retry_after_seconds": admission.retry_after_seconds,
                },
                headers={"Retry-After": str(admission.retry_after_seconds or 1)},
            )

        response = await asyncio.wait_for(
            defense_controller.handle_request(
                user_id=request.user_id,
                prompt=request.prompt,
                mode=current_mode,
                attachments=request.attachments,
                requested_tools=request.requested_tools,
                rag_enabled=request.rag_enabled,
                rag_scope=request.rag_scope,
                rag_document_ids=request.rag_document_ids,
                trace_id=trace_id,
                conversation_id=conversation_id,
            ),
            timeout=settings.CHAT_REQUEST_TIMEOUT_SECONDS,
        )

        if persist_memory and conversation_id:
            try:
                await shared_conversation_memory.append_turn(
                    conversation_id,
                    request.user_id,
                    "assistant",
                    response.response,
                    decision=response.decision,
                    risk_level=response.risk_level,
                    trace_id=trace_id,
                )
            except ConversationMemoryError as exc:
                await shared_metrics_logger.log_event(
                    event_type="conversation_memory_error",
                    trace_id=trace_id,
                    user_id=request.user_id,
                    details={"error": str(exc), "conversation_id": conversation_id},
                )

        return response
    except (InvalidConversationIdError, ConversationNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ConversationOwnershipError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except asyncio.TimeoutError:
        if admission is not None and admission.admitted:
            await shared_traffic_guard.release(timed_out=True)
            admission = None
        await shared_metrics_logger.log_event(
            event_type="chat_timeout",
            trace_id=trace_id,
            user_id=request.user_id,
            details={
                "reason_code": "chat_processing_timeout",
                "message": "Chat processing timed out",
                "api_key_fingerprint": api_key_fingerprint,
                "client_ip": client_ip,
                "timeout_seconds": settings.CHAT_REQUEST_TIMEOUT_SECONDS,
                "retry_after_seconds": None,
            },
        )
        raise HTTPException(
            status_code=504,
            detail={
                "code": "chat_processing_timeout",
                "message": "Chat processing timed out",
                "retry_after_seconds": None,
            },
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Processing error: {str(e)}"
        )
    finally:
        if admission is not None and admission.admitted:
            await shared_traffic_guard.release()


async def _log_rejection_event(
    trace_id: str,
    user_id: str,
    api_key_fingerprint: str,
    client_ip: str,
    admission: AdmissionResult,
) -> None:
    event_type = "rate_limit_rejected"
    if admission.reason_code in {"user_minute_quota_exceeded", "user_daily_quota_exceeded"}:
        event_type = "quota_rejected"
    elif admission.reason_code == "chat_capacity_exceeded":
        event_type = "concurrency_rejected"

    await shared_metrics_logger.log_event(
        event_type=event_type,
        trace_id=trace_id,
        user_id=user_id,
        details={
            "reason_code": admission.reason_code,
            "message": admission.message,
            "api_key_fingerprint": api_key_fingerprint,
            "client_ip": client_ip,
            "retry_after_seconds": admission.retry_after_seconds,
            "active_in_flight": admission.active_in_flight,
        },
    )


async def _log_alert_events(trace_id: str, user_id: str, alert_events: list[dict]) -> None:
    for alert_event in alert_events:
        await shared_metrics_logger.log_event(
            event_type="traffic_spike_alert",
            trace_id=trace_id,
            user_id=user_id,
            details={
                "reason_code": alert_event["code"],
                "level": alert_event["level"],
                "threshold": alert_event["threshold"],
                "window_seconds": alert_event["window_seconds"],
                "current_value": alert_event["current_value"],
                "triggered_at": alert_event["triggered_at"],
            },
        )
