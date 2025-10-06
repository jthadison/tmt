/**
 * Action Badge Component
 * Displays BUY/SELL/NEUTRAL action with color coding
 * Story 7.3: Supporting component for activity feed
 */

'use client';

import React from 'react';

interface ActionBadgeProps {
  action: 'BUY' | 'SELL' | 'NEUTRAL';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function ActionBadge({ action, size = 'md', className = '' }: ActionBadgeProps) {
  const sizeClasses = {
    sm: 'text-xs px-1.5 py-0.5',
    md: 'text-sm px-2 py-1',
    lg: 'text-base px-3 py-1.5'
  };

  const colorClasses = {
    BUY: 'bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20',
    SELL: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20',
    NEUTRAL: 'bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20'
  };

  return (
    <span
      className={`inline-flex items-center font-semibold rounded border ${sizeClasses[size]} ${colorClasses[action]} ${className}`}
      data-testid="action-badge"
    >
      {action}
    </span>
  );
}
