/**
 * Currency Pair Preference Engine
 * 
 * This service intelligently assigns primary and secondary currency pairs to trading
 * personalities based on their traits, risk profile, time preferences, and market
 * conditions. It ensures realistic pair selection that matches trader psychology.
 */

import {
  TradingPersonality,
  PersonalityTraits,
  CurrencyPairPreference,
  TradingTimePreferences,
  PersonalityArchetype
} from '../types/personality'

/**
 * Currency pair metadata with trading characteristics
 */
interface CurrencyPairMetadata {
  symbol: string
  category: 'major' | 'minor' | 'exotic'
  averageSpread: number
  volatility: 'low' | 'medium' | 'high' | 'very_high'
  liquidity: 'high' | 'medium' | 'low'
  correlations: string[] // Correlated pairs
  optimalSessions: Array<'asian' | 'london' | 'newyork' | 'overlap'>
  newsImpact: 'low' | 'medium' | 'high'
  carryPotential: number // -5 to +5 scale
  technicalReliability: 'low' | 'medium' | 'high'
  institutionalFlow: 'low' | 'medium' | 'high'
  retailPopularity: number // 1-10 scale
}

/**
 * Pair selection criteria based on personality traits
 */
interface PairSelectionCriteria {
  riskTolerance: number
  experienceLevel: number
  preferredVolatility: 'low' | 'medium' | 'high'
  sessionFocus: Array<'asian' | 'london' | 'newyork' | 'overlap'>
  newsReaction: 'avoid' | 'neutral' | 'seek'
  carryTradeInterest: boolean
  correlationTolerance: 'low' | 'medium' | 'high'
  spreadSensitivity: 'low' | 'medium' | 'high'
}

/**
 * Pair assignment strategy configuration
 */
interface PairAssignmentStrategy {
  primaryPairCount: { min: number; max: number }
  secondaryPairCount: { min: number; max: number }
  diversificationLevel: 'low' | 'medium' | 'high'
  rotationFrequency: 'never' | 'monthly' | 'quarterly' | 'yearly'
  evolutionSpeed: 'slow' | 'medium' | 'fast'
}

/**
 * Pair preference result with detailed assignment reasoning
 */
interface PairPreferenceResult {
  primary: CurrencyPairPreference[]
  secondary: CurrencyPairPreference[]
  avoided: string[]
  assignment_reasoning: {
    selection_criteria: PairSelectionCriteria
    strategy_applied: string
    diversification_score: number
    risk_distribution: string
    session_coverage: string
  }
  rotation_schedule: Array<{
    date: Date
    changes: Array<{ type: 'add' | 'remove' | 'promote' | 'demote'; pair: string; reason: string }>
  }>
}

/**
 * Currency Pair Preference Engine
 */
export class PairPreferenceEngine {
  
  private readonly pairDatabase: Record<string, CurrencyPairMetadata> = {
    // Major Pairs
    'EURUSD': {
      symbol: 'EURUSD',
      category: 'major',
      averageSpread: 1.2,
      volatility: 'medium',
      liquidity: 'high',
      correlations: ['GBPUSD', 'AUDUSD', 'NZDUSD'],
      optimalSessions: ['london', 'newyork', 'overlap'],
      newsImpact: 'high',
      carryPotential: -1,
      technicalReliability: 'high',
      institutionalFlow: 'high',
      retailPopularity: 10
    },
    'GBPUSD': {
      symbol: 'GBPUSD',
      category: 'major',
      averageSpread: 1.8,
      volatility: 'high',
      liquidity: 'high',
      correlations: ['EURUSD', 'EURGBP'],
      optimalSessions: ['london', 'newyork', 'overlap'],
      newsImpact: 'high',
      carryPotential: 1,
      technicalReliability: 'medium',
      institutionalFlow: 'high',
      retailPopularity: 9
    },
    'USDJPY': {
      symbol: 'USDJPY',
      category: 'major',
      averageSpread: 1.1,
      volatility: 'medium',
      liquidity: 'high',
      correlations: ['EURJPY', 'GBPJPY'],
      optimalSessions: ['asian', 'newyork', 'overlap'],
      newsImpact: 'medium',
      carryPotential: 3,
      technicalReliability: 'high',
      institutionalFlow: 'high',
      retailPopularity: 8
    },
    'USDCHF': {
      symbol: 'USDCHF',
      category: 'major',
      averageSpread: 1.9,
      volatility: 'low',
      liquidity: 'high',
      correlations: ['EURUSD'],
      optimalSessions: ['london', 'newyork'],
      newsImpact: 'medium',
      carryPotential: -2,
      technicalReliability: 'high',
      institutionalFlow: 'medium',
      retailPopularity: 6
    },
    'AUDUSD': {
      symbol: 'AUDUSD',
      category: 'major',
      averageSpread: 1.5,
      volatility: 'medium',
      liquidity: 'high',
      correlations: ['NZDUSD', 'EURUSD'],
      optimalSessions: ['asian', 'overlap'],
      newsImpact: 'medium',
      carryPotential: 2,
      technicalReliability: 'medium',
      institutionalFlow: 'medium',
      retailPopularity: 7
    },
    'USDCAD': {
      symbol: 'USDCAD',
      category: 'major',
      averageSpread: 1.7,
      volatility: 'medium',
      liquidity: 'high',
      correlations: ['CADJPY'],
      optimalSessions: ['newyork', 'overlap'],
      newsImpact: 'medium',
      carryPotential: 1,
      technicalReliability: 'high',
      institutionalFlow: 'medium',
      retailPopularity: 5
    },
    'NZDUSD': {
      symbol: 'NZDUSD',
      category: 'major',
      averageSpread: 2.1,
      volatility: 'high',
      liquidity: 'medium',
      correlations: ['AUDUSD'],
      optimalSessions: ['asian', 'overlap'],
      newsImpact: 'medium',
      carryPotential: 3,
      technicalReliability: 'medium',
      institutionalFlow: 'low',
      retailPopularity: 6
    },

    // Minor Pairs
    'EURJPY': {
      symbol: 'EURJPY',
      category: 'minor',
      averageSpread: 2.1,
      volatility: 'high',
      liquidity: 'medium',
      correlations: ['USDJPY', 'EURUSD'],
      optimalSessions: ['london', 'asian'],
      newsImpact: 'high',
      carryPotential: 2,
      technicalReliability: 'medium',
      institutionalFlow: 'medium',
      retailPopularity: 8
    },
    'GBPJPY': {
      symbol: 'GBPJPY',
      category: 'minor',
      averageSpread: 3.2,
      volatility: 'very_high',
      liquidity: 'medium',
      correlations: ['USDJPY', 'GBPUSD'],
      optimalSessions: ['london', 'asian'],
      newsImpact: 'high',
      carryPotential: 4,
      technicalReliability: 'low',
      institutionalFlow: 'medium',
      retailPopularity: 7
    },
    'EURGBP': {
      symbol: 'EURGBP',
      category: 'minor',
      averageSpread: 2.8,
      volatility: 'low',
      liquidity: 'medium',
      correlations: ['EURUSD', 'GBPUSD'],
      optimalSessions: ['london'],
      newsImpact: 'medium',
      carryPotential: -1,
      technicalReliability: 'high',
      institutionalFlow: 'high',
      retailPopularity: 5
    },
    'AUDCAD': {
      symbol: 'AUDCAD',
      category: 'minor',
      averageSpread: 3.5,
      volatility: 'medium',
      liquidity: 'medium',
      correlations: ['AUDUSD', 'USDCAD'],
      optimalSessions: ['overlap'],
      newsImpact: 'low',
      carryPotential: 1,
      technicalReliability: 'medium',
      institutionalFlow: 'low',
      retailPopularity: 4
    },
    'AUDCHF': {
      symbol: 'AUDCHF',
      category: 'minor',
      averageSpread: 4.1,
      volatility: 'medium',
      liquidity: 'medium',
      correlations: ['AUDUSD', 'USDCHF'],
      optimalSessions: ['overlap'],
      newsImpact: 'low',
      carryPotential: 2,
      technicalReliability: 'medium',
      institutionalFlow: 'low',
      retailPopularity: 3
    },
    'CADJPY': {
      symbol: 'CADJPY',
      category: 'minor',
      averageSpread: 3.8,
      volatility: 'high',
      liquidity: 'medium',
      correlations: ['USDCAD', 'USDJPY'],
      optimalSessions: ['newyork', 'asian'],
      newsImpact: 'medium',
      carryPotential: 3,
      technicalReliability: 'medium',
      institutionalFlow: 'low',
      retailPopularity: 4
    },

    // Exotic Pairs (Selection)
    'USDMXN': {
      symbol: 'USDMXN',
      category: 'exotic',
      averageSpread: 15.2,
      volatility: 'very_high',
      liquidity: 'low',
      correlations: [],
      optimalSessions: ['newyork'],
      newsImpact: 'high',
      carryPotential: 5,
      technicalReliability: 'low',
      institutionalFlow: 'low',
      retailPopularity: 2
    },
    'USDZAR': {
      symbol: 'USDZAR',
      category: 'exotic',
      averageSpread: 18.5,
      volatility: 'very_high',
      liquidity: 'low',
      correlations: [],
      optimalSessions: ['london'],
      newsImpact: 'high',
      carryPotential: 4,
      technicalReliability: 'low',
      institutionalFlow: 'low',
      retailPopularity: 2
    },
    'USDTRY': {
      symbol: 'USDTRY',
      category: 'exotic',
      averageSpread: 25.0,
      volatility: 'very_high',
      liquidity: 'low',
      correlations: [],
      optimalSessions: ['london'],
      newsImpact: 'high',
      carryPotential: 5,
      technicalReliability: 'low',
      institutionalFlow: 'low',
      retailPopularity: 1
    },
    'EURTRY': {
      symbol: 'EURTRY',
      category: 'exotic',
      averageSpread: 28.0,
      volatility: 'very_high',
      liquidity: 'low',
      correlations: ['USDTRY'],
      optimalSessions: ['london'],
      newsImpact: 'high',
      carryPotential: 4,
      technicalReliability: 'low',
      institutionalFlow: 'low',
      retailPopularity: 1
    }
  }

  /**
   * Generate currency pair preferences for a trading personality
   */
  public generatePairPreferences(personality: TradingPersonality): PairPreferenceResult {
    // Analyze personality to determine selection criteria
    const criteria = this.analyzeSelectionCriteria(personality)
    
    // Determine assignment strategy
    const strategy = this.determineAssignmentStrategy(personality, criteria)
    
    // Score and rank all available pairs
    const pairScores = this.scorePairsForPersonality(criteria, personality.timePreferences)
    
    // Select primary and secondary pairs
    const { primary, secondary, avoided } = this.selectPairs(pairScores, strategy, criteria)
    
    // Generate assignment reasoning
    const assignment_reasoning = this.generateAssignmentReasoning(criteria, strategy, primary, secondary)
    
    // Create rotation schedule
    const rotation_schedule = this.createRotationSchedule(personality, strategy)

    return {
      primary,
      secondary,
      avoided,
      assignment_reasoning,
      rotation_schedule
    }
  }

  /**
   * Analyze personality traits to determine pair selection criteria
   */
  private analyzeSelectionCriteria(personality: TradingPersonality): PairSelectionCriteria {
    const traits = personality.traits
    const timePrefs = personality.timePreferences
    
    // Determine preferred volatility
    let preferredVolatility: 'low' | 'medium' | 'high'
    if (traits.riskTolerance > 70 && traits.emotionality < 40) {
      preferredVolatility = 'high'
    } else if (traits.riskTolerance < 40 || traits.emotionality > 60) {
      preferredVolatility = 'low'
    } else {
      preferredVolatility = 'medium'
    }
    
    // Determine session focus
    const sessionFocus: Array<'asian' | 'london' | 'newyork' | 'overlap'> = []
    Object.entries(timePrefs.sessionActivity).forEach(([session, activity]) => {
      if (activity > 60) {
        sessionFocus.push(session as 'asian' | 'london' | 'newyork' | 'overlap')
      }
    })
    
    // Determine news reaction preference
    let newsReaction: 'avoid' | 'neutral' | 'seek'
    if (traits.emotionality > 60 && traits.discipline < 50) {
      newsReaction = 'avoid'
    } else if (traits.adaptability > 70 && traits.confidence > 60) {
      newsReaction = 'seek'
    } else {
      newsReaction = 'neutral'
    }
    
    // Determine carry trade interest
    const carryTradeInterest = traits.patience > 70 && traits.riskTolerance > 40
    
    // Determine correlation tolerance
    let correlationTolerance: 'low' | 'medium' | 'high'
    if (traits.adaptability > 70 && traits.discipline > 60) {
      correlationTolerance = 'high'
    } else if (traits.discipline < 40) {
      correlationTolerance = 'low'
    } else {
      correlationTolerance = 'medium'
    }
    
    // Determine spread sensitivity
    let spreadSensitivity: 'low' | 'medium' | 'high'
    if (traits.riskTolerance < 40 || personality.riskAppetite.baseRiskPerTrade < 1.0) {
      spreadSensitivity = 'high'
    } else if (traits.riskTolerance > 70) {
      spreadSensitivity = 'low'
    } else {
      spreadSensitivity = 'medium'
    }

    return {
      riskTolerance: traits.riskTolerance,
      experienceLevel: personality.evolution.experienceLevel,
      preferredVolatility,
      sessionFocus,
      newsReaction,
      carryTradeInterest,
      correlationTolerance,
      spreadSensitivity
    }
  }

  /**
   * Determine pair assignment strategy based on personality
   */
  private determineAssignmentStrategy(personality: TradingPersonality, criteria: PairSelectionCriteria): PairAssignmentStrategy {
    const traits = personality.traits
    
    // Determine pair counts
    let primaryCount: { min: number; max: number }
    let secondaryCount: { min: number; max: number }
    
    if (criteria.experienceLevel < 30) {
      // Beginners: fewer pairs for focus
      primaryCount = { min: 2, max: 2 }
      secondaryCount = { min: 1, max: 2 }
    } else if (criteria.experienceLevel > 70) {
      // Advanced: more pairs for diversification
      primaryCount = { min: 2, max: 4 }
      secondaryCount = { min: 2, max: 4 }
    } else {
      // Intermediate: standard allocation
      primaryCount = { min: 2, max: 3 }
      secondaryCount = { min: 2, max: 3 }
    }
    
    // Determine diversification level
    let diversificationLevel: 'low' | 'medium' | 'high'
    if (traits.adaptability > 70 && traits.confidence > 60) {
      diversificationLevel = 'high'
    } else if (traits.discipline < 40) {
      diversificationLevel = 'low'
    } else {
      diversificationLevel = 'medium'
    }
    
    // Determine rotation frequency
    let rotationFrequency: 'never' | 'monthly' | 'quarterly' | 'yearly'
    if (traits.adaptability > 80) {
      rotationFrequency = 'monthly'
    } else if (traits.adaptability > 60) {
      rotationFrequency = 'quarterly'
    } else if (traits.adaptability > 40) {
      rotationFrequency = 'yearly'
    } else {
      rotationFrequency = 'never'
    }
    
    // Determine evolution speed
    let evolutionSpeed: 'slow' | 'medium' | 'fast'
    if (personality.evolution.improvementRate > 3) {
      evolutionSpeed = 'fast'
    } else if (personality.evolution.improvementRate > 1.5) {
      evolutionSpeed = 'medium'
    } else {
      evolutionSpeed = 'slow'
    }

    return {
      primaryPairCount: primaryCount,
      secondaryPairCount: secondaryCount,
      diversificationLevel,
      rotationFrequency,
      evolutionSpeed
    }
  }

  /**
   * Score all currency pairs based on personality fit
   */
  private scorePairsForPersonality(
    criteria: PairSelectionCriteria, 
    timePrefs: TradingTimePreferences
  ): Array<{ symbol: string; score: number; reasons: string[] }> {
    const pairScores: Array<{ symbol: string; score: number; reasons: string[] }> = []

    for (const [symbol, metadata] of Object.entries(this.pairDatabase)) {
      let score = 0
      const reasons: string[] = []

      // Volatility preference scoring
      const volatilityScore = this.scoreVolatilityMatch(metadata.volatility, criteria.preferredVolatility)
      score += volatilityScore * 25
      if (volatilityScore > 0.7) reasons.push(`Good volatility match (${metadata.volatility})`)

      // Session alignment scoring
      const sessionScore = this.scoreSessionAlignment(metadata.optimalSessions, criteria.sessionFocus)
      score += sessionScore * 20
      if (sessionScore > 0.7) reasons.push(`Aligns with active sessions`)

      // Experience level appropriateness
      const experienceScore = this.scoreExperienceMatch(metadata, criteria.experienceLevel)
      score += experienceScore * 15
      if (experienceScore > 0.7) reasons.push(`Suitable for experience level`)

      // News impact preference
      const newsScore = this.scoreNewsImpactMatch(metadata.newsImpact, criteria.newsReaction)
      score += newsScore * 10
      if (newsScore > 0.7) reasons.push(`News impact aligns with preference`)

      // Carry trade potential
      if (criteria.carryTradeInterest && Math.abs(metadata.carryPotential) > 2) {
        score += 10
        reasons.push(`Good carry trade potential`)
      }

      // Spread sensitivity
      const spreadScore = this.scoreSpreadSuitability(metadata.averageSpread, criteria.spreadSensitivity)
      score += spreadScore * 10
      if (spreadScore > 0.7) reasons.push(`Acceptable spread costs`)

      // Liquidity preference (higher experience = can handle lower liquidity)
      const liquidityScore = this.scoreLiquidityMatch(metadata.liquidity, criteria.experienceLevel)
      score += liquidityScore * 10
      if (liquidityScore > 0.7) reasons.push(`Good liquidity for skill level`)

      // Technical reliability bonus for disciplined traders
      if (criteria.riskTolerance < 60 && metadata.technicalReliability === 'high') {
        score += 5
        reasons.push(`High technical reliability`)
      }

      // Retail popularity penalty for advanced traders (avoid crowded trades)
      if (criteria.experienceLevel > 60 && metadata.retailPopularity > 8) {
        score -= 5
        reasons.push(`High retail popularity`)
      }

      pairScores.push({ symbol, score: Math.max(0, score), reasons })
    }

    return pairScores.sort((a, b) => b.score - a.score)
  }

  /**
   * Score volatility match between pair and preference
   */
  private scoreVolatilityMatch(pairVolatility: string, preferredVolatility: string): number {
    const volatilityMap = { 'low': 1, 'medium': 2, 'high': 3, 'very_high': 4 }
    const pairVol = volatilityMap[pairVolatility as keyof typeof volatilityMap]
    const prefVol = volatilityMap[preferredVolatility as keyof typeof volatilityMap]
    
    const difference = Math.abs(pairVol - prefVol)
    return Math.max(0, 1 - difference * 0.3)
  }

  /**
   * Score session alignment between pair and trader preferences
   */
  private scoreSessionAlignment(pairSessions: string[], traderSessions: string[]): number {
    if (traderSessions.length === 0) return 0.5 // neutral if no specific preference
    
    const overlap = pairSessions.filter(session => traderSessions.includes(session)).length
    return overlap / Math.max(pairSessions.length, traderSessions.length)
  }

  /**
   * Score experience level appropriateness
   */
  private scoreExperienceMatch(metadata: CurrencyPairMetadata, experienceLevel: number): number {
    // Beginners should avoid exotic pairs and very high volatility
    if (experienceLevel < 30) {
      if (metadata.category === 'exotic' || metadata.volatility === 'very_high') return 0.2
      if (metadata.category === 'major') return 1.0
      return 0.6
    }
    
    // Intermediate traders can handle minors
    if (experienceLevel < 60) {
      if (metadata.category === 'exotic') return 0.4
      return 1.0
    }
    
    // Advanced traders can handle all pairs
    return 1.0
  }

  /**
   * Score news impact alignment
   */
  private scoreNewsImpactMatch(newsImpact: string, newsReaction: string): number {
    const impactMap = { 'low': 1, 'medium': 2, 'high': 3 }
    const impact = impactMap[newsImpact as keyof typeof impactMap]
    
    switch (newsReaction) {
      case 'avoid': return impact === 1 ? 1.0 : impact === 2 ? 0.6 : 0.2
      case 'neutral': return impact === 2 ? 1.0 : 0.7
      case 'seek': return impact === 3 ? 1.0 : impact === 2 ? 0.7 : 0.3
      default: return 0.5
    }
  }

  /**
   * Score spread suitability
   */
  private scoreSpreadSuitability(spread: number, sensitivity: string): number {
    switch (sensitivity) {
      case 'high': return spread < 2 ? 1.0 : spread < 4 ? 0.6 : 0.2
      case 'medium': return spread < 5 ? 1.0 : spread < 10 ? 0.7 : 0.4
      case 'low': return spread < 15 ? 1.0 : 0.6
      default: return 0.5
    }
  }

  /**
   * Score liquidity match
   */
  private scoreLiquidityMatch(liquidity: string, experienceLevel: number): number {
    const liquidityMap = { 'low': 1, 'medium': 2, 'high': 3 }
    const liq = liquidityMap[liquidity as keyof typeof liquidityMap]
    
    // Beginners need high liquidity
    if (experienceLevel < 30) return liq === 3 ? 1.0 : liq === 2 ? 0.5 : 0.1
    // Intermediate can handle medium+
    if (experienceLevel < 60) return liq >= 2 ? 1.0 : 0.3
    // Advanced can handle all
    return 1.0
  }

  /**
   * Select primary and secondary pairs from scored list
   */
  private selectPairs(
    pairScores: Array<{ symbol: string; score: number; reasons: string[] }>,
    strategy: PairAssignmentStrategy,
    criteria: PairSelectionCriteria
  ): { primary: CurrencyPairPreference[]; secondary: CurrencyPairPreference[]; avoided: string[] } {
    const primary: CurrencyPairPreference[] = []
    const secondary: CurrencyPairPreference[] = []
    const avoided: string[] = []
    const used: Set<string> = new Set()

    // Select primary pairs
    const primaryCount = this.randomBetween(strategy.primaryPairCount.min, strategy.primaryPairCount.max)
    
    for (let i = 0; i < primaryCount && i < pairScores.length; i++) {
      const pairScore = pairScores[i]
      
      if (this.shouldAvoidDueToCorrelation(pairScore.symbol, Array.from(used), criteria.correlationTolerance)) {
        continue
      }

      const preference: CurrencyPairPreference = {
        symbol: pairScore.symbol,
        strength: Math.min(95, 70 + (pairScore.score / 100) * 25),
        category: this.pairDatabase[pairScore.symbol].category,
        frequency: this.calculateTradeFrequency(pairScore.score, 'primary'),
        maxPositionSize: this.calculateMaxPositionSize(pairScore.score, criteria.riskTolerance, 'primary')
      }

      primary.push(preference)
      used.add(pairScore.symbol)
    }

    // Select secondary pairs
    const secondaryCount = this.randomBetween(strategy.secondaryPairCount.min, strategy.secondaryPairCount.max)
    
    for (let i = 0; i < pairScores.length && secondary.length < secondaryCount; i++) {
      const pairScore = pairScores[i]
      
      if (used.has(pairScore.symbol)) continue
      if (this.shouldAvoidDueToCorrelation(pairScore.symbol, Array.from(used), criteria.correlationTolerance)) {
        continue
      }

      const preference: CurrencyPairPreference = {
        symbol: pairScore.symbol,
        strength: Math.min(75, 40 + (pairScore.score / 100) * 35),
        category: this.pairDatabase[pairScore.symbol].category,
        frequency: this.calculateTradeFrequency(pairScore.score, 'secondary'),
        maxPositionSize: this.calculateMaxPositionSize(pairScore.score, criteria.riskTolerance, 'secondary')
      }

      secondary.push(preference)
      used.add(pairScore.symbol)
    }

    // Identify avoided pairs (low scoring pairs)
    for (const pairScore of pairScores) {
      if (!used.has(pairScore.symbol) && pairScore.score < 30) {
        avoided.push(pairScore.symbol)
      }
    }

    return { primary, secondary, avoided }
  }

  /**
   * Check if pair should be avoided due to correlation
   */
  private shouldAvoidDueToCorrelation(symbol: string, usedPairs: string[], correlationTolerance: string): boolean {
    const metadata = this.pairDatabase[symbol]
    if (!metadata || correlationTolerance === 'high') return false

    const correlatedWithUsed = metadata.correlations.some(corr => usedPairs.includes(corr))
    
    if (correlationTolerance === 'low') return correlatedWithUsed
    if (correlationTolerance === 'medium') return correlatedWithUsed && usedPairs.length >= 2
    
    return false
  }

  /**
   * Calculate trading frequency for a pair
   */
  private calculateTradeFrequency(score: number, type: 'primary' | 'secondary'): number {
    const baseFrequency = type === 'primary' ? 12 : 6 // trades per month
    const scoreMultiplier = (score / 100)
    return Math.max(1, Math.round(baseFrequency * (0.5 + scoreMultiplier * 0.8)))
  }

  /**
   * Calculate maximum position size for a pair
   */
  private calculateMaxPositionSize(score: number, riskTolerance: number, type: 'primary' | 'secondary'): number {
    const baseSize = type === 'primary' ? 5 : 3 // percentage of account
    const riskMultiplier = riskTolerance / 100
    const scoreMultiplier = (score / 100)
    
    return Math.max(0.5, baseSize * riskMultiplier * (0.6 + scoreMultiplier * 0.7))
  }

  /**
   * Generate detailed assignment reasoning
   */
  private generateAssignmentReasoning(
    criteria: PairSelectionCriteria,
    strategy: PairAssignmentStrategy,
    primary: CurrencyPairPreference[],
    secondary: CurrencyPairPreference[]
  ): PairPreferenceResult['assignment_reasoning'] {
    // Calculate diversification score
    const allPairs = [...primary, ...secondary]
    const categories = new Set(allPairs.map(p => p.category))
    const diversificationScore = (categories.size / 3) * 100 // 3 possible categories

    // Analyze risk distribution
    const avgRisk = allPairs.reduce((sum, p) => sum + p.maxPositionSize, 0) / allPairs.length
    let riskDistribution: string
    if (avgRisk > 4) riskDistribution = 'aggressive'
    else if (avgRisk < 2) riskDistribution = 'conservative'
    else riskDistribution = 'balanced'

    // Analyze session coverage
    const sessionCoverage = criteria.sessionFocus.length > 2 ? 'comprehensive' : 
                           criteria.sessionFocus.length > 1 ? 'focused' : 'limited'

    return {
      selection_criteria: criteria,
      strategy_applied: `${strategy.diversificationLevel}_diversification_${strategy.rotationFrequency}_rotation`,
      diversification_score: Math.round(diversificationScore),
      risk_distribution: riskDistribution,
      session_coverage: sessionCoverage
    }
  }

  /**
   * Create rotation schedule for pair preferences
   */
  private createRotationSchedule(
    personality: TradingPersonality,
    strategy: PairAssignmentStrategy
  ): PairPreferenceResult['rotation_schedule'] {
    if (strategy.rotationFrequency === 'never') return []

    const schedule: PairPreferenceResult['rotation_schedule'] = []
    const now = new Date()
    
    // Determine rotation interval
    let intervalMonths: number
    switch (strategy.rotationFrequency) {
      case 'monthly': intervalMonths = 1; break
      case 'quarterly': intervalMonths = 3; break
      case 'yearly': intervalMonths = 12; break
      default: return []
    }

    // Generate next 4 rotation dates
    for (let i = 1; i <= 4; i++) {
      const rotationDate = new Date(now)
      rotationDate.setMonth(rotationDate.getMonth() + (intervalMonths * i))
      
      const changes = this.generateRotationChanges(personality, strategy, i)
      
      schedule.push({
        date: rotationDate,
        changes
      })
    }

    return schedule
  }

  /**
   * Generate rotation changes for a specific rotation cycle
   */
  private generateRotationChanges(
    personality: TradingPersonality,
    strategy: PairAssignmentStrategy,
    cycleNumber: number
  ): Array<{ type: 'add' | 'remove' | 'promote' | 'demote'; pair: string; reason: string }> {
    const changes: Array<{ type: 'add' | 'remove' | 'promote' | 'demote'; pair: string; reason: string }> = []
    
    // Simulate evolution-based changes
    if (personality.evolution.improvementRate > 2 && cycleNumber % 2 === 0) {
      changes.push({
        type: 'add',
        pair: 'EURJPY', // Example pair addition
        reason: 'Experience level increased, expanding to cross-currency pairs'
      })
    }

    // Simulate performance-based changes
    if (strategy.evolutionSpeed === 'fast' && cycleNumber === 2) {
      changes.push({
        type: 'promote',
        pair: 'GBPUSD',
        reason: 'Strong performance, promoting from secondary to primary'
      })
    }

    // Simulate market condition adaptations
    if (personality.traits.adaptability > 70 && cycleNumber % 3 === 0) {
      changes.push({
        type: 'remove',
        pair: 'USDCHF',
        reason: 'Market conditions changed, removing low-volatility pair'
      })
    }

    return changes
  }

  /**
   * Utility function for random number generation
   */
  private randomBetween(min: number, max: number): number {
    return Math.floor(Math.random() * (max - min + 1)) + min
  }

  /**
   * Update pair preferences based on trading performance
   */
  public updatePairPreferencesBasedOnPerformance(
    currentPreferences: { primary: CurrencyPairPreference[]; secondary: CurrencyPairPreference[] },
    performanceData: Record<string, { pnl: number; trades: number; winRate: number }>
  ): { primary: CurrencyPairPreference[]; secondary: CurrencyPairPreference[] } {
    const updated = {
      primary: [...currentPreferences.primary],
      secondary: [...currentPreferences.secondary]
    }

    // Adjust strengths based on performance
    for (const preference of [...updated.primary, ...updated.secondary]) {
      const performance = performanceData[preference.symbol]
      if (!performance) continue

      // Calculate performance score
      const profitability = performance.pnl > 0 ? 1 : -1
      const winRateScore = (performance.winRate - 50) / 50 // -1 to 1
      const volumeScore = Math.min(1, performance.trades / 50) // 0 to 1
      
      const performanceScore = (profitability * 0.4 + winRateScore * 0.4 + volumeScore * 0.2)
      
      // Adjust strength (max ±15 points)
      const strengthAdjustment = performanceScore * 15
      preference.strength = Math.max(10, Math.min(100, preference.strength + strengthAdjustment))
      
      // Adjust frequency based on performance
      if (performanceScore > 0.3) {
        preference.frequency = Math.min(20, preference.frequency * 1.2)
      } else if (performanceScore < -0.3) {
        preference.frequency = Math.max(1, preference.frequency * 0.8)
      }
    }

    return updated
  }
}

/**
 * Default pair preference engine instance
 */
export const defaultPairPreferenceEngine = new PairPreferenceEngine()

/**
 * Utility functions for pair preference management
 */
export const PairPreferenceUtils = {
  /**
   * Calculate correlation between two currency pairs
   */
  calculatePairCorrelation(pair1: string, pair2: string): number {
    // Simplified correlation calculation - in real implementation would use historical price data
    const commonCurrencies = this.getCommonCurrencies(pair1, pair2)
    return commonCurrencies.length * 0.3 // 0.0 to 0.6 correlation
  },

  /**
   * Get common currencies between two pairs
   */
  getCommonCurrencies(pair1: string, pair2: string): string[] {
    const currencies1 = [pair1.slice(0, 3), pair1.slice(3, 6)]
    const currencies2 = [pair2.slice(0, 3), pair2.slice(3, 6)]
    
    return currencies1.filter(curr => currencies2.includes(curr))
  },

  /**
   * Validate pair preference configuration
   */
  validatePairPreferences(preferences: { primary: CurrencyPairPreference[]; secondary: CurrencyPairPreference[] }): {
    isValid: boolean
    warnings: string[]
    errors: string[]
  } {
    const warnings: string[] = []
    const errors: string[] = []

    // Check pair counts
    if (preferences.primary.length < 2) {
      errors.push('Minimum 2 primary pairs required')
    }
    if (preferences.primary.length > 4) {
      warnings.push('More than 4 primary pairs may reduce focus')
    }

    // Check for excessive correlation
    const allPairs = [...preferences.primary, ...preferences.secondary]
    let highCorrelationCount = 0
    
    for (let i = 0; i < allPairs.length; i++) {
      for (let j = i + 1; j < allPairs.length; j++) {
        const correlation = this.calculatePairCorrelation(allPairs[i].symbol, allPairs[j].symbol)
        if (correlation > 0.7) {
          highCorrelationCount++
        }
      }
    }

    if (highCorrelationCount > 2) {
      warnings.push('High correlation detected between multiple pairs')
    }

    // Check position sizing
    const totalMaxPosition = allPairs.reduce((sum, p) => sum + p.maxPositionSize, 0)
    if (totalMaxPosition > 50) {
      errors.push('Total maximum position size exceeds 50% of account')
    }

    return {
      isValid: errors.length === 0,
      warnings,
      errors
    }
  }
}