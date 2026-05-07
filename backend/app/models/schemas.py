"""Pydantic models and schemas for the protected chat system."""

from datetime import datetime
import uuid
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from ..core.security_modes import SecurityMode


AttachmentKind = Literal["image", "file"]
AttachmentDisposition = Literal["allow", "flag", "block"]
AttachmentExtractionStatus = Literal["success", "partial", "failed", "metadata_only"]
AttachmentExtractionMethod = Literal["plain_text", "json_text", "pdf_text", "pdf_ocr", "image_ocr", "docx_text", "none"]
RAGScope = Literal["default", "static_only", "user_uploads_only"]


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
    conversation_id: Optional[str] = Field(default=None, description="Conversation identifier for multi-turn memory")
    prompt: str = Field(..., min_length=1, max_length=10000, description="User prompt/message")
    attachments: List[AttachmentRef] = Field(default_factory=list, description="Structured attachment payloads")
    requested_tools: Optional[List[str]] = Field(default=None, description="Optional explicit tool list")
    rag_enabled: bool = Field(default=True, description="Whether retrieval-augmented generation may run")
    rag_scope: RAGScope = Field(default="default", description="Restrict retrieval scope")
    rag_document_ids: Optional[List[str]] = Field(default=None, description="Optional explicit document IDs for retrieval")


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
    conversation_id: str = Field(..., description="Conversation identifier used for memory persistence")
    memory_used: bool = Field(default=False, description="Whether conversation memory was loaded into the model prompt")
    memory_turns_loaded: int = Field(default=0, ge=0, description="Number of prior turns loaded from conversation memory")
    memory_chars_loaded: int = Field(default=0, ge=0, description="Character count loaded from conversation memory")
    memory_truncated: bool = Field(default=False, description="Whether older conversation turns were omitted from the model prompt")
    signals: Optional[Dict[str, Any]] = Field(default=None, description="Short signals summary")
    user_id: str = Field(..., description="User ID from the request")
    security_mode: SecurityMode = Field(..., description="Security mode that was applied")
    tools_requested: List[str] = Field(default_factory=list, description="Requested tool names")
    tools_allowed: List[str] = Field(default_factory=list, description="Authorized tool names")
    tool_decisions: Dict[str, str] = Field(default_factory=dict, description="Per-tool allow or deny status")
    rag_context_used: bool = Field(default=False, description="Whether validated RAG context was used")
    rag_context_validated: bool = Field(default=False, description="Whether retrieved context was validated safe")
    rag_retrieval_attempted: bool = Field(default=False, description="Whether RAG retrieval was attempted")
    rag_sources_considered: int = Field(default=0, ge=0, description="Number of candidate sources considered during retrieval")
    rag_chunks_retrieved: int = Field(default=0, ge=0, description="Number of retrieved chunks before filtering")
    rag_chunks_used: int = Field(default=0, ge=0, description="Number of chunks retained for the model")
    rag_chunks_dropped: int = Field(default=0, ge=0, description="Number of chunks dropped by validation or policy")
    rag_sources_used: List[str] = Field(default_factory=list, description="Document IDs used in final context")
    rag_warnings: List[str] = Field(default_factory=list, description="Warnings generated during retrieval or validation")
    attachments_received: List[str] = Field(default_factory=list, description="Attachment names received")
    attachments_flagged: List[str] = Field(default_factory=list, description="Attachment names flagged by defenses")
    attachment_results: List[AttachmentResult] = Field(default_factory=list, description="Attachment extraction and security results")
    model_called: bool = Field(default=False, description="Whether the request reached the language model")
    timestamp: datetime = Field(default_factory=datetime.now)


class RAGSourceRecord(BaseModel):
    """Admin-visible metadata for indexed RAG sources."""

    document_id: str = Field(..., description="Stable document identifier")
    title: str = Field(..., description="Source title")
    source_type: Literal["static_doc", "upload"] = Field(..., description="Source category")
    security_label: Literal["trusted", "user_supplied", "quarantined"] = Field(..., description="Source trust label")
    owner_user_id: Optional[str] = Field(default=None, description="Owning user for upload sources")
    source_path: str = Field(default="", description="Filesystem-relative or logical source path")
    chunk_count: int = Field(default=0, ge=0, description="Indexed chunk count")
    scan_flags: List[str] = Field(default_factory=list, description="Security scan flags for the source")
    retrieval_allowed: bool = Field(default=True, description="Whether the source is eligible for retrieval")
    ingested_at: Optional[str] = Field(default=None, description="Ingestion timestamp")
    expires_at: Optional[str] = Field(default=None, description="Expiration timestamp for transient uploads")


class RAGStatusResponse(BaseModel):
    """Admin-visible RAG status payload."""

    enabled: bool = Field(..., description="Whether RAG is enabled")
    provider: str = Field(..., description="Configured vector DB provider")
    collection_name: str = Field(..., description="Vector collection name")
    backend: str = Field(..., description="Underlying vector-store backend in use")
    point_count: int = Field(default=0, ge=0, description="Indexed vector count")
    source_count: int = Field(default=0, ge=0, description="Indexed source count")
    quarantined_source_count: int = Field(default=0, ge=0, description="Number of quarantined sources")
    embedding: Dict[str, Any] = Field(default_factory=dict, description="Embedding configuration details")
    indexed_at: str = Field(..., description="Timestamp of the last indexing refresh")
    warnings: List[str] = Field(default_factory=list, description="Runtime warnings affecting RAG")


class RAGSourcesResponse(BaseModel):
    """Admin-visible indexed source list."""

    sources: List[RAGSourceRecord] = Field(default_factory=list, description="Indexed source records")
    total_sources: int = Field(default=0, ge=0, description="Total number of indexed sources")
    timestamp: datetime = Field(default_factory=datetime.now)


class ConversationTurnRecord(BaseModel):
    """Admin-visible conversation turn record."""

    turn_id: str = Field(..., description="Unique turn identifier")
    sequence_number: int = Field(..., ge=1, description="Conversation-local order of the turn")
    role: str = Field(..., description="Stored turn role")
    content: str = Field(..., description="Rendered content shown in the chat")
    decision: Optional[str] = Field(default=None, description="Decision associated with assistant/system turns")
    risk_level: Optional[str] = Field(default=None, description="Risk level associated with assistant/system turns")
    trace_id: Optional[str] = Field(default=None, description="Trace identifier associated with the turn")
    created_at: str = Field(..., description="Turn creation timestamp")


class ConversationRecord(BaseModel):
    """Admin-visible conversation summary."""

    conversation_id: str = Field(..., description="Conversation identifier")
    user_id: str = Field(..., description="Owning user identifier")
    created_at: str = Field(..., description="Conversation creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    status: str = Field(..., description="Conversation status")
    turn_count: int = Field(default=0, ge=0, description="Number of persisted turns")


class ConversationDetailResponse(ConversationRecord):
    """Admin-visible conversation transcript."""

    turns: List[ConversationTurnRecord] = Field(default_factory=list, description="Ordered transcript turns")


class ConversationsResponse(BaseModel):
    """Admin-visible conversation list."""

    conversations: List[ConversationRecord] = Field(default_factory=list, description="Stored conversations")
    total_conversations: int = Field(default=0, ge=0, description="Total conversations returned")
    limit: int = Field(default=50, ge=1, description="Maximum conversations requested")
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
    total_decisions: int = Field(..., description="Total number of decisions available")
    limit: int = Field(..., description="Maximum number of decisions requested")
    page: int = Field(..., ge=1, description="Current decisions page")
    total_pages: int = Field(..., ge=1, description="Total number of decisions pages")
    has_previous: bool = Field(..., description="Whether a previous page exists")
    has_next: bool = Field(..., description="Whether a next page exists")
    timestamp: datetime = Field(default_factory=datetime.now)


EvaluationLabel = Literal["attack", "benign"]
ReviewStatus = Literal["pending", "completed"]


class EvaluationReviewRequest(BaseModel):
    """Request body for attaching a verified ground-truth label."""

    ground_truth_label: EvaluationLabel = Field(..., description="Verified label for the request")
    reviewer_id: Optional[str] = Field(default=None, description="Reviewer identifier")
    review_note: Optional[str] = Field(default=None, description="Optional review note")


class EvaluationRecordResponse(BaseModel):
    """Reviewable evaluation record."""

    trace_id: str = Field(..., description="Trace identifier for the request")
    created_at: str = Field(..., description="Record creation timestamp")
    user_id: str = Field(..., description="User identifier")
    conversation_id: Optional[str] = Field(default=None, description="Conversation identifier for the request")
    decision: str = Field(..., description="Gateway decision")
    predicted_label: EvaluationLabel = Field(..., description="Prediction derived from the gateway decision")
    prompt_text: str = Field(default="", description="Original prompt submitted for review")
    response_text: str = Field(default="", description="Gateway or model response returned for review")
    reason: str = Field(default="", description="Decision rationale captured at request time")
    risk_level: Optional[str] = Field(default=None, description="Risk level assigned to the request")
    security_mode: Optional[str] = Field(default=None, description="Security mode active during the request")
    ground_truth_label: Optional[EvaluationLabel] = Field(default=None, description="Verified label when reviewed")
    review_status: ReviewStatus = Field(..., description="Whether the record has been reviewed")
    reviewed_at: Optional[str] = Field(default=None, description="Review completion timestamp")
    reviewer_id: Optional[str] = Field(default=None, description="Reviewer identifier")
    review_note: Optional[str] = Field(default=None, description="Optional reviewer note")


class EvaluationRecordsResponse(BaseModel):
    """Paginated admin-visible evaluation review queue."""

    evaluations: List[EvaluationRecordResponse] = Field(default_factory=list, description="Evaluation records")
    total_evaluations: int = Field(default=0, ge=0, description="Total records matching the filter")
    page: int = Field(default=1, ge=1, description="Current page number")
    limit: int = Field(default=50, ge=1, description="Maximum records requested")
    total_pages: int = Field(default=1, ge=1, description="Total number of pages")
    has_previous: bool = Field(default=False, description="Whether a previous page exists")
    has_next: bool = Field(default=False, description="Whether a next page exists")
    timestamp: datetime = Field(default_factory=datetime.now)
