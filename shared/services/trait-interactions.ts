/**
 * Trading Personality Trait Interaction System
 * 
 * This service manages complex interactions between personality traits to create
 * realistic behavioral patterns that distinguish aggressive vs conservative traders
 * and morning vs evening trading preferences.
 */

import {
  TradingPersonality,
  PersonalityTraits,
  TradingTimePreferences,
  RiskAppetite,
  BehavioralPatterns
} from '../types/personality'

/**
 * Trait interaction weights for behavioral modeling
 */
interface TraitInteractionWeights {
  primary: keyof PersonalityTraits
  secondary: keyof PersonalityTraits
  coefficient: number
  effect: 'amplify' | 'dampen' | 'invert'
}

/**
 * Time-based trait modifiers
 */
interface TimeBasedModifiers {
  sessionMultipliers: {
    asian: number
    london: number
    newyork: number
    overlap: number
  }
  hourlyVariance: Record<number, number> // 0-23 hour modifiers
  weekendBehavior: number
  holidayBehavior: number
}

/**
 * Aggressive vs Conservative trait profiles
 */
interface RiskProfileTraits {
  aggressive: {
    traitRanges: Partial<Record<keyof PersonalityTraits, { min: number; max: number }>>
    riskMultipliers: { base: number; variance: number; scaling: number }
    preferredConditions: string[]
    avoidedConditions: string[]
  }
  conservative: {
    traitRanges: Partial<Record<keyof PersonalityTraits, { min: number; max: number }>>
    riskMultipliers: { base: number; variance: number; scaling: number }
    preferredConditions: string[]
    avoidedConditions: string[]
  }
}

/**
 * Morning vs Evening trader profiles
 */
interface TimeProfileTraits {
  morning: {
    peakHours: number[]
    traitModifiers: Partial<PersonalityTraits>
    sessionPreference: number[]
    marketConditions: string[]
  }
  evening: {
    peakHours: number[]
    traitModifiers: Partial<PersonalityTraits>
    sessionPreference: number[]
    marketConditions: string[]
  }
}

/**
 * Complex behavioral interaction result
 */
interface TraitInteractionResult {
  adjustedTraits: PersonalityTraits
  riskModifications: Partial<RiskAppetite>
  timeModifications: Partial<TradingTimePreferences>
  behavioralAdjustments: Partial<BehavioralPatterns>
  marketConditionPreferences: string[]
  optimalTradingWindows: Array<{ start: number; end: number; intensity: number }>
}

/**
 * Trait Interaction Manager
 */
export class TraitInteractionManager {
  
  private readonly traitInteractions: TraitInteractionWeights[] = [
    // Risk tolerance interactions
    { primary: 'riskTolerance', secondary: 'emotionality', coefficient: -0.3, effect: 'dampen' },
    { primary: 'riskTolerance', secondary: 'discipline', coefficient: 0.2, effect: 'amplify' },
    { primary: 'riskTolerance', secondary: 'confidence', coefficient: 0.4, effect: 'amplify' },
    
    // Patience interactions
    { primary: 'patience', secondary: 'emotionality', coefficient: -0.4, effect: 'dampen' },
    { primary: 'patience', secondary: 'discipline', coefficient: 0.3, effect: 'amplify' },
    { primary: 'patience', secondary: 'adaptability', coefficient: 0.2, effect: 'amplify' },
    
    // Confidence interactions
    { primary: 'confidence', secondary: 'emotionality', coefficient: -0.2, effect: 'dampen' },
    { primary: 'confidence', secondary: 'discipline', coefficient: 0.15, effect: 'amplify' },
    
    // Discipline interactions
    { primary: 'discipline', secondary: 'emotionality', coefficient: -0.5, effect: 'dampen' },
    { primary: 'discipline', secondary: 'adaptability', coefficient: 0.1, effect: 'amplify' },
    
    // Adaptability interactions
    { primary: 'adaptability', secondary: 'emotionality', coefficient: -0.1, effect: 'dampen' },
    { primary: 'adaptability', secondary: 'patience', coefficient: -0.2, effect: 'dampen' }
  ]

  private readonly aggressiveConservativeProfiles: RiskProfileTraits = {
    aggressive: {
      traitRanges: {
        riskTolerance: { min: 65, max: 95 },
        confidence: { min: 60, max: 90 },
        emotionality: { min: 40, max: 75 },
        discipline: { min: 45, max: 80 },
        patience: { min: 20, max: 60 },
        adaptability: { min: 55, max: 85 }
      },
      riskMultipliers: { base: 1.3, variance: 0.8, scaling: 1.5 },
      preferredConditions: [
        'high_volatility', 'momentum_breakouts', 'news_events', 
        'gap_trading', 'trend_acceleration', 'volatility_spikes'
      ],
      avoidedConditions: [
        'low_volatility', 'range_bound_markets', 'consolidation',
        'holiday_trading', 'thin_liquidity'
      ]
    },
    conservative: {
      traitRanges: {
        riskTolerance: { min: 15, max: 45 },
        confidence: { min: 35, max: 70 },
        emotionality: { min: 10, max: 40 },
        discipline: { min: 70, max: 95 },
        patience: { min: 60, max: 95 },
        adaptability: { min: 30, max: 70 }
      },
      riskMultipliers: { base: 0.7, variance: 0.3, scaling: 0.6 },
      preferredConditions: [
        'stable_trends', 'clear_patterns', 'high_probability_setups',
        'established_support_resistance', 'low_volatility', 'predictable_moves'
      ],
      avoidedConditions: [
        'high_volatility', 'gap_trading', 'news_spikes',
        'uncertain_patterns', 'low_liquidity', 'exotic_pairs'
      ]
    }
  }

  private readonly morningEveningProfiles: TimeProfileTraits = {
    morning: {
      peakHours: [6, 7, 8, 9, 10, 11], // 6 AM - 11 AM UTC
      traitModifiers: {
        confidence: 5,
        patience: 10,
        discipline: 8,
        emotionality: -5,
        riskTolerance: 3,
        adaptability: 5
      },
      sessionPreference: [90, 95, 85, 100], // [asian, london, newyork, overlap]
      marketConditions: [
        'london_open_volatility', 'european_news', 'morning_momentum',
        'session_transitions', 'early_trend_development'
      ]
    },
    evening: {
      peakHours: [19, 20, 21, 22, 23, 0, 1, 2], // 7 PM - 2 AM UTC
      traitModifiers: {
        confidence: -3,
        patience: 15,
        discipline: 5,
        emotionality: -8,
        riskTolerance: -5,
        adaptability: 10
      },
      sessionPreference: [95, 30, 40, 20], // [asian, london, newyork, overlap]
      marketConditions: [
        'asian_range_trading', 'overnight_positions', 'carry_trades',
        'lower_volatility', 'technical_patterns', 'patient_setups'
      ]
    }
  }

  /**
   * Apply complex trait interactions to enhance personality realism
   */
  public applyTraitInteractions(personality: TradingPersonality): TraitInteractionResult {
    const baseTraits = { ...personality.traits }
    
    // Apply trait interaction effects
    const adjustedTraits = this.calculateTraitInteractions(baseTraits)
    
    // Determine risk profile classification
    const riskProfile = this.classifyRiskProfile(adjustedTraits)
    
    // Determine time profile classification
    const timeProfile = this.classifyTimeProfile(personality.timePreferences, adjustedTraits)
    
    // Apply profile-specific modifications
    const riskModifications = this.applyRiskProfileModifications(riskProfile, adjustedTraits)
    const timeModifications = this.applyTimeProfileModifications(timeProfile, adjustedTraits)
    const behavioralAdjustments = this.calculateBehavioralAdjustments(riskProfile, timeProfile, adjustedTraits)
    
    // Generate market condition preferences
    const marketConditionPreferences = this.generateMarketConditionPreferences(riskProfile, timeProfile)
    
    // Calculate optimal trading windows
    const optimalTradingWindows = this.calculateOptimalTradingWindows(timeProfile, adjustedTraits)

    return {
      adjustedTraits,
      riskModifications,
      timeModifications,
      behavioralAdjustments,
      marketConditionPreferences,
      optimalTradingWindows
    }
  }

  /**
   * Calculate trait interactions based on psychological relationships
   */
  private calculateTraitInteractions(baseTraits: PersonalityTraits): PersonalityTraits {
    const adjustedTraits = { ...baseTraits }

    for (const interaction of this.traitInteractions) {
      const primaryValue = baseTraits[interaction.primary]
      const secondaryValue = baseTraits[interaction.secondary]
      
      const interactionEffect = (secondaryValue - 50) * interaction.coefficient
      
      let adjustment: number
      switch (interaction.effect) {
        case 'amplify':
          adjustment = interactionEffect
          break
        case 'dampen':
          adjustment = interactionEffect
          break
        case 'invert':
          adjustment = -interactionEffect
          break
      }

      // Apply the adjustment with bounds checking
      adjustedTraits[interaction.primary] = Math.max(0, Math.min(100, 
        primaryValue + adjustment
      ))
    }

    return adjustedTraits
  }

  /**
   * Classify personality as aggressive or conservative
   */
  private classifyRiskProfile(traits: PersonalityTraits): 'aggressive' | 'conservative' | 'moderate' {
    const riskScore = (
      traits.riskTolerance * 0.4 +
      traits.confidence * 0.2 +
      traits.emotionality * 0.1 +
      (100 - traits.discipline) * 0.2 +
      (100 - traits.patience) * 0.1
    )

    if (riskScore >= 65) return 'aggressive'
    if (riskScore <= 40) return 'conservative'
    return 'moderate'
  }

  /**
   * Classify personality as morning or evening trader
   */
  private classifyTimeProfile(timePrefs: TradingTimePreferences, traits: PersonalityTraits): 'morning' | 'evening' | 'flexible' {
    const morningSessionActivity = (timePrefs.sessionActivity.london + timePrefs.sessionActivity.newyork + timePrefs.sessionActivity.overlap) / 3
    const eveningSessionActivity = timePrefs.sessionActivity.asian
    
    const morningScore = morningSessionActivity + (traits.confidence * 0.1) + (traits.adaptability * 0.1)
    const eveningScore = eveningSessionActivity + (traits.patience * 0.1) + (traits.discipline * 0.1)
    
    const scoreDifference = Math.abs(morningScore - eveningScore)
    
    if (scoreDifference < 15) return 'flexible'
    return morningScore > eveningScore ? 'morning' : 'evening'
  }

  /**
   * Apply risk profile specific modifications
   */
  private applyRiskProfileModifications(
    riskProfile: 'aggressive' | 'conservative' | 'moderate',
    traits: PersonalityTraits
  ): Partial<RiskAppetite> {
    if (riskProfile === 'moderate') {
      return {} // No specific modifications for moderate profiles
    }

    const profile = this.aggressiveConservativeProfiles[riskProfile]
    const baseRiskPerTrade = traits.riskTolerance / 100 * 2 // 0-2% base range
    
    return {
      baseRiskPerTrade: baseRiskPerTrade * profile.riskMultipliers.base,
      riskVariance: {
        min: Math.max(0.3, baseRiskPerTrade * profile.riskMultipliers.base - profile.riskMultipliers.variance),
        max: Math.min(2.5, baseRiskPerTrade * profile.riskMultipliers.base + profile.riskMultipliers.variance)
      },
      performanceScaling: {
        winningStreak: 1.0 + (profile.riskMultipliers.scaling - 1.0) * 0.5,
        losingStreak: 1.0 - (profile.riskMultipliers.scaling - 1.0) * 0.3
      }
    }
  }

  /**
   * Apply time profile specific modifications
   */
  private applyTimeProfileModifications(
    timeProfile: 'morning' | 'evening' | 'flexible',
    traits: PersonalityTraits
  ): Partial<TradingTimePreferences> {
    if (timeProfile === 'flexible') {
      return {} // No specific modifications for flexible profiles
    }

    const profile = this.morningEveningProfiles[timeProfile]
    
    return {
      sessionActivity: {
        asian: profile.sessionPreference[0],
        london: profile.sessionPreference[1],
        newyork: profile.sessionPreference[2],
        overlap: profile.sessionPreference[3]
      },
      weekendActivity: timeProfile === 'evening' ? 40 : 15,
      holidayActivity: timeProfile === 'evening' ? 60 : 25
    }
  }

  /**
   * Calculate behavioral adjustments based on profiles
   */
  private calculateBehavioralAdjustments(
    riskProfile: 'aggressive' | 'conservative' | 'moderate',
    timeProfile: 'morning' | 'evening' | 'flexible',
    traits: PersonalityTraits
  ): Partial<BehavioralPatterns> {
    const baseDecisionSpeed = 3000 // 3 seconds base
    const baseAnalysisTime = 300 // 5 minutes base

    // Risk profile adjustments
    let speedMultiplier = 1.0
    let analysisMultiplier = 1.0
    let stopLossMovement = 50
    let partialProfitTaking = 50
    let letWinnersRun = 50

    if (riskProfile === 'aggressive') {
      speedMultiplier = 0.6 // Faster decisions
      analysisMultiplier = 0.7 // Less analysis time
      stopLossMovement = 70 // More likely to move stops
      partialProfitTaking = 40 // Less likely to take partial profits
      letWinnersRun = 80 // More likely to let winners run
    } else if (riskProfile === 'conservative') {
      speedMultiplier = 1.8 // Slower decisions
      analysisMultiplier = 1.5 // More analysis time
      stopLossMovement = 20 // Less likely to move stops
      partialProfitTaking = 80 // More likely to take partial profits
      letWinnersRun = 30 // Less likely to let winners run
    }

    // Time profile adjustments
    if (timeProfile === 'morning') {
      speedMultiplier *= 0.8 // Slightly faster in morning
      analysisMultiplier *= 0.9 // Slightly less analysis needed
    } else if (timeProfile === 'evening') {
      speedMultiplier *= 1.2 // Slower in evening
      analysisMultiplier *= 1.3 // More thorough analysis
    }

    return {
      decisionSpeed: {
        min: Math.floor(baseDecisionSpeed * speedMultiplier * 0.5),
        max: Math.floor(baseDecisionSpeed * speedMultiplier * 2.0),
        average: Math.floor(baseDecisionSpeed * speedMultiplier)
      },
      analysisTime: {
        min: Math.floor(baseAnalysisTime * analysisMultiplier * 0.3),
        max: Math.floor(baseAnalysisTime * analysisMultiplier * 3.0),
        average: Math.floor(baseAnalysisTime * analysisMultiplier)
      },
      positionManagement: {
        stopLossMovement: Math.max(0, Math.min(100, stopLossMovement + (traits.emotionality - 50) * 0.3)),
        partialProfitTaking: Math.max(0, Math.min(100, partialProfitTaking + (traits.discipline - 50) * 0.4)),
        letWinnersRun: Math.max(0, Math.min(100, letWinnersRun + (traits.patience - 50) * 0.5))
      }
    }
  }

  /**
   * Generate market condition preferences based on profiles
   */
  private generateMarketConditionPreferences(
    riskProfile: 'aggressive' | 'conservative' | 'moderate',
    timeProfile: 'morning' | 'evening' | 'flexible'
  ): string[] {
    const preferences: string[] = []

    // Add risk profile preferences
    if (riskProfile !== 'moderate') {
      const profile = this.aggressiveConservativeProfiles[riskProfile]
      preferences.push(...profile.preferredConditions)
    }

    // Add time profile preferences
    if (timeProfile !== 'flexible') {
      const profile = this.morningEveningProfiles[timeProfile]
      preferences.push(...profile.marketConditions)
    }

    // Add general preferences for moderate/flexible profiles
    if (riskProfile === 'moderate') {
      preferences.push('trend_following', 'breakout_patterns', 'moderate_volatility')
    }

    if (timeProfile === 'flexible') {
      preferences.push('adaptable_strategies', 'multi_session_trading', 'diverse_timeframes')
    }

    return [...new Set(preferences)] // Remove duplicates
  }

  /**
   * Calculate optimal trading windows based on time profile and traits
   */
  private calculateOptimalTradingWindows(
    timeProfile: 'morning' | 'evening' | 'flexible',
    traits: PersonalityTraits
  ): Array<{ start: number; end: number; intensity: number }> {
    const windows: Array<{ start: number; end: number; intensity: number }> = []

    if (timeProfile === 'morning') {
      // London session
      windows.push({ start: 7, end: 12, intensity: 0.9 })
      // NY open
      windows.push({ start: 13, end: 16, intensity: 0.95 })
      // Overlap period
      windows.push({ start: 13, end: 15, intensity: 1.0 })
    } else if (timeProfile === 'evening') {
      // Asian session
      windows.push({ start: 21, end: 6, intensity: 0.9 })
      // Early Asian
      windows.push({ start: 23, end: 2, intensity: 0.95 })
    } else {
      // Flexible - multiple windows based on traits
      if (traits.adaptability > 60) {
        windows.push({ start: 7, end: 11, intensity: 0.7 })
        windows.push({ start: 13, end: 16, intensity: 0.8 })
        windows.push({ start: 21, end: 1, intensity: 0.6 })
      }
    }

    // Adjust intensity based on confidence and discipline
    const intensityModifier = (traits.confidence + traits.discipline) / 200
    return windows.map(window => ({
      ...window,
      intensity: Math.min(1.0, window.intensity * (0.7 + intensityModifier * 0.6))
    }))
  }

  /**
   * Generate time-based trait modifiers for specific hours
   */
  public generateHourlyTraitModifiers(
    timeProfile: 'morning' | 'evening' | 'flexible',
    traits: PersonalityTraits
  ): Record<number, Partial<PersonalityTraits>> {
    const hourlyModifiers: Record<number, Partial<PersonalityTraits>> = {}

    for (let hour = 0; hour < 24; hour++) {
      let modifiers: Partial<PersonalityTraits> = {}

      if (timeProfile === 'morning' && this.morningEveningProfiles.morning.peakHours.includes(hour)) {
        modifiers = this.morningEveningProfiles.morning.traitModifiers
      } else if (timeProfile === 'evening' && this.morningEveningProfiles.evening.peakHours.includes(hour)) {
        modifiers = this.morningEveningProfiles.evening.traitModifiers
      }

      // Apply fatigue effects for extended trading hours
      const hoursFromPeakStart = this.getHoursFromPeakStart(hour, timeProfile)
      if (hoursFromPeakStart > 6) {
        modifiers = {
          ...modifiers,
          confidence: (modifiers.confidence || 0) - (hoursFromPeakStart - 6) * 2,
          patience: (modifiers.patience || 0) - (hoursFromPeakStart - 6) * 1.5,
          discipline: (modifiers.discipline || 0) - (hoursFromPeakStart - 6) * 1
        }
      }

      hourlyModifiers[hour] = modifiers
    }

    return hourlyModifiers
  }

  /**
   * Calculate hours from peak start for fatigue modeling
   */
  private getHoursFromPeakStart(currentHour: number, timeProfile: 'morning' | 'evening' | 'flexible'): number {
    if (timeProfile === 'flexible') return 0

    const profile = this.morningEveningProfiles[timeProfile]
    const peakStart = Math.min(...profile.peakHours)
    
    let hoursDiff = currentHour - peakStart
    if (hoursDiff < 0) hoursDiff += 24 // Handle day wrap-around
    
    return hoursDiff
  }
}

/**
 * Default trait interaction manager instance
 */
export const defaultTraitInteractionManager = new TraitInteractionManager()

/**
 * Utility functions for trait interactions
 */
export const TraitInteractionUtils = {
  /**
   * Validate trait interaction results
   */
  validateTraitInteractions(original: PersonalityTraits, adjusted: PersonalityTraits): boolean {
    for (const key of Object.keys(original) as Array<keyof PersonalityTraits>) {
      if (adjusted[key] < 0 || adjusted[key] > 100) {
        return false
      }
      
      // Check for extreme changes (more than 30 points)
      if (Math.abs(adjusted[key] - original[key]) > 30) {
        return false
      }
    }
    return true
  },

  /**
   * Get interaction strength between two traits
   */
  getInteractionStrength(trait1: keyof PersonalityTraits, trait2: keyof PersonalityTraits): number {
    const interactions = [
      { traits: ['riskTolerance', 'emotionality'], strength: 0.8 },
      { traits: ['patience', 'emotionality'], strength: 0.9 },
      { traits: ['discipline', 'emotionality'], strength: 0.95 },
      { traits: ['confidence', 'riskTolerance'], strength: 0.7 },
      { traits: ['adaptability', 'patience'], strength: 0.6 }
    ]

    const interaction = interactions.find(i => 
      (i.traits[0] === trait1 && i.traits[1] === trait2) ||
      (i.traits[0] === trait2 && i.traits[1] === trait1)
    )

    return interaction?.strength || 0.3
  },

  /**
   * Generate trait interaction summary
   */
  generateInteractionSummary(original: PersonalityTraits, adjusted: PersonalityTraits): {
    significantChanges: Array<{ trait: keyof PersonalityTraits; change: number; direction: 'increase' | 'decrease' }>
    totalAdjustment: number
    stabilityScore: number
  } {
    const significantChanges: Array<{ trait: keyof PersonalityTraits; change: number; direction: 'increase' | 'decrease' }> = []
    let totalAdjustment = 0

    for (const key of Object.keys(original) as Array<keyof PersonalityTraits>) {
      const change = adjusted[key] - original[key]
      totalAdjustment += Math.abs(change)
      
      if (Math.abs(change) > 5) { // Threshold for "significant" change
        significantChanges.push({
          trait: key,
          change: Math.abs(change),
          direction: change > 0 ? 'increase' : 'decrease'
        })
      }
    }

    const stabilityScore = Math.max(0, 100 - totalAdjustment / 6) // Normalize to 0-100

    return { significantChanges, totalAdjustment, stabilityScore }
  }
}