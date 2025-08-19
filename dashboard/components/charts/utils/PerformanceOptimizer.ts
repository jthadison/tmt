/**
 * Performance Optimization Utilities
 * Story 9.4: Performance optimization for <100ms real-time update requirements
 * 
 * FEATURES: Data throttling, rendering optimization, memory management, batching
 */

/**
 * Performance optimization configuration
 */
export interface PerformanceConfig {
  /** Maximum update frequency in milliseconds */
  maxUpdateFrequency: number
  /** Maximum number of data points to render */
  maxDataPoints: number
  /** Enable data point sampling for performance */
  enableSampling: boolean
  /** Batch size for updates */
  batchSize: number
  /** Memory management threshold in MB */
  memoryThreshold: number
  /** Enable performance monitoring */
  enableMonitoring: boolean
  /** Debounce delay for resize events */
  resizeDebounceMs: number
}

/**
 * Default performance configuration
 */
export const DEFAULT_PERFORMANCE_CONFIG: PerformanceConfig = {
  maxUpdateFrequency: 50, // 50ms = 20fps
  maxDataPoints: 5000,
  enableSampling: true,
  batchSize: 10,
  memoryThreshold: 50, // 50MB
  enableMonitoring: true,
  resizeDebounceMs: 100
}

/**
 * Performance metrics tracking
 */
export class PerformanceTracker {
  private metrics: Map<string, number[]> = new Map()
  private startTimes: Map<string, number> = new Map()
  private config: PerformanceConfig

  constructor(config: PerformanceConfig = DEFAULT_PERFORMANCE_CONFIG) {
    this.config = config
  }

  /**
   * Start tracking a metric
   */
  startTracking(metricName: string): void {
    this.startTimes.set(metricName, performance.now())
  }

  /**
   * Stop tracking and record metric
   */
  stopTracking(metricName: string): number {
    const startTime = this.startTimes.get(metricName)
    if (!startTime) return 0

    const duration = performance.now() - startTime
    
    if (!this.metrics.has(metricName)) {
      this.metrics.set(metricName, [])
    }

    const metricArray = this.metrics.get(metricName)!
    metricArray.push(duration)

    // Keep only last 100 measurements
    if (metricArray.length > 100) {
      metricArray.splice(0, metricArray.length - 100)
    }

    this.startTimes.delete(metricName)
    return duration
  }

  /**
   * Get average for a metric
   */
  getAverage(metricName: string): number {
    const values = this.metrics.get(metricName)
    if (!values || values.length === 0) return 0

    const sum = values.reduce((a, b) => a + b, 0)
    return sum / values.length
  }

  /**
   * Get latest value for a metric
   */
  getLatest(metricName: string): number {
    const values = this.metrics.get(metricName)
    if (!values || values.length === 0) return 0
    return values[values.length - 1]
  }

  /**
   * Get all metrics summary
   */
  getSummary(): Record<string, { average: number; latest: number; count: number }> {
    const summary: Record<string, { average: number; latest: number; count: number }> = {}

    for (const [name, values] of this.metrics.entries()) {
      summary[name] = {
        average: this.getAverage(name),
        latest: this.getLatest(name),
        count: values.length
      }
    }

    return summary
  }

  /**
   * Clear all metrics
   */
  clear(): void {
    this.metrics.clear()
    this.startTimes.clear()
  }
}

/**
 * Data throttling and batching utilities
 */
export class DataThrottler<T> {
  private queue: T[] = []
  private lastUpdate: number = 0
  private batchTimeout: NodeJS.Timeout | null = null
  private config: PerformanceConfig

  constructor(
    private onUpdate: (batch: T[]) => void,
    config: PerformanceConfig = DEFAULT_PERFORMANCE_CONFIG
  ) {
    this.config = config
  }

  /**
   * Add data to queue with throttling
   */
  addData(data: T): void {
    this.queue.push(data)

    const now = Date.now()
    const timeSinceLastUpdate = now - this.lastUpdate

    // If enough time has passed or queue is full, process immediately
    if (timeSinceLastUpdate >= this.config.maxUpdateFrequency || 
        this.queue.length >= this.config.batchSize) {
      this.processQueue()
    } else if (!this.batchTimeout) {
      // Schedule processing
      const remainingTime = this.config.maxUpdateFrequency - timeSinceLastUpdate
      this.batchTimeout = setTimeout(() => {
        this.processQueue()
      }, remainingTime)
    }
  }

  /**
   * Process queued data
   */
  private processQueue(): void {
    if (this.queue.length === 0) return

    const batch = this.queue.splice(0)
    this.lastUpdate = Date.now()
    
    if (this.batchTimeout) {
      clearTimeout(this.batchTimeout)
      this.batchTimeout = null
    }

    this.onUpdate(batch)
  }

  /**
   * Force flush all queued data
   */
  flush(): void {
    this.processQueue()
  }

  /**
   * Clear queue
   */
  clear(): void {
    this.queue = []
    if (this.batchTimeout) {
      clearTimeout(this.batchTimeout)
      this.batchTimeout = null
    }
  }
}

/**
 * Data sampling for large datasets
 */
export class DataSampler {
  /**
   * Sample data points using largest triangle three buckets algorithm
   */
  static sampleLTTB<T extends { timestamp: number; [key: string]: any }>(
    data: T[],
    threshold: number
  ): T[] {
    if (data.length <= threshold) return data
    if (threshold < 3) return data.slice(0, threshold)

    const sampled: T[] = []
    sampled.push(data[0]) // Always keep first point

    const bucketSize = (data.length - 2) / (threshold - 2)

    for (let i = 0; i < threshold - 2; i++) {
      const bucketStart = Math.floor((i + 1) * bucketSize) + 1
      const bucketEnd = Math.floor((i + 2) * bucketSize) + 1
      const bucketMiddle = Math.floor((bucketStart + bucketEnd) / 2)

      // Get average of next bucket for triangle calculation
      let avgX = 0
      let avgY = 0
      const nextBucketStart = Math.min(bucketEnd, data.length - 1)
      const nextBucketEnd = Math.min(Math.floor((i + 3) * bucketSize) + 1, data.length - 1)

      for (let j = nextBucketStart; j < nextBucketEnd; j++) {
        avgX += data[j].timestamp
        avgY += this.getNumericValue(data[j])
      }
      avgX /= (nextBucketEnd - nextBucketStart)
      avgY /= (nextBucketEnd - nextBucketStart)

      // Find point in current bucket that forms largest triangle
      let maxArea = 0
      let selectedIndex = bucketStart
      const prevPoint = sampled[sampled.length - 1]

      for (let j = bucketStart; j < bucketEnd && j < data.length; j++) {
        const area = Math.abs(
          (prevPoint.timestamp - avgX) * (this.getNumericValue(data[j]) - prevPoint.timestamp) -
          (prevPoint.timestamp - data[j].timestamp) * (avgY - prevPoint.timestamp)
        )

        if (area > maxArea) {
          maxArea = area
          selectedIndex = j
        }
      }

      sampled.push(data[selectedIndex])
    }

    sampled.push(data[data.length - 1]) // Always keep last point
    return sampled
  }

  /**
   * Simple uniform sampling
   */
  static sampleUniform<T>(data: T[], targetSize: number): T[] {
    if (data.length <= targetSize) return data

    const step = data.length / targetSize
    const sampled: T[] = []

    for (let i = 0; i < targetSize; i++) {
      const index = Math.floor(i * step)
      sampled.push(data[index])
    }

    return sampled
  }

  /**
   * Extract numeric value for triangle calculation
   */
  private static getNumericValue(point: any): number {
    if (typeof point === 'number') return point
    if (point.close !== undefined) return point.close
    if (point.value !== undefined) return point.value
    if (point.y !== undefined) return point.y
    return 0
  }
}

/**
 * Memory management utilities
 */
export class MemoryManager {
  private config: PerformanceConfig
  private cleanupCallbacks: Array<() => void> = []

  constructor(config: PerformanceConfig = DEFAULT_PERFORMANCE_CONFIG) {
    this.config = config
  }

  /**
   * Register cleanup callback
   */
  registerCleanup(callback: () => void): void {
    this.cleanupCallbacks.push(callback)
  }

  /**
   * Check memory usage and trigger cleanup if needed
   */
  checkMemoryUsage(): void {
    if (this.getMemoryUsage() > this.config.memoryThreshold) {
      this.runCleanup()
    }
  }

  /**
   * Get estimated memory usage in MB
   */
  getMemoryUsage(): number {
    if ('memory' in performance) {
      return (performance as any).memory.usedJSHeapSize / 1024 / 1024
    }
    return 0
  }

  /**
   * Run cleanup callbacks
   */
  runCleanup(): void {
    this.cleanupCallbacks.forEach(callback => {
      try {
        callback()
      } catch (error) {
        console.warn('Cleanup callback error:', error)
      }
    })
  }
}

/**
 * Rendering optimization utilities
 */
export class RenderOptimizer {
  private rafId: number | null = null
  private pendingUpdates = new Set<() => void>()

  /**
   * Schedule update for next animation frame
   */
  scheduleUpdate(updateFn: () => void): void {
    this.pendingUpdates.add(updateFn)

    if (this.rafId === null) {
      this.rafId = requestAnimationFrame(() => {
        const updates = Array.from(this.pendingUpdates)
        this.pendingUpdates.clear()
        this.rafId = null

        // Execute all pending updates in a single frame
        updates.forEach(updateFn => {
          try {
            updateFn()
          } catch (error) {
            console.error('Render update error:', error)
          }
        })
      })
    }
  }

  /**
   * Cancel all pending updates
   */
  cancelUpdates(): void {
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId)
      this.rafId = null
    }
    this.pendingUpdates.clear()
  }
}

/**
 * Debounce utility for event handling
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout

  return (...args: Parameters<T>) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}

/**
 * Throttle utility for high-frequency events
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle = false

  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args)
      inThrottle = true
      setTimeout(() => inThrottle = false, limit)
    }
  }
}

/**
 * Performance optimization hook for React components
 */
export function usePerformanceOptimization(config?: Partial<PerformanceConfig>) {
  const fullConfig = { ...DEFAULT_PERFORMANCE_CONFIG, ...config }
  const tracker = React.useMemo(() => new PerformanceTracker(fullConfig), [fullConfig])
  const memoryManager = React.useMemo(() => new MemoryManager(fullConfig), [fullConfig])
  const renderOptimizer = React.useMemo(() => new RenderOptimizer(), [])

  // Cleanup on unmount
  React.useEffect(() => {
    return () => {
      renderOptimizer.cancelUpdates()
      memoryManager.runCleanup()
    }
  }, [renderOptimizer, memoryManager])

  // Periodic memory check
  React.useEffect(() => {
    if (fullConfig.enableMonitoring) {
      const interval = setInterval(() => {
        memoryManager.checkMemoryUsage()
      }, 10000) // Check every 10 seconds

      return () => clearInterval(interval)
    }
  }, [fullConfig.enableMonitoring, memoryManager])

  return {
    tracker,
    memoryManager,
    renderOptimizer,
    config: fullConfig,
    createThrottler: <T>(onUpdate: (batch: T[]) => void) => 
      new DataThrottler(onUpdate, fullConfig)
  }
}

// Re-export for convenience
export * from './PerformanceOptimizer'