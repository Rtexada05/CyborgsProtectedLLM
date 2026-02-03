"""
Admin endpoints for system configuration
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any

from ...models.schemas import ModeRequest, ModeResponse, EventsResponse
from ...core.security_modes import SecurityMode
from ...services.metrics_logger import shared_metrics_logger

router = APIRouter(prefix="/admin", tags=["admin"])

# In-memory storage for current mode (in production, use database)
current_mode: SecurityMode = SecurityMode.NORMAL

# Initialize metrics logger
metrics_logger = shared_metrics_logger


@router.post("/mode", response_model=ModeResponse)
async def set_security_mode(request: ModeRequest):
    """Set the security mode for the system"""
    global current_mode
    
    try:
        current_mode = request.mode
        return ModeResponse(
            active_mode=current_mode,
            message=f"Security mode set to {current_mode.value}"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to set mode: {str(e)}")


@router.get("/mode", response_model=ModeResponse)
async def get_security_mode():
    """Get the current security mode"""
    return ModeResponse(
        active_mode=current_mode,
        message=f"Current security mode is {current_mode.value}"
    )


@router.get("/events", response_model=EventsResponse)
async def get_recent_events(limit: int = Query(default=50, ge=1, le=100, description="Maximum number of events to return")):
    """Get the most recent events from the metrics logger"""
    try:
        # Get recent events from metrics logger
        events = await metrics_logger.get_recent_events(limit=limit)
        
        return EventsResponse(
            events=events,
            total_events=len(events),
            limit=limit
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve events: {str(e)}"
        )
