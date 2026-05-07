import { useCallback, useEffect, useState } from 'react';
import { apiService } from '../services/api';
import { AttachmentRef, ChatRequest, ChatResponse, ChatMessage, RAGScope } from '../services/types';

export interface ComposePayload {
  prompt: string;
  requestedTools?: string[];
  attachments?: AttachmentRef[];
  ragEnabled?: boolean;
  ragScope?: RAGScope;
  ragDocumentIds?: string[];
}

const CHAT_MESSAGES_STORAGE_KEY = 'cyborgs.chat.messages';

const loadStoredMessages = (): ChatMessage[] => {
  if (typeof window === 'undefined') {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(CHAT_MESSAGES_STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

export const useChat = () => {
  const [messages, setMessages] = useState<ChatMessage[]>(() => loadStoredMessages());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    window.localStorage.setItem(CHAT_MESSAGES_STORAGE_KEY, JSON.stringify(messages));
  }, [messages]);

  const sendMessage = useCallback(async (payload: string | ComposePayload, userId: string = 'demo-user') => {
    setIsLoading(true);
    setError(null);

    const normalizedPayload: ComposePayload = typeof payload === 'string'
      ? { prompt: payload, requestedTools: [], attachments: [] }
      : {
          prompt: payload.prompt,
          requestedTools: payload.requestedTools || [],
          attachments: payload.attachments || [],
          ragEnabled: payload.ragEnabled ?? true,
          ragScope: payload.ragScope || 'default',
          ragDocumentIds: payload.ragDocumentIds || [],
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
        rag_enabled: normalizedPayload.ragEnabled ?? true,
        rag_scope: normalizedPayload.ragScope || 'default',
        rag_document_ids: normalizedPayload.ragDocumentIds || undefined,
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
        rag_retrieval_attempted: response.rag_retrieval_attempted,
        rag_sources_considered: response.rag_sources_considered,
        rag_chunks_retrieved: response.rag_chunks_retrieved,
        rag_chunks_used: response.rag_chunks_used,
        rag_chunks_dropped: response.rag_chunks_dropped,
        rag_sources_used: response.rag_sources_used,
        rag_warnings: response.rag_warnings,
        attachment_names: response.attachments_received,
        attachments_flagged: response.attachments_flagged,
        attachment_results: response.attachment_results,
        model_called: response.model_called,
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      const errorMessageText = err instanceof Error ? err.message : 'An error occurred';
      setError(errorMessageText);

      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'system',
        content: `Error: ${errorMessageText}`,
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
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(CHAT_MESSAGES_STORAGE_KEY);
    }
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
  };
};
