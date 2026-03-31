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

  const formatExtractionLabel = (method?: string) => {
    switch (method) {
      case 'plain_text':
        return 'Plain text';
      case 'json_text':
        return 'JSON text';
      case 'pdf_text':
        return 'PDF text';
      case 'pdf_ocr':
        return 'PDF OCR';
      case 'image_ocr':
        return 'Image OCR';
      default:
        return 'Metadata only';
    }
  };

  return (
    <div className={`chat-message ${getMessageClass()} mb-4`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <span className="text-base font-medium">
            {isUser ? 'You' : isSystem ? 'System' : 'Assistant'}
          </span>
          <span className="text-sm text-gray-500">
            {formatTimestamp(message.timestamp)}
          </span>
        </div>

        {!isUser && message.decision && (
          <div className="flex items-center space-x-2">
            <DecisionBadge decision={message.decision} />
            {message.risk_level && (
              <RiskIndicator riskLevel={message.risk_level} />
            )}
          </div>
        )}
      </div>

      <div className="whitespace-pre-wrap text-base leading-7 text-gray-900">
        {message.content}
      </div>

      {message.attachments && message.attachments.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {message.attachments.map((attachment) => (
            <span key={attachment.id} className="inline-flex items-center rounded-full border border-gray-200 bg-gray-100 px-3 py-1.5 text-sm text-gray-700">
              {attachment.name}
            </span>
          ))}
        </div>
      )}

      {!isUser && (
        <div className="mt-3 space-y-2">
          {message.trace_id && (
            <div className="font-mono text-sm text-gray-500">Trace ID: {message.trace_id}</div>
          )}

          {message.reason && (
            <div className="rounded bg-gray-50 p-3 text-base text-gray-600">
              <span className="font-medium">Reason:</span> {message.reason}
            </div>
          )}

          {message.tools_requested && message.tools_requested.length > 0 && (
            <div className="flex items-center flex-wrap gap-2">
              <span className="text-base text-gray-600">Tools requested:</span>
              {message.tools_requested.map((tool, index) => (
                <ToolRequestBadge
                  key={index}
                  tool={tool}
                  allowed={message.tools_allowed?.includes(tool) || false}
                />
              ))}
            </div>
          )}

          {message.rag_context_used !== undefined && (
            <RAGStatusBadge
              used={message.rag_context_used}
              validated={message.rag_context_validated}
            />
          )}

          {message.attachment_names && message.attachment_names.length > 0 && (
            <div className="rounded bg-gray-50 p-3 text-base text-gray-600">
              <span className="font-medium">Attachments:</span> {message.attachment_names.join(', ')}
              {message.attachments_flagged && message.attachments_flagged.length > 0 && (
                <div className="mt-1 text-sm text-danger-700">
                  Flagged: {message.attachments_flagged.join(', ')}
                </div>
              )}
            </div>
          )}

          {message.attachment_results && message.attachment_results.length > 0 && (
            <div className="rounded bg-gray-50 p-3 text-base text-gray-600">
              <div className="font-medium">Attachment analysis:</div>
              <div className="mt-2 space-y-2">
                {message.attachment_results.map((attachment) => (
                  <div key={attachment.id} className="rounded border border-gray-200 bg-white p-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-gray-800">{attachment.name}</span>
                      <span className={`rounded-full px-2 py-0.5 text-xs ${attachment.disposition === 'block' ? 'bg-red-100 text-red-700' : attachment.disposition === 'flag' ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`}>
                        {attachment.disposition}
                      </span>
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700">
                        {formatExtractionLabel(attachment.extraction_method)}
                      </span>
                      <span className="text-xs text-gray-500">
                        {attachment.extraction_status}
                        {attachment.ocr_used ? ' • OCR used' : ''}
                        {attachment.page_count ? ` • ${attachment.page_count} page${attachment.page_count > 1 ? 's' : ''}` : ''}
                      </span>
                    </div>
                    <div className="mt-1 text-xs text-gray-500">
                      {attachment.extracted_chars} chars extracted
                      {attachment.truncated ? ' • truncated' : ''}
                      {attachment.metadata_only ? ' • metadata only' : ''}
                    </div>
                    {attachment.flags.length > 0 && (
                      <div className="mt-1 text-xs text-red-700">
                        Flags: {attachment.flags.join(', ')}
                      </div>
                    )}
                    {attachment.extraction_reason && (
                      <div className="mt-1 text-xs text-gray-500">
                        Reason: {attachment.extraction_reason}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {message.model_called !== undefined && (
            <div className="text-sm text-gray-500">
              Model called: {message.model_called ? 'yes' : 'no'}
            </div>
          )}

          {message.signals && Object.keys(message.signals).length > 0 && (
            <div className="rounded bg-gray-50 p-3 text-base text-gray-600">
              <span className="font-medium">Security Signals:</span>
              <ul className="mt-1 space-y-1">
                {Object.entries(message.signals).map(([signalType, details]: [string, any]) => (
                  <li key={signalType} className="text-sm">
                    • {signalType}: {typeof details === 'boolean' ? (details ? 'detected' : 'clear') : Array.isArray(details) ? (details.length ? details.join(', ') : 'none') : 'detected'}
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
