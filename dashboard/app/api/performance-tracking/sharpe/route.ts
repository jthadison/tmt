/**
 * API endpoint for Sharpe ratio monitoring data
 * Connects to orchestrator performance tracking service
 */

import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    // First try to get real Sharpe ratio data from orchestrator
    console.log('Fetching real Sharpe ratio data from orchestrator...')

    const response = await fetch('http://localhost:8089/api/performance-tracking/sharpe-ratio', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      },
      timeout: 5000 // 5 second timeout
    })

    if (response.ok) {
      const data = await response.json()
      console.log('Successfully received real Sharpe ratio data:', data)

      // Transform real Sharpe data for frontend
      const sharpeData = {
        current_30day: data.sharpe_30day || 0,
        rolling_7day: data.sharpe_7day || 0,
        rolling_14day: data.sharpe_14day || 0,
        trend: data.trend || 'stable',
        target_threshold: data.target_threshold || 1.5
      }

      return NextResponse.json({
        success: true,
        data: sharpeData,
        timestamp: new Date().toISOString(),
        source: 'real_data'
      })
    } else {
      throw new Error(`Orchestrator responded with status: ${response.status}`)
    }

  } catch (error) {
    console.warn('Failed to fetch real Sharpe ratio data, using fallback:', error.message)

    // Only use mock data as fallback when real system is unavailable
    const mockData = {
      current_30day: 1.67,
      rolling_7day: 1.89,
      rolling_14day: 1.73,
      trend: 'improving',
      target_threshold: 1.5
    }

    return NextResponse.json({
      success: true,
      data: mockData,
      timestamp: new Date().toISOString(),
      source: 'fallback_mock',
      warning: 'Using mock data - orchestrator service unavailable'
    })
  }
}