/**
 * Lib module exports
 * Centralized exports for better module resolution in Docker builds
 */

// Re-export everything from oanda-client
export * from './oanda-client'
export { getOandaClient } from './oanda-client'

// Re-export everything from tradingConfigService
export * from './tradingConfigService'
export { tradingConfigService } from './tradingConfigService'

// Re-export everything from instruments
export * from './instruments'