import { useState, useCallback } from 'react';
import { apiService } from '../services/api';
import { ChatRequest, ChatResponse, ChatMessage } from '../services/types';

export const useChat = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(async (prompt: string, userId: string = 'demo-user') => {
    setIsLoading(true);
    setError(null);

    // Add user message
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: prompt,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);

    try {
      const request: ChatRequest = {
        user_id: userId,
        prompt,
        attachments: [],
        requested_tools: []
      };

      const response: ChatResponse = await apiService.sendChatMessage(request);

      // Add assistant/system response
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: response.decision === 'BLOCK' ? 'system' : 'assistant',
        content: response.response,
        timestamp: response.timestamp,
        decision: response.decision,
        risk_level: response.risk_level,
        reason: response.reason,
        signals: response.signals,
        tools_requested: request.requested_tools,
        tools_allowed: response.decision === 'ALLOW' && request.requested_tools ? request.requested_tools : [],
        rag_context_used: false, // Would be determined by backend
        rag_context_validated: false // Would be determined by backend
      };

      setMessages(prev => [...prev, assistantMessage]);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      
      // Add error message
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'system',
        content: 'Error: Failed to process your request. Please try again.',
        timestamp: new Date().toISOString()
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
    clearMessages
  };
};
