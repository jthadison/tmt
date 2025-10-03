/**
 * P&L Breakdown Modal Component
 * Displays detailed P&L breakdown with period comparisons and best/worst trades
 */

'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import Modal from '@/components/ui/Modal'
import { usePnLData } from '@/hooks/usePnLData'
import { usePeriodPerformance } from '@/hooks/usePeriodPerformance'
import { useOandaData } from '@/hooks/useOandaData'
import { formatCurrency, formatPercentage, getPnLColorClass } from '@/utils/formatCurrency'
import { PeriodType, TradeInfo } from '@/types/performance'

interface PnLBreakdownModalProps {
  isOpen: boolean
  onClose: () => void
}

/**
 * Metric card component for displaying P&L metrics
 */
function MetricCard({
  label,
  value,
  highlight = false,
}: {
  label: string
  value: number
  highlight?: boolean
}) {
  const colorClass = getPnLColorClass(value)

  return (
    <div
      className={`p-4 rounded-lg border ${
        highlight
          ? 'bg-blue-500/10 border-blue-500/30'
          : 'bg-gray-800 border-gray-700'
      }`}
    >
      <div className="text-sm text-gray-400 mb-1">{label}</div>
      <div className={`text-2xl font-bold ${colorClass}`}>
        {formatCurrency(value, 'USD', true)}
      </div>
    </div>
  )
}

/**
 * Trade card component for best/worst trade display
 */
function TradeCard({
  label,
  trade,
  variant,
}: {
  label: string
  trade: TradeInfo | null
  variant: 'success' | 'danger'
}) {
  const borderColor =
    variant === 'success' ? 'border-green-500/30' : 'border-red-500/30'
  const bgColor = variant === 'success' ? 'bg-green-500/5' : 'bg-red-500/5'

  if (!trade) {
    return (
      <div className={`p-4 rounded-lg border ${borderColor} ${bgColor}`}>
        <div className="text-sm font-medium text-gray-400 mb-2">{label}</div>
        <div className="text-sm text-gray-500">No trades yet</div>
      </div>
    )
  }

  const pnlColor = getPnLColorClass(trade.pnL)

  return (
    <div className={`p-4 rounded-lg border ${borderColor} ${bgColor}`}>
      <div className="text-sm font-medium text-gray-400 mb-2">{label}</div>
      <div className="space-y-2">
        <div className={`text-xl font-bold ${pnlColor}`}>
          {formatCurrency(trade.pnL, 'USD', true)}
        </div>
        <div className="text-sm space-y-1">
          <div className="flex justify-between">
            <span className="text-gray-400">Instrument:</span>
            <span className="text-white">{trade.instrument}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Direction:</span>
            <span className="text-white capitalize">{trade.direction}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Entry:</span>
            <span className="text-white">{trade.entryPrice.toFixed(5)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Exit:</span>
            <span className="text-white">{trade.exitPrice.toFixed(5)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Time:</span>
            <span className="text-white">
              {trade.exitTime.toLocaleTimeString()}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * P&L Breakdown Modal
 */
export function PnLBreakdownModal({ isOpen, onClose }: PnLBreakdownModalProps) {
  const router = useRouter()
  const { dailyPnL, realizedPnL, unrealizedPnL } = usePnLData()
  const { accounts } = useOandaData()
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodType>('today')

  const {
    periodData,
    bestTrade,
    worstTrade,
    isLoading: periodLoading,
    error: periodError,
  } = usePeriodPerformance(selectedPeriod)

  const periods: { value: PeriodType; label: string }[] = [
    { value: 'today', label: 'Today' },
    { value: 'week', label: 'This Week' },
    { value: 'month', label: 'This Month' },
    { value: 'all', label: 'All-Time' },
  ]

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="P&L Breakdown"
      size="lg"
      showCloseButton={true}
    >
      <div className="space-y-6">
        {/* Daily Summary */}
        <section>
          <h3 className="text-lg font-semibold text-white mb-3">
            Daily Summary
          </h3>
          <div className="grid grid-cols-3 gap-4">
            <MetricCard label="Realized P&L" value={realizedPnL} />
            <MetricCard label="Unrealized P&L" value={unrealizedPnL} />
            <MetricCard label="Total Daily P&L" value={dailyPnL} highlight />
          </div>
        </section>

        {/* Period Comparison */}
        <section>
          <h3 className="text-lg font-semibold text-white mb-3">
            Period Comparison
          </h3>

          {/* Period Tabs */}
          <div className="flex space-x-2 mb-4">
            {periods.map((period) => (
              <button
                key={period.value}
                onClick={() => setSelectedPeriod(period.value)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  selectedPeriod === period.value
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                {period.label}
              </button>
            ))}
          </div>

          {/* Period Stats */}
          {periodError ? (
            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
              <div className="text-red-400 font-medium mb-2">Error Loading Data</div>
              <div className="text-sm text-red-300">{periodError}</div>
              <button
                onClick={() => window.location.reload()}
                className="mt-3 text-sm text-red-400 hover:text-red-300 underline"
              >
                Retry
              </button>
            </div>
          ) : periodLoading ? (
            <div className="p-4 bg-gray-800 rounded-lg text-center text-gray-400">
              <div className="animate-pulse">Loading period data...</div>
            </div>
          ) : periodData ? (
            <div className="p-4 bg-gray-800 rounded-lg space-y-3">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-gray-400">Total P&L</div>
                  <div
                    className={`text-xl font-bold ${getPnLColorClass(
                      periodData.totalPnL
                    )}`}
                  >
                    {formatCurrency(periodData.totalPnL, 'USD', true)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-400">P&L %</div>
                  <div
                    className={`text-xl font-bold ${getPnLColorClass(
                      periodData.pnLPercentage
                    )}`}
                  >
                    {formatPercentage(periodData.pnLPercentage)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-400">Trades</div>
                  <div className="text-xl font-bold text-white">
                    {periodData.tradeCount}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-400">Win Rate</div>
                  <div className="text-xl font-bold text-white">
                    {periodData.winRate.toFixed(1)}%
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-4 bg-gray-800 rounded-lg text-center text-gray-400">
              No data available for this period
            </div>
          )}
        </section>

        {/* Account Breakdown (if multiple accounts) */}
        {accounts.length > 1 && (
          <section>
            <h3 className="text-lg font-semibold text-white mb-3">
              Account Breakdown
            </h3>
            <div className="space-y-2">
              {accounts.map((account) => (
                <div
                  key={account.id}
                  className="flex justify-between items-center p-3 bg-gray-800 rounded-lg"
                >
                  <span className="text-white">{account.alias}</span>
                  <span
                    className={`font-semibold ${getPnLColorClass(
                      account.unrealizedPL + account.realizedPL
                    )}`}
                  >
                    {formatCurrency(
                      account.unrealizedPL + account.realizedPL,
                      'USD',
                      true
                    )}
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Best & Worst Trades */}
        <section>
          <h3 className="text-lg font-semibold text-white mb-3">
            Best & Worst Trades
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <TradeCard label="Best Trade" trade={bestTrade} variant="success" />
            <TradeCard
              label="Worst Trade"
              trade={worstTrade}
              variant="danger"
            />
          </div>
        </section>

        {/* Footer */}
        <div className="flex justify-end pt-4 border-t border-gray-700">
          <button
            onClick={() => {
              onClose()
              router.push('/performance-analytics')
            }}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg transition-colors font-medium"
          >
            View Detailed Analytics
          </button>
        </div>
      </div>
    </Modal>
  )
}

export default PnLBreakdownModal
