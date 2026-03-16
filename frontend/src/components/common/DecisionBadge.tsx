import React from 'react';
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
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getIcon = () => {
    switch (decision) {
      case 'ALLOW':
        return '✓';
      case 'SANITIZE':
        return '⚠';
      case 'BLOCK':
        return '✕';
      default:
        return '?';
    }
  };

  return (
    <span className={`decision-badge ${getDecisionClass()} ${className}`}>
      <span className="mr-1">{getIcon()}</span>
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
        return 'bg-gray-50 text-gray-700';
    }
  };

  const getRiskColor = () => {
    switch (riskLevel) {
      case 'LOW':
        return 'text-success-600';
      case 'MEDIUM':
        return 'text-warning-600';
      case 'HIGH':
        return 'text-danger-600';
      case 'CRITICAL':
        return 'text-danger-800';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <div className={`px-3 py-1 rounded-full text-sm font-medium ${getRiskClass()} ${className}`}>
      <span className={`font-semibold ${getRiskColor()}`}>{riskLevel}</span>
    </div>
  );
};
