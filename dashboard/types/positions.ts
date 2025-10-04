/**
 * Position Type Definitions
 * Types for open positions, position management, and real-time position tracking
 */

/**
 * Position direction
 */
export type PositionDirection = 'long' | 'short'

/**
 * Position state for visual indicators
 */
export type PositionState = 'winning' | 'losing' | 'near_tp' | 'near_sl'

/**
 * Sort options for position grid
 */
export type PositionSortOption =
  | 'pnl-high'
  | 'pnl-low'
  | 'age-new'
  | 'age-old'
  | 'instrument'

/**
 * Individual position data structure
 */
export interface Position {
  /** Position ID */
  id: string
  /** Account ID */
  accountId: string
  /** Trading instrument (e.g., EUR_USD) */
  instrument: string
  /** Position direction (long/short) */
  direction: PositionDirection
  /** Position size in units */
  units: number
  /** Entry price */
  entryPrice: number
  /** Current market price */
  currentPrice: number
  /** Stop loss price (optional) */
  stopLoss?: number
  /** Take profit price (optional) */
  takeProfit?: number
  /** Unrealized P&L amount */
  unrealizedPL: number
  /** Unrealized P&L as percentage */
  unrealizedPLPercentage: number
  /** Position open timestamp */
  openTime: string
  /** Agent that generated the signal */
  agentSource: string

  // Calculated fields
  /** Human-readable position age (e.g., "2h 34m") */
  positionAge: string
  /** Progress to take profit (0-100%) */
  progressToTP: number
  /** Progress to stop loss (0-100%) */
  progressToSL: number
  /** Is position near take profit (within 10 pips) */
  isNearTP: boolean
  /** Is position near stop loss (within 10 pips) */
  isNearSL: boolean
}

/**
 * Raw position data from OANDA API
 */
export interface RawPosition {
  id: string
  instrument: string
  units: string
  price: string
  unrealizedPL: string
  openTime: string
  stopLoss?: string
  takeProfit?: string
  clientExtensions?: {
    agent?: string
  }
}

/**
 * Position modification request
 */
export interface PositionModifyRequest {
  /** Position ID */
  positionId: string
  /** New stop loss price */
  stopLoss?: number
  /** New take profit price */
  takeProfit?: number
}

/**
 * Position close request
 */
export interface PositionCloseRequest {
  /** Position ID */
  positionId: string
}

/**
 * Position close response
 */
export interface PositionCloseResponse {
  success: boolean
  message: string
  realizedPL?: number
}

/**
 * Position modify response
 */
export interface PositionModifyResponse {
  success: boolean
  message: string
  position?: Position
}

/**
 * WebSocket position update message
 */
export interface PositionUpdateMessage {
  type: 'positions.update'
  data: {
    position_id: string
    instrument: string
    current_price: number
    unrealized_pl: number
    timestamp: string
  }
}

/**
 * Position filter options
 */
export interface PositionFilters {
  /** Filter by agent sources */
  agentSources: string[]
  /** Filter by instrument types */
  instrumentTypes: string[]
}

/**
 * Positions hook state
 */
export interface UsePositionsState {
  /** All positions */
  positions: Position[]
  /** Is data loading */
  isLoading: boolean
  /** Error message if any */
  error: string | null
  /** Close position function */
  closePosition: (positionId: string) => Promise<void>
  /** Modify position function */
  modifyPosition: (positionId: string, stopLoss?: number, takeProfit?: number) => Promise<void>
  /** Refresh positions function */
  refreshPositions: () => Promise<void>
}
