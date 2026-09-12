import { useEffect, useState, useCallback } from 'react';
import { getAuthToken } from '../services/api';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * React hook for subscribing to real-time agent events via SSE
 */
export function useAgentEvents(runId = null) {
  const [events, setEvents] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);

  const connect = useCallback(() => {
    const token = getAuthToken();
    
    // Don't connect if no auth token (user not logged in)
    if (!token) {
      console.warn('[Agent Events] No auth token, skipping connection');
      return null;
    }

    const url = `${API_BASE}/api/v1/events/stream${runId ? `?run_id=${runId}` : ''}`;
    
    console.log('[Agent Events] Connecting to:', url);
    
    // EventSource doesn't support custom headers in browser, so we'll use query param fallback
    // Backend should also accept token via query param for EventSource compatibility
    const urlWithAuth = token ? `${url}${runId ? '&' : '?'}token=${token}` : url;
    
    const eventSource = new EventSource(urlWithAuth);
    
    eventSource.addEventListener('agent_event', (e) => {
      try {
        const event = JSON.parse(e.data);
        console.log('[Agent Events] Received:', event);
        setEvents((prev) => [...prev, event]);
        setError(null);
      } catch (err) {
        console.error('[Agent Events] Failed to parse event:', err);
        setError(err.message);
      }
    });
    
    eventSource.onopen = () => {
      console.log('[Agent Events] Connection opened');
      setIsConnected(true);
      setError(null);
    };
    
    eventSource.onerror = (err) => {
      console.error('[Agent Events] Connection error:', err);
      setIsConnected(false);
      setError('Connection lost');
      eventSource.close();
    };
    
    return eventSource;
  }, [runId]);

  useEffect(() => {
    const eventSource = connect();
    
    // Cleanup on unmount
    return () => {
      if (eventSource) {
        console.log('[Agent Events] Disconnecting');
        eventSource.close();
      }
    };
  }, [connect]);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  return {
    events,
    isConnected,
    error,
    clearEvents,
  };
}
