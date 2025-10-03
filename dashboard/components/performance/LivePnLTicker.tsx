/**
 * Live P&L Ticker Component
 * Real-time profit/loss display in header with sparkline and modal trigger
 */

'use client'

import React, { useMemo, useState } from 'react'
import { usePnLData } from '@/hooks/usePnLData'
import { MiniSparkline } from '@/components/charts/MiniSparkline'
import { AnimatedNumber } from '@/components/ui/AnimatedNumber'
import { formatCurrency, formatPercentage, getPnLColorClass, getPnLBackgroundClass } from '@/utils/formatCurrency'
import { PnLBreakdownModal } from './PnLBreakdownModal'

/**
 * Live P&L Ticker component for header
 */
export function LivePnLTicker() {
  const { dailyPnL, pnLPercentage, pnLHistory, isLoading } = usePnLData()
  const [isModalOpen, setIsModalOpen] = useState(false)

  // Determine direction arrow
  const directionArrow = useMemo(() => {
    if (dailyPnL > 0) return '↑'
    if (dailyPnL < 0) return '↓'
    return '→'
  }, [dailyPnL])

  // Memoize formatted percentage
  const formattedPercentage = useMemo(
    () => formatPercentage(pnLPercentage),
    [pnLPercentage]
  )

  // Color classes
  const textColorClass = getPnLColorClass(dailyPnL)
  const bgColorClass = getPnLBackgroundClass(dailyPnL)

  if (isLoading) {
    return (
      <div className="px-4 py-2 rounded-lg bg-gray-700 text-gray-400">
        <span className="text-sm">Loading...</span>
      </div>
    )
  }

  return (
    <>
      <button
        onClick={() => setIsModalOpen(true)}
        className={`
          px-4 py-2 rounded-lg cursor-pointer transition-all
          hover:opacity-80 border
          flex items-center space-x-2
          ${textColorClass} ${bgColorClass}
        `}
        aria-label="Live profit and loss ticker. Click to see detailed breakdown"
        aria-live="polite"
      >
        {/* Direction arrow */}
        <span className="text-lg font-bold" aria-hidden="true">
          {directionArrow}
        </span>

        {/* P&L amount with animation */}
        <AnimatedNumber
          value={dailyPnL}
          format={formatCurrency}
          className="text-base font-semibold"
        />

        {/* Percentage */}
        <span className="text-sm opacity-90">({formattedPercentage})</span>

        {/* Mini sparkline */}
        {pnLHistory.length >= 2 && (
          <MiniSparkline data={pnLHistory} width={80} height={30} />
        )}
      </button>

      {/* Breakdown Modal */}
      <PnLBreakdownModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </>
  )
}

export default LivePnLTicker
