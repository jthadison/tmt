/**
 * Agent Position Card Component
 *
 * Displays individual agent's position in disagreement analysis:
 * - Agent icon and name
 * - Action badge (BUY/SELL/NEUTRAL) color-coded
 * - Confidence meter
 * - Reasoning bullets
 * - Timestamp
 *
 * Story 7.1: AC5
 */

import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { AgentPosition } from '@/types/intelligence';
import { ConfidenceMeter } from './ConfidenceMeter';
import { AgentIcon } from './AgentIcon';

export interface AgentPositionCardProps {
  position: AgentPosition;
}

/**
 * AgentPositionCard displays individual agent trading position
 *
 * @param position - Agent position data with action, confidence, reasoning
 *
 * @example
 * <AgentPositionCard position={agentPosition} />
 */
export function AgentPositionCard({ position }: AgentPositionCardProps) {
  const actionConfig = {
    BUY: {
      icon: TrendingUp,
      color: 'text-green-600 dark:text-green-400',
      bg: 'bg-green-50 dark:bg-green-900/20'
    },
    SELL: {
      icon: TrendingDown,
      color: 'text-red-600 dark:text-red-400',
      bg: 'bg-red-50 dark:bg-red-900/20'
    },
    NEUTRAL: {
      icon: Minus,
      color: 'text-gray-600 dark:text-gray-400',
      bg: 'bg-gray-50 dark:bg-gray-800/50'
    }
  };

  const { icon: ActionIcon, color, bg } = actionConfig[position.action];

  const formatTimestamp = (timestamp: number): string => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  return (
    <div
      className="agent-position-card p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:shadow-md transition-shadow"
      data-testid="agent-position-card"
    >
      {/* Header: Agent name + Action */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <AgentIcon agentId={position.agentId} size="md" />
          <span className="font-semibold text-foreground">{position.agentName}</span>
        </div>
        <div className={`flex items-center gap-1 px-2 py-1 rounded ${bg}`}>
          <ActionIcon className={`w-4 h-4 ${color}`} />
          <span className={`text-sm font-semibold ${color}`}>
            {position.action}
          </span>
        </div>
      </div>

      {/* Confidence Meter */}
      <div className="mb-3">
        <ConfidenceMeter confidence={position.confidence} size="sm" />
      </div>

      {/* Reasoning */}
      {position.reasoning && position.reasoning.length > 0 && (
        <div className="reasoning">
          <h4 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
            Reasoning:
          </h4>
          <ul className="text-sm space-y-1">
            {position.reasoning.map((point, index) => (
              <li key={index} className="flex items-start gap-2">
                <span className="text-gray-500 dark:text-gray-500 mt-0.5">•</span>
                <span className="text-gray-700 dark:text-gray-300">{point}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Timestamp */}
      <div className="text-xs text-gray-500 dark:text-gray-400 mt-3">
        {formatTimestamp(position.timestamp)}
      </div>
    </div>
  );
}
