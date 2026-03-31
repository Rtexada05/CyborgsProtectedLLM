import { useState, useCallback, useEffect } from 'react';
import { apiService } from '../services/api';
import { SecurityMode, ModeResponse, AdminMetricsResponse } from '../services/types';

export const useAdmin = () => {
  const [securityMode, setSecurityMode] = useState<SecurityMode>('Normal');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSecurityMode = useCallback(async () => {
    try {
      const response: ModeResponse = await apiService.getSecurityMode();
      setSecurityMode(response.active_mode);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch security mode');
    }
  }, []);

  const updateSecurityMode = useCallback(async (newMode: SecurityMode) => {
    setIsLoading(true);
    setError(null);

    try {
      const response: ModeResponse = await apiService.setSecurityMode({ mode: newMode });
      setSecurityMode(response.active_mode);
      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update security mode');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSecurityMode();
  }, [fetchSecurityMode]);

  return {
    securityMode,
    isLoading,
    error,
    updateSecurityMode,
    refreshSecurityMode: fetchSecurityMode
  };
};

export const useMetrics = () => {
  const [metrics, setMetrics] = useState<AdminMetricsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response: AdminMetricsResponse = await apiService.getMetrics();
      setMetrics(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch metrics');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  return {
    metrics,
    isLoading,
    error,
    refreshMetrics: fetchMetrics
  };
};
