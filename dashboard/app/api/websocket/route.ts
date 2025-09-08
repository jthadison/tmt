/**
 * WebSocket API for Real-time Updates
 * Provides Server-Sent Events for live trade and pricing updates
 */

import { NextRequest } from 'next/server'

export async function GET(request: NextRequest) {
  // Use Server-Sent Events instead of WebSocket for simplicity in Next.js
  const encoder = new TextEncoder()
  let isClosed = false
  let interval: NodeJS.Timeout | null = null
  
  const customReadable = new ReadableStream({
    start(controller) {
      // Helper function to safely enqueue data
      const safeEnqueue = (data: string) => {
        if (!isClosed) {
          try {
            controller.enqueue(encoder.encode(data))
          } catch (error) {
            console.warn('Failed to enqueue data, stream likely closed:', error)
            isClosed = true
            if (interval) {
              clearInterval(interval)
              interval = null
            }
          }
        }
      }
      
      // Send initial connection message
      const data = `data: ${JSON.stringify({
        type: 'connected',
        timestamp: Date.now(),
        message: 'Real-time updates connected'
      })}\n\n`
      
      safeEnqueue(data)
      
      // Set up periodic updates
      interval = setInterval(async () => {
        if (isClosed) {
          if (interval) {
            clearInterval(interval)
            interval = null
          }
          return
        }
        
        try {
          // Fetch live updates from orchestrator
          const updates = await fetchLiveUpdates()
          
          if (updates && !isClosed) {
            const data = `data: ${JSON.stringify(updates)}\n\n`
            safeEnqueue(data)
          }
          
          // Send heartbeat
          if (!isClosed) {
            const heartbeat = `data: ${JSON.stringify({
              type: 'heartbeat',
              timestamp: Date.now()
            })}\n\n`
            
            safeEnqueue(heartbeat)
          }
          
        } catch (error) {
          if (!isClosed) {
            console.error('WebSocket update error:', error)
            
            const errorData = `data: ${JSON.stringify({
              type: 'error',
              timestamp: Date.now(),
              error: 'Failed to fetch updates'
            })}\n\n`
            
            safeEnqueue(errorData)
          }
        }
      }, 5000) // Update every 5 seconds
      
      // Cleanup on close
      const cleanup = () => {
        isClosed = true
        if (interval) {
          clearInterval(interval)
          interval = null
        }
        try {
          controller.close()
        } catch (error) {
          // Already closed, ignore
        }
      }
      
      request.signal?.addEventListener('abort', cleanup)
      
      // Also listen for client disconnect
      setTimeout(() => {
        if (request.signal?.aborted) {
          cleanup()
        }
      }, 100)
    },
    
    cancel() {
      isClosed = true
      if (interval) {
        clearInterval(interval)
        interval = null
      }
    }
  })
  
  return new Response(customReadable, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET',
      'Access-Control-Allow-Headers': 'Cache-Control'
    }
  })
}

/**
 * Fetch live updates from trading system
 */
async function fetchLiveUpdates() {
  const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL || 'http://localhost:8089'
  
  try {
    // Get system status
    const statusResponse = await fetch(`${ORCHESTRATOR_URL}/health`, {
      method: 'GET',
      timeout: 3000
    })
    
    let systemStatus = null
    if (statusResponse.ok) {
      systemStatus = await statusResponse.json()
    }
    
    // Get recent trades (last few)
    const tradesResponse = await fetch(`${ORCHESTRATOR_URL}/analytics/trade-history`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        accountId: 'all-accounts',
        limit: 5,
        sortBy: 'openTime',
        sortOrder: 'desc'
      }),
      timeout: 3000
    })
    
    let recentTrades = []
    if (tradesResponse.ok) {
      const tradesData = await tradesResponse.json()
      recentTrades = tradesData.trades || []
    }
    
    return {
      type: 'update',
      timestamp: Date.now(),
      data: {
        systemStatus,
        recentTrades,
        openTradeCount: recentTrades.filter(t => t.status === 'open').length,
        totalPnL: recentTrades
          .filter(t => t.status === 'closed')
          .reduce((sum, t) => sum + (t.pnl || 0), 0)
      }
    }
    
  } catch (error) {
    console.warn('Failed to fetch live updates:', error)
    
    // Return mock data for development
    return {
      type: 'update',
      timestamp: Date.now(),
      data: {
        systemStatus: {
          running: true,
          trading_enabled: true,
          uptime_seconds: Math.floor(Date.now() / 1000) % 86400,
          connected_agents: 8,
          total_agents: 8
        },
        recentTrades: [],
        openTradeCount: Math.floor(Math.random() * 5),
        totalPnL: (Math.random() - 0.5) * 1000
      }
    }
  }
}