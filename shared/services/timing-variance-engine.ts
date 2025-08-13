/**
 * Entry Timing Variance Engine
 * 
 * Introduces natural timing delays (1-30 seconds) between signal generation
 * and trade execution to simulate human reaction times and decision patterns.
 */

import {
  Signal,
  MarketConditions,
  TimingVarianceConfig,
  ExecutionVariance
} from '../types/execution-variance'
import { TradingPersonality } from '../types/personality'

interface TimingVarianceResult {
  delay: number
  reason: string
  factors: {
    base: number
    volatility: number
    session: number
    news: number
    personality: number
  }
}

export class TimingVarianceEngine {
  private configs = new Map<string, TimingVarianceConfig>()
  private recentSkips = new Map<string, number>() // Track consecutive skips
  
  /**
   * Register timing variance configuration for a personality
   */
  public registerPersonality(personality: TradingPersonality): void {
    const config: TimingVarianceConfig = {
      personalityId: personality.id,
      baseDelay: this.calculateBaseDelay(personality),
      volatilityThreshold: this.calculateVolatilityThreshold(personality),
      sessionMultipliers: this.calculateSessionMultipliers(personality),
      newsProximityFactor: this.calculateNewsProximityFactor(personality),
      consistencyLevel: personality.traits.discipline / 100
    }
    
    this.configs.set(personality.id, config)
  }
  
  /**
   * Calculate entry timing delay for a signal
   */
  public calculateEntryDelay(
    signal: Signal,
    marketConditions: MarketConditions,
    personality: TradingPersonality
  ): TimingVarianceResult {
    const config = this.configs.get(personality.id)
    if (!config) {
      throw new Error(`No timing config found for personality ${personality.id}`)
    }
    
    // Base delay from personality (typically 2-8 seconds)
    const baseDelay = config.baseDelay
    
    // Volatility impact (higher volatility = more hesitation)
    const volatilityMultiplier = this.calculateVolatilityMultiplier(
      marketConditions.volatility,
      config.volatilityThreshold
    )
    
    // Session-based adjustments
    const sessionMultiplier = config.sessionMultipliers[marketConditions.session] || 1.0
    
    // News event proximity (more delay near news)
    const newsMultiplier = marketConditions.isNewsTime 
      ? 1.0 + config.newsProximityFactor 
      : 1.0
    
    // Personality consistency (some traders always fast, others always slow)
    const consistencyFactor = this.generateConsistencyFactor(config.consistencyLevel)
    
    // Calculate total delay
    let totalDelay = baseDelay * volatilityMultiplier * sessionMultiplier * newsMultiplier * consistencyFactor
    
    // Add random component but keep within personality bounds
    const randomComponent = this.generateNormalRandom(0, baseDelay * 0.3)
    totalDelay += randomComponent
    
    // Ensure within 1-30 second bounds
    const finalDelay = this.clamp(totalDelay, 1, 30)
    
    // Determine primary reason for delay
    const reason = this.determineDelayReason({
      base: baseDelay,
      volatility: volatilityMultiplier,
      session: sessionMultiplier,
      news: newsMultiplier,
      personality: consistencyFactor
    })
    
    return {
      delay: Number(finalDelay.toFixed(2)),
      reason,
      factors: {
        base: baseDelay,
        volatility: volatilityMultiplier,
        session: sessionMultiplier,
        news: newsMultiplier,
        personality: consistencyFactor
      }
    }
  }
  
  /**
   * Apply timing variance to a signal
   */
  public applyTimingVariance(
    signal: Signal,
    marketConditions: MarketConditions,
    personality: TradingPersonality
  ): Promise<ExecutionVariance['variances']['entryTiming']> {
    const timingResult = this.calculateEntryDelay(signal, marketConditions, personality)
    
    return Promise.resolve({
      originalDelay: 0,
      appliedDelay: timingResult.delay,
      reason: timingResult.reason
    })
  }
  
  /**
   * Calculate base delay from personality traits
   */
  private calculateBaseDelay(personality: TradingPersonality): number {
    const patience = personality.traits.patience / 100
    const confidence = personality.traits.confidence / 100
    const discipline = personality.traits.discipline / 100
    
    // More patient personalities take longer to act
    // More confident personalities act faster
    // More disciplined personalities are more consistent
    const baseDelay = 2 + (patience * 6) - (confidence * 2) + (Math.random() * 2)
    
    return this.clamp(baseDelay, 1, 10)
  }
  
  /**
   * Calculate volatility threshold from personality
   */
  private calculateVolatilityThreshold(personality: TradingPersonality): number {
    const emotionality = personality.traits.emotionality / 100
    const riskTolerance = personality.traits.riskTolerance / 100
    
    // More emotional traders are more affected by volatility
    // Risk-tolerant traders are less affected
    return 1.0 + (emotionality * 0.8) - (riskTolerance * 0.4)
  }
  
  /**
   * Calculate session-specific delay multipliers
   */
  private calculateSessionMultipliers(personality: TradingPersonality): Record<string, number> {
    const timePrefs = personality.timePreferences
    const confidence = personality.traits.confidence / 100
    
    return {
      asian: timePrefs.sessionActivity.asian > 70 ? 0.8 + confidence * 0.4 : 1.2,
      london: timePrefs.sessionActivity.london > 70 ? 0.9 + confidence * 0.2 : 1.1,
      newyork: timePrefs.sessionActivity.newyork > 70 ? 0.85 + confidence * 0.3 : 1.15,
      overlap: timePrefs.sessionActivity.overlap > 80 ? 0.7 + confidence * 0.5 : 1.3
    }
  }
  
  /**
   * Calculate news proximity impact factor
   */
  private calculateNewsProximityFactor(personality: TradingPersonality): number {
    const emotionality = personality.traits.emotionality / 100
    const adaptability = personality.traits.adaptability / 100
    
    // More emotional traders hesitate more during news
    // More adaptable traders handle news better
    return (emotionality * 0.5) - (adaptability * 0.3)
  }
  
  /**
   * Calculate volatility multiplier based on market conditions
   */
  private calculateVolatilityMultiplier(volatility: number, threshold: number): number {
    if (volatility < threshold) {
      return 1.0
    }
    
    // Exponential increase in delay for high volatility
    const excess = volatility - threshold
    return 1.0 + Math.min(excess * 2, 2.0) // Cap at 3x multiplier
  }
  
  /**
   * Generate consistency factor based on discipline
   */
  private generateConsistencyFactor(consistencyLevel: number): number {
    // High discipline = more consistent timing
    // Low discipline = more random timing
    const randomness = (1 - consistencyLevel) * 0.5
    return 1.0 + this.generateNormalRandom(-randomness, randomness)
  }
  
  /**
   * Determine primary reason for delay
   */
  private determineDelayReason(factors: TimingVarianceResult['factors']): string {
    const reasons = [
      { factor: factors.volatility, reason: 'market_volatility' },
      { factor: factors.news, reason: 'news_proximity' },
      { factor: factors.session, reason: 'session_unfamiliarity' },
      { factor: factors.personality, reason: 'personality_hesitation' }
    ]
    
    // Find the factor with highest impact (furthest from 1.0)
    const maxImpact = reasons.reduce((max, current) => 
      Math.abs(current.factor - 1.0) > Math.abs(max.factor - 1.0) ? current : max
    )
    
    return maxImpact.reason
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
    
    return center + (normal * range / 6) // 6-sigma range
  }
  
  /**
   * Clamp value between min and max
   */
  private clamp(value: number, min: number, max: number): number {
    return Math.max(min, Math.min(max, value))
  }
  
  /**
   * Get timing statistics for a personality
   */
  public getTimingStats(personalityId: string): {
    config: TimingVarianceConfig | undefined
    averageDelay: number
    recentSkips: number
  } {
    return {
      config: this.configs.get(personalityId),
      averageDelay: 0, // Would be calculated from historical data
      recentSkips: this.recentSkips.get(personalityId) || 0
    }
  }
  
  /**
   * Reset timing configuration for a personality
   */
  public resetPersonality(personalityId: string): void {
    this.configs.delete(personalityId)
    this.recentSkips.delete(personalityId)
  }
}