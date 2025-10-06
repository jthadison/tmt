/**
 * Agent Filter Component
 * Dropdown filter for agent activity feed
 * Story 7.3: AC7 - Activity Feed Filters and Controls
 */

'use client';

import React from 'react';
import { AI_AGENTS } from '@/types/intelligence';

interface AgentFilterProps {
  value: string | null;
  onChange: (agentId: string | null) => void;
  className?: string;
}

export function AgentFilter({ value, onChange, className = '' }: AgentFilterProps) {
  return (
    <select
      value={value || ''}
      onChange={(e) => onChange(e.target.value || null)}
      className={`text-sm px-3 py-1.5 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded hover:border-gray-400 dark:hover:border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 ${className}`}
      aria-label="Filter by agent"
    >
      <option value="">All Agents</option>
      {AI_AGENTS.map((agent) => (
        <option key={agent.id} value={agent.id}>
          {agent.icon} {agent.name}
        </option>
      ))}
    </select>
  );
}
