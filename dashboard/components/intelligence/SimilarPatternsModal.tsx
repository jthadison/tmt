/**
 * Similar Patterns Modal Component
 * Shows historical trades with similar patterns
 * Story 7.2: AC7
 */

import React, { useState, useEffect } from 'react';
import { EnhancedTradeRecord, PatternStats, formatPatternType } from '@/types/intelligence';
import { fetchTradesByPattern } from '@/services/api/patterns';
import { HistoricalTradeCard } from './HistoricalTradeCard';
import { X } from 'lucide-react';

export interface SimilarPatternsModalProps {
  patternType: string;
  isOpen: boolean;
  onClose: () => void;
  symbol?: string;
}

/**
 * Modal showing historical trades with similar patterns
 */
export function SimilarPatternsModal({ patternType, isOpen, onClose, symbol }: SimilarPatternsModalProps) {
  const [similarTrades, setSimilarTrades] = useState<EnhancedTradeRecord[]>([]);
  const [stats, setStats] = useState<PatternStats | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    const fetchData = async () => {
      setLoading(true);
      try {
        const data = await fetchTradesByPattern(patternType, symbol, 20);
        setSimilarTrades(data.trades);
        setStats(data.stats);
      } catch (error) {
        console.error('Error fetching similar patterns:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [patternType, isOpen, symbol]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
      data-testid="similar-patterns-modal"
    >
      <div
        className="bg-card border border-border rounded-lg shadow-2xl w-full max-w-4xl max-h-[80vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border">
          <h2 className="text-2xl font-bold text-foreground">
            Similar Patterns: {formatPatternType(patternType)}
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-surface rounded-lg transition-colors"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(80vh-80px)]">
          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4" />
              <p className="text-secondary">Loading similar patterns...</p>
            </div>
          ) : (
            <>
              {/* Pattern statistics */}
              {stats && (
                <div className="stats-grid grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                  <StatCard
                    label="Win Rate"
                    value={`${stats.winRate.toFixed(1)}%`}
                    color={stats.winRate > 60 ? 'success' : 'warning'}
                  />
                  <StatCard
                    label="Avg Profit"
                    value={`$${stats.avgProfit.toFixed(2)}`}
                    color="info"
                  />
                  <StatCard
                    label="Avg Loss"
                    value={`$${Math.abs(stats.avgLoss).toFixed(2)}`}
                    color="danger"
                  />
                  <StatCard
                    label="Total Trades"
                    value={stats.totalTrades.toString()}
                    color="secondary"
                  />
                </div>
              )}

              {/* Historical trades */}
              {similarTrades.length > 0 ? (
                <div className="historical-trades">
                  <h3 className="font-semibold mb-3 text-foreground">
                    Historical Trades ({similarTrades.length})
                  </h3>
                  <div className="space-y-3">
                    {similarTrades.map(trade => (
                      <HistoricalTradeCard key={trade.id} trade={trade} compact />
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-center py-12">
                  <p className="text-secondary">No historical trades found with this pattern</p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Stat card component
 */
interface StatCardProps {
  label: string;
  value: string;
  color: 'success' | 'warning' | 'danger' | 'info' | 'secondary';
}

function StatCard({ label, value, color }: StatCardProps) {
  const colorClasses = {
    success: 'bg-green-100 dark:bg-green-900/30 border-green-300 dark:border-green-700 text-green-800 dark:text-green-300',
    warning: 'bg-yellow-100 dark:bg-yellow-900/30 border-yellow-300 dark:border-yellow-700 text-yellow-800 dark:text-yellow-300',
    danger: 'bg-red-100 dark:bg-red-900/30 border-red-300 dark:border-red-700 text-red-800 dark:text-red-300',
    info: 'bg-blue-100 dark:bg-blue-900/30 border-blue-300 dark:border-blue-700 text-blue-800 dark:text-blue-300',
    secondary: 'bg-gray-100 dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-800 dark:text-gray-300'
  };

  return (
    <div className={`p-4 rounded-lg border ${colorClasses[color]}`} data-testid={`stat-card-${label.toLowerCase().replace(' ', '-')}`}>
      <div className="text-sm font-medium mb-1">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
}
