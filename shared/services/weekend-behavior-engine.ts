/**
 * Weekend Behavior Variance Engine
 * 
 * Implements personality-driven weekend trading behaviors including
 * Sunday open trading preferences, gap strategies, and risk adjustments.
 */

import {
  WeekendConfig,
  MarketConditions,
  ExecutionVariance
} from '../types/execution-variance'
import { TradingPersonality } from '../types/personality'

export type GapStrategy = 'avoid' | 'fade' | 'follow'
export type NewsReactionStyle = 'ignore' | 'cautious' | 'opportunistic'

interface WeekendBehaviorResult {
  shouldTrade: boolean
  riskMultiplier: number
  gapStrategy: GapStrategy
  newsReaction: NewsReactionStyle
  reason: string
  factors: {
    personalityBias: number
    gapSize: number
    newsImpact: number
    sessionTime: number
  }
}

interface WeekendSession {
  start: Date
  end: Date
  type: 'sunday_open' | 'weekend_close'
  majorPairs: boolean
  newsEvents: string[]
}

export class WeekendBehaviorEngine {
  private configs = new Map<string, WeekendConfig>()
  private weekendHistory = new Map<string, WeekendBehaviorResult[]>()
  
  // Regional preferences for Sunday trading
  private readonly REGIONAL_PREFERENCES = {
    asian: { sundayTradingRate: 0.6, preferredPairs: ['USDJPY', 'AUDUSD', 'NZDUSD'] },
    european: { sundayTradingRate: 0.2, preferredPairs: ['EURUSD', 'GBPUSD', 'USDCHF'] },
    american: { sundayTradingRate: 0.3, preferredPairs: ['EURUSD', 'GBPUSD', 'USDCAD'] }
  }
  
  // Gap size categories and typical trader reactions
  private readonly GAP_THRESHOLDS = {
    small: 10,   // <10 pips - usually ignored
    medium: 30,  // 10-30 pips - some action
    large: 60,   // 30-60 pips - definite action
    huge: 100    // >60 pips - major event
  }
  
  /**
   * Register weekend behavior configuration for a personality
   */
  public registerPersonality(personality: TradingPersonality): void {
    const config: WeekendConfig = {
      personalityId: personality.id,
      tradeSundayOpen: this.calculateSundayTradingPreference(personality),
      sundayRiskMultiplier: this.calculateSundayRiskMultiplier(personality),
      gapStrategy: this.calculateGapStrategy(personality),
      newsReactionStyle: this.calculateNewsReactionStyle(personality)
    }
    
    this.configs.set(personality.id, config)
    this.weekendHistory.set(personality.id, [])
  }
  
  /**
   * Determine weekend trading behavior for a personality
   */
  public determineWeekendBehavior(
    personality: TradingPersonality,
    weekendSession: WeekendSession,
    marketConditions: MarketConditions
  ): WeekendBehaviorResult {
    const config = this.configs.get(personality.id)
    if (!config) {
      throw new Error(`No weekend config found for personality ${personality.id}`)
    }
    
    const behavior = this.calculateWeekendBehavior(
      config,
      personality,
      weekendSession,
      marketConditions
    )
    
    // Update behavior history
    this.updateWeekendHistory(personality.id, behavior)
    
    return behavior
  }
  
  /**
   * Check if personality should trade during Sunday open
   */
  public shouldTradeSundayOpen(
    personalityId: string,
    gapSize: number = 0,
    hasWeekendNews: boolean = false
  ): boolean {
    const config = this.configs.get(personalityId)
    if (!config) return false
    
    let tradingProbability = config.tradeSundayOpen ? 0.7 : 0.3
    
    // Adjust based on gap size
    if (gapSize > this.GAP_THRESHOLDS.medium) {
      if (config.gapStrategy === 'avoid') {
        tradingProbability *= 0.5
      } else {
        tradingProbability *= 1.3
      }
    }
    
    // Adjust based on weekend news
    if (hasWeekendNews) {
      if (config.newsReactionStyle === 'ignore') {
        tradingProbability *= 0.8
      } else if (config.newsReactionStyle === 'opportunistic') {
        tradingProbability *= 1.4
      }
    }
    
    return Math.random() < Math.min(0.9, tradingProbability)
  }
  
  /**
   * Calculate weekend trading behavior
   */
  private calculateWeekendBehavior(
    config: WeekendConfig,
    personality: TradingPersonality,
    weekendSession: WeekendSession,
    marketConditions: MarketConditions
  ): WeekendBehaviorResult {
    // Base trading decision
    let shouldTrade = config.tradeSundayOpen
    
    // Personality influence on Sunday trading
    const personalityBias = this.calculatePersonalityBias(personality, weekendSession)
    
    // Gap size influence
    const gapSize = marketConditions.gapSize || 0
    const gapInfluence = this.calculateGapInfluence(gapSize, config.gapStrategy)
    
    // News impact
    const newsImpact = this.calculateNewsImpact(
      weekendSession.newsEvents,
      config.newsReactionStyle
    )
    
    // Session timing influence
    const sessionInfluence = this.calculateSessionInfluence(weekendSession, personality)
    
    // Combine factors to make final decision
    let tradingProbability = shouldTrade ? 0.6 : 0.3
    tradingProbability += personalityBias
    tradingProbability += gapInfluence
    tradingProbability += newsImpact
    tradingProbability += sessionInfluence
    
    // Make final decision
    shouldTrade = Math.random() < Math.max(0.1, Math.min(0.9, tradingProbability))
    
    // Determine risk multiplier
    const riskMultiplier = this.calculateRiskMultiplier(
      config,
      personality,
      gapSize,
      weekendSession.newsEvents.length > 0
    )
    
    // Determine reason
    const reason = this.determineWeekendReason(
      shouldTrade,
      gapSize,
      weekendSession.newsEvents.length > 0,
      personalityBias,
      config
    )
    
    return {
      shouldTrade,
      riskMultiplier,
      gapStrategy: config.gapStrategy,
      newsReaction: config.newsReactionStyle,
      reason,
      factors: {
        personalityBias,
        gapSize,
        newsImpact,
        sessionTime: sessionInfluence
      }
    }
  }
  
  /**
   * Calculate Sunday trading preference based on personality
   */
  private calculateSundayTradingPreference(personality: TradingPersonality): boolean {
    const riskTolerance = personality.traits.riskTolerance / 100
    const patience = personality.traits.patience / 100
    const adaptability = personality.traits.adaptability / 100
    
    // Risk-tolerant and adaptable traders more likely to trade Sunday
    // Patient traders may wait for Monday
    let probability = 0.3 // Base 30% trade Sunday
    
    probability += riskTolerance * 0.4  // Up to +40%
    probability += adaptability * 0.3   // Up to +30%
    probability -= (patience > 0.8 ? 0.2 : 0) // -20% for very patient traders
    
    // Asian time preference increases Sunday trading
    if (personality.timePreferences.sessionActivity.asian > 70) {
      probability += 0.3
    }
    
    return Math.random() < probability
  }
  
  /**
   * Calculate Sunday risk multiplier
   */
  private calculateSundayRiskMultiplier(personality: TradingPersonality): number {
    const discipline = personality.traits.discipline / 100
    const emotionality = personality.traits.emotionality / 100
    
    // Disciplined traders reduce risk on Sunday
    // Emotional traders may increase or decrease unpredictably
    let multiplier = 1.0
    
    if (discipline > 0.7) {
      multiplier = 0.5 + Math.random() * 0.3 // 0.5-0.8x risk
    } else if (emotionality > 0.7) {
      multiplier = 0.3 + Math.random() * 1.0 // 0.3-1.3x risk (very variable)
    } else {
      multiplier = 0.6 + Math.random() * 0.6 // 0.6-1.2x risk
    }
    
    return Number(multiplier.toFixed(2))
  }
  
  /**
   * Calculate gap trading strategy
   */
  private calculateGapStrategy(personality: TradingPersonality): GapStrategy {
    const confidence = personality.traits.confidence / 100
    const riskTolerance = personality.traits.riskTolerance / 100
    const adaptability = personality.traits.adaptability / 100
    
    // Confident + risk-tolerant = follow gaps
    // Conservative = avoid gaps
    // Adaptable = fade gaps (contrarian)
    
    if (confidence > 0.7 && riskTolerance > 0.6) {
      return 'follow' // Chase momentum
    } else if (adaptability > 0.7 && confidence > 0.6) {
      return 'fade'   // Contrarian approach
    } else {
      return 'avoid'  // Conservative approach
    }
  }
  
  /**
   * Calculate news reaction style
   */
  private calculateNewsReactionStyle(personality: TradingPersonality): NewsReactionStyle {
    const emotionality = personality.traits.emotionality / 100
    const adaptability = personality.traits.adaptability / 100
    const patience = personality.traits.patience / 100
    
    // Emotional traders react more to news
    // Adaptable traders see opportunities
    // Patient traders ignore short-term news
    
    if (patience > 0.8 && emotionality < 0.4) {
      return 'ignore'        // Patient, unemotional
    } else if (adaptability > 0.7 && emotionality > 0.5) {
      return 'opportunistic' // See chances in volatility
    } else {
      return 'cautious'      // Careful, wait and see
    }
  }
  
  /**
   * Calculate personality bias for weekend trading
   */
  private calculatePersonalityBias(
    personality: TradingPersonality,
    weekendSession: WeekendSession
  ): number {
    let bias = 0
    
    // Asian session preference
    if (personality.timePreferences.sessionActivity.asian > 70 && weekendSession.type === 'sunday_open') {
      bias += 0.2
    }
    
    // Risk tolerance
    const riskTolerance = personality.traits.riskTolerance / 100
    bias += (riskTolerance - 0.5) * 0.3
    
    // Adaptability
    const adaptability = personality.traits.adaptability / 100
    bias += (adaptability - 0.5) * 0.2
    
    return bias
  }
  
  /**
   * Calculate gap size influence on trading decision
   */
  private calculateGapInfluence(gapSize: number, strategy: GapStrategy): number {
    if (gapSize < this.GAP_THRESHOLDS.small) {
      return 0 // No influence for small gaps
    }
    
    const gapMagnitude = Math.min(gapSize / this.GAP_THRESHOLDS.huge, 1) // 0-1 scale
    
    switch (strategy) {
      case 'follow':
        return gapMagnitude * 0.3 // Larger gaps = more likely to trade
      case 'fade':
        return gapMagnitude * 0.25 // Larger gaps = more opportunity
      case 'avoid':
        return -gapMagnitude * 0.4 // Larger gaps = less likely to trade
    }
  }
  
  /**
   * Calculate news impact on trading decision
   */
  private calculateNewsImpact(newsEvents: string[], reactionStyle: NewsReactionStyle): number {
    const newsCount = newsEvents.length
    if (newsCount === 0) return 0
    
    const newsMagnitude = Math.min(newsCount / 3, 1) // Scale based on news count
    
    switch (reactionStyle) {
      case 'ignore':
        return -newsMagnitude * 0.1 // Slight negative impact
      case 'cautious':
        return -newsMagnitude * 0.2 // More hesitant with more news
      case 'opportunistic':
        return newsMagnitude * 0.3  // More excited with more news
    }
  }
  
  /**
   * Calculate session timing influence
   */
  private calculateSessionInfluence(
    weekendSession: WeekendSession,
    personality: TradingPersonality
  ): number {
    // Early Sunday morning (Asian open) vs later
    const hour = weekendSession.start.getHours()
    
    if (hour >= 21 || hour <= 6) { // Asian session hours
      return personality.timePreferences.sessionActivity.asian > 70 ? 0.2 : -0.1
    } else {
      return personality.timePreferences.sessionActivity.asian <= 70 ? 0.1 : -0.1
    }
  }
  
  /**
   * Calculate risk multiplier for weekend trading
   */
  private calculateRiskMultiplier(
    config: WeekendConfig,
    personality: TradingPersonality,
    gapSize: number,
    hasNews: boolean
  ): number {
    let multiplier = config.sundayRiskMultiplier
    
    // Large gaps increase caution
    if (gapSize > this.GAP_THRESHOLDS.large) {
      multiplier *= 0.7
    }
    
    // News increases caution unless opportunistic
    if (hasNews && config.newsReactionStyle !== 'opportunistic') {
      multiplier *= 0.8
    } else if (hasNews && config.newsReactionStyle === 'opportunistic') {
      multiplier *= 1.2
    }
    
    // Add some randomness
    const randomFactor = 0.9 + Math.random() * 0.2 // 0.9-1.1x
    multiplier *= randomFactor
    
    return Number(Math.max(0.1, Math.min(2.0, multiplier)).toFixed(2))
  }
  
  /**
   * Determine primary reason for weekend behavior
   */
  private determineWeekendReason(
    shouldTrade: boolean,
    gapSize: number,
    hasNews: boolean,
    personalityBias: number,
    config: WeekendConfig
  ): string {
    if (!shouldTrade) {
      if (gapSize > this.GAP_THRESHOLDS.large) {
        return 'avoiding_large_gap'
      } else if (hasNews) {
        return 'waiting_for_news_clarity'
      } else if (!config.tradeSundayOpen) {
        return 'prefer_monday_open'
      } else {
        return 'weekend_rest_preference'
      }
    } else {
      if (gapSize > this.GAP_THRESHOLDS.medium && config.gapStrategy === 'follow') {
        return 'gap_momentum_opportunity'
      } else if (gapSize > this.GAP_THRESHOLDS.medium && config.gapStrategy === 'fade') {
        return 'gap_fade_opportunity'
      } else if (hasNews && config.newsReactionStyle === 'opportunistic') {
        return 'weekend_news_opportunity'
      } else if (personalityBias > 0.2) {
        return 'personality_driven_trading'
      } else {
        return 'sunday_session_preference'
      }
    }
  }
  
  /**
   * Update weekend behavior history
   */
  private updateWeekendHistory(personalityId: string, behavior: WeekendBehaviorResult): void {
    const history = this.weekendHistory.get(personalityId) || []
    history.push(behavior)
    
    // Keep only last 20 weekend decisions
    if (history.length > 20) {
      history.shift()
    }
    
    this.weekendHistory.set(personalityId, history)
  }
  
  /**
   * Get weekend behavior statistics
   */
  public getWeekendStats(personalityId: string): {
    config: WeekendConfig | undefined
    sundayTradingRate: number
    averageRiskMultiplier: number
    gapStrategyUsage: Record<GapStrategy, number>
    newsReactionPatterns: Record<NewsReactionStyle, number>
    recentBehaviors: WeekendBehaviorResult[]
  } {
    const history = this.weekendHistory.get(personalityId) || []
    
    const sundayTradingRate = history.length > 0 
      ? history.filter(h => h.shouldTrade).length / history.length 
      : 0
    
    const averageRiskMultiplier = history.length > 0
      ? history.reduce((sum, h) => sum + h.riskMultiplier, 0) / history.length
      : 0
    
    // Calculate strategy and reaction usage
    const gapStrategyUsage: Record<GapStrategy, number> = { avoid: 0, fade: 0, follow: 0 }
    const newsReactionPatterns: Record<NewsReactionStyle, number> = { ignore: 0, cautious: 0, opportunistic: 0 }
    
    history.forEach(h => {
      gapStrategyUsage[h.gapStrategy]++
      newsReactionPatterns[h.newsReaction]++
    })
    
    return {
      config: this.configs.get(personalityId),
      sundayTradingRate,
      averageRiskMultiplier,
      gapStrategyUsage,
      newsReactionPatterns,
      recentBehaviors: history.slice(-10)
    }
  }
  
  /**
   * Create weekend session for testing
   */
  public createWeekendSession(
    start: Date,
    gapSize: number = 0,
    newsEvents: string[] = []
  ): WeekendSession {
    const end = new Date(start.getTime() + 4 * 60 * 60 * 1000) // 4 hours
    
    return {
      start,
      end,
      type: start.getDay() === 0 ? 'sunday_open' : 'weekend_close',
      majorPairs: true,
      newsEvents
    }
  }
  
  /**
   * Validate weekend behavior is consistent with personality
   */
  public validateWeekendBehavior(personalityId: string): {
    isValid: boolean
    consistencyScore: number
    issues: string[]
  } {
    const stats = this.getWeekendStats(personalityId)
    const config = stats.config
    const issues: string[] = []
    
    if (!config) {
      return { isValid: false, consistencyScore: 0, issues: ['No configuration found'] }
    }
    
    // Check Sunday trading rate consistency
    const expectedRate = config.tradeSundayOpen ? 0.6 : 0.3
    const actualRate = stats.sundayTradingRate
    const rateDifference = Math.abs(actualRate - expectedRate)
    
    if (rateDifference > 0.4) {
      issues.push(`Sunday trading rate inconsistent: expected ~${expectedRate}, actual ${actualRate}`)
    }
    
    // Check risk multiplier consistency
    if (stats.averageRiskMultiplier > 1.5) {
      issues.push('Average weekend risk too high')
    } else if (stats.averageRiskMultiplier < 0.3) {
      issues.push('Average weekend risk too low')
    }
    
    const consistencyScore = Math.max(0, 1 - (rateDifference + issues.length * 0.2))
    
    return {
      isValid: issues.length === 0,
      consistencyScore,
      issues
    }
  }
  
  /**
   * Reset weekend configuration for a personality
   */
  public resetPersonality(personalityId: string): void {
    this.configs.delete(personalityId)
    this.weekendHistory.delete(personalityId)
  }
}