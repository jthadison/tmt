"use client";

import React, { useState } from 'react';
import { useBrokerData } from '../../hooks/useBrokerData';
import { AggregateOverview } from '../../components/broker/AggregateOverview';
import { BrokerOverviewCard } from '../../components/broker/BrokerOverviewCard';
import { PLChart } from '../../components/broker/PLChart';
import { ConnectionMonitor } from '../../components/broker/ConnectionMonitor';
import { BrokerManagementPanel } from '../../components/broker/BrokerManagementPanel';
import { LoadingSkeleton } from '../../components/ui/LoadingSkeleton';
import { ToastContainer } from '../../components/ui/Toast';
import ErrorBoundary from '../../components/ui/ErrorBoundary';

export default function BrokersPage() {
  const {
    brokerAccounts,
    aggregateData,
    connectionStatus,
    isLoading,
    error,
    reconnectBroker,
    addBrokerAccount,
    removeBrokerAccount,
    refreshData
  } = useBrokerData();

  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [view, setView] = useState<'overview' | 'management'>('overview');

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  };

  const handleReconnectBroker = async (accountId: string) => {
    try {
      await reconnectBroker(accountId);
      showToast('Broker reconnection initiated', 'success');
    } catch {
      showToast('Failed to reconnect broker', 'error');
    }
  };

  const handleDisconnectBroker = async () => {
    // For now, we'll just show a message since disconnect isn't implemented in the hook
    showToast('Disconnect functionality coming soon', 'info');
  };

  const handleRemoveBroker = async (accountId: string) => {
    try {
      await removeBrokerAccount(accountId);
      await refreshData(); // Refresh the broker list after removing
      showToast('Broker account removed successfully', 'success');
    } catch {
      showToast('Failed to remove broker account', 'error');
    }
  };

  const handleAddBroker = async (config: {
    broker_name: string;
    account_type: 'live' | 'demo';
    display_name: string;
    credentials: Record<string, string>;
  }) => {
    console.log('handleAddBroker called with config:', config);
    try {
      console.log('Calling addBrokerAccount...');
      await addBrokerAccount(config);
      console.log('addBrokerAccount completed, refreshing data...');
      await refreshData(); // Refresh the broker list after adding
      console.log('Data refresh completed');
      showToast('Broker account added successfully', 'success');
    } catch (error) {
      console.error('handleAddBroker error:', error);
      showToast('Failed to add broker account', 'error');
    }
  };

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <LoadingSkeleton className="h-8 w-64" />
        <LoadingSkeleton className="h-32 w-full" />
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {[1, 2, 3].map(i => (
            <LoadingSkeleton key={i} className="h-64 w-full" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between py-6">
              <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                  Broker Integration Dashboard
                </h1>
                <p className="text-gray-600 dark:text-gray-400 mt-1">
                  Manage and monitor all your broker accounts from one place
                </p>
              </div>
              
              <div className="flex items-center space-x-4">
                {/* Connection Status Indicator */}
                <div className="flex items-center space-x-2">
                  <div className={`w-3 h-3 rounded-full ${
                    connectionStatus === 'connected' ? 'bg-green-500' :
                    connectionStatus === 'connecting' ? 'bg-yellow-500 animate-pulse' :
                    connectionStatus === 'error' ? 'bg-red-500' :
                    'bg-gray-500'
                  }`} />
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {connectionStatus === 'connected' ? 'Live Updates' :
                     connectionStatus === 'connecting' ? 'Connecting...' :
                     connectionStatus === 'error' ? 'Connection Error' :
                     'Offline'}
                  </span>
                </div>

                {/* View Toggle */}
                <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
                  <button
                    onClick={() => setView('overview')}
                    className={`px-3 py-1 rounded text-sm transition-colors ${
                      view === 'overview'
                        ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm'
                        : 'text-gray-600 dark:text-gray-400'
                    }`}
                  >
                    Overview
                  </button>
                  <button
                    onClick={() => setView('management')}
                    className={`px-3 py-1 rounded text-sm transition-colors ${
                      view === 'management'
                        ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm'
                        : 'text-gray-600 dark:text-gray-400'
                    }`}
                  >
                    Management
                  </button>
                </div>

                {/* Refresh Button */}
                <button
                  onClick={refreshData}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Refresh
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {error && (
            <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <p className="text-red-600 dark:text-red-400">{error}</p>
            </div>
          )}

          {view === 'overview' ? (
            <>
              {/* Aggregate Overview */}
              <AggregateOverview data={aggregateData} className="mb-8" />

              {/* Main Dashboard Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                {/* Connection Monitor */}
                <ConnectionMonitor
                  brokerAccounts={brokerAccounts}
                  onReconnect={handleReconnectBroker}
                  className="lg:col-span-1"
                />

                {/* P&L Chart */}
                <PLChart
                  brokerAccounts={brokerAccounts}
                  className="lg:col-span-2"
                />
              </div>

              {/* Broker Account Cards */}
              <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                {brokerAccounts.map((account) => (
                  <BrokerOverviewCard
                    key={account.id}
                    account={account}
                    onReconnect={handleReconnectBroker}
                    onDisconnect={handleDisconnectBroker}
                    onRemove={handleRemoveBroker}
                  />
                ))}
                
                {brokerAccounts.length === 0 && (
                  <div className="col-span-full">
                    <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600">
                      <div className="mx-auto w-12 h-12 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mb-4">
                        <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                        </svg>
                      </div>
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                        No broker accounts configured
                      </h3>
                      <p className="text-gray-600 dark:text-gray-400 mb-4">
                        Get started by adding your first broker account
                      </p>
                      <button
                        onClick={() => setView('management')}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        Add Broker Account
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <>
              {/* Management View */}
              <BrokerManagementPanel
                brokerAccounts={brokerAccounts}
                onAddBroker={handleAddBroker}
                onRemoveBroker={handleRemoveBroker}
                onReconnectBroker={handleReconnectBroker}
              />
            </>
          )}
        </div>

        {/* Toast Notifications */}
        <ToastContainer
          toasts={toast ? [{ id: '1', ...toast }] : []}
          onClose={() => setToast(null)}
        />
      </div>
    </ErrorBoundary>
  );
}