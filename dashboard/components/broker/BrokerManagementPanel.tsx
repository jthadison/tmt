// Broker management panel with add/remove/configure functionality

import React, { useState } from 'react';
import Image from 'next/image';
import { BrokerAccount, BrokerConfig } from '../../types/broker';
import Card from '../ui/Card';

interface BrokerManagementPanelProps {
  brokerAccounts: BrokerAccount[];
  onAddBroker: (config: BrokerConfig) => Promise<void>;
  onRemoveBroker: (accountId: string) => Promise<void>;
  onReconnectBroker: (accountId: string) => Promise<void>;
  className?: string;
}

interface AddBrokerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (config: BrokerConfig) => Promise<void>;
}

const AddBrokerModal: React.FC<AddBrokerModalProps> = ({ isOpen, onClose, onSubmit }) => {
  const [config, setConfig] = useState<Partial<BrokerConfig>>({
    broker_name: 'oanda',
    account_type: 'demo',
    display_name: '',
    credentials: {}
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!config.display_name || !config.broker_name) {
      setError('Display name and broker are required');
      return;
    }

    if (config.broker_name === 'oanda' && (!config.credentials?.api_key || !config.credentials?.account_id)) {
      setError('OANDA API key and account ID are required');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await onSubmit(config as BrokerConfig);
      onClose();
      setConfig({
        broker_name: 'oanda',
        account_type: 'demo',
        display_name: '',
        credentials: {}
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add broker');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md mx-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Add Broker Account
        </h3>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Display Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Display Name
            </label>
            <input
              type="text"
              value={config.display_name || ''}
              onChange={(e) => setConfig(prev => ({ ...prev, display_name: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              placeholder="My OANDA Account"
              required
            />
          </div>

          {/* Broker Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Broker
            </label>
            <select
              value={config.broker_name || 'oanda'}
              onChange={(e) => setConfig(prev => ({ ...prev, broker_name: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="oanda">OANDA</option>
              <option value="interactive_brokers" disabled>Interactive Brokers (Coming Soon)</option>
              <option value="alpaca" disabled>Alpaca (Coming Soon)</option>
            </select>
          </div>

          {/* Account Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Account Type
            </label>
            <select
              value={config.account_type || 'demo'}
              onChange={(e) => setConfig(prev => ({ ...prev, account_type: e.target.value as 'live' | 'demo' }))}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="demo">Demo</option>
              <option value="live">Live</option>
            </select>
          </div>

          {/* OANDA Specific Fields */}
          {config.broker_name === 'oanda' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  API Key
                </label>
                <input
                  type="password"
                  value={config.credentials?.api_key || ''}
                  onChange={(e) => setConfig(prev => ({ 
                    ...prev, 
                    credentials: { ...prev.credentials, api_key: e.target.value }
                  }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="Your OANDA API key"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Account ID
                </label>
                <input
                  type="text"
                  value={config.credentials?.account_id || ''}
                  onChange={(e) => setConfig(prev => ({ 
                    ...prev, 
                    credentials: { ...prev.credentials, account_id: e.target.value }
                  }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="Your OANDA account ID"
                  required
                />
              </div>
            </>
          )}

          {/* Error Message */}
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
              <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isSubmitting ? 'Adding...' : 'Add Broker'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export const BrokerManagementPanel: React.FC<BrokerManagementPanelProps> = ({
  brokerAccounts,
  onAddBroker,
  onRemoveBroker,
  onReconnectBroker,
  className = ''
}) => {
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const handleRemoveBroker = async (accountId: string) => {
    if (confirmRemove !== accountId) {
      setConfirmRemove(accountId);
      setTimeout(() => setConfirmRemove(null), 5000); // Auto-cancel after 5 seconds
      return;
    }

    setActionLoading(accountId);
    try {
      await onRemoveBroker(accountId);
      setConfirmRemove(null);
    } catch (error) {
      console.error('Failed to remove broker:', error);
    } finally {
      setActionLoading(null);
    }
  };

  const handleReconnectBroker = async (accountId: string) => {
    setActionLoading(accountId);
    try {
      await onReconnectBroker(accountId);
    } catch (error) {
      console.error('Failed to reconnect broker:', error);
    } finally {
      setActionLoading(null);
    }
  };

  const getStatusBadge = (account: BrokerAccount) => {
    const statusConfig = {
      connected: { bg: 'bg-green-100 dark:bg-green-900/20', text: 'text-green-800 dark:text-green-400', label: 'Connected' },
      disconnected: { bg: 'bg-gray-100 dark:bg-gray-900/20', text: 'text-gray-800 dark:text-gray-400', label: 'Disconnected' },
      reconnecting: { bg: 'bg-yellow-100 dark:bg-yellow-900/20', text: 'text-yellow-800 dark:text-yellow-400', label: 'Reconnecting' },
      error: { bg: 'bg-red-100 dark:bg-red-900/20', text: 'text-red-800 dark:text-red-400', label: 'Error' }
    };

    const config = statusConfig[account.connection_status] || statusConfig.disconnected;

    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
        {config.label}
      </span>
    );
  };

  return (
    <Card className={`p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Broker Management
        </h3>
        <button
          onClick={() => setIsAddModalOpen(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          Add Broker
        </button>
      </div>

      {/* Broker List */}
      <div className="space-y-4">
        {brokerAccounts.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            <p className="mb-2">No broker accounts configured</p>
            <button
              onClick={() => setIsAddModalOpen(true)}
              className="text-blue-600 dark:text-blue-400 hover:underline"
            >
              Add your first broker account
            </button>
          </div>
        ) : (
          brokerAccounts.map((account) => (
            <div key={account.id} className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              {/* Account Info */}
              <div className="flex items-center space-x-4">
                {account.logo_url && (
                  <Image 
                    src={account.logo_url} 
                    alt={account.broker_name}
                    width={40}
                    height={40}
                    className="rounded"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                  />
                )}
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white">
                    {account.display_name}
                  </h4>
                  <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
                    <span>{account.broker_name}</span>
                    <span>•</span>
                    <span className="uppercase">{account.account_type}</span>
                    <span>•</span>
                    {getStatusBadge(account)}
                  </div>
                </div>
              </div>

              {/* Account Metrics */}
              <div className="text-right mr-4">
                <p className="font-medium text-gray-900 dark:text-white">
                  {new Intl.NumberFormat('en-US', { style: 'currency', currency: account.currency }).format(account.balance)}
                </p>
                <p className={`text-sm ${account.unrealized_pl >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                  {account.unrealized_pl >= 0 ? '+' : ''}{new Intl.NumberFormat('en-US', { style: 'currency', currency: account.currency }).format(account.unrealized_pl)}
                </p>
              </div>

              {/* Actions */}
              <div className="flex items-center space-x-2">
                {account.connection_status === 'disconnected' && (
                  <button
                    onClick={() => handleReconnectBroker(account.id)}
                    disabled={actionLoading === account.id}
                    className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 transition-colors"
                  >
                    {actionLoading === account.id ? 'Connecting...' : 'Connect'}
                  </button>
                )}
                
                <button
                  onClick={() => handleRemoveBroker(account.id)}
                  disabled={actionLoading === account.id}
                  className={`px-3 py-1 text-sm rounded transition-colors ${
                    confirmRemove === account.id
                      ? 'bg-red-600 text-white hover:bg-red-700'
                      : 'bg-gray-600 text-white hover:bg-gray-700'
                  }`}
                >
                  {actionLoading === account.id 
                    ? 'Removing...'
                    : confirmRemove === account.id 
                    ? 'Confirm Remove' 
                    : 'Remove'
                  }
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Quick Actions */}
      <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-600">
        <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
          Quick Actions
        </h4>
        <div className="flex space-x-2">
          <button
            onClick={() => {
              brokerAccounts.forEach(account => {
                if (account.connection_status === 'disconnected') {
                  handleReconnectBroker(account.id);
                }
              });
            }}
            className="px-3 py-2 text-sm bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
          >
            Reconnect All
          </button>
          <button
            onClick={() => setIsAddModalOpen(true)}
            className="px-3 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            Add Account
          </button>
        </div>
      </div>

      {/* Add Broker Modal */}
      <AddBrokerModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onSubmit={onAddBroker}
      />
    </Card>
  );
};