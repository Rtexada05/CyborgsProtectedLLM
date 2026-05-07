import React from 'react';
import { SecurityMode } from '../../services/types';

interface SecurityModeSelectorProps {
  currentMode: SecurityMode;
  onModeChange: (mode: SecurityMode) => void;
  isLoading?: boolean;
}

export const SecurityModeSelector: React.FC<SecurityModeSelectorProps> = ({
  currentMode,
  onModeChange,
  isLoading = false
}) => {
  const modes: Array<{
    mode: SecurityMode;
    label: string;
    description: string;
    color: string;
    impact: string;
  }> = [
    {
      mode: 'Off',
      label: 'Off',
      description: 'No protection applied. All requests allowed.',
      color: 'border-white/10 bg-white/10 text-cyber-200',
      impact: 'No security filtering'
    },
    {
      mode: 'Weak',
      label: 'Weak',
      description: 'Basic input validation only.',
      color: 'border-primary-400/20 bg-primary-500/15 text-primary-100',
      impact: 'Minimal filtering'
    },
    {
      mode: 'Normal',
      label: 'Normal',
      description: 'Standard protection with policy enforcement.',
      color: 'border-warning-400/20 bg-warning-500/15 text-warning-100',
      impact: 'Balanced security'
    },
    {
      mode: 'Strong',
      label: 'Strong',
      description: 'Maximum security with strict validation.',
      color: 'border-danger-400/20 bg-danger-500/15 text-danger-100',
      impact: 'Most restrictive'
    }
  ];

  return (
    <div className="cyber-panel-subtle p-6">
      <h3 className="mb-4 text-lg font-semibold text-white">Security Mode Configuration</h3>

      <div className="mb-6">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium uppercase tracking-[0.2em] text-cyber-400">Current Mode</span>
          <div className={`rounded-full border px-3 py-1 text-sm font-medium ${
            modes.find(m => m.mode === currentMode)?.color
          }`}>
            {currentMode}
          </div>
        </div>
      </div>

      <div className="space-y-3">
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyber-400">Select Security Mode</p>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {modes.map((mode) => (
            <button
              key={mode.mode}
              onClick={() => onModeChange(mode.mode)}
              disabled={isLoading || mode.mode === currentMode}
              className={`
                rounded-2xl border p-4 text-left transition-all
                ${currentMode === mode.mode
                  ? 'border-primary-300/45 bg-primary-500/14 shadow-[0_0_35px_rgba(78,207,255,0.12)]'
                  : 'border-white/10 bg-white/5 hover:border-primary-300/20 hover:bg-primary-500/8'
                }
                ${isLoading ? 'cursor-not-allowed opacity-50' : ''}
                ${mode.mode === currentMode ? 'cursor-default' : ''}
              `}
            >
              <div className="mb-2 flex items-center justify-between gap-3">
                <div className={`rounded-full border px-2.5 py-1 text-sm font-medium ${mode.color}`}>
                  {mode.label}
                </div>
                {currentMode === mode.mode && (
                  <span className="text-xs font-medium uppercase tracking-[0.2em] text-primary-200">Active</span>
                )}
              </div>
              <p className="mb-1 text-sm text-cyber-200">{mode.description}</p>
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-cyber-400">{mode.impact}</p>
            </button>
          ))}
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-4">
        <h4 className="mb-3 text-sm font-semibold uppercase tracking-[0.2em] text-cyber-300">Security Level Impact</h4>
        <div className="space-y-2 text-xs">
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-success-400"></div>
            <span className="text-cyber-300">Low Risk: Basic queries, calculations</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-warning-400"></div>
            <span className="text-cyber-300">Medium Risk: Role manipulation, suspicious patterns</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-danger-400"></div>
            <span className="text-cyber-300">High/Critical Risk: Injection attempts, tool abuse</span>
          </div>
        </div>
      </div>

      {isLoading && (
        <div className="mt-4 flex items-center gap-2 text-sm text-cyber-300">
          <div className="h-4 w-4 animate-spin rounded-full border-b-2 border-primary-400"></div>
          <span>Updating security mode...</span>
        </div>
      )}
    </div>
  );
};
