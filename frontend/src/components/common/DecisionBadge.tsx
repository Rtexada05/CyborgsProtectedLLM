import React from 'react';
import { AlertTriangle, Ban, CheckCircle2 } from 'lucide-react';
import { Decision, RiskLevel } from '../../services/types';

interface DecisionBadgeProps {
  decision: Decision;
  className?: string;
}

export const DecisionBadge: React.FC<DecisionBadgeProps> = ({ decision, className = '' }) => {
  const getDecisionClass = () => {
    switch (decision) {
      case 'ALLOW':
        return 'decision-allow';
      case 'SANITIZE':
        return 'decision-sanitize';
      case 'BLOCK':
        return 'decision-block';
      default:
        return 'border-white/10 bg-white/10 text-cyber-100';
    }
  };

  const getIcon = () => {
    switch (decision) {
      case 'ALLOW':
        return <CheckCircle2 className="h-4 w-4" />;
      case 'SANITIZE':
        return <AlertTriangle className="h-4 w-4" />;
      case 'BLOCK':
        return <Ban className="h-4 w-4" />;
      default:
        return null;
    }
  };

  return (
    <span className={`decision-badge ${getDecisionClass()} ${className}`}>
      {getIcon()}
      {decision}
    </span>
  );
};

interface RiskIndicatorProps {
  riskLevel: RiskLevel;
  className?: string;
}

export const RiskIndicator: React.FC<RiskIndicatorProps> = ({ riskLevel, className = '' }) => {
  const getRiskClass = () => {
    switch (riskLevel) {
      case 'LOW':
        return 'risk-low';
      case 'MEDIUM':
        return 'risk-medium';
      case 'HIGH':
        return 'risk-high';
      case 'CRITICAL':
        return 'risk-critical';
      default:
        return 'border border-white/10 bg-white/10 text-cyber-100';
    }
  };

  const getRiskColor = () => {
    switch (riskLevel) {
      case 'LOW':
        return 'text-success-100';
      case 'MEDIUM':
        return 'text-warning-100';
      case 'HIGH':
        return 'text-danger-100';
      case 'CRITICAL':
        return 'text-danger-50';
      default:
        return 'text-cyber-200';
    }
  };

  return (
    <div className={`rounded-full px-3 py-1.5 text-sm font-medium ${getRiskClass()} ${className}`}>
      <span className={`font-semibold ${getRiskColor()}`}>{riskLevel}</span>
    </div>
  );
};
