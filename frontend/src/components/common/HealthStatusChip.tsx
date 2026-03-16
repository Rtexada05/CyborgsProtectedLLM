import React from 'react';
import { CheckCircle, AlertCircle, XCircle } from 'lucide-react';

interface HealthStatusChipProps {
  status: 'ok' | 'warning' | 'error';
  message?: string;
  className?: string;
}

export const HealthStatusChip: React.FC<HealthStatusChipProps> = ({ 
  status, 
  message, 
  className = '' 
}) => {
  const getStatusColor = () => {
    switch (status) {
      case 'ok':
        return 'bg-success-100 text-success-800 border-success-200';
      case 'warning':
        return 'bg-warning-100 text-warning-800 border-warning-200';
      case 'error':
        return 'bg-danger-100 text-danger-800 border-danger-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'ok':
        return <CheckCircle className="h-4 w-4" />;
      case 'warning':
        return <AlertCircle className="h-4 w-4" />;
      case 'error':
        return <XCircle className="h-4 w-4" />;
      default:
        return null;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'ok':
        return 'Healthy';
      case 'warning':
        return 'Warning';
      case 'error':
        return 'Error';
      default:
        return 'Unknown';
    }
  };

  return (
    <div className={`inline-flex items-center space-x-2 px-3 py-1 rounded-full border text-sm font-medium ${getStatusColor()} ${className}`}>
      {getStatusIcon()}
      <span>{getStatusText()}</span>
      {message && <span className="text-xs opacity-75">({message})</span>}
    </div>
  );
};
