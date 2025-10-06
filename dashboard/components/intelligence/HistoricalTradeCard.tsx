/**
 * Historical Trade Card Component
 * Compact trade card for historical trades list
 * Story 7.2: AC7
 */

import React from 'react';
import { EnhancedTradeRecord } from '@/types/intelligence';
import { OutcomeBadge } from './OutcomeBadge';

export interface HistoricalTradeCardProps {
  trade: EnhancedTradeRecord;
  compact?: boolean;
  onClick?: () => void;
}

/**
 * Display a compact historical trade card
 */
export function HistoricalTradeCard({ trade, compact = false, onClick }: HistoricalTradeCardProps) {
  const formattedDate = new Date(trade.timestamp).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });

  return (
    <div
      className={`historical-trade-card p-3 bg-surface border border-border rounded-lg hover:border-primary transition-colors ${
        onClick ? 'cursor-pointer' : ''
      }`}
      onClick={onClick}
      data-testid={`historical-trade-${trade.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        {/* Trade Info */}
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold text-foreground">{trade.symbol}</span>
            <span
              className={`text-xs font-medium px-2 py-0.5 rounded ${
                trade.action === 'BUY'
                  ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                  : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
              }`}
            >
              {trade.action}
            </span>
          </div>

          <div className="text-xs text-secondary space-y-0.5">
            <div className="flex items-center gap-2">
              <span>Price: <span className="font-mono text-foreground">{trade.price.toFixed(4)}</span></span>
              <span>Qty: <span className="font-mono text-foreground">{trade.quantity}</span></span>
            </div>
            <div>{formattedDate}</div>
          </div>

          {/* Pattern info (if available and not compact) */}
          {!compact && trade.patternDetected && (
            <div className="mt-2 text-xs text-primary">
              Pattern: {trade.patternDetected.patternType}
            </div>
          )}
        </div>

        {/* Outcome */}
        <div className="flex-shrink-0">
          {trade.outcome && (
            <OutcomeBadge outcome={trade.outcome} profitLoss={trade.profitLoss} />
          )}
        </div>
      </div>

      {/* Agent consensus (if available and not compact) */}
      {!compact && trade.agentAttribution && (
        <div className="mt-2 pt-2 border-t border-border">
          <div className="text-xs text-secondary">
            Consensus: <span className="font-semibold text-foreground">{trade.agentAttribution.consensusPercentage}%</span>
            {trade.agentAttribution.sessionContext && (
              <span className="ml-2">
                Session: <span className="text-foreground">{trade.agentAttribution.sessionContext}</span>
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
