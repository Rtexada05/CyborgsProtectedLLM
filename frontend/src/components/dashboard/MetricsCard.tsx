import React from 'react';
import { TrendingUp, Users, Shield, AlertTriangle } from 'lucide-react';

interface MetricsCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon: React.ReactNode;
  color: 'success' | 'warning' | 'danger' | 'primary';
  subtitle?: string;
}

export const MetricsCard: React.FC<MetricsCardProps> = ({
  title,
  value,
  change,
  icon,
  color,
  subtitle
}) => {
  const getColorClasses = () => {
    switch (color) {
      case 'success':
        return 'bg-success-50 text-success-700 border-success-200';
      case 'warning':
        return 'bg-warning-50 text-warning-700 border-warning-200';
      case 'danger':
        return 'bg-danger-50 text-danger-700 border-danger-200';
      case 'primary':
        return 'bg-primary-50 text-primary-700 border-primary-200';
      default:
        return 'bg-gray-50 text-gray-700 border-gray-200';
    }
  };

  const getChangeColor = () => {
    if (change === undefined) return '';
    return change > 0 ? 'text-success-600' : change < 0 ? 'text-danger-600' : 'text-gray-600';
  };

  const getChangeIcon = () => {
    if (change === undefined) return null;
    return change > 0 ? '↑' : change < 0 ? '↓' : '→';
  };

  return (
    <div className="metric-card">
      <div className="flex items-center justify-between mb-4">
        <div className={`p-2 rounded-lg ${getColorClasses()}`}>
          {icon}
        </div>
        {change !== undefined && (
          <div className={`flex items-center space-x-1 text-sm font-medium ${getChangeColor()}`}>
            <span>{getChangeIcon()}</span>
            <span>{Math.abs(change)}%</span>
          </div>
        )}
      </div>
      
      <div>
        <h3 className="text-2xl font-bold text-gray-900">{value}</h3>
        <p className="text-sm text-gray-600 mt-1">{title}</p>
        {subtitle && (
          <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
        )}
      </div>
    </div>
  );
};

interface MetricsOverviewProps {
  metrics: {
    traffic: {
      total_chat_traces: number;
    };
    decisions: {
      distribution: Record<string, number>;
    };
    kpis: {
      attack_success_rate_percent: number;
      false_positive_proxy_percent: number;
    };
  } | null;
  isLoading: boolean;
}

export const MetricsOverview: React.FC<MetricsOverviewProps> = ({ metrics, isLoading }) => {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="metric-card animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
            <div className="h-8 bg-gray-200 rounded w-3/4 mb-2"></div>
            <div className="h-3 bg-gray-200 rounded w-full"></div>
          </div>
        ))}
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500">No metrics available</p>
      </div>
    );
  }

  const metricCards = [
    {
      title: 'Total Requests',
      value: metrics.traffic.total_chat_traces.toLocaleString(),
      icon: <Users className="h-5 w-5" />,
      color: 'primary' as const,
      subtitle: 'All chat interactions'
    },
    {
      title: 'Allowed Requests',
      value: (metrics.decisions.distribution.ALLOW || 0).toLocaleString(),
      change: ((metrics.decisions.distribution.ALLOW || 0) / Math.max(metrics.traffic.total_chat_traces, 1)) * 100,
      icon: <Shield className="h-5 w-5" />,
      color: 'success' as const,
      subtitle: 'Passed security checks'
    },
    {
      title: 'Sanitized Requests',
      value: (metrics.decisions.distribution.SANITIZE || 0).toLocaleString(),
      change: ((metrics.decisions.distribution.SANITIZE || 0) / Math.max(metrics.traffic.total_chat_traces, 1)) * 100,
      icon: <AlertTriangle className="h-5 w-5" />,
      color: 'warning' as const,
      subtitle: 'Cleaned before processing'
    },
    {
      title: 'Blocked Requests',
      value: (metrics.decisions.distribution.BLOCK || 0).toLocaleString(),
      change: ((metrics.decisions.distribution.BLOCK || 0) / Math.max(metrics.traffic.total_chat_traces, 1)) * 100,
      icon: <TrendingUp className="h-5 w-5" />,
      color: 'danger' as const,
      subtitle: 'Security violations'
    },
    {
      title: 'Attack Success Rate',
      value: `${metrics.kpis.attack_success_rate_percent.toFixed(1)}%`,
      icon: <TrendingUp className="h-5 w-5" />,
      color: (metrics.kpis.attack_success_rate_percent > 50 ? 'danger' as const : metrics.kpis.attack_success_rate_percent > 20 ? 'warning' as const : 'success' as const),
      subtitle: 'Lower is better'
    },
    {
      title: 'False Positive Rate',
      value: `${metrics.kpis.false_positive_proxy_percent.toFixed(1)}%`,
      icon: <AlertTriangle className="h-5 w-5" />,
      color: (metrics.kpis.false_positive_proxy_percent > 15 ? 'danger' as const : metrics.kpis.false_positive_proxy_percent > 5 ? 'warning' as const : 'success' as const),
      subtitle: 'Lower is better'
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {metricCards.map((card, index) => (
        <MetricsCard key={index} {...card} />
      ))}
    </div>
  );
};
