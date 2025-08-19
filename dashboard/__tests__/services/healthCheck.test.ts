/**
 * Health Check Service Tests
 */

import HealthCheckService, { ServiceHealth, SystemHealth } from '@/services/healthCheck'

// Mock fetch
global.fetch = jest.fn()

describe('HealthCheckService', () => {
  let service: HealthCheckService
  
  beforeEach(() => {
    jest.clearAllMocks()
    service = new HealthCheckService({
      endpoints: {
        'Service1': {
          url: 'http://localhost:8001/health',
          timeout: 1000,
          critical: true
        },
        'Service2': {
          url: 'http://localhost:8002/health',
          timeout: 1000,
          critical: false
        }
      },
      checkInterval: 5000
    })
  })
  
  afterEach(() => {
    service.stop()
  })

  describe('checkNow', () => {
    it('should check all configured services', async () => {
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>
      
      mockFetch.mockImplementation((url) => {
        if (url === 'http://localhost:8001/health') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ status: 'healthy' })
          } as Response)
        } else if (url === 'http://localhost:8002/health') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ status: 'healthy' })
          } as Response)
        }
        return Promise.reject(new Error('Unknown URL'))
      })
      
      const health = await service.checkNow()
      
      expect(health.overall).toBe('healthy')
      expect(health.services).toHaveLength(2)
      expect(health.services[0].status).toBe('healthy')
      expect(health.services[1].status).toBe('healthy')
    })
    
    it('should handle service failures', async () => {
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>
      
      mockFetch.mockImplementation((url) => {
        if (url === 'http://localhost:8001/health') {
          return Promise.reject(new Error('Connection refused'))
        } else if (url === 'http://localhost:8002/health') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ status: 'healthy' })
          } as Response)
        }
        return Promise.reject(new Error('Unknown URL'))
      })
      
      const health = await service.checkNow()
      
      expect(health.overall).toBe('unhealthy') // Critical service is down
      expect(health.services).toHaveLength(2)
      
      const service1 = health.services.find(s => s.name === 'Service1')
      expect(service1?.status).toBe('unhealthy')
      expect(service1?.message).toContain('Connection refused')
      
      const service2 = health.services.find(s => s.name === 'Service2')
      expect(service2?.status).toBe('healthy')
    })
    
    it('should handle degraded services', async () => {
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>
      
      mockFetch.mockImplementation((url) => {
        if (url === 'http://localhost:8001/health') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ status: 'healthy' })
          } as Response)
        } else if (url === 'http://localhost:8002/health') {
          return Promise.resolve({
            ok: false,
            status: 503,
            statusText: 'Service Unavailable'
          } as Response)
        }
        return Promise.reject(new Error('Unknown URL'))
      })
      
      const health = await service.checkNow()
      
      expect(health.overall).toBe('degraded')
      
      const service2 = health.services.find(s => s.name === 'Service2')
      expect(service2?.status).toBe('unhealthy')
      expect(service2?.message).toContain('503')
    })
  })

  describe('subscribe', () => {
    it('should notify subscribers of health changes', async () => {
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'healthy' })
      } as Response)
      
      const callback = jest.fn()
      const unsubscribe = service.subscribe(callback)
      
      // Should receive initial state immediately
      expect(callback).toHaveBeenCalledTimes(1)
      expect(callback).toHaveBeenCalledWith(
        expect.objectContaining({
          overall: expect.any(String),
          services: expect.any(Array),
          timestamp: expect.any(Date),
          uptime: expect.any(Number)
        })
      )
      
      // Trigger a health check
      await service.checkNow()
      
      // Should receive updated state
      expect(callback).toHaveBeenCalledTimes(2)
      
      // Unsubscribe
      unsubscribe()
      
      // Should not receive further updates
      await service.checkNow()
      expect(callback).toHaveBeenCalledTimes(2)
    })
  })

  describe('start/stop', () => {
    it('should start and stop periodic health checks', () => {
      jest.useFakeTimers()
      
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'healthy' })
      } as Response)
      
      service.start()
      
      // Initial check should happen immediately
      expect(mockFetch).toHaveBeenCalled()
      
      const initialCallCount = mockFetch.mock.calls.length
      
      // Advance time by check interval
      jest.advanceTimersByTime(5000)
      
      // Should have made another check
      expect(mockFetch.mock.calls.length).toBeGreaterThan(initialCallCount)
      
      service.stop()
      
      const callCountAfterStop = mockFetch.mock.calls.length
      
      // Advance time again
      jest.advanceTimersByTime(5000)
      
      // Should not make more checks after stop
      expect(mockFetch.mock.calls.length).toBe(callCountAfterStop)
      
      jest.useRealTimers()
    })
  })

  describe('getSystemHealth', () => {
    it('should calculate overall health correctly', async () => {
      const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>
      
      // All healthy
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'healthy' })
      } as Response)
      
      await service.checkNow()
      let health = service.getSystemHealth()
      expect(health.overall).toBe('healthy')
      
      // One non-critical degraded
      mockFetch.mockImplementation((url) => {
        if (url === 'http://localhost:8001/health') {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ status: 'healthy' })
          } as Response)
        } else {
          return Promise.resolve({
            ok: false,
            status: 400,
            statusText: 'Bad Request'
          } as Response)
        }
      })
      
      await service.checkNow()
      health = service.getSystemHealth()
      expect(health.overall).toBe('degraded')
      
      // Critical service unhealthy
      mockFetch.mockImplementation((url) => {
        if (url === 'http://localhost:8001/health') {
          return Promise.reject(new Error('Connection failed'))
        } else {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ status: 'healthy' })
          } as Response)
        }
      })
      
      await service.checkNow()
      health = service.getSystemHealth()
      expect(health.overall).toBe('unhealthy')
    })
  })
})