/**
 * Stop Loss/Take Profit Variance Engine
 * 
 * Introduces 1-3 pip variance in stop loss and take profit placement
 * to simulate human imprecision and avoid round number clustering.
 */

import {
  Signal,
  MarketConditions,
  LevelVarianceConfig,
  ExecutionVariance
} from '../types/execution-variance'
import { TradingPersonality } from '../types/personality'

interface LevelVarianceResult {
  originalLevel: number
  adjustedLevel: number
  variance: number
  reason: string
  avoidedRoundNumber: boolean
}

export class LevelVarianceEngine {
  private configs = new Map<string, LevelVarianceConfig>()
  
  // Common round numbers that traders often use
  private readonly ROUND_NUMBERS = [
    0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100
  ]
  
  // Pip precision for different currency pairs
  private readonly PIP_PRECISION: Record<string, number> = {
    'USDJPY': 0.01,
    'EURJPY': 0.01,
    'GBPJPY': 0.01,
    'CHFJPY': 0.01,
    'default': 0.0001 // Most major pairs
  }
  
  /**
   * Register level variance configuration for a personality
   */
  public registerPersonality(personality: TradingPersonality): void {
    const config: LevelVarianceConfig = {
      personalityId: personality.id,
      stopLossRange: this.calculateStopLossRange(personality),
      takeProfitRange: this.calculateTakeProfitRange(personality),
      roundNumberAvoidance: this.calculateRoundNumberAvoidance(personality),
      marketConditionImpact: this.calculateMarketConditionImpact(personality)
    }
    
    this.configs.set(personality.id, config)
  }
  
  /**
   * Apply stop loss variance
   */
  public applyStopLossVariance(
    signal: Signal,
    marketConditions: MarketConditions,
    personality: TradingPersonality
  ): ExecutionVariance['variances']['stopLoss'] {
    const config = this.configs.get(personality.id)
    if (!config) {
      throw new Error(`No level config found for personality ${personality.id}`)
    }
    
    const result = this.calculateLevelVariance(
      signal.stopLoss,
      signal.symbol,
      config.stopLossRange,
      'stopLoss',
      config,
      marketConditions,
      personality
    )
    
    return {
      originalLevel: result.originalLevel,
      adjustedLevel: result.adjustedLevel,
      variance: result.variance,
      reason: result.reason
    }
  }
  
  /**
   * Apply take profit variance
   */
  public applyTakeProfitVariance(
    signal: Signal,
    marketConditions: MarketConditions,
    personality: TradingPersonality
  ): ExecutionVariance['variances']['takeProfit'] {
    const config = this.configs.get(personality.id)
    if (!config) {
      throw new Error(`No level config found for personality ${personality.id}`)
    }
    
    const result = this.calculateLevelVariance(
      signal.takeProfit,
      signal.symbol,
      config.takeProfitRange,
      'takeProfit',
      config,
      marketConditions,
      personality
    )
    
    return {
      originalLevel: result.originalLevel,
      adjustedLevel: result.adjustedLevel,
      variance: result.variance,
      reason: result.reason
    }
  }
  
  /**
   * Calculate level variance for stop loss or take profit
   */
  private calculateLevelVariance(
    originalLevel: number,
    symbol: string,
    varianceRange: { min: number; max: number },
    levelType: 'stopLoss' | 'takeProfit',
    config: LevelVarianceConfig,
    marketConditions: MarketConditions,
    personality: TradingPersonality
  ): LevelVarianceResult {
    const pipSize = this.getPipSize(symbol)
    
    // Generate base variance (1-3 pips)
    const baseVariance = this.generateVariance(varianceRange, personality)
    
    // Apply market condition adjustments
    const marketAdjustedVariance = this.applyMarketConditionAdjustment(
      baseVariance,
      marketConditions,
      config.marketConditionImpact
    )
    
    // Convert pips to price units
    const priceVariance = marketAdjustedVariance * pipSize
    
    // Apply directional bias based on level type and personality
    const directedVariance = this.applyDirectionalBias(
      priceVariance,
      levelType,
      personality,
      config
    )
    
    // Calculate adjusted level
    let adjustedLevel = originalLevel + directedVariance
    
    // Apply round number avoidance
    const { finalLevel, avoidedRoundNumber } = this.applyRoundNumberAvoidance(
      adjustedLevel,
      originalLevel,
      config.roundNumberAvoidance,
      pipSize
    )
    
    // Determine reason for adjustment
    const reason = this.determineLevelReason(
      baseVariance,
      marketConditions,
      avoidedRoundNumber,
      levelType,
      personality
    )
    
    return {
      originalLevel,
      adjustedLevel: Number(finalLevel.toFixed(symbol.includes('JPY') ? 2 : 4)),
      variance: Number(((finalLevel - originalLevel) / pipSize).toFixed(1)),
      reason,
      avoidedRoundNumber
    }
  }
  
  /**
   * Calculate stop loss variance range from personality
   */
  private calculateStopLossRange(personality: TradingPersonality): { min: number; max: number } {
    const emotionality = personality.traits.emotionality / 100
    const discipline = personality.traits.discipline / 100
    
    // Emotional traders have more variance
    // Disciplined traders have less variance
    const baseMin = 1
    const baseMax = 3
    
    const emotionalAdjustment = emotionality * 1.5 // Up to 1.5 additional pips
    const disciplineReduction = discipline * 0.5   // Up to 0.5 pip reduction
    
    return {
      min: Math.max(0.5, baseMin - disciplineReduction),
      max: Math.min(5, baseMax + emotionalAdjustment)
    }
  }
  
  /**
   * Calculate take profit variance range from personality
   */
  private calculateTakeProfitRange(personality: TradingPersonality): { min: number; max: number } {
    const patience = personality.traits.patience / 100
    const confidence = personality.traits.confidence / 100
    
    // Patient traders less likely to adjust targets
    // Confident traders more willing to adjust
    const baseMin = 1
    const baseMax = 3
    
    const patienceReduction = patience * 0.8
    const confidenceIncrease = confidence * 1.2
    
    return {
      min: Math.max(0.3, baseMin - patienceReduction),
      max: Math.min(4, baseMax + confidenceIncrease)
    }
  }
  
  /**
   * Calculate round number avoidance strength
   */
  private calculateRoundNumberAvoidance(personality: TradingPersonality): number {
    const discipline = personality.traits.discipline / 100
    const adaptability = personality.traits.adaptability / 100
    
    // Disciplined traders more likely to avoid obvious levels
    // Adaptable traders vary their approach
    return 0.3 + (discipline * 0.5) + (adaptability * 0.2) // 0.3 to 1.0
  }
  
  /**
   * Calculate market condition impact factor
   */
  private calculateMarketConditionImpact(personality: TradingPersonality): number {
    const emotionality = personality.traits.emotionality / 100
    const adaptability = personality.traits.adaptability / 100
    
    // Emotional traders more affected by market conditions
    // Adaptable traders adjust better to conditions
    return 0.5 + (emotionality * 0.4) + (adaptability * 0.3) // 0.5 to 1.2
  }
  
  /**
   * Generate variance within range
   */
  private generateVariance(range: { min: number; max: number }, personality: TradingPersonality): number {
    const consistency = personality.traits.discipline / 100
    
    // More consistent personalities have tighter variance distribution
    if (consistency > 0.8) {
      // Normal distribution centered on range midpoint
      const center = (range.min + range.max) / 2
      const stdDev = (range.max - range.min) / 4
      return this.generateNormalRandom(center - stdDev, center + stdDev)
    } else {
      // Uniform distribution across full range
      return range.min + Math.random() * (range.max - range.min)
    }
  }
  
  /**
   * Apply market condition adjustments
   */
  private applyMarketConditionAdjustment(
    baseVariance: number,
    marketConditions: MarketConditions,
    impactFactor: number
  ): number {
    let adjustedVariance = baseVariance
    
    // High volatility increases variance
    if (marketConditions.volatility > 1.5) {
      adjustedVariance *= 1.2 * impactFactor
    }
    
    // Low liquidity increases variance
    if (marketConditions.liquidity === 'low') {
      adjustedVariance *= 1.3 * impactFactor
    }
    
    // News time increases variance
    if (marketConditions.isNewsTime) {
      adjustedVariance *= 1.4 * impactFactor
    }
    
    // Market session affects variance
    const sessionMultipliers = {
      asian: 0.9,    // Lower variance in quieter session
      london: 1.1,   // Higher variance in active session
      newyork: 1.2,  // Highest variance in most active session
      overlap: 1.3   // Maximum variance during overlaps
    }
    
    adjustedVariance *= sessionMultipliers[marketConditions.session] || 1.0
    
    return adjustedVariance
  }
  
  /**
   * Apply directional bias to variance
   */
  private applyDirectionalBias(
    priceVariance: number,
    levelType: 'stopLoss' | 'takeProfit',
    personality: TradingPersonality,
    config: LevelVarianceConfig
  ): number {
    // Determine bias from configuration
    const bias = levelType === 'stopLoss' 
      ? (config.stopLossRange as any).bias || 'neutral'
      : (config.takeProfitRange as any).bias || 'neutral'
    
    // Apply personality-influenced directional bias
    let direction = 0
    
    if (levelType === 'stopLoss') {
      if (bias === 'conservative') {
        direction = Math.random() < 0.7 ? -1 : 1 // 70% chance of tighter stop
      } else if (bias === 'aggressive') {
        direction = Math.random() < 0.7 ? 1 : -1  // 70% chance of wider stop
      }
    } else {
      if (bias === 'greedy') {
        direction = Math.random() < 0.7 ? 1 : -1  // 70% chance of higher target
      } else if (bias === 'cautious') {
        direction = Math.random() < 0.7 ? -1 : 1  // 70% chance of lower target
      }
    }
    
    if (direction === 0) {
      direction = Math.random() < 0.5 ? -1 : 1 // Random direction for neutral bias
    }
    
    return priceVariance * direction
  }
  
  /**
   * Apply round number avoidance logic
   */
  private applyRoundNumberAvoidance(
    adjustedLevel: number,
    originalLevel: number,
    avoidanceStrength: number,
    pipSize: number
  ): { finalLevel: number; avoidedRoundNumber: boolean } {
    // Check if adjusted level hits a round number
    const levelInPips = Math.round(adjustedLevel / pipSize)
    const isRoundNumber = this.ROUND_NUMBERS.some(roundNum => 
      Math.abs(levelInPips % 100 - roundNum) < 2
    )
    
    if (!isRoundNumber || Math.random() > avoidanceStrength) {
      return { finalLevel: adjustedLevel, avoidedRoundNumber: false }
    }
    
    // Apply small adjustment to avoid round number
    const avoidanceAdjustment = (Math.random() < 0.5 ? -1 : 1) * 
                               (2 + Math.random() * 3) * pipSize // 2-5 pip adjustment
    
    const finalLevel = adjustedLevel + avoidanceAdjustment
    
    return { finalLevel, avoidedRoundNumber: true }
  }
  
  /**
   * Determine reason for level adjustment
   */
  private determineLevelReason(
    baseVariance: number,
    marketConditions: MarketConditions,
    avoidedRoundNumber: boolean,
    levelType: 'stopLoss' | 'takeProfit',
    personality: TradingPersonality
  ): string {
    if (avoidedRoundNumber) {
      return 'round_number_avoidance'
    }
    
    if (marketConditions.isNewsTime) {
      return 'news_event_adjustment'
    }
    
    if (marketConditions.volatility > 1.5) {
      return 'high_volatility_adjustment'
    }
    
    if (marketConditions.liquidity === 'low') {
      return 'liquidity_concern'
    }
    
    if (baseVariance > 2.5) {
      return personality.traits.emotionality > 60 
        ? 'emotional_adjustment' 
        : 'market_adaptation'
    }
    
    return `${levelType}_precision_variance`
  }
  
  /**
   * Get pip size for currency pair
   */
  private getPipSize(symbol: string): number {
    return this.PIP_PRECISION[symbol] || this.PIP_PRECISION.default
  }
  
  /**
   * Generate normal random number
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
   * Get level variance statistics for a personality
   */
  public getLevelStats(personalityId: string): {
    config: LevelVarianceConfig | undefined
    stopLossStats: { averageVariance: number; roundNumberAvoidance: number }
    takeProfitStats: { averageVariance: number; roundNumberAvoidance: number }
  } {
    return {
      config: this.configs.get(personalityId),
      stopLossStats: { averageVariance: 0, roundNumberAvoidance: 0 },
      takeProfitStats: { averageVariance: 0, roundNumberAvoidance: 0 }
    }
  }
  
  /**
   * Validate level is within acceptable bounds
   */
  public validateLevel(level: number, symbol: string, levelType: 'stopLoss' | 'takeProfit'): boolean {
    // Basic validation - levels should be positive
    if (level <= 0) return false
    
    // Symbol-specific validation could be added here
    return true
  }
  
  /**
   * Reset configuration for a personality
   */
  public resetPersonality(personalityId: string): void {
    this.configs.delete(personalityId)
  }
}