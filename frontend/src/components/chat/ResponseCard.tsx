import React from 'react';
import { Bot, FileSearch, FileText, Paperclip, UserCircle2 } from 'lucide-react';
import { ChatMessage } from '../../services/types';
import { DecisionBadge, RiskIndicator } from '../common/DecisionBadge';
import { ToolRequestBadge } from './ToolRequestBadge';
import { RAGStatusBadge } from './RAGStatusBadge';

interface ResponseCardProps {
  message: ChatMessage;
}

const renderInlineMarkdown = (text: string) => {
  const tokens = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);

  return tokens.filter(Boolean).map((token, index) => {
    if (token.startsWith('**') && token.endsWith('**')) {
      return (
        <strong key={index} className="font-semibold text-white">
          {token.slice(2, -2)}
        </strong>
      );
    }

    if (token.startsWith('`') && token.endsWith('`')) {
      return (
        <code key={index} className="rounded-md border border-white/10 bg-cyber-950/70 px-1.5 py-0.5 text-[0.95em] text-primary-100">
          {token.slice(1, -1)}
        </code>
      );
    }

    return <React.Fragment key={index}>{token}</React.Fragment>;
  });
};

const renderFormattedContent = (content: string) => {
  const lines = content.split('\n');
  const blocks: React.ReactNode[] = [];
  let paragraphLines: string[] = [];
  let orderedItems: string[] = [];
  let unorderedItems: string[] = [];

  const flushParagraph = () => {
    if (!paragraphLines.length) {
      return;
    }

    const paragraph = paragraphLines.join(' ').trim();
    if (paragraph) {
      blocks.push(
        <p key={`p-${blocks.length}`} className="message-paragraph">
          {renderInlineMarkdown(paragraph)}
        </p>
      );
    }
    paragraphLines = [];
  };

  const flushOrderedList = () => {
    if (!orderedItems.length) {
      return;
    }

    blocks.push(
      <ol key={`ol-${blocks.length}`} className="message-list message-list-ordered">
        {orderedItems.map((item, index) => (
          <li key={`ol-item-${index}`}>{renderInlineMarkdown(item)}</li>
        ))}
      </ol>
    );
    orderedItems = [];
  };

  const flushUnorderedList = () => {
    if (!unorderedItems.length) {
      return;
    }

    blocks.push(
      <ul key={`ul-${blocks.length}`} className="message-list message-list-unordered">
        {unorderedItems.map((item, index) => (
          <li key={`ul-item-${index}`}>{renderInlineMarkdown(item)}</li>
        ))}
      </ul>
    );
    unorderedItems = [];
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (!line) {
      flushParagraph();
      flushOrderedList();
      flushUnorderedList();
      continue;
    }

    const orderedMatch = line.match(/^\d+\.\s+(.*)$/);
    if (orderedMatch) {
      flushParagraph();
      flushUnorderedList();
      orderedItems.push(orderedMatch[1]);
      continue;
    }

    const unorderedMatch = line.match(/^[-*]\s+(.*)$/);
    if (unorderedMatch) {
      flushParagraph();
      flushOrderedList();
      unorderedItems.push(unorderedMatch[1]);
      continue;
    }

    flushOrderedList();
    flushUnorderedList();
    paragraphLines.push(line);
  }

  flushParagraph();
  flushOrderedList();
  flushUnorderedList();

  return blocks.length > 0 ? blocks : <p className="message-paragraph">{content}</p>;
};

export const ResponseCard: React.FC<ResponseCardProps> = ({ message }) => {
  const isUser = message.type === 'user';
  const isSystem = message.type === 'system';

  const getMessageClass = () => {
    if (isUser) return 'user-message';
    if (isSystem) return 'system-message';
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
      case 'docx_text':
        return 'DOCX text';
      default:
        return 'Metadata only';
    }
  };

  const AuthorIcon = isUser ? UserCircle2 : Bot;

  return (
    <div className={`chat-message ${getMessageClass()} mb-4 animate-enter`}>
      <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-2xl border border-white/10 bg-cyber-950/50 p-2">
            <AuthorIcon className="h-5 w-5 text-primary-300" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-base font-semibold text-white">
                {isUser ? 'You' : isSystem ? 'System' : 'Assistant'}
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-xs uppercase tracking-[0.2em] text-cyber-400">
                {formatTimestamp(message.timestamp)}
              </span>
            </div>
            {!isUser && message.trace_id && (
              <div className="mt-1 font-mono text-xs text-cyber-400">Trace ID: {message.trace_id}</div>
            )}
          </div>
        </div>

        {!isUser && message.decision && (
          <div className="flex flex-wrap items-center gap-2">
            <DecisionBadge decision={message.decision} />
            {message.risk_level && <RiskIndicator riskLevel={message.risk_level} />}
          </div>
        )}
      </div>

      <div className="message-content text-base leading-7 text-cyber-100">
        {renderFormattedContent(message.content)}
      </div>

      {message.attachments && message.attachments.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {message.attachments.map((attachment) => (
            <span key={attachment.id} className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-cyber-200">
              <Paperclip className="h-3.5 w-3.5 text-primary-300" />
              {attachment.name}
            </span>
          ))}
        </div>
      )}

      {!isUser && (
        <div className="mt-4 space-y-3">
          {message.reason && (
            <div className="subtle-panel">
              <div className="mb-1 text-xs font-semibold uppercase tracking-[0.2em] text-primary-300">Decision rationale</div>
              <div className="text-sm text-cyber-200">{message.reason}</div>
            </div>
          )}

          {message.tools_requested && message.tools_requested.length > 0 && (
            <div className="subtle-panel">
              <div className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-primary-300">Tool requests</div>
              <div className="flex flex-wrap items-center gap-2">
                {message.tools_requested.map((tool, index) => (
                  <ToolRequestBadge
                    key={index}
                    tool={tool}
                    allowed={message.tools_allowed?.includes(tool) || false}
                  />
                ))}
              </div>
            </div>
          )}

          {message.rag_context_used !== undefined && (
            <div className="subtle-panel">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-sm text-cyber-200">
                  <FileSearch className="h-4 w-4 text-primary-300" />
                  Retrieval context status
                </div>
                <RAGStatusBadge
                  used={message.rag_context_used}
                  validated={message.rag_context_validated}
                />
              </div>
              <div className="mt-3 grid gap-2 text-sm text-cyber-200 sm:grid-cols-2 xl:grid-cols-4">
                <div>Attempted: {message.rag_retrieval_attempted ? 'yes' : 'no'}</div>
                <div>Sources considered: {message.rag_sources_considered ?? 0}</div>
                <div>Chunks retrieved: {message.rag_chunks_retrieved ?? 0}</div>
                <div>Chunks used: {message.rag_chunks_used ?? 0}</div>
              </div>
              {message.rag_sources_used && message.rag_sources_used.length > 0 && (
                <div className="mt-2 text-sm text-cyber-200">
                  Sources used: {message.rag_sources_used.join(', ')}
                </div>
              )}
              {message.rag_warnings && message.rag_warnings.length > 0 && (
                <div className="mt-2 text-sm text-warning-100">
                  RAG warnings: {message.rag_warnings.join(', ')}
                </div>
              )}
            </div>
          )}

          {message.attachment_names && message.attachment_names.length > 0 && (
            <div className="subtle-panel">
              <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-primary-300">
                <FileText className="h-4 w-4" />
                Attachments received
              </div>
              <div className="text-sm text-cyber-200">{message.attachment_names.join(', ')}</div>
              {message.attachments_flagged && message.attachments_flagged.length > 0 && (
                <div className="mt-2 text-sm text-danger-100">
                  Flagged: {message.attachments_flagged.join(', ')}
                </div>
              )}
            </div>
          )}

          {message.attachment_results && message.attachment_results.length > 0 && (
            <div className="subtle-panel">
              <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-primary-300">
                <FileSearch className="h-4 w-4" />
                Attachment analysis
              </div>
              <div className="space-y-2">
                {message.attachment_results.map((attachment) => (
                  <div key={attachment.id} className="rounded-2xl border border-white/10 bg-cyber-950/55 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-white">{attachment.name}</span>
                      <span className={`rounded-full px-2 py-0.5 text-xs ${attachment.disposition === 'block' ? 'bg-danger-500/15 text-danger-100' : attachment.disposition === 'flag' ? 'bg-warning-500/15 text-warning-100' : 'bg-success-500/15 text-success-100'}`}>
                        {attachment.disposition}
                      </span>
                      <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-xs text-cyber-300">
                        {formatExtractionLabel(attachment.extraction_method)}
                      </span>
                      <span className="text-xs text-cyber-400">
                        {attachment.extraction_status}
                        {attachment.ocr_used ? ' | OCR used' : ''}
                        {attachment.page_count ? ` | ${attachment.page_count} page${attachment.page_count > 1 ? 's' : ''}` : ''}
                      </span>
                    </div>
                    <div className="mt-1 text-xs text-cyber-400">
                      {attachment.extracted_chars} chars extracted
                      {attachment.truncated ? ' | truncated' : ''}
                      {attachment.metadata_only ? ' | metadata only' : ''}
                    </div>
                    {attachment.flags.length > 0 && (
                      <div className="mt-1 text-xs text-danger-100">
                        Flags: {attachment.flags.join(', ')}
                      </div>
                    )}
                    {attachment.extraction_reason && (
                      <div className="mt-1 text-xs text-cyber-400">
                        Reason: {attachment.extraction_reason}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {message.model_called !== undefined && (
            <div className="text-xs uppercase tracking-[0.2em] text-cyber-400">
              Model called: {message.model_called ? 'yes' : 'no'}
            </div>
          )}

          {message.signals && Object.keys(message.signals).length > 0 && (
            <div className="subtle-panel">
              <div className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-primary-300">Security signals</div>
              <ul className="space-y-1.5">
                {Object.entries(message.signals).map(([signalType, details]: [string, any]) => (
                  <li key={signalType} className="text-sm text-cyber-200">
                    <span className="font-medium text-white">{signalType}:</span>{' '}
                    {typeof details === 'boolean'
                      ? details ? 'detected' : 'clear'
                      : Array.isArray(details)
                        ? (details.length ? details.join(', ') : 'none')
                        : 'detected'}
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
