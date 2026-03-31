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
      ? 'bg-success-100 text-success-800 border border-success-200'
      : 'bg-danger-100 text-danger-800 border border-danger-200';
  };

  const getIcon = () => {
    return allowed ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />;
  };

  const getToolIcon = () => {
    return <Wrench className="h-4 w-4" />;
  };

  return (
    <span className={`inline-flex items-center space-x-1 rounded-full px-3 py-1.5 text-sm font-medium ${getBadgeClass()}`}>
      {getToolIcon()}
      <span>{formattedTool}</span>
      {getIcon()}
    </span>
  );
};
