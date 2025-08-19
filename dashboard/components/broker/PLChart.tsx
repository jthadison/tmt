// Combined P&L chart component with broker breakdown

import React, { useMemo } from 'react';
import { BrokerAccount } from '../../types/broker';
import Card from '../ui/Card';

interface PLChartProps {
  brokerAccounts: BrokerAccount[];
  className?: string;
}

export const PLChart: React.FC<PLChartProps> = ({
  brokerAccounts,
  className = ''
}) => {
  const plData = useMemo(() => {
    if (!brokerAccounts.length) return [];

    return brokerAccounts.map(account => ({
      broker_id: account.id,
      broker_name: account.display_name,
      unrealized_pl: account.unrealized_pl,
      realized_pl: account.realized_pl,
      total_pl: account.unrealized_pl + account.realized_pl,
      percentage: account.balance > 0 ? ((account.unrealized_pl + account.realized_pl) / account.balance) * 100 : 0
    })).sort((a, b) => b.total_pl - a.total_pl);
  }, [brokerAccounts]);

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

  const getPLBgColor = (value: number) => {
    if (value > 0) return 'bg-green-500';
    if (value < 0) return 'bg-red-500';
    return 'bg-gray-500';
  };

  const totalPL = plData.reduce((sum, item) => sum + item.total_pl, 0);
  const maxAbsPL = Math.max(...plData.map(item => Math.abs(item.total_pl)));

  if (!plData.length) {
    return (
      <Card className={`p-6 ${className}`}>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          P&L Breakdown
        </h3>
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          No broker accounts available
        </div>
      </Card>
    );
  }

  return (
    <Card className={`p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          P&L Breakdown
        </h3>
        <div className="text-right">
          <p className={`text-xl font-bold ${getPLColor(totalPL)}`}>
            {formatCurrency(totalPL)}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">Total P&L</p>
        </div>
      </div>

      {/* Chart */}
      <div className="space-y-4">
        {plData.map((item) => {
          const barWidth = maxAbsPL > 0 ? (Math.abs(item.total_pl) / maxAbsPL) * 100 : 0;
          
          return (
            <div key={item.broker_id} className="space-y-2">
              {/* Broker Name and Values */}
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <p className="font-medium text-gray-900 dark:text-white">
                    {item.broker_name}
                  </p>
                  <div className="flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-400">
                    <span>Unrealized: {formatCurrency(item.unrealized_pl)}</span>
                    <span>Realized: {formatCurrency(item.realized_pl)}</span>
                  </div>
                </div>
                <div className="text-right">
                  <p className={`font-bold ${getPLColor(item.total_pl)}`}>
                    {formatCurrency(item.total_pl)}
                  </p>
                  <p className={`text-sm ${getPLColor(item.percentage)}`}>
                    {formatPercentage(item.percentage)}
                  </p>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="relative">
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full transition-all duration-500 ${getPLBgColor(item.total_pl)}`}
                    style={{ width: `${barWidth}%` }}
                  />
                </div>
                {/* Center line for zero */}
                <div className="absolute top-0 left-1/2 w-px h-3 bg-gray-400 dark:bg-gray-500 transform -translate-x-1/2" />
              </div>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-600">
        <div className="flex items-center justify-center space-x-6 text-sm">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-green-500 rounded"></div>
            <span className="text-gray-600 dark:text-gray-400">Profitable</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-red-500 rounded"></div>
            <span className="text-gray-600 dark:text-gray-400">Loss</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-gray-500 rounded"></div>
            <span className="text-gray-600 dark:text-gray-400">Breakeven</span>
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="mt-6 grid grid-cols-3 gap-4 pt-4 border-t border-gray-200 dark:border-gray-600">
        <div className="text-center">
          <p className="text-2xl font-bold text-green-600 dark:text-green-400">
            {plData.filter(item => item.total_pl > 0).length}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">Profitable</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-red-600 dark:text-red-400">
            {plData.filter(item => item.total_pl < 0).length}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">In Loss</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-gray-600 dark:text-gray-400">
            {plData.filter(item => item.total_pl === 0).length}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">Breakeven</p>
        </div>
      </div>
    </Card>
  );
};