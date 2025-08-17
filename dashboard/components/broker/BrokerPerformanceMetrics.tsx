// Broker performance metrics display component

import React, { useState, useEffect } from 'react';
import { BrokerAccount, BrokerPerformanceMetrics } from '../../types/broker';
import { Card } from '../ui/Card';

interface BrokerPerformanceMetricsProps {
  account: BrokerAccount;
  className?: string;
}

interface PerformanceData {
  metrics: BrokerPerformanceMetrics;
  loading: boolean;
  error: string | null;
}

export const BrokerPerformanceMetricsComponent: React.FC<BrokerPerformanceMetricsProps> = ({
  account,
  className = ''
}) => {
  const [performanceData, setPerformanceData] = useState<PerformanceData>({
    metrics: {
      avg_latency_ms: 0,
      fill_quality_score: 100,
      uptime_percentage: 100,
      total_trades: 0,
      successful_trades: 0,
      failed_trades: 0,
      avg_slippage_pips: 0,
      connection_stability: 100
    },
    loading: true,
    error: null
  });

  useEffect(() => {
    const fetchPerformanceMetrics = async () => {
      try {
        setPerformanceData(prev => ({ ...prev, loading: true, error: null }));
        
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/brokers/${account.id}/performance`);
        
        if (!response.ok) {
          throw new Error('Failed to fetch performance metrics');
        }
        
        const metrics = await response.json();
        
        setPerformanceData({
          metrics,
          loading: false,
          error: null
        });
      } catch (error) {
        setPerformanceData(prev => ({
          ...prev,
          loading: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        }));
      }
    };

    fetchPerformanceMetrics();
    
    // Refresh metrics every 30 seconds
    const interval = setInterval(fetchPerformanceMetrics, 30000);
    
    return () => clearInterval(interval);
  }, [account.id]);

  const getLatencyColor = (latency: number) => {
    if (latency < 50) return 'text-green-600 dark:text-green-400';
    if (latency < 100) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getLatencyBadge = (latency: number) => {
    if (latency < 50) return { label: 'Excellent', color: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400' };
    if (latency < 100) return { label: 'Good', color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400' };
    return { label: 'Slow', color: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400' };
  };

  const getScoreColor = (score: number) => {
    if (score >= 95) return 'text-green-600 dark:text-green-400';
    if (score >= 85) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getCapabilityIcon = (capability: string) => {
    const icons: Record<string, string> = {
      'market_orders': '🎯',
      'limit_orders': '📋',
      'stop_orders': '🛑',
      'trailing_stops': '📈',
      'guaranteed_stops': '🛡️',
      'fractional_units': '⚖️',
      'hedging': '🔄',
      'fifo_only': '📊'
    };
    return icons[capability] || '⚡';
  };

  const getCapabilityLabel = (capability: string) => {
    return capability.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  if (performanceData.loading) {
    return (
      <Card className={`p-6 ${className}`}>
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
          <div className="space-y-3">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="flex justify-between">
                <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
                <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/4"></div>
              </div>
            ))}
          </div>
        </div>
      </Card>
    );
  }

  if (performanceData.error) {
    return (
      <Card className={`p-6 ${className}`}>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Performance Metrics
        </h3>
        <div className="text-center py-4">
          <p className="text-red-600 dark:text-red-400 text-sm">{performanceData.error}</p>
        </div>
      </Card>
    );
  }

  const { metrics } = performanceData;
  const successRate = metrics.total_trades > 0 ? (metrics.successful_trades / metrics.total_trades) * 100 : 100;
  const latencyBadge = getLatencyBadge(metrics.avg_latency_ms);

  return (
    <Card className={`p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Performance Metrics
        </h3>
        <div className="text-xs text-gray-500 dark:text-gray-400">
          Live Data
        </div>
      </div>

      {/* Key Performance Indicators */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {/* Latency */}
        <div className="text-center">
          <div className={`text-2xl font-bold ${getLatencyColor(metrics.avg_latency_ms)}`}>
            {metrics.avg_latency_ms.toFixed(0)}ms
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">Latency</div>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${latencyBadge.color}`}>
            {latencyBadge.label}
          </span>
        </div>

        {/* Fill Quality */}
        <div className="text-center">
          <div className={`text-2xl font-bold ${getScoreColor(metrics.fill_quality_score)}`}>
            {metrics.fill_quality_score.toFixed(1)}%
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">Fill Quality</div>
        </div>

        {/* Uptime */}
        <div className="text-center">
          <div className={`text-2xl font-bold ${getScoreColor(metrics.uptime_percentage)}`}>
            {metrics.uptime_percentage.toFixed(1)}%
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">Uptime</div>
        </div>

        {/* Connection Stability */}
        <div className="text-center">
          <div className={`text-2xl font-bold ${getScoreColor(metrics.connection_stability)}`}>
            {metrics.connection_stability.toFixed(1)}%
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">Stability</div>
        </div>
      </div>

      {/* Detailed Metrics */}
      <div className="space-y-4 mb-6">
        {/* Trade Statistics */}
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 dark:text-white mb-3">Trade Statistics</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-gray-500 dark:text-gray-400">Total Trades</p>
              <p className="font-semibold text-gray-900 dark:text-white">{metrics.total_trades.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-gray-500 dark:text-gray-400">Successful</p>
              <p className="font-semibold text-green-600 dark:text-green-400">{metrics.successful_trades.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-gray-500 dark:text-gray-400">Failed</p>
              <p className="font-semibold text-red-600 dark:text-red-400">{metrics.failed_trades.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-gray-500 dark:text-gray-400">Success Rate</p>
              <p className={`font-semibold ${getScoreColor(successRate)}`}>{successRate.toFixed(1)}%</p>
            </div>
          </div>
        </div>

        {/* Execution Quality */}
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 dark:text-white mb-3">Execution Quality</h4>
          <div className="space-y-3">
            {/* Average Slippage */}
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600 dark:text-gray-400">Average Slippage</span>
              <span className={`font-medium ${metrics.avg_slippage_pips > 1 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                {metrics.avg_slippage_pips.toFixed(2)} pips
              </span>
            </div>
            
            {/* Fill Quality Progress Bar */}
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-600 dark:text-gray-400">Fill Quality Score</span>
                <span className="font-medium text-gray-900 dark:text-white">{metrics.fill_quality_score.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all duration-300 ${
                    metrics.fill_quality_score >= 95 ? 'bg-green-500' :
                    metrics.fill_quality_score >= 85 ? 'bg-yellow-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${metrics.fill_quality_score}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Broker Capabilities */}
      <div className="border-t border-gray-200 dark:border-gray-600 pt-4">
        <h4 className="font-medium text-gray-900 dark:text-white mb-3">Supported Features</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {account.capabilities.map((capability) => (
            <div key={capability} className="flex items-center space-x-2 text-sm">
              <span className="text-lg">{getCapabilityIcon(capability)}</span>
              <span className="text-gray-600 dark:text-gray-400 truncate">
                {getCapabilityLabel(capability)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Performance Indicators */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600">
        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
          <span>Performance Score</span>
          <span>
            {((metrics.fill_quality_score + metrics.uptime_percentage + metrics.connection_stability) / 3).toFixed(0)}/100
          </span>
        </div>
      </div>
    </Card>
  );
};