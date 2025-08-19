// Aggregate overview component showing combined data across all brokers

import React from 'react';
import { AggregateData } from '../../types/broker';
import Card from '../ui/Card';

interface AggregateOverviewProps {
  data: AggregateData | null;
  className?: string;
}

export const AggregateOverview: React.FC<AggregateOverviewProps> = ({
  data,
  className = ''
}) => {
  if (!data) {
    return (
      <Card className={`p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="space-y-2">
                <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
              </div>
            ))}
          </div>
        </div>
      </Card>
    );
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const formatPercentage = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const getPLColor = (value: number) => {
    if (value > 0) return 'text-green-600 dark:text-green-400';
    if (value < 0) return 'text-red-600 dark:text-red-400';
    return 'text-gray-600 dark:text-gray-400';
  };

  const totalPLPercentage = data.total_balance > 0 ? (data.total_unrealized_pl / data.total_balance) * 100 : 0;
  const marginUtilization = data.total_margin_used + data.total_margin_available > 0 
    ? (data.total_margin_used / (data.total_margin_used + data.total_margin_available)) * 100 
    : 0;

  return (
    <Card className={`p-6 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-gray-800 dark:to-gray-700 border-2 border-blue-200 dark:border-blue-700 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Portfolio Overview
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            {data.account_count} accounts • {data.connected_count} connected
          </p>
        </div>
        <div className="text-right">
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${data.connected_count === data.account_count ? 'bg-green-500' : 'bg-yellow-500'}`}></div>
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {data.connected_count === data.account_count ? 'All Connected' : 'Partial Connection'}
            </span>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Last updated: {new Date(data.last_update).toLocaleTimeString()}
          </p>
        </div>
      </div>

      {/* Main Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6 mb-6">
        {/* Total Balance */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">Total Balance</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">
            {formatCurrency(data.total_balance)}
          </p>
        </div>

        {/* Total Equity */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">Total Equity</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">
            {formatCurrency(data.total_equity)}
          </p>
        </div>

        {/* Unrealized P&L */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
          <div className="flex justify-between items-center mb-1">
            <p className="text-sm text-gray-500 dark:text-gray-400">Unrealized P&L</p>
            <span className={`text-sm ${getPLColor(totalPLPercentage)}`}>
              {formatPercentage(totalPLPercentage)}
            </span>
          </div>
          <p className={`text-2xl font-bold ${getPLColor(data.total_unrealized_pl)}`}>
            {formatCurrency(data.total_unrealized_pl)}
          </p>
        </div>

        {/* Margin Usage */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
          <div className="flex justify-between items-center mb-1">
            <p className="text-sm text-gray-500 dark:text-gray-400">Margin Used</p>
            <span className="text-sm text-gray-600 dark:text-gray-300">
              {marginUtilization.toFixed(1)}%
            </span>
          </div>
          <p className="text-lg font-bold text-gray-900 dark:text-white mb-2">
            {formatCurrency(data.total_margin_used)}
          </p>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${
                marginUtilization > 80 
                  ? 'bg-red-500' 
                  : marginUtilization > 60 
                  ? 'bg-yellow-500' 
                  : 'bg-green-500'
              }`}
              style={{ width: `${Math.min(marginUtilization, 100)}%` }}
            />
          </div>
        </div>
      </div>

      {/* P&L Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Daily P&L */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">Daily P&L</p>
          <p className={`text-xl font-bold ${getPLColor(data.daily_pl)}`}>
            {formatCurrency(data.daily_pl)}
          </p>
        </div>

        {/* Weekly P&L */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">Weekly P&L</p>
          <p className={`text-xl font-bold ${getPLColor(data.weekly_pl)}`}>
            {formatCurrency(data.weekly_pl)}
          </p>
        </div>

        {/* Monthly P&L */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">Monthly P&L</p>
          <p className={`text-xl font-bold ${getPLColor(data.monthly_pl)}`}>
            {formatCurrency(data.monthly_pl)}
          </p>
        </div>
      </div>

      {/* Performance Indicators */}
      {(data.best_performer || data.worst_performer) && (
        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-600">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.best_performer && (
              <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3">
                <p className="text-sm text-green-600 dark:text-green-400 font-medium">
                  🏆 Best Performer
                </p>
                <p className="text-green-800 dark:text-green-300 font-semibold">
                  {data.best_performer}
                </p>
              </div>
            )}
            {data.worst_performer && (
              <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3">
                <p className="text-sm text-red-600 dark:text-red-400 font-medium">
                  📉 Needs Attention
                </p>
                <p className="text-red-800 dark:text-red-300 font-semibold">
                  {data.worst_performer}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </Card>
  );
};