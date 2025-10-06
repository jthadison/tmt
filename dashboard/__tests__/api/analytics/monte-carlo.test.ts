/**
 * Tests for Monte Carlo API Endpoint - Story 8.1
 */

import { GET } from '@/app/api/analytics/monte-carlo/route'
import { NextRequest } from 'next/server'

describe('/api/analytics/monte-carlo', () => {
  it('returns Monte Carlo simulation data with default parameters', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/monte-carlo')
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.monteCarlo).toHaveProperty('expectedTrajectory')
    expect(data.monteCarlo).toHaveProperty('confidenceIntervals')
    expect(data.monteCarlo).toHaveProperty('simulationsRun')
    expect(data.monteCarlo).toHaveProperty('parameters')
    expect(data.monteCarlo).toHaveProperty('calculatedAt')
    expect(data.monteCarlo).toHaveProperty('cachedUntil')
  })

  it('returns expected trajectory with correct length', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/monte-carlo?days=180')
    const response = await GET(request)
    const data = await response.json()

    expect(Array.isArray(data.monteCarlo.expectedTrajectory)).toBe(true)
    expect(data.monteCarlo.expectedTrajectory.length).toBe(180)
  })

  it('returns 95% confidence intervals', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/monte-carlo')
    const response = await GET(request)
    const data = await response.json()

    expect(data.monteCarlo.confidenceIntervals).toHaveProperty('95')
    expect(data.monteCarlo.confidenceIntervals['95']).toHaveProperty('lower')
    expect(data.monteCarlo.confidenceIntervals['95']).toHaveProperty('upper')

    expect(Array.isArray(data.monteCarlo.confidenceIntervals['95'].lower)).toBe(true)
    expect(Array.isArray(data.monteCarlo.confidenceIntervals['95'].upper)).toBe(true)
  })

  it('returns 99% confidence intervals', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/monte-carlo')
    const response = await GET(request)
    const data = await response.json()

    expect(data.monteCarlo.confidenceIntervals).toHaveProperty('99')
    expect(data.monteCarlo.confidenceIntervals['99']).toHaveProperty('lower')
    expect(data.monteCarlo.confidenceIntervals['99']).toHaveProperty('upper')
  })

  it('returns simulation parameters', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/monte-carlo')
    const response = await GET(request)
    const data = await response.json()

    expect(data.monteCarlo.parameters).toHaveProperty('winRate')
    expect(data.monteCarlo.parameters).toHaveProperty('avgProfit')
    expect(data.monteCarlo.parameters).toHaveProperty('avgLoss')
    expect(data.monteCarlo.parameters).toHaveProperty('stdDev')
    expect(data.monteCarlo.parameters).toHaveProperty('tradesPerDay')

    // Validate parameter ranges
    expect(data.monteCarlo.parameters.winRate).toBeGreaterThanOrEqual(0)
    expect(data.monteCarlo.parameters.winRate).toBeLessThanOrEqual(1)
  })

  it('accepts custom days parameter', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/monte-carlo?days=90')
    const response = await GET(request)
    const data = await response.json()

    expect(data.monteCarlo.expectedTrajectory.length).toBe(90)
    expect(data.monteCarlo.confidenceIntervals['95'].lower.length).toBe(90)
    expect(data.monteCarlo.confidenceIntervals['95'].upper.length).toBe(90)
  })

  it('accepts custom simulations parameter', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/monte-carlo?simulations=500')
    const response = await GET(request)
    const data = await response.json()

    expect(data.monteCarlo.simulationsRun).toBe(500)
  })

  it('validates days parameter range', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/monte-carlo?days=500')
    const response = await GET(request)

    expect(response.status).toBe(400)
    const data = await response.json()
    expect(data.error).toContain('Days must be between 1 and 365')
  })

  it('validates simulations parameter range', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/monte-carlo?simulations=50000')
    const response = await GET(request)

    expect(response.status).toBe(400)
    const data = await response.json()
    expect(data.error).toContain('Simulations must be between 100 and 10000')
  })

  it('returns stability metrics when requested', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/monte-carlo?stability=true')
    const response = await GET(request)
    const data = await response.json()

    expect(data).toHaveProperty('stability')
    if (data.stability) {
      expect(data.stability).toHaveProperty('walkForwardScore')
      expect(data.stability).toHaveProperty('overfittingScore')
      expect(data.stability).toHaveProperty('outOfSampleValidation')
    }
  })

  it('does not return stability metrics by default', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/monte-carlo')
    const response = await GET(request)
    const data = await response.json()

    expect(data.stability).toBeUndefined()
  })

  it('confidence intervals maintain proper ordering', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/monte-carlo')
    const response = await GET(request)
    const data = await response.json()

    const ci95 = data.monteCarlo.confidenceIntervals['95']
    const ci99 = data.monteCarlo.confidenceIntervals['99']

    // For each day, check ordering: 99% lower <= 95% lower <= expected <= 95% upper <= 99% upper
    for (let i = 0; i < data.monteCarlo.expectedTrajectory.length; i++) {
      expect(ci99.lower[i]).toBeLessThanOrEqual(ci95.lower[i])
      expect(ci95.upper[i]).toBeLessThanOrEqual(ci99.upper[i])
    }
  })

  it('returns numeric values for all trajectories', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/monte-carlo')
    const response = await GET(request)
    const data = await response.json()

    data.monteCarlo.expectedTrajectory.forEach((value: any) => {
      expect(typeof value).toBe('number')
    })

    data.monteCarlo.confidenceIntervals['95'].lower.forEach((value: any) => {
      expect(typeof value).toBe('number')
    })

    data.monteCarlo.confidenceIntervals['95'].upper.forEach((value: any) => {
      expect(typeof value).toBe('number')
    })
  })

  it('returns valid timestamp values', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/monte-carlo')
    const response = await GET(request)
    const data = await response.json()

    expect(data.monteCarlo.calculatedAt).toBeGreaterThan(0)
    expect(data.monteCarlo.cachedUntil).toBeGreaterThan(data.monteCarlo.calculatedAt)
  })

  it('handles refresh parameter', async () => {
    const request = new NextRequest('http://localhost:3000/api/analytics/monte-carlo?refresh=true')
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.monteCarlo.calculatedAt).toBeLessThanOrEqual(Date.now())
  })
})
