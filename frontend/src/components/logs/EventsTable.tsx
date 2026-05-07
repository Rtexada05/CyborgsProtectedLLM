import React from 'react';
import { Check, ChevronLeft, ChevronRight, Copy } from 'lucide-react';
import { AdminDecisionRecord } from '../../services/types';
import { DecisionBadge, RiskIndicator } from '../common/DecisionBadge';

interface EventsTableProps {
  events: AdminDecisionRecord[];
  isLoading: boolean;
  currentPage: number;
  pageSize: number;
  totalEvents: number;
  totalPages: number;
  hasPrevious: boolean;
  hasNext: boolean;
  onPageSizeChange: (pageSize: number) => void;
  onPreviousPage: () => void;
  onNextPage: () => void;
}

const PAGE_SIZE_OPTIONS = [10, 25, 50];

export const EventsTable: React.FC<EventsTableProps> = ({
  events,
  isLoading,
  currentPage,
  pageSize,
  totalEvents,
  totalPages,
  hasPrevious,
  hasNext,
  onPageSizeChange,
  onPreviousPage,
  onNextPage,
}) => {
  const [copiedTraceId, setCopiedTraceId] = React.useState<string | null>(null);

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const getPromptPreview = (event: AdminDecisionRecord) => {
    const preview = event.prompt_preview?.trim();
    return preview || 'Prompt preview unavailable';
  };

  const showingCount = Math.min(events.length, pageSize);

  const handleCopyTraceId = async (traceId: string) => {
    try {
      await navigator.clipboard.writeText(traceId);
      setCopiedTraceId(traceId);
      window.setTimeout(() => {
        setCopiedTraceId((current) => (current === traceId ? null : current));
      }, 1500);
    } catch (error) {
      console.error('Failed to copy trace ID:', error);
    }
  };

  return (
    <div className="cyber-panel-subtle overflow-hidden">
      <div className="border-b border-white/10 px-6 py-5">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-white">Recent Chat Decisions</h3>
            <p className="text-sm text-cyber-300">
              Showing {showingCount} of {totalEvents} logs
            </p>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <label className="flex items-center gap-2 text-sm text-cyber-300">
              <span>Logs per page</span>
              <select
                value={pageSize}
                onChange={(event) => onPageSizeChange(Number(event.target.value))}
                disabled={isLoading}
                className="rounded-xl border border-white/10 bg-cyber-950/80 px-3 py-2 text-sm text-cyber-100 disabled:bg-white/5"
              >
                {PAGE_SIZE_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>

            <div className="flex items-center gap-2 self-start sm:self-auto">
              <button
                type="button"
                onClick={onPreviousPage}
                disabled={!hasPrevious || isLoading}
                className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-cyber-200 transition hover:border-primary-300/30 hover:bg-primary-500/10 disabled:cursor-not-allowed disabled:opacity-40"
                aria-label="Previous logs page"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="min-w-[96px] text-center text-sm text-cyber-300">
                Page {currentPage} of {totalPages}
              </span>
              <button
                type="button"
                onClick={onNextPage}
                disabled={!hasNext || isLoading}
                className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-cyber-200 transition hover:border-primary-300/30 hover:bg-primary-500/10 disabled:cursor-not-allowed disabled:opacity-40"
                aria-label="Next logs page"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-4 p-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="animate-pulse rounded-2xl border border-white/10 p-4">
              <div className="mb-2 h-4 w-1/4 rounded bg-white/10"></div>
              <div className="mb-2 h-3 w-1/2 rounded bg-white/10"></div>
              <div className="h-3 w-3/4 rounded bg-white/10"></div>
            </div>
          ))}
        </div>
      ) : events.length === 0 ? (
        <div className="py-8 text-center">
          <p className="text-cyber-300">No security events to display</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b border-white/10 bg-cyber-950/55">
              <tr>
                <th className="table-header-cell">Timestamp</th>
                <th className="table-header-cell">Prompt</th>
                <th className="table-header-cell">Decision</th>
                <th className="table-header-cell">Risk Level</th>
                <th className="table-header-cell">Mode</th>
                <th className="table-header-cell">Reason</th>
                <th className="table-header-cell">Trace ID</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {events.map((event) => (
                <tr key={event.trace_id} className="transition hover:bg-white/5">
                  <td className="table-cell whitespace-nowrap">
                    {formatTimestamp(event.timestamp)}
                  </td>
                  <td className="table-cell max-w-xs">
                    <div className="truncate" title={getPromptPreview(event)}>
                      {getPromptPreview(event)}
                    </div>
                  </td>
                  <td className="table-cell whitespace-nowrap">
                    <DecisionBadge decision={event.decision} />
                  </td>
                  <td className="table-cell whitespace-nowrap">
                    <RiskIndicator riskLevel={event.risk_level} />
                  </td>
                  <td className="table-cell whitespace-nowrap">
                    {event.security_mode}
                  </td>
                  <td className="table-cell max-w-xs">
                    <div className="truncate" title={event.reason}>
                      {event.reason}
                    </div>
                  </td>
                  <td className="table-cell min-w-[260px] font-mono text-cyber-300">
                    <div className="flex items-center gap-2">
                      <span className="truncate" title={event.trace_id}>
                        {event.trace_id}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleCopyTraceId(event.trace_id)}
                        className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-cyber-300 transition hover:border-primary-300/30 hover:bg-primary-500/10 hover:text-white"
                        aria-label={`Copy trace ID ${event.trace_id}`}
                        title={copiedTraceId === event.trace_id ? 'Copied' : 'Copy trace ID'}
                      >
                        {copiedTraceId === event.trace_id ? (
                          <Check className="h-4 w-4" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
