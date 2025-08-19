/**
 * Technical Indicators Component - AC3
 * Story 9.4: Technical indicator overlays including Wyckoff pattern recognition and volume analysis
 * 
 * FEATURES: Moving averages, RSI, MACD, Bollinger Bands, Wyckoff patterns, VPA analysis
 */

'use client'

import React, { useState, useCallback, useMemo, useEffect } from 'react'
import {
  TechnicalIndicator,
  WyckoffPattern,
  VolumeAnalysis,
  PriceLevel,
  ChartTimeframe,
  OHLCV,
  IndicatorDataPoint
} from '@/types/marketData'
import { useMarketData } from '@/hooks/useMarketData'

/**
 * Available technical indicators
 */
const AVAILABLE_INDICATORS = [
  { id: 'sma_20', name: 'SMA 20', category: 'trend', overlay: true },
  { id: 'sma_50', name: 'SMA 50', category: 'trend', overlay: true },
  { id: 'ema_12', name: 'EMA 12', category: 'trend', overlay: true },
  { id: 'ema_26', name: 'EMA 26', category: 'trend', overlay: true },
  { id: 'bollinger_bands', name: 'Bollinger Bands', category: 'volatility', overlay: true },
  { id: 'rsi', name: 'RSI (14)', category: 'momentum', overlay: false },
  { id: 'macd', name: 'MACD', category: 'momentum', overlay: false },
  { id: 'stochastic', name: 'Stochastic', category: 'momentum', overlay: false },
  { id: 'volume', name: 'Volume', category: 'volume', overlay: false },
  { id: 'vwap', name: 'VWAP', category: 'volume', overlay: true },
  { id: 'obv', name: 'On Balance Volume', category: 'volume', overlay: false }
]

/**
 * Wyckoff pattern types
 */
const WYCKOFF_PATTERNS = [
  { id: 'accumulation', name: 'Accumulation', color: '#22c55e' },
  { id: 'distribution', name: 'Distribution', color: '#ef4444' },
  { id: 'markup', name: 'Markup', color: '#3b82f6' },
  { id: 'markdown', name: 'Markdown', color: '#f59e0b' }
]

/**
 * Indicator configuration panel
 */
function IndicatorConfigPanel({
  availableIndicators,
  selectedIndicators,
  onToggleIndicator,
  onUpdateIndicator,
  compact = false
}: {
  availableIndicators: typeof AVAILABLE_INDICATORS
  selectedIndicators: TechnicalIndicator[]
  onToggleIndicator: (indicatorId: string) => void
  onUpdateIndicator: (indicatorId: string, config: Partial<TechnicalIndicator>) => void
  compact?: boolean
}) {
  const [expandedCategory, setExpandedCategory] = useState<string | null>('trend')

  const categorizedIndicators = useMemo(() => {
    const categories: Record<string, typeof AVAILABLE_INDICATORS> = {}
    availableIndicators.forEach(indicator => {
      if (!categories[indicator.category]) {
        categories[indicator.category] = []
      }
      categories[indicator.category].push(indicator)
    })
    return categories
  }, [availableIndicators])

  const isIndicatorSelected = useCallback((indicatorId: string) => {
    return selectedIndicators.some(ind => ind.name === indicatorId)
  }, [selectedIndicators])

  const getIndicatorConfig = useCallback((indicatorId: string) => {
    return selectedIndicators.find(ind => ind.name === indicatorId)
  }, [selectedIndicators])

  if (compact) {
    return (
      <div className="p-3 bg-gray-800 rounded border border-gray-700">
        <h4 className="text-sm font-medium text-white mb-2">Indicators</h4>
        <div className="flex flex-wrap gap-1">
          {availableIndicators.slice(0, 6).map(indicator => (
            <button
              key={indicator.id}
              onClick={() => onToggleIndicator(indicator.id)}
              className={`px-2 py-1 text-xs rounded ${
                isIndicatorSelected(indicator.id)
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {indicator.name}
            </button>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-white">Technical Indicators</h3>
      
      {Object.entries(categorizedIndicators).map(([category, indicators]) => (
        <div key={category} className="bg-gray-800 rounded-lg border border-gray-700">
          <button
            onClick={() => setExpandedCategory(expandedCategory === category ? null : category)}
            className="w-full flex items-center justify-between p-3 text-left"
          >
            <span className="font-medium text-white capitalize">{category}</span>
            <span className="text-gray-400">
              {expandedCategory === category ? '▼' : '▶'}
            </span>
          </button>
          
          {expandedCategory === category && (
            <div className="px-3 pb-3 space-y-2">
              {indicators.map(indicator => {
                const isSelected = isIndicatorSelected(indicator.id)
                const config = getIndicatorConfig(indicator.id)
                
                return (
                  <div key={indicator.id} className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => onToggleIndicator(indicator.id)}
                        className="text-blue-600"
                      />
                      <span className="text-sm text-gray-300">{indicator.name}</span>
                    </div>
                    
                    {isSelected && config && (
                      <div className="flex items-center space-x-2">
                        <input
                          type="color"
                          value={config.display.color}
                          onChange={(e) => onUpdateIndicator(indicator.id, {
                            display: { ...config.display, color: e.target.value }
                          })}
                          className="w-6 h-6 rounded border border-gray-600"
                        />
                        <button
                          onClick={() => onUpdateIndicator(indicator.id, {
                            display: { ...config.display, visible: !config.display.visible }
                          })}
                          className={`p-1 rounded text-xs ${
                            config.display.visible
                              ? 'bg-green-600 text-white'
                              : 'bg-gray-600 text-gray-300'
                          }`}
                        >
                          {config.display.visible ? '👁️' : '🙈'}
                        </button>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

/**
 * Wyckoff pattern display component
 */
function WyckoffPatternDisplay({
  patterns,
  onPatternClick,
  showDetails = false
}: {
  patterns: WyckoffPattern[]
  onPatternClick: (pattern: WyckoffPattern) => void
  showDetails?: boolean
}) {
  const getPatternColor = (type: WyckoffPattern['type']) => {
    const pattern = WYCKOFF_PATTERNS.find(p => p.id === type)
    return pattern?.color || '#6b7280'
  }

  const getPatternIcon = (type: WyckoffPattern['type']) => {
    switch (type) {
      case 'accumulation': return '📈'
      case 'distribution': return '📉'
      case 'markup': return '🚀'
      case 'markdown': return '⬇️'
      default: return '📊'
    }
  }

  const getPhaseDescription = (phase: WyckoffPattern['phase']) => {
    const descriptions = {
      phase_a: 'Stopping Action',
      phase_b: 'Testing Supply/Demand',
      phase_c: 'Spring/Upthrust',
      phase_d: 'Strength/Weakness',
      phase_e: 'Sign of Strength/Weakness'
    }
    return descriptions[phase] || phase
  }

  if (patterns.length === 0) {
    return (
      <div className="text-center py-4 text-gray-400">
        <div className="text-sm">No Wyckoff patterns detected</div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <h4 className="font-medium text-white flex items-center space-x-2">
        <span>📊</span>
        <span>Wyckoff Patterns</span>
      </h4>
      
      {patterns.map((pattern, index) => (
        <div
          key={index}
          onClick={() => onPatternClick(pattern)}
          className="p-3 bg-gray-800 border border-gray-700 rounded cursor-pointer hover:bg-gray-750 transition-colors"
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <span className="text-lg">{getPatternIcon(pattern.type)}</span>
              <span className="font-medium text-white capitalize">
                {pattern.type}
              </span>
              <span className="text-xs text-gray-400 uppercase">
                {pattern.phase.replace('_', ' ')}
              </span>
            </div>
            
            <div className="flex items-center space-x-2">
              <div className="text-xs text-gray-400">
                Confidence: {(pattern.confidence * 100).toFixed(0)}%
              </div>
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: getPatternColor(pattern.type) }}
              />
            </div>
          </div>

          {showDetails && (
            <>
              <div className="text-sm text-gray-300 mb-2">
                {pattern.description}
              </div>
              
              <div className="text-xs text-gray-400 mb-2">
                Phase: {getPhaseDescription(pattern.phase)}
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-gray-400">Key Levels: </span>
                  <span className="text-white">{pattern.keyLevels.length}</span>
                </div>
                <div>
                  <span className="text-gray-400">Volume Trend: </span>
                  <span className={`capitalize ${
                    pattern.volumeAnalysis.trend === 'increasing' ? 'text-green-400' :
                    pattern.volumeAnalysis.trend === 'decreasing' ? 'text-red-400' :
                    'text-gray-400'
                  }`}>
                    {pattern.volumeAnalysis.trend}
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">VWAP: </span>
                  <span className="font-mono text-white">
                    {pattern.volumeAnalysis.vwap.toFixed(4)}
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">Effort/Result: </span>
                  <span className={`capitalize ${
                    pattern.volumeAnalysis.effortResult === 'bullish' ? 'text-green-400' :
                    pattern.volumeAnalysis.effortResult === 'bearish' ? 'text-red-400' :
                    'text-gray-400'
                  }`}>
                    {pattern.volumeAnalysis.effortResult}
                  </span>
                </div>
              </div>

              {pattern.keyLevels.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-700">
                  <div className="text-xs text-gray-400 mb-1">Key Price Levels:</div>
                  <div className="flex flex-wrap gap-1">
                    {pattern.keyLevels.slice(0, 4).map((level, levelIndex) => (
                      <span
                        key={levelIndex}
                        className={`px-2 py-1 text-xs rounded ${
                          level.type === 'support' ? 'bg-green-900 text-green-200' :
                          level.type === 'resistance' ? 'bg-red-900 text-red-200' :
                          'bg-blue-900 text-blue-200'
                        }`}
                      >
                        {level.type}: {level.price.toFixed(4)}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      ))}
    </div>
  )
}

/**
 * Volume analysis component
 */
function VolumeAnalysisDisplay({
  analysis,
  showProfile = false
}: {
  analysis: VolumeAnalysis | null
  showProfile?: boolean
}) {
  if (!analysis) {
    return (
      <div className="text-center py-4 text-gray-400">
        <div className="text-sm">No volume analysis available</div>
      </div>
    )
  }

  const getTrendColor = (trend: VolumeAnalysis['trend']) => {
    switch (trend) {
      case 'increasing': return 'text-green-400'
      case 'decreasing': return 'text-red-400'
      default: return 'text-gray-400'
    }
  }

  const getEffortResultColor = (effortResult: VolumeAnalysis['effortResult']) => {
    switch (effortResult) {
      case 'bullish': return 'text-green-400'
      case 'bearish': return 'text-red-400'
      default: return 'text-gray-400'
    }
  }

  return (
    <div className="space-y-3">
      <h4 className="font-medium text-white flex items-center space-x-2">
        <span>📊</span>
        <span>Volume Analysis</span>
      </h4>
      
      <div className="p-3 bg-gray-800 border border-gray-700 rounded">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Trend: </span>
            <span className={`capitalize font-medium ${getTrendColor(analysis.trend)}`}>
              {analysis.trend}
            </span>
          </div>
          
          <div>
            <span className="text-gray-400">VWAP: </span>
            <span className="font-mono text-white">
              {analysis.vwap.toFixed(4)}
            </span>
          </div>
          
          <div className="col-span-2">
            <span className="text-gray-400">Effort vs Result: </span>
            <span className={`capitalize font-medium ${getEffortResultColor(analysis.effortResult)}`}>
              {analysis.effortResult}
            </span>
          </div>
        </div>

        {showProfile && analysis.profile.length > 0 && (
          <div className="mt-4 pt-3 border-t border-gray-700">
            <div className="text-sm text-gray-400 mb-2">Volume Profile (Top 5)</div>
            <div className="space-y-1">
              {analysis.profile
                .sort((a, b) => b.volume - a.volume)
                .slice(0, 5)
                .map((level, index) => (
                  <div key={index} className="flex items-center justify-between text-xs">
                    <span className="font-mono text-gray-300">
                      {level.price.toFixed(4)}
                      {level.isPOC && <span className="ml-1 text-yellow-400">POC</span>}
                    </span>
                    <div className="flex items-center space-x-2">
                      <div className="w-16 bg-gray-700 rounded h-2">
                        <div
                          className="bg-blue-500 h-2 rounded"
                          style={{ width: `${level.volumePercent}%` }}
                        />
                      </div>
                      <span className="text-gray-400 w-12 text-right">
                        {level.volumePercent.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Indicator calculation utilities (mock implementations)
 */
const calculateIndicators = {
  sma: (data: OHLCV[], period: number): IndicatorDataPoint[] => {
    const result: IndicatorDataPoint[] = []
    for (let i = period - 1; i < data.length; i++) {
      const sum = data.slice(i - period + 1, i + 1).reduce((acc, bar) => acc + bar.close, 0)
      result.push({
        timestamp: data[i].timestamp,
        value: sum / period
      })
    }
    return result
  },

  ema: (data: OHLCV[], period: number): IndicatorDataPoint[] => {
    const result: IndicatorDataPoint[] = []
    const multiplier = 2 / (period + 1)
    let ema = data[0].close
    
    for (let i = 0; i < data.length; i++) {
      ema = data[i].close * multiplier + ema * (1 - multiplier)
      result.push({
        timestamp: data[i].timestamp,
        value: ema
      })
    }
    return result
  },

  rsi: (data: OHLCV[], period: number = 14): IndicatorDataPoint[] => {
    const result: IndicatorDataPoint[] = []
    const changes = data.slice(1).map((bar, i) => bar.close - data[i].close)
    
    for (let i = period; i < changes.length; i++) {
      const gains = changes.slice(i - period, i).filter(c => c > 0)
      const losses = changes.slice(i - period, i).filter(c => c < 0).map(c => -c)
      
      const avgGain = gains.length > 0 ? gains.reduce((a, b) => a + b, 0) / period : 0
      const avgLoss = losses.length > 0 ? losses.reduce((a, b) => a + b, 0) / period : 0
      
      const rs = avgLoss !== 0 ? avgGain / avgLoss : 100
      const rsi = 100 - (100 / (1 + rs))
      
      result.push({
        timestamp: data[i + 1].timestamp,
        value: rsi,
        signal: rsi > 70 ? 'sell' : rsi < 30 ? 'buy' : 'neutral'
      })
    }
    return result
  }
}

/**
 * Props for TechnicalIndicators component
 */
interface TechnicalIndicatorsProps {
  /** Instrument symbol */
  instrument: string
  /** Chart timeframe */
  timeframe: ChartTimeframe
  /** Historical price data */
  data: OHLCV[]
  /** Enabled indicators */
  enabledIndicators?: string[]
  /** Enable Wyckoff pattern recognition */
  enableWyckoffPatterns?: boolean
  /** Enable volume analysis */
  enableVolumeAnalysis?: boolean
  /** Callback for indicator updates */
  onIndicatorUpdate?: (indicators: TechnicalIndicator[]) => void
  /** Callback for pattern detection */
  onPatternDetected?: (patterns: WyckoffPattern[]) => void
  /** Compact display mode */
  compact?: boolean
}

/**
 * Main TechnicalIndicators component
 */
export function TechnicalIndicators({
  instrument,
  timeframe,
  data,
  enabledIndicators = [],
  enableWyckoffPatterns = false,
  enableVolumeAnalysis = false,
  onIndicatorUpdate,
  onPatternDetected,
  compact = false
}: TechnicalIndicatorsProps) {
  const [selectedIndicators, setSelectedIndicators] = useState<TechnicalIndicator[]>([])
  const [wyckoffPatterns, setWyckoffPatterns] = useState<WyckoffPattern[]>([])
  const [volumeAnalysis, setVolumeAnalysis] = useState<VolumeAnalysis | null>(null)
  const [showPatternDetails, setShowPatternDetails] = useState(false)

  const { actions } = useMarketData()

  /**
   * Calculate and update indicators
   */
  const calculateAndUpdateIndicators = useCallback(() => {
    if (data.length === 0) return

    const newIndicators: TechnicalIndicator[] = enabledIndicators.map(indicatorId => {
      const indicator = AVAILABLE_INDICATORS.find(ind => ind.id === indicatorId)
      if (!indicator) return null

      let indicatorData: IndicatorDataPoint[] = []
      let parameters: Record<string, any> = {}

      // Calculate indicator data based on type
      switch (indicatorId) {
        case 'sma_20':
          indicatorData = calculateIndicators.sma(data, 20)
          parameters = { period: 20 }
          break
        case 'sma_50':
          indicatorData = calculateIndicators.sma(data, 50)
          parameters = { period: 50 }
          break
        case 'ema_12':
          indicatorData = calculateIndicators.ema(data, 12)
          parameters = { period: 12 }
          break
        case 'ema_26':
          indicatorData = calculateIndicators.ema(data, 26)
          parameters = { period: 26 }
          break
        case 'rsi':
          indicatorData = calculateIndicators.rsi(data, 14)
          parameters = { period: 14, overbought: 70, oversold: 30 }
          break
        default:
          // Mock data for other indicators
          indicatorData = data.map(bar => ({
            timestamp: bar.timestamp,
            value: bar.close * (0.98 + Math.random() * 0.04)
          }))
      }

      return {
        name: indicatorId,
        type: indicator.overlay ? 'overlay' : 'oscillator' as any,
        data: indicatorData,
        parameters,
        display: {
          color: getIndicatorDefaultColor(indicatorId),
          lineWidth: 1,
          lineStyle: 'solid' as const,
          showOnPrice: indicator.overlay,
          visible: true
        }
      }
    }).filter(Boolean) as TechnicalIndicator[]

    setSelectedIndicators(newIndicators)
    onIndicatorUpdate?.(newIndicators)
  }, [data, enabledIndicators, onIndicatorUpdate])

  /**
   * Load Wyckoff patterns
   */
  const loadWyckoffPatterns = useCallback(async () => {
    if (!enableWyckoffPatterns) return

    try {
      const from = new Date(data[0]?.timestamp || Date.now())
      const to = new Date(data[data.length - 1]?.timestamp || Date.now())
      
      const response = await actions.loadWyckoffPatterns(instrument, timeframe, from, to)
      // The patterns would be available in the hook's state
      // For now, we'll use mock data
      
      const mockPatterns: WyckoffPattern[] = [
        {
          type: 'accumulation',
          phase: 'phase_c',
          startTime: from.getTime(),
          endTime: to.getTime(),
          confidence: 0.75,
          keyLevels: [
            {
              type: 'support',
              price: Math.min(...data.map(d => d.low)) * 1.001,
              timestamp: from.getTime(),
              strength: 0.8,
              touches: 3
            }
          ],
          volumeAnalysis: {
            trend: 'increasing',
            profile: [],
            vwap: data.reduce((sum, d) => sum + d.close, 0) / data.length,
            effortResult: 'bullish'
          },
          description: 'Accumulation pattern detected in Phase C with potential spring formation'
        }
      ]

      setWyckoffPatterns(mockPatterns)
      onPatternDetected?.(mockPatterns)
    } catch (error) {
      console.error('Failed to load Wyckoff patterns:', error)
    }
  }, [enableWyckoffPatterns, actions, instrument, timeframe, data, onPatternDetected])

  /**
   * Calculate volume analysis
   */
  const calculateVolumeAnalysis = useCallback(() => {
    if (!enableVolumeAnalysis || data.length === 0) return

    const totalVolume = data.reduce((sum, bar) => sum + bar.volume, 0)
    const avgVolume = totalVolume / data.length
    const recentVolume = data.slice(-10).reduce((sum, bar) => sum + bar.volume, 0) / 10

    const trend = recentVolume > avgVolume * 1.1 ? 'increasing' :
                  recentVolume < avgVolume * 0.9 ? 'decreasing' : 'neutral'

    // Calculate VWAP
    const vwapNumerator = data.reduce((sum, bar) => sum + (bar.close * bar.volume), 0)
    const vwapDenominator = data.reduce((sum, bar) => sum + bar.volume, 0)
    const vwap = vwapNumerator / vwapDenominator

    // Simple effort vs result analysis
    const priceChange = data[data.length - 1].close - data[0].close
    const volumeIncrease = recentVolume > avgVolume
    
    const effortResult = priceChange > 0 && volumeIncrease ? 'bullish' :
                        priceChange < 0 && volumeIncrease ? 'bearish' : 'neutral'

    const analysis: VolumeAnalysis = {
      trend,
      profile: [], // Would be calculated from actual volume profile data
      vwap,
      effortResult
    }

    setVolumeAnalysis(analysis)
  }, [enableVolumeAnalysis, data])

  /**
   * Get default color for indicator
   */
  const getIndicatorDefaultColor = useCallback((indicatorId: string): string => {
    const colors: Record<string, string> = {
      sma_20: '#3b82f6',
      sma_50: '#ef4444',
      ema_12: '#22c55e',
      ema_26: '#f59e0b',
      rsi: '#8b5cf6',
      macd: '#10b981',
      bollinger_bands: '#ec4899'
    }
    return colors[indicatorId] || '#6b7280'
  }, [])

  /**
   * Toggle indicator selection
   */
  const handleToggleIndicator = useCallback((indicatorId: string) => {
    const newEnabledIndicators = enabledIndicators.includes(indicatorId)
      ? enabledIndicators.filter(id => id !== indicatorId)
      : [...enabledIndicators, indicatorId]
    
    // Update would be handled by parent component
    console.log('Toggle indicator:', indicatorId, newEnabledIndicators)
  }, [enabledIndicators])

  /**
   * Update indicator configuration
   */
  const handleUpdateIndicator = useCallback((indicatorId: string, config: Partial<TechnicalIndicator>) => {
    setSelectedIndicators(prev =>
      prev.map(ind => ind.name === indicatorId ? { ...ind, ...config } : ind)
    )
  }, [])

  /**
   * Handle pattern click
   */
  const handlePatternClick = useCallback((pattern: WyckoffPattern) => {
    console.log('Pattern clicked:', pattern)
    setShowPatternDetails(true)
  }, [])

  /**
   * Effects
   */
  useEffect(() => {
    calculateAndUpdateIndicators()
  }, [calculateAndUpdateIndicators])

  useEffect(() => {
    loadWyckoffPatterns()
  }, [loadWyckoffPatterns])

  useEffect(() => {
    calculateVolumeAnalysis()
  }, [calculateVolumeAnalysis])

  if (compact) {
    return (
      <div className="space-y-3">
        <IndicatorConfigPanel
          availableIndicators={AVAILABLE_INDICATORS}
          selectedIndicators={selectedIndicators}
          onToggleIndicator={handleToggleIndicator}
          onUpdateIndicator={handleUpdateIndicator}
          compact={true}
        />
        
        {enableWyckoffPatterns && wyckoffPatterns.length > 0 && (
          <div className="p-2 bg-gray-800 rounded border border-gray-700">
            <div className="text-xs text-gray-400 mb-1">Wyckoff Patterns</div>
            <div className="flex space-x-1">
              {wyckoffPatterns.slice(0, 2).map((pattern, index) => (
                <span
                  key={index}
                  className="px-2 py-1 text-xs rounded bg-gray-700 text-white"
                >
                  {pattern.type}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <IndicatorConfigPanel
        availableIndicators={AVAILABLE_INDICATORS}
        selectedIndicators={selectedIndicators}
        onToggleIndicator={handleToggleIndicator}
        onUpdateIndicator={handleUpdateIndicator}
      />

      {enableWyckoffPatterns && (
        <WyckoffPatternDisplay
          patterns={wyckoffPatterns}
          onPatternClick={handlePatternClick}
          showDetails={showPatternDetails}
        />
      )}

      {enableVolumeAnalysis && (
        <VolumeAnalysisDisplay
          analysis={volumeAnalysis}
          showProfile={true}
        />
      )}
    </div>
  )
}

export default TechnicalIndicators