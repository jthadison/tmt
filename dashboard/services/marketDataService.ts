/**
 * Market Data Service
 * Story 9.4: Service layer for market data retrieval, real-time subscriptions, and TimescaleDB integration
 * 
 * PERFORMANCE: Optimized for <100ms data updates and efficient caching
 */

import {
  MarketInstrument,
  OHLCV,
  PriceTick,
  ChartTimeframe,
  MarketDataRequest,
  MarketDataResponse,
  RealtimeSubscription,
  TechnicalIndicator,
  WyckoffPattern,
  AgentAnnotation,
  MarketDataServiceResponse
} from '@/types/marketData'

/**
 * Market data cache configuration
 */
interface CacheConfig {
  /** Cache TTL in milliseconds */
  ttl: number
  /** Maximum cache size */
  maxSize: number
  /** Enable compression */
  compression: boolean
}

/**
 * Market data service configuration
 */
interface MarketDataServiceConfig {
  /** TimescaleDB connection settings */
  database: {
    host: string
    port: number
    database: string
    username: string
    password: string
  }
  /** WebSocket settings for real-time data */
  websocket: {
    url: string
    reconnectAttempts: number
    heartbeatInterval: number
  }
  /** Cache configuration */
  cache: CacheConfig
  /** Performance settings */
  performance: {
    maxConcurrentRequests: number
    requestTimeout: number
    batchSize: number
  }
}

/**
 * Default service configuration
 */
const DEFAULT_CONFIG: MarketDataServiceConfig = {
  database: {
    host: process.env.TIMESCALEDB_HOST || 'localhost',
    port: parseInt(process.env.TIMESCALEDB_PORT || '5432'),
    database: process.env.TIMESCALEDB_DATABASE || 'trading_system',
    username: process.env.TIMESCALEDB_USERNAME || 'trading_user',
    password: process.env.TIMESCALEDB_PASSWORD || ''
  },
  websocket: {
    url: process.env.MARKET_DATA_WS_URL || 'wss://api.market-data.com/stream',
    reconnectAttempts: 5,
    heartbeatInterval: 30000
  },
  cache: {
    ttl: 30000, // 30 seconds
    maxSize: 1000,
    compression: true
  },
  performance: {
    maxConcurrentRequests: 10,
    requestTimeout: 5000,
    batchSize: 1000
  }
}

/**
 * Market data cache implementation
 */
class MarketDataCache {
  private cache = new Map<string, { data: any; timestamp: number; ttl: number }>()
  private readonly maxSize: number
  private readonly compression: boolean

  constructor(config: CacheConfig) {
    this.maxSize = config.maxSize
    this.compression = config.compression
  }

  /**
   * Store data in cache
   */
  set<T>(key: string, data: T, ttl?: number): void {
    // Implement LRU eviction if cache is full
    if (this.cache.size >= this.maxSize) {
      const oldestKey = this.cache.keys().next().value
      this.cache.delete(oldestKey)
    }

    this.cache.set(key, {
      data: this.compression ? this.compress(data) : data,
      timestamp: Date.now(),
      ttl: ttl || DEFAULT_CONFIG.cache.ttl
    })
  }

  /**
   * Retrieve data from cache
   */
  get<T>(key: string): T | null {
    const item = this.cache.get(key)
    if (!item) return null

    // Check if item has expired
    if (Date.now() - item.timestamp > item.ttl) {
      this.cache.delete(key)
      return null
    }

    return this.compression ? this.decompress(item.data) : item.data
  }

  /**
   * Clear expired cache entries
   */
  cleanup(): void {
    const now = Date.now()
    for (const [key, item] of this.cache.entries()) {
      if (now - item.timestamp > item.ttl) {
        this.cache.delete(key)
      }
    }
  }

  /**
   * Simple compression (placeholder for actual implementation)
   */
  private compress(data: any): string {
    return JSON.stringify(data)
  }

  /**
   * Simple decompression
   */
  private decompress(data: string): any {
    return JSON.parse(data)
  }
}

/**
 * Market Data Service Implementation
 */
export class MarketDataService {
  private config: MarketDataServiceConfig
  private cache: MarketDataCache
  private websocket: WebSocket | null = null
  private subscriptions = new Map<string, RealtimeSubscription>()
  private reconnectAttempts = 0
  private heartbeatInterval: NodeJS.Timeout | null = null

  constructor(config?: Partial<MarketDataServiceConfig>) {
    this.config = { ...DEFAULT_CONFIG, ...config }
    this.cache = new MarketDataCache(this.config.cache)
    
    // Setup cache cleanup interval
    setInterval(() => this.cache.cleanup(), 60000) // Cleanup every minute
  }

  /**
   * Get available market instruments
   */
  async getInstruments(): Promise<MarketDataServiceResponse<MarketInstrument[]>> {
    const cacheKey = 'instruments'
    const cached = this.cache.get<MarketInstrument[]>(cacheKey)
    
    if (cached) {
      return {
        data: cached,
        status: 'success',
        metadata: {
          timestamp: Date.now(),
          latency: 0,
          source: 'cache',
          cached: true
        }
      }
    }

    try {
      const startTime = Date.now()
      
      // Mock implementation - replace with actual TimescaleDB query
      const instruments: MarketInstrument[] = [
        {
          symbol: 'EUR_USD',
          displayName: 'EUR/USD',
          type: 'forex',
          baseCurrency: 'EUR',
          quoteCurrency: 'USD',
          pipLocation: -4,
          tradingHours: [
            {
              name: 'Sydney',
              startTime: '22:00',
              endTime: '07:00',
              daysActive: [1, 2, 3, 4, 5],
              isActive: false
            },
            {
              name: 'London',
              startTime: '08:00',
              endTime: '17:00',
              daysActive: [1, 2, 3, 4, 5],
              isActive: true
            },
            {
              name: 'New York',
              startTime: '13:00',
              endTime: '22:00',
              daysActive: [1, 2, 3, 4, 5],
              isActive: true
            }
          ],
          isActive: true,
          averageSpread: 0.8,
          minTradeSize: 1000,
          maxTradeSize: 10000000
        },
        {
          symbol: 'GBP_USD',
          displayName: 'GBP/USD',
          type: 'forex',
          baseCurrency: 'GBP',
          quoteCurrency: 'USD',
          pipLocation: -4,
          tradingHours: [
            {
              name: 'London',
              startTime: '08:00',
              endTime: '17:00',
              daysActive: [1, 2, 3, 4, 5],
              isActive: true
            }
          ],
          isActive: true,
          averageSpread: 1.2,
          minTradeSize: 1000,
          maxTradeSize: 10000000
        },
        {
          symbol: 'USD_JPY',
          displayName: 'USD/JPY',
          type: 'forex',
          baseCurrency: 'USD',
          quoteCurrency: 'JPY',
          pipLocation: -2,
          tradingHours: [
            {
              name: 'Tokyo',
              startTime: '00:00',
              endTime: '09:00',
              daysActive: [1, 2, 3, 4, 5],
              isActive: false
            }
          ],
          isActive: true,
          averageSpread: 0.9,
          minTradeSize: 1000,
          maxTradeSize: 10000000
        }
      ]

      this.cache.set(cacheKey, instruments, 300000) // Cache for 5 minutes

      return {
        data: instruments,
        status: 'success',
        metadata: {
          timestamp: Date.now(),
          latency: Date.now() - startTime,
          source: 'database',
          cached: false
        }
      }
    } catch (error) {
      return {
        data: [],
        status: 'error',
        error: error instanceof Error ? error.message : 'Unknown error',
        metadata: {
          timestamp: Date.now(),
          latency: 0,
          source: 'database',
          cached: false
        }
      }
    }
  }

  /**
   * Get historical market data
   */
  async getHistoricalData(request: MarketDataRequest): Promise<MarketDataServiceResponse<MarketDataResponse>> {
    const cacheKey = `historical_${request.instrument}_${request.timeframe}_${request.from.getTime()}_${request.to.getTime()}`
    const cached = this.cache.get<MarketDataResponse>(cacheKey)
    
    if (cached) {
      return {
        data: cached,
        status: 'success',
        metadata: {
          timestamp: Date.now(),
          latency: 0,
          source: 'cache',
          cached: true
        }
      }
    }

    try {
      const startTime = Date.now()
      
      // Generate mock OHLCV data - replace with actual TimescaleDB query
      const data = this.generateMockOHLCV(request)
      
      const instrument: MarketInstrument = {
        symbol: request.instrument,
        displayName: request.instrument.replace('_', '/'),
        type: 'forex',
        baseCurrency: request.instrument.split('_')[0],
        quoteCurrency: request.instrument.split('_')[1],
        pipLocation: -4,
        tradingHours: [],
        isActive: true,
        averageSpread: 1.0,
        minTradeSize: 1000,
        maxTradeSize: 10000000
      }

      const response: MarketDataResponse = {
        instrument,
        data,
        totalCount: data.length,
        hasMore: data.length >= (request.maxBars || 1000),
        metadata: {
          requestTime: Date.now(),
          dataSource: 'TimescaleDB',
          latency: Date.now() - startTime
        }
      }

      this.cache.set(cacheKey, response)

      return {
        data: response,
        status: 'success',
        metadata: {
          timestamp: Date.now(),
          latency: Date.now() - startTime,
          source: 'database',
          cached: false
        }
      }
    } catch (error) {
      return {
        data: {} as MarketDataResponse,
        status: 'error',
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    }
  }

  /**
   * Subscribe to real-time market data
   */
  async subscribeToRealtimeData(subscription: Omit<RealtimeSubscription, 'id' | 'status'>): Promise<string> {
    const subscriptionId = `sub_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    
    const fullSubscription: RealtimeSubscription = {
      id: subscriptionId,
      status: 'pending',
      ...subscription
    }

    this.subscriptions.set(subscriptionId, fullSubscription)

    try {
      await this.ensureWebSocketConnection()
      
      // Send subscription message to WebSocket
      if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
        this.websocket.send(JSON.stringify({
          type: 'subscribe',
          id: subscriptionId,
          instruments: subscription.instruments,
          dataTypes: subscription.dataTypes
        }))

        fullSubscription.status = 'active'
      }
    } catch (error) {
      subscription.onError(error instanceof Error ? error : new Error('Subscription failed'))
      this.subscriptions.delete(subscriptionId)
      throw error
    }

    return subscriptionId
  }

  /**
   * Unsubscribe from real-time data
   */
  async unsubscribe(subscriptionId: string): Promise<void> {
    const subscription = this.subscriptions.get(subscriptionId)
    if (!subscription) return

    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      this.websocket.send(JSON.stringify({
        type: 'unsubscribe',
        id: subscriptionId
      }))
    }

    subscription.status = 'stopped'
    this.subscriptions.delete(subscriptionId)
  }

  /**
   * Get technical indicators for an instrument
   */
  async getTechnicalIndicators(
    instrument: string,
    timeframe: ChartTimeframe,
    indicators: string[]
  ): Promise<MarketDataServiceResponse<TechnicalIndicator[]>> {
    try {
      const startTime = Date.now()
      
      // Mock technical indicators - replace with actual calculation
      const technicalIndicators: TechnicalIndicator[] = indicators.map(indicator => ({
        name: indicator,
        type: this.getIndicatorType(indicator),
        data: this.generateMockIndicatorData(indicator),
        parameters: this.getDefaultParameters(indicator),
        display: {
          color: this.getIndicatorColor(indicator),
          lineWidth: 1,
          lineStyle: 'solid',
          showOnPrice: this.isOverlayIndicator(indicator),
          visible: true
        }
      }))

      return {
        data: technicalIndicators,
        status: 'success',
        metadata: {
          timestamp: Date.now(),
          latency: Date.now() - startTime,
          source: 'calculation',
          cached: false
        }
      }
    } catch (error) {
      return {
        data: [],
        status: 'error',
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    }
  }

  /**
   * Get Wyckoff patterns for an instrument
   */
  async getWyckoffPatterns(
    instrument: string,
    timeframe: ChartTimeframe,
    from: Date,
    to: Date
  ): Promise<MarketDataServiceResponse<WyckoffPattern[]>> {
    try {
      const startTime = Date.now()
      
      // Mock Wyckoff patterns - replace with actual pattern recognition
      const patterns: WyckoffPattern[] = [
        {
          type: 'accumulation',
          phase: 'phase_c',
          startTime: from.getTime(),
          endTime: to.getTime(),
          confidence: 0.75,
          keyLevels: [
            {
              type: 'support',
              price: 1.0950,
              timestamp: from.getTime(),
              strength: 0.8,
              touches: 3
            },
            {
              type: 'resistance',
              price: 1.1050,
              timestamp: from.getTime() + 86400000,
              strength: 0.7,
              touches: 2
            }
          ],
          volumeAnalysis: {
            trend: 'increasing',
            profile: [],
            vwap: 1.1000,
            effortResult: 'bullish'
          },
          description: 'Accumulation pattern in Phase C with potential spring formation'
        }
      ]

      return {
        data: patterns,
        status: 'success',
        metadata: {
          timestamp: Date.now(),
          latency: Date.now() - startTime,
          source: 'ai_analysis',
          cached: false
        }
      }
    } catch (error) {
      return {
        data: [],
        status: 'error',
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    }
  }

  /**
   * Get AI agent annotations
   */
  async getAIAnnotations(
    instrument: string,
    from: Date,
    to: Date
  ): Promise<MarketDataServiceResponse<AgentAnnotation[]>> {
    try {
      const startTime = Date.now()
      
      // Mock AI annotations - replace with actual agent decision data
      const annotations: AgentAnnotation[] = [
        {
          id: 'ann_001',
          agentId: 'market_analysis_001',
          agentName: 'Market Analysis Agent',
          type: 'entry',
          timestamp: from.getTime() + 3600000,
          price: 1.0980,
          action: 'buy',
          size: 10000,
          confidence: 0.85,
          rationale: 'Wyckoff accumulation pattern confirmed with volume increase',
          supportingData: {
            wyckoff_confidence: 0.75,
            volume_trend: 'increasing',
            rsi: 35
          },
          riskAssessment: {
            level: 'medium',
            riskRewardRatio: 2.5,
            stopLossDistance: 50,
            takeProfitDistance: 125,
            maxLoss: 500,
            expectedProfit: 1250
          },
          display: {
            shape: 'triangle',
            color: '#22c55e',
            size: 8,
            label: 'BUY',
            showTooltip: true,
            tooltipContent: 'Market Analysis Agent - Buy Signal'
          }
        }
      ]

      return {
        data: annotations,
        status: 'success',
        metadata: {
          timestamp: Date.now(),
          latency: Date.now() - startTime,
          source: 'agent_decisions',
          cached: false
        }
      }
    } catch (error) {
      return {
        data: [],
        status: 'error',
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    }
  }

  /**
   * Ensure WebSocket connection is established
   */
  private async ensureWebSocketConnection(): Promise<void> {
    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
      return
    }

    return new Promise((resolve, reject) => {
      try {
        this.websocket = new WebSocket(this.config.websocket.url)
        
        this.websocket.onopen = () => {
          console.log('Market data WebSocket connected')
          this.reconnectAttempts = 0
          this.setupHeartbeat()
          resolve()
        }

        this.websocket.onmessage = (event) => {
          this.handleWebSocketMessage(event.data)
        }

        this.websocket.onerror = (error) => {
          console.error('Market data WebSocket error:', error)
          reject(new Error('WebSocket connection failed'))
        }

        this.websocket.onclose = () => {
          console.log('Market data WebSocket disconnected')
          this.cleanup()
          this.attemptReconnection()
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  /**
   * Handle WebSocket message
   */
  private handleWebSocketMessage(data: string): void {
    try {
      const message = JSON.parse(data)
      
      switch (message.type) {
        case 'tick':
          this.handleTickData(message.data)
          break
        case 'bar':
          this.handleBarData(message.data)
          break
        case 'error':
          this.handleWebSocketError(message)
          break
        default:
          console.warn('Unknown WebSocket message type:', message.type)
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error)
    }
  }

  /**
   * Handle tick data from WebSocket
   */
  private handleTickData(tickData: PriceTick): void {
    for (const [, subscription] of this.subscriptions) {
      if (subscription.status === 'active' && 
          subscription.instruments.includes(tickData.instrument) &&
          subscription.dataTypes.includes('ticks')) {
        subscription.onUpdate(tickData)
      }
    }
  }

  /**
   * Handle bar data from WebSocket
   */
  private handleBarData(barData: OHLCV): void {
    for (const [, subscription] of this.subscriptions) {
      if (subscription.status === 'active' && subscription.dataTypes.includes('bars')) {
        subscription.onUpdate(barData)
      }
    }
  }

  /**
   * Handle WebSocket error
   */
  private handleWebSocketError(message: any): void {
    const error = new Error(message.error || 'WebSocket error')
    
    for (const [, subscription] of this.subscriptions) {
      subscription.onError(error)
    }
  }

  /**
   * Setup heartbeat mechanism
   */
  private setupHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
    }

    this.heartbeatInterval = setInterval(() => {
      if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
        this.websocket.send(JSON.stringify({ type: 'ping' }))
      }
    }, this.config.websocket.heartbeatInterval)
  }

  /**
   * Attempt WebSocket reconnection
   */
  private attemptReconnection(): void {
    if (this.reconnectAttempts >= this.config.websocket.reconnectAttempts) {
      console.error('Max reconnection attempts reached')
      return
    }

    this.reconnectAttempts++
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000)
    
    setTimeout(() => {
      console.log(`Attempting WebSocket reconnection (${this.reconnectAttempts}/${this.config.websocket.reconnectAttempts})`)
      this.ensureWebSocketConnection().catch(console.error)
    }, delay)
  }

  /**
   * Cleanup resources
   */
  private cleanup(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  /**
   * Generate mock OHLCV data
   */
  private generateMockOHLCV(request: MarketDataRequest): OHLCV[] {
    const data: OHLCV[] = []
    const timeframeMs = this.getTimeframeInMs(request.timeframe)
    let currentTime = request.from.getTime()
    let currentPrice = 1.1000 + (Math.random() - 0.5) * 0.01

    while (currentTime <= request.to.getTime()) {
      const open = currentPrice
      const change = (Math.random() - 0.5) * 0.005
      const high = open + Math.abs(change) + Math.random() * 0.002
      const low = open - Math.abs(change) - Math.random() * 0.002
      const close = open + change
      const volume = Math.floor(Math.random() * 1000000) + 100000

      data.push({
        timestamp: currentTime,
        open,
        high,
        low,
        close,
        volume
      })

      currentPrice = close
      currentTime += timeframeMs
    }

    return data
  }

  /**
   * Get timeframe in milliseconds
   */
  private getTimeframeInMs(timeframe: ChartTimeframe): number {
    const timeframes: Record<ChartTimeframe, number> = {
      '1m': 60 * 1000,
      '5m': 5 * 60 * 1000,
      '15m': 15 * 60 * 1000,
      '30m': 30 * 60 * 1000,
      '1h': 60 * 60 * 1000,
      '4h': 4 * 60 * 60 * 1000,
      '1d': 24 * 60 * 60 * 1000,
      '1w': 7 * 24 * 60 * 60 * 1000,
      '1M': 30 * 24 * 60 * 60 * 1000
    }
    return timeframes[timeframe]
  }

  /**
   * Generate mock indicator data
   */
  private generateMockIndicatorData(indicator: string): any[] {
    // Mock indicator data generation
    return []
  }

  /**
   * Get indicator type
   */
  private getIndicatorType(indicator: string): 'overlay' | 'oscillator' | 'volume' {
    const overlayIndicators = ['sma', 'ema', 'bollinger_bands', 'vwap']
    const oscillatorIndicators = ['rsi', 'macd', 'stochastic']
    const volumeIndicators = ['volume', 'volume_profile', 'obv']

    if (overlayIndicators.includes(indicator)) return 'overlay'
    if (oscillatorIndicators.includes(indicator)) return 'oscillator'
    if (volumeIndicators.includes(indicator)) return 'volume'
    return 'overlay'
  }

  /**
   * Get default parameters for indicator
   */
  private getDefaultParameters(indicator: string): Record<string, any> {
    const parameters: Record<string, any> = {
      'sma': { period: 20 },
      'ema': { period: 20 },
      'rsi': { period: 14 },
      'macd': { fast: 12, slow: 26, signal: 9 },
      'bollinger_bands': { period: 20, deviation: 2 }
    }
    return parameters[indicator] || {}
  }

  /**
   * Get indicator color
   */
  private getIndicatorColor(indicator: string): string {
    const colors: Record<string, string> = {
      'sma': '#3b82f6',
      'ema': '#ef4444',
      'rsi': '#8b5cf6',
      'macd': '#10b981',
      'bollinger_bands': '#f59e0b'
    }
    return colors[indicator] || '#6b7280'
  }

  /**
   * Check if indicator is overlay type
   */
  private isOverlayIndicator(indicator: string): boolean {
    return ['sma', 'ema', 'bollinger_bands', 'vwap'].includes(indicator)
  }

  /**
   * Cleanup and disconnect
   */
  public disconnect(): void {
    if (this.websocket) {
      this.websocket.close()
      this.websocket = null
    }
    this.cleanup()
    this.subscriptions.clear()
  }
}

/**
 * Default market data service instance
 */
export const marketDataService = new MarketDataService()