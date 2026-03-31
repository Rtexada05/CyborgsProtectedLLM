import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/common/Header';
import { ChatWindow } from './components/chat/ChatWindow';
import { SecurityModeSelector } from './components/admin/SecurityModeSelector';
import { MetricsOverview } from './components/dashboard/MetricsCard';
import { EventsTable } from './components/logs/EventsTable';
import { useChat } from './hooks/useChat';
import { useAdmin, useMetrics } from './hooks/useAdmin';
import { SecurityMode } from './services/types';
import { apiService } from './services/api';
import './index.css';

const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('chat');
  const [systemHealth, setSystemHealth] = useState<'ok' | 'warning' | 'error'>('ok');
  
  const { messages, isLoading: chatLoading, error: chatError, sendMessage, clearMessages } = useChat();
  const { securityMode, isLoading: adminLoading, updateSecurityMode } = useAdmin();
  const { metrics, isLoading: metricsLoading, refreshMetrics } = useMetrics();
  const [events, setEvents] = useState<any[]>([]);
  const [eventsLoading, setEventsLoading] = useState(false);

  const fetchEvents = useCallback(async () => {
    setEventsLoading(true);
    try {
      const decisionsResponse = await apiService.getDecisions(50);
      setEvents(decisionsResponse.decisions);
    } catch (error) {
      console.error('Failed to fetch events:', error);
    } finally {
      setEventsLoading(false);
    }
  }, []);

  // Fetch logs and dashboard data when their tabs are selected
  useEffect(() => {
    if (currentTab === 'logs') {
      fetchEvents();
    }
    if (currentTab === 'dashboard') {
      refreshMetrics();
    }
  }, [currentTab, fetchEvents, refreshMetrics]);

  // Refresh dashboard/log data after completed chat responses.
  useEffect(() => {
    const latestMessage = messages[messages.length - 1];
    if (!latestMessage || !latestMessage.trace_id) {
      return;
    }

    refreshMetrics();
    if (currentTab === 'logs') {
      fetchEvents();
    }
  }, [messages, currentTab, fetchEvents, refreshMetrics]);

  // Check system health periodically
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const health = await apiService.getHealth();
        setSystemHealth(health.status === 'ok' ? 'ok' : 'warning');
      } catch (error) {
        setSystemHealth('error');
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const handleModeChange = async (newMode: SecurityMode) => {
    try {
      await updateSecurityMode(newMode);
      refreshMetrics(); // Refresh metrics after mode change
      if (currentTab === 'logs') {
        fetchEvents();
      }
    } catch (error) {
      console.error('Failed to update security mode:', error);
    }
  };

  const renderContent = () => {
    switch (currentTab) {
      case 'chat':
        return (
          <div className="h-full">
            <ChatWindow
              messages={messages}
              isLoading={chatLoading}
              error={chatError}
              onSendMessage={sendMessage}
              onClearMessages={clearMessages}
            />
          </div>
        );

      case 'dashboard':
        return (
          <div className="p-6">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Security Dashboard</h2>
              <p className="text-gray-600">Monitor system performance and security metrics</p>
            </div>
            <MetricsOverview metrics={metrics} isLoading={metricsLoading} />
          </div>
        );

      case 'admin':
        return (
          <div className="p-6">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Admin Controls</h2>
              <p className="text-gray-600">Manage security settings and system configuration</p>
            </div>
            <SecurityModeSelector
              currentMode={securityMode}
              onModeChange={handleModeChange}
              isLoading={adminLoading}
            />
          </div>
        );

      case 'logs':
        return (
          <div className="p-6">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Security Logs</h2>
                <p className="text-gray-600">View recent security events and decisions</p>
              </div>
              <button
                onClick={fetchEvents}
                disabled={eventsLoading}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                {eventsLoading ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>
            <EventsTable events={events} isLoading={eventsLoading} />
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      <Header
        currentTab={currentTab}
        onTabChange={setCurrentTab}
        securityMode={securityMode}
        systemHealth={systemHealth}
      />
      
      <main className="flex-1 overflow-hidden">
        {renderContent()}
      </main>
    </div>
  );
};

export default App;
