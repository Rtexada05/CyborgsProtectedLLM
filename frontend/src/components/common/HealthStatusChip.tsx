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
        return 'border-success-400/25 bg-success-500/15 text-success-100';
      case 'warning':
        return 'border-warning-400/25 bg-warning-500/15 text-warning-100';
      case 'error':
        return 'border-danger-400/25 bg-danger-500/15 text-danger-100';
      default:
        return 'border-white/15 bg-white/10 text-cyber-100';
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
    <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-medium shadow-[0_0_0_1px_rgba(255,255,255,0.02)] ${getStatusColor()} ${className}`}>
      {getStatusIcon()}
      <span>{getStatusText()}</span>
      {message && <span className="text-xs opacity-75">({message})</span>}
    </div>
  );
};
