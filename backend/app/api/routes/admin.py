"""
Admin endpoints for system configuration
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any

from ...models.schemas import ModeRequest, ModeResponse, EventsResponse, DecisionsResponse
from ...core.security_modes import SecurityMode
from ...services.metrics_logger import shared_metrics_logger
from ...services.mode_manager import shared_mode_manager

router = APIRouter(prefix="/admin", tags=["admin"])

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
async def get_decisions(limit: int = Query(default=50, ge=1, le=100)):
    """Get recent decisions"""
    try:
        decisions = await metrics_logger.get_decisions(limit)
        return DecisionsResponse(
            decisions=decisions,
            total_decisions=len(decisions),
            limit=limit
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
        return await metrics_logger.get_admin_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving metrics: {str(e)}")
