"""Pydantic models and schemas for the protected chat system."""

from datetime import datetime
import uuid
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from ..core.security_modes import SecurityMode


AttachmentKind = Literal["image", "file"]
AttachmentDisposition = Literal["allow", "flag", "block"]
AttachmentExtractionStatus = Literal["success", "partial", "failed", "metadata_only"]
AttachmentExtractionMethod = Literal["plain_text", "json_text", "pdf_text", "pdf_ocr", "image_ocr", "none"]


class AttachmentRef(BaseModel):
    """Attachment payload submitted with a chat request."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Attachment identifier")
    name: str = Field(..., min_length=1, description="Original attachment name")
    mime_type: str = Field(..., min_length=1, description="Attachment MIME type")
    kind: AttachmentKind = Field(..., description="Attachment classification")
    content_b64: Optional[str] = Field(default=None, description="Base64 encoded attachment body")


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    user_id: str = Field(..., description="Unique identifier for user")
    prompt: str = Field(..., min_length=1, max_length=10000, description="User prompt/message")
    attachments: List[AttachmentRef] = Field(default_factory=list, description="Structured attachment payloads")
    requested_tools: Optional[List[str]] = Field(default=None, description="Optional explicit tool list")


class AttachmentResult(BaseModel):
    """Attachment analysis and extraction result returned to the client."""

    id: str = Field(..., description="Attachment identifier")
    name: str = Field(..., description="Original attachment name")
    mime_type: str = Field(..., description="Attachment MIME type")
    kind: AttachmentKind = Field(..., description="Attachment classification")
    size_bytes: int = Field(..., ge=0, description="Decoded attachment size in bytes")
    disposition: AttachmentDisposition = Field(..., description="Attachment policy disposition")
    flags: List[str] = Field(default_factory=list, description="Attachment security flags")
    text_preview: str = Field(default="", description="Bounded extracted text preview")
    metadata_only: bool = Field(default=False, description="Whether only metadata could be analyzed")
    extraction_status: AttachmentExtractionStatus = Field(..., description="Attachment extraction outcome")
    extraction_method: AttachmentExtractionMethod = Field(..., description="Attachment extraction method")
    extracted_chars: int = Field(default=0, ge=0, description="Number of extracted characters before truncation")
    truncated: bool = Field(default=False, description="Whether extracted text was truncated")
    ocr_used: bool = Field(default=False, description="Whether OCR was used during extraction")
    page_count: Optional[int] = Field(default=None, ge=1, description="Page count when applicable")
    extraction_reason: str = Field(default="", description="Internal extraction reason/status")
    signals: Dict[str, Any] = Field(default_factory=dict, description="Signals derived from extracted content")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    decision: str = Field(..., description="Final decision: ALLOW, SANITIZE, or BLOCK")
    risk_level: str = Field(..., description="Risk level: LOW, MEDIUM, HIGH, or CRITICAL")
    response: str = Field(..., description="Response message or reason for blocking")
    reason: str = Field(..., description="Detailed reason for the decision")
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique trace identifier for request tracking")
    signals: Optional[Dict[str, Any]] = Field(default=None, description="Short signals summary")
    user_id: str = Field(..., description="User ID from the request")
    security_mode: SecurityMode = Field(..., description="Security mode that was applied")
    tools_requested: List[str] = Field(default_factory=list, description="Requested tool names")
    tools_allowed: List[str] = Field(default_factory=list, description="Authorized tool names")
    tool_decisions: Dict[str, str] = Field(default_factory=dict, description="Per-tool allow or deny status")
    rag_context_used: bool = Field(default=False, description="Whether validated RAG context was used")
    rag_context_validated: bool = Field(default=False, description="Whether retrieved context was validated safe")
    attachments_received: List[str] = Field(default_factory=list, description="Attachment names received")
    attachments_flagged: List[str] = Field(default_factory=list, description="Attachment names flagged by defenses")
    attachment_results: List[AttachmentResult] = Field(default_factory=list, description="Attachment extraction and security results")
    model_called: bool = Field(default=False, description="Whether the request reached the language model")
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
