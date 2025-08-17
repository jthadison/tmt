// Broker account overview card component

import React from 'react';
import { BrokerAccount, ConnectionStatus } from '../../types/broker';
import { Card } from '../ui/Card';
import { ConnectionStatus as ConnectionStatusComponent } from '../ui/ConnectionStatus';

interface BrokerOverviewCardProps {
  account: BrokerAccount;
  onReconnect: (accountId: string) => void;
  onDisconnect: (accountId: string) => void;
  onRemove: (accountId: string) => void;
  className?: string;
}

export const BrokerOverviewCard: React.FC<BrokerOverviewCardProps> = ({
  account,
  onReconnect,
  onDisconnect,
  onRemove,
  className = ''
}) => {
  const formatCurrency = (amount: number, currency: string = account.currency) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
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

  const getConnectionStatusColor = (status: ConnectionStatus) => {
    switch (status) {
      case ConnectionStatus.CONNECTED:
        return 'bg-green-500';
      case ConnectionStatus.DISCONNECTED:
        return 'bg-gray-500';
      case ConnectionStatus.RECONNECTING:
        return 'bg-yellow-500';
      case ConnectionStatus.ERROR:
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const marginUtilization = account.margin_used / (account.margin_used + account.margin_available) * 100;
  const plPercentage = (account.unrealized_pl / account.balance) * 100;

  return (
    <Card className={`p-6 hover:shadow-lg transition-shadow duration-200 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          {account.logo_url && (
            <img 
              src={account.logo_url} 
              alt={account.broker_name}
              className="w-8 h-8 rounded"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          )}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {account.display_name}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {account.broker_name} • {account.account_type.toUpperCase()}
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <ConnectionStatusComponent status={account.connection_status} />
          <div className="flex space-x-1">
            {account.connection_status === ConnectionStatus.DISCONNECTED && (
              <button
                onClick={() => onReconnect(account.id)}
                className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                title="Reconnect"
              >
                Connect
              </button>
            )}
            {account.connection_status === ConnectionStatus.CONNECTED && (
              <button
                onClick={() => onDisconnect(account.id)}
                className="px-2 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
                title="Disconnect"
              >
                Disconnect
              </button>
            )}
            <button
              onClick={() => onRemove(account.id)}
              className="px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
              title="Remove Account"
            >
              Remove
            </button>
          </div>
        </div>
      </div>

      {/* Balance and Equity */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">Balance</p>
          <p className="text-xl font-bold text-gray-900 dark:text-white">
            {formatCurrency(account.balance)}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">Equity</p>
          <p className="text-xl font-bold text-gray-900 dark:text-white">
            {formatCurrency(account.equity)}
          </p>
        </div>
      </div>

      {/* P&L */}
      <div className="mb-4">
        <div className="flex justify-between items-center">
          <p className="text-sm text-gray-500 dark:text-gray-400">Unrealized P&L</p>
          <p className={`text-sm ${getPLColor(plPercentage)}`}>
            {formatPercentage(plPercentage)}
          </p>
        </div>
        <p className={`text-lg font-semibold ${getPLColor(account.unrealized_pl)}`}>
          {formatCurrency(account.unrealized_pl)}
        </p>
      </div>

      {/* Margin Usage */}
      <div className="mb-4">
        <div className="flex justify-between items-center mb-2">
          <p className="text-sm text-gray-500 dark:text-gray-400">Margin Used</p>
          <p className="text-sm text-gray-600 dark:text-gray-300">
            {marginUtilization.toFixed(1)}%
          </p>
        </div>
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
        <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
          <span>{formatCurrency(account.margin_used)}</span>
          <span>{formatCurrency(account.margin_available)} available</span>
        </div>
      </div>

      {/* Capabilities */}
      <div className="mb-4">
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Capabilities</p>
        <div className="flex flex-wrap gap-1">
          {account.capabilities.slice(0, 4).map((capability) => (
            <span
              key={capability}
              className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded"
            >
              {capability.replace('_', ' ').toLowerCase()}
            </span>
          ))}
          {account.capabilities.length > 4 && (
            <span className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded">
              +{account.capabilities.length - 4} more
            </span>
          )}
        </div>
      </div>

      {/* Last Update */}
      <div className="text-xs text-gray-400 dark:text-gray-500">
        Last updated: {new Date(account.last_update).toLocaleTimeString()}
      </div>
    </Card>
  );
};