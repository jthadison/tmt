/**
 * Market Data Types for Chart Visualization
 * Story 9.4: Comprehensive market data structures for interactive charts
 */

export type ChartTimeframe = '1m' | '5m' | '15m' | '30m' | '1h' | '4h' | '1d' | '1w' | '1M'
export type ChartType = 'candlestick' | 'line' | 'area' | 'volume' | 'heikin_ashi'
export type InstrumentType = 'forex' | 'indices' | 'commodities' | 'crypto'

/**
 * Basic OHLCV data structure for price data
 */
export interface OHLCV {
  /** Timestamp in milliseconds */
  timestamp: number
  /** Opening price */
  open: number
  /** Highest price */
  high: number
  /** Lowest price */
  low: number
  /** Closing price */
  close: number
  /** Volume */
  volume: number
  /** Tick volume (for forex) */
  tickVolume?: number
  /** Spread */
  spread?: number
}

/**
 * Real-time price tick data
 */
export interface PriceTick {
  /** Instrument symbol */
  instrument: string
  /** Timestamp in milliseconds */
  timestamp: number
  /** Bid price */
  bid: number
  /** Ask price */
  ask: number
  /** Mid price */
  mid: number
  /** Volume since last tick */
  volume: number
  /** Daily change */
  change: number
  /** Daily change percentage */
  changePercent: number
}

/**
 * Market instrument definition
 */
export interface MarketInstrument {
  /** Unique instrument identifier */
  symbol: string
  /** Display name */
  displayName: string
  /** Instrument type */
  type: InstrumentType
  /** Base currency */
  baseCurrency: string
  /** Quote currency */
  quoteCurrency: string
  /** Minimum pip size */
  pipLocation: number
  /** Trading session information */
  tradingHours: TradingSession[]
  /** Whether instrument is actively traded */
  isActive: boolean
  /** Spread information */
  averageSpread: number
  /** Minimum trade size */
  minTradeSize: number
  /** Maximum trade size */
  maxTradeSize: number
}

/**
 * Trading session definition
 */
export interface TradingSession {
  /** Session name (e.g., 'London', 'New York') */
  name: string
  /** Session start time (UTC) */
  startTime: string
  /** Session end time (UTC) */
  endTime: string
  /** Days of week active */
  daysActive: number[]
  /** Whether session is currently active */
  isActive: boolean
}

/**
 * Technical indicator data point
 */
export interface TechnicalIndicator {
  /** Indicator name */
  name: string
  /** Indicator type */
  type: 'overlay' | 'oscillator' | 'volume'
  /** Data points */
  data: IndicatorDataPoint[]
  /** Indicator parameters */
  parameters: Record<string, any>
  /** Display settings */
  display: IndicatorDisplay
}

/**
 * Individual indicator data point
 */
export interface IndicatorDataPoint {
  /** Timestamp in milliseconds */
  timestamp: number
  /** Primary value */
  value: number
  /** Additional values (e.g., upper/lower bands) */
  values?: Record<string, number>
  /** Signal information */
  signal?: 'buy' | 'sell' | 'neutral'
}

/**
 * Indicator display configuration
 */
export interface IndicatorDisplay {
  /** Line color */
  color: string
  /** Line width */
  lineWidth: number
  /** Line style */
  lineStyle: 'solid' | 'dashed' | 'dotted'
  /** Whether to show on price chart or separate pane */
  showOnPrice: boolean
  /** Visibility */
  visible: boolean
}

/**
 * Wyckoff pattern recognition data
 */
export interface WyckoffPattern {
  /** Pattern type */
  type: 'accumulation' | 'distribution' | 'markup' | 'markdown'
  /** Pattern phase */
  phase: 'phase_a' | 'phase_b' | 'phase_c' | 'phase_d' | 'phase_e'
  /** Pattern start timestamp */
  startTime: number
  /** Pattern end timestamp */
  endTime: number
  /** Confidence level (0-1) */
  confidence: number
  /** Key price levels */
  keyLevels: PriceLevel[]
  /** Volume analysis */
  volumeAnalysis: VolumeAnalysis
  /** Pattern description */
  description: string
}

/**
 * Price level definition
 */
export interface PriceLevel {
  /** Level type */
  type: 'support' | 'resistance' | 'supply' | 'demand' | 'spring' | 'upthrust'
  /** Price value */
  price: number
  /** Timestamp when level was formed */
  timestamp: number
  /** Strength of the level (0-1) */
  strength: number
  /** Number of touches */
  touches: number
}

/**
 * Volume analysis data
 */
export interface VolumeAnalysis {
  /** Volume trend */
  trend: 'increasing' | 'decreasing' | 'neutral'
  /** Volume profile data */
  profile: VolumeProfileLevel[]
  /** Volume weighted average price */
  vwap: number
  /** Effort vs result analysis */
  effortResult: 'bullish' | 'bearish' | 'neutral'
}

/**
 * Volume profile level
 */
export interface VolumeProfileLevel {
  /** Price level */
  price: number
  /** Volume at this price */
  volume: number
  /** Percentage of total volume */
  volumePercent: number
  /** Point of control (highest volume) */
  isPOC: boolean
}

/**
 * AI Agent trading decision annotation
 */
export interface AgentAnnotation {
  /** Unique annotation ID */
  id: string
  /** Agent ID that made the decision */
  agentId: string
  /** Agent name */
  agentName: string
  /** Annotation type */
  type: 'entry' | 'exit' | 'stop_loss' | 'take_profit' | 'decision_point'
  /** Timestamp of the annotation */
  timestamp: number
  /** Price at which annotation occurs */
  price: number
  /** Trading action */
  action: 'buy' | 'sell' | 'hold' | 'close'
  /** Position size */
  size: number
  /** Confidence level (0-1) */
  confidence: number
  /** Decision rationale */
  rationale: string
  /** Supporting data */
  supportingData: Record<string, any>
  /** Risk assessment */
  riskAssessment: RiskAssessment
  /** Visual styling */
  display: AnnotationDisplay
}

/**
 * Risk assessment for annotations
 */
export interface RiskAssessment {
  /** Risk level */
  level: 'low' | 'medium' | 'high' | 'critical'
  /** Risk-reward ratio */
  riskRewardRatio: number
  /** Stop loss distance */
  stopLossDistance: number
  /** Take profit distance */
  takeProfitDistance: number
  /** Maximum loss */
  maxLoss: number
  /** Expected profit */
  expectedProfit: number
}

/**
 * Annotation display configuration
 */
export interface AnnotationDisplay {
  /** Marker shape */
  shape: 'circle' | 'triangle' | 'square' | 'arrow' | 'flag'
  /** Marker color */
  color: string
  /** Marker size */
  size: number
  /** Label text */
  label: string
  /** Whether to show tooltip */
  showTooltip: boolean
  /** Tooltip content */
  tooltipContent?: string
}

/**
 * Chart configuration
 */
export interface ChartConfig {
  /** Chart type */
  type: ChartType
  /** Selected timeframe */
  timeframe: ChartTimeframe
  /** Instrument being displayed */
  instrument: string
  /** Number of bars to display */
  barsVisible: number
  /** Auto-scale price axis */
  autoScale: boolean
  /** Show volume */
  showVolume: boolean
  /** Show grid */
  showGrid: boolean
  /** Show crosshair */
  showCrosshair: boolean
  /** Color scheme */
  colorScheme: 'light' | 'dark'
  /** Active technical indicators */
  indicators: TechnicalIndicator[]
  /** Show Wyckoff patterns */
  showWyckoffPatterns: boolean
  /** Show AI annotations */
  showAIAnnotations: boolean
}

/**
 * Market data request parameters
 */
export interface MarketDataRequest {
  /** Instrument symbol */
  instrument: string
  /** Timeframe */
  timeframe: ChartTimeframe
  /** Start date */
  from: Date
  /** End date */
  to: Date
  /** Maximum number of bars */
  maxBars?: number
  /** Include volume data */
  includeVolume?: boolean
  /** Include tick data */
  includeTicks?: boolean
}

/**
 * Market data response
 */
export interface MarketDataResponse {
  /** Instrument information */
  instrument: MarketInstrument
  /** OHLCV data */
  data: OHLCV[]
  /** Total count of available bars */
  totalCount: number
  /** Whether more data is available */
  hasMore: boolean
  /** Request metadata */
  metadata: {
    requestTime: number
    dataSource: string
    latency: number
  }
}

/**
 * Real-time subscription configuration
 */
export interface RealtimeSubscription {
  /** Subscription ID */
  id: string
  /** Instruments to subscribe to */
  instruments: string[]
  /** Data types to receive */
  dataTypes: ('ticks' | 'bars' | 'book')[]
  /** Callback for data updates */
  onUpdate: (data: PriceTick | OHLCV) => void
  /** Callback for errors */
  onError: (error: Error) => void
  /** Subscription status */
  status: 'pending' | 'active' | 'paused' | 'stopped'
}

/**
 * Chart synchronization state
 */
export interface ChartSyncState {
  /** Master chart ID */
  masterId: string
  /** Synchronized chart IDs */
  syncedCharts: string[]
  /** Current visible time range */
  timeRange: {
    from: number
    to: number
  }
  /** Current crosshair position */
  crosshairPosition?: {
    time: number
    price: number
  }
  /** Zoom level */
  zoomLevel: number
}

/**
 * Multi-chart layout configuration
 */
export interface MultiChartLayout {
  /** Layout ID */
  id: string
  /** Layout name */
  name: string
  /** Layout type */
  type: 'single' | 'split_vertical' | 'split_horizontal' | 'grid_2x2' | 'grid_3x1' | 'custom'
  /** Chart configurations */
  charts: ChartPanelConfig[]
  /** Synchronization settings */
  sync: {
    enabled: boolean
    syncTime: boolean
    syncCrosshair: boolean
    syncZoom: boolean
  }
}

/**
 * Individual chart panel configuration
 */
export interface ChartPanelConfig {
  /** Panel ID */
  id: string
  /** Panel position */
  position: {
    x: number
    y: number
    width: number
    height: number
  }
  /** Chart configuration */
  chartConfig: ChartConfig
  /** Panel title */
  title: string
  /** Whether panel is visible */
  visible: boolean
}

/**
 * Chart performance metrics
 */
export interface ChartPerformance {
  /** Chart ID */
  chartId: string
  /** Rendering metrics */
  renderTime: number
  /** Data update latency */
  updateLatency: number
  /** Frame rate (FPS) */
  frameRate: number
  /** Memory usage */
  memoryUsage: number
  /** Number of data points */
  dataPoints: number
  /** Last update timestamp */
  lastUpdate: number
}

/**
 * Chart event types
 */
export type ChartEventType = 
  | 'data_updated'
  | 'timerange_changed'
  | 'crosshair_moved'
  | 'zoom_changed'
  | 'annotation_clicked'
  | 'pattern_detected'
  | 'indicator_signal'

/**
 * Chart event data
 */
export interface ChartEvent {
  /** Event type */
  type: ChartEventType
  /** Chart ID */
  chartId: string
  /** Event timestamp */
  timestamp: number
  /** Event data */
  data: any
  /** Source of the event */
  source: 'user' | 'system' | 'ai_agent'
}

/**
 * Export for market data service responses
 */
export interface MarketDataServiceResponse<T = any> {
  /** Response data */
  data: T
  /** Response status */
  status: 'success' | 'error' | 'partial'
  /** Error message if any */
  error?: string
  /** Response metadata */
  metadata?: {
    timestamp: number
    latency: number
    source: string
    cached: boolean
  }
}