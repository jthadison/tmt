// Connection status monitoring component with health indicators

import React, { useState } from 'react';
import { BrokerAccount, ConnectionStatus } from '../../types/broker';
import { Card } from '../ui/Card';

interface ConnectionMonitorProps {
  brokerAccounts: BrokerAccount[];
  onReconnect: (accountId: string) => void;
  className?: string;
}

export const ConnectionMonitor: React.FC<ConnectionMonitorProps> = ({
  brokerAccounts,
  onReconnect,
  className = ''
}) => {
  const [reconnectingAccounts, setReconnectingAccounts] = useState<Set<string>>(new Set());

  const getStatusColor = (status: ConnectionStatus) => {
    switch (status) {
      case ConnectionStatus.CONNECTED:
        return 'text-green-600 dark:text-green-400';
      case ConnectionStatus.DISCONNECTED:
        return 'text-gray-600 dark:text-gray-400';
      case ConnectionStatus.RECONNECTING:
        return 'text-yellow-600 dark:text-yellow-400';
      case ConnectionStatus.ERROR:
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getStatusBgColor = (status: ConnectionStatus) => {
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

  const getStatusIcon = (status: ConnectionStatus) => {
    switch (status) {
      case ConnectionStatus.CONNECTED:
        return '🟢';
      case ConnectionStatus.DISCONNECTED:
        return '⚫';
      case ConnectionStatus.RECONNECTING:
        return '🟡';
      case ConnectionStatus.ERROR:
        return '🔴';
      default:
        return '⚫';
    }
  };

  const getStatusLabel = (status: ConnectionStatus) => {
    switch (status) {
      case ConnectionStatus.CONNECTED:
        return 'Connected';
      case ConnectionStatus.DISCONNECTED:
        return 'Disconnected';
      case ConnectionStatus.RECONNECTING:
        return 'Reconnecting...';
      case ConnectionStatus.ERROR:
        return 'Error';
      default:
        return 'Unknown';
    }
  };

  const getConnectionQuality = (account: BrokerAccount) => {
    const lastUpdate = new Date(account.last_update);
    const now = new Date();
    const timeDiff = now.getTime() - lastUpdate.getTime();
    const minutesDiff = Math.floor(timeDiff / (1000 * 60));

    if (account.connection_status !== ConnectionStatus.CONNECTED) {
      return { quality: 'poor', label: 'Offline', color: 'text-red-600' };
    }

    if (minutesDiff < 1) {
      return { quality: 'excellent', label: 'Real-time', color: 'text-green-600' };
    } else if (minutesDiff < 5) {
      return { quality: 'good', label: 'Recent', color: 'text-green-500' };
    } else if (minutesDiff < 15) {
      return { quality: 'fair', label: 'Delayed', color: 'text-yellow-600' };
    } else {
      return { quality: 'poor', label: 'Stale', color: 'text-red-600' };
    }
  };

  const handleReconnect = async (accountId: string) => {
    setReconnectingAccounts(prev => new Set(prev).add(accountId));
    
    try {
      await onReconnect(accountId);
    } finally {
      setTimeout(() => {
        setReconnectingAccounts(prev => {
          const next = new Set(prev);
          next.delete(accountId);
          return next;
        });
      }, 2000);
    }
  };

  const connectedCount = brokerAccounts.filter(acc => acc.connection_status === ConnectionStatus.CONNECTED).length;
  const totalCount = brokerAccounts.length;
  const connectionPercentage = totalCount > 0 ? (connectedCount / totalCount) * 100 : 0;

  return (
    <Card className={`p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Connection Monitor
        </h3>
        <div className="text-right">
          <p className="text-lg font-bold text-gray-900 dark:text-white">
            {connectedCount}/{totalCount}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">Connected</p>
        </div>
      </div>

      {/* Overall Status */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-600 dark:text-gray-400">Overall Health</span>
          <span className="text-sm font-medium text-gray-900 dark:text-white">
            {connectionPercentage.toFixed(0)}%
          </span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
          <div
            className={`h-3 rounded-full transition-all duration-500 ${
              connectionPercentage === 100 
                ? 'bg-green-500' 
                : connectionPercentage >= 75 
                ? 'bg-yellow-500' 
                : 'bg-red-500'
            }`}
            style={{ width: `${connectionPercentage}%` }}
          />
        </div>
      </div>

      {/* Individual Broker Status */}
      <div className="space-y-4">
        {brokerAccounts.map((account) => {
          const quality = getConnectionQuality(account);
          const isReconnecting = reconnectingAccounts.has(account.id);
          
          return (
            <div key={account.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
              {/* Broker Info */}
              <div className="flex items-center space-x-3">
                <div className={`w-3 h-3 rounded-full ${getStatusBgColor(account.connection_status)} ${
                  account.connection_status === ConnectionStatus.RECONNECTING ? 'animate-pulse' : ''
                }`} />
                
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {account.display_name}
                  </p>
                  <div className="flex items-center space-x-2 text-sm">
                    <span className={getStatusColor(account.connection_status)}>
                      {getStatusLabel(account.connection_status)}
                    </span>
                    <span className="text-gray-400">•</span>
                    <span className={quality.color}>
                      {quality.label}
                    </span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center space-x-2">
                {/* Last Update Time */}
                <div className="text-right text-xs text-gray-500 dark:text-gray-400 mr-2">
                  {new Date(account.last_update).toLocaleTimeString()}
                </div>

                {/* Reconnect Button */}
                {account.connection_status !== ConnectionStatus.CONNECTED && (
                  <button
                    onClick={() => handleReconnect(account.id)}
                    disabled={isReconnecting || account.connection_status === ConnectionStatus.RECONNECTING}
                    className={`px-3 py-1 text-xs rounded transition-colors ${
                      isReconnecting || account.connection_status === ConnectionStatus.RECONNECTING
                        ? 'bg-gray-400 text-white cursor-not-allowed'
                        : 'bg-blue-600 text-white hover:bg-blue-700'
                    }`}
                  >
                    {isReconnecting || account.connection_status === ConnectionStatus.RECONNECTING
                      ? 'Reconnecting...'
                      : 'Reconnect'
                    }
                  </button>
                )}

                {/* Health Indicator */}
                <div className="flex flex-col items-center">
                  <div className={`w-2 h-2 rounded-full ${
                    quality.quality === 'excellent' ? 'bg-green-500' :
                    quality.quality === 'good' ? 'bg-green-400' :
                    quality.quality === 'fair' ? 'bg-yellow-500' :
                    'bg-red-500'
                  }`} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Connection Timeline (simplified) */}
      <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-600">
        <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
          Connection History
        </h4>
        <div className="space-y-2">
          {brokerAccounts.slice(0, 3).map((account) => {
            const timeSinceUpdate = Math.floor((new Date().getTime() - new Date(account.last_update).getTime()) / 60000);
            
            return (
              <div key={account.id} className="flex items-center justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">
                  {account.display_name}
                </span>
                <span className="text-gray-500 dark:text-gray-500">
                  {timeSinceUpdate < 1 ? 'Just now' : `${timeSinceUpdate}m ago`}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </Card>
  );
};