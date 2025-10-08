/**
 * Reconnecting WebSocket with Increasing Intervals
 *
 * Implements automatic reconnection with increasing delays:
 * - Attempt 1: Immediate (0ms)
 * - Attempt 2: 1 second delay
 * - Attempt 3: 2 seconds delay
 * - Attempt 4: 5 seconds delay
 * - Attempt 5+: 10 seconds delay (max)
 *
 * Features:
 * - Message buffering during disconnection
 * - Automatic state synchronization on reconnect
 * - Fallback to polling after max attempts
 */

export type WebSocketStatus = 'connecting' | 'connected' | 'reconnecting' | 'disconnected' | 'failed'

export interface ReconnectingWebSocketOptions {
  maxReconnectAttempts?: number
  reconnectIntervals?: number[]
  enableMessageBuffer?: boolean
}

export class ReconnectingWebSocket {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempt = 0
  private maxReconnectAttempts: number
  private reconnectIntervals: number[]
  private messageBuffer: unknown[] = []
  private isIntentionallyClosed = false
  private reconnectTimeoutId: NodeJS.Timeout | null = null

  private onMessageCallback?: (data: unknown) => void
  private onOpenCallback?: () => void
  private onCloseCallback?: () => void
  private onErrorCallback?: (error: Event) => void
  private onReconnectCallback?: () => void
  private onFallbackCallback?: () => void
  private onStatusChangeCallback?: (status: WebSocketStatus) => void

  private currentStatus: WebSocketStatus = 'connecting'
  private enableMessageBuffer: boolean

  constructor(url: string, options: ReconnectingWebSocketOptions = {}) {
    this.url = url
    this.maxReconnectAttempts = options.maxReconnectAttempts ?? 5
    this.reconnectIntervals = options.reconnectIntervals ?? [0, 1000, 2000, 5000, 10000]
    this.enableMessageBuffer = options.enableMessageBuffer ?? true
    this.connect()
  }

  private setStatus(status: WebSocketStatus) {
    if (this.currentStatus !== status) {
      this.currentStatus = status
      this.onStatusChangeCallback?.(status)
    }
  }

  private connect() {
    if (this.isIntentionallyClosed) return

    try {
      this.setStatus(this.reconnectAttempt === 0 ? 'connecting' : 'reconnecting')
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.setStatus('connected')
        const wasReconnecting = this.reconnectAttempt > 0
        this.reconnectAttempt = 0

        this.onOpenCallback?.()

        // Send buffered messages
        if (this.enableMessageBuffer) {
          this.messageBuffer.forEach(msg => this.send(msg))
          this.messageBuffer = []
        }

        if (wasReconnecting) {
          this.onReconnectCallback?.()
        }
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.onMessageCallback?.(data)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.onErrorCallback?.(error)
      }

      this.ws.onclose = () => {
        console.log('WebSocket disconnected')
        this.setStatus('disconnected')
        this.onCloseCallback?.()

        if (this.isIntentionallyClosed) return

        // Attempt reconnection
        if (this.reconnectAttempt < this.maxReconnectAttempts) {
          const delay = this.reconnectIntervals[this.reconnectAttempt] || 10000
          console.log(
            `Reconnecting in ${delay}ms... (Attempt ${this.reconnectAttempt + 1}/${this.maxReconnectAttempts})`
          )

          this.reconnectTimeoutId = setTimeout(() => {
            this.reconnectAttempt++
            this.connect()
          }, delay)
        } else {
          console.error('Max reconnection attempts reached. Falling back to polling.')
          this.setStatus('failed')
          this.onFallbackCallback?.()
        }
      }
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      this.setStatus('failed')
    }
  }

  send(data: unknown) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      // Buffer message for retry
      if (this.enableMessageBuffer) {
        this.messageBuffer.push(data)
      }
    }
  }

  onMessage(callback: (data: unknown) => void) {
    this.onMessageCallback = callback
  }

  onOpen(callback: () => void) {
    this.onOpenCallback = callback
  }

  onClose(callback: () => void) {
    this.onCloseCallback = callback
  }

  onError(callback: (error: Event) => void) {
    this.onErrorCallback = callback
  }

  onReconnect(callback: () => void) {
    this.onReconnectCallback = callback
  }

  onFallback(callback: () => void) {
    this.onFallbackCallback = callback
  }

  onStatusChange(callback: (status: WebSocketStatus) => void) {
    this.onStatusChangeCallback = callback
  }

  getStatus(): WebSocketStatus {
    return this.currentStatus
  }

  close() {
    this.isIntentionallyClosed = true
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId)
      this.reconnectTimeoutId = null
    }
    this.ws?.close()
    this.setStatus('disconnected')
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}
