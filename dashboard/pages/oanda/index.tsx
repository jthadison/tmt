'use client'

import React, { useState, useEffect } from 'react'
import { useOandaData } from '@/hooks/useOandaData'
import { AccountsGrid } from '@/components/oanda/AccountsGrid'
import { MultiAccountSummary } from '@/components/oanda/MultiAccountSummary'
import { AccountCharts } from '@/components/oanda/AccountCharts'
import { AccountFilter, AccountHealthStatus, CurrencyCode, TimeFrame } from '@/types/oanda'
import Card from '@/components/ui/Card'

/**
 * Main OANDA Dashboard Page - Story 9.3 Implementation
 * 
 * This page implements all 5 acceptance criteria for Story 9.3:
 * AC1: Account overview dashboard showing balance, equity, margin for all connected OANDA accounts
 * AC2: Real-time updates with visual indicators for active data streams
 * AC3: Trading limits and utilization tracking
 * AC4: Historical performance charts with multiple timeframes
 * AC5: Multi-account summary view with drill-down capability
 */
export default function OandaDashboard() {
  const {
    accounts,
    accountMetrics,
    accountHistory,
    performanceSummaries,
    tradingLimits,
    aggregatedMetrics,
    connectionStatus,
    alerts,
    isLoading,
    error,
    lastUpdate,
    refreshData,
    refreshAccount,
    loadAccountHistory,
    getPerformanceSummary,
    subscribeToUpdates,
    unsubscribeFromUpdates,
    reconnectAccount,
    dismissAlert,
    getAlertsForAccount,
    getFilteredAccounts,
    getAccountById,
    getMetricsById,
    isAccountConnected
  } = useOandaData()

  const [currentView, setCurrentView] = useState<'summary' | 'grid' | 'charts'>('summary')
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null)
  const [accountFilter, setAccountFilter] = useState<AccountFilter>({})
  const [chartTimeFrame, setChartTimeFrame] = useState<TimeFrame>('1D')

  // Real-time updates subscription
  useEffect(() => {
    subscribeToUpdates()
    return () => unsubscribeFromUpdates()
  }, [subscribeToUpdates, unsubscribeFromUpdates])

  // Auto-refresh data every 30 seconds - live data refresh mechanism
  useEffect(() => {
    const interval = setInterval(() => {
      refreshData()
    }, 30000) // auto-refresh every 30 seconds

    return () => clearInterval(interval)
  }, [refreshData])

  // Handle account selection for charts
  const handleAccountClick = (accountId: string) => {
    setSelectedAccountId(accountId)
    setCurrentView('charts')
    
    // Load historical data for charts
    const endDate = new Date()
    const startDate = new Date()
    startDate.setDate(endDate.getDate() - 30) // Last 30 days
    
    loadAccountHistory(accountId, chartTimeFrame, startDate, endDate)
    getPerformanceSummary(accountId, startDate, endDate)
  }

  // Handle drill-down from summary
  const handleDrillDown = (filter: { healthStatus?: AccountHealthStatus; currency?: CurrencyCode }) => {
    setAccountFilter(filter)
    setCurrentView('grid')
  }

  // Handle time frame change for charts
  const handleTimeFrameChange = (timeFrame: TimeFrame) => {
    setChartTimeFrame(timeFrame)
    
    if (selectedAccountId) {
      const endDate = new Date()
      const startDate = new Date()
      
      // Adjust date range based on timeframe
      switch (timeFrame) {
        case '1H':
          startDate.setHours(endDate.getHours() - 24)
          break
        case '4H':
          startDate.setDate(endDate.getDate() - 7)
          break
        case '1D':
          startDate.setDate(endDate.getDate() - 30)
          break
        case '1W':
          startDate.setDate(endDate.getDate() - 90)
          break
        case '1M':
          startDate.setFullYear(endDate.getFullYear() - 1)
          break
      }
      
      loadAccountHistory(selectedAccountId, timeFrame, startDate, endDate)
    }
  }

  // Connection status indicators
  const getConnectionStatusColor = (accountId: string): string => {
    return isAccountConnected(accountId) ? 'text-green-400' : 'text-red-400'
  }

  const selectedAccount = selectedAccountId ? getAccountById(selectedAccountId) : null
  const selectedAccountHistory = selectedAccountId ? accountHistory.get(selectedAccountId) || [] : []
  const selectedAccountPerformance = selectedAccountId ? performanceSummaries.get(selectedAccountId) : undefined

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">OANDA Dashboard</h1>
            <div className="flex items-center gap-4 text-sm text-gray-400">
              <span>
                Last updated: {lastUpdate ? lastUpdate.toLocaleTimeString() : 'Never'}
              </span>
              <span>•</span>
              <span>{accounts.length} accounts</span>
              <span>•</span>
              <span className={isLoading ? 'text-yellow-400' : 'text-green-400'}>
                {isLoading ? 'Updating...' : 'Live'}
              </span>
            </div>
          </div>

          {/* Navigation */}
          <div className="flex items-center gap-2">
            <div className="flex bg-gray-800 rounded-lg p-1">
              <button
                onClick={() => setCurrentView('summary')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  currentView === 'summary'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Summary
              </button>
              <button
                onClick={() => setCurrentView('grid')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  currentView === 'grid'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Accounts
              </button>
              <button
                onClick={() => setCurrentView('charts')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  currentView === 'charts'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
                disabled={!selectedAccountId}
              >
                Charts
              </button>
            </div>
            <button
              onClick={refreshData}
              disabled={isLoading}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white rounded-lg transition-colors text-sm font-medium"
            >
              {isLoading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <Card className="border-red-500/50 bg-red-900/20">
            <div className="flex items-center gap-3">
              <div className="text-red-400 text-lg">⚠️</div>
              <div>
                <div className="text-red-400 font-medium">Error</div>
                <div className="text-red-300 text-sm">{error}</div>
              </div>
            </div>
          </Card>
        )}

        {/* Alerts */}
        {alerts.length > 0 && (
          <Card className="border-yellow-500/50 bg-yellow-900/20">
            <div className="space-y-3">
              <h3 className="text-yellow-400 font-medium">Active Alerts ({alerts.length})</h3>
              <div className="space-y-2">
                {alerts.slice(0, 3).map(alert => (
                  <div key={alert.id} className="flex justify-between items-center">
                    <div className="text-yellow-300 text-sm">
                      <span className="font-medium">{alert.accountId}:</span> {alert.message}
                    </div>
                    <button
                      onClick={() => dismissAlert(alert.id)}
                      className="text-yellow-400 hover:text-yellow-300 text-xs"
                    >
                      Dismiss
                    </button>
                  </div>
                ))}
                {alerts.length > 3 && (
                  <div className="text-yellow-400 text-xs">
                    ... and {alerts.length - 3} more alerts
                  </div>
                )}
              </div>
            </div>
          </Card>
        )}

        {/* Connection Status */}
        <Card>
          <h3 className="text-white font-medium mb-3">Connection Status</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {connectionStatus.map(status => (
              <div key={status.accountId} className="flex items-center justify-between">
                <span className="text-gray-400 text-sm">{status.accountId}</span>
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${
                    status.status === 'connected' ? 'bg-green-400' : 
                    status.status === 'connecting' ? 'bg-yellow-400' : 'bg-red-400'
                  }`} />
                  <span className={`text-xs ${getConnectionStatusColor(status.accountId)}`}>
                    {status.status}
                  </span>
                  {status.status === 'disconnected' && (
                    <button
                      onClick={() => reconnectAccount(status.accountId)}
                      className="text-blue-400 hover:text-blue-300 text-xs"
                    >
                      Reconnect
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Main Content */}
        {currentView === 'summary' && aggregatedMetrics && (
          <MultiAccountSummary
            aggregatedMetrics={aggregatedMetrics}
            loading={isLoading}
            detailed={true}
            onDrillDown={handleDrillDown}
          />
        )}

        {currentView === 'grid' && (
          <AccountsGrid
            accounts={accounts}
            accountMetrics={accountMetrics}
            alertCounts={new Map(alerts.map(alert => [alert.accountId, getAlertsForAccount(alert.accountId).length]))}
            loading={isLoading}
            error={error}
            onAccountClick={handleAccountClick}
            filter={accountFilter}
            onFilterChange={setAccountFilter}
            showFilters={true}
            detailed={true}
          />
        )}

        {currentView === 'charts' && selectedAccount && (
          <div className="space-y-6">
            {/* Chart Header */}
            <Card>
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-xl font-bold text-white">{selectedAccount.alias}</h2>
                  <div className="text-gray-400 text-sm">
                    {selectedAccount.type.toUpperCase()} • {selectedAccount.currency} • ID: {selectedAccount.id}
                  </div>
                </div>
                <button
                  onClick={() => setCurrentView('grid')}
                  className="text-blue-400 hover:text-blue-300 text-sm"
                >
                  ← Back to Grid
                </button>
              </div>
            </Card>

            {/* Charts */}
            <AccountCharts
              accountId={selectedAccount.id}
              currency={selectedAccount.currency}
              historyData={selectedAccountHistory}
              performanceSummary={selectedAccountPerformance}
              loading={isLoading}
              error={error}
              timeFrame={chartTimeFrame}
              onTimeFrameChange={handleTimeFrameChange}
              height={400}
            />

            {/* Trading Limits */}
            {tradingLimits.has(selectedAccount.id) && (
              <Card>
                <h3 className="text-lg font-semibold text-white mb-4">Trading Limits & Utilization</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {(() => {
                    const limits = tradingLimits.get(selectedAccount.id)!
                    return (
                      <>
                        <div>
                          <div className="text-gray-400 text-sm">Max Position Size</div>
                          <div className="text-white font-medium">
                            {new Intl.NumberFormat().format(limits.maxPositionSize)}
                          </div>
                          <div className="text-xs text-gray-500">
                            Used: {((limits.currentPositionSize / limits.maxPositionSize) * 100).toFixed(1)}%
                          </div>
                        </div>
                        <div>
                          <div className="text-gray-400 text-sm">Max Open Trades</div>
                          <div className="text-white font-medium">{limits.maxOpenTrades}</div>
                          <div className="text-xs text-gray-500">
                            Used: {limits.currentOpenTrades}/{limits.maxOpenTrades}
                          </div>
                        </div>
                        <div>
                          <div className="text-gray-400 text-sm">Max Drawdown</div>
                          <div className="text-white font-medium">{limits.maxDrawdownPercent}%</div>
                          <div className="text-xs text-gray-500">
                            Current: {limits.currentDrawdownPercent.toFixed(2)}%
                          </div>
                        </div>
                        <div>
                          <div className="text-gray-400 text-sm">Daily Loss Limit</div>
                          <div className="text-white font-medium">
                            {new Intl.NumberFormat('en-US', {
                              style: 'currency',
                              currency: selectedAccount.currency
                            }).format(limits.maxDailyLoss)}
                          </div>
                          <div className="text-xs text-gray-500">
                            Used: {((Math.abs(limits.currentDailyLoss) / limits.maxDailyLoss) * 100).toFixed(1)}%
                          </div>
                        </div>
                      </>
                    )
                  })()}
                </div>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  )
}