/**
 * Agent Disagreement Panel Component
 *
 * Main component displaying agent disagreement visualization:
 * - Consensus meter showing agreement percentage
 * - Individual agent position cards
 * - Final decision badge with threshold explanation
 *
 * Story 7.1: AC3
 */

'use client';

import React from 'react';
import { useAgentDisagreement } from '@/hooks/useAgentDisagreement';
import { ConsensusMeter } from './ConsensusMeter';
import { DecisionBadge } from './DecisionBadge';
import { AgentPositionCard } from './AgentPositionCard';
import { Loader2, AlertCircle } from 'lucide-react';

export interface AgentDisagreementPanelProps {
  symbol: string;
  isExpanded: boolean;
  refreshInterval?: number;
}

/**
 * AgentDisagreementPanel displays comprehensive agent disagreement analysis
 *
 * @param symbol - Trading symbol to analyze
 * @param isExpanded - Whether panel is expanded/visible
 * @param refreshInterval - Auto-refresh interval in milliseconds (optional)
 *
 * @example
 * <AgentDisagreementPanel
 *   symbol="EUR_USD"
 *   isExpanded={true}
 *   refreshInterval={5000}
 * />
 */
export function AgentDisagreementPanel({
  symbol,
  isExpanded,
  refreshInterval = 10000
}: AgentDisagreementPanelProps) {
  const { data: disagreement, loading, error } = useAgentDisagreement({
    symbol,
    enabled: isExpanded,
    refreshInterval: isExpanded ? refreshInterval : undefined
  });

  if (!isExpanded) return null;

  // Loading state
  if (loading && !disagreement) {
    return (
      <div className="agent-disagreement-panel p-6 bg-white dark:bg-gray-800 rounded-lg">
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          <span className="ml-3 text-gray-600 dark:text-gray-400">
            Loading agent disagreement data...
          </span>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="agent-disagreement-panel p-6 bg-white dark:bg-gray-800 rounded-lg">
        <div className="flex items-center justify-center py-12">
          <AlertCircle className="w-8 h-8 text-red-600" />
          <span className="ml-3 text-red-600 dark:text-red-400">
            Failed to load disagreement data: {error.message}
          </span>
        </div>
      </div>
    );
  }

  // No data state
  if (!disagreement) {
    return (
      <div className="agent-disagreement-panel p-6 bg-white dark:bg-gray-800 rounded-lg">
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          No disagreement data available for {symbol}
        </div>
      </div>
    );
  }

  const agreeingAgents = disagreement.agentPositions.filter(
    p => p.action === disagreement.finalDecision
  ).length;

  return (
    <div className="agent-disagreement-panel p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      {/* Consensus Section */}
      <div className="consensus-section mb-6">
        <h3 className="text-lg font-semibold mb-4 text-foreground">Agent Consensus</h3>
        <div className="flex items-center gap-6">
          <ConsensusMeter
            percentage={disagreement.consensusPercentage}
            threshold={disagreement.requiredThreshold}
          />
          <div>
            <div className="text-3xl font-bold text-foreground">
              {disagreement.consensusPercentage}%
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              {agreeingAgents} of {disagreement.agentPositions.length} agents agree
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">
              Last updated: {new Date(disagreement.timestamp).toLocaleTimeString()}
            </div>
          </div>
        </div>
      </div>

      {/* Final Decision */}
      <div className="final-decision mb-6">
        <h3 className="text-lg font-semibold mb-3 text-foreground">Final Decision</h3>
        <DecisionBadge
          decision={disagreement.finalDecision}
          thresholdMet={disagreement.thresholdMet}
          threshold={disagreement.requiredThreshold}
          actualPercentage={disagreement.consensusPercentage}
        />
      </div>

      {/* Individual Agent Positions */}
      <div className="agent-positions">
        <h3 className="text-lg font-semibold mb-4 text-foreground">
          Individual Agent Positions
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {disagreement.agentPositions.map(position => (
            <AgentPositionCard key={position.agentId} position={position} />
          ))}
        </div>
      </div>
    </div>
  );
}
