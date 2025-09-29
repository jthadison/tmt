/**
 * Health Check Service
 * Monitors system components and provides real-time health status
 */

export interface ServiceHealth {
  name: string
  status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown'
  latency?: number
  lastChecked: Date
  message?: string
  details?: Record<string, any>
}

export interface SystemHealth {
  overall: 'healthy' | 'degraded' | 'unhealthy'
  services: ServiceHealth[]
  timestamp: Date
  uptime: number
}

export interface HealthCheckConfig {
  endpoints: {
    [key: string]: {
      url: string
      timeout?: number
      critical?: boolean
    }
  }
  checkInterval?: number
}

class HealthCheckService {
  private config: HealthCheckConfig
  private healthStatus: Map<string, ServiceHealth>
  private checkInterval: NodeJS.Timeout | null = null
  private startTime: Date
  private subscribers: Set<(health: SystemHealth) => void>

  constructor(config: HealthCheckConfig) {
    this.config = config
    this.healthStatus = new Map()
    this.startTime = new Date()
    this.subscribers = new Set()
  }

  /**
   * Start periodic health checks
   */
  start() {
    if (this.checkInterval) {
      return
    }

    // Initial check
    this.performHealthChecks()

    // Schedule periodic checks
    this.checkInterval = setInterval(
      () => this.performHealthChecks(),
      this.config.checkInterval || 30000
    )
  }

  /**
   * Stop health checks
   */
  stop() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval)
      this.checkInterval = null
    }
  }

  /**
   * Subscribe to health status updates
   */
  subscribe(callback: (health: SystemHealth) => void) {
    this.subscribers.add(callback)
    // Send current status immediately
    callback(this.getSystemHealth())
    
    return () => {
      this.subscribers.delete(callback)
    }
  }

  /**
   * Perform health checks for all configured services
   */
  private async performHealthChecks() {
    const checks = Object.entries(this.config.endpoints).map(
      async ([name, endpoint]) => {
        const health = await this.checkService(name, endpoint)
        this.healthStatus.set(name, health)
        return health
      }
    )

    await Promise.all(checks)
    this.notifySubscribers()
  }

  /**
   * Check individual service health
   */
  private async checkService(
    name: string,
    endpoint: { url: string; timeout?: number }
  ): Promise<ServiceHealth> {
    const startTime = Date.now()
    
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(
        () => controller.abort(),
        endpoint.timeout || 5000
      )

      const response = await fetch(endpoint.url, {
        method: 'GET',
        signal: controller.signal,
        headers: {
          'Accept': 'application/json'
        }
      })

      clearTimeout(timeoutId)
      const latency = Date.now() - startTime

      if (response.ok) {
        const data = await response.json().catch(() => ({}))
        
        return {
          name,
          status: 'healthy',
          latency,
          lastChecked: new Date(),
          details: data
        }
      } else {
        return {
          name,
          status: response.status >= 500 ? 'unhealthy' : 'degraded',
          latency,
          lastChecked: new Date(),
          message: `HTTP ${response.status}: ${response.statusText}`
        }
      }
    } catch (error: any) {
      return {
        name,
        status: 'unhealthy',
        lastChecked: new Date(),
        message: error.name === 'AbortError' 
          ? 'Request timeout' 
          : error.message || 'Connection failed'
      }
    }
  }

  /**
   * Get current system health
   */
  getSystemHealth(): SystemHealth {
    const services = Array.from(this.healthStatus.values())
    const criticalServices = Object.entries(this.config.endpoints)
      .filter(([_, endpoint]) => endpoint.critical)
      .map(([name]) => name)

    // Determine overall health
    let overall: 'healthy' | 'degraded' | 'unhealthy' = 'healthy'
    
    const hasUnhealthyCritical = services.some(
      s => criticalServices.includes(s.name) && s.status === 'unhealthy'
    )
    
    if (hasUnhealthyCritical) {
      overall = 'unhealthy'
    } else if (services.some(s => s.status !== 'healthy')) {
      overall = 'degraded'
    }

    return {
      overall,
      services,
      timestamp: new Date(),
      uptime: Date.now() - this.startTime.getTime()
    }
  }

  /**
   * Notify all subscribers of health status change
   */
  private notifySubscribers() {
    const health = this.getSystemHealth()
    this.subscribers.forEach(callback => {
      try {
        callback(health)
      } catch (error) {
        console.error('Error in health check subscriber:', error)
      }
    })
  }

  /**
   * Force immediate health check
   */
  async checkNow(): Promise<SystemHealth> {
    await this.performHealthChecks()
    return this.getSystemHealth()
  }
}

// Helper to determine if running in Docker
const isDocker = process.env.DOCKER_ENV === 'true' || process.env.NODE_ENV === 'production'

// Get service URL based on environment
const getServiceUrl = (serviceName: string, defaultPort: number): string => {
  // Always use hostname:port for client-side requests in production
  if (typeof window !== 'undefined') {
    // Client-side: use window location hostname with service port
    return `http://${window.location.hostname}:${defaultPort}/health`
  } else if (isDocker) {
    // Server-side Docker: use container names
    return `http://${serviceName}:${defaultPort}/health`
  } else {
    // Server-side local development: use localhost
    return `http://localhost:${defaultPort}/health`
  }
}

// Default configuration for the trading system - Updated for 8-agent ecosystem
// Made into a function to ensure dynamic URL generation at runtime
export const getDefaultHealthCheckConfig = (): HealthCheckConfig => ({
  endpoints: {
    'Market Analysis': {
      url: getServiceUrl('market-analysis', 8001),
      timeout: 3000,
      critical: true
    },
    'Strategy Analysis': {
      url: getServiceUrl('strategy-analysis', 8002),
      timeout: 3000,
      critical: true
    },
    'Parameter Optimization': {
      url: getServiceUrl('parameter-optimization', 8003),
      timeout: 3000,
      critical: true
    },
    'Learning Safety': {
      url: getServiceUrl('learning-safety', 8004),
      timeout: 3000,
      critical: true
    },
    'Disagreement Engine': {
      url: getServiceUrl('disagreement-engine', 8005),
      timeout: 3000,
      critical: true
    },
    'Data Collection': {
      url: getServiceUrl('data-collection', 8006),
      timeout: 3000,
      critical: true
    },
    'Continuous Improvement': {
      url: getServiceUrl('continuous-improvement', 8007),
      timeout: 3000,
      critical: false
    },
    'Pattern Detection': {
      url: getServiceUrl('pattern-detection', 8008),
      timeout: 3000,
      critical: false
    },
    'Execution Engine': {
      url: getServiceUrl('execution-engine', 8082),
      timeout: 3000,
      critical: true
    },
    'Orchestrator': {
      url: getServiceUrl('orchestrator', 8089),
      timeout: 3000,
      critical: true
    }
  },
  checkInterval: 15000 // Check every 15 seconds
})

// For backward compatibility
export const defaultHealthCheckConfig = getDefaultHealthCheckConfig()

// Singleton instance
let healthCheckInstance: HealthCheckService | null = null

/**
 * Get or create health check service instance
 */
export function getHealthCheckService(
  config?: HealthCheckConfig
): HealthCheckService {
  if (!healthCheckInstance) {
    // Use dynamic config generation if no config provided
    healthCheckInstance = new HealthCheckService(config || getDefaultHealthCheckConfig())
  }
  return healthCheckInstance
}

export default HealthCheckService