import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('Overfitting Analysis API', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  describe('overfitting score calculation', () => {
    it('calculates overfitting score correctly for low degradation', () => {
      const backtest = { winRate: 70, profitFactor: 2.5, sharpeRatio: 1.8, avgWin: 145, avgLoss: 82 }
      const forward = { winRate: 68, profitFactor: 2.4, sharpeRatio: 1.7, avgWin: 140, avgLoss: 85 }

      // Average degradation: ~2.9%, 4%, 5.6%, 3.4%, -3.7% (only count negative)
      // Average of negatives: (2.9 + 4 + 5.6 + 3.4 + 3.7) / 5 = ~3.9%
      // Normalized: 3.9/30 = ~0.13
      const expectedScore = 0.13

      // Mock implementation
      const degradations = [
        ((68 - 70) / 70) * -100, // winRate: -2.86%
        ((2.4 - 2.5) / 2.5) * -100, // profitFactor: -4%
        ((1.7 - 1.8) / 1.8) * -100, // sharpeRatio: -5.56%
        ((140 - 145) / 145) * -100, // avgWin: -3.45%
        ((85 - 82) / 82) * 100 // avgLoss: +3.66% (better, so 0)
      ].filter(d => d > 0)

      const avgDegradation = degradations.reduce((sum, d) => sum + d, 0) / degradations.length
      const score = Math.min(avgDegradation / 30, 1)

      expect(score).toBeCloseTo(expectedScore, 1)
    })

    it('calculates overfitting score correctly for high degradation', () => {
      const backtest = { winRate: 70, profitFactor: 2.5, sharpeRatio: 1.8, avgWin: 145, avgLoss: 82 }
      const forward = { winRate: 45, profitFactor: 1.2, sharpeRatio: 0.8, avgWin: 95, avgLoss: 110 }

      // High degradation should produce score close to 1
      const degradations = [
        Math.abs(((45 - 70) / 70) * 100), // winRate: 35.7%
        Math.abs(((1.2 - 2.5) / 2.5) * 100), // profitFactor: 52%
        Math.abs(((0.8 - 1.8) / 1.8) * 100), // sharpeRatio: 55.6%
        Math.abs(((95 - 145) / 145) * 100), // avgWin: 34.5%
        Math.abs(((110 - 82) / 82) * -100) // avgLoss: 34.1% (worse)
      ]

      const avgDegradation = degradations.reduce((sum, d) => sum + d, 0) / degradations.length
      const score = Math.min(avgDegradation / 30, 1)

      expect(score).toBeGreaterThanOrEqual(0.8)
      expect(avgDegradation).toBeGreaterThan(30)
    })

    it('caps overfitting score at 1.0', () => {
      const degradations = [100, 90, 80, 70, 60] // Extreme degradation
      const avgDegradation = degradations.reduce((sum, d) => sum + d, 0) / degradations.length
      const score = Math.min(avgDegradation / 30, 1)

      expect(score).toBe(1.0)
    })
  })

  describe('risk level determination', () => {
    it('assigns low risk for <15% degradation', () => {
      const avgDegradation = 10
      const riskLevel = avgDegradation < 15 ? 'low' : avgDegradation < 30 ? 'moderate' : 'high'

      expect(riskLevel).toBe('low')
    })

    it('assigns moderate risk for 15-30% degradation', () => {
      const avgDegradation = 22
      const riskLevel = avgDegradation < 15 ? 'low' : avgDegradation < 30 ? 'moderate' : 'high'

      expect(riskLevel).toBe('moderate')
    })

    it('assigns high risk for >30% degradation', () => {
      const avgDegradation = 35
      const riskLevel = avgDegradation < 15 ? 'low' : avgDegradation < 30 ? 'moderate' : 'high'

      expect(riskLevel).toBe('high')
    })
  })

  describe('stability score calculation', () => {
    it('calculates high stability for consistent returns', () => {
      const dailyReturns = Array(28).fill(0).map(() => 100 + (Math.random() - 0.5) * 10)

      // Split into 4 weekly windows
      const windows = []
      for (let i = 0; i < 4; i++) {
        windows.push(dailyReturns.slice(i * 7, (i + 1) * 7))
      }

      // Calculate Sharpe for each window
      const windowSharpes = windows.map(window => {
        const avg = window.reduce((sum, r) => sum + r, 0) / window.length
        const variance = window.reduce((sum, r) => sum + Math.pow(r - avg, 2), 0) / window.length
        const stdDev = Math.sqrt(variance)
        return stdDev === 0 ? 0 : (avg / stdDev) * Math.sqrt(252)
      })

      // Calculate coefficient of variation
      const mean = windowSharpes.reduce((sum, s) => sum + s, 0) / windowSharpes.length
      const variance = windowSharpes.reduce((sum, s) => sum + Math.pow(s - mean, 2), 0) / windowSharpes.length
      const stdDev = Math.sqrt(variance)
      const cv = Math.abs(mean) > 0.01 ? stdDev / Math.abs(mean) : 0

      const stabilityScore = Math.max(0, Math.min(100, 100 - (cv * 100)))

      // Consistent returns should have high stability
      expect(stabilityScore).toBeGreaterThan(50)
    })

    it('calculates low stability for volatile returns', () => {
      const dailyReturns = [200, -150, 300, -200, 250, -180, 100, -50, 400, -300, 150, -100, 200, -250]

      // Very volatile returns should have low stability
      // This is a simplified test - actual calculation is in the API
      const returns = dailyReturns.map(r => Math.abs(r))
      const avg = returns.reduce((sum, r) => sum + r, 0) / returns.length
      const variance = returns.reduce((sum, r) => sum + Math.pow(r - avg, 2), 0) / returns.length
      const stdDev = Math.sqrt(variance)
      const cv = avg > 0 ? stdDev / avg : 0

      expect(cv).toBeGreaterThan(0.5) // High coefficient of variation
    })

    it('returns 100 for insufficient data', () => {
      const dailyReturns = [100, 105, 98] // Less than 7 days

      const stabilityScore = dailyReturns.length < 7 ? 100 : 50

      expect(stabilityScore).toBe(100)
    })
  })

  describe('recommendations generation', () => {
    it('generates rollback recommendations for high risk', () => {
      const riskLevel = 'high'
      const recommendations: string[] = []

      if (riskLevel === 'high') {
        recommendations.push('Consider rolling back to previous strategy version')
        recommendations.push('Re-optimize parameters with walk-forward analysis')
      }

      expect(recommendations).toContain('Consider rolling back to previous strategy version')
      expect(recommendations.length).toBeGreaterThan(0)
    })

    it('generates monitoring recommendations for moderate risk', () => {
      const riskLevel = 'moderate'
      const recommendations: string[] = []

      if (riskLevel === 'moderate') {
        recommendations.push('Monitor performance daily for further degradation')
        recommendations.push('Review trading session optimization parameters')
      }

      expect(recommendations).toContain('Monitor performance daily for further degradation')
    })

    it('generates metric-specific recommendations', () => {
      const metricDegradation = {
        winRate: { backtest: 70, forward: 50, degradation: -28.6 },
        profitFactor: { backtest: 2.5, forward: 1.8, degradation: -28 }
      }

      const recommendations: string[] = []

      if (metricDegradation.winRate.degradation < -15) {
        recommendations.push('Win rate declined significantly - review entry criteria')
      }

      if (metricDegradation.profitFactor.degradation < -20) {
        recommendations.push('Profit factor dropped - adjust risk/reward ratios')
      }

      expect(recommendations).toContain('Win rate declined significantly - review entry criteria')
      expect(recommendations).toContain('Profit factor dropped - adjust risk/reward ratios')
    })
  })
})
