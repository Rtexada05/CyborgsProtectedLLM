import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/common/Header';
import { ChatWindow } from './components/chat/ChatWindow';
import { PromptComposer } from './components/chat/PromptComposer';
import { SecurityModeSelector } from './components/admin/SecurityModeSelector';
import { PageHeader } from './components/common/PageHeader';
import { MetricsOverview } from './components/dashboard/MetricsCard';
import { EventsTable } from './components/logs/EventsTable';
import { useChat } from './hooks/useChat';
import { useAdmin, useMetrics } from './hooks/useAdmin';
import { AdminDecisionRecord, SecurityMode } from './services/types';
import { apiService } from './services/api';
import './index.css';

const DEFAULT_LOGS_PAGE_SIZE = 10;
const DEFAULT_CHAT_USER_ID = 'demo-user';
const CHAT_COMPOSER_BOTTOM_SPACER = '22rem';

const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('chat');
  const [systemHealth, setSystemHealth] = useState<'ok' | 'warning' | 'error'>('ok');

  const { messages, isLoading: chatLoading, sendMessage, clearMessages } = useChat();
  const { securityMode, isLoading: adminLoading, updateSecurityMode } = useAdmin();
  const { metrics, isLoading: metricsLoading, refreshMetrics } = useMetrics();
  const [events, setEvents] = useState<AdminDecisionRecord[]>([]);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_LOGS_PAGE_SIZE);
  const [totalDecisions, setTotalDecisions] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [hasPrevious, setHasPrevious] = useState(false);
  const [hasNext, setHasNext] = useState(false);

  const fetchEvents = useCallback(async (page: number, limit: number) => {
    setEventsLoading(true);
    try {
      const decisionsResponse = await apiService.getDecisions(page, limit);
      setEvents(decisionsResponse.decisions);
      setCurrentPage(decisionsResponse.page);
      setPageSize(decisionsResponse.limit);
      setTotalDecisions(decisionsResponse.total_decisions);
      setTotalPages(decisionsResponse.total_pages);
      setHasPrevious(decisionsResponse.has_previous);
      setHasNext(decisionsResponse.has_next);
    } catch (error) {
      console.error('Failed to fetch events:', error);
    } finally {
      setEventsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (currentTab === 'logs') {
      fetchEvents(1, pageSize);
    }
    if (currentTab === 'dashboard') {
      refreshMetrics();
    }
  }, [currentTab, fetchEvents, refreshMetrics, pageSize]);

  useEffect(() => {
    const latestMessage = messages[messages.length - 1];
    if (!latestMessage || !latestMessage.trace_id) {
      return;
    }

    refreshMetrics();
    if (currentTab === 'logs') {
      fetchEvents(currentPage, pageSize);
    }
  }, [messages, currentTab, currentPage, pageSize, fetchEvents, refreshMetrics]);

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
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleModeChange = async (newMode: SecurityMode) => {
    try {
      await updateSecurityMode(newMode);
      refreshMetrics();
      if (currentTab === 'logs') {
        fetchEvents(currentPage, pageSize);
      }
    } catch (error) {
      console.error('Failed to update security mode:', error);
    }
  };

  const handlePageSizeChange = (nextPageSize: number) => {
    setPageSize(nextPageSize);
    setCurrentPage(1);
  };

  const handlePreviousPage = () => {
    if (!hasPrevious || eventsLoading) {
      return;
    }
    fetchEvents(currentPage - 1, pageSize);
  };

  const handleNextPage = () => {
    if (!hasNext || eventsLoading) {
      return;
    }
    fetchEvents(currentPage + 1, pageSize);
  };

  const renderContent = () => {
    switch (currentTab) {
      case 'chat':
        return (
          <div className="content-panel" style={{ paddingBottom: CHAT_COMPOSER_BOTTOM_SPACER }}>
            <ChatWindow
              messages={messages}
              isLoading={chatLoading}
              onSendMessage={sendMessage}
              onClearMessages={clearMessages}
            />
          </div>
        );

      case 'dashboard':
        return (
          <div className="content-panel overflow-y-auto p-6 sm:p-8">
            <PageHeader
              eyebrow="Threat monitoring"
              title="Security Dashboard"
              description="Monitor system performance, decision quality, and gateway resilience in real time."
            />
            <MetricsOverview metrics={metrics} isLoading={metricsLoading} />
          </div>
        );

      case 'admin':
        return (
          <div className="content-panel overflow-y-auto p-6 sm:p-8">
            <PageHeader
              eyebrow="Control surface"
              title="Admin Controls"
              description="Manage security posture and keep the gateway aligned with your risk tolerance."
            />
            <SecurityModeSelector
              currentMode={securityMode}
              onModeChange={handleModeChange}
              isLoading={adminLoading}
            />
          </div>
        );

      case 'logs':
        return (
          <div className="content-panel min-h-0 overflow-y-auto p-6 sm:p-8">
            <PageHeader
              eyebrow="Audit trail"
              title="Security Logs"
              description="Inspect recent decisions, trace activity, and review how the gateway handled risky requests."
              actions={
                <button
                  onClick={() => fetchEvents(currentPage, pageSize)}
                  disabled={eventsLoading}
                  className="glass-button"
                >
                  {eventsLoading ? 'Refreshing...' : 'Refresh'}
                </button>
              }
            />
            <EventsTable
              events={events}
              isLoading={eventsLoading}
              currentPage={currentPage}
              pageSize={pageSize}
              totalEvents={totalDecisions}
              totalPages={totalPages}
              hasPrevious={hasPrevious}
              hasNext={hasNext}
              onPageSizeChange={handlePageSizeChange}
              onPreviousPage={handlePreviousPage}
              onNextPage={handleNextPage}
            />
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="app-shell">
      <Header
        currentTab={currentTab}
        onTabChange={setCurrentTab}
        securityMode={securityMode}
        systemHealth={systemHealth}
      />

      <main className="content-shell flex-1 overflow-hidden pt-4">
        {renderContent()}
      </main>

      {currentTab === 'chat' && (
        <div className="pointer-events-none fixed inset-x-0 bottom-0 z-50 px-4 pb-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl">
            <div className="pointer-events-auto">
              <PromptComposer
                onSendMessage={sendMessage}
                isLoading={chatLoading}
                disabled={chatLoading}
                currentUserId={DEFAULT_CHAT_USER_ID}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
