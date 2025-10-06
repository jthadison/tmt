/**
 * Agent Activity Feed Component
 * Real-time scrollable list of agent activity events
 * Story 7.3: AC5 - Real-Time Agent Activity Feed Component
 */

'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Wifi, WifiOff, Trash2 } from 'lucide-react';
import { useAgentActivity } from '@/hooks/useAgentActivity';
import { AgentActivityEvent } from '@/types/intelligence';
import { ActivityEventCard } from './ActivityEventCard';
import { AgentFilter } from './AgentFilter';

interface ConnectionIndicatorProps {
  connected: boolean;
}

function ConnectionIndicator({ connected }: ConnectionIndicatorProps) {
  return (
    <div className="flex items-center gap-2">
      {connected ? (
        <>
          <Wifi className="w-4 h-4 text-green-600 dark:text-green-400" />
          <span className="text-xs text-green-600 dark:text-green-400">Live</span>
        </>
      ) : (
        <>
          <WifiOff className="w-4 h-4 text-red-600 dark:text-red-400" />
          <span className="text-xs text-red-600 dark:text-red-400">Disconnected</span>
        </>
      )}
    </div>
  );
}

export function AgentActivityFeed() {
  const [events, setEvents] = useState<AgentActivityEvent[]>([]);
  const [paused, setPaused] = useState(false);
  const [filterAgent, setFilterAgent] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Use the agent activity hook
  const { connected, lastEvent, error, eventHistory } = useAgentActivity({
    enabled: true,
    maxHistory: 100
  });

  // Update events when new event arrives
  useEffect(() => {
    if (!lastEvent) return;

    // Apply filter
    if (filterAgent && lastEvent.agentId !== filterAgent) return;

    setEvents((prev) => {
      // Add to top, limit to 100 events
      const updated = [lastEvent, ...prev].slice(0, 100);
      return updated;
    });

    // Auto-scroll to top if not paused and user at top
    if (!paused && containerRef.current) {
      const isAtTop = containerRef.current.scrollTop < 50;
      if (isAtTop) {
        containerRef.current.scrollTo({ top: 0, behavior: 'smooth' });
      }
    }
  }, [lastEvent, filterAgent, paused]);

  // Update events when filter changes
  useEffect(() => {
    if (filterAgent) {
      // Filter existing events
      setEvents(eventHistory.filter((e) => e.agentId === filterAgent).slice(0, 100));
    } else {
      // Show all events
      setEvents(eventHistory.slice(0, 100));
    }
  }, [filterAgent, eventHistory]);

  // Pause when user scrolls down
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.target as HTMLDivElement;
    const isAtTop = target.scrollTop < 50;
    setPaused(!isAtTop);
  };

  const handleClear = () => {
    setEvents([]);
  };

  return (
    <div className="agent-activity-feed h-full flex flex-col bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="feed-header p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Agent Activity
          </h3>
          <div className="flex items-center gap-2">
            <ConnectionIndicator connected={connected} />
            {paused && (
              <button
                onClick={() => {
                  setPaused(false);
                  if (containerRef.current) {
                    containerRef.current.scrollTo({ top: 0, behavior: 'smooth' });
                  }
                }}
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
              >
                Resume
              </button>
            )}
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2">
          <AgentFilter value={filterAgent} onChange={setFilterAgent} />
          <button
            onClick={handleClear}
            className="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 px-3 py-1.5 border border-gray-300 dark:border-gray-700 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
            title="Clear all events"
          >
            <Trash2 className="w-3 h-3" />
            Clear
          </button>
        </div>

        {/* Error message */}
        {error && (
          <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-xs text-red-800 dark:text-red-200">
            {error}
          </div>
        )}
      </div>

      {/* Event list */}
      <div
        ref={containerRef}
        className="feed-content flex-1 overflow-y-auto p-4 space-y-3"
        onScroll={handleScroll}
        data-testid="feed-content"
      >
        {events.length === 0 && (
          <div className="text-center text-gray-500 dark:text-gray-400 py-8">
            {connected ? (
              <>
                <div className="text-4xl mb-2">👀</div>
                <div>Waiting for agent activity...</div>
              </>
            ) : (
              <>
                <div className="text-4xl mb-2">🔌</div>
                <div>Connecting to activity stream...</div>
              </>
            )}
          </div>
        )}

        {events.map((event) => (
          <ActivityEventCard key={event.eventId} event={event} />
        ))}
      </div>

      {/* Footer info */}
      <div className="feed-footer px-4 py-2 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400">
        {events.length > 0 && (
          <div className="flex items-center justify-between">
            <span>Showing {events.length} event{events.length !== 1 ? 's' : ''}</span>
            {paused && (
              <span className="text-yellow-600 dark:text-yellow-400">⏸ Paused (scroll to top to resume)</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
