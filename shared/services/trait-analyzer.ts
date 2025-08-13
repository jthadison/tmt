/**
 * Trading Personality Trait Analysis Service
 * 
 * This service provides advanced analysis and categorization of trading personalities
 * based on their traits, focusing on key behavioral patterns like risk appetite
 * and time preferences that distinguish different trader types.
 */

import {
  TradingPersonality,
  PersonalityTraits,
  TradingTimePreferences,
  PersonalityArchetype
} from '../types/personality'

/**
 * Trait categories for personality classification
 */
export interface TraitCategories {
  riskProfile: 'conservative' | 'moderate' | 'aggressive' | 'very_aggressive'
  timeProfile: 'morning' | 'afternoon' | 'evening' | 'night' | 'flexible'
  tradingStyle: 'scalper' | 'day_trader' | 'swing_trader' | 'position_trader'
  emotionalProfile: 'disciplined' | 'balanced' | 'emotional' | 'volatile'
  adaptabilityProfile: 'rigid' | 'moderate' | 'adaptive' | 'highly_adaptive'
}

/**
 * Behavioral tendencies based on trait combinations
 */
export interface BehavioralTendencies {
  entryTiming: 'impulsive' | 'quick' | 'deliberate' | 'patient'
  exitStrategy: 'cut_losses_quick' | 'ride_trends' | 'take_profits_early' | 'diamond_hands'
  positionSizing: 'conservative' | 'calculated' | 'aggressive' | 'reckless'
  marketConditions: 'trending' | 'ranging' | 'volatile' | 'all_conditions'
  newsReaction: 'ignore' | 'cautious' | 'reactive' | 'anticipatory'
}

/**
 * Session activity modifiers based on personality traits
 */
export interface SessionActivityModifiers {
  asian: {
    baseActivity: number
    riskAdjustment: number
    pairPreference: string[]
    optimalConditions: string[]
  }
  london: {
    baseActivity: number
    riskAdjustment: number
    pairPreference: string[]
    optimalConditions: string[]
  }
  newyork: {
    baseActivity: number
    riskAdjustment: number
    pairPreference: string[]
    optimalConditions: string[]
  }
  overlap: {
    baseActivity: number
    riskAdjustment: number
    pairPreference: string[]
    optimalConditions: string[]
  }
}

/**
 * Comprehensive personality analysis result
 */
export interface PersonalityAnalysis {
  categories: TraitCategories
  tendencies: BehavioralTendencies
  sessionModifiers: SessionActivityModifiers
  strengthsWeaknesses: {
    strengths: string[]
    weaknesses: string[]
    recommendations: string[]
  }
  compatibilityFactors: {
    marketConditions: string[]
    timeframes: string[]
    instruments: string[]
  }
}

/**
 * Trading Personality Trait Analyzer
 */
export class TraitAnalyzer {
  
  /**
   * Analyze a complete trading personality and categorize traits
   */
  public analyzePersonality(personality: TradingPersonality): PersonalityAnalysis {
    const categories = this.categorizeTraits(personality.traits)
    const tendencies = this.analyzeBehavioralTendencies(personality.traits, personality.timePreferences)
    const sessionModifiers = this.calculateSessionModifiers(personality.traits, personality.timePreferences)
    const strengthsWeaknesses = this.analyzeStrengthsWeaknesses(personality.traits, categories)
    const compatibilityFactors = this.determineCompatibilityFactors(categories, tendencies)

    return {
      categories,
      tendencies,
      sessionModifiers,
      strengthsWeaknesses,
      compatibilityFactors
    }
  }

  /**
   * Categorize personality traits into meaningful classifications
   */
  public categorizeTraits(traits: PersonalityTraits): TraitCategories {
    // Risk Profile Classification
    const riskProfile = this.classifyRiskProfile(traits.riskTolerance, traits.discipline, traits.emotionality)
    
    // Time Profile Classification (requires time preferences for full analysis)
    const timeProfile = this.classifyTimeProfile(traits.patience, traits.adaptability)
    
    // Trading Style Classification
    const tradingStyle = this.classifyTradingStyle(traits.patience, traits.riskTolerance, traits.confidence)
    
    // Emotional Profile Classification
    const emotionalProfile = this.classifyEmotionalProfile(traits.emotionality, traits.discipline, traits.confidence)
    
    // Adaptability Profile Classification
    const adaptabilityProfile = this.classifyAdaptabilityProfile(traits.adaptability, traits.confidence)

    return {
      riskProfile,
      timeProfile,
      tradingStyle,
      emotionalProfile,
      adaptabilityProfile
    }
  }

  /**
   * Analyze behavioral tendencies based on trait combinations
   */
  public analyzeBehavioralTendencies(traits: PersonalityTraits, timePrefs: TradingTimePreferences): BehavioralTendencies {
    const entryTiming = this.analyzeEntryTiming(traits.patience, traits.emotionality, traits.confidence)
    const exitStrategy = this.analyzeExitStrategy(traits.discipline, traits.riskTolerance, traits.emotionality)
    const positionSizing = this.analyzePositionSizing(traits.riskTolerance, traits.discipline, traits.confidence)
    const marketConditions = this.analyzeMarketConditions(traits.adaptability, traits.riskTolerance, timePrefs)
    const newsReaction = this.analyzeNewsReaction(traits.emotionality, traits.adaptability, traits.confidence)

    return {
      entryTiming,
      exitStrategy,
      positionSizing,
      marketConditions,
      newsReaction
    }
  }

  /**
   * Calculate session-specific activity modifiers
   */
  public calculateSessionModifiers(traits: PersonalityTraits, timePrefs: TradingTimePreferences): SessionActivityModifiers {
    const baseRiskAdjustment = (traits.riskTolerance - 50) / 100 // -0.5 to +0.5 adjustment

    return {
      asian: {
        baseActivity: timePrefs.sessionActivity.asian,
        riskAdjustment: this.getAsianSessionRiskAdjustment(traits),
        pairPreference: this.getAsianSessionPairs(traits),
        optimalConditions: this.getAsianSessionConditions(traits)
      },
      london: {
        baseActivity: timePrefs.sessionActivity.london,
        riskAdjustment: this.getLondonSessionRiskAdjustment(traits),
        pairPreference: this.getLondonSessionPairs(traits),
        optimalConditions: this.getLondonSessionConditions(traits)
      },
      newyork: {
        baseActivity: timePrefs.sessionActivity.newyork,
        riskAdjustment: this.getNewYorkSessionRiskAdjustment(traits),
        pairPreference: this.getNewYorkSessionPairs(traits),
        optimalConditions: this.getNewYorkSessionConditions(traits)
      },
      overlap: {
        baseActivity: timePrefs.sessionActivity.overlap,
        riskAdjustment: this.getOverlapSessionRiskAdjustment(traits),
        pairPreference: this.getOverlapSessionPairs(traits),
        optimalConditions: this.getOverlapSessionConditions(traits)
      }
    }
  }

  /**
   * Risk Profile Classification
   */
  private classifyRiskProfile(riskTolerance: number, discipline: number, emotionality: number): TraitCategories['riskProfile'] {
    const adjustedRisk = riskTolerance - (emotionality * 0.3) + (discipline * 0.2)
    
    if (adjustedRisk >= 75) return 'very_aggressive'
    if (adjustedRisk >= 60) return 'aggressive'
    if (adjustedRisk >= 40) return 'moderate'
    return 'conservative'
  }

  /**
   * Time Profile Classification
   */
  private classifyTimeProfile(patience: number, adaptability: number): TraitCategories['timeProfile'] {
    // This is a simplified classification - full implementation would use time preferences
    const timeScore = (patience + adaptability) / 2
    
    if (timeScore >= 75) return 'flexible'
    if (timeScore >= 60) return 'afternoon'
    if (timeScore >= 40) return 'morning'
    return 'evening'
  }

  /**
   * Trading Style Classification
   */
  private classifyTradingStyle(patience: number, riskTolerance: number, confidence: number): TraitCategories['tradingStyle'] {
    const styleScore = patience * 0.5 + riskTolerance * 0.3 + confidence * 0.2
    
    if (patience < 30 && riskTolerance > 70) return 'scalper'
    if (patience < 50 && styleScore < 50) return 'day_trader'
    if (patience > 70 && styleScore > 60) return 'position_trader'
    return 'swing_trader'
  }

  /**
   * Emotional Profile Classification
   */
  private classifyEmotionalProfile(emotionality: number, discipline: number, confidence: number): TraitCategories['emotionalProfile'] {
    const emotionalStability = discipline - emotionality + (confidence * 0.5)
    
    if (emotionalStability >= 50) return 'disciplined'
    if (emotionalStability >= 20) return 'balanced'
    if (emotionalStability >= -20) return 'emotional'
    return 'volatile'
  }

  /**
   * Adaptability Profile Classification
   */
  private classifyAdaptabilityProfile(adaptability: number, confidence: number): TraitCategories['adaptabilityProfile'] {
    const adaptabilityScore = adaptability + (confidence * 0.3)
    
    if (adaptabilityScore >= 80) return 'highly_adaptive'
    if (adaptabilityScore >= 60) return 'adaptive'
    if (adaptabilityScore >= 40) return 'moderate'
    return 'rigid'
  }

  /**
   * Entry Timing Analysis
   */
  private analyzeEntryTiming(patience: number, emotionality: number, confidence: number): BehavioralTendencies['entryTiming'] {
    const timingScore = patience - emotionality + (confidence * 0.3)
    
    if (timingScore >= 50) return 'patient'
    if (timingScore >= 20) return 'deliberate'
    if (timingScore >= -10) return 'quick'
    return 'impulsive'
  }

  /**
   * Exit Strategy Analysis
   */
  private analyzeExitStrategy(discipline: number, riskTolerance: number, emotionality: number): BehavioralTendencies['exitStrategy'] {
    const exitScore = discipline + riskTolerance - (emotionality * 1.2)
    
    if (exitScore >= 80 && riskTolerance > 60) return 'ride_trends'
    if (exitScore >= 60) return 'diamond_hands'
    if (discipline > emotionality) return 'cut_losses_quick'
    return 'take_profits_early'
  }

  /**
   * Position Sizing Analysis
   */
  private analyzePositionSizing(riskTolerance: number, discipline: number, confidence: number): BehavioralTendencies['positionSizing'] {
    const sizingScore = riskTolerance + confidence - (discipline * 0.5)
    
    if (sizingScore >= 90) return 'reckless'
    if (sizingScore >= 70) return 'aggressive'
    if (sizingScore >= 40) return 'calculated'
    return 'conservative'
  }

  /**
   * Market Conditions Analysis
   */
  private analyzeMarketConditions(adaptability: number, riskTolerance: number, timePrefs: TradingTimePreferences): BehavioralTendencies['marketConditions'] {
    const conditionsScore = adaptability + (riskTolerance * 0.5)
    const isFlexibleSchedule = timePrefs.preferredSessions.length > 2
    
    if (conditionsScore >= 80 && isFlexibleSchedule) return 'all_conditions'
    if (riskTolerance > 70) return 'volatile'
    if (adaptability < 40) return 'ranging'
    return 'trending'
  }

  /**
   * News Reaction Analysis
   */
  private analyzeNewsReaction(emotionality: number, adaptability: number, confidence: number): BehavioralTendencies['newsReaction'] {
    const reactionScore = emotionality + adaptability + (confidence * 0.3)
    
    if (reactionScore >= 90) return 'anticipatory'
    if (reactionScore >= 70) return 'reactive'
    if (reactionScore >= 40) return 'cautious'
    return 'ignore'
  }

  /**
   * Session-specific risk adjustments and preferences
   */
  private getAsianSessionRiskAdjustment(traits: PersonalityTraits): number {
    // Asian session typically lower volatility - conservative traders prefer, aggressive reduce risk
    const baseAdjustment = (traits.patience - 50) / 200 // -0.25 to +0.25
    const disciplineBonus = traits.discipline > 70 ? 0.1 : 0
    return baseAdjustment + disciplineBonus
  }

  private getLondonSessionRiskAdjustment(traits: PersonalityTraits): number {
    // London session moderate volatility - balanced approach
    return (traits.adaptability - 50) / 200
  }

  private getNewYorkSessionRiskAdjustment(traits: PersonalityTraits): number {
    // NY session high volatility - aggressive traders thrive
    const aggressiveBonus = traits.riskTolerance > 70 ? 0.15 : 0
    const emotionalPenalty = traits.emotionality > 60 ? -0.1 : 0
    return aggressiveBonus + emotionalPenalty
  }

  private getOverlapSessionRiskAdjustment(traits: PersonalityTraits): number {
    // Overlap highest volatility - requires confidence and discipline
    const confidenceBonus = traits.confidence > 70 ? 0.2 : 0
    const disciplineRequirement = traits.discipline > 60 ? 0.1 : -0.15
    return confidenceBonus + disciplineRequirement
  }

  private getAsianSessionPairs(traits: PersonalityTraits): string[] {
    if (traits.riskTolerance < 40) return ['USDJPY', 'AUDUSD', 'NZDUSD']
    if (traits.riskTolerance > 70) return ['AUDJPY', 'NZDJPY', 'EURJPY']
    return ['USDJPY', 'AUDUSD', 'EURJPY', 'GBPJPY']
  }

  private getLondonSessionPairs(traits: PersonalityTraits): string[] {
    if (traits.riskTolerance < 40) return ['EURUSD', 'GBPUSD', 'EURGBP']
    if (traits.riskTolerance > 70) return ['GBPJPY', 'EURGBP', 'GBPAUD']
    return ['EURUSD', 'GBPUSD', 'EURJPY', 'GBPJPY']
  }

  private getNewYorkSessionPairs(traits: PersonalityTraits): string[] {
    if (traits.riskTolerance < 40) return ['EURUSD', 'USDCAD', 'USDCHF']
    if (traits.riskTolerance > 70) return ['GBPUSD', 'AUDUSD', 'EURJPY']
    return ['EURUSD', 'GBPUSD', 'USDCAD', 'USDJPY']
  }

  private getOverlapSessionPairs(traits: PersonalityTraits): string[] {
    if (traits.riskTolerance < 40) return ['EURUSD', 'GBPUSD']
    if (traits.riskTolerance > 70) return ['GBPJPY', 'EURJPY', 'AUDJPY']
    return ['EURUSD', 'GBPUSD', 'EURJPY', 'GBPJPY']
  }

  private getAsianSessionConditions(traits: PersonalityTraits): string[] {
    const conditions = ['low_volatility', 'range_trading']
    if (traits.patience > 70) conditions.push('accumulation_patterns')
    if (traits.discipline > 60) conditions.push('carry_trade_setups')
    return conditions
  }

  private getLondonSessionConditions(traits: PersonalityTraits): string[] {
    const conditions = ['moderate_volatility', 'trend_continuation']
    if (traits.adaptability > 60) conditions.push('breakout_patterns')
    if (traits.confidence > 70) conditions.push('news_driven_moves')
    return conditions
  }

  private getNewYorkSessionConditions(traits: PersonalityTraits): string[] {
    const conditions = ['high_volatility', 'momentum_trading']
    if (traits.riskTolerance > 70) conditions.push('gap_trading')
    if (traits.emotionality < 40) conditions.push('reversal_patterns')
    return conditions
  }

  private getOverlapSessionConditions(traits: PersonalityTraits): string[] {
    const conditions = ['highest_volatility', 'major_breakouts']
    if (traits.confidence > 80) conditions.push('news_scalping')
    if (traits.discipline > 70) conditions.push('institutional_flows')
    return conditions
  }

  /**
   * Analyze strengths and weaknesses based on trait combinations
   */
  private analyzeStrengthsWeaknesses(traits: PersonalityTraits, categories: TraitCategories): {
    strengths: string[]
    weaknesses: string[]
    recommendations: string[]
  } {
    const strengths: string[] = []
    const weaknesses: string[] = []
    const recommendations: string[] = []

    // Analyze each trait for strengths/weaknesses
    if (traits.discipline > 70) {
      strengths.push('Strong risk management', 'Consistent execution')
    } else if (traits.discipline < 40) {
      weaknesses.push('Inconsistent rule following', 'Emotional decision making')
      recommendations.push('Implement automated risk management', 'Practice meditation/mindfulness')
    }

    if (traits.patience > 70) {
      strengths.push('Good timing on entries', 'Lets winners run')
    } else if (traits.patience < 40) {
      weaknesses.push('Premature entries', 'Cuts winners short')
      recommendations.push('Use longer timeframe analysis', 'Set minimum hold times')
    }

    if (traits.confidence > 70) {
      strengths.push('Strong conviction trades', 'Good position sizing')
    } else if (traits.confidence < 40) {
      weaknesses.push('Undersized positions', 'Second-guessing decisions')
      recommendations.push('Start with paper trading', 'Focus on high-probability setups')
    }

    if (traits.adaptability > 70) {
      strengths.push('Adjusts to market conditions', 'Learns from mistakes')
    } else if (traits.adaptability < 40) {
      weaknesses.push('Rigid approach', 'Slow to adapt strategies')
      recommendations.push('Study multiple market environments', 'Regular strategy reviews')
    }

    if (traits.emotionality > 60) {
      weaknesses.push('Emotional trading decisions', 'Revenge trading tendency')
      recommendations.push('Implement cooling-off periods', 'Use position sizing rules')
    } else if (traits.emotionality < 30) {
      strengths.push('Rational decision making', 'Unaffected by losses')
    }

    if (traits.riskTolerance > 80) {
      weaknesses.push('Potentially reckless sizing', 'Overconfidence in bad setups')
      recommendations.push('Implement maximum risk limits', 'Focus on risk-adjusted returns')
    } else if (traits.riskTolerance < 30) {
      strengths.push('Conservative approach', 'Good capital preservation')
      weaknesses.push('May miss profitable opportunities', 'Undersized positions')
      recommendations.push('Gradually increase position sizes', 'Focus on high win-rate strategies')
    }

    return { strengths, weaknesses, recommendations }
  }

  /**
   * Determine compatibility factors for optimal trading conditions
   */
  private determineCompatibilityFactors(categories: TraitCategories, tendencies: BehavioralTendencies): {
    marketConditions: string[]
    timeframes: string[]
    instruments: string[]
  } {
    const marketConditions: string[] = []
    const timeframes: string[] = []
    const instruments: string[] = []

    // Market conditions based on risk profile and adaptability
    switch (categories.riskProfile) {
      case 'conservative':
        marketConditions.push('stable_trends', 'low_volatility', 'clear_patterns')
        break
      case 'moderate':
        marketConditions.push('moderate_volatility', 'trend_continuation', 'range_breakouts')
        break
      case 'aggressive':
        marketConditions.push('high_volatility', 'momentum_moves', 'news_events')
        break
      case 'very_aggressive':
        marketConditions.push('extreme_volatility', 'gap_trading', 'event_driven')
        break
    }

    // Timeframes based on trading style and patience
    switch (categories.tradingStyle) {
      case 'scalper':
        timeframes.push('1m', '5m', '15m')
        break
      case 'day_trader':
        timeframes.push('5m', '15m', '1h', '4h')
        break
      case 'swing_trader':
        timeframes.push('1h', '4h', '1d')
        break
      case 'position_trader':
        timeframes.push('4h', '1d', '1w')
        break
    }

    // Instruments based on risk profile and experience
    switch (categories.riskProfile) {
      case 'conservative':
        instruments.push('major_pairs', 'low_spread_instruments')
        break
      case 'moderate':
        instruments.push('major_pairs', 'minor_pairs', 'some_commodities')
        break
      case 'aggressive':
        instruments.push('minor_pairs', 'exotic_pairs', 'commodities', 'indices')
        break
      case 'very_aggressive':
        instruments.push('exotic_pairs', 'cryptocurrencies', 'high_beta_stocks')
        break
    }

    return { marketConditions, timeframes, instruments }
  }
}

/**
 * Default trait analyzer instance
 */
export const defaultTraitAnalyzer = new TraitAnalyzer()

/**
 * Utility functions for trait analysis
 */
export const TraitUtils = {
  /**
   * Get personality archetype recommendations based on traits
   */
  getArchetypeRecommendations(traits: PersonalityTraits): PersonalityArchetype[] {
    const recommendations: PersonalityArchetype[] = []
    
    // Conservative recommendations
    if (traits.riskTolerance < 40 && traits.discipline > 60) {
      recommendations.push('conservative_scalper', 'risk_averse_conservative')
    }
    
    // Aggressive recommendations
    if (traits.riskTolerance > 70 && traits.confidence > 60) {
      recommendations.push('aggressive_swing_trader', 'volatility_hunter')
    }
    
    // Time-based recommendations
    if (traits.patience > 70) {
      recommendations.push('carry_trade_specialist', 'technical_pattern_trader')
    } else if (traits.patience < 40) {
      recommendations.push('conservative_scalper', 'news_reaction_trader')
    }
    
    // Balanced recommendations
    if (traits.adaptability > 60 && traits.discipline > 60) {
      recommendations.push('balanced_opportunist')
    }
    
    return recommendations
  },

  /**
   * Calculate trait compatibility score between two personalities
   */
  calculateTraitCompatibility(traits1: PersonalityTraits, traits2: PersonalityTraits): number {
    const differences = Object.keys(traits1).map(key => {
      const k = key as keyof PersonalityTraits
      return Math.abs(traits1[k] - traits2[k])
    })
    
    const avgDifference = differences.reduce((sum, diff) => sum + diff, 0) / differences.length
    return Math.max(0, 100 - avgDifference)
  },

  /**
   * Generate trait evolution suggestions
   */
  generateEvolutionSuggestions(traits: PersonalityTraits): {
    improvementTargets: Array<keyof PersonalityTraits>
    evolutionPath: string
    timeframe: string
  } {
    const improvementTargets: Array<keyof PersonalityTraits> = []
    
    // Identify traits that need improvement
    if (traits.discipline < 60) improvementTargets.push('discipline')
    if (traits.patience < 50) improvementTargets.push('patience')
    if (traits.confidence < 50) improvementTargets.push('confidence')
    if (traits.adaptability < 60) improvementTargets.push('adaptability')
    
    // Identify traits that might be too high (risk management)
    if (traits.emotionality > 70) improvementTargets.push('emotionality')
    if (traits.riskTolerance > 85) improvementTargets.push('riskTolerance')
    
    let evolutionPath = 'balanced_growth'
    if (improvementTargets.includes('discipline')) evolutionPath = 'risk_management_focus'
    if (improvementTargets.includes('confidence')) evolutionPath = 'confidence_building'
    if (improvementTargets.includes('adaptability')) evolutionPath = 'strategy_diversification'
    
    const timeframe = improvementTargets.length > 3 ? '6-12 months' : '3-6 months'
    
    return { improvementTargets, evolutionPath, timeframe }
  }
}