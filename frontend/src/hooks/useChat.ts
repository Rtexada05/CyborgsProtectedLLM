import { useState, useCallback } from 'react';
import { apiService } from '../services/api';
import { AttachmentRef, ChatRequest, ChatResponse, ChatMessage } from '../services/types';

export interface ComposePayload {
  prompt: string;
  requestedTools?: string[];
  attachments?: AttachmentRef[];
}

export const useChat = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(async (payload: string | ComposePayload, userId: string = 'demo-user') => {
    setIsLoading(true);
    setError(null);

    const normalizedPayload: ComposePayload = typeof payload === 'string'
      ? { prompt: payload, requestedTools: [], attachments: [] }
      : {
          prompt: payload.prompt,
          requestedTools: payload.requestedTools || [],
          attachments: payload.attachments || [],
        };

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: normalizedPayload.prompt,
      timestamp: new Date().toISOString(),
      attachments: normalizedPayload.attachments,
      tools_requested: normalizedPayload.requestedTools,
    };

    setMessages(prev => [...prev, userMessage]);

    try {
      const request: ChatRequest = {
        user_id: userId,
        prompt: normalizedPayload.prompt,
        attachments: normalizedPayload.attachments,
        requested_tools: normalizedPayload.requestedTools,
      };

      const response: ChatResponse = await apiService.sendChatMessage(request);

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: response.decision === 'BLOCK' ? 'system' : 'assistant',
        content: response.response,
        timestamp: response.timestamp,
        trace_id: response.trace_id,
        decision: response.decision,
        risk_level: response.risk_level,
        reason: response.reason,
        signals: response.signals,
        tools_requested: response.tools_requested,
        tools_allowed: response.tools_allowed,
        tool_decisions: response.tool_decisions,
        rag_context_used: response.rag_context_used,
        rag_context_validated: response.rag_context_validated,
        attachment_names: response.attachments_received,
        attachments_flagged: response.attachments_flagged,
        attachment_results: response.attachment_results,
        model_called: response.model_called,
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');

      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'system',
        content: 'Error: Failed to process your request. Please try again.',
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
  };
};
