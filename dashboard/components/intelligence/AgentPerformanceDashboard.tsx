/**
 * Agent Performance Dashboard Component
 * Displays performance comparison for all 8 agents
 * Story 7.3: AC2 - Agent Performance Comparison Dashboard
 */

'use client';

import React, { useState, useEffect } from 'react';
import { TrendingUp, Activity, DollarSign, Target } from 'lucide-react';
import {
  AgentPerformanceData,
  SystemMetrics,
  type PerformancePeriod
} from '@/types/intelligence';
import { AgentPerformanceCard } from './AgentPerformanceCard';

interface MetricCardProps {
  label: string;
  value: string | number;
  trend?: number;
  color: 'primary' | 'info' | 'success' | 'warning';
  icon: React.ReactNode;
}

function MetricCard({ label, value, trend, color, icon }: MetricCardProps) {
  const colorClasses = {
    primary: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
    info: 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400',
    success: 'bg-green-500/10 text-green-600 dark:text-green-400',
    warning: 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400'
  };

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-500 dark:text-gray-400">{label}</span>
        <div className={`p-2 rounded ${colorClasses[color]}`}>{icon}</div>
      </div>
      <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{value}</div>
      {trend !== undefined && (
        <div className={`text-xs mt-1 ${trend >= 0 ? 'text-green-600' : 'text-red-600'}`}>
          {trend >= 0 ? '↑' : '↓'} {Math.abs(trend).toFixed(1)}%
        </div>
      )}
    </div>
  );
}

interface TimePeriodSelectorProps {
  value: PerformancePeriod;
  onChange: (period: PerformancePeriod) => void;
}

function TimePeriodSelector({ value, onChange }: TimePeriodSelectorProps) {
  const periods: { value: PerformancePeriod; label: string }[] = [
    { value: '7d', label: '7 Days' },
    { value: '30d', label: '30 Days' },
    { value: '90d', label: '90 Days' },
    { value: 'all', label: 'All Time' }
  ];

  return (
    <div className="inline-flex rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800">
      {periods.map((period) => (
        <button
          key={period.value}
          onClick={() => onChange(period.value)}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            value === period.value
              ? 'bg-blue-600 text-white'
              : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
          } ${period.value === '7d' ? 'rounded-l-lg' : ''} ${
            period.value === 'all' ? 'rounded-r-lg' : ''
          }`}
        >
          {period.label}
        </button>
      ))}
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="grid grid-cols-4 gap-4 mb-8">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
        ))}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="h-64 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
        ))}
      </div>
    </div>
  );
}

function calculateSystemMetrics(agents: AgentPerformanceData[]): SystemMetrics {
  if (agents.length === 0) {
    return {
      winRate: 0,
      totalSignals: 0,
      avgProfit: 0,
      profitFactor: 0,
      winRateTrend: 0
    };
  }

  const totalTrades = agents.reduce((sum, a) => sum + a.metrics.totalTrades, 0);
  const totalSignals = agents.reduce((sum, a) => sum + a.metrics.totalSignals, 0);

  // Weighted average win rate by trade count
  const weightedWinRate = agents.reduce((sum, a) => {
    return sum + (a.metrics.winRate * a.metrics.totalTrades);
  }, 0) / (totalTrades || 1);

  // Calculate system-wide profit factor
  const totalProfits = agents.reduce((sum, a) => {
    const wins = a.metrics.totalTrades * (a.metrics.winRate / 100);
    return sum + (wins * a.metrics.avgProfit);
  }, 0);

  const totalLosses = agents.reduce((sum, a) => {
    const losses = a.metrics.totalTrades * ((100 - a.metrics.winRate) / 100);
    return sum + (losses * Math.abs(a.metrics.avgLoss));
  }, 0);

  const profitFactor = totalLosses > 0 ? totalProfits / totalLosses : 0;

  // Average profit per trade across all agents
  const avgProfit = totalTrades > 0 ? totalProfits / totalTrades : 0;

  return {
    winRate: Math.round(weightedWinRate * 10) / 10,
    totalSignals,
    avgProfit: Math.round(avgProfit * 100) / 100,
    profitFactor: Math.round(profitFactor * 100) / 100,
    winRateTrend: 0 // TODO: Calculate from historical data
  };
}

export function AgentPerformanceDashboard() {
  const [performanceData, setPerformanceData] = useState<AgentPerformanceData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timePeriod, setTimePeriod] = useState<PerformancePeriod>('30d');

  useEffect(() => {
    const fetchPerformance = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(`/api/agents/performance?period=${timePeriod}`);

        if (!response.ok) {
          throw new Error(`Failed to fetch performance data: ${response.statusText}`);
        }

        const data = await response.json();

        // Sort by win rate (should already be sorted, but ensure)
        const sorted = data.sort((a: AgentPerformanceData, b: AgentPerformanceData) =>
          b.metrics.winRate - a.metrics.winRate
        );

        setPerformanceData(sorted);
      } catch (error) {
        console.error('Failed to fetch agent performance:', error);
        setError('Failed to load performance data. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchPerformance();
  }, [timePeriod]);

  if (loading) return <LoadingSkeleton />;

  if (error) {
    return (
      <div className="p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
        <p className="text-red-800 dark:text-red-200">{error}</p>
      </div>
    );
  }

  const systemMetrics = calculateSystemMetrics(performanceData);

  return (
    <div className="agent-performance-dashboard p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Agent Performance
        </h2>
        <TimePeriodSelector value={timePeriod} onChange={setTimePeriod} />
      </div>

      {/* System-wide metrics */}
      <div className="system-metrics grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <MetricCard
          label="System Win Rate"
          value={`${systemMetrics.winRate.toFixed(1)}%`}
          trend={systemMetrics.winRateTrend}
          color="primary"
          icon={<TrendingUp className="w-5 h-5" />}
        />
        <MetricCard
          label="Total Signals"
          value={systemMetrics.totalSignals}
          color="info"
          icon={<Activity className="w-5 h-5" />}
        />
        <MetricCard
          label="Avg Profit/Trade"
          value={`$${systemMetrics.avgProfit.toFixed(2)}`}
          color="success"
          icon={<DollarSign className="w-5 h-5" />}
        />
        <MetricCard
          label="Profit Factor"
          value={systemMetrics.profitFactor.toFixed(2)}
          color="warning"
          icon={<Target className="w-5 h-5" />}
        />
      </div>

      {/* Individual agent performance */}
      <div className="agent-performance-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {performanceData.map((agent, index) => (
          <AgentPerformanceCard
            key={agent.agentId}
            agent={agent}
            rank={index + 1}
            showMedal={index < 3}
          />
        ))}
      </div>
    </div>
  );
}
