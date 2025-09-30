/**
 * Configuration for real-time update intervals
 * All intervals are in milliseconds
 */

export interface IntervalConfig {
  // Mock account data simulation updates - how often P&L and positions change (ms)
  accountDataUpdate: number

  // Main dashboard overview grid auto-refresh - AccountOverviewGrid component (seconds)
  dashboardRefresh: number

  // WebSocket keep-alive heartbeat messages to maintain connection (ms)
  websocketHeartbeat: number

  // WebSocket auto-reconnection delay on connection loss (ms, with exponential backoff)
  websocketReconnect: number

  // OANDA live account data polling - real trading account updates (ms)
  oandaDataRefresh: number
}

/**
 * Default interval values
 */
const DEFAULT_INTERVALS: IntervalConfig = {
  accountDataUpdate: 5000,    // 5 seconds - Mock account P&L simulation updates
  dashboardRefresh: 30,       // 30 seconds - Main dashboard auto-refresh
  websocketHeartbeat: 30000,  // 30 seconds - Keep-alive heartbeat messages
  websocketReconnect: 5000,   // 5 seconds - Auto-reconnection delay (with backoff)
  oandaDataRefresh: 10000,    // 10 seconds - OANDA live account polling
}

/**
 * Parse environment variable as integer with fallback
 */
function parseEnvInt(envVar: string | undefined, defaultValue: number): number {
  if (!envVar) return defaultValue
  const parsed = parseInt(envVar, 10)
  return isNaN(parsed) ? defaultValue : parsed
}

/**
 * Get interval configuration from environment variables with fallbacks
 */
export function getIntervalConfig(): IntervalConfig {
  return {
    accountDataUpdate: parseEnvInt(
      process.env.NEXT_PUBLIC_ACCOUNT_UPDATE_INTERVAL,  // How often mock account P&L changes (ms)
      DEFAULT_INTERVALS.accountDataUpdate
    ),
    dashboardRefresh: parseEnvInt(
      process.env.NEXT_PUBLIC_DASHBOARD_REFRESH_INTERVAL,  // Dashboard auto-refresh interval (seconds)
      DEFAULT_INTERVALS.dashboardRefresh
    ),
    websocketHeartbeat: parseEnvInt(
      process.env.NEXT_PUBLIC_WS_HEARTBEAT_INTERVAL,  // WebSocket keep-alive ping frequency (ms)
      DEFAULT_INTERVALS.websocketHeartbeat
    ),
    websocketReconnect: parseEnvInt(
      process.env.NEXT_PUBLIC_WS_RECONNECT_INTERVAL,  // Delay before reconnecting lost connection (ms)
      DEFAULT_INTERVALS.websocketReconnect
    ),
    oandaDataRefresh: parseEnvInt(
      process.env.NEXT_PUBLIC_OANDA_REFRESH_INTERVAL,  // OANDA live data refresh rate (ms)
      DEFAULT_INTERVALS.oandaDataRefresh
    ),
  }
}

/**
 * Singleton instance of interval configuration
 */
export const intervalConfig = getIntervalConfig()