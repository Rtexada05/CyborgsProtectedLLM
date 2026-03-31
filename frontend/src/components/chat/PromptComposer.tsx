import React, { useRef, useState } from 'react';
import { Send, Paperclip } from 'lucide-react';
import { AttachmentRef } from '../../services/types';

interface PromptComposerProps {
  onSendMessage: (payload: { prompt: string; requestedTools: string[]; attachments: AttachmentRef[] }) => void;
  isLoading: boolean;
  disabled?: boolean;
}

const TOOL_OPTIONS = ['calculator', 'file_reader', 'web', 'database'];

const formatToolLabel = (tool: string) =>
  tool
    .split('_')
    .map(segment => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ');

export const PromptComposer: React.FC<PromptComposerProps> = ({
  onSendMessage,
  isLoading,
  disabled = false
}) => {
  const [prompt, setPrompt] = useState('');
  const [requestedTools, setRequestedTools] = useState<string[]>([]);
  const [attachments, setAttachments] = useState<AttachmentRef[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const normalizedPrompt = prompt.trim() || (attachments.length > 0 ? 'Please inspect the attached file.' : '');
    if ((normalizedPrompt || attachments.length > 0) && !isLoading && !disabled) {
      onSendMessage({
        prompt: normalizedPrompt,
        requestedTools,
        attachments,
      });
      setPrompt('');
      setRequestedTools([]);
      setAttachments([]);
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
                mime_type: file.type || 'application/octet-stream',
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

  return (
    <form onSubmit={handleSubmit} className="border-t border-gray-200 bg-white p-5">
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={handleFilesSelected}
        accept=".txt,.csv,.json,.pdf,image/png,image/jpeg,image/webp"
      />

      <div className="mb-4 flex flex-wrap gap-3">
        {TOOL_OPTIONS.map(tool => {
          const active = requestedTools.includes(tool);
          return (
            <button
              key={tool}
              type="button"
              disabled={disabled || isLoading}
              onClick={() => handleToolToggle(tool)}
              className={`min-h-[44px] rounded-full border px-4 py-2 text-sm font-medium ${active ? 'bg-primary-100 text-primary-700 border-primary-300' : 'bg-gray-100 text-gray-700 border-gray-200'}`}
            >
              {formatToolLabel(tool)}
            </button>
          );
        })}
      </div>

      {attachments.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-3">
          {attachments.map(attachment => (
            <button
              key={attachment.id}
              type="button"
              onClick={() => removeAttachment(attachment.id)}
              className="min-h-[44px] rounded-full border border-gray-300 bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700"
              title="Remove attachment"
            >
              {attachment.name}
            </button>
          ))}
        </div>
      )}

      <div className="flex items-end space-x-3">
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          className="flex h-11 w-11 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
          title="Attach files or images"
        >
          <Paperclip className="h-5 w-5" />
        </button>

        <div className="flex-1">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message here..."
            disabled={disabled || isLoading}
            className="w-full resize-none rounded-lg border border-gray-300 px-4 py-3 text-base leading-7 focus:border-primary-500 focus:ring-2 focus:ring-primary-500 disabled:cursor-not-allowed disabled:bg-gray-100"
            rows={3}
          />
        </div>

        <button
          type="submit"
          disabled={(!prompt.trim() && attachments.length === 0) || isLoading || disabled}
          className="flex min-h-[52px] items-center space-x-2 rounded-lg bg-primary-600 px-5 py-3 text-base font-medium text-white hover:bg-primary-700 disabled:cursor-not-allowed disabled:bg-gray-300"
        >
          {isLoading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
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
