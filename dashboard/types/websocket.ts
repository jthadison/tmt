/**
 * WebSocket message types and interfaces
 */

export enum MessageType {
  ACCOUNT_UPDATE = 'account_update',
  POSITION_UPDATE = 'position_update',
  PRICE_UPDATE = 'price_update',
  SYSTEM_STATUS = 'system_status',
  HEARTBEAT = 'heartbeat',
}

export interface WebSocketMessage {
  type: MessageType
  data: any
  timestamp: string
  correlation_id: string
}

export interface AccountUpdate {
  account_id: string
  balance: number
  equity: number
  margin: number
  free_margin: number
  margin_level: number
}

export interface PositionUpdate {
  position_id: string
  account_id: string
  symbol: string
  side: 'buy' | 'sell'
  volume: number
  open_price: number
  current_price: number
  profit: number
  swap: number
  commission: number
}

export interface PriceUpdate {
  symbol: string
  bid: number
  ask: number
  timestamp: string
}

export interface SystemStatus {
  service: string
  status: 'active' | 'inactive' | 'warning' | 'error'
  message?: string
  last_updated: string
}

export enum ConnectionStatus {
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  RECONNECTING = 'reconnecting',
  ERROR = 'error',
}