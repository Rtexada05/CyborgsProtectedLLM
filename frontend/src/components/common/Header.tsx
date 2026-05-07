import React from 'react';
import { Activity, FileText, MessageSquare, Settings } from 'lucide-react';
import { SecurityMode } from '../../services/types';
import { BrandLogo } from './BrandLogo';
import { HealthStatusChip } from './HealthStatusChip';

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
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'dashboard', label: 'Dashboard', icon: Activity },
    { id: 'admin', label: 'Admin', icon: Settings },
    { id: 'logs', label: 'Logs', icon: FileText }
  ];

  const getModeColor = () => {
    switch (securityMode) {
      case 'Off':
        return 'border-white/15 bg-white/10 text-cyber-200';
      case 'Weak':
        return 'border-primary-400/25 bg-primary-500/15 text-primary-100';
      case 'Normal':
        return 'border-warning-400/25 bg-warning-500/15 text-warning-100';
      case 'Strong':
        return 'border-danger-400/25 bg-danger-500/15 text-danger-100';
      default:
        return 'border-white/15 bg-white/10 text-cyber-200';
    }
  };

  return (
    <header className="relative z-10 pt-4 sm:pt-6">
      <div className="content-shell">
        <div className="cyber-panel-subtle animate-enter overflow-hidden px-4 py-4 sm:px-6">
          <div className="flex flex-col gap-5">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
              <div className="flex items-center gap-4">
                <div className="rounded-2xl border border-primary-300/20 bg-cyber-950/70 p-2.5 shadow-[0_0_30px_rgba(78,207,255,0.12)]">
                  <BrandLogo className="h-14 w-14 sm:h-16 sm:w-16" />
                </div>
                <div>
                  <p className="section-kicker mb-1">Protected LLM Gateway</p>
                  <h1 className="text-2xl font-semibold tracking-[0.16em] text-white sm:text-3xl">CYBORGS</h1>
                  <p className="text-sm uppercase tracking-[0.25em] text-primary-200/80 sm:text-[0.92rem]">
                    Secure. Detect. Defend.
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <div className={`status-pill ${getModeColor()}`}>
                  <span className="text-cyber-400">Mode</span>
                  <span>{securityMode}</span>
                </div>
                <HealthStatusChip
                  status={systemHealth}
                  className={systemHealth === 'ok' ? 'shadow-[0_0_28px_rgba(20,179,119,0.15)]' : ''}
                />
              </div>
            </div>

            <nav className="flex flex-wrap gap-2">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = currentTab === tab.id;

                return (
                  <button
                    key={tab.id}
                    onClick={() => onTabChange(tab.id)}
                    className={`inline-flex items-center gap-2 rounded-full border px-4 py-2.5 text-sm font-medium transition ${
                      isActive
                        ? 'border-primary-300/45 bg-primary-500/20 text-white shadow-[0_0_30px_rgba(78,207,255,0.12)]'
                        : 'border-white/10 bg-white/5 text-cyber-300 hover:border-primary-400/30 hover:bg-primary-500/10 hover:text-white'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>
        </div>
      </div>
    </header>
  );
};
