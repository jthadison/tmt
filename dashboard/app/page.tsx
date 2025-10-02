'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import MainLayout from '@/components/layout/MainLayout'
import Card from '@/components/ui/Card'
import Grid from '@/components/ui/Grid'
import ConnectionStatus from '@/components/ui/ConnectionStatus'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import { AccountOverviewGrid } from '@/components/dashboard/AccountOverviewGrid'
import HealthCheckPanel from '@/components/dashboard/HealthCheckPanel'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useAccountData, useAccountWebSocket } from '@/hooks/useAccountData'
import { useRealTimeStore } from '@/store/realTimeStore'
import { useOandaData } from '@/hooks/useOandaData'
import { AccountsGrid } from '@/components/oanda/AccountsGrid'
import { intervalConfig } from '@/config/intervals'

export default function Home() {
  const router = useRouter()
  const { state: realTimeState, store } = useRealTimeStore()
  
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8080'

  // Debug: Log the WebSocket URL being used
  useEffect(() => {
    console.log('WebSocket URL configured:', wsUrl)
  }, [wsUrl])

  const { connectionStatus, connect, lastMessage, lastError, reconnectCount } = useWebSocket({
    url: wsUrl,
    reconnectAttempts: 5,
    reconnectInterval: intervalConfig.websocketReconnect,  // Auto-reconnection delay (configurable)
    heartbeatInterval: intervalConfig.websocketHeartbeat,  // Keep-alive heartbeat frequency (configurable)
    onError: (error) => {
      console.error('WebSocket error:', error)
    },
    onReconnectFailed: () => {
      console.error('Failed to reconnect after maximum attempts')
    }
  })

  const { accounts, loading, error, refreshData } = useAccountData()
  const { connectionStatus: wsAccountStatus } = useAccountWebSocket(accounts)
  
  // OANDA data integration
  const {
    accounts: oandaAccounts,
    accountMetrics: oandaMetrics,
    aggregatedMetrics: oandaAggregated,
    isLoading: oandaLoading,
    error: oandaError,
    lastUpdate: oandaLastUpdate,
    refreshData: refreshOandaData
  } = useOandaData()

  useEffect(() => {
    // Auto-connect on component mount
    connect()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    // Process WebSocket messages through real-time store
    if (lastMessage) {
      store.processMessage(lastMessage)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lastMessage])

  useEffect(() => {
    // Update connection status in store
    if (connectionStatus === 'connected') {
      store.setConnectionStatus('connected')
    } else if (connectionStatus === 'error') {
      store.setConnectionStatus('error')
    } else {
      store.setConnectionStatus('disconnected')
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connectionStatus])

  // Handle account drill-down navigation
  const handleAccountClick = (accountId: string) => {
    router.push(`/accounts/${accountId}`)
  }

  // Calculate summary metrics from both mock and OANDA accounts
  const totalBalance = accounts.reduce((sum, account) => sum + account.balance, 0) + 
                      oandaAccounts.reduce((sum, account) => sum + account.balance, 0)
  const totalEquity = accounts.reduce((sum, account) => sum + account.equity, 0) + 
                     oandaAccounts.reduce((sum, account) => sum + account.NAV, 0)
  const totalDailyPnL = accounts.reduce((sum, account) => sum + account.pnl.daily, 0) + 
                       oandaAccounts.reduce((sum, account) => sum + account.unrealizedPL, 0)
  const totalActivePositions = accounts.reduce((sum, account) => sum + account.positions.active, 0) + 
                              oandaAccounts.reduce((sum, account) => sum + account.openPositionCount, 0)
  
  // Health status for mock accounts
  const healthyAccounts = accounts.filter(account => account.status === 'healthy').length
  const warningAccounts = accounts.filter(account => account.status === 'warning').length
  const dangerAccounts = accounts.filter(account => account.status === 'danger').length
  
  // Health status for OANDA accounts
  const oandaHealthyAccounts = oandaAccounts.filter(account => account.healthStatus === 'healthy').length
  const oandaWarningAccounts = oandaAccounts.filter(account => account.healthStatus === 'warning').length
  const oandaDangerAccounts = oandaAccounts.filter(account => ['danger', 'margin_call'].includes(account.healthStatus)).length
  
  // Combined health metrics
  const totalHealthyAccounts = healthyAccounts + oandaHealthyAccounts
  const totalWarningAccounts = warningAccounts + oandaWarningAccounts
  const totalDangerAccounts = dangerAccounts + oandaDangerAccounts
  const totalAccounts = accounts.length + oandaAccounts.length

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount)
  }

  return (
    <ProtectedRoute>
      <MainLayout>
        <div className="space-y-8">
          {/* Summary Cards */}
          <Grid cols={{ default: 1, md: 2, xl: 4 }}>
            <Card title="Total Balance">
              <p className="text-2xl font-bold text-green-400">{formatCurrency(totalBalance)}</p>
              <p className="text-sm text-gray-500 mt-1">
                {totalAccounts} accounts ({accounts.length} demo, {oandaAccounts.length} OANDA)
              </p>
            </Card>
            
            <Card title="Total Equity">
              <p className="text-2xl font-bold text-blue-400">{formatCurrency(totalEquity)}</p>
              <p className="text-sm text-gray-500 mt-1">
                {totalDailyPnL >= 0 ? '+' : ''}{formatCurrency(totalDailyPnL)} today
              </p>
            </Card>
            
            <Card title="Active Positions">
              <p className="text-2xl font-bold text-purple-400">{totalActivePositions}</p>
              <p className="text-sm text-gray-500 mt-1">Across all accounts</p>
            </Card>
            
            <Card title="Account Health">
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-1">
                  <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                  <span className="text-sm text-green-400">{totalHealthyAccounts}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                  <span className="text-sm text-yellow-400">{totalWarningAccounts}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                  <span className="text-sm text-red-400">{totalDangerAccounts}</span>
                </div>
              </div>
              {oandaAccounts.length > 0 && (
                <div className="text-xs text-gray-400 mt-2">
                  Includes {oandaAccounts.length} live OANDA account{oandaAccounts.length !== 1 ? 's' : ''}
                </div>
              )}
            </Card>
          </Grid>

          {/* Account Overview Grid */}
          <AccountOverviewGrid
            accounts={accounts}
            loading={loading}
            error={error || undefined}
            onAccountClick={handleAccountClick}
            onRefresh={refreshData}
            refreshInterval={intervalConfig.dashboardRefresh}  // Auto-refresh interval in seconds (configurable)
          />

          {/* OANDA Live Accounts Section */}
          {oandaAccounts.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-white">OANDA Live Accounts</h2>
                  <p className="text-gray-400">Real-time data from your OANDA trading accounts</p>
                </div>
                <div className="flex items-center space-x-4">
                  <div className="text-sm text-gray-400">
                    Last updated: {oandaLastUpdate ? oandaLastUpdate.toLocaleTimeString() : 'Never'}
                  </div>
                  <button
                    onClick={refreshOandaData}
                    disabled={oandaLoading}
                    className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-3 py-1 rounded text-sm transition-colors"
                  >
                    {oandaLoading ? 'Refreshing...' : 'Refresh'}
                  </button>
                </div>
              </div>

              {oandaError && (
                <div className="p-3 bg-red-500/10 border border-red-500/20 rounded">
                  <span className="text-red-400 text-sm">OANDA Error: {oandaError}</span>
                </div>
              )}

              <AccountsGrid
                accounts={oandaAccounts}
                accountMetrics={oandaMetrics}
                loading={oandaLoading}
                error={oandaError || undefined}
                onAccountClick={(accountId) => window.open(`/oanda?account=${accountId}`, '_blank')}
                showFilters={false}
                columns={2}
                detailed={true}
              />
            </div>
          )}

          {/* OANDA Connection Prompt */}
          {oandaAccounts.length === 0 && !oandaLoading && (
            <Card title="OANDA Integration" className="border-blue-500/20 bg-blue-500/5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-300 mb-2">
                    Connect your OANDA account to see live trading data alongside your other accounts.
                  </p>
                  <p className="text-sm text-gray-400">
                    Real-time balance, positions, and P&L tracking from your OANDA practice or live account.
                  </p>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => router.push('/oanda')}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded transition-colors"
                  >
                    View OANDA
                  </button>
                </div>
              </div>
            </Card>
          )}

          {/* System Status */}
          <Grid cols={{ default: 1, lg: 2 }}>
            <HealthCheckPanel className="h-64" />

            <Card title="Connection Status" className="h-64">
              <div className="space-y-4">
                {/* WebSocket Status */}
                <div className="p-3 bg-gray-800 rounded">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">WebSocket</span>
                    <ConnectionStatus status={connectionStatus} />
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    URL: {wsUrl}
                  </div>
                  {reconnectCount > 0 && (
                    <div className="text-xs text-yellow-400">
                      Reconnection attempts: {reconnectCount}
                    </div>
                  )}
                  {lastError && (
                    <div className="text-xs text-red-400 mt-1">
                      Error: {lastError.message}
                    </div>
                  )}
                </div>

                {/* Account Updates */}
                <div className="p-3 bg-gray-800 rounded">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Account Updates</span>
                    <ConnectionStatus status={wsAccountStatus} />
                  </div>
                  {realTimeState.lastUpdate && (
                    <div className="text-xs text-gray-500 mt-1">
                      Last update: {new Date(realTimeState.lastUpdate).toLocaleTimeString()}
                    </div>
                  )}
                </div>

                {/* Alerts */}
                <div className="space-y-2">
                  {totalDangerAccounts > 0 && (
                    <div className="flex items-center p-2 bg-red-500/10 border border-red-500/20 rounded">
                      <span className="text-red-400 text-sm">
                        {totalDangerAccounts} account{totalDangerAccounts !== 1 ? 's' : ''} critical
                        {oandaDangerAccounts > 0 && ` (${oandaDangerAccounts} OANDA)`}
                      </span>
                    </div>
                  )}
                  {totalWarningAccounts > 0 && (
                    <div className="flex items-center p-2 bg-yellow-500/10 border border-yellow-500/20 rounded">
                      <span className="text-yellow-400 text-sm">
                        {totalWarningAccounts} account{totalWarningAccounts !== 1 ? 's' : ''} warning
                        {oandaWarningAccounts > 0 && ` (${oandaWarningAccounts} OANDA)`}
                      </span>
                    </div>
                  )}
                  {oandaAccounts.length > 0 && oandaLastUpdate && (
                    <div className="flex items-center p-2 bg-blue-500/10 border border-blue-500/20 rounded">
                      <span className="text-blue-400 text-sm">
                        OANDA: Last update {oandaLastUpdate.toLocaleTimeString()}
                      </span>
                    </div>
                  )}
                  {totalDangerAccounts === 0 && totalWarningAccounts === 0 && (
                    <div className="flex items-center p-2 bg-green-500/10 border border-green-500/20 rounded">
                      <span className="text-green-400 text-sm">
                        All accounts healthy{oandaAccounts.length > 0 ? ' (including OANDA)' : ''}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </Card>
          </Grid>
        </div>
      </MainLayout>
    </ProtectedRoute>
  )
}
