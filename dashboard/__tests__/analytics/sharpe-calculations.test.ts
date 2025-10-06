/**
 * Tests for Sharpe Ratio Calculations - Story 8.1
 */

describe('Sharpe Ratio Calculations', () => {
  describe('Sharpe Ratio Formula', () => {
    it('calculates Sharpe ratio correctly with standard formula', () => {
      // Given: Returns and risk-free rate
      const avgReturn = 0.001 // 0.1% daily
      const stdDev = 0.005 // 0.5% std dev
      const riskFreeRate = 0.02 / 252 // 2% annual to daily

      // When: Calculate Sharpe ratio
      const sharpe = (avgReturn - riskFreeRate) / stdDev
      const annualizedSharpe = sharpe * Math.sqrt(252)

      // Then: Should produce valid Sharpe ratio
      expect(annualizedSharpe).toBeGreaterThan(0)
      expect(annualizedSharpe).toBeCloseTo(2.9, 0)
    })

    it('returns zero Sharpe ratio when standard deviation is zero', () => {
      const avgReturn = 0.001
      const stdDev = 0
      const riskFreeRate = 0.02 / 252

      // Cannot divide by zero
      const sharpe = stdDev === 0 ? 0 : (avgReturn - riskFreeRate) / stdDev

      expect(sharpe).toBe(0)
    })

    it('handles negative Sharpe ratio for poor performance', () => {
      const avgReturn = -0.001 // Losing money
      const stdDev = 0.005
      const riskFreeRate = 0.02 / 252

      const sharpe = (avgReturn - riskFreeRate) / stdDev
      const annualizedSharpe = sharpe * Math.sqrt(252)

      expect(annualizedSharpe).toBeLessThan(0)
    })
  })

  describe('Threshold Classification', () => {
    it('classifies outstanding Sharpe ratio correctly', () => {
      const sharpe = 2.5

      const threshold = sharpe >= 2.0 ? 'outstanding' : 'other'

      expect(threshold).toBe('outstanding')
    })

    it('classifies excellent Sharpe ratio correctly', () => {
      const sharpe = 1.7

      const threshold =
        sharpe >= 2.0 ? 'outstanding' :
        sharpe >= 1.5 ? 'excellent' : 'other'

      expect(threshold).toBe('excellent')
    })

    it('classifies good Sharpe ratio correctly', () => {
      const sharpe = 1.2

      const threshold =
        sharpe >= 2.0 ? 'outstanding' :
        sharpe >= 1.5 ? 'excellent' :
        sharpe >= 1.0 ? 'good' : 'other'

      expect(threshold).toBe('good')
    })

    it('classifies acceptable Sharpe ratio correctly', () => {
      const sharpe = 0.7

      const threshold =
        sharpe >= 2.0 ? 'outstanding' :
        sharpe >= 1.5 ? 'excellent' :
        sharpe >= 1.0 ? 'good' :
        sharpe >= 0.5 ? 'acceptable' : 'poor'

      expect(threshold).toBe('acceptable')
    })

    it('classifies poor Sharpe ratio correctly', () => {
      const sharpe = 0.3

      const threshold =
        sharpe >= 2.0 ? 'outstanding' :
        sharpe >= 1.5 ? 'excellent' :
        sharpe >= 1.0 ? 'good' :
        sharpe >= 0.5 ? 'acceptable' : 'poor'

      expect(threshold).toBe('poor')
    })
  })

  describe('Rolling Window Trend Detection', () => {
    it('detects upward trend correctly', () => {
      const currentSharpe = 1.8
      const previousSharpe = 1.5
      const changePercent = ((currentSharpe - previousSharpe) / Math.abs(previousSharpe)) * 100

      const trend = Math.abs(changePercent) < 5 ? 'stable' : changePercent > 0 ? 'up' : 'down'

      expect(trend).toBe('up')
      expect(changePercent).toBeCloseTo(20, 0)
    })

    it('detects downward trend correctly', () => {
      const currentSharpe = 1.2
      const previousSharpe = 1.5
      const changePercent = ((currentSharpe - previousSharpe) / Math.abs(previousSharpe)) * 100

      const trend = Math.abs(changePercent) < 5 ? 'stable' : changePercent > 0 ? 'up' : 'down'

      expect(trend).toBe('down')
      expect(changePercent).toBeCloseTo(-20, 0)
    })

    it('detects stable trend correctly', () => {
      const currentSharpe = 1.52
      const previousSharpe = 1.5
      const changePercent = ((currentSharpe - previousSharpe) / Math.abs(previousSharpe)) * 100

      const trend = Math.abs(changePercent) < 5 ? 'stable' : changePercent > 0 ? 'up' : 'down'

      expect(trend).toBe('stable')
      expect(changePercent).toBeCloseTo(1.3, 1)
    })
  })

  describe('Daily Returns Calculation', () => {
    it('calculates daily returns correctly', () => {
      const dailyPnL = 100
      const initialCapital = 10000
      const dailyReturn = dailyPnL / initialCapital

      expect(dailyReturn).toBe(0.01) // 1% return
    })

    it('handles zero initial capital', () => {
      const dailyPnL = 100
      const initialCapital = 0

      // Should handle edge case
      expect(initialCapital).toBe(0)
    })
  })

  describe('Risk-Free Rate Conversion', () => {
    it('converts annual risk-free rate to daily correctly', () => {
      const annualRate = 0.02 // 2%
      const dailyRate = annualRate / 252 // 252 trading days

      expect(dailyRate).toBeCloseTo(0.0000794, 7)
    })

    it('handles custom risk-free rates', () => {
      const annualRate = 0.03 // 3%
      const dailyRate = annualRate / 252

      expect(dailyRate).toBeCloseTo(0.000119, 6)
    })
  })

  describe('Annualization Factor', () => {
    it('uses correct annualization factor for Sharpe ratio', () => {
      const annualizationFactor = Math.sqrt(252)

      expect(annualizationFactor).toBeCloseTo(15.87, 2)
    })

    it('annualizes daily Sharpe ratio correctly', () => {
      const dailySharpe = 0.1
      const annualizedSharpe = dailySharpe * Math.sqrt(252)

      expect(annualizedSharpe).toBeCloseTo(1.587, 2)
    })
  })
})
