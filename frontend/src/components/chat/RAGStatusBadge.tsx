import React from 'react';
import { Database, Check, AlertTriangle } from 'lucide-react';

interface RAGStatusBadgeProps {
  used: boolean;
  validated?: boolean;
}

export const RAGStatusBadge: React.FC<RAGStatusBadgeProps> = ({ used, validated }) => {
  if (!used) {
    return (
      <span className="inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 border border-gray-200">
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
    if (validated === undefined) return 'bg-blue-100 text-blue-800 border border-blue-200';
    return validated 
      ? 'bg-success-100 text-success-800 border border-success-200'
      : 'bg-warning-100 text-warning-800 border border-warning-200';
  };

  const getValidationText = () => {
    if (validated === undefined) return 'RAG Used';
    return validated ? 'RAG Validated' : 'RAG Flagged';
  };

  return (
    <span className={`inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium ${getValidationClass()}`}>
      <Database className="h-3 w-3" />
      <span>{getValidationText()}</span>
      {getValidationIcon()}
    </span>
  );
};
