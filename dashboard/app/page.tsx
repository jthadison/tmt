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

export default function Home() {
  const router = useRouter()
  const { state: realTimeState, store } = useRealTimeStore()
  
  const { connectionStatus, connect, lastMessage, lastError, reconnectCount } = useWebSocket({
    url: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8080',
    reconnectAttempts: 5,
    reconnectInterval: 3000,
    onError: (error) => {
      console.error('WebSocket error:', error)
    },
    onReconnectFailed: () => {
      console.error('Failed to reconnect after maximum attempts')
    }
  })

  const { accounts, loading, error, refreshData } = useAccountData()
  const { connectionStatus: wsAccountStatus } = useAccountWebSocket(accounts)

  useEffect(() => {
    // Auto-connect on component mount
    connect()
  }, [connect])

  useEffect(() => {
    // Process WebSocket messages through real-time store
    if (lastMessage) {
      store.processMessage(lastMessage)
    }
  }, [lastMessage, store])

  useEffect(() => {
    // Update connection status in store
    if (connectionStatus === 'connected') {
      store.setConnectionStatus('connected')
    } else if (connectionStatus === 'error') {
      store.setConnectionStatus('error')
    } else {
      store.setConnectionStatus('disconnected')
    }
  }, [connectionStatus, store])

  // Handle account drill-down navigation
  const handleAccountClick = (accountId: string) => {
    router.push(`/accounts/${accountId}`)
  }

  // Calculate summary metrics from accounts
  const totalBalance = accounts.reduce((sum, account) => sum + account.balance, 0)
  const totalEquity = accounts.reduce((sum, account) => sum + account.equity, 0)
  const totalDailyPnL = accounts.reduce((sum, account) => sum + account.pnl.daily, 0)
  const totalActivePositions = accounts.reduce((sum, account) => sum + account.positions.active, 0)
  const healthyAccounts = accounts.filter(account => account.status === 'healthy').length
  const warningAccounts = accounts.filter(account => account.status === 'warning').length
  const dangerAccounts = accounts.filter(account => account.status === 'danger').length

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
              <p className="text-sm text-gray-500 mt-1">{accounts.length} accounts</p>
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
                  <span className="text-sm text-green-400">{healthyAccounts}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                  <span className="text-sm text-yellow-400">{warningAccounts}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                  <span className="text-sm text-red-400">{dangerAccounts}</span>
                </div>
              </div>
            </Card>
          </Grid>

          {/* Account Overview Grid */}
          <AccountOverviewGrid
            accounts={accounts}
            loading={loading}
            error={error || undefined}
            onAccountClick={handleAccountClick}
            onRefresh={refreshData}
            refreshInterval={30}
          />

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
                  {dangerAccounts > 0 && (
                    <div className="flex items-center p-2 bg-red-500/10 border border-red-500/20 rounded">
                      <span className="text-red-400 text-sm">
                        {dangerAccounts} account{dangerAccounts !== 1 ? 's' : ''} critical
                      </span>
                    </div>
                  )}
                  {warningAccounts > 0 && (
                    <div className="flex items-center p-2 bg-yellow-500/10 border border-yellow-500/20 rounded">
                      <span className="text-yellow-400 text-sm">
                        {warningAccounts} account{warningAccounts !== 1 ? 's' : ''} warning
                      </span>
                    </div>
                  )}
                  {dangerAccounts === 0 && warningAccounts === 0 && (
                    <div className="flex items-center p-2 bg-green-500/10 border border-green-500/20 rounded">
                      <span className="text-green-400 text-sm">
                        All accounts healthy
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
