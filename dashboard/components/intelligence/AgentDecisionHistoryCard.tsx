/**
 * Agent Decision History Card Component
 * Displays historical agent decision reasoning for a trade
 * Story 7.2: AC2
 */

import React from 'react';
import { EnhancedTradeRecord } from '@/types/intelligence';
import { AgentIcon } from './AgentIcon';
import { ConfidenceMeter } from './ConfidenceMeter';
import { OutcomeBadge } from './OutcomeBadge';
import { ConfirmingAgentCard } from './ConfirmingAgentCard';
import { TrendingUp } from 'lucide-react';

export interface AgentDecisionHistoryCardProps {
  trade: EnhancedTradeRecord;
}

/**
 * Display agent decision history for a trade
 */
export function AgentDecisionHistoryCard({ trade }: AgentDecisionHistoryCardProps) {
  if (!trade.agentAttribution) {
    return (
      <div className="agent-decision-history-card p-6 bg-card border border-border rounded-lg">
        <div className="text-center py-8">
          <p className="text-secondary text-sm">No agent attribution data available for this trade</p>
        </div>
      </div>
    );
  }

  const { primaryAgent, confirmingAgents, consensusPercentage, sessionContext } = trade.agentAttribution;

  return (
    <div className="agent-decision-history-card p-6 bg-card border border-border rounded-lg" data-testid="agent-decision-history-card">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-foreground">Agent Decision History</h3>
        {trade.outcome && (
          <OutcomeBadge outcome={trade.outcome} profitLoss={trade.profitLoss} />
        )}
      </div>

      {/* Consensus Summary */}
      <div className="consensus-summary mb-6 p-4 bg-surface rounded-lg">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm text-secondary">Consensus at Trade Time</div>
            <div className="text-2xl font-bold text-foreground">{consensusPercentage}%</div>
          </div>
          {sessionContext && (
            <div className="text-right">
              <div className="text-sm text-secondary">Session</div>
              <div className="font-medium text-foreground">{sessionContext}</div>
            </div>
          )}
        </div>
      </div>

      {/* Primary Agent */}
      <div className="primary-agent mb-6">
        <h4 className="text-sm font-medium text-secondary mb-3">Primary Signal Agent</h4>
        <div className="p-4 bg-surface border-2 border-primary rounded-lg">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <AgentIcon agentId={primaryAgent.agentId} size="md" />
              <span className="font-semibold text-foreground">{primaryAgent.agentName}</span>
            </div>
          </div>

          <ConfidenceMeter confidence={primaryAgent.confidence} size="md" />

          <div className="mt-3">
            <h5 className="text-sm font-medium mb-2 text-foreground">Reasoning:</h5>
            <ul className="text-sm space-y-1">
              {primaryAgent.reasoning.map((point, index) => (
                <li key={index} className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  <span className="text-foreground">{point}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Confirming Agents */}
      {confirmingAgents && confirmingAgents.length > 0 && (
        <div className="confirming-agents mb-6">
          <h4 className="text-sm font-medium text-secondary mb-3">
            Confirming Agents ({confirmingAgents.length})
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {confirmingAgents.map(agent => (
              <ConfirmingAgentCard key={agent.agentId} agent={agent} />
            ))}
          </div>
        </div>
      )}

      {/* Pattern Detection */}
      {trade.patternDetected && (
        <div className="pattern-detected p-4 bg-info/10 border border-info rounded-lg">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 bg-info rounded-full flex items-center justify-center flex-shrink-0">
              <TrendingUp className="w-5 h-5 text-white" />
            </div>
            <div className="flex-1">
              <h5 className="font-semibold text-foreground">Pattern Detected</h5>
              <p className="text-sm mt-1 text-secondary">{trade.patternDetected.patternType}</p>
              <div className="mt-2">
                <ConfidenceMeter
                  confidence={trade.patternDetected.confidence}
                  size="sm"
                  showLabel={false}
                />
              </div>
              <div className="mt-3 text-sm space-y-1">
                <div className="flex justify-between">
                  <span className="text-secondary">Entry:</span>
                  <span className="font-mono text-foreground">{trade.patternDetected.keyLevels.entry}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-secondary">Target:</span>
                  <span className="font-mono text-success">{trade.patternDetected.keyLevels.target}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-secondary">Stop Loss:</span>
                  <span className="font-mono text-danger">{trade.patternDetected.keyLevels.stopLoss}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
