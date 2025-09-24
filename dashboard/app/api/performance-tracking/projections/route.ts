/**
 * API endpoint for performance projections data
 * Connects to orchestrator performance tracking service
 */

import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    // First try to get real data from orchestrator
    console.log('Fetching real performance tracking data from orchestrator...')

    const response = await fetch('http://localhost:8090/api/performance-tracking/status', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      },
      timeout: 5000 // 5 second timeout
    })

    if (response.ok) {
      const data = await response.json()
      console.log('Successfully received real performance data:', data)

      // Use real data from the performance tracking system
      const projectionData = {
        expected_6month_pnl: 79563.0, // Forward testing baseline
        current_actual_pnl: data.current_pnl || 0,
        daily_expected: 79563.0 / 180, // 6 months = ~180 days
        weekly_expected: 79563.0 / 26, // 6 months = ~26 weeks
        monthly_expected: 79563.0 / 6, // 6 months
        confidence_lower_95: data.confidence_intervals?.lower_95 || 0,
        confidence_upper_95: data.confidence_intervals?.upper_95 || 0,
        confidence_lower_99: data.confidence_intervals?.lower_99 || 0,
        confidence_upper_99: data.confidence_intervals?.upper_99 || 0,
        days_elapsed: data.days_elapsed || Math.floor((Date.now() - new Date('2025-01-01').getTime()) / (1000 * 60 * 60 * 24)),
        variance_percentage: data.performance_variance?.percentage || 0
      }

      return NextResponse.json({
        success: true,
        data: projectionData,
        timestamp: new Date().toISOString(),
        source: 'real_data'
      })
    } else {
      throw new Error(`Orchestrator responded with status: ${response.status}`)
    }

  } catch (error) {
    console.warn('Failed to fetch real performance data, using fallback:', error.message)

    // Only use mock data as fallback when real system is unavailable
    const mockData = {
      expected_6month_pnl: 79563.0,
      current_actual_pnl: 12450.0,
      daily_expected: 442.0,
      weekly_expected: 3060.0,
      monthly_expected: 13260.0,
      confidence_lower_95: 10200.0,
      confidence_upper_95: 14800.0,
      confidence_lower_99: 9500.0,
      confidence_upper_99: 15600.0,
      days_elapsed: 28,
      variance_percentage: 0.7
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