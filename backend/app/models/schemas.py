"""
Pydantic models and schemas for the protected chat system
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from ..core.security_modes import SecurityMode


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    user_id: str = Field(..., description="Unique identifier for user")
    prompt: str = Field(..., min_length=1, max_length=10000, description="User prompt/message")
    attachments: List[str] = Field(default=[], description="List of attachment identifiers")
    requested_tools: Optional[List[str]] = Field(default=None, description="Optional explicit tool list")


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    decision: str = Field(..., description="Final decision: ALLOW, SANITIZE, or BLOCK")
    risk_level: str = Field(..., description="Risk level: LOW, MEDIUM, HIGH, or CRITICAL")
    response: str = Field(..., description="Response message or reason for blocking")
    reason: str = Field(..., description="Detailed reason for the decision")
    trace_id: str = Field(default_factory=uuid.uuid4, description="Unique trace identifier for request tracking")
    signals: Optional[Dict[str, Any]] = Field(default=None, description="Short signals summary")
    user_id: str = Field(..., description="User ID from the request")
    security_mode: SecurityMode = Field(..., description="Security mode that was applied")
    timestamp: datetime = Field(default_factory=datetime.now)


class ModeRequest(BaseModel):
    """Request model for mode configuration"""
    mode: SecurityMode = Field(..., description="Security mode to set")


class ModeResponse(BaseModel):
    """Response model for mode configuration"""
    active_mode: SecurityMode = Field(..., description="Currently active security mode")
    message: str = Field(default="Mode updated successfully", description="Status message")


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str = Field(default="ok", description="Health status")
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = Field(default="1.0.0", description="API version")


class LogEvent(BaseModel):
    """Model for logging events"""
    trace_id: str = Field(..., description="Trace identifier for request tracking")
    timestamp: str = Field(..., description="Event timestamp as string")
    user_id: str = Field(..., description="User ID")
    event_type: str = Field(..., description="Type of event (e.g., risk_scored, decision_made, rag_checked, tool_checked)")
    details: Dict[str, Any] = Field(..., description="Event details")


class SecuritySignal(BaseModel):
    """Model for security signals from various detectors"""
    signal_type: str = Field(..., description="Type of security signal")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    details: Dict[str, Any] = Field(default={}, description="Signal details")
    detected_at: datetime = Field(default_factory=datetime.now)


class EventsResponse(BaseModel):
    """Response model for events endpoint"""
    events: List[Dict[str, Any]] = Field(..., description="List of recent events")
    total_events: int = Field(..., description="Total number of events returned")
    limit: int = Field(..., description="Maximum number of events requested")
    timestamp: datetime = Field(default_factory=datetime.now)


class DecisionsResponse(BaseModel):
    """Response model for decisions endpoint"""
    decisions: List[Dict[str, Any]] = Field(..., description="List of recent decisions")
    total_decisions: int = Field(..., description="Total number of decisions returned")
    limit: int = Field(..., description="Maximum number of decisions requested")
    timestamp: datetime = Field(default_factory=datetime.now)
