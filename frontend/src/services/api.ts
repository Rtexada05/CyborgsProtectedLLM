import {
  ChatRequest,
  ChatResponse,
  ModeRequest,
  ModeResponse,
  HealthResponse,
  EventsResponse,
  DecisionsResponse,
  AdminMetricsResponse,
} from './types';

class ApiService {
  private baseUrl: string;
  private clientApiKey?: string;

  constructor() {
    this.baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    this.clientApiKey = import.meta.env.VITE_CLIENT_API_KEY;
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);

    if (init.body && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    if (this.clientApiKey) {
      headers.set('X-API-Key', this.clientApiKey);
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers,
    });

    if (!response.ok) {
      let message = `Request failed with status ${response.status}`;

      try {
        const errorPayload = await response.json();
        message = errorPayload.detail || errorPayload.message || message;
      } catch {
        // Leave the default message when the response body is not JSON.
      }

      throw new Error(message);
    }

    return response.json() as Promise<T>;
  }

  async sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
    return this.request<ChatResponse>('/chat/', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getSecurityMode(): Promise<ModeResponse> {
    return this.request<ModeResponse>('/admin/mode');
  }

  async setSecurityMode(request: ModeRequest): Promise<ModeResponse> {
    return this.request<ModeResponse>('/admin/mode', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getEvents(limit: number = 50): Promise<EventsResponse> {
    return this.request<EventsResponse>(`/admin/events?limit=${limit}`);
  }

  async getDecisions(limit: number = 50): Promise<DecisionsResponse> {
    return this.request<DecisionsResponse>(`/admin/decisions?limit=${limit}`);
  }

  async getMetrics(): Promise<AdminMetricsResponse> {
    return this.request<AdminMetricsResponse>('/admin/metrics');
  }

  async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health/');
  }
}

export const apiService = new ApiService();
