// Type definitions based on backend schemas
export type SecurityMode = 'Off' | 'Weak' | 'Normal' | 'Strong';
export type Decision = 'ALLOW' | 'SANITIZE' | 'BLOCK';
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type AttachmentKind = 'image' | 'file';
export type ToolDecision = 'allowed' | 'denied';
export type AttachmentDisposition = 'allow' | 'flag' | 'block';
export type AttachmentExtractionStatus = 'success' | 'partial' | 'failed' | 'metadata_only';
export type AttachmentExtractionMethod = 'plain_text' | 'json_text' | 'pdf_text' | 'pdf_ocr' | 'image_ocr' | 'none';

export interface AttachmentRef {
  id: string;
  name: string;
  mime_type: string;
  kind: AttachmentKind;
  content_b64?: string;
}

export interface AttachmentResult {
  id: string;
  name: string;
  mime_type: string;
  kind: AttachmentKind;
  size_bytes: number;
  disposition: AttachmentDisposition;
  flags: string[];
  text_preview: string;
  metadata_only: boolean;
  extraction_status: AttachmentExtractionStatus;
  extraction_method: AttachmentExtractionMethod;
  extracted_chars: number;
  truncated: boolean;
  ocr_used: boolean;
  page_count?: number | null;
  extraction_reason: string;
  signals: Record<string, any>;
}

export type ToolDecisionMap = Record<string, ToolDecision>;

export interface ChatRequest {
  user_id: string;
  prompt: string;
  attachments?: AttachmentRef[];
  requested_tools?: string[];
}

export interface ChatResponse {
  decision: Decision;
  risk_level: RiskLevel;
  response: string;
  reason: string;
  trace_id: string;
  signals?: Record<string, any>;
  user_id: string;
  security_mode: SecurityMode;
  tools_requested: string[];
  tools_allowed: string[];
  tool_decisions: ToolDecisionMap;
  rag_context_used: boolean;
  rag_context_validated: boolean;
  attachments_received: string[];
  attachments_flagged: string[];
  attachment_results: AttachmentResult[];
  model_called: boolean;
  timestamp: string;
}

export interface ModeRequest {
  mode: SecurityMode;
}

export interface ModeResponse {
  active_mode: SecurityMode;
  message: string;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
}

export interface LogEvent {
  trace_id: string;
  timestamp: string;
  user_id: string;
  event_type: string;
  details: Record<string, any>;
}

export interface SecuritySignal {
  signal_type: string;
  confidence: number;
  details: Record<string, any>;
  detected_at: string;
}

export interface EventsResponse {
  events: LogEvent[];
  total_events: number;
  limit: number;
  timestamp: string;
}

export interface AdminDecisionRecord extends ChatResponse {
  prompt_preview?: string;
}

export interface DecisionsResponse {
  decisions: AdminDecisionRecord[];
  total_decisions: number;
  limit: number;
  timestamp: string;
}

export interface AdminMetricsResponse {
  traffic: {
    total_chat_traces: number;
    total_decision_records: number;
    requests_per_hour: number;
  };
  decisions: {
    distribution: Record<Decision, number>;
    blocked_rate_percent: number;
    sanitized_rate_percent: number;
    allowed_rate_percent: number;
  };
  risk: {
    distribution: Record<string, number>;
    high_risk_rate_percent: number;
    medium_risk_rate_percent: number;
    low_risk_rate_percent: number;
  };
  kpis: {
    attack_success_rate_percent: number;
    false_positive_proxy_percent: number;
    throughput_rps_placeholder: number | null;
    latency_p50_ms_placeholder: number | null;
    latency_p95_ms_placeholder: number | null;
  };
  generated_at: string;
}

export interface ChatMessage {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  trace_id?: string;
  decision?: Decision;
  risk_level?: RiskLevel;
  reason?: string;
  signals?: Record<string, any>;
  attachments?: AttachmentRef[];
  attachment_names?: string[];
  attachments_flagged?: string[];
  attachment_results?: AttachmentResult[];
  tools_requested?: string[];
  tools_allowed?: string[];
  tool_decisions?: ToolDecisionMap;
  rag_context_used?: boolean;
  rag_context_validated?: boolean;
  model_called?: boolean;
}
