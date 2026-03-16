import React from 'react';
import { ChatResponse } from '../../services/types';
import { DecisionBadge, RiskIndicator } from '../common/DecisionBadge';

interface EventsTableProps {
  events: ChatResponse[];
  isLoading: boolean;
}

export const EventsTable: React.FC<EventsTableProps> = ({ events, isLoading }) => {
  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const getSignalSummary = (signals: Record<string, any> | undefined) => {
    if (!signals || Object.keys(signals).length === 0) {
      return <span className="text-gray-500">None</span>;
    }

    return (
      <div className="space-y-1">
        {Object.entries(signals).map(([signalType, details]: [string, any]) => (
          <div key={signalType} className="text-xs">
            <span className="font-medium text-gray-700">{signalType}:</span>{' '}
            <span className="text-gray-600">
              {details.confidence ? `${(details.confidence * 100).toFixed(1)}%` : 'detected'}
            </span>
          </div>
        ))}
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="bg-white rounded-lg border border-gray-200 p-4 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/4 mb-2"></div>
            <div className="h-3 bg-gray-200 rounded w-1/2 mb-2"></div>
            <div className="h-3 bg-gray-200 rounded w-3/4"></div>
          </div>
        ))}
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500">No security events to display</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">Recent Security Events</h3>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Timestamp
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                User ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Decision
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Risk Level
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Signals
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Reason
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Trace ID
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {events.map((event) => (
              <tr key={event.trace_id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {formatTimestamp(event.timestamp)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {event.user_id}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <DecisionBadge decision={event.decision} />
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <RiskIndicator riskLevel={event.risk_level} />
                </td>
                <td className="px-6 py-4 text-sm text-gray-900">
                  {getSignalSummary(event.signals)}
                </td>
                <td className="px-6 py-4 text-sm text-gray-900 max-w-xs">
                  <div className="truncate" title={event.reason}>
                    {event.reason}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-500">
                  {event.trace_id.slice(0, 8)}...
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
