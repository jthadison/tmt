/**
 * Utility functions for formatting numbers, currencies, and percentages
 * Used across performance analytics components
 */

/**
 * Format currency values
 */
export function formatCurrency(
  value: number,
  currency: string = 'USD',
  locale: string = 'en-US',
  minimumFractionDigits: number = 2
): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits,
    maximumFractionDigits: minimumFractionDigits
  }).format(value)
}

/**
 * Format percentage values
 */
export function formatPercent(
  value: number,
  minimumFractionDigits: number = 2,
  locale: string = 'en-US'
): string {
  return new Intl.NumberFormat(locale, {
    style: 'percent',
    minimumFractionDigits,
    maximumFractionDigits: minimumFractionDigits
  }).format(value / 100)
}

/**
 * Format regular numbers
 */
export function formatNumber(
  value: number,
  minimumFractionDigits: number = 0,
  locale: string = 'en-US'
): string {
  return new Intl.NumberFormat(locale, {
    minimumFractionDigits,
    maximumFractionDigits: minimumFractionDigits
  }).format(value)
}

/**
 * Format large numbers with suffixes (K, M, B)
 */
export function formatLargeNumber(
  value: number,
  locale: string = 'en-US'
): string {
  const absValue = Math.abs(value)
  const sign = value < 0 ? '-' : ''

  if (absValue >= 1e9) {
    return sign + (absValue / 1e9).toFixed(1) + 'B'
  } else if (absValue >= 1e6) {
    return sign + (absValue / 1e6).toFixed(1) + 'M'
  } else if (absValue >= 1e3) {
    return sign + (absValue / 1e3).toFixed(1) + 'K'
  }
  
  return formatNumber(value, 0, locale)
}

/**
 * Format date ranges
 */
export function formatDateRange(
  start: Date,
  end: Date,
  locale: string = 'en-US'
): string {
  const startStr = start.toLocaleDateString(locale)
  const endStr = end.toLocaleDateString(locale)
  return `${startStr} - ${endStr}`
}

/**
 * Format duration in human readable format
 */
export function formatDuration(milliseconds: number): string {
  const seconds = Math.floor(milliseconds / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (days > 0) {
    return `${days}d ${hours % 24}h`
  } else if (hours > 0) {
    return `${hours}h ${minutes % 60}m`
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`
  } else {
    return `${seconds}s`
  }
}

/**
 * Format file size
 */
export function formatFileSize(bytes: number): string {
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  if (bytes === 0) return '0 B'
  
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
}

/**
 * Format risk level
 */
export function formatRiskLevel(score: number): {
  level: string
  color: string
  bgColor: string
} {
  if (score >= 80) return { level: 'Low', color: 'text-green-400', bgColor: 'bg-green-900/50' }
  if (score >= 60) return { level: 'Medium', color: 'text-yellow-400', bgColor: 'bg-yellow-900/50' }
  if (score >= 40) return { level: 'High', color: 'text-orange-400', bgColor: 'bg-orange-900/50' }
  return { level: 'Critical', color: 'text-red-400', bgColor: 'bg-red-900/50' }
}

/**
 * Format performance indicator
 */
export function formatPerformanceIndicator(
  value: number,
  type: 'currency' | 'percent' | 'number' = 'number'
): {
  formatted: string
  color: string
  trend: 'up' | 'down' | 'neutral'
} {
  let formatted: string
  let color: string
  let trend: 'up' | 'down' | 'neutral'

  switch (type) {
    case 'currency':
      formatted = formatCurrency(value)
      color = value > 0 ? 'text-green-400' : value < 0 ? 'text-red-400' : 'text-gray-400'
      trend = value > 0 ? 'up' : value < 0 ? 'down' : 'neutral'
      break
    case 'percent':
      formatted = formatPercent(value)
      color = value > 0 ? 'text-green-400' : value < 0 ? 'text-red-400' : 'text-gray-400'
      trend = value > 0 ? 'up' : value < 0 ? 'down' : 'neutral'
      break
    default:
      formatted = formatNumber(value, 2)
      color = value > 0 ? 'text-green-400' : value < 0 ? 'text-red-400' : 'text-gray-400'
      trend = value > 0 ? 'up' : value < 0 ? 'down' : 'neutral'
  }

  return { formatted, color, trend }
}

/**
 * Format confidence score
 */
export function formatConfidence(score: number): {
  label: string
  color: string
  bgColor: string
} {
  if (score >= 0.8) return { label: 'High', color: 'text-green-400', bgColor: 'bg-green-900/50' }
  if (score >= 0.6) return { label: 'Medium', color: 'text-yellow-400', bgColor: 'bg-yellow-900/50' }
  if (score >= 0.4) return { label: 'Low', color: 'text-orange-400', bgColor: 'bg-orange-900/50' }
  return { label: 'Very Low', color: 'text-red-400', bgColor: 'bg-red-900/50' }
}

/**
 * Format trading session
 */
export function formatTradingSession(hour: number): string {
  // Convert UTC hour to trading session
  if (hour >= 0 && hour < 9) return 'Asian'
  if (hour >= 9 && hour < 16) return 'London'
  if (hour >= 16 && hour < 21) return 'New York'
  if (hour >= 21 && hour < 24) return 'Sydney'
  return 'Off Hours'
}

/**
 * Format account type
 */
export function formatAccountType(type: string): {
  label: string
  color: string
  bgColor: string
} {
  switch (type.toLowerCase()) {
    case 'funded':
      return { label: 'Funded', color: 'text-green-400', bgColor: 'bg-green-900/50' }
    case 'challenge':
      return { label: 'Challenge', color: 'text-blue-400', bgColor: 'bg-blue-900/50' }
    case 'demo':
      return { label: 'Demo', color: 'text-gray-400', bgColor: 'bg-gray-900/50' }
    default:
      return { label: type, color: 'text-gray-400', bgColor: 'bg-gray-900/50' }
  }
}

/**
 * Truncate text with ellipsis
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength - 3) + '...'
}

/**
 * Format time ago
 */
export function formatTimeAgo(date: Date): string {
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  
  if (days > 0) return `${days}d ago`
  if (hours > 0) return `${hours}h ago`
  if (minutes > 0) return `${minutes}m ago`
  return `${seconds}s ago`
}