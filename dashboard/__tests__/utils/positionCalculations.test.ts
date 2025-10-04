/**
 * Position Calculations Unit Tests
 */

import {
  calculateProgressToTarget,
  calculatePositionAge,
  isNearTarget,
  calculatePLPercentage,
  enrichPosition,
  formatInstrument,
  formatPrice,
  getPipValue,
} from '@/utils/positionCalculations'

describe('positionCalculations', () => {
  describe('calculateProgressToTarget', () => {
    it('should calculate progress for LONG position to TP', () => {
      const progress = calculateProgressToTarget(1.0800, 1.0850, 1.0900, 'long')
      expect(progress).toBeCloseTo(50, 1)
    })

    it('should calculate progress for SHORT position to TP', () => {
      const progress = calculateProgressToTarget(1.0800, 1.0750, 1.0700, 'short')
      expect(progress).toBeCloseTo(50, 1)
    })

    it('should clamp progress between 0 and 100', () => {
      const overProgress = calculateProgressToTarget(1.0800, 1.1000, 1.0900, 'long')
      expect(overProgress).toBe(100)

      const underProgress = calculateProgressToTarget(1.0800, 1.0700, 1.0900, 'long')
      expect(underProgress).toBe(0)
    })
  })

  describe('calculatePositionAge', () => {
    it('should format age in minutes for recent positions', () => {
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString()
      const age = calculatePositionAge(fiveMinutesAgo)
      expect(age).toBe('5m')
    })

    it('should format age in hours and minutes', () => {
      const twoHoursAgo = new Date(Date.now() - (2 * 60 * 60 * 1000 + 30 * 60 * 1000)).toISOString()
      const age = calculatePositionAge(twoHoursAgo)
      expect(age).toBe('2h 30m')
    })

    it('should format age in days for old positions', () => {
      const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString()
      const age = calculatePositionAge(threeDaysAgo)
      expect(age).toBe('3 days')
    })
  })

  describe('isNearTarget', () => {
    it('should return true when within 10 pips for non-JPY pairs', () => {
      const result = isNearTarget(1.0850, 1.0851, 'EUR_USD')
      expect(result).toBe(true)
    })

    it('should return false when more than 10 pips away', () => {
      const result = isNearTarget(1.0850, 1.0900, 'EUR_USD')
      expect(result).toBe(false)
    })

    it('should use different threshold for JPY pairs', () => {
      const result = isNearTarget(110.50, 110.60, 'USD_JPY')
      expect(result).toBe(true)
    })
  })

  describe('calculatePLPercentage', () => {
    it('should calculate P&L percentage correctly', () => {
      const percentage = calculatePLPercentage(100, 1.0800, 10000)
      expect(percentage).toBeCloseTo(0.926, 2)
    })

    it('should handle zero position value', () => {
      const percentage = calculatePLPercentage(100, 0, 0)
      expect(percentage).toBe(0)
    })
  })

  describe('enrichPosition', () => {
    it('should enrich raw position with calculated fields', () => {
      const rawPosition = {
        id: '123',
        instrument: 'EUR_USD',
        units: '10000',
        price: '1.0800',
        unrealizedPL: '100',
        openTime: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
        stopLoss: '1.0750',
        takeProfit: '1.0900',
        clientExtensions: {
          agent: 'Market Analysis',
        },
      }

      const enriched = enrichPosition(rawPosition, 1.0850)

      expect(enriched.direction).toBe('long')
      expect(enriched.units).toBe(10000)
      expect(enriched.currentPrice).toBe(1.0850)
      expect(enriched.stopLoss).toBe(1.0750)
      expect(enriched.takeProfit).toBe(1.0900)
      expect(enriched.agentSource).toBe('Market Analysis')
      expect(enriched.positionAge).toBeTruthy()
      expect(enriched.progressToTP).toBeGreaterThan(0)
    })
  })

  describe('formatInstrument', () => {
    it('should format instrument name with slash', () => {
      expect(formatInstrument('EUR_USD')).toBe('EUR/USD')
      expect(formatInstrument('GBP_JPY')).toBe('GBP/JPY')
    })
  })

  describe('formatPrice', () => {
    it('should format non-JPY pairs with 5 decimals', () => {
      expect(formatPrice(1.08456, 'EUR_USD')).toBe('1.08456')
    })

    it('should format JPY pairs with 3 decimals', () => {
      expect(formatPrice(110.456, 'USD_JPY')).toBe('110.456')
    })
  })

  describe('getPipValue', () => {
    it('should return correct pip value for non-JPY pairs', () => {
      expect(getPipValue('EUR_USD')).toBe(0.0001)
    })

    it('should return correct pip value for JPY pairs', () => {
      expect(getPipValue('USD_JPY')).toBe(0.01)
    })
  })
})
