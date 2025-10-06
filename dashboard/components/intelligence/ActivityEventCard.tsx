/**
 * Activity Event Card Component
 * Displays individual agent activity events with animation
 * Story 7.3: AC6 - Activity Event Card with Animation
 */

'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Activity, TrendingUp, Target, Users, XCircle } from 'lucide-react';
import { AgentActivityEvent } from '@/types/intelligence';
import { AgentIcon } from './AgentIcon';
import { ActionBadge } from './ActionBadge';

interface ActivityEventCardProps {
  event: AgentActivityEvent;
}

const eventConfig = {
  signal_generated: {
    icon: Activity,
    color: 'text-blue-600 dark:text-blue-400',
    bg: 'bg-blue-500/10 dark:bg-blue-500/20'
  },
  trade_executed: {
    icon: TrendingUp,
    color: 'text-green-600 dark:text-green-400',
    bg: 'bg-green-500/10 dark:bg-green-500/20'
  },
  pattern_detected: {
    icon: Target,
    color: 'text-purple-600 dark:text-purple-400',
    bg: 'bg-purple-500/10 dark:bg-purple-500/20'
  },
  disagreement_resolved: {
    icon: Users,
    color: 'text-yellow-600 dark:text-yellow-400',
    bg: 'bg-yellow-500/10 dark:bg-yellow-500/20'
  },
  threshold_not_met: {
    icon: XCircle,
    color: 'text-gray-600 dark:text-gray-400',
    bg: 'bg-gray-500/10 dark:bg-gray-500/20'
  }
};

function formatRelativeTime(timestamp: number): string {
  const now = Date.now();
  const diff = now - timestamp;
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) return `${days}d ago`;
  if (hours > 0) return `${hours}h ago`;
  if (minutes > 0) return `${minutes}m ago`;
  return 'Just now';
}

export function ActivityEventCard({ event }: ActivityEventCardProps) {
  const [expanded, setExpanded] = useState(false);

  const { icon: EventIcon, color, bg } = eventConfig[event.eventType];

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`activity-event-card p-3 rounded-lg border border-gray-200 dark:border-gray-700 ${bg}`}
      data-testid="activity-event-card"
    >
      {/* Header */}
      <div className="flex items-start gap-3 mb-2">
        {/* Event icon */}
        <div className={`w-8 h-8 rounded-full ${bg} flex items-center justify-center flex-shrink-0`}>
          <EventIcon className={`w-4 h-4 ${color}`} />
        </div>

        {/* Event details */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <AgentIcon agentId={event.agentId} size="sm" />
            <span className="text-sm font-medium truncate text-gray-900 dark:text-gray-100">
              {event.agentName}
            </span>
            <ActionBadge action={event.action} size="sm" />
          </div>

          <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
            <span className="font-mono font-semibold text-gray-700 dark:text-gray-300">
              {event.symbol}
            </span>
            <span>•</span>
            <span>{event.confidence}%</span>
            <span>•</span>
            <span>{formatRelativeTime(event.timestamp)}</span>
          </div>
        </div>
      </div>

      {/* Reasoning */}
      <div className="ml-11 text-xs">
        <ul className="space-y-0.5">
          {event.reasoning.slice(0, expanded ? undefined : 1).map((point, index) => (
            <li key={index} className="flex items-start gap-1 text-gray-700 dark:text-gray-300">
              <span className={color}>•</span>
              <span>{point}</span>
            </li>
          ))}
        </ul>

        {event.reasoning.length > 1 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-blue-600 dark:text-blue-400 hover:underline mt-1"
          >
            {expanded ? 'Show less' : `+${event.reasoning.length - 1} more`}
          </button>
        )}
      </div>

      {/* Metadata */}
      {event.metadata && (
        <div className="ml-11 mt-2 text-xs text-gray-500 dark:text-gray-400 flex items-center gap-2 flex-wrap">
          {event.metadata.consensusPercentage !== undefined && (
            <span>Consensus: {event.metadata.consensusPercentage}%</span>
          )}
          {event.metadata.patternType && (
            <>
              {event.metadata.consensusPercentage !== undefined && <span>•</span>}
              <span className="capitalize">
                {event.metadata.patternType.replace(/-/g, ' ')}
              </span>
            </>
          )}
          {event.metadata.sessionContext && (
            <>
              {(event.metadata.consensusPercentage !== undefined || event.metadata.patternType) && (
                <span>•</span>
              )}
              <span>{event.metadata.sessionContext}</span>
            </>
          )}
          {event.metadata.pnl !== undefined && (
            <>
              <span>•</span>
              <span className={event.metadata.pnl >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}>
                P/L: ${event.metadata.pnl.toFixed(2)}
              </span>
            </>
          )}
        </div>
      )}
    </motion.div>
  );
}
