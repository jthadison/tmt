/**
 * Trade Execution Service - WebSocket and API integration
 * Story 9.4: Trade Execution Monitoring Interface
 */

import { 
  TradeExecution, 
  ExecutionMetrics, 
  AggregatedMetrics,
  ExecutionAlert,
  ExecutionAlertRule,
  ExecutionUpdate,
  ExecutionFilter,
  ExecutionSort,
  ExecutionApiResponse,
  WebSocketStatus,
  ExecutionExportConfig,
  OrderLifecycle,
  TimeframePeriod
} from '@/types/tradeExecution'

/**
 * Configuration for the trade execution service
 */
interface TradeExecutionServiceConfig {
  apiUrl: string
  wsUrl: string
  apiKey: string
  reconnectAttempts: number
  reconnectDelay: number
  maxRetries: number
  timeout: number
}

/**
 * Rate limiter for API calls
 */
class RateLimiter {
  private requests: number[] = []
  private maxRequests: number
  private windowMs: number

  constructor(maxRequests: number = 100, windowMs: number = 60000) {
    this.maxRequests = maxRequests
    this.windowMs = windowMs
  }

  async acquire(): Promise<void> {
    const now = Date.now()
    this.requests = this.requests.filter(time => now - time < this.windowMs)

    if (this.requests.length >= this.maxRequests) {
      const oldestRequest = Math.min(...this.requests)
      const delay = this.windowMs - (now - oldestRequest)
      await new Promise(resolve => setTimeout(resolve, delay))
    }

    this.requests.push(now)
  }
}

/**
 * Mock data generator for development and testing
 */
class MockDataGenerator {
  private instruments = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'NZDUSD', 'USDCHF']
  private brokers = ['OANDA', 'MetaTrader4', 'MetaTrader5', 'cTrader', 'TradeLocker']
  private accounts = ['account-001', 'account-002', 'account-003', 'account-004']

  generateMockExecution(): TradeExecution {
    const id = `exec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    const orderId = `order_${Math.random().toString(36).substr(2, 9)}`
    const instrument = this.instruments[Math.floor(Math.random() * this.instruments.length)]
    const direction = Math.random() > 0.5 ? 'buy' : 'sell'
    const requestedSize = Math.floor(Math.random() * 100000) + 10000
    const requestedPrice = 1.0 + Math.random() * 0.5
    const slippage = (Math.random() - 0.5) * 0.0020 // ±2 pips
    const executedPrice = requestedPrice + slippage
    const broker = this.brokers[Math.floor(Math.random() * this.brokers.length)]
    const accountId = this.accounts[Math.floor(Math.random() * this.accounts.length)]

    const now = new Date()
    const createdTime = new Date(now.getTime() - Math.random() * 10000)
    const submittedTime = new Date(createdTime.getTime() + Math.random() * 1000)
    
    const statuses: any[] = ['filled', 'partial', 'pending', 'rejected']
    const status = statuses[Math.floor(Math.random() * statuses.length)]

    return {
      id,
      accountId,
      accountAlias: `Account ${accountId.slice(-3)}`,
      orderId,
      instrument,
      direction,
      requestedSize,
      executedSize: status === 'filled' ? requestedSize : 
                    status === 'partial' ? Math.floor(requestedSize * (0.3 + Math.random() * 0.4)) : 0,
      remainingSize: status === 'filled' ? 0 : 
                     status === 'partial' ? requestedSize - Math.floor(requestedSize * 0.7) : requestedSize,
      requestedPrice,
      averagePrice: status === 'filled' ? executedPrice : undefined,
      executedPrice: status !== 'pending' ? executedPrice : undefined,
      marketPrice: requestedPrice + (Math.random() - 0.5) * 0.001,
      slippage: Math.abs(slippage),
      slippagePercent: (Math.abs(slippage) / requestedPrice) * 100,
      status,
      timestamps: {
        created: createdTime,
        submitted: submittedTime,
        acknowledged: status !== 'pending' ? new Date(submittedTime.getTime() + Math.random() * 500) : undefined,
        partialFills: [],
        completed: status === 'filled' ? new Date(submittedTime.getTime() + Math.random() * 2000) : undefined,
        cancelled: status === 'rejected' ? new Date(submittedTime.getTime() + Math.random() * 1000) : undefined,
        lastUpdate: now
      },
      broker,
      platform: broker,
      fees: {
        commission: requestedSize * 0.00002,
        spread: requestedSize * 0.00001,
        total: requestedSize * 0.00003,
        currency: 'USD'
      },
      relatedOrders: [],
      tags: ['automated'],
      metadata: { signal_id: `signal_${Math.random().toString(36).substr(2, 6)}` },
      reasonCode: status === 'rejected' ? 'INSUFFICIENT_MARGIN' : undefined,
      reasonMessage: status === 'rejected' ? 'Insufficient margin to execute order' : undefined,
      venue: broker,
      priority: 'normal'
    }
  }

  generateMockMetrics(): AggregatedMetrics {
    const now = new Date()
    const hourAgo = new Date(now.getTime() - 3600000)

    const overall: ExecutionMetrics = {
      totalExecutions: Math.floor(Math.random() * 1000) + 500,
      successfulExecutions: Math.floor(Math.random() * 800) + 400,
      failedExecutions: Math.floor(Math.random() * 50) + 10,
      partialExecutions: Math.floor(Math.random() * 100) + 20,
      cancelledExecutions: Math.floor(Math.random() * 30) + 5,
      fillRate: 85 + Math.random() * 10,
      averageSlippage: Math.random() * 0.002,
      averageSlippagePercent: Math.random() * 0.1,
      averageExecutionSpeed: 150 + Math.random() * 300,
      rejectionRate: Math.random() * 5,
      fastestExecution: 50 + Math.random() * 100,
      slowestExecution: 1000 + Math.random() * 2000,
      medianExecutionSpeed: 200 + Math.random() * 200,
      totalVolumeTraded: Math.floor(Math.random() * 10000000) + 1000000,
      averageTradeSize: 50000 + Math.random() * 100000,
      totalFees: Math.random() * 10000,
      averageFees: Math.random() * 50,
      periodStart: hourAgo,
      periodEnd: now,
      executionsPerHour: Math.floor(Math.random() * 200) + 50
    }

    return {
      overall,
      byAccount: new Map(),
      byInstrument: new Map(),
      byBroker: new Map(),
      byStatus: new Map(),
      byHour: new Map(),
      timeframe: '1h',
      lastUpdate: now
    }
  }

  generateMockAlert(): ExecutionAlert {
    const types: any[] = ['execution_failed', 'high_slippage', 'partial_fill', 'execution_delay']
    const severities: any[] = ['warning', 'error', 'critical']
    
    return {
      id: `alert_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`,
      ruleId: 'rule_001',
      ruleName: 'High Slippage Alert',
      type: types[Math.floor(Math.random() * types.length)],
      severity: severities[Math.floor(Math.random() * severities.length)],
      title: 'Execution Alert',
      message: 'High slippage detected on EURUSD execution',
      executionId: `exec_${Math.random().toString(36).substr(2, 9)}`,
      accountId: this.accounts[Math.floor(Math.random() * this.accounts.length)],
      instrument: this.instruments[Math.floor(Math.random() * this.instruments.length)],
      broker: this.brokers[Math.floor(Math.random() * this.brokers.length)],
      timestamp: new Date(),
      acknowledged: Math.random() > 0.7,
      resolved: Math.random() > 0.8,
      metadata: {}
    }
  }
}

/**
 * Main trade execution service class
 */
export class TradeExecutionService {
  private config: TradeExecutionServiceConfig
  private rateLimiter: RateLimiter
  private mockGenerator: MockDataGenerator
  private ws: WebSocket | null = null
  private wsStatus: WebSocketStatus
  private reconnectAttempts = 0
  private eventListeners: Map<string, Function[]> = new Map()
  private isConnecting = false

  constructor(config: Partial<TradeExecutionServiceConfig> = {}) {
    this.config = {
      apiUrl: process.env.NEXT_PUBLIC_TRADE_API_URL || 'http://localhost:8080/api',
      wsUrl: process.env.NEXT_PUBLIC_TRADE_WS_URL || 'ws://localhost:8080/ws',
      apiKey: process.env.NEXT_PUBLIC_TRADE_API_KEY || 'demo-key',
      reconnectAttempts: 5,
      reconnectDelay: 3000,
      maxRetries: 3,
      timeout: 10000,
      ...config
    }

    this.rateLimiter = new RateLimiter(100, 60000)
    this.mockGenerator = new MockDataGenerator()
    this.wsStatus = {
      connected: false,
      url: this.config.wsUrl,
      reconnectAttempts: 0
    }

    this.initializeWebSocket()
  }

  /**
   * Initialize WebSocket connection for real-time updates
   */
  private initializeWebSocket(): void {
    if (this.isConnecting || this.ws?.readyState === WebSocket.CONNECTING) {
      return
    }

    this.isConnecting = true

    try {
      this.ws = new WebSocket(this.config.wsUrl)
      
      this.ws.onopen = () => {
        console.log('Trade execution WebSocket connected')
        this.isConnecting = false
        this.reconnectAttempts = 0
        this.wsStatus = {
          ...this.wsStatus,
          connected: true,
          reconnectAttempts: 0,
          error: undefined
        }
        this.emit('ws:connected', this.wsStatus)
      }

      this.ws.onmessage = (event) => {
        try {
          const update: ExecutionUpdate = JSON.parse(event.data)
          this.wsStatus.lastMessage = new Date()
          this.handleWebSocketUpdate(update)
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      this.ws.onclose = () => {
        console.log('Trade execution WebSocket disconnected')
        this.isConnecting = false
        this.wsStatus.connected = false
        this.emit('ws:disconnected', this.wsStatus)
        this.attemptReconnect()
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.isConnecting = false
        this.wsStatus = {
          ...this.wsStatus,
          connected: false,
          error: 'Connection error'
        }
        this.emit('ws:error', { error, status: this.wsStatus })
      }

    } catch (error) {
      console.error('Failed to initialize WebSocket:', error)
      this.isConnecting = false
      this.wsStatus.error = 'Failed to initialize connection'
    }
  }

  /**
   * Handle WebSocket updates
   */
  private handleWebSocketUpdate(update: ExecutionUpdate): void {
    switch (update.type) {
      case 'execution_created':
      case 'execution_updated':
      case 'execution_completed':
        if (update.execution) {
          this.emit('execution:update', update.execution)
        }
        break
      case 'alert_triggered':
        if (update.alert) {
          this.emit('alert:new', update.alert)
        }
        break
    }
    this.emit('update', update)
  }

  /**
   * Attempt to reconnect WebSocket
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.config.reconnectAttempts) {
      console.log('Max reconnection attempts reached')
      return
    }

    this.reconnectAttempts++
    this.wsStatus.reconnectAttempts = this.reconnectAttempts

    setTimeout(() => {
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.config.reconnectAttempts})`)
      this.initializeWebSocket()
    }, this.config.reconnectDelay * this.reconnectAttempts)
  }

  /**
   * Event listener management
   */
  on(event: string, callback: Function): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, [])
    }
    this.eventListeners.get(event)!.push(callback)
  }

  off(event: string, callback: Function): void {
    const listeners = this.eventListeners.get(event)
    if (listeners) {
      const index = listeners.indexOf(callback)
      if (index > -1) {
        listeners.splice(index, 1)
      }
    }
  }

  private emit(event: string, data: any): void {
    const listeners = this.eventListeners.get(event) || []
    listeners.forEach(callback => {
      try {
        callback(data)
      } catch (error) {
        console.error('Error in event listener:', error)
      }
    })
  }

  /**
   * API Methods
   */

  /**
   * Get trade executions with filtering and pagination
   */
  async getExecutions(
    filter: ExecutionFilter = {},
    sort: ExecutionSort = { field: 'timestamp', direction: 'desc' },
    page = 1,
    pageSize = 50
  ): Promise<ExecutionApiResponse<TradeExecution[]>> {
    await this.rateLimiter.acquire()

    try {
      // In production, this would make actual API call
      // For demo, return mock data
      const mockExecutions = Array.from({ length: pageSize }, () => 
        this.mockGenerator.generateMockExecution()
      )

      return {
        success: true,
        data: mockExecutions,
        timestamp: new Date(),
        requestId: `req_${Date.now()}`,
        pagination: {
          page,
          pageSize,
          total: 1000,
          hasNext: page < 20,
          hasPrevious: page > 1
        }
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date(),
        requestId: `req_${Date.now()}`
      }
    }
  }

  /**
   * Get single execution by ID
   */
  async getExecution(id: string): Promise<ExecutionApiResponse<TradeExecution>> {
    await this.rateLimiter.acquire()

    try {
      const mockExecution = this.mockGenerator.generateMockExecution()
      mockExecution.id = id

      return {
        success: true,
        data: mockExecution,
        timestamp: new Date(),
        requestId: `req_${Date.now()}`
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date(),
        requestId: `req_${Date.now()}`
      }
    }
  }

  /**
   * Get aggregated execution metrics
   */
  async getMetrics(
    timeframe: TimeframePeriod = '1h',
    accounts?: string[],
    instruments?: string[]
  ): Promise<ExecutionApiResponse<AggregatedMetrics>> {
    await this.rateLimiter.acquire()

    try {
      const mockMetrics = this.mockGenerator.generateMockMetrics()
      mockMetrics.timeframe = timeframe

      return {
        success: true,
        data: mockMetrics,
        timestamp: new Date(),
        requestId: `req_${Date.now()}`
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date(),
        requestId: `req_${Date.now()}`
      }
    }
  }

  /**
   * Get execution alerts
   */
  async getAlerts(
    filter: { acknowledged?: boolean; resolved?: boolean } = {}
  ): Promise<ExecutionApiResponse<ExecutionAlert[]>> {
    await this.rateLimiter.acquire()

    try {
      const mockAlerts = Array.from({ length: 10 }, () =>
        this.mockGenerator.generateMockAlert()
      )

      return {
        success: true,
        data: mockAlerts,
        timestamp: new Date(),
        requestId: `req_${Date.now()}`
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date(),
        requestId: `req_${Date.now()}`
      }
    }
  }

  /**
   * Acknowledge alert
   */
  async acknowledgeAlert(alertId: string): Promise<ExecutionApiResponse<boolean>> {
    await this.rateLimiter.acquire()

    try {
      // Mock API call
      return {
        success: true,
        data: true,
        timestamp: new Date(),
        requestId: `req_${Date.now()}`
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date(),
        requestId: `req_${Date.now()}`
      }
    }
  }

  /**
   * Get order lifecycle tracking
   */
  async getOrderLifecycle(orderId: string): Promise<ExecutionApiResponse<OrderLifecycle>> {
    await this.rateLimiter.acquire()

    try {
      // Mock order lifecycle data
      const lifecycle: OrderLifecycle = {
        orderId,
        executionId: `exec_${orderId}`,
        stages: [
          {
            id: 'created',
            name: 'Order Created',
            timestamp: new Date(Date.now() - 5000),
            status: 'completed',
            expected: true,
            latencyMs: 0
          },
          {
            id: 'submitted',
            name: 'Submitted to Broker',
            timestamp: new Date(Date.now() - 4000),
            status: 'completed',
            expected: true,
            latencyMs: 1000
          },
          {
            id: 'acknowledged',
            name: 'Broker Acknowledgment',
            timestamp: new Date(Date.now() - 3500),
            status: 'completed',
            expected: true,
            latencyMs: 500
          },
          {
            id: 'executed',
            name: 'Order Executed',
            timestamp: new Date(Date.now() - 2000),
            status: 'completed',
            expected: true,
            latencyMs: 1500
          }
        ],
        totalDuration: 3000,
        currentStage: 'executed',
        isComplete: true,
        hasErrors: false,
        warnings: [],
        expectedStages: ['created', 'submitted', 'acknowledged', 'executed'],
        actualStages: ['created', 'submitted', 'acknowledged', 'executed']
      }

      return {
        success: true,
        data: lifecycle,
        timestamp: new Date(),
        requestId: `req_${Date.now()}`
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date(),
        requestId: `req_${Date.now()}`
      }
    }
  }

  /**
   * Export execution data
   */
  async exportExecutions(config: ExecutionExportConfig): Promise<ExecutionApiResponse<string>> {
    await this.rateLimiter.acquire()

    try {
      // Mock export URL
      const exportUrl = `/api/exports/executions_${Date.now()}.${config.format}`

      return {
        success: true,
        data: exportUrl,
        timestamp: new Date(),
        requestId: `req_${Date.now()}`
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date(),
        requestId: `req_${Date.now()}`
      }
    }
  }

  /**
   * Get WebSocket status
   */
  getWebSocketStatus(): WebSocketStatus {
    return { ...this.wsStatus }
  }

  /**
   * Manually reconnect WebSocket
   */
  reconnect(): void {
    if (this.ws) {
      this.ws.close()
    }
    this.reconnectAttempts = 0
    this.initializeWebSocket()
  }

  /**
   * Start mock data simulation for development
   */
  startMockDataSimulation(): void {
    if (process.env.NODE_ENV === 'development') {
      // Simulate periodic execution updates
      setInterval(() => {
        const mockExecution = this.mockGenerator.generateMockExecution()
        this.emit('execution:update', mockExecution)
      }, 3000)

      // Simulate periodic alerts
      setInterval(() => {
        if (Math.random() > 0.8) {
          const mockAlert = this.mockGenerator.generateMockAlert()
          this.emit('alert:new', mockAlert)
        }
      }, 10000)
    }
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.eventListeners.clear()
  }
}

export default TradeExecutionService