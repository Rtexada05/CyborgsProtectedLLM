import React from 'react';
import { AlertTriangle, Check, Database } from 'lucide-react';

interface RAGStatusBadgeProps {
  used: boolean;
  validated?: boolean;
}

export const RAGStatusBadge: React.FC<RAGStatusBadgeProps> = ({ used, validated }) => {
  if (!used) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs font-medium text-cyber-200">
        <Database className="h-3 w-3" />
        <span>No RAG</span>
      </span>
    );
  }

  const getValidationIcon = () => {
    if (validated === undefined) return null;
    return validated ? <Check className="h-3 w-3" /> : <AlertTriangle className="h-3 w-3" />;
  };

  const getValidationClass = () => {
    if (validated === undefined) return 'border border-primary-400/20 bg-primary-500/15 text-primary-100';
    return validated
      ? 'border border-success-400/20 bg-success-500/15 text-success-100'
      : 'border border-warning-400/20 bg-warning-500/15 text-warning-100';
  };

  const getValidationText = () => {
    if (validated === undefined) return 'RAG Used';
    return validated ? 'RAG Validated' : 'RAG Flagged';
  };

  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${getValidationClass()}`}>
      <Database className="h-3 w-3" />
      <span>{getValidationText()}</span>
      {getValidationIcon()}
    </span>
  );
};
