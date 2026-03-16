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
      color: 'bg-gray-100 text-gray-800 border-gray-300',
      impact: 'No security filtering'
    },
    {
      mode: 'Weak',
      label: 'Weak',
      description: 'Basic input validation only.',
      color: 'bg-blue-100 text-blue-800 border-blue-300',
      impact: 'Minimal filtering'
    },
    {
      mode: 'Normal',
      label: 'Normal',
      description: 'Standard protection with policy enforcement.',
      color: 'bg-warning-100 text-warning-800 border-warning-300',
      impact: 'Balanced security'
    },
    {
      mode: 'Strong',
      label: 'Strong',
      description: 'Maximum security with strict validation.',
      color: 'bg-danger-100 text-danger-800 border-danger-300',
      impact: 'Most restrictive'
    }
  ];

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Security Mode Configuration</h3>
      
      {/* Current Mode Display */}
      <div className="mb-6">
        <div className="flex items-center space-x-3">
          <span className="text-sm font-medium text-gray-700">Current Mode:</span>
          <div className={`px-3 py-1 rounded-full text-sm font-medium border ${
            modes.find(m => m.mode === currentMode)?.color
          }`}>
            {currentMode}
          </div>
        </div>
      </div>

      {/* Mode Selection */}
      <div className="space-y-3">
        <p className="text-sm font-medium text-gray-700">Select Security Mode:</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {modes.map((mode) => (
            <button
              key={mode.mode}
              onClick={() => onModeChange(mode.mode)}
              disabled={isLoading || mode.mode === currentMode}
              className={`
                p-4 rounded-lg border-2 text-left transition-all
                ${currentMode === mode.mode
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                }
                ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
                ${mode.mode === currentMode ? 'cursor-default' : ''}
              `}
            >
              <div className="flex items-center justify-between mb-2">
                <div className={`px-2 py-1 rounded text-sm font-medium ${mode.color}`}>
                  {mode.label}
                </div>
                {currentMode === mode.mode && (
                  <span className="text-xs text-primary-600 font-medium">Active</span>
                )}
              </div>
              <p className="text-sm text-gray-600 mb-1">{mode.description}</p>
              <p className="text-xs text-gray-500 font-medium">{mode.impact}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Security Level Indicator */}
      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <h4 className="text-sm font-semibold text-gray-700 mb-3">Security Level Impact</h4>
        <div className="space-y-2 text-xs">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-success-500 rounded-full"></div>
            <span className="text-gray-600">Low Risk: Basic queries, calculations</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-warning-500 rounded-full"></div>
            <span className="text-gray-600">Medium Risk: Role manipulation, suspicious patterns</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-danger-500 rounded-full"></div>
            <span className="text-gray-600">High/Critical Risk: Injection attempts, tool abuse</span>
          </div>
        </div>
      </div>

      {isLoading && (
        <div className="mt-4 text-sm text-gray-600 flex items-center space-x-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
          <span>Updating security mode...</span>
        </div>
      )}
    </div>
  );
};
