import React from 'react';
import { Check, X, Wrench } from 'lucide-react';

interface ToolRequestBadgeProps {
  tool: string;
  allowed: boolean;
}

export const ToolRequestBadge: React.FC<ToolRequestBadgeProps> = ({ tool, allowed }) => {
  const formattedTool = tool
    .split('_')
    .map(segment => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ');

  const getBadgeClass = () => {
    return allowed
      ? 'border border-success-400/20 bg-success-500/15 text-success-100'
      : 'border border-danger-400/20 bg-danger-500/15 text-danger-100';
  };

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium ${getBadgeClass()}`}>
      <Wrench className="h-4 w-4" />
      <span>{formattedTool}</span>
      {allowed ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />}
    </span>
  );
};
