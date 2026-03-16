import React from 'react';
import { ChatMessage } from '../../services/types';
import { DecisionBadge, RiskIndicator } from '../common/DecisionBadge';
import { ToolRequestBadge } from './ToolRequestBadge';
import { RAGStatusBadge } from './RAGStatusBadge';

interface ResponseCardProps {
  message: ChatMessage;
}

export const ResponseCard: React.FC<ResponseCardProps> = ({ message }) => {
  const isUser = message.type === 'user';
  const isSystem = message.type === 'system';

  const getMessageClass = () => {
    if (isUser) return 'user-message';
    if (isSystem) return 'bg-yellow-50 border border-yellow-200';
    return 'assistant-message';
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  return (
    <div className={`chat-message ${getMessageClass()} mb-4`}>
      {/* Message Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <span className="font-medium text-sm">
            {isUser ? 'You' : isSystem ? 'System' : 'Assistant'}
          </span>
          <span className="text-xs text-gray-500">
            {formatTimestamp(message.timestamp)}
          </span>
        </div>
        
        {/* Decision and Risk Indicators */}
        {!isUser && message.decision && (
          <div className="flex items-center space-x-2">
            <DecisionBadge decision={message.decision} />
            {message.risk_level && (
              <RiskIndicator riskLevel={message.risk_level} />
            )}
          </div>
        )}
      </div>

      {/* Message Content */}
      <div className="text-gray-900 whitespace-pre-wrap">
        {message.content}
      </div>

      {/* Security Details for Non-User Messages */}
      {!isUser && (
        <div className="mt-3 space-y-2">
          {/* Decision Reason */}
          {message.reason && (
            <div className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
              <span className="font-medium">Reason:</span> {message.reason}
            </div>
          )}

          {/* Tool Status */}
          {message.tools_requested && message.tools_requested.length > 0 && (
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600">Tools requested:</span>
              {message.tools_requested.map((tool, index) => (
                <ToolRequestBadge
                  key={index}
                  tool={tool}
                  allowed={message.tools_allowed?.includes(tool) || false}
                />
              ))}
            </div>
          )}

          {/* RAG Status */}
          {message.rag_context_used !== undefined && (
            <RAGStatusBadge
              used={message.rag_context_used}
              validated={message.rag_context_validated}
            />
          )}

          {/* Signals Summary */}
          {message.signals && Object.keys(message.signals).length > 0 && (
            <div className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
              <span className="font-medium">Security Signals:</span>
              <ul className="mt-1 space-y-1">
                {Object.entries(message.signals).map(([signalType, details]: [string, any]) => (
                  <li key={signalType} className="text-xs">
                    • {signalType}: {details.confidence ? `${(details.confidence * 100).toFixed(1)}% confidence` : 'detected'}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
