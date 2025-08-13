/**
 * Signal Skip Mechanism
 * 
 * Implements intelligent signal skipping (5% base rate) to simulate
 * human traders occasionally missing or ignoring trading opportunities.
 */

import {
  Signal,
  MarketConditions,
  SkipConfig,
  ExecutionVariance
} from '../types/execution-variance'
import { TradingPersonality } from '../types/personality'

interface SkipDecision {
  shouldSkip: boolean
  reason: string
  skipProbability: number
  factors: {
    base: number
    volatility: number
    confidence: number
    consecutive: number
    market: number
    news: number
  }
}

export class SignalSkipEngine {
  private configs = new Map<string, SkipConfig>()
  private skipHistory = new Map<string, SkipDecision[]>() // Recent skip decisions
  private consecutiveSkips = new Map<string, number>() // Track consecutive skips
  
  // Pool of realistic skip reasons
  private readonly SKIP_REASONS = [
    'phone_call_interruption',
    'coffee_break',
    'second_guessing_signal',
    'waiting_for_confirmation',
    'distracted_by_news',
    'bathroom_break',
    'checking_other_positions',
    'market_uncertainty',
    'low_confidence_period',
    'taking_profit_on_other_trade',
    'reviewing_market_analysis',
    'momentary_hesitation',
    'waiting_for_better_entry',
    'risk_management_pause',
    'mental_break_needed'
  ]
  
  /**
   * Register skip configuration for a personality
   */
  public registerPersonality(personality: TradingPersonality): void {
    const config: SkipConfig = {
      personalityId: personality.id,
      baseSkipRate: this.calculateBaseSkipRate(personality),
      skipTriggers: this.calculateSkipTriggers(personality),
      skipReasons: this.selectSkipReasons(personality),
      maxConsecutiveSkips: this.calculateMaxConsecutiveSkips(personality)
    }
    
    this.configs.set(personality.id, config)
    this.skipHistory.set(personality.id, [])
    this.consecutiveSkips.set(personality.id, 0)
  }
  
  /**
   * Determine if a signal should be skipped
   */
  public shouldSkipSignal(
    signal: Signal,
    marketConditions: MarketConditions,
    personality: TradingPersonality
  ): ExecutionVariance['variances']['execution'] {
    const config = this.configs.get(personality.id)
    if (!config) {
      throw new Error(`No skip config found for personality ${personality.id}`)
    }
    
    const skipDecision = this.calculateSkipDecision(
      signal,
      marketConditions,
      personality,
      config
    )
    
    // Update skip history and consecutive counter
    this.updateSkipHistory(personality.id, skipDecision)
    
    return {
      microDelay: this.generateMicroDelay(personality), // Always generate micro delay
      skipSignal: skipDecision.shouldSkip,
      skipReason: skipDecision.shouldSkip ? skipDecision.reason : undefined
    }
  }
  
  /**
   * Calculate skip decision based on multiple factors
   */
  private calculateSkipDecision(
    signal: Signal,
    marketConditions: MarketConditions,
    personality: TradingPersonality,
    config: SkipConfig
  ): SkipDecision {
    // Base skip probability
    let skipProbability = config.baseSkipRate
    
    // Factor weights
    const factors = {
      base: config.baseSkipRate,
      volatility: 0,
      confidence: 0,
      consecutive: 0,
      market: 0,
      news: 0
    }
    
    // Volatility factor
    if (config.skipTriggers.highVolatility && marketConditions.volatility > 1.5) {
      const volatilityIncrease = Math.min(0.15, (marketConditions.volatility - 1.5) * 0.1)
      skipProbability += volatilityIncrease
      factors.volatility = volatilityIncrease
    }
    
    // Low confidence factor
    if (config.skipTriggers.lowConfidence && signal.confidence < 0.7) {
      const confidenceDecrease = (0.7 - signal.confidence) * 0.2
      skipProbability += confidenceDecrease
      factors.confidence = confidenceDecrease
    }
    
    // Consecutive skips - reduce probability to avoid too many skips in a row
    const consecutiveCount = this.consecutiveSkips.get(personality.id) || 0
    if (consecutiveCount >= 2) {
      const consecutiveReduction = Math.min(0.8, consecutiveCount * 0.3)
      skipProbability -= consecutiveReduction
      factors.consecutive = -consecutiveReduction
    }
    
    // Market session factor
    const sessionSkipRates = {
      asian: 0.02,    // Slightly higher skip rate in quieter session
      london: -0.01,  // Slightly lower in active session
      newyork: -0.01, // Lower in most active session
      overlap: -0.02  // Lowest during overlaps (don't want to miss opportunities)
    }
    
    if (config.skipTriggers.marketOpen) {
      const marketAdjustment = sessionSkipRates[marketConditions.session] || 0
      skipProbability += marketAdjustment
      factors.market = marketAdjustment
    }
    
    // News factor
    if (config.skipTriggers.news && marketConditions.isNewsTime) {
      // Some traders skip during news, others are more active
      const newsAdjustment = personality.traits.emotionality > 60 ? 0.1 : -0.05
      skipProbability += newsAdjustment
      factors.news = newsAdjustment
    }
    
    // Ensure skip probability stays within reasonable bounds
    skipProbability = Math.max(0.01, Math.min(0.25, skipProbability))
    
    // Make skip decision
    const shouldSkip = Math.random() < skipProbability && consecutiveCount < config.maxConsecutiveSkips
    
    // Select reason if skipping
    const reason = shouldSkip ? this.selectSkipReason(config, factors, marketConditions) : ''
    
    return {
      shouldSkip,
      reason,
      skipProbability,
      factors
    }
  }
  
  /**
   * Calculate base skip rate from personality
   */
  private calculateBaseSkipRate(personality: TradingPersonality): number {
    const discipline = personality.traits.discipline / 100
    const emotionality = personality.traits.emotionality / 100
    const patience = personality.traits.patience / 100
    
    // Base 5% skip rate with personality adjustments
    let baseRate = 0.05
    
    // Disciplined traders skip fewer signals
    baseRate -= discipline * 0.02
    
    // Emotional traders skip more signals
    baseRate += emotionality * 0.03
    
    // Patient traders might skip more (waiting for perfect setup)
    baseRate += (patience > 0.8 ? patience * 0.02 : 0)
    
    return Math.max(0.02, Math.min(0.12, baseRate)) // 2-12% range
  }
  
  /**
   * Calculate skip triggers based on personality
   */
  private calculateSkipTriggers(personality: TradingPersonality): SkipConfig['skipTriggers'] {
    return {
      highVolatility: personality.traits.emotionality > 50, // Emotional traders affected by volatility
      lowConfidence: personality.traits.confidence < 70,    // Less confident traders skip low-confidence signals
      consecutiveLosses: personality.traits.emotionality > 60, // Emotional response to losses
      marketOpen: personality.traits.adaptability < 60,     // Less adaptable to different sessions
      news: personality.traits.emotionality > 60 || personality.traits.patience > 80 // Either avoid or wait
    }
  }
  
  /**
   * Select appropriate skip reasons for personality
   */
  private selectSkipReasons(personality: TradingPersonality): string[] {
    const reasons: string[] = []
    
    // Base reasons everyone might have
    reasons.push('second_guessing_signal', 'waiting_for_confirmation', 'market_uncertainty')
    
    // Emotional personality reasons
    if (personality.traits.emotionality > 60) {
      reasons.push('low_confidence_period', 'momentary_hesitation', 'mental_break_needed')
    }
    
    // Disciplined personality reasons
    if (personality.traits.discipline > 70) {
      reasons.push('risk_management_pause', 'reviewing_market_analysis', 'waiting_for_better_entry')
    }
    
    // Patient personality reasons
    if (personality.traits.patience > 70) {
      reasons.push('waiting_for_better_entry', 'waiting_for_confirmation', 'reviewing_market_analysis')
    }
    
    // Add some random human reasons
    const humanReasons = ['phone_call_interruption', 'coffee_break', 'bathroom_break', 'distracted_by_news']
    reasons.push(...humanReasons.slice(0, 2)) // Add 2 random human reasons
    
    return reasons
  }
  
  /**
   * Calculate maximum consecutive skips
   */
  private calculateMaxConsecutiveSkips(personality: TradingPersonality): number {
    const discipline = personality.traits.discipline / 100
    const patience = personality.traits.patience / 100
    
    // Disciplined traders don't skip many in a row
    // Patient traders might skip more consecutive signals
    let maxSkips = 3 // Base maximum
    
    if (discipline > 0.8) {
      maxSkips = 2 // Very disciplined traders limit consecutive skips
    } else if (patience > 0.8) {
      maxSkips = 4 // Very patient traders might skip more
    }
    
    return maxSkips
  }
  
  /**
   * Select specific reason for skipping this signal
   */
  private selectSkipReason(
    config: SkipConfig,
    factors: SkipDecision['factors'],
    marketConditions: MarketConditions
  ): string {
    // Determine most influential factor
    const maxFactor = Math.max(
      Math.abs(factors.volatility),
      Math.abs(factors.confidence),
      Math.abs(factors.market),
      Math.abs(factors.news)
    )
    
    // Select reason based on primary factor
    if (Math.abs(factors.volatility) === maxFactor && factors.volatility > 0) {
      return 'market_uncertainty'
    }
    
    if (Math.abs(factors.confidence) === maxFactor && factors.confidence > 0) {
      return 'low_confidence_period'
    }
    
    if (Math.abs(factors.news) === maxFactor && factors.news > 0) {
      return 'distracted_by_news'
    }
    
    if (marketConditions.isNewsTime) {
      return 'distracted_by_news'
    }
    
    // Otherwise pick random reason from personality pool
    return config.skipReasons[Math.floor(Math.random() * config.skipReasons.length)]
  }
  
  /**
   * Generate micro delay (100-500ms) for all executions
   */
  private generateMicroDelay(personality: TradingPersonality): number {
    const patience = personality.traits.patience / 100
    const discipline = personality.traits.discipline / 100
    
    // Patient traders take slightly longer
    // Disciplined traders are more consistent
    const baseDelay = 200 + (patience * 200) // 200-400ms base
    const variance = discipline > 0.7 ? 50 : 100 // Less variance for disciplined traders
    
    const delay = baseDelay + (Math.random() - 0.5) * variance
    return Math.round(Math.max(100, Math.min(500, delay)))
  }
  
  /**
   * Update skip history for a personality
   */
  private updateSkipHistory(personalityId: string, decision: SkipDecision): void {
    const history = this.skipHistory.get(personalityId) || []
    history.push(decision)
    
    // Keep only last 50 decisions
    if (history.length > 50) {
      history.shift()
    }
    
    this.skipHistory.set(personalityId, history)
    
    // Update consecutive skip counter
    if (decision.shouldSkip) {
      const current = this.consecutiveSkips.get(personalityId) || 0
      this.consecutiveSkips.set(personalityId, current + 1)
    } else {
      this.consecutiveSkips.set(personalityId, 0)
    }
  }
  
  /**
   * Get skip statistics for a personality
   */
  public getSkipStats(personalityId: string): {
    config: SkipConfig | undefined
    actualSkipRate: number
    consecutiveSkips: number
    reasonDistribution: Record<string, number>
    recentDecisions: SkipDecision[]
  } {
    const history = this.skipHistory.get(personalityId) || []
    const skippedCount = history.filter(d => d.shouldSkip).length
    const actualSkipRate = history.length > 0 ? skippedCount / history.length : 0
    
    // Calculate reason distribution
    const reasonDistribution: Record<string, number> = {}
    history.filter(d => d.shouldSkip).forEach(d => {
      reasonDistribution[d.reason] = (reasonDistribution[d.reason] || 0) + 1
    })
    
    return {
      config: this.configs.get(personalityId),
      actualSkipRate,
      consecutiveSkips: this.consecutiveSkips.get(personalityId) || 0,
      reasonDistribution,
      recentDecisions: history.slice(-10) // Last 10 decisions
    }
  }
  
  /**
   * Check if skip rate is within acceptable bounds
   */
  public validateSkipRate(personalityId: string): { isValid: boolean; actualRate: number; targetRate: number } {
    const config = this.configs.get(personalityId)
    if (!config) {
      return { isValid: false, actualRate: 0, targetRate: 0.05 }
    }
    
    const stats = this.getSkipStats(personalityId)
    const targetRate = config.baseSkipRate
    const tolerance = 0.03 // ±3% tolerance
    
    const isValid = Math.abs(stats.actualSkipRate - targetRate) <= tolerance
    
    return {
      isValid,
      actualRate: stats.actualSkipRate,
      targetRate
    }
  }
  
  /**
   * Reset skip data for a personality
   */
  public resetPersonality(personalityId: string): void {
    this.configs.delete(personalityId)
    this.skipHistory.delete(personalityId)
    this.consecutiveSkips.delete(personalityId)
  }
  
  /**
   * Force skip next N signals (for testing or manual control)
   */
  public forceSkip(personalityId: string, count: number, reason: string): void {
    // Implementation for manual skip forcing if needed
    console.log(`Force skipping next ${count} signals for ${personalityId}: ${reason}`)
  }
}