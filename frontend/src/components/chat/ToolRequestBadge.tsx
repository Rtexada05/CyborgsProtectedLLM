import React from 'react';
import { Check, X, Wrench } from 'lucide-react';

interface ToolRequestBadgeProps {
  tool: string;
  allowed: boolean;
}

export const ToolRequestBadge: React.FC<ToolRequestBadgeProps> = ({ tool, allowed }) => {
  const getBadgeClass = () => {
    return allowed
      ? 'bg-success-100 text-success-800 border border-success-200'
      : 'bg-danger-100 text-danger-800 border border-danger-200';
  };

  const getIcon = () => {
    return allowed ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />;
  };

  const getToolIcon = () => {
    return <Wrench className="h-3 w-3" />;
  };

  return (
    <span className={`inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium ${getBadgeClass()}`}>
      {getToolIcon()}
      <span>{tool}</span>
      {getIcon()}
    </span>
  );
};
