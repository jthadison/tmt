/**
 * Real-time state management store
 * Handles WebSocket messages and maintains application state
 */

import { WebSocketMessage, MessageType, AccountUpdate, PositionUpdate, PriceUpdate, SystemStatus } from '@/types/websocket'
import { Account } from '@/types/account'

export interface RealTimeState {
  accounts: Map<string, Account>
  positions: Map<string, PositionUpdate>
  prices: Map<string, PriceUpdate>
  systemStatus: Map<string, SystemStatus>
  lastUpdate: Date | null
  connectionStatus: 'connected' | 'disconnected' | 'error'
}

export type StateUpdateCallback = (state: RealTimeState) => void
export type MessageHandler = (message: WebSocketMessage) => void

class RealTimeStore {
  private state: RealTimeState
  private subscribers: Set<StateUpdateCallback>
  private messageHandlers: Map<MessageType, Set<MessageHandler>>
  private updateQueue: WebSocketMessage[]
  private isProcessing: boolean
  private batchTimeout: NodeJS.Timeout | null

  constructor() {
    this.state = {
      accounts: new Map(),
      positions: new Map(),
      prices: new Map(),
      systemStatus: new Map(),
      lastUpdate: null,
      connectionStatus: 'disconnected'
    }
    
    this.subscribers = new Set()
    this.messageHandlers = new Map()
    this.updateQueue = []
    this.isProcessing = false
    this.batchTimeout = null
  }

  /**
   * Subscribe to state updates
   */
  subscribe(callback: StateUpdateCallback): () => void {
    this.subscribers.add(callback)
    // Send current state immediately
    callback(this.getState())
    
    return () => {
      this.subscribers.delete(callback)
    }
  }

  /**
   * Register a message handler for specific message type
   */
  onMessage(type: MessageType, handler: MessageHandler): () => void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, new Set())
    }
    
    this.messageHandlers.get(type)!.add(handler)
    
    return () => {
      this.messageHandlers.get(type)?.delete(handler)
    }
  }

  /**
   * Process incoming WebSocket message
   */
  processMessage(message: WebSocketMessage) {
    // Add to queue for batch processing
    this.updateQueue.push(message)
    
    // Process immediately if not batching
    if (!this.batchTimeout) {
      this.batchTimeout = setTimeout(() => {
        this.processBatch()
      }, 50) // 50ms batching window
    }
  }

  /**
   * Process batch of messages
   */
  private processBatch() {
    if (this.isProcessing || this.updateQueue.length === 0) {
      return
    }
    
    this.isProcessing = true
    const messages = [...this.updateQueue]
    this.updateQueue = []
    
    try {
      // Process each message
      messages.forEach(message => {
        this.handleMessage(message)
        
        // Call registered handlers
        const handlers = this.messageHandlers.get(message.type)
        if (handlers) {
          handlers.forEach(handler => {
            try {
              handler(message)
            } catch (error) {
              console.error('Error in message handler:', error)
            }
          })
        }
      })
      
      // Update last update time
      this.state = {
        ...this.state,
        lastUpdate: new Date()
      }
      
      // Notify subscribers
      this.notifySubscribers()
      
    } finally {
      this.isProcessing = false
      this.batchTimeout = null
    }
  }

  /**
   * Handle specific message types
   */
  private handleMessage(message: WebSocketMessage) {
    switch (message.type) {
      case MessageType.ACCOUNT_UPDATE:
        this.handleAccountUpdate(message.data as AccountUpdate)
        break
        
      case MessageType.POSITION_UPDATE:
        this.handlePositionUpdate(message.data as PositionUpdate)
        break
        
      case MessageType.PRICE_UPDATE:
        this.handlePriceUpdate(message.data as PriceUpdate)
        break
        
      case MessageType.SYSTEM_STATUS:
        this.handleSystemStatus(message.data as SystemStatus)
        break
        
      case MessageType.HEARTBEAT:
        // Heartbeat messages are handled at connection level
        break
        
      default:
        console.warn('Unknown message type:', message.type)
    }
  }

  /**
   * Handle account update
   */
  private handleAccountUpdate(update: AccountUpdate) {
    const existing = this.state.accounts.get(update.account_id)
    
    if (existing) {
      // Update existing account
      const updated: Account = {
        ...existing,
        balance: update.balance,
        equity: update.equity,
        margin: update.margin,
        freeMargin: update.free_margin,
        marginLevel: update.margin_level,
        lastUpdate: new Date().toISOString()
      }
      
      this.state.accounts.set(update.account_id, updated)
    } else {
      // Create new account entry (partial data)
      const newAccount: Account = {
        id: update.account_id,
        name: `Account ${update.account_id}`,
        broker: 'Unknown',
        status: this.determineAccountStatus(update),
        balance: update.balance,
        equity: update.equity,
        margin: update.margin,
        freeMargin: update.free_margin,
        marginLevel: update.margin_level,
        pnl: {
          daily: 0,
          weekly: 0,
          monthly: 0,
          total: 0
        },
        positions: {
          active: 0,
          pending: 0,
          total: 0
        },
        drawdown: {
          current: 0,
          max: 0,
          daily: 0
        },
        lastUpdate: new Date().toISOString()
      }
      
      this.state.accounts.set(update.account_id, newAccount)
    }
  }

  /**
   * Determine account status based on metrics
   */
  private determineAccountStatus(update: AccountUpdate): 'healthy' | 'warning' | 'danger' | 'inactive' {
    if (update.margin_level < 100) {
      return 'danger'
    } else if (update.margin_level < 200) {
      return 'warning'
    } else {
      return 'healthy'
    }
  }

  /**
   * Handle position update
   */
  private handlePositionUpdate(update: PositionUpdate) {
    this.state.positions.set(update.position_id, update)
    
    // Update account position count
    const account = this.state.accounts.get(update.account_id)
    if (account) {
      const positions = Array.from(this.state.positions.values())
        .filter(p => p.account_id === update.account_id)
      
      account.positions.active = positions.length
      this.state.accounts.set(update.account_id, account)
    }
  }

  /**
   * Handle price update
   */
  private handlePriceUpdate(update: PriceUpdate) {
    this.state.prices.set(update.symbol, update)
  }

  /**
   * Handle system status update
   */
  private handleSystemStatus(status: SystemStatus) {
    this.state.systemStatus.set(status.service, status)
  }

  /**
   * Update connection status
   */
  setConnectionStatus(status: 'connected' | 'disconnected' | 'error') {
    if (this.state.connectionStatus !== status) {
      this.state = {
        ...this.state,
        connectionStatus: status
      }
      this.notifySubscribers()
    }
  }

  /**
   * Get current state
   */
  getState(): RealTimeState {
    return {
      ...this.state,
      accounts: new Map(this.state.accounts),
      positions: new Map(this.state.positions),
      prices: new Map(this.state.prices),
      systemStatus: new Map(this.state.systemStatus)
    }
  }

  /**
   * Get specific account
   */
  getAccount(accountId: string): Account | undefined {
    return this.state.accounts.get(accountId)
  }

  /**
   * Get account positions
   */
  getAccountPositions(accountId: string): PositionUpdate[] {
    return Array.from(this.state.positions.values())
      .filter(p => p.account_id === accountId)
  }

  /**
   * Clear all state
   */
  clear() {
    this.state = {
      accounts: new Map(),
      positions: new Map(),
      prices: new Map(),
      systemStatus: new Map(),
      lastUpdate: null,
      connectionStatus: 'disconnected'
    }
    this.updateQueue = []
    this.notifySubscribers()
  }

  /**
   * Notify all subscribers of state change
   */
  private notifySubscribers() {
    const state = this.getState()
    this.subscribers.forEach(callback => {
      try {
        callback(state)
      } catch (error) {
        console.error('Error in state subscriber:', error)
      }
    })
  }
}

// Singleton instance
let storeInstance: RealTimeStore | null = null

/**
 * Get or create store instance
 */
export function getRealTimeStore(): RealTimeStore {
  if (!storeInstance) {
    storeInstance = new RealTimeStore()
  }
  return storeInstance
}

/**
 * React hook for using real-time store
 */
import { useEffect, useState } from 'react'

export function useRealTimeStore() {
  const [state, setState] = useState<RealTimeState>(() => 
    getRealTimeStore().getState()
  )
  
  useEffect(() => {
    const store = getRealTimeStore()
    const unsubscribe = store.subscribe(setState)
    
    return unsubscribe
  }, [])
  
  return {
    state,
    store: getRealTimeStore()
  }
}

export default RealTimeStore