// Type definitions based on backend schemas
export type SecurityMode = 'Off' | 'Weak' | 'Normal' | 'Strong';
export type Decision = 'ALLOW' | 'SANITIZE' | 'BLOCK';
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface ChatRequest {
  user_id: string;
  prompt: string;
  attachments?: string[];
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

export interface DecisionsResponse {
  decisions: ChatResponse[];
  total_decisions: number;
  limit: number;
  timestamp: string;
}

export interface Metrics {
  total_chat_traces: number;
  allow_count: number;
  sanitize_count: number;
  block_count: number;
  attack_success_rate: number;
  false_positive_rate: number;
  risk_distribution: Record<RiskLevel, number>;
  throughput_rps_placeholder: number | null;
  latency_p50_ms_placeholder: number | null;
  latency_p95_ms_placeholder: number | null;
}

export interface ChatMessage {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  decision?: Decision;
  risk_level?: RiskLevel;
  reason?: string;
  signals?: Record<string, any>;
  tools_requested?: string[];
  tools_allowed?: string[];
  rag_context_used?: boolean;
  rag_context_validated?: boolean;
}
