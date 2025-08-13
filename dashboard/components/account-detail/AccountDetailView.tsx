'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { AccountDetails } from '@/types/accountDetail'
import { PositionsTable } from './PositionsTable'
import { TradeHistory } from './TradeHistory'
import { EquityCurveChart } from './EquityCurveChart'
import { RiskMetricsDashboard } from './RiskMetricsDashboard'
import { ComplianceMonitor } from './ComplianceMonitor'
import { ManualOverridePanel } from './ManualOverridePanel'
import { LoadingSkeleton } from '../ui/LoadingSkeleton'

/**
 * Props for AccountDetailView component
 */
interface AccountDetailViewProps {
  /** Account ID to display details for */
  accountId?: string
  /** Loading state indicator */
  loading?: boolean
  /** Error message */
  error?: string
  /** Callback when account data needs refresh */
  onRefresh?: () => void
}

/**
 * Main container component for individual account detail view
 * Provides comprehensive analysis and control capabilities
 */
export function AccountDetailView({
  accountId,
  loading = false,
  error,
  onRefresh
}: AccountDetailViewProps) {
  const params = useParams()
  const finalAccountId = accountId || (params.id as string)
  
  const [accountDetails, setAccountDetails] = useState<AccountDetails | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'positions' | 'history' | 'analytics'>('overview')

  // Mock data for development - will be replaced with real API calls
  useEffect(() => {
    if (!finalAccountId) return

    const loadAccountDetails = async () => {
      // Simulate API call delay
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      // Mock account details data
      const mockDetails: AccountDetails = {
        id: finalAccountId,
        accountName: `Account ${finalAccountId.slice(-2).toUpperCase()}`,
        propFirm: 'FTMO',
        balance: 100000,
        equity: 102500,
        positions: [
          {
            id: 'pos-1',
            symbol: 'EUR/USD',
            type: 'long',
            size: 1.5,
            entryPrice: 1.0850,
            currentPrice: 1.0875,
            pnl: 375,
            pnlPercentage: 2.3,
            openTime: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
            duration: 120,
            stopLoss: 1.0820,
            takeProfit: 1.0920,
            commission: 15,
            riskPercentage: 1.5
          },
          {
            id: 'pos-2',
            symbol: 'GBP/JPY',
            type: 'short',
            size: 0.8,
            entryPrice: 185.50,
            currentPrice: 185.20,
            pnl: 240,
            pnlPercentage: 1.6,
            openTime: new Date(Date.now() - 45 * 60 * 1000), // 45 minutes ago
            duration: 45,
            commission: 12,
            riskPercentage: 1.2
          }
        ],
        recentTrades: [
          {
            id: 'trade-1',
            symbol: 'XAU/USD',
            type: 'long',
            size: 0.1,
            entryPrice: 2050.00,
            exitPrice: 2065.00,
            pnl: 150,
            commission: 8,
            openTime: new Date(Date.now() - 24 * 60 * 60 * 1000),
            closeTime: new Date(Date.now() - 22 * 60 * 60 * 1000),
            duration: 120,
            strategy: 'Breakout'
          }
        ],
        equityHistory: Array.from({ length: 30 }, (_, i) => ({
          timestamp: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000),
          equity: 100000 + Math.random() * 5000 - 2500,
          balance: 100000,
          drawdown: Math.random() * 1000
        })),
        riskMetrics: {
          sharpeRatio: 1.85,
          winRate: 68.5,
          profitFactor: 1.45,
          maxDrawdown: 8.2,
          averageWin: 145,
          averageLoss: -85,
          totalTrades: 156,
          consecutiveWins: 5,
          consecutiveLosses: 2,
          largestWin: 850,
          largestLoss: -450
        },
        complianceStatus: {
          dailyLossLimit: { current: 500, limit: 5000, percentage: 10 },
          monthlyLossLimit: { current: 2500, limit: 10000, percentage: 25 },
          maxDrawdown: { current: 8200, limit: 10000, percentage: 82 },
          minTradingDays: { current: 15, required: 30, percentage: 50 },
          accountTier: 'Tier 1',
          violations: [],
          overallStatus: 'compliant'
        },
        tradingPermissions: {
          canTrade: true,
          canClose: true,
          canModify: true,
          maxPositionSize: 10,
          maxDailyTrades: 20,
          requiresConfirmation: false
        },
        lastUpdate: new Date()
      }

      setAccountDetails(mockDetails)
    }

    if (!loading) {
      loadAccountDetails()
    }
  }, [finalAccountId, loading])

  if (loading || !accountDetails) {
    return (
      <div className="space-y-6">
        <LoadingSkeleton className="h-20" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <LoadingSkeleton className="h-64" />
          <LoadingSkeleton className="h-64" />
          <LoadingSkeleton className="h-64" />
        </div>
        <LoadingSkeleton className="h-96" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-400 text-xl mb-2">Error Loading Account Details</div>
        <p className="text-gray-400 mb-4">{error}</p>
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded transition-colors"
          >
            Try Again
          </button>
        )}
      </div>
    )
  }

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount)
  }

  return (
    <div className="space-y-6">
      {/* Account Header */}
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white mb-2">{accountDetails.accountName}</h1>
            <p className="text-gray-400">{accountDetails.propFirm}</p>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-400">Balance</div>
            <div className="text-xl font-bold text-white">{formatCurrency(accountDetails.balance)}</div>
            <div className="text-sm text-gray-400 mt-1">
              Equity: {formatCurrency(accountDetails.equity)}
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="bg-gray-800 rounded-lg">
        <div className="border-b border-gray-700">
          <nav className="flex space-x-8 px-6">
            {[
              { id: 'overview', label: 'Overview' },
              { id: 'positions', label: 'Positions' },
              { id: 'history', label: 'Trade History' },
              { id: 'analytics', label: 'Analytics' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as 'overview' | 'positions' | 'history' | 'analytics')}
                className={`
                  py-4 px-2 border-b-2 font-medium text-sm transition-colors
                  ${activeTab === tab.id
                    ? 'border-blue-500 text-blue-400'
                    : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-300'
                  }
                `}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <RiskMetricsDashboard riskMetrics={accountDetails.riskMetrics} />
              <ComplianceMonitor complianceStatus={accountDetails.complianceStatus} />
              <div className="lg:col-span-2">
                <EquityCurveChart 
                  equityHistory={accountDetails.equityHistory}
                  accountName={accountDetails.accountName}
                />
              </div>
            </div>
          )}

          {activeTab === 'positions' && (
            <div className="space-y-6">
              <PositionsTable 
                positions={accountDetails.positions}
                onRefresh={onRefresh}
              />
              <ManualOverridePanel 
                tradingPermissions={accountDetails.tradingPermissions}
                positions={accountDetails.positions}
              />
            </div>
          )}

          {activeTab === 'history' && (
            <TradeHistory 
              trades={accountDetails.recentTrades}
              accountId={accountDetails.id}
            />
          )}

          {activeTab === 'analytics' && (
            <div className="grid grid-cols-1 gap-6">
              <EquityCurveChart 
                equityHistory={accountDetails.equityHistory}
                accountName={accountDetails.accountName}
                showDetailed
              />
              <RiskMetricsDashboard 
                riskMetrics={accountDetails.riskMetrics}
                detailed
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}