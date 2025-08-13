/**
 * Position Size Rounding Engine
 * 
 * Rounds position sizes to human-friendly numbers (0.01, 0.05, 0.1 lots)
 * based on personality preferences and psychological trading patterns.
 */

import {
  Signal,
  SizingVarianceConfig,
  ExecutionVariance
} from '../types/execution-variance'
import { TradingPersonality } from '../types/personality'

interface SizingVarianceResult {
  originalSize: number
  adjustedSize: number
  roundingMethod: 'up' | 'down' | 'nearest'
  reason: string
  deviation: number
}

export class SizingVarianceEngine {
  private configs = new Map<string, SizingVarianceConfig>()
  
  // Standard lot size increments traders commonly use
  private readonly STANDARD_INCREMENTS = [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
  
  // Psychological levels that humans gravitate towards
  private readonly PSYCHOLOGICAL_LEVELS = [0.01, 0.02, 0.05, 0.1, 0.2, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 5.0]
  
  /**
   * Register sizing variance configuration for a personality
   */
  public registerPersonality(personality: TradingPersonality): void {
    const config: SizingVarianceConfig = {
      personalityId: personality.id,
      preferredIncrements: this.calculatePreferredIncrements(personality),
      roundingBias: this.calculateRoundingBias(personality),
      maxDeviationPercent: this.calculateMaxDeviation(personality),
      accountSizeThresholds: {
        small: 1000,   // Under $1k
        medium: 10000, // $1k - $10k
        large: 50000   // Over $50k
      }
    }
    
    this.configs.set(personality.id, config)
  }
  
  /**
   * Apply position size rounding variance
   */
  public applyPositionSizeVariance(
    signal: Signal,
    personality: TradingPersonality,
    accountBalance: number
  ): ExecutionVariance['variances']['positionSize'] {
    const config = this.configs.get(personality.id)
    if (!config) {
      throw new Error(`No sizing config found for personality ${personality.id}`)
    }
    
    const result = this.calculateHumanFriendlySize(
      signal.size,
      config,
      accountBalance,
      personality
    )
    
    return {
      originalSize: result.originalSize,
      adjustedSize: result.adjustedSize,
      roundingMethod: result.roundingMethod,
      reason: result.reason
    }
  }
  
  /**
   * Calculate human-friendly position size
   */
  private calculateHumanFriendlySize(
    originalSize: number,
    config: SizingVarianceConfig,
    accountBalance: number,
    personality: TradingPersonality
  ): SizingVarianceResult {
    // Determine account size category
    const accountCategory = this.getAccountCategory(accountBalance, config.accountSizeThresholds)
    
    // Get appropriate increments for this account size
    const availableIncrements = this.getIncrements(config, accountCategory)
    
    // Find the best increment to round to
    const targetIncrement = this.findBestIncrement(originalSize, availableIncrements)
    
    // Apply rounding based on personality bias
    const { adjustedSize, roundingMethod } = this.applyRounding(
      originalSize,
      targetIncrement,
      config.roundingBias,
      personality
    )
    
    // Ensure deviation is within acceptable bounds
    const deviation = Math.abs(adjustedSize - originalSize) / originalSize
    const finalSize = deviation > config.maxDeviationPercent 
      ? this.fallbackRounding(originalSize, config.maxDeviationPercent)
      : adjustedSize
    
    const reason = this.determineRoundingReason(
      originalSize,
      finalSize,
      roundingMethod,
      accountCategory,
      personality
    )
    
    return {
      originalSize,
      adjustedSize: Number(finalSize.toFixed(2)),
      roundingMethod,
      reason,
      deviation: Math.abs(finalSize - originalSize) / originalSize
    }
  }
  
  /**
   * Calculate preferred increments based on personality
   */
  private calculatePreferredIncrements(personality: TradingPersonality): number[] {
    const discipline = personality.traits.discipline / 100
    const riskTolerance = personality.traits.riskTolerance / 100
    
    // Disciplined traders prefer standard increments
    // Risk-tolerant traders use larger increments
    if (discipline > 0.7) {
      return this.STANDARD_INCREMENTS
    } else if (riskTolerance > 0.7) {
      return [0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0] // Larger increments
    } else {
      return this.PSYCHOLOGICAL_LEVELS // More varied, psychological levels
    }
  }
  
  /**
   * Calculate rounding bias based on personality
   */
  private calculateRoundingBias(personality: TradingPersonality): 'up' | 'down' | 'nearest' | 'psychological' {
    const confidence = personality.traits.confidence / 100
    const emotionality = personality.traits.emotionality / 100
    const riskTolerance = personality.traits.riskTolerance / 100
    
    // Confident traders tend to round up
    if (confidence > 0.75 && riskTolerance > 0.6) {
      return 'up'
    }
    
    // Emotional/cautious traders tend to round down
    if (emotionality > 0.6 || riskTolerance < 0.4) {
      return 'down'
    }
    
    // Disciplined traders use nearest rounding
    if (personality.traits.discipline > 75) {
      return 'nearest'
    }
    
    // Others gravitate to psychological levels
    return 'psychological'
  }
  
  /**
   * Calculate maximum allowed deviation
   */
  private calculateMaxDeviation(personality: TradingPersonality): number {
    const discipline = personality.traits.discipline / 100
    const adaptability = personality.traits.adaptability / 100
    
    // More disciplined traders allow less deviation
    // More adaptable traders allow more deviation
    return 0.15 + (adaptability * 0.15) - (discipline * 0.1) // 5-30% deviation
  }
  
  /**
   * Get account size category
   */
  private getAccountCategory(
    balance: number, 
    thresholds: SizingVarianceConfig['accountSizeThresholds']
  ): 'small' | 'medium' | 'large' {
    if (balance < thresholds.small) return 'small'
    if (balance < thresholds.medium) return 'medium'
    return 'large'
  }
  
  /**
   * Get appropriate increments for account size
   */
  private getIncrements(
    config: SizingVarianceConfig, 
    accountCategory: 'small' | 'medium' | 'large'
  ): number[] {
    const baseIncrements = config.preferredIncrements
    
    switch (accountCategory) {
      case 'small':
        return baseIncrements.filter(inc => inc <= 1.0) // Micro and mini lots only
      case 'medium':
        return baseIncrements.filter(inc => inc <= 5.0) // Up to 5 lots
      case 'large':
        return baseIncrements // All increments available
    }
  }
  
  /**
   * Find the best increment to round to
   */
  private findBestIncrement(size: number, increments: number[]): number {
    return increments.reduce((closest, current) => 
      Math.abs(size - this.roundToIncrement(size, current)) < 
      Math.abs(size - this.roundToIncrement(size, closest)) 
        ? current 
        : closest
    )
  }
  
  /**
   * Round to specific increment
   */
  private roundToIncrement(size: number, increment: number): number {
    return Math.round(size / increment) * increment
  }
  
  /**
   * Apply rounding based on bias
   */
  private applyRounding(
    size: number,
    increment: number,
    bias: SizingVarianceConfig['roundingBias'],
    personality: TradingPersonality
  ): { adjustedSize: number; roundingMethod: 'up' | 'down' | 'nearest' } {
    switch (bias) {
      case 'up':
        return {
          adjustedSize: Math.ceil(size / increment) * increment,
          roundingMethod: 'up'
        }
        
      case 'down':
        return {
          adjustedSize: Math.floor(size / increment) * increment,
          roundingMethod: 'down'
        }
        
      case 'nearest':
        return {
          adjustedSize: Math.round(size / increment) * increment,
          roundingMethod: 'nearest'
        }
        
      case 'psychological':
        const psychLevel = this.findPsychologicalLevel(size, personality)
        return {
          adjustedSize: psychLevel,
          roundingMethod: psychLevel > size ? 'up' : psychLevel < size ? 'down' : 'nearest'
        }
    }
  }
  
  /**
   * Find psychological level close to size
   */
  private findPsychologicalLevel(size: number, personality: TradingPersonality): number {
    const emotionality = personality.traits.emotionality / 100
    
    // More emotional traders gravitate more strongly to round numbers
    const psychStrength = 0.3 + (emotionality * 0.4)
    
    // Find nearest psychological levels
    const lowerPsych = this.PSYCHOLOGICAL_LEVELS
      .filter(level => level <= size)
      .pop() || this.PSYCHOLOGICAL_LEVELS[0]
      
    const higherPsych = this.PSYCHOLOGICAL_LEVELS
      .find(level => level >= size) || this.PSYCHOLOGICAL_LEVELS[this.PSYCHOLOGICAL_LEVELS.length - 1]
    
    // Determine which psychological level to use
    const lowerDistance = size - lowerPsych
    const higherDistance = higherPsych - size
    
    // Weight towards psychological levels based on personality
    if (Math.random() < psychStrength) {
      return lowerDistance < higherDistance ? lowerPsych : higherPsych
    }
    
    // Otherwise use normal rounding
    return Math.round(size / 0.01) * 0.01
  }
  
  /**
   * Fallback rounding when deviation is too large
   */
  private fallbackRounding(size: number, maxDeviation: number): number {
    // Find the increment that keeps deviation within bounds
    const maxChange = size * maxDeviation
    
    for (const increment of this.STANDARD_INCREMENTS) {
      const rounded = Math.round(size / increment) * increment
      if (Math.abs(rounded - size) <= maxChange) {
        return rounded
      }
    }
    
    // If no increment works, use minimal rounding
    return Math.round(size * 100) / 100 // Round to nearest 0.01
  }
  
  /**
   * Determine reason for the rounding decision
   */
  private determineRoundingReason(
    originalSize: number,
    finalSize: number,
    roundingMethod: 'up' | 'down' | 'nearest',
    accountCategory: 'small' | 'medium' | 'large',
    personality: TradingPersonality
  ): string {
    const deviation = Math.abs(finalSize - originalSize) / originalSize
    
    if (deviation < 0.05) {
      return 'minimal_adjustment'
    }
    
    if (this.PSYCHOLOGICAL_LEVELS.includes(finalSize)) {
      return 'psychological_level'
    }
    
    if (accountCategory === 'small' && finalSize <= 0.1) {
      return 'micro_lot_constraint'
    }
    
    if (personality.traits.discipline > 75) {
      return 'disciplined_rounding'
    }
    
    if (personality.traits.emotionality > 60) {
      return 'emotional_comfort_level'
    }
    
    return `${roundingMethod}_rounding_preference`
  }
  
  /**
   * Get sizing statistics for a personality
   */
  public getSizingStats(personalityId: string): {
    config: SizingVarianceConfig | undefined
    averageDeviation: number
    roundingPattern: Record<string, number>
  } {
    return {
      config: this.configs.get(personalityId),
      averageDeviation: 0, // Would be calculated from historical data
      roundingPattern: {} // Distribution of rounding methods used
    }
  }
  
  /**
   * Validate a position size meets exchange requirements
   */
  public validateSize(size: number, minSize: number = 0.01, maxSize: number = 100): boolean {
    return size >= minSize && size <= maxSize && this.isValidIncrement(size)
  }
  
  /**
   * Check if size uses valid increment
   */
  private isValidIncrement(size: number): boolean {
    // Check if size is a multiple of 0.01 (standard increment)
    return Math.abs((size * 100) - Math.round(size * 100)) < 0.001
  }
  
  /**
   * Reset configuration for a personality
   */
  public resetPersonality(personalityId: string): void {
    this.configs.delete(personalityId)
  }
}