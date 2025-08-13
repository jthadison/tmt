/**
 * Micro-Delay System
 * 
 * Implements random micro-delays (100-500ms) for order modifications
 * to simulate human reaction times and network/processing delays.
 */

import { TradingPersonality } from '../types/personality'
import { MarketConditions } from '../types/execution-variance'

export type OrderAction = 
  | 'place_order'
  | 'modify_stop_loss' 
  | 'modify_take_profit'
  | 'cancel_order'
  | 'close_position'
  | 'partial_close'

interface DelayConfig {
  personalityId: string
  baseDelays: Record<OrderAction, { min: number; max: number }>
  networkSimulation: boolean
  consistencyFactor: number
  contextualModifiers: {
    highVolatility: number
    newsTime: number
    marketOpen: number
    systemLoad: number
  }
}

interface DelayResult {
  action: OrderAction
  delay: number
  components: {
    base: number
    personality: number
    network: number
    context: number
  }
  reason: string
}

export class MicroDelayEngine {
  private configs = new Map<string, DelayConfig>()
  private delayHistory = new Map<string, DelayResult[]>()
  
  // Base delay ranges for different order actions (in milliseconds)
  private readonly BASE_DELAYS: Record<OrderAction, { min: number; max: number }> = {
    place_order: { min: 150, max: 400 },
    modify_stop_loss: { min: 100, max: 300 },
    modify_take_profit: { min: 120, max: 350 },
    cancel_order: { min: 80, max: 200 },
    close_position: { min: 100, max: 250 },
    partial_close: { min: 120, max: 300 }
  }
  
  // Network simulation delays to mimic real trading conditions
  private readonly NETWORK_DELAYS = {
    excellent: { min: 10, max: 30 },   // Fiber connection, close to server
    good: { min: 20, max: 60 },        // Standard broadband
    average: { min: 40, max: 100 },    // Average connection
    poor: { min: 80, max: 200 },       // Slower connection or distant server
    variable: { min: 15, max: 150 }    // Realistic variable network
  }
  
  /**
   * Register micro-delay configuration for a personality
   */
  public registerPersonality(personality: TradingPersonality): void {
    const config: DelayConfig = {
      personalityId: personality.id,
      baseDelays: this.calculatePersonalizedDelays(personality),
      networkSimulation: true,
      consistencyFactor: this.calculateConsistencyFactor(personality),
      contextualModifiers: this.calculateContextualModifiers(personality)
    }
    
    this.configs.set(personality.id, config)
    this.delayHistory.set(personality.id, [])
  }
  
  /**
   * Calculate delay for a specific order action
   */
  public calculateDelay(
    action: OrderAction,
    personalityId: string,
    marketConditions?: MarketConditions,
    systemLoad: number = 1.0
  ): DelayResult {
    const config = this.configs.get(personalityId)
    if (!config) {
      throw new Error(`No delay config found for personality ${personalityId}`)
    }
    
    const delayRange = config.baseDelays[action]
    
    // Base delay from action type and personality
    const baseDelay = this.generateRandomDelay(delayRange.min, delayRange.max, config.consistencyFactor)
    
    // Personality-specific adjustments
    const personalityDelay = this.applyPersonalityModifiers(baseDelay, config, action)
    
    // Network simulation delay
    const networkDelay = config.networkSimulation 
      ? this.generateNetworkDelay() 
      : 0
    
    // Contextual modifiers based on market conditions
    const contextDelay = marketConditions 
      ? this.applyContextualModifiers(personalityDelay, config, marketConditions, systemLoad)
      : 0
    
    const totalDelay = Math.round(baseDelay + personalityDelay + networkDelay + contextDelay)
    const finalDelay = Math.max(100, Math.min(500, totalDelay)) // Enforce 100-500ms bounds
    
    const result: DelayResult = {
      action,
      delay: finalDelay,
      components: {
        base: baseDelay,
        personality: personalityDelay,
        network: networkDelay,
        context: contextDelay
      },
      reason: this.determineDelayReason(config, marketConditions, action, finalDelay)
    }
    
    // Update delay history
    this.updateDelayHistory(personalityId, result)
    
    return result
  }
  
  /**
   * Apply delay to an action (returns a Promise that resolves after the delay)
   */
  public async applyDelay(
    action: OrderAction,
    personalityId: string,
    marketConditions?: MarketConditions,
    systemLoad: number = 1.0
  ): Promise<DelayResult> {
    const delayResult = this.calculateDelay(action, personalityId, marketConditions, systemLoad)
    
    return new Promise(resolve => {
      setTimeout(() => {
        resolve(delayResult)
      }, delayResult.delay)
    })
  }
  
  /**
   * Calculate personalized delay ranges based on personality traits
   */
  private calculatePersonalizedDelays(personality: TradingPersonality): DelayConfig['baseDelays'] {
    const patience = personality.traits.patience / 100
    const confidence = personality.traits.confidence / 100
    const emotionality = personality.traits.emotionality / 100
    
    const personalizedDelays: DelayConfig['baseDelays'] = {} as DelayConfig['baseDelays']
    
    for (const [action, baseRange] of Object.entries(this.BASE_DELAYS)) {
      const actionKey = action as OrderAction
      
      // Patient traders take slightly longer
      const patienceAdjustment = patience * 50
      
      // Confident traders act faster
      const confidenceAdjustment = (1 - confidence) * 40
      
      // Emotional traders have more variable timing
      const emotionalityVariance = emotionality * 30
      
      personalizedDelays[actionKey] = {
        min: Math.round(baseRange.min + patienceAdjustment + confidenceAdjustment - emotionalityVariance),
        max: Math.round(baseRange.max + patienceAdjustment + confidenceAdjustment + emotionalityVariance)
      }
    }
    
    return personalizedDelays
  }
  
  /**
   * Calculate consistency factor from personality
   */
  private calculateConsistencyFactor(personality: TradingPersonality): number {
    const discipline = personality.traits.discipline / 100
    const emotionality = personality.traits.emotionality / 100
    
    // Disciplined traders are more consistent (less variance)
    // Emotional traders are less consistent (more variance)
    return 0.3 + (discipline * 0.4) - (emotionality * 0.2) // 0.1 to 0.7 range
  }
  
  /**
   * Calculate contextual modifiers from personality
   */
  private calculateContextualModifiers(personality: TradingPersonality): DelayConfig['contextualModifiers'] {
    const emotionality = personality.traits.emotionality / 100
    const adaptability = personality.traits.adaptability / 100
    
    return {
      highVolatility: emotionality * 0.3,      // Emotional traders slower in high vol
      newsTime: emotionality * 0.4,            // More hesitation during news
      marketOpen: (1 - adaptability) * 0.2,    // Less adaptable traders affected by session changes
      systemLoad: 0.1 + emotionality * 0.2     // How much system load affects this trader
    }
  }
  
  /**
   * Generate random delay with consistency applied
   */
  private generateRandomDelay(min: number, max: number, consistency: number): number {
    if (consistency > 0.6) {
      // High consistency - use normal distribution centered on midpoint
      const center = (min + max) / 2
      const stdDev = (max - min) / 6
      return this.generateNormalRandom(center - stdDev, center + stdDev)
    } else {
      // Low consistency - use uniform distribution
      return min + Math.random() * (max - min)
    }
  }
  
  /**
   * Apply personality-specific modifications to base delay
   */
  private applyPersonalityModifiers(
    baseDelay: number, 
    config: DelayConfig, 
    action: OrderAction
  ): number {
    // Different actions affected differently by personality
    const actionMultipliers = {
      place_order: 1.0,         // Base reference
      modify_stop_loss: 0.8,    // Usually faster - protective action
      modify_take_profit: 1.1,  // Slightly slower - greed/hesitation
      cancel_order: 0.7,        // Fast - cutting losses or changing mind
      close_position: 0.9,      // Fairly quick - taking profit or loss
      partial_close: 1.2        // Slower - more complex decision
    }
    
    const multiplier = actionMultipliers[action] || 1.0
    return baseDelay * (multiplier - 1) * config.consistencyFactor
  }
  
  /**
   * Generate network simulation delay
   */
  private generateNetworkDelay(): number {
    // Most traders have good to average connections
    const networkTypes = ['excellent', 'good', 'average', 'variable'] as const
    const weights = [0.1, 0.4, 0.4, 0.1] // Distribution of connection qualities
    
    const randomValue = Math.random()
    let cumulativeWeight = 0
    let selectedType: keyof typeof this.NETWORK_DELAYS = 'average'
    
    for (let i = 0; i < networkTypes.length; i++) {
      cumulativeWeight += weights[i]
      if (randomValue <= cumulativeWeight) {
        selectedType = networkTypes[i]
        break
      }
    }
    
    const range = this.NETWORK_DELAYS[selectedType]
    return range.min + Math.random() * (range.max - range.min)
  }
  
  /**
   * Apply contextual modifiers based on market conditions
   */
  private applyContextualModifiers(
    baseDelay: number,
    config: DelayConfig,
    marketConditions: MarketConditions,
    systemLoad: number
  ): number {
    let contextDelay = 0
    
    // High volatility affects some traders
    if (marketConditions.volatility > 1.5) {
      contextDelay += baseDelay * config.contextualModifiers.highVolatility
    }
    
    // News time affects decision speed
    if (marketConditions.isNewsTime) {
      contextDelay += baseDelay * config.contextualModifiers.newsTime
    }
    
    // Market session changes affect some traders
    if (marketConditions.session === 'london' || marketConditions.session === 'overlap') {
      contextDelay += baseDelay * config.contextualModifiers.marketOpen
    }
    
    // System load affects execution speed
    if (systemLoad > 1.5) {
      contextDelay += baseDelay * config.contextualModifiers.systemLoad * (systemLoad - 1)
    }
    
    return contextDelay
  }
  
  /**
   * Determine primary reason for delay
   */
  private determineDelayReason(
    config: DelayConfig,
    marketConditions: MarketConditions | undefined,
    action: OrderAction,
    totalDelay: number
  ): string {
    if (totalDelay > 400) {
      return 'slow_reaction_time'
    }
    
    if (marketConditions?.isNewsTime) {
      return 'news_hesitation'
    }
    
    if (marketConditions?.volatility && marketConditions.volatility > 1.8) {
      return 'market_volatility_pause'
    }
    
    if (action === 'partial_close') {
      return 'complex_decision_time'
    }
    
    if (action === 'modify_take_profit') {
      return 'profit_target_adjustment'
    }
    
    if (totalDelay < 150) {
      return 'quick_reaction'
    }
    
    return 'normal_processing_time'
  }
  
  /**
   * Generate normal random number using Box-Muller transform
   */
  private generateNormalRandom(min: number, max: number): number {
    const u1 = Math.random()
    const u2 = Math.random()
    
    // Box-Muller transformation
    const normal = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2)
    
    // Scale to range
    const range = max - min
    const center = (min + max) / 2
    
    const result = center + (normal * range / 6) // 6-sigma range
    return Math.max(min, Math.min(max, result))
  }
  
  /**
   * Update delay history for analysis
   */
  private updateDelayHistory(personalityId: string, result: DelayResult): void {
    const history = this.delayHistory.get(personalityId) || []
    history.push(result)
    
    // Keep only last 100 delays
    if (history.length > 100) {
      history.shift()
    }
    
    this.delayHistory.set(personalityId, history)
  }
  
  /**
   * Get delay statistics for a personality
   */
  public getDelayStats(personalityId: string): {
    config: DelayConfig | undefined
    averageDelay: number
    delayDistribution: Record<OrderAction, number>
    recentDelays: DelayResult[]
  } {
    const history = this.delayHistory.get(personalityId) || []
    
    const averageDelay = history.length > 0 
      ? history.reduce((sum, d) => sum + d.delay, 0) / history.length 
      : 0
    
    // Calculate distribution by action type
    const delayDistribution: Record<OrderAction, number> = {} as Record<OrderAction, number>
    for (const action of Object.keys(this.BASE_DELAYS) as OrderAction[]) {
      const actionDelays = history.filter(d => d.action === action)
      delayDistribution[action] = actionDelays.length > 0
        ? actionDelays.reduce((sum, d) => sum + d.delay, 0) / actionDelays.length
        : 0
    }
    
    return {
      config: this.configs.get(personalityId),
      averageDelay,
      delayDistribution,
      recentDelays: history.slice(-20) // Last 20 delays
    }
  }
  
  /**
   * Validate delay performance is within acceptable bounds
   */
  public validateDelayPerformance(personalityId: string): {
    isValid: boolean
    averageDelay: number
    issues: string[]
  } {
    const stats = this.getDelayStats(personalityId)
    const issues: string[] = []
    
    // Check if average delay is within bounds
    if (stats.averageDelay < 100) {
      issues.push('Average delay too low - may appear robotic')
    } else if (stats.averageDelay > 500) {
      issues.push('Average delay too high - may appear unresponsive')
    }
    
    // Check for consistency issues
    const recentDelays = stats.recentDelays.slice(-10)
    if (recentDelays.length >= 5) {
      const variance = this.calculateVariance(recentDelays.map(d => d.delay))
      if (variance < 100) {
        issues.push('Delay variance too low - pattern may be detectable')
      }
    }
    
    return {
      isValid: issues.length === 0,
      averageDelay: stats.averageDelay,
      issues
    }
  }
  
  /**
   * Calculate variance of an array of numbers
   */
  private calculateVariance(numbers: number[]): number {
    if (numbers.length < 2) return 0
    
    const mean = numbers.reduce((sum, n) => sum + n, 0) / numbers.length
    const squaredDiffs = numbers.map(n => Math.pow(n - mean, 2))
    
    return squaredDiffs.reduce((sum, sq) => sum + sq, 0) / (numbers.length - 1)
  }
  
  /**
   * Reset delay configuration and history for a personality
   */
  public resetPersonality(personalityId: string): void {
    this.configs.delete(personalityId)
    this.delayHistory.delete(personalityId)
  }
  
  /**
   * Simulate network latency spike (for testing)
   */
  public simulateNetworkSpike(durationMs: number, additionalDelayMs: number): void {
    console.log(`Simulating network spike: +${additionalDelayMs}ms for ${durationMs}ms`)
    // Implementation would temporarily increase all network delays
  }
}