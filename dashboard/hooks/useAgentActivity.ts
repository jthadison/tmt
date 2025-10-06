/**
 * Agent Activity Hook
 * Manages SSE connection for real-time agent activity events
 * Story 7.3: Supporting hook for AgentActivityFeed
 */

'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { AgentActivityEvent } from '@/types/intelligence';

interface UseAgentActivityOptions {
  /** Enable activity stream */
  enabled?: boolean;
  /** Callback when new event received */
  onEvent?: (event: AgentActivityEvent) => void;
  /** Callback when error occurs */
  onError?: (error: Error) => void;
  /** Callback when connection status changes */
  onConnectionChange?: (connected: boolean) => void;
  /** Maximum number of events to keep in history */
  maxHistory?: number;
}

interface UseAgentActivityReturn {
  /** Connection status */
  connected: boolean;
  /** Latest event */
  lastEvent: AgentActivityEvent | null;
  /** Connection error */
  error: string | null;
  /** Manually reconnect */
  reconnect: () => void;
  /** Disconnect */
  disconnect: () => void;
  /** Recent events history */
  eventHistory: AgentActivityEvent[];
}

export function useAgentActivity({
  enabled = true,
  onEvent,
  onError,
  onConnectionChange,
  maxHistory = 100
}: UseAgentActivityOptions = {}): UseAgentActivityReturn {
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<AgentActivityEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [eventHistory, setEventHistory] = useState<AgentActivityEvent[]>([]);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  const connect = useCallback(() => {
    if (!enabled) return;

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      const eventSource = new EventSource('/api/agent-activity');
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('Agent activity stream connected');
        setConnected(true);
        setError(null);
        onConnectionChange?.(true);
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Handle different message types
          if (data.type === 'connected') {
            console.log('Agent activity stream:', data.message);
            return;
          }

          if (data.type === 'error') {
            console.error('Agent activity error:', data.error);
            setError(data.error);
            onError?.(new Error(data.error));
            return;
          }

          // Regular activity event
          const activityEvent = data as AgentActivityEvent;
          setLastEvent(activityEvent);
          onEvent?.(activityEvent);

          // Add to history
          setEventHistory((prev) => {
            const updated = [activityEvent, ...prev].slice(0, maxHistory);
            return updated;
          });

        } catch (err) {
          console.error('Failed to parse agent activity event:', err);
          setError('Failed to parse event data');
          onError?.(err as Error);
        }
      };

      eventSource.onerror = (err) => {
        console.error('Agent activity stream error:', err);
        setConnected(false);
        setError('Connection error');
        onConnectionChange?.(false);
        onError?.(new Error('EventSource connection failed'));

        // Attempt to reconnect after 5 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting to reconnect agent activity stream...');
          connect();
        }, 5000);
      };

    } catch (err) {
      console.error('Failed to create EventSource:', err);
      setError('Failed to connect');
      onError?.(err as Error);
    }
  }, [enabled, onEvent, onError, onConnectionChange, maxHistory]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    setConnected(false);
    onConnectionChange?.(false);
  }, [onConnectionChange]);

  const reconnect = useCallback(() => {
    disconnect();
    setTimeout(connect, 100);
  }, [connect, disconnect]);

  // Auto-connect on mount if enabled
  useEffect(() => {
    if (enabled) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  return {
    connected,
    lastEvent,
    error,
    reconnect,
    disconnect,
    eventHistory
  };
}
