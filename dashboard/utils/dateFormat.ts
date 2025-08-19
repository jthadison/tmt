/**
 * Date formatting utilities
 */

/**
 * Format a date to a relative time string (e.g., "2 minutes ago")
 */
export function formatDistanceToNow(date: Date | string): string {
  const now = new Date()
  const then = new Date(date)
  const seconds = Math.floor((now.getTime() - then.getTime()) / 1000)

  if (seconds < 5) {
    return 'just now'
  } else if (seconds < 60) {
    return `${seconds} seconds ago`
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60)
    return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`
  } else if (seconds < 86400) {
    const hours = Math.floor(seconds / 3600)
    return `${hours} hour${hours !== 1 ? 's' : ''} ago`
  } else {
    const days = Math.floor(seconds / 86400)
    return `${days} day${days !== 1 ? 's' : ''} ago`
  }
}

/**
 * Format a date to ISO string
 */
export function formatISO(date: Date | string): string {
  return new Date(date).toISOString()
}

/**
 * Format a date to local date string
 */
export function formatDate(date: Date | string): string {
  return new Date(date).toLocaleDateString()
}

/**
 * Format a date to local time string
 */
export function formatTime(date: Date | string): string {
  return new Date(date).toLocaleTimeString()
}

/**
 * Format a date to local date and time string
 */
export function formatDateTime(date: Date | string): string {
  const d = new Date(date)
  return `${d.toLocaleDateString()} ${d.toLocaleTimeString()}`
}

/**
 * Format milliseconds to human readable duration
 */
export function formatDuration(milliseconds: number): string {
  const seconds = Math.floor(milliseconds / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (days > 0) {
    return `${days}d ${hours % 24}h ${minutes % 60}m`
  } else if (hours > 0) {
    return `${hours}h ${minutes % 60}m ${seconds % 60}s`
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`
  } else {
    return `${seconds}s`
  }
}

/**
 * Get time zone offset string
 */
export function getTimeZoneOffset(): string {
  const offset = new Date().getTimezoneOffset()
  const hours = Math.floor(Math.abs(offset) / 60)
  const minutes = Math.abs(offset) % 60
  const sign = offset <= 0 ? '+' : '-'
  
  return `UTC${sign}${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`
}