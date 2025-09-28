/**
 * Live Prices API Endpoint
 * Real-time OANDA price feeds for current market prices
 */

import { NextRequest, NextResponse } from 'next/server'
import { getOandaClient } from '@/lib/oanda-client'

// Force dynamic rendering - prevent static generation during build
export const dynamic = 'force-dynamic'

const PRICING_CACHE = new Map<string, { price: number; bid: number; ask: number; timestamp: number }>()
const CACHE_TTL = 5000 // 5 seconds cache to prevent API abuse

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const instruments = searchParams.get('instruments')?.split(',') || []
    
    if (instruments.length === 0) {
      return NextResponse.json({ error: 'No instruments specified' }, { status: 400 })
    }

    const oandaClient = getOandaClient()
    const prices: Record<string, { price: number; bid: number; ask: number; timestamp: number }> = {}
    
    // Check cache first
    const now = Date.now()
    const cachedPrices: Record<string, { price: number; bid: number; ask: number; timestamp: number }> = {}
    const uncachedInstruments: string[] = []
    
    for (const instrument of instruments) {
      const cached = PRICING_CACHE.get(instrument)
      if (cached && (now - cached.timestamp) < CACHE_TTL) {
        cachedPrices[instrument] = cached
      } else {
        uncachedInstruments.push(instrument)
      }
    }
    
    // Fetch uncached prices from OANDA
    if (uncachedInstruments.length > 0) {
      try {
        // Get current pricing from OANDA
        const response = await fetch(
          `${oandaClient['baseUrl']}/v3/accounts/${oandaClient['config'].accountId}/pricing?instruments=${uncachedInstruments.join(',')}`,
          {
            headers: oandaClient['headers']
          }
        )
        
        if (response.ok) {
          const data = await response.json()
          
          for (const priceData of data.prices || []) {
            const instrument = priceData.instrument.replace('_', '/')
            const bid = parseFloat(priceData.bids?.[0]?.price || '0')
            const ask = parseFloat(priceData.asks?.[0]?.price || '0')
            const midPrice = (bid + ask) / 2
            
            const priceInfo = {
              price: midPrice,
              bid,
              ask,
              timestamp: now
            }
            
            prices[instrument] = priceInfo
            PRICING_CACHE.set(instrument, priceInfo)
          }
        } else {
          console.warn('OANDA pricing API error:', response.statusText)
          // Fall back to mock prices for development
          for (const instrument of uncachedInstruments) {
            const mockPrice = getMockPrice(instrument)
            prices[instrument] = mockPrice
            PRICING_CACHE.set(instrument, mockPrice)
          }
        }
      } catch (error) {
        console.warn('Failed to fetch OANDA prices:', error)
        
        // Fall back to mock prices
        for (const instrument of uncachedInstruments) {
          const mockPrice = getMockPrice(instrument)
          prices[instrument] = mockPrice
          PRICING_CACHE.set(instrument, mockPrice)
        }
      }
    }
    
    // Merge cached and fresh prices
    const allPrices = { ...cachedPrices, ...prices }
    
    return NextResponse.json({
      prices: allPrices,
      timestamp: now,
      source: uncachedInstruments.length > 0 ? 'oanda' : 'cache',
      cached: Object.keys(cachedPrices).length,
      fresh: Object.keys(prices).length
    })
    
  } catch (error) {
    console.error('Error fetching live prices:', error)
    return NextResponse.json(
      { error: 'Internal server error', details: error },
      { status: 500 }
    )
  }
}

/**
 * Generate realistic mock prices for development/fallback
 */
function getMockPrice(instrument: string): { price: number; bid: number; ask: number; timestamp: number } {
  const basePrices: Record<string, number> = {
    'EUR/USD': 1.0856,
    'GBP/USD': 1.2745,
    'USD/JPY': 148.25,
    'USD/CHF': 0.9012,
    'AUD/USD': 0.6523,
    'USD/CAD': 1.3654,
    'NZD/USD': 0.5987,
    'EUR/GBP': 0.8745,
    'EUR/JPY': 160.89,
    'GBP/JPY': 184.12
  }
  
  const basePrice = basePrices[instrument] || 1.0000
  
  // Add some realistic movement
  const variation = (Math.random() - 0.5) * 0.001 // ±0.1% variation
  const currentPrice = basePrice + variation
  
  // Calculate bid/ask spread (typical forex spread)
  const spread = basePrice * 0.0001 // 1 pip spread
  const bid = currentPrice - spread / 2
  const ask = currentPrice + spread / 2
  
  return {
    price: Math.round(currentPrice * 100000) / 100000,
    bid: Math.round(bid * 100000) / 100000,
    ask: Math.round(ask * 100000) / 100000,
    timestamp: Date.now()
  }
}

export async function POST(request: NextRequest) {
  // POST method for bulk price requests
  try {
    const { instruments } = await request.json()
    
    if (!Array.isArray(instruments)) {
      return NextResponse.json({ error: 'Instruments must be an array' }, { status: 400 })
    }
    
    // Redirect to GET with query params
    const params = new URLSearchParams({ instruments: instruments.join(',') })
    const url = new URL(request.url)
    url.search = params.toString()
    
    const getRequest = new NextRequest(url)
    return GET(getRequest)
    
  } catch (error) {
    return NextResponse.json({ error: 'Invalid request body' }, { status: 400 })
  }
}