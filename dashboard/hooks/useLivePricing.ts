/**
 * Live Pricing Hook
 * Real-time price updates for trading instruments
 */

'use client'

import { useState, useEffect, useCallback, useRef } from 'react'

export interface LivePrice {
  instrument: string
  price: number
  bid: number
  ask: number
  timestamp: number
  change?: number
  changePercent?: number
}

export interface LivePriceUpdate {
  prices: Record<string, LivePrice>
  timestamp: number
  source: 'oanda' | 'cache' | 'mock'
  cached: number
  fresh: number
}

interface UseLivePricingOptions {
  /** Instruments to track */
  instruments: string[]
  /** Update interval in milliseconds */
  updateInterval?: number
  /** Enable automatic updates */
  enabled?: boolean
  /** Callback when prices update */
  onUpdate?: (update: LivePriceUpdate) => void
  /** Callback when error occurs */
  onError?: (error: Error) => void
}

interface UseLivePricingReturn {
  /** Current prices */
  prices: Record<string, LivePrice>
  /** Last update timestamp */
  lastUpdate: number
  /** Loading state */
  loading: boolean
  /** Error state */
  error: string | null
  /** Connection status */
  connected: boolean
  /** Manually refresh prices */
  refresh: () => Promise<void>
  /** Get specific instrument price */
  getPrice: (instrument: string) => LivePrice | null
  /** Calculate P&L for a position */
  calculatePnL: (instrument: string, entryPrice: number, units: number, side: 'buy' | 'sell') => number | null
}

const DEFAULT_UPDATE_INTERVAL = 10000 // 10 seconds
const MAX_RETRY_ATTEMPTS = 3
const RETRY_DELAY = 5000 // 5 seconds

export function useLivePricing({
  instruments,
  updateInterval = DEFAULT_UPDATE_INTERVAL,
  enabled = true,
  onUpdate,
  onError
}: UseLivePricingOptions): UseLivePricingReturn {
  const [prices, setPrices] = useState<Record<string, LivePrice>>({})
  const [lastUpdate, setLastUpdate] = useState<number>(0)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [connected, setConnected] = useState<boolean>(false)
  
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const retryAttempts = useRef<number>(0)
  const previousPrices = useRef<Record<string, LivePrice>>({})
  
  /**
   * Fetch live prices from API
   */
  const fetchPrices = useCallback(async (): Promise<void> => {
    if (!enabled || instruments.length === 0) return
    
    try {
      setLoading(true)
      setError(null)
      
      const response = await fetch(`/api/prices/live?instruments=${instruments.join(',')}`)
      
      if (!response.ok) {
        throw new Error(`Failed to fetch prices: ${response.statusText}`)
      }
      
      const data: LivePriceUpdate = await response.json()
      
      // Calculate price changes
      const updatedPrices: Record<string, LivePrice> = {}
      
      Object.entries(data.prices).forEach(([instrument, priceData]) => {
        const previousPrice = previousPrices.current[instrument]
        const change = previousPrice ? priceData.price - previousPrice.price : 0
        const changePercent = previousPrice && previousPrice.price > 0 
          ? (change / previousPrice.price) * 100 
          : 0
        
        updatedPrices[instrument] = {
          ...priceData,
          change,
          changePercent
        }
      })
      
      setPrices(updatedPrices)
      previousPrices.current = { ...updatedPrices }
      setLastUpdate(data.timestamp)
      setConnected(true)
      retryAttempts.current = 0
      
      // Call update callback
      if (onUpdate) {
        onUpdate({
          ...data,
          prices: updatedPrices
        })
      }
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      setError(errorMessage)
      setConnected(false)
      retryAttempts.current++
      
      if (onError) {
        onError(new Error(errorMessage))
      }
      
      console.error('Live pricing error:', errorMessage)
      
      // Retry logic
      if (retryAttempts.current < MAX_RETRY_ATTEMPTS) {
        setTimeout(() => {
          fetchPrices()
        }, RETRY_DELAY)
      }
      
    } finally {
      setLoading(false)
    }
  }, [enabled, instruments, onUpdate, onError])
  
  /**
   * Start price updates
   */
  const startUpdates = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
    }
    
    // Fetch immediately
    fetchPrices()
    
    // Set up recurring updates
    intervalRef.current = setInterval(fetchPrices, updateInterval)
  }, [fetchPrices, updateInterval])
  
  /**
   * Stop price updates
   */
  const stopUpdates = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    setConnected(false)
  }, [])
  
  /**
   * Manual refresh
   */
  const refresh = useCallback(async (): Promise<void> => {
    await fetchPrices()
  }, [fetchPrices])
  
  /**
   * Get specific instrument price
   */
  const getPrice = useCallback((instrument: string): LivePrice | null => {
    return prices[instrument] || null
  }, [prices])
  
  /**
   * Calculate P&L for a position
   */
  const calculatePnL = useCallback((
    instrument: string, 
    entryPrice: number, 
    units: number, 
    side: 'buy' | 'sell'
  ): number | null => {
    const currentPrice = prices[instrument]?.price
    if (!currentPrice || !entryPrice || !units) return null
    
    const priceDiff = currentPrice - entryPrice
    let pnl: number
    
    if (side === 'buy') {
      pnl = priceDiff * units
    } else {
      pnl = -priceDiff * units
    }
    
    // For forex, multiply by pip value (typically 10 for standard lots)
    // This is a simplified calculation - real implementation would use proper pip values
    const isForexPair = instrument.includes('/')
    if (isForexPair) {
      const pipValue = getPipValue(instrument)
      pnl = pnl * pipValue
    }
    
    return Math.round(pnl * 100) / 100 // Round to 2 decimal places
  }, [prices])
  
  /**
   * Get pip value for instrument
   */
  const getPipValue = (instrument: string): number => {
    // Simplified pip value calculation
    // In real implementation, this would consider account currency and position size
    if (instrument.includes('JPY')) {
      return 100 // JPY pairs have 2 decimal places
    }
    return 10000 // Most major pairs have 4 decimal places
  }
  
  /**
   * Setup and cleanup effects
   */
  useEffect(() => {
    if (enabled && instruments.length > 0) {
      startUpdates()
    } else {
      stopUpdates()
    }
    
    return () => {
      stopUpdates()
    }
  }, [enabled, instruments, startUpdates, stopUpdates])
  
  /**
   * Handle instruments change
   */
  useEffect(() => {
    if (enabled) {
      // Clear prices for instruments no longer tracked
      setPrices(prevPrices => {
        const newPrices: Record<string, LivePrice> = {}
        instruments.forEach(instrument => {
          if (prevPrices[instrument]) {
            newPrices[instrument] = prevPrices[instrument]
          }
        })
        return newPrices
      })
      
      // Reset retry attempts when instruments change
      retryAttempts.current = 0
    }
  }, [instruments, enabled])
  
  return {
    prices,
    lastUpdate,
    loading,
    error,
    connected,
    refresh,
    getPrice,
    calculatePnL
  }
}