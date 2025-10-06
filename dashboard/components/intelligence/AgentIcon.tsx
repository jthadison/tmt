/**
 * Agent Icon Component
 *
 * Displays icon for each of the 8 AI agents
 *
 * Story 7.1: Supporting component
 */

import React from 'react';
import { AI_AGENTS } from '@/types/intelligence';

export interface AgentIconProps {
  agentId: string;
  size?: 'sm' | 'md' | 'lg';
}

/**
 * AgentIcon displays emoji icon for each agent
 *
 * @param agentId - Agent identifier (e.g., 'market-analysis')
 * @param size - Icon size: sm (16px), md (20px), lg (24px)
 *
 * @example
 * <AgentIcon agentId="market-analysis" size="md" />
 */
export function AgentIcon({ agentId, size = 'md' }: AgentIconProps) {
  const agent = AI_AGENTS.find(a => a.id === agentId);

  const sizes = {
    sm: 'text-base',
    md: 'text-xl',
    lg: 'text-2xl'
  };

  if (!agent) {
    return (
      <span className={`${sizes[size]}`} data-testid="agent-icon">
        🤖
      </span>
    );
  }

  return (
    <span
      className={`${sizes[size]}`}
      title={agent.name}
      data-testid="agent-icon"
      aria-label={agent.name}
    >
      {agent.icon}
    </span>
  );
}
