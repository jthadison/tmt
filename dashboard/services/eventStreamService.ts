/**
 * WebSocket event streaming service
 * Manages connections to backend services and provides fallback polling
 */

'use client'

type EventHandler = (event: SystemEvent) => void

export interface SystemEvent {
  type: string
  priority: 'critical' | 'warning' | 'success' | 'info'
  timestamp: string
  data: Record<string, unknown>
  source?: string
}

export interface EventStreamConfig {
  url: string
  reconnectDelay?: number
  maxReconnectAttempts?: number
  pollingInterval?: number
  enableFallback?: boolean
}

export class EventStreamService {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts: number
  private reconnectDelay: number
  private pollingInterval: number
  private enableFallback: boolean
  private url: string
  private handlers: Set<EventHandler> = new Set()
  private pollingTimer: NodeJS.Timeout | null = null
  private isConnected = false
  private shouldReconnect = true

  constructor(config: EventStreamConfig) {
    this.url = config.url
    this.reconnectDelay = config.reconnectDelay || 3000
    this.maxReconnectAttempts = config.maxReconnectAttempts || 10
    this.pollingInterval = config.pollingInterval || 30000 // 30 seconds for critical events
    this.enableFallback = config.enableFallback ?? true
  }

  /**
   * Connect to WebSocket event stream
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return // Already connected
    }

    try {
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        console.log('[EventStream] Connected to WebSocket')
        this.isConnected = true
        this.reconnectAttempts = 0
        this.stopPolling() // Stop fallback polling if active
      }

      this.ws.onmessage = (event) => {
        try {
          const data: SystemEvent = JSON.parse(event.data)
          this.notifyHandlers(data)
        } catch (error) {
          console.error('[EventStream] Failed to parse event:', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('[EventStream] WebSocket error:', error)
      }

      this.ws.onclose = () => {
        console.log('[EventStream] WebSocket closed')
        this.isConnected = false

        if (this.shouldReconnect) {
          this.handleReconnect()
        }
      }
    } catch (error) {
      console.error('[EventStream] Failed to create WebSocket:', error)
      this.handleReconnect()
    }
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect(): void {
    this.shouldReconnect = false
    this.stopPolling()

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    this.isConnected = false
  }

  /**
   * Subscribe to events
   */
  subscribe(handler: EventHandler): () => void {
    this.handlers.add(handler)

    // Return unsubscribe function
    return () => {
      this.handlers.delete(handler)
    }
  }

  /**
   * Check if currently connected
   */
  getConnectionStatus(): boolean {
    return this.isConnected
  }

  /**
   * Handle reconnection logic
   */
  private handleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[EventStream] Max reconnection attempts reached')

      if (this.enableFallback) {
        console.log('[EventStream] Starting fallback polling')
        this.startPolling()
      }
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.min(this.reconnectAttempts, 5) // Exponential backoff (capped)

    console.log(`[EventStream] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`)

    setTimeout(() => {
      if (this.shouldReconnect) {
        this.connect()
      }
    }, delay)
  }

  /**
   * Start polling fallback for critical events
   */
  private startPolling(): void {
    if (this.pollingTimer) {
      return // Already polling
    }

    console.log(`[EventStream] Starting polling (${this.pollingInterval}ms interval)`)

    const poll = async () => {
      try {
        // Poll critical endpoints only (circuit breaker status)
        const response = await fetch('http://localhost:8084/api/status')

        if (response.ok) {
          const data = await response.json()

          // Check if there are any critical events to notify about
          if (data.circuit_breaker_active) {
            const event: SystemEvent = {
              type: 'circuit_breaker.triggered',
              priority: 'critical',
              timestamp: new Date().toISOString(),
              data: data.circuit_breaker_details || {},
              source: 'polling'
            }
            this.notifyHandlers(event)
          }
        }
      } catch (error) {
        console.error('[EventStream] Polling failed:', error)
      }
    }

    // Initial poll
    poll()

    // Setup interval
    this.pollingTimer = setInterval(poll, this.pollingInterval)
  }

  /**
   * Stop polling fallback
   */
  private stopPolling(): void {
    if (this.pollingTimer) {
      clearInterval(this.pollingTimer)
      this.pollingTimer = null
      console.log('[EventStream] Stopped polling')
    }
  }

  /**
   * Notify all subscribed handlers
   */
  private notifyHandlers(event: SystemEvent): void {
    this.handlers.forEach(handler => {
      try {
        handler(event)
      } catch (error) {
        console.error('[EventStream] Handler error:', error)
      }
    })
  }
}

// Singleton instance for the orchestrator event stream
let orchestratorStream: EventStreamService | null = null

/**
 * Get or create the orchestrator event stream instance
 */
export function getOrchestratorEventStream(): EventStreamService {
  if (!orchestratorStream) {
    orchestratorStream = new EventStreamService({
      url: 'ws://localhost:8089/ws/events',
      reconnectDelay: 3000,
      maxReconnectAttempts: 10,
      pollingInterval: 30000,
      enableFallback: true
    })
  }
  return orchestratorStream
}
