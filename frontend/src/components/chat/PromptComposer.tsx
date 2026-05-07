import React, { useRef, useState } from 'react';
import { ChevronDown, ChevronUp, Paperclip, Send, SlidersHorizontal } from 'lucide-react';
import { AttachmentRef, RAGScope } from '../../services/types';

interface PromptComposerProps {
  onSendMessage: (payload: {
    prompt: string;
    requestedTools: string[];
    attachments: AttachmentRef[];
    ragEnabled: boolean;
    ragScope: RAGScope;
    ragDocumentIds: string[];
  }) => void;
  isLoading: boolean;
  disabled?: boolean;
  currentUserId: string;
}

const TOOL_OPTIONS = ['calculator', 'file_reader', 'web', 'database'];
const ACCEPTED_ATTACHMENTS = '.txt,.csv,.json,.pdf,.docx,image/png,image/jpeg,image/webp';

const formatToolLabel = (tool: string) =>
  tool
    .split('_')
    .map(segment => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ');

export const PromptComposer: React.FC<PromptComposerProps> = ({
  onSendMessage,
  isLoading,
  disabled = false,
  currentUserId,
}) => {
  const [prompt, setPrompt] = useState('');
  const [requestedTools, setRequestedTools] = useState<string[]>([]);
  const [attachments, setAttachments] = useState<AttachmentRef[]>([]);
  const [ragEnabled, setRagEnabled] = useState(true);
  const [ragScope, setRagScope] = useState<RAGScope>('default');
  const [ragDocumentIdsInput, setRagDocumentIdsInput] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const normalizedPrompt = prompt.trim() || (attachments.length > 0 ? 'Please inspect the attached file.' : '');
    const ragDocumentIds = ragDocumentIdsInput
      .split(',')
      .map(entry => entry.trim())
      .filter(Boolean);
    if ((normalizedPrompt || attachments.length > 0) && !isLoading && !disabled) {
      onSendMessage({
        prompt: normalizedPrompt,
        requestedTools,
        attachments,
        ragEnabled,
        ragScope,
        ragDocumentIds,
      });
      setPrompt('');
      setRequestedTools([]);
      setAttachments([]);
      setRagDocumentIdsInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleToolToggle = (tool: string) => {
    setRequestedTools(current =>
      current.includes(tool) ? current.filter(entry => entry !== tool) : [...current, tool]
    );
  };

  const handleFilesSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    const nextAttachments = await Promise.all(
      files.map(
        async file =>
          new Promise<AttachmentRef>((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
              const result = typeof reader.result === 'string' ? reader.result : '';
              resolve({
                id: `${Date.now()}-${file.name}`,
                name: file.name,
                mime_type:
                  file.type ||
                  (file.name.toLowerCase().endsWith('.docx')
                    ? 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    : 'application/octet-stream'),
                kind: file.type.startsWith('image/') ? 'image' : 'file',
                content_b64: result.includes(',') ? result.split(',')[1] : '',
              });
            };
            reader.onerror = () => reject(reader.error);
            reader.readAsDataURL(file);
          })
      )
    );
    setAttachments(current => [...current, ...nextAttachments]);
    event.target.value = '';
  };

  const removeAttachment = (id: string) => {
    setAttachments(current => current.filter(attachment => attachment.id !== id));
  };

  const buildUploadDocumentId = (attachment: AttachmentRef) => `upload:${currentUserId}:${attachment.id}`;

  return (
    <form
      onSubmit={handleSubmit}
      className="cyber-panel border border-cyan-300/20 bg-cyber-900/88 p-4 shadow-[0_-12px_40px_rgba(0,0,0,0.35)] backdrop-blur-xl supports-[backdrop-filter]:bg-cyber-900/72"
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={handleFilesSelected}
        accept={ACCEPTED_ATTACHMENTS}
      />

      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {attachments.length > 0 && (
            <span className="rounded-full border border-primary-300/20 bg-primary-500/10 px-3 py-1 text-xs font-medium text-primary-100">
              {attachments.length} attachment{attachments.length > 1 ? 's' : ''}
            </span>
          )}
          {requestedTools.length > 0 && (
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium text-cyber-200">
              Tools: {requestedTools.length}
            </span>
          )}
          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium text-cyber-200">
            RAG: {ragEnabled ? ragScope.replace(/_/g, ' ') : 'off'}
          </span>
        </div>

        <button
          type="button"
          onClick={() => setShowAdvanced(current => !current)}
          disabled={disabled || isLoading}
          className="inline-flex min-h-[40px] items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-cyber-200 transition hover:border-primary-300/30 hover:bg-primary-500/10 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          <SlidersHorizontal className="h-4 w-4" />
          <span>Controls</span>
          {showAdvanced ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
        </button>
      </div>

      {showAdvanced && (
        <div className="mb-4 space-y-3">
          <div className="flex flex-wrap gap-2">
            {TOOL_OPTIONS.map(tool => {
              const active = requestedTools.includes(tool);
              return (
                <button
                  key={tool}
                  type="button"
                  disabled={disabled || isLoading}
                  onClick={() => handleToolToggle(tool)}
                  className={`min-h-[40px] rounded-full border px-4 py-2 text-sm font-medium transition ${active ? 'border-primary-300/40 bg-primary-500/20 text-primary-100 shadow-[0_0_18px_rgba(78,207,255,0.12)]' : 'border-white/10 bg-white/5 text-cyber-200 hover:border-primary-300/30 hover:bg-primary-500/10'}`}
                >
                  {formatToolLabel(tool)}
                </button>
              );
            })}
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="mb-3 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.2em] text-primary-300">RAG Controls</div>
                <div className="mt-1 text-sm text-cyber-300">
                  These controls scope retrieval only. Defense behavior still comes from the backend security mode.
                </div>
              </div>
              <label className="flex items-center gap-2 text-sm text-cyber-200">
                <input
                  type="checkbox"
                  checked={ragEnabled}
                  onChange={(e) => setRagEnabled(e.target.checked)}
                  disabled={disabled || isLoading}
                  className="h-4 w-4 rounded border-white/20 bg-cyber-950/70"
                />
                Enable RAG
              </label>
            </div>

            <div className="grid gap-3 lg:grid-cols-[220px_1fr]">
              <label className="flex flex-col gap-2 text-sm text-cyber-200">
                <span>Scope</span>
                <select
                  value={ragScope}
                  onChange={(e) => setRagScope(e.target.value as RAGScope)}
                  disabled={disabled || isLoading || !ragEnabled}
                  className="cyber-input"
                >
                  <option value="default">Default</option>
                  <option value="static_only">Static Docs Only</option>
                  <option value="user_uploads_only">User Uploads Only</option>
                </select>
              </label>

              <label className="flex flex-col gap-2 text-sm text-cyber-200">
                <span>Document IDs</span>
                <input
                  type="text"
                  value={ragDocumentIdsInput}
                  onChange={(e) => setRagDocumentIdsInput(e.target.value)}
                  disabled={disabled || isLoading || !ragEnabled}
                  placeholder="Optional comma-separated IDs like security_playbook or upload:demo-user:file-1"
                  className="cyber-input"
                />
              </label>
            </div>
          </div>
        </div>
      )}

      {attachments.length > 0 && (
        <div className="mb-4 space-y-3">
          <div className="flex flex-wrap gap-3">
            {attachments.map(attachment => (
              <button
                key={attachment.id}
                type="button"
                onClick={() => removeAttachment(attachment.id)}
                className="min-h-[44px] rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-cyber-200 transition hover:border-danger-400/30 hover:bg-danger-500/10 hover:text-danger-100"
                title="Remove attachment"
              >
                {attachment.name}
              </button>
            ))}
          </div>

          <div className="rounded-2xl border border-white/10 bg-cyber-950/40 p-3">
            <div className="text-xs font-semibold uppercase tracking-[0.2em] text-primary-300">
              Upload Document IDs
            </div>
            <div className="mt-1 text-sm text-cyber-300">
              Use these in the `Document IDs` field when testing `User Uploads Only` retrieval.
            </div>
            <div className="mt-3 space-y-2">
              {attachments.map(attachment => (
                <div key={`doc-id-${attachment.id}`} className="rounded-xl border border-white/10 bg-white/5 px-3 py-2">
                  <div className="text-sm text-white">{attachment.name}</div>
                  <code className="mt-1 block break-all text-xs text-primary-100">
                    {buildUploadDocumentId(attachment)}
                  </code>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="flex flex-col gap-3 lg:flex-row lg:items-end">
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-cyber-300 transition hover:border-primary-300/30 hover:bg-primary-500/10 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
          title="Attach files or images"
        >
          <Paperclip className="h-5 w-5" />
        </button>

        <div className="flex-1">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Compose a request for the protected gateway..."
            disabled={disabled || isLoading}
            className="cyber-input w-full resize-none"
            rows={2}
          />
        </div>

        <button
          type="submit"
          disabled={(!prompt.trim() && attachments.length === 0) || isLoading || disabled}
          className="flex min-h-[48px] items-center justify-center gap-2 rounded-2xl border border-primary-300/35 bg-primary-500/85 px-5 py-3 text-base font-medium text-cyber-950 transition hover:bg-primary-400 disabled:cursor-not-allowed disabled:border-white/10 disabled:bg-white/10 disabled:text-cyber-400"
        >
          {isLoading ? (
            <>
              <div className="h-4 w-4 animate-spin rounded-full border-b-2 border-cyber-950"></div>
              <span>Sending...</span>
            </>
          ) : (
            <>
              <Send className="h-4 w-4" />
              <span>Send</span>
            </>
          )}
        </button>
      </div>
    </form>
  );
};
