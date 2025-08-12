'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import MainLayout from '@/components/layout/MainLayout'
import Card from '@/components/ui/Card'
import Grid from '@/components/ui/Grid'
import ConnectionStatus from '@/components/ui/ConnectionStatus'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import { AccountOverviewGrid } from '@/components/dashboard/AccountOverviewGrid'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useAccountData, useAccountWebSocket } from '@/hooks/useAccountData'

export default function Home() {
  const router = useRouter()
  
  const { connectionStatus, connect } = useWebSocket({
    url: 'ws://localhost:8080', // Development WebSocket URL
    reconnectAttempts: 3,
    reconnectInterval: 3000
  })

  const { accounts, loading, error, refreshData } = useAccountData()
  const { connectionStatus: wsAccountStatus } = useAccountWebSocket(accounts)

  useEffect(() => {
    // Auto-connect on component mount
    connect()
  }, [connect])

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
            <Card title="System Status" className="h-64">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span>Market Analysis Agent</span>
                  <span className="text-green-400">● Active</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Risk Management</span>
                  <span className="text-green-400">● Active</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Circuit Breaker</span>
                  <span className="text-yellow-400">● Monitoring</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>WebSocket Connection</span>
                  <ConnectionStatus status={connectionStatus} />
                </div>
                <div className="flex items-center justify-between">
                  <span>Account Updates</span>
                  <ConnectionStatus status={wsAccountStatus} />
                </div>
              </div>
            </Card>

            <Card title="Recent Alerts" className="h-64">
              <div className="space-y-2">
                {dangerAccounts > 0 && (
                  <div className="flex items-center p-2 bg-red-500/10 border border-red-500/20 rounded">
                    <span className="text-red-400 text-sm">
                      ⚠️ {dangerAccounts} account{dangerAccounts !== 1 ? 's' : ''} in danger zone
                    </span>
                  </div>
                )}
                {warningAccounts > 0 && (
                  <div className="flex items-center p-2 bg-yellow-500/10 border border-yellow-500/20 rounded">
                    <span className="text-yellow-400 text-sm">
                      ⚡ {warningAccounts} account{warningAccounts !== 1 ? 's' : ''} need attention
                    </span>
                  </div>
                )}
                {dangerAccounts === 0 && warningAccounts === 0 && (
                  <div className="flex items-center p-2 bg-green-500/10 border border-green-500/20 rounded">
                    <span className="text-green-400 text-sm">
                      ✅ All accounts operating normally
                    </span>
                  </div>
                )}
              </div>
            </Card>
          </Grid>
        </div>
      </MainLayout>
    </ProtectedRoute>
  )
}
