/**
 * Tests for Sharpe Ratio API Endpoint - Story 8.1
 */

import { GET } from '@/app/api/analytics/sharpe-ratio/route'
import { NextRequest } from 'next/server'

describe('/api/analytics/sharpe-ratio', () => {
  it('returns Sharpe ratio data with default parameters', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/sharpe-ratio')
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toHaveProperty('currentSharpe')
    expect(data).toHaveProperty('rollingWindows')
    expect(data).toHaveProperty('historicalData')
    expect(data).toHaveProperty('interpretation')
    expect(data).toHaveProperty('thresholdLevel')
    expect(data).toHaveProperty('calculatedAt')
    expect(data).toHaveProperty('riskFreeRate')
    expect(data).toHaveProperty('totalTrades')
  })

  it('returns rolling windows for all periods', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/sharpe-ratio')
    const response = await GET(request)
    const data = await response.json()

    expect(data.rollingWindows).toHaveProperty('7d')
    expect(data.rollingWindows).toHaveProperty('14d')
    expect(data.rollingWindows).toHaveProperty('30d')
    expect(data.rollingWindows).toHaveProperty('90d')

    // Check rolling window structure
    expect(data.rollingWindows['7d']).toHaveProperty('value')
    expect(data.rollingWindows['7d']).toHaveProperty('trend')
    expect(data.rollingWindows['7d']).toHaveProperty('changePercent')
    expect(['up', 'down', 'stable']).toContain(data.rollingWindows['7d'].trend)
  })

  it('returns historical data array', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/sharpe-ratio')
    const response = await GET(request)
    const data = await response.json()

    expect(Array.isArray(data.historicalData)).toBe(true)
    expect(data.historicalData.length).toBeGreaterThan(0)

    // Check historical data structure
    const firstPoint = data.historicalData[0]
    expect(firstPoint).toHaveProperty('date')
    expect(firstPoint).toHaveProperty('sharpeRatio')
  })

  it('returns valid threshold level', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/sharpe-ratio')
    const response = await GET(request)
    const data = await response.json()

    const validThresholds = ['outstanding', 'excellent', 'good', 'acceptable', 'poor']
    expect(validThresholds).toContain(data.thresholdLevel)
  })

  it('accepts custom risk-free rate parameter', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/sharpe-ratio?riskFreeRate=0.03')
    const response = await GET(request)
    const data = await response.json()

    expect(data.riskFreeRate).toBe(0.03)
  })

  it('accepts custom period parameter', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/sharpe-ratio?period=90d')
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toHaveProperty('currentSharpe')
  })

  it('forces refresh when requested', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/sharpe-ratio?refresh=true')
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.calculatedAt).toBeLessThanOrEqual(Date.now())
  })

  it('returns correct Sharpe ratio interpretation for outstanding', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/sharpe-ratio')
    const response = await GET(request)
    const data = await response.json()

    if (data.currentSharpe >= 2.0) {
      expect(data.thresholdLevel).toBe('outstanding')
      expect(data.interpretation).toContain('Outstanding')
    }
  })

  it('returns numeric values for Sharpe ratios', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/sharpe-ratio')
    const response = await GET(request)
    const data = await response.json()

    expect(typeof data.currentSharpe).toBe('number')
    expect(typeof data.rollingWindows['7d'].value).toBe('number')
    expect(typeof data.rollingWindows['14d'].value).toBe('number')
    expect(typeof data.rollingWindows['30d'].value).toBe('number')
    expect(typeof data.rollingWindows['90d'].value).toBe('number')
  })

  it('returns valid change percentages', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/sharpe-ratio')
    const response = await GET(request)
    const data = await response.json()

    expect(typeof data.rollingWindows['7d'].changePercent).toBe('number')
    expect(typeof data.rollingWindows['14d'].changePercent).toBe('number')
    expect(typeof data.rollingWindows['30d'].changePercent).toBe('number')
    expect(typeof data.rollingWindows['90d'].changePercent).toBe('number')
  })

  it('returns total trades count', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/sharpe-ratio')
    const response = await GET(request)
    const data = await response.json()

    expect(typeof data.totalTrades).toBe('number')
    expect(data.totalTrades).toBeGreaterThanOrEqual(0)
  })
})
