/**
 * Unit tests for connection quality utility functions
 */

import {
  calculateConnectionQuality,
  getQualityColorClasses,
  formatDataAge
} from '@/utils/connectionQuality'
import { ConnectionMetrics } from '@/types/health'

describe('connectionQuality utility', () => {
  describe('calculateConnectionQuality', () => {
    it('should return "excellent" for optimal conditions', () => {
      const metrics: ConnectionMetrics = {
        wsStatus: 'connected',
        avgLatency: 50,
        dataAge: 1
      }

      expect(calculateConnectionQuality(metrics)).toBe('excellent')
    })

    it('should return "good" for slightly elevated latency', () => {
      const metrics: ConnectionMetrics = {
        wsStatus: 'connected',
        avgLatency: 150,
        dataAge: 1
      }

      expect(calculateConnectionQuality(metrics)).toBe('good')
    })

    it('should return "good" for slightly stale data', () => {
      const metrics: ConnectionMetrics = {
        wsStatus: 'connected',
        avgLatency: 50,
        dataAge: 3
      }

      expect(calculateConnectionQuality(metrics)).toBe('good')
    })

    it('should return "fair" for moderate latency', () => {
      const metrics: ConnectionMetrics = {
        wsStatus: 'connected',
        avgLatency: 300,
        dataAge: 1
      }

      expect(calculateConnectionQuality(metrics)).toBe('fair')
    })

    it('should return "fair" for moderately stale data', () => {
      const metrics: ConnectionMetrics = {
        wsStatus: 'connected',
        avgLatency: 50,
        dataAge: 7
      }

      expect(calculateConnectionQuality(metrics)).toBe('fair')
    })

    it('should return "poor" for high latency', () => {
      const metrics: ConnectionMetrics = {
        wsStatus: 'connected',
        avgLatency: 600,
        dataAge: 1
      }

      expect(calculateConnectionQuality(metrics)).toBe('poor')
    })

    it('should return "poor" for very stale data', () => {
      const metrics: ConnectionMetrics = {
        wsStatus: 'connected',
        avgLatency: 50,
        dataAge: 15
      }

      expect(calculateConnectionQuality(metrics)).toBe('poor')
    })

    it('should return "poor" for connecting status', () => {
      const metrics: ConnectionMetrics = {
        wsStatus: 'connecting',
        avgLatency: 50,
        dataAge: 1
      }

      expect(calculateConnectionQuality(metrics)).toBe('poor')
    })

    it('should return "poor" for error status', () => {
      const metrics: ConnectionMetrics = {
        wsStatus: 'error',
        avgLatency: 50,
        dataAge: 1
      }

      expect(calculateConnectionQuality(metrics)).toBe('poor')
    })

    it('should return "disconnected" for disconnected with very stale data', () => {
      const metrics: ConnectionMetrics = {
        wsStatus: 'disconnected',
        avgLatency: 0,
        dataAge: 35
      }

      expect(calculateConnectionQuality(metrics)).toBe('disconnected')
    })

    it('should return "poor" for disconnected with recent data', () => {
      const metrics: ConnectionMetrics = {
        wsStatus: 'disconnected',
        avgLatency: 0,
        dataAge: 5
      }

      expect(calculateConnectionQuality(metrics)).toBe('poor')
    })
  })

  describe('getQualityColorClasses', () => {
    it('should return correct classes for excellent quality', () => {
      const classes = getQualityColorClasses('excellent')

      expect(classes.text).toBe('text-green-400')
      expect(classes.bg).toBe('bg-green-500/10')
      expect(classes.label).toBe('Excellent')
    })

    it('should return correct classes for good quality', () => {
      const classes = getQualityColorClasses('good')

      expect(classes.text).toBe('text-lime-400')
      expect(classes.bg).toBe('bg-lime-500/10')
      expect(classes.label).toBe('Good')
    })

    it('should return correct classes for fair quality', () => {
      const classes = getQualityColorClasses('fair')

      expect(classes.text).toBe('text-yellow-400')
      expect(classes.bg).toBe('bg-yellow-500/10')
      expect(classes.label).toBe('Fair')
    })

    it('should return correct classes for poor quality', () => {
      const classes = getQualityColorClasses('poor')

      expect(classes.text).toBe('text-orange-400')
      expect(classes.bg).toBe('bg-orange-500/10')
      expect(classes.label).toBe('Poor')
    })

    it('should return correct classes for disconnected quality', () => {
      const classes = getQualityColorClasses('disconnected')

      expect(classes.text).toBe('text-red-400')
      expect(classes.bg).toBe('bg-red-500/10')
      expect(classes.label).toBe('Disconnected')
    })
  })

  describe('formatDataAge', () => {
    it('should return "just now" for very recent data', () => {
      expect(formatDataAge(0.5)).toBe('just now')
    })

    it('should format seconds correctly', () => {
      expect(formatDataAge(5)).toBe('5s ago')
      expect(formatDataAge(30)).toBe('30s ago')
      expect(formatDataAge(59)).toBe('59s ago')
    })

    it('should format minutes correctly', () => {
      expect(formatDataAge(60)).toBe('1m ago')
      expect(formatDataAge(120)).toBe('2m ago')
      expect(formatDataAge(3599)).toBe('59m ago')
    })

    it('should format hours correctly', () => {
      expect(formatDataAge(3600)).toBe('1h ago')
      expect(formatDataAge(7200)).toBe('2h ago')
      expect(formatDataAge(86400)).toBe('24h ago')
    })
  })
})
