"""
Pydantic models and schemas for the protected chat system
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from ..core.security_modes import SecurityMode


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    user_id: str = Field(..., description="Unique identifier for the user")
    prompt: str = Field(..., min_length=1, max_length=10000, description="User prompt/message")
    mode: SecurityMode = Field(default=SecurityMode.NORMAL, description="Security mode")
    attachments: List[str] = Field(default=[], description="List of attachment identifiers")


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    decision: str = Field(..., description="Final decision: ALLOW, SANITIZE, or BLOCK")
    risk_level: str = Field(..., description="Risk level: LOW, MEDIUM, or HIGH")
    response: str = Field(..., description="Response message or reason for blocking")
    reason: str = Field(..., description="Detailed reason for the decision")
    user_id: str = Field(..., description="User ID from the request")
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
    event_type: str = Field(..., description="Type of event")
    user_id: Optional[str] = Field(None, description="User ID if applicable")
    decision: Optional[str] = Field(None, description="Decision made")
    risk_level: Optional[str] = Field(None, description="Risk level assessed")
    reason: Optional[str] = Field(None, description="Reason for decision")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default={}, description="Additional event metadata")


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
