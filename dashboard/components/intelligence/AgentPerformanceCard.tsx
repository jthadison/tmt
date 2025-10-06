/**
 * Agent Performance Card Component
 * Displays individual agent performance metrics with expandable details
 * Story 7.3: AC3 - Agent Performance Card with Details
 */

'use client';

import React, { useState } from 'react';
import { AgentPerformanceData } from '@/types/intelligence';
import { AgentIcon } from './AgentIcon';
import { Sparkline, generateSparklineData } from './Sparkline';

interface AgentPerformanceCardProps {
  agent: AgentPerformanceData;
  rank: number;
  showMedal: boolean;
}

export function AgentPerformanceCard({ agent, rank, showMedal }: AgentPerformanceCardProps) {
  const [expanded, setExpanded] = useState(false);

  const getWinRateColor = (winRate: number) => {
    if (winRate >= 70) return 'text-green-600 bg-green-500/10 dark:text-green-400 dark:bg-green-500/20';
    if (winRate >= 60) return 'text-yellow-600 bg-yellow-500/10 dark:text-yellow-400 dark:bg-yellow-500/20';
    return 'text-red-600 bg-red-500/10 dark:text-red-400 dark:bg-red-500/20';
  };

  const getMedalEmoji = (rank: number) => {
    if (rank === 1) return '🥇';
    if (rank === 2) return '🥈';
    if (rank === 3) return '🥉';
    return null;
  };

  const sparklineData = generateSparklineData(agent.metrics.winRate);

  return (
    <div
      className="agent-performance-card bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-lg transition-shadow"
      data-testid="agent-performance-card"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <AgentIcon agentId={agent.agentId} size="md" />
          <div>
            <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100">
              {agent.agentName}
            </h3>
            <div className="text-xs text-gray-500 dark:text-gray-400">Rank #{rank}</div>
          </div>
        </div>
        {showMedal && (
          <div className="text-2xl" data-testid="medal-icon">
            {getMedalEmoji(rank)}
          </div>
        )}
      </div>

      {/* Win Rate */}
      <div className="mb-3">
        <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Win Rate</div>
        <div className={`inline-flex items-center gap-2 px-2 py-1 rounded ${getWinRateColor(agent.metrics.winRate)}`}>
          <span className="text-lg font-bold">{agent.metrics.winRate.toFixed(1)}%</span>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div>
          <div className="text-xs text-gray-500 dark:text-gray-400">Avg Profit</div>
          <div className="text-sm font-semibold text-green-600 dark:text-green-400">
            ${agent.metrics.avgProfit.toFixed(2)}
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500 dark:text-gray-400">Signals</div>
          <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            {agent.metrics.totalSignals}
          </div>
        </div>
      </div>

      {/* Sparkline */}
      <div className="mb-3">
        <Sparkline data={sparklineData} height={40} width={240} />
      </div>

      {/* Expand button */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-sm text-blue-600 dark:text-blue-400 hover:underline"
      >
        {expanded ? 'Hide Details' : 'View Details'}
      </button>

      {/* Expanded details */}
      {expanded && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          {/* Best pairs */}
          {agent.bestPairs.length > 0 && (
            <div className="mb-4">
              <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                Best Performing Pairs
              </h4>
              <div className="space-y-2">
                {agent.bestPairs.slice(0, 3).map((pair) => (
                  <div
                    key={pair.symbol}
                    className="flex items-center justify-between text-xs"
                  >
                    <span className="font-medium text-gray-900 dark:text-gray-100">
                      {pair.symbol}
                    </span>
                    <span className={getWinRateColor(pair.winRate)}>
                      {pair.winRate.toFixed(1)}% ({pair.totalTrades} trades)
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Session performance */}
          {agent.sessionPerformance && agent.sessionPerformance.length > 0 && (
            <div className="mb-4">
              <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                Session Performance
              </h4>
              <div className="space-y-2">
                {agent.sessionPerformance.map((session) => (
                  <div
                    key={session.session}
                    className="flex items-center justify-between text-xs"
                  >
                    <span className="text-gray-700 dark:text-gray-300">{session.session}</span>
                    <span className={getWinRateColor(session.winRate)}>
                      {session.winRate.toFixed(1)}% ({session.totalTrades} trades)
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Additional metrics */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <div className="text-gray-500 dark:text-gray-400">Profit Factor</div>
              <div className="font-semibold text-gray-900 dark:text-gray-100">
                {agent.metrics.profitFactor.toFixed(2)}
              </div>
            </div>
            <div>
              <div className="text-gray-500 dark:text-gray-400">Trades (30d)</div>
              <div className="font-semibold text-gray-900 dark:text-gray-100">
                {agent.recentActivity.last30Days}
              </div>
            </div>
            {agent.metrics.maxDrawdown !== undefined && (
              <>
                <div>
                  <div className="text-gray-500 dark:text-gray-400">Max Drawdown</div>
                  <div className="font-semibold text-red-600 dark:text-red-400">
                    ${Math.abs(agent.metrics.maxDrawdown).toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-gray-500 dark:text-gray-400">Total Trades</div>
                  <div className="font-semibold text-gray-900 dark:text-gray-100">
                    {agent.metrics.totalTrades}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
