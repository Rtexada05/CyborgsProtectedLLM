import React from 'react';
import { AlertTriangle, Shield, TrendingDown, TrendingUp, Users } from 'lucide-react';

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
        return 'border-success-400/25 bg-success-500/15 text-success-100';
      case 'warning':
        return 'border-warning-400/25 bg-warning-500/15 text-warning-100';
      case 'danger':
        return 'border-danger-400/25 bg-danger-500/15 text-danger-100';
      case 'primary':
        return 'border-primary-400/25 bg-primary-500/15 text-primary-100';
      default:
        return 'border-white/10 bg-white/5 text-cyber-100';
    }
  };

  const getChangeColor = () => {
    if (change === undefined) return '';
    return change > 0 ? 'text-success-200' : change < 0 ? 'text-danger-100' : 'text-cyber-300';
  };

  const getChangeIcon = () => {
    if (change === undefined) return null;
    if (change > 0) return <TrendingUp className="h-4 w-4" />;
    if (change < 0) return <TrendingDown className="h-4 w-4" />;
    return <div className="h-2 w-2 rounded-full bg-cyber-400" />;
  };

  return (
    <div className="metric-card animate-enter">
      <div className="mb-4 flex items-start justify-between">
        <div className={`rounded-2xl border p-3 ${getColorClasses()}`}>
          {icon}
        </div>
        {change !== undefined && (
          <div className={`flex items-center gap-1 text-sm font-medium ${getChangeColor()}`}>
            {getChangeIcon()}
            <span>{Math.abs(change)}%</span>
          </div>
        )}
      </div>
      <div>
        <p className="text-sm uppercase tracking-[0.22em] text-cyber-400">{title}</p>
        <h3 className="mt-2 text-3xl font-semibold text-white">{value}</h3>
        {subtitle && (
          <p className="mt-2 text-sm text-cyber-300">{subtitle}</p>
        )}
      </div>
    </div>
  );
};

interface MetricsOverviewProps {
  metrics: {
    traffic: {
      total_chat_traces: number;
      total_decision_records: number;
      requests_without_decision_record: number;
    };
    decisions: {
      distribution: Record<string, number>;
    };
    evaluation: {
      labeled_samples: number;
      pending_reviews: number;
      fpr: number | null;
      asr: number | null;
    };
  } | null;
  isLoading: boolean;
}

export const MetricsOverview: React.FC<MetricsOverviewProps> = ({ metrics, isLoading }) => {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="metric-card animate-pulse">
            <div className="mb-4 h-4 w-1/2 rounded bg-white/10"></div>
            <div className="mb-2 h-8 w-3/4 rounded bg-white/10"></div>
            <div className="h-3 w-full rounded bg-white/10"></div>
          </div>
        ))}
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="py-8 text-center">
        <p className="text-cyber-300">No metrics available</p>
      </div>
    );
  }

  const asrPercent = metrics.evaluation.asr === null ? null : metrics.evaluation.asr * 100;
  const fprPercent = metrics.evaluation.fpr === null ? null : metrics.evaluation.fpr * 100;

  const metricCards = [
    {
      title: 'Completed Requests',
      value: metrics.traffic.total_decision_records.toLocaleString(),
      icon: <Users className="h-5 w-5" />,
      color: 'primary' as const,
      subtitle: `${metrics.traffic.requests_without_decision_record.toLocaleString()} attempts failed before decision`
    },
    {
      title: 'Allowed Requests',
      value: (metrics.decisions.distribution.ALLOW || 0).toLocaleString(),
      change: ((metrics.decisions.distribution.ALLOW || 0) / Math.max(metrics.traffic.total_decision_records, 1)) * 100,
      icon: <Shield className="h-5 w-5" />,
      color: 'success' as const,
      subtitle: 'Passed security checks'
    },
    {
      title: 'Sanitized Requests',
      value: (metrics.decisions.distribution.SANITIZE || 0).toLocaleString(),
      change: ((metrics.decisions.distribution.SANITIZE || 0) / Math.max(metrics.traffic.total_decision_records, 1)) * 100,
      icon: <AlertTriangle className="h-5 w-5" />,
      color: 'warning' as const,
      subtitle: 'Cleaned before processing'
    },
    {
      title: 'Blocked Requests',
      value: (metrics.decisions.distribution.BLOCK || 0).toLocaleString(),
      change: ((metrics.decisions.distribution.BLOCK || 0) / Math.max(metrics.traffic.total_decision_records, 1)) * 100,
      icon: <TrendingUp className="h-5 w-5" />,
      color: 'danger' as const,
      subtitle: 'Security violations'
    },
    {
      title: 'Attack Success Rate',
      value: asrPercent === null ? 'N/A' : `${asrPercent.toFixed(1)}%`,
      icon: <TrendingUp className="h-5 w-5" />,
      color: (asrPercent === null ? 'primary' as const : asrPercent > 50 ? 'danger' as const : asrPercent > 20 ? 'warning' as const : 'success' as const),
      subtitle: asrPercent === null
        ? `Needs reviewed attack samples (${metrics.evaluation.labeled_samples} labeled)`
        : 'Lower is better'
    },
    {
      title: 'False Positive Rate',
      value: fprPercent === null ? 'N/A' : `${fprPercent.toFixed(1)}%`,
      icon: <AlertTriangle className="h-5 w-5" />,
      color: (fprPercent === null ? 'primary' as const : fprPercent > 15 ? 'danger' as const : fprPercent > 5 ? 'warning' as const : 'success' as const),
      subtitle: fprPercent === null
        ? `Needs reviewed benign samples (${metrics.evaluation.labeled_samples} labeled)`
        : 'Lower is better'
    }
  ];

  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
      {metricCards.map((card, index) => (
        <MetricsCard key={index} {...card} />
      ))}
    </div>
  );
};
