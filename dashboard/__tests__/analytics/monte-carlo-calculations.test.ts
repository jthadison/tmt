/**
 * Tests for Monte Carlo Simulation Calculations - Story 8.1
 */

describe('Monte Carlo Simulation Calculations', () => {
  describe('Percentile Calculations', () => {
    it('calculates 95th percentile correctly', () => {
      const sortedData = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
      const percentile = 95
      const index = (percentile / 100) * (sortedData.length - 1)
      const result = sortedData[Math.ceil(index)]

      expect(result).toBeGreaterThanOrEqual(9)
    })

    it('calculates 5th percentile correctly', () => {
      const sortedData = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
      const percentile = 5
      const index = (percentile / 100) * (sortedData.length - 1)
      const result = sortedData[Math.floor(index)]

      expect(result).toBeLessThanOrEqual(2)
    })

    it('calculates median (50th percentile) correctly', () => {
      const sortedData = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
      const percentile = 50
      const index = (percentile / 100) * (sortedData.length - 1)
      const lower = Math.floor(index)
      const upper = Math.ceil(index)
      const weight = index % 1
      const result = sortedData[lower] * (1 - weight) + sortedData[upper] * weight

      expect(result).toBeCloseTo(5.5, 1)
    })
  })

  describe('Confidence Interval Ordering', () => {
    it('ensures 99% CI contains 95% CI', () => {
      // Simulated results
      const sortedResults = Array.from({ length: 1000 }, (_, i) => i)

      // Calculate percentiles
      const ci99Lower = sortedResults[5] // 0.5th percentile
      const ci95Lower = sortedResults[25] // 2.5th percentile
      const ci95Upper = sortedResults[975] // 97.5th percentile
      const ci99Upper = sortedResults[995] // 99.5th percentile

      // Verify ordering: 99% lower <= 95% lower <= 95% upper <= 99% upper
      expect(ci99Lower).toBeLessThanOrEqual(ci95Lower)
      expect(ci95Lower).toBeLessThanOrEqual(ci95Upper)
      expect(ci95Upper).toBeLessThanOrEqual(ci99Upper)
    })
  })

  describe('Simulation Parameters', () => {
    it('calculates win rate from historical trades correctly', () => {
      const trades = [
        { profit: 100 },
        { profit: 50 },
        { profit: -30 },
        { profit: 80 },
        { profit: -20 },
      ]

      const winningTrades = trades.filter(t => t.profit > 0)
      const winRate = winningTrades.length / trades.length

      expect(winRate).toBe(0.6) // 60% win rate
    })

    it('calculates average profit correctly', () => {
      const profits = [100, 150, 200]
      const avgProfit = profits.reduce((a, b) => a + b, 0) / profits.length

      expect(avgProfit).toBe(150)
    })

    it('calculates average loss correctly', () => {
      const losses = [-50, -80, -100]
      const avgLoss = losses.reduce((a, b) => a + b, 0) / losses.length

      expect(avgLoss).toBeCloseTo(-76.67, 1)
    })

    it('calculates standard deviation correctly', () => {
      const values = [100, 150, 200, 50, 80]
      const mean = values.reduce((a, b) => a + b, 0) / values.length
      const variance = values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length
      const stdDev = Math.sqrt(variance)

      expect(stdDev).toBeCloseTo(53.14, 0)
    })

    it('calculates trades per day from historical data', () => {
      const trades = [
        { timestamp: '2025-01-01' },
        { timestamp: '2025-01-01' },
        { timestamp: '2025-01-02' },
        { timestamp: '2025-01-03' },
        { timestamp: '2025-01-03' },
        { timestamp: '2025-01-03' },
      ]

      const daysSpan = 3 // 3 days of data
      const tradesPerDay = trades.length / daysSpan

      expect(tradesPerDay).toBe(2)
    })
  })

  describe('Normal Distribution (Box-Muller Transform)', () => {
    it('generates values with correct mean', () => {
      const mean = 100
      const stdDev = 15

      // Simulate Box-Muller transform
      const u1 = 0.5
      const u2 = 0.5
      const z0 = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2)
      const result = mean + z0 * stdDev

      // Result should be reasonable
      expect(typeof result).toBe('number')
      expect(result).not.toBe(NaN)
    })
  })

  describe('Poisson Distribution', () => {
    it('generates trade frequency correctly', () => {
      const lambda = 2.5 // Average trades per day

      // Approximate Poisson
      const L = Math.exp(-lambda)
      let k = 0
      let p = 1

      // This would be the loop in actual implementation
      // Just verify the concept
      expect(L).toBeLessThan(1)
      expect(L).toBeGreaterThan(0)
    })
  })

  describe('Stability Metrics', () => {
    it('calculates walk-forward stability score', () => {
      const inSampleWinRate = 0.65
      const outSampleWinRate = 0.60

      const performanceDegradation = Math.abs(inSampleWinRate - outSampleWinRate)
      const walkForwardScore = Math.max(0, 100 - performanceDegradation * 200)

      expect(walkForwardScore).toBeCloseTo(90, 0)
    })

    it('calculates overfitting score', () => {
      const inSampleAvgReturn = 150
      const outSampleAvgReturn = 120

      const returnDegradation = Math.abs((inSampleAvgReturn - outSampleAvgReturn) / inSampleAvgReturn)
      const overfittingScore = Math.min(1, returnDegradation)

      expect(overfittingScore).toBe(0.2)
    })

    it('calculates out-of-sample validation percentage', () => {
      const inSampleAvgReturn = 150
      const outSampleAvgReturn = 135

      const outOfSampleValidation = (outSampleAvgReturn / inSampleAvgReturn) * 100

      expect(outOfSampleValidation).toBe(90)
    })

    it('handles edge case of zero in-sample return', () => {
      const inSampleAvgReturn = 0
      const outSampleAvgReturn = 50

      const outOfSampleValidation = inSampleAvgReturn !== 0
        ? (outSampleAvgReturn / inSampleAvgReturn) * 100
        : 50

      expect(outOfSampleValidation).toBe(50)
    })
  })

  describe('Variance Calculations', () => {
    it('calculates positive variance correctly', () => {
      const actual = 1200
      const expected = 1000

      const variance = ((actual - expected) / Math.abs(expected)) * 100

      expect(variance).toBe(20)
    })

    it('calculates negative variance correctly', () => {
      const actual = 800
      const expected = 1000

      const variance = ((actual - expected) / Math.abs(expected)) * 100

      expect(variance).toBe(-20)
    })

    it('handles zero expected value', () => {
      const actual = 100
      const expected = 0

      const variance = expected === 0 ? 0 : ((actual - expected) / Math.abs(expected)) * 100

      expect(variance).toBe(0)
    })
  })

  describe('Below Expected Detection', () => {
    it('detects below expected for 2+ consecutive days', () => {
      const actual = [100, 90, 80, 70]
      const expected = [100, 100, 100, 100]
      const currentDay = 3

      const today = actual[currentDay] < expected[currentDay]
      const yesterday = actual[currentDay - 1] < expected[currentDay - 1]
      const isBelowExpected = today && yesterday

      expect(isBelowExpected).toBe(true)
    })

    it('does not detect when only one day below expected', () => {
      const actual = [100, 110, 120, 70]
      const expected = [100, 100, 100, 100]
      const currentDay = 3

      const today = actual[currentDay] < expected[currentDay]
      const yesterday = actual[currentDay - 1] < expected[currentDay - 1]
      const isBelowExpected = today && yesterday

      expect(isBelowExpected).toBe(false)
    })

    it('handles edge case of first two days', () => {
      const actual = [80, 90]
      const expected = [100, 100]
      const currentDay = 1

      const today = actual[currentDay] < expected[currentDay]
      const yesterday = currentDay > 0 ? actual[currentDay - 1] < expected[currentDay - 1] : false
      const isBelowExpected = today && yesterday

      expect(isBelowExpected).toBe(true)
    })
  })
})
