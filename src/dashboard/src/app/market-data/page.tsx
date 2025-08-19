'use client'

import React, { useState, useEffect } from 'react'
import { Line, Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
} from 'chart.js'
import 'chartjs-adapter-date-fns'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
)

// Types
interface MarketInstrument {
  symbol: string
  display_name: string
  type: string
  base_currency: string
  quote_currency: string
  is_active: boolean
  average_spread: number
  trading_sessions: string[]
}

interface OHLCV {
  timestamp: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface TechnicalIndicator {
  name: string
  type: string
  value: number
  timestamp: number
  parameters: Record<string, any>
}

interface WyckoffPattern {
  type: string
  phase: string
  confidence: number
  start_time: number
  end_time: number
  key_levels: Array<{
    type: string
    price: number
    strength: number
    touches: number
  }>
  volume_analysis: Record<string, any>
  description: string
}

interface MarketData {
  instrument: MarketInstrument
  timeframe: string
  data: OHLCV[]
  indicators: TechnicalIndicator[]
  wyckoff_patterns: WyckoffPattern[]
  metadata: Record<string, any>
}

interface LivePrice {
  symbol: string
  bid: number
  ask: number
  spread: number
  timestamp: string
  change_24h: number
  volume_24h: number
}

interface MarketOverview {
  major_pairs: Array<{
    symbol: string
    display_name: string
    price: number
    change_24h: number
    change_percent: number
    volume: number
    volatility: number
    trend: string
  }>
  market_sentiment: {
    overall_sentiment: string
    risk_on_off: string
    volatility_index: number
    dollar_strength: number
    active_sessions: string[]
    news_impact: string
  }
  timestamp: string
}

const MarketDataPage = () => {
  const [instruments, setInstruments] = useState<MarketInstrument[]>([])
  const [selectedSymbol, setSelectedSymbol] = useState<string>('EUR_USD')
  const [selectedTimeframe, setSelectedTimeframe] = useState<string>('1h')
  const [marketData, setMarketData] = useState<MarketData | null>(null)
  const [livePrices, setLivePrices] = useState<Record<string, LivePrice>>({})
  const [marketOverview, setMarketOverview] = useState<MarketOverview | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

  // Fetch available instruments
  useEffect(() => {
    const fetchInstruments = async () => {
      try {
        const response = await fetch('http://localhost:8001/api/instruments')
        const result = await response.json()
        if (result.status === 'success') {
          setInstruments(result.data)
        }
      } catch (err) {
        console.error('Error fetching instruments:', err)
        setError('Failed to load instruments')
      }
    }

    fetchInstruments()
  }, [])

  // Fetch market data
  const fetchMarketData = async () => {
    if (!selectedSymbol) return

    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(
        `http://localhost:8001/api/market-data/${selectedSymbol}?timeframe=${selectedTimeframe}&count=100&include_indicators=true&include_wyckoff=true`
      )
      const result = await response.json()

      if (result.status === 'success') {
        setMarketData(result.data)
        setLastUpdate(new Date())
      } else {
        setError(result.error || 'Failed to fetch market data')
      }
    } catch (err) {
      console.error('Error fetching market data:', err)
      setError('Failed to fetch market data')
    } finally {
      setIsLoading(false)
    }
  }

  // Fetch live prices
  const fetchLivePrices = async () => {
    if (instruments.length === 0) return

    try {
      const symbols = instruments.map(inst => inst.symbol).join(',')
      const response = await fetch(`http://localhost:8001/api/live-prices?symbols=${symbols}`)
      const result = await response.json()

      if (result.status === 'success') {
        setLivePrices(result.data)
      }
    } catch (err) {
      console.error('Error fetching live prices:', err)
    }
  }

  // Fetch market overview
  const fetchMarketOverview = async () => {
    try {
      const response = await fetch('http://localhost:8001/api/market-overview')
      const result = await response.json()

      if (result.status === 'success') {
        setMarketOverview(result.data)
      }
    } catch (err) {
      console.error('Error fetching market overview:', err)
    }
  }

  // Initial data fetch
  useEffect(() => {
    fetchMarketData()
  }, [selectedSymbol, selectedTimeframe])

  // Auto-refresh live data
  useEffect(() => {
    fetchLivePrices()
    fetchMarketOverview()

    const interval = setInterval(() => {
      fetchLivePrices()
      fetchMarketOverview()
    }, 5000) // Update every 5 seconds

    return () => clearInterval(interval)
  }, [instruments])

  // Prepare chart data
  const prepareChartData = () => {
    if (!marketData || !marketData.data.length) return null

    const labels = marketData.data.map(item => new Date(item.timestamp))
    const prices = marketData.data.map(item => item.close)
    const volumes = marketData.data.map(item => item.volume)

    return {
      price: {
        labels,
        datasets: [
          {
            label: `${selectedSymbol} Price`,
            data: prices,
            borderColor: 'rgb(59, 130, 246)',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.1,
          },
          // Add SMA indicators if available
          ...(marketData.indicators
            .filter(ind => ind.name.startsWith('SMA'))
            .map((indicator, index) => ({
              label: indicator.name,
              data: marketData.data.map(() => indicator.value),
              borderColor: index === 0 ? 'rgb(34, 197, 94)' : 'rgb(239, 68, 68)',
              borderWidth: 1,
              fill: false,
              tension: 0.1,
            }))
          ),
        ],
      },
      volume: {
        labels,
        datasets: [
          {
            label: 'Volume',
            data: volumes,
            backgroundColor: 'rgba(156, 163, 175, 0.6)',
            borderColor: 'rgb(156, 163, 175)',
            borderWidth: 1,
          },
        ],
      },
    }
  }

  const chartData = prepareChartData()

  const formatCurrency = (amount: number, decimals = 5) => {
    return amount.toFixed(decimals)
  }

  const formatVolume = (volume: number) => {
    if (volume >= 1000000) {
      return `${(volume / 1000000).toFixed(1)}M`
    } else if (volume >= 1000) {
      return `${(volume / 1000).toFixed(1)}K`
    }
    return volume.toString()
  }

  const getChangeColor = (change: number) => {
    return change >= 0 ? 'text-green-400' : 'text-red-400'
  }

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'bullish': return '📈'
      case 'bearish': return '📉'
      default: return '➡️'
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-blue-400 mb-2">
                Market Data & Analysis
              </h1>
              <p className="text-gray-300">
                Real-time market data, technical indicators, and Wyckoff analysis
              </p>
            </div>
            <div className="text-right">
              {lastUpdate && (
                <p className="text-sm text-gray-400">
                  Last updated: {lastUpdate.toLocaleTimeString()}
                </p>
              )}
              <button
                onClick={fetchMarketData}
                disabled={isLoading}
                className="mt-2 bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded transition-colors disabled:opacity-50"
              >
                {isLoading ? '🔄 Loading...' : '🔄 Refresh Data'}
              </button>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-900/50 border border-red-500 rounded-lg">
            <p className="text-red-400">⚠️ {error}</p>
          </div>
        )}

        {/* Market Overview */}
        {marketOverview && (
          <div className="mb-8 bg-gray-800 p-6 rounded-lg border border-gray-700">
            <h2 className="text-2xl font-semibold mb-4">Market Overview</h2>
            
            {/* Market Sentiment */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="text-center">
                <p className="text-gray-400 text-sm">Overall Sentiment</p>
                <p className="text-xl font-bold capitalize">{marketOverview.market_sentiment.overall_sentiment}</p>
              </div>
              <div className="text-center">
                <p className="text-gray-400 text-sm">Risk Appetite</p>
                <p className="text-xl font-bold capitalize">{marketOverview.market_sentiment.risk_on_off.replace('_', ' ')}</p>
              </div>
              <div className="text-center">
                <p className="text-gray-400 text-sm">Volatility Index</p>
                <p className="text-xl font-bold">{marketOverview.market_sentiment.volatility_index}</p>
              </div>
              <div className="text-center">
                <p className="text-gray-400 text-sm">USD Strength</p>
                <p className={`text-xl font-bold ${getChangeColor(marketOverview.market_sentiment.dollar_strength)}`}>
                  {marketOverview.market_sentiment.dollar_strength > 0 ? '+' : ''}{marketOverview.market_sentiment.dollar_strength}
                </p>
              </div>
            </div>

            {/* Active Sessions */}
            <div className="mb-6">
              <p className="text-gray-400 text-sm mb-2">Active Trading Sessions</p>
              <div className="flex gap-2">
                {marketOverview.market_sentiment.active_sessions.map(session => (
                  <span key={session} className="bg-green-600 text-white px-3 py-1 rounded text-sm">
                    {session}
                  </span>
                ))}
              </div>
            </div>

            {/* Major Pairs Overview */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {marketOverview.major_pairs.map(pair => (
                <div key={pair.symbol} className="bg-gray-700 p-4 rounded border border-gray-600">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold">{pair.display_name}</h3>
                    <span className="text-lg">{getTrendIcon(pair.trend)}</span>
                  </div>
                  <div className="space-y-1">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Price:</span>
                      <span className="font-mono">{formatCurrency(pair.price)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">24h Change:</span>
                      <span className={`font-mono ${getChangeColor(pair.change_24h)}`}>
                        {pair.change_24h >= 0 ? '+' : ''}{formatCurrency(pair.change_24h, 4)} ({pair.change_percent}%)
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Volume:</span>
                      <span className="font-mono">{formatVolume(pair.volume)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Instrument Selection */}
        <div className="mb-6 bg-gray-800 p-4 rounded-lg border border-gray-700">
          <div className="flex flex-wrap items-center gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Instrument</label>
              <select
                value={selectedSymbol}
                onChange={(e) => setSelectedSymbol(e.target.value)}
                className="bg-gray-700 border border-gray-600 text-white px-3 py-2 rounded focus:outline-none focus:border-blue-500"
              >
                {instruments.map(instrument => (
                  <option key={instrument.symbol} value={instrument.symbol}>
                    {instrument.display_name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Timeframe</label>
              <select
                value={selectedTimeframe}
                onChange={(e) => setSelectedTimeframe(e.target.value)}
                className="bg-gray-700 border border-gray-600 text-white px-3 py-2 rounded focus:outline-none focus:border-blue-500"
              >
                <option value="1m">1 Minute</option>
                <option value="5m">5 Minutes</option>
                <option value="15m">15 Minutes</option>
                <option value="30m">30 Minutes</option>
                <option value="1h">1 Hour</option>
                <option value="4h">4 Hours</option>
                <option value="1d">1 Day</option>
              </select>
            </div>

            {/* Live Price Display */}
            {livePrices[selectedSymbol] && (
              <div className="ml-auto">
                <p className="text-sm text-gray-400">Live Price</p>
                <div className="flex items-center gap-4">
                  <div>
                    <span className="text-sm text-gray-400">Bid: </span>
                    <span className="font-mono text-green-400">{formatCurrency(livePrices[selectedSymbol].bid)}</span>
                  </div>
                  <div>
                    <span className="text-sm text-gray-400">Ask: </span>
                    <span className="font-mono text-red-400">{formatCurrency(livePrices[selectedSymbol].ask)}</span>
                  </div>
                  <div>
                    <span className="text-sm text-gray-400">Spread: </span>
                    <span className="font-mono">{formatCurrency(livePrices[selectedSymbol].spread, 4)}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Charts */}
        {chartData && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            {/* Price Chart */}
            <div className="lg:col-span-2 bg-gray-800 p-6 rounded-lg border border-gray-700">
              <h3 className="text-xl font-semibold mb-4">Price Chart</h3>
              <div style={{ height: '400px' }}>
                <Line
                  data={chartData.price}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        position: 'top' as const,
                        labels: { color: 'white' }
                      },
                    },
                    scales: {
                      x: {
                        type: 'time',
                        time: { unit: selectedTimeframe.includes('d') ? 'day' : 'hour' },
                        ticks: { color: 'white' },
                        grid: { color: 'rgba(255,255,255,0.1)' }
                      },
                      y: {
                        ticks: { color: 'white' },
                        grid: { color: 'rgba(255,255,255,0.1)' }
                      },
                    },
                  }}
                />
              </div>
            </div>

            {/* Volume Chart */}
            <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
              <h3 className="text-xl font-semibold mb-4">Volume</h3>
              <div style={{ height: '400px' }}>
                <Bar
                  data={chartData.volume}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: { display: false },
                    },
                    scales: {
                      x: {
                        ticks: { color: 'white' },
                        grid: { color: 'rgba(255,255,255,0.1)' }
                      },
                      y: {
                        ticks: { 
                          color: 'white',
                          callback: function(value) {
                            return formatVolume(value as number)
                          }
                        },
                        grid: { color: 'rgba(255,255,255,0.1)' }
                      },
                    },
                  }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Technical Indicators & Wyckoff Analysis */}
        {marketData && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Technical Indicators */}
            <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
              <h3 className="text-xl font-semibold mb-4">Technical Indicators</h3>
              {marketData.indicators.length > 0 ? (
                <div className="space-y-4">
                  {marketData.indicators.map((indicator, index) => (
                    <div key={index} className="flex justify-between items-center p-3 bg-gray-700 rounded">
                      <div>
                        <span className="font-semibold">{indicator.name}</span>
                        <span className="text-sm text-gray-400 ml-2">({indicator.type})</span>
                      </div>
                      <span className="font-mono text-blue-400">{formatCurrency(indicator.value)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-400">No indicators available</p>
              )}
            </div>

            {/* Wyckoff Analysis */}
            <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
              <h3 className="text-xl font-semibold mb-4">Wyckoff Analysis</h3>
              {marketData.wyckoff_patterns.length > 0 ? (
                <div className="space-y-4">
                  {marketData.wyckoff_patterns.map((pattern, index) => (
                    <div key={index} className="p-4 bg-gray-700 rounded">
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-semibold capitalize">{pattern.type}</span>
                        <span className="text-sm bg-blue-600 px-2 py-1 rounded">{pattern.phase}</span>
                      </div>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-400">Confidence:</span>
                          <span className="text-green-400">{(pattern.confidence * 100).toFixed(0)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">Key Levels:</span>
                          <span>{pattern.key_levels.length} levels</span>
                        </div>
                        <p className="text-gray-300 mt-2">{pattern.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-400">No Wyckoff patterns detected</p>
              )}
            </div>
          </div>
        )}

        {/* Loading State */}
        {isLoading && !marketData && (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-400 mx-auto mb-4"></div>
            <p className="text-gray-400">Loading market data...</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default MarketDataPage