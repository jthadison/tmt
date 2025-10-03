/**
 * Currency formatting utilities
 */

/**
 * Format number as currency with symbol and sign
 */
export function formatCurrency(
  amount: number,
  currency: string = 'USD',
  showSign: boolean = false
): string {
  const formatter = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })

  const formatted = formatter.format(Math.abs(amount))

  if (showSign) {
    if (amount > 0) return `+${formatted}`
    if (amount < 0) return `-${formatted}`
  } else if (amount < 0) {
    return `-${formatted.replace('-', '')}`
  }

  return formatted
}

/**
 * Format percentage with sign
 */
export function formatPercentage(
  value: number,
  decimals: number = 2,
  showSign: boolean = true
): string {
  const sign = showSign && value > 0 ? '+' : ''
  return `${sign}${value.toFixed(decimals)}%`
}

/**
 * Format large numbers with abbreviations (K, M, B)
 */
export function formatCompactNumber(num: number): string {
  const abs = Math.abs(num)
  const sign = num < 0 ? '-' : ''

  if (abs >= 1_000_000_000) {
    return `${sign}${(abs / 1_000_000_000).toFixed(1)}B`
  }
  if (abs >= 1_000_000) {
    return `${sign}${(abs / 1_000_000).toFixed(1)}M`
  }
  if (abs >= 1_000) {
    return `${sign}${(abs / 1_000).toFixed(1)}K`
  }
  return `${sign}${abs.toFixed(0)}`
}

/**
 * Get color class based on P&L value
 */
export function getPnLColorClass(value: number): string {
  if (value > 0) return 'text-green-400'
  if (value < 0) return 'text-red-400'
  return 'text-gray-400'
}

/**
 * Get background color class based on P&L value
 */
export function getPnLBackgroundClass(value: number): string {
  if (value > 0) return 'bg-green-500/10 border-green-500/20'
  if (value < 0) return 'bg-red-500/10 border-red-500/20'
  return 'bg-gray-700'
}
