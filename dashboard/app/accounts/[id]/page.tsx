'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import MainLayout from '@/components/layout/MainLayout'
import Card from '@/components/ui/Card'
import Grid from '@/components/ui/Grid'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import { StatusIndicator } from '@/components/dashboard/StatusIndicator'
import { PnLDisplay } from '@/components/dashboard/PnLDisplay'
import { DrawdownBar } from '@/components/dashboard/DrawdownBar'
import { PositionMetrics } from '@/components/dashboard/PositionMetrics'
import { AccountOverview } from '@/types/account'
import { useAccountData } from '@/hooks/useAccountData'

/**
 * Individual account details page
 * Provides comprehensive view of single account with detailed metrics
 */
export default function AccountDetailPage() {
  const router = useRouter()
  const params = useParams()
  const accountId = params.id as string

  const { accounts, loading, error } = useAccountData()
  const [account, setAccount] = useState<AccountOverview | null>(null)

  useEffect(() => {
    if (accounts.length > 0) {
      const foundAccount = accounts.find(acc => acc.id === accountId)
      setAccount(foundAccount || null)
    }
  }, [accounts, accountId])

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount)
  }

  const formatPercentage = (value: number): string => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  if (loading) {
    return (
      <ProtectedRoute>
        <MainLayout>
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-gray-700 rounded w-1/3"></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-32 bg-gray-700 rounded"></div>
              ))}
            </div>
          </div>
        </MainLayout>
      </ProtectedRoute>
    )
  }

  if (error || !account) {
    return (
      <ProtectedRoute>
        <MainLayout>
          <div className="text-center py-12">
            <div className="text-red-400 text-xl mb-2">Account Not Found</div>
            <p className="text-gray-400 mb-4">
              {error || 'The requested account could not be found.'}
            </p>
            <button
              onClick={() => router.push('/')}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded transition-colors"
            >
              Return to Dashboard
            </button>
          </div>
        </MainLayout>
      </ProtectedRoute>
    )
  }

  return (
    <ProtectedRoute>
      <MainLayout>
        <div className="space-y-6">
          {/* Breadcrumb Navigation */}
          <nav className="flex" aria-label="Breadcrumb">
            <ol className="flex items-center space-x-4">
              <li>
                <button
                  onClick={() => router.push('/')}
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  Dashboard
                </button>
              </li>
              <li className="flex items-center">
                <span className="text-gray-500 mx-2">/</span>
                <span className="text-white">Accounts</span>
              </li>
              <li className="flex items-center">
                <span className="text-gray-500 mx-2">/</span>
                <span className="text-white">{account.accountName}</span>
              </li>
            </ol>
          </nav>

          {/* Account Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <h1 className="text-3xl font-bold text-white">{account.accountName}</h1>
              <StatusIndicator status={account.status} showText size="lg" />
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-400">{account.propFirm}</div>
              <div className="text-xs text-gray-500">
                Last updated: {account.lastUpdate.toLocaleString()}
              </div>
            </div>
          </div>

          {/* Key Metrics Grid */}
          <Grid cols={{ default: 1, md: 2, lg: 4 }}>
            <Card title="Account Balance">
              <p className="text-2xl font-bold text-white">{formatCurrency(account.balance)}</p>
              <p className="text-sm text-gray-400 mt-1">Starting balance</p>
            </Card>

            <Card title="Current Equity">
              <p className="text-2xl font-bold text-blue-400">{formatCurrency(account.equity)}</p>
              <p className="text-sm text-gray-400 mt-1">
                {account.equity > account.balance ? 'Above' : 'Below'} balance
              </p>
            </Card>

            <Card title="Total P&L">
              <p className={`text-2xl font-bold ${account.pnl.total >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {formatCurrency(account.pnl.total)}
              </p>
              <p className="text-sm text-gray-400 mt-1">
                {formatPercentage(account.pnl.percentage)} return
              </p>
            </Card>

            <Card title="Risk Level">
              <p className={`text-2xl font-bold ${
                account.drawdown.percentage <= 30 ? 'text-green-400' :
                account.drawdown.percentage <= 50 ? 'text-yellow-400' :
                account.drawdown.percentage <= 80 ? 'text-orange-400' : 'text-red-400'
              }`}>
                {account.drawdown.percentage.toFixed(1)}%
              </p>
              <p className="text-sm text-gray-400 mt-1">Drawdown utilized</p>
            </Card>
          </Grid>

          {/* Detailed Components Grid */}
          <Grid cols={{ default: 1, lg: 2 }}>
            {/* P&L Analysis */}
            <Card title="Profit & Loss Analysis" className="h-auto">
              <PnLDisplay pnl={account.pnl} detailed />
            </Card>

            {/* Position & Exposure Details */}
            <Card title="Positions & Exposure" className="h-auto">
              <PositionMetrics 
                positions={account.positions} 
                exposure={account.exposure} 
                detailed 
              />
            </Card>
          </Grid>

          {/* Risk Management */}
          <Grid cols={{ default: 1 }}>
            <Card title="Risk Management">
              <div className="space-y-6">
                <div>
                  <h4 className="text-lg font-medium text-white mb-3">Drawdown Analysis</h4>
                  <DrawdownBar drawdown={account.drawdown} />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-gray-800 rounded-lg p-4">
                    <div className="text-sm text-gray-400 mb-1">Current Drawdown</div>
                    <div className="text-lg font-bold text-white">
                      {formatCurrency(account.drawdown.current)}
                    </div>
                  </div>
                  
                  <div className="bg-gray-800 rounded-lg p-4">
                    <div className="text-sm text-gray-400 mb-1">Maximum Allowed</div>
                    <div className="text-lg font-bold text-white">
                      {formatCurrency(account.drawdown.maximum)}
                    </div>
                  </div>
                  
                  <div className="bg-gray-800 rounded-lg p-4">
                    <div className="text-sm text-gray-400 mb-1">Remaining Buffer</div>
                    <div className="text-lg font-bold text-green-400">
                      {formatCurrency(account.drawdown.maximum - account.drawdown.current)}
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </Grid>

          {/* Account Actions */}
          <div className="flex justify-center space-x-4">
            <button
              onClick={() => router.push('/')}
              className="bg-gray-700 hover:bg-gray-600 text-white px-6 py-2 rounded transition-colors"
            >
              Back to Overview
            </button>
            
            <button
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded transition-colors"
              disabled
            >
              Export Report (Coming Soon)
            </button>
            
            {account.status === 'danger' && (
              <button
                className="bg-red-600 hover:bg-red-700 text-white px-6 py-2 rounded transition-colors"
                disabled
              >
                Emergency Stop (Coming Soon)
              </button>
            )}
          </div>
        </div>
      </MainLayout>
    </ProtectedRoute>
  )
}