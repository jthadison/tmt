/**
 * Confirming Agent Card Component
 * Displays a confirming agent's details in decision history
 * Story 7.2: AC2
 */

import React from 'react';
import { AgentIcon } from './AgentIcon';
import { ConfidenceMeter } from './ConfidenceMeter';

export interface ConfirmingAgentCardProps {
  agent: {
    agentId: string;
    agentName: string;
    confidence: number;
    reasoning: string[];
  };
}

/**
 * Display a confirming agent's contribution to a trade decision
 */
export function ConfirmingAgentCard({ agent }: ConfirmingAgentCardProps) {
  return (
    <div
      className="p-3 bg-surface/50 border border-border rounded-lg"
      data-testid={`confirming-agent-${agent.agentId}`}
    >
      <div className="flex items-center gap-2 mb-2">
        <AgentIcon agentId={agent.agentId} size="sm" />
        <span className="font-medium text-sm">{agent.agentName}</span>
      </div>

      <ConfidenceMeter confidence={agent.confidence} size="sm" showLabel={false} />

      <div className="mt-2">
        <h6 className="text-xs font-medium text-secondary mb-1">Reasoning:</h6>
        <ul className="text-xs space-y-0.5">
          {agent.reasoning.map((point, index) => (
            <li key={index} className="flex items-start gap-1">
              <span className="text-primary mt-0.5">•</span>
              <span className="text-secondary">{point}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
