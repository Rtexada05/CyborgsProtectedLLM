import React from 'react';
import { Shield, Activity, Settings, FileText } from 'lucide-react';
import { SecurityMode } from '../../services/types';

interface HeaderProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
  securityMode: SecurityMode;
  systemHealth: 'ok' | 'warning' | 'error';
}

export const Header: React.FC<HeaderProps> = ({ 
  currentTab, 
  onTabChange, 
  securityMode, 
  systemHealth 
}) => {
  const tabs = [
    { id: 'chat', label: 'Chat', icon: Shield },
    { id: 'dashboard', label: 'Dashboard', icon: Activity },
    { id: 'admin', label: 'Admin', icon: Settings },
    { id: 'logs', label: 'Logs', icon: FileText }
  ];

  const getHealthColor = () => {
    switch (systemHealth) {
      case 'ok': return 'bg-success-500';
      case 'warning': return 'bg-warning-500';
      case 'error': return 'bg-danger-500';
      default: return 'bg-gray-500';
    }
  };

  const getModeColor = () => {
    switch (securityMode) {
      case 'Off': return 'bg-gray-100 text-gray-800';
      case 'Weak': return 'bg-blue-100 text-blue-800';
      case 'Normal': return 'bg-warning-100 text-warning-800';
      case 'Strong': return 'bg-danger-100 text-danger-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <header className="bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-20">
          {/* Logo and Title */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Shield className="h-9 w-9 text-primary-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  Cyborgs Protected Chat System
                </h1>
                <p className="text-base text-gray-500">Protected LLM Gateway</p>
              </div>
            </div>
          </div>

          {/* Status Indicators */}
          <div className="flex items-center space-x-4">
            {/* Security Mode Badge */}
            <div className={`rounded-full px-4 py-2 text-base font-medium ${getModeColor()}`}>
              Mode: {securityMode}
            </div>
            
            {/* Health Status */}
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${getHealthColor()}`}></div>
              <span className="text-base text-gray-600">
                System {systemHealth}
              </span>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex space-x-8">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = currentTab === tab.id;
            
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`
                  flex items-center space-x-2 px-1 py-4 border-b-2 text-base font-medium
                  ${isActive 
                    ? 'border-primary-500 text-primary-600' 
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                <Icon className="h-5 w-5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
};
