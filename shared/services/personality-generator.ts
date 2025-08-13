/**
 * Trading Personality Generator Service
 * 
 * This service generates unique trading personalities for accounts to create
 * behavioral diversity and avoid AI detection by prop firms.
 */

import {
  TradingPersonality,
  PersonalityTraits,
  PersonalityArchetype,
  TradingTimePreferences,
  CurrencyPairPreference,
  RiskAppetite,
  PersonalityEvolution,
  BehavioralPatterns,
  PersonalityGenerationConfig,
  PersonalityValidation,
  PersonalityTemplate,
  PersonalityPerformance
} from '../types/personality'

/**
 * Default validation constraints for personality generation
 */
export const DEFAULT_PERSONALITY_VALIDATION: PersonalityValidation = {
  traitBounds: {
    riskTolerance: { min: 10, max: 90 },
    patience: { min: 20, max: 95 },
    confidence: { min: 30, max: 85 },
    emotionality: { min: 10, max: 80 },
    discipline: { min: 40, max: 95 },
    adaptability: { min: 25, max: 90 }
  },
  primaryPairCount: { min: 2, max: 3 },
  secondaryPairCount: { min: 2, max: 3 },
  riskLimits: {
    minRiskPerTrade: 0.5,
    maxRiskPerTrade: 2.0,
    maxPortfolioRisk: 10.0
  },
  timeConstraints: {
    minActiveHours: 4,
    maxActiveHours: 16
  }
}

/**
 * Available currency pairs categorized by type
 */
export const CURRENCY_PAIRS = {
  major: [
    'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 
    'AUDUSD', 'USDCAD', 'NZDUSD'
  ],
  minor: [
    'EURJPY', 'GBPJPY', 'EURGBP', 'AUDCAD', 
    'AUDCHF', 'AUDNZD', 'CADJPY', 'CHFJPY',
    'EURNZD', 'EURCAD', 'EURAUD', 'GBPCAD'
  ],
  exotic: [
    'USDMXN', 'USDZAR', 'USDTRY', 'USDSEK',
    'USDNOK', 'USDDKK', 'USDPLN', 'USDHUF',
    'EURTRY', 'GBPTRY', 'AUDSGD', 'NZDSGD'
  ]
} as const

/**
 * Personality archetype templates with predefined characteristics
 */
export const PERSONALITY_ARCHETYPES: Record<PersonalityArchetype, Partial<TradingPersonality>> = {
  conservative_scalper: {
    name: 'Conservative Scalper',
    description: 'Risk-averse trader focused on quick, small profits with major currency pairs',
    traits: {
      riskTolerance: 25,
      patience: 35,
      confidence: 60,
      emotionality: 20,
      discipline: 85,
      adaptability: 50
    },
    riskAppetite: {
      baseRiskPerTrade: 0.8,
      riskVariance: { min: 0.5, max: 1.2 },
      maxPortfolioRisk: 5.0,
      performanceScaling: { winningStreak: 1.1, losingStreak: 0.8 },
      drawdownAdjustments: { mild: 0.9, moderate: 0.7, severe: 0.5 }
    }
  },
  aggressive_swing_trader: {
    name: 'Aggressive Swing Trader',
    description: 'High-risk trader seeking larger moves with diverse currency pairs',
    traits: {
      riskTolerance: 80,
      patience: 70,
      confidence: 85,
      emotionality: 45,
      discipline: 65,
      adaptability: 80
    },
    riskAppetite: {
      baseRiskPerTrade: 1.8,
      riskVariance: { min: 1.2, max: 2.0 },
      maxPortfolioRisk: 12.0,
      performanceScaling: { winningStreak: 1.3, losingStreak: 0.7 },
      drawdownAdjustments: { mild: 0.95, moderate: 0.8, severe: 0.6 }
    }
  },
  morning_momentum_trader: {
    name: 'Morning Momentum Trader',
    description: 'Active during London/NY open, focuses on momentum and volatility',
    traits: {
      riskTolerance: 65,
      patience: 40,
      confidence: 75,
      emotionality: 35,
      discipline: 75,
      adaptability: 70
    },
    timePreferences: {
      preferredSessions: ['london', 'newyork', 'overlap'],
      activeHours: { start: 7, end: 16, timezone: 'UTC' },
      sessionActivity: { asian: 20, london: 90, newyork: 95, overlap: 100 },
      weekendActivity: 10,
      holidayActivity: 25
    }
  },
  evening_range_trader: {
    name: 'Evening Range Trader',
    description: 'Focuses on Asian session range trading with patient approach',
    traits: {
      riskTolerance: 45,
      patience: 85,
      confidence: 55,
      emotionality: 25,
      discipline: 80,
      adaptability: 60
    },
    timePreferences: {
      preferredSessions: ['asian'],
      activeHours: { start: 21, end: 6, timezone: 'UTC' },
      sessionActivity: { asian: 95, london: 30, newyork: 25, overlap: 15 },
      weekendActivity: 40,
      holidayActivity: 60
    }
  },
  news_reaction_trader: {
    name: 'News Reaction Trader',
    description: 'Reacts quickly to economic events and market news',
    traits: {
      riskTolerance: 70,
      patience: 30,
      confidence: 80,
      emotionality: 60,
      discipline: 60,
      adaptability: 90
    },
    behavioralPatterns: {
      decisionSpeed: { min: 500, max: 2000, average: 1000 },
      analysisTime: { min: 30, max: 180, average: 90 },
      positionManagement: {
        stopLossMovement: 40,
        partialProfitTaking: 60,
        letWinnersRun: 45
      },
      emotionalResponses: {
        lossReaction: 'aggressive',
        winReaction: 'confident',
        stressResponse: 'fight'
      }
    }
  },
  technical_pattern_trader: {
    name: 'Technical Pattern Trader',
    description: 'Methodical approach focusing on chart patterns and technical analysis',
    traits: {
      riskTolerance: 55,
      patience: 80,
      confidence: 70,
      emotionality: 30,
      discipline: 90,
      adaptability: 65
    },
    behavioralPatterns: {
      decisionSpeed: { min: 3000, max: 8000, average: 5000 },
      analysisTime: { min: 300, max: 900, average: 600 },
      positionManagement: {
        stopLossMovement: 20,
        partialProfitTaking: 40,
        letWinnersRun: 80
      },
      emotionalResponses: {
        lossReaction: 'neutral',
        winReaction: 'cautious',
        stressResponse: 'freeze'
      }
    }
  },
  carry_trade_specialist: {
    name: 'Carry Trade Specialist',
    description: 'Long-term positions focused on interest rate differentials',
    traits: {
      riskTolerance: 40,
      patience: 95,
      confidence: 65,
      emotionality: 20,
      discipline: 85,
      adaptability: 45
    },
    riskAppetite: {
      baseRiskPerTrade: 1.2,
      riskVariance: { min: 0.8, max: 1.6 },
      maxPortfolioRisk: 8.0,
      performanceScaling: { winningStreak: 1.05, losingStreak: 0.95 },
      drawdownAdjustments: { mild: 0.95, moderate: 0.85, severe: 0.7 }
    }
  },
  volatility_hunter: {
    name: 'Volatility Hunter',
    description: 'Seeks high volatility opportunities in exotic currency pairs',
    traits: {
      riskTolerance: 85,
      patience: 50,
      confidence: 90,
      emotionality: 55,
      discipline: 70,
      adaptability: 85
    },
    riskAppetite: {
      baseRiskPerTrade: 1.9,
      riskVariance: { min: 1.5, max: 2.0 },
      maxPortfolioRisk: 15.0,
      performanceScaling: { winningStreak: 1.4, losingStreak: 0.6 },
      drawdownAdjustments: { mild: 1.0, moderate: 0.85, severe: 0.65 }
    }
  },
  risk_averse_conservative: {
    name: 'Risk Averse Conservative',
    description: 'Minimal risk approach with major pairs and slow, steady growth',
    traits: {
      riskTolerance: 15,
      patience: 90,
      confidence: 45,
      emotionality: 15,
      discipline: 95,
      adaptability: 40
    },
    riskAppetite: {
      baseRiskPerTrade: 0.6,
      riskVariance: { min: 0.5, max: 0.8 },
      maxPortfolioRisk: 3.0,
      performanceScaling: { winningStreak: 1.02, losingStreak: 0.9 },
      drawdownAdjustments: { mild: 0.8, moderate: 0.6, severe: 0.4 }
    }
  },
  balanced_opportunist: {
    name: 'Balanced Opportunist',
    description: 'Balanced approach that adapts to different market conditions',
    traits: {
      riskTolerance: 55,
      patience: 65,
      confidence: 65,
      emotionality: 40,
      discipline: 75,
      adaptability: 80
    },
    riskAppetite: {
      baseRiskPerTrade: 1.3,
      riskVariance: { min: 1.0, max: 1.6 },
      maxPortfolioRisk: 8.0,
      performanceScaling: { winningStreak: 1.2, losingStreak: 0.8 },
      drawdownAdjustments: { mild: 0.9, moderate: 0.75, severe: 0.6 }
    }
  }
}

/**
 * Trading Personality Generator Class
 */
export class PersonalityGenerator {
  private validation: PersonalityValidation

  constructor(validation: PersonalityValidation = DEFAULT_PERSONALITY_VALIDATION) {
    this.validation = validation
  }

  /**
   * Generate a random number within a range with normal distribution
   */
  private generateNormalRandom(min: number, max: number, skew: number = 0): number {
    const range = max - min
    const center = min + range / 2
    const random1 = Math.random()
    const random2 = Math.random()
    
    // Box-Muller transformation for normal distribution
    const normal = Math.sqrt(-2 * Math.log(random1)) * Math.cos(2 * Math.PI * random2)
    
    // Apply skew and scale to range
    const skewed = normal + skew
    const scaled = center + (skewed * range / 6) // 6 sigma range
    
    return Math.max(min, Math.min(max, scaled))
  }

  /**
   * Generate random traits with archetype influence
   */
  private generateTraits(archetype: PersonalityArchetype, randomization: number): PersonalityTraits {
    const archetypeTraits = PERSONALITY_ARCHETYPES[archetype].traits || {}
    const traits: PersonalityTraits = {
      riskTolerance: 50,
      patience: 50,
      confidence: 50,
      emotionality: 50,
      discipline: 50,
      adaptability: 50
    }

    for (const [trait, bounds] of Object.entries(this.validation.traitBounds)) {
      const traitKey = trait as keyof PersonalityTraits
      const archetypeValue = archetypeTraits[traitKey] || 50
      const randomFactor = (randomization / 100) * 30 // Max 30 point deviation
      
      // Blend archetype value with randomization
      const baseValue = archetypeValue
      const randomValue = this.generateNormalRandom(
        Math.max(bounds.min, baseValue - randomFactor),
        Math.min(bounds.max, baseValue + randomFactor)
      )
      
      traits[traitKey] = Math.round(randomValue)
    }

    return traits
  }

  /**
   * Generate trading time preferences
   */
  private generateTimePreferences(archetype: PersonalityArchetype, traits: PersonalityTraits): TradingTimePreferences {
    const archetypePrefs = PERSONALITY_ARCHETYPES[archetype].timePreferences
    
    if (archetypePrefs) {
      // Use archetype preferences with minor variations
      return {
        ...archetypePrefs,
        sessionActivity: {
          asian: Math.max(0, Math.min(100, archetypePrefs.sessionActivity.asian + this.generateNormalRandom(-10, 10))),
          london: Math.max(0, Math.min(100, archetypePrefs.sessionActivity.london + this.generateNormalRandom(-10, 10))),
          newyork: Math.max(0, Math.min(100, archetypePrefs.sessionActivity.newyork + this.generateNormalRandom(-10, 10))),
          overlap: Math.max(0, Math.min(100, archetypePrefs.sessionActivity.overlap + this.generateNormalRandom(-10, 10)))
        }
      }
    }

    // Generate based on traits
    const isPatient = traits.patience > 60
    const isRiskTolerant = traits.riskTolerance > 60
    
    let preferredSessions: Array<'asian' | 'london' | 'newyork' | 'overlap'>
    let activeHours: { start: number; end: number; timezone: string }
    
    if (isRiskTolerant && !isPatient) {
      // High volatility sessions
      preferredSessions = ['london', 'newyork', 'overlap']
      activeHours = { start: 7, end: 16, timezone: 'UTC' }
    } else if (isPatient) {
      // Quieter sessions
      preferredSessions = ['asian']
      activeHours = { start: 21, end: 6, timezone: 'UTC' }
    } else {
      // Mixed approach
      preferredSessions = ['london', 'newyork']
      activeHours = { start: 8, end: 17, timezone: 'UTC' }
    }

    return {
      preferredSessions,
      activeHours,
      sessionActivity: {
        asian: preferredSessions.includes('asian') ? this.generateNormalRandom(70, 95) : this.generateNormalRandom(10, 30),
        london: preferredSessions.includes('london') ? this.generateNormalRandom(80, 95) : this.generateNormalRandom(20, 40),
        newyork: preferredSessions.includes('newyork') ? this.generateNormalRandom(80, 95) : this.generateNormalRandom(20, 40),
        overlap: preferredSessions.includes('overlap') ? this.generateNormalRandom(90, 100) : this.generateNormalRandom(30, 50)
      },
      weekendActivity: this.generateNormalRandom(5, 30),
      holidayActivity: this.generateNormalRandom(10, 40)
    }
  }

  /**
   * Generate currency pair preferences
   */
  private generatePairPreferences(archetype: PersonalityArchetype, traits: PersonalityTraits): {
    primary: CurrencyPairPreference[]
    secondary: CurrencyPairPreference[]
  } {
    const isRiskTolerant = traits.riskTolerance > 60
    const isConservative = traits.riskTolerance < 40
    
    let availablePairs: { symbol: string; category: 'major' | 'minor' | 'exotic' }[]
    
    if (isConservative) {
      // Conservative traders prefer majors
      availablePairs = CURRENCY_PAIRS.major.map(symbol => ({ symbol, category: 'major' as const }))
    } else if (isRiskTolerant) {
      // Risk-tolerant traders include exotics
      availablePairs = [
        ...CURRENCY_PAIRS.major.map(symbol => ({ symbol, category: 'major' as const })),
        ...CURRENCY_PAIRS.minor.map(symbol => ({ symbol, category: 'minor' as const })),
        ...CURRENCY_PAIRS.exotic.map(symbol => ({ symbol, category: 'exotic' as const }))
      ]
    } else {
      // Balanced approach with majors and minors
      availablePairs = [
        ...CURRENCY_PAIRS.major.map(symbol => ({ symbol, category: 'major' as const })),
        ...CURRENCY_PAIRS.minor.map(symbol => ({ symbol, category: 'minor' as const }))
      ]
    }

    // Shuffle and select pairs
    const shuffled = availablePairs.sort(() => Math.random() - 0.5)
    
    const primaryCount = Math.floor(this.generateNormalRandom(
      this.validation.primaryPairCount.min,
      this.validation.primaryPairCount.max
    ))
    
    const secondaryCount = Math.floor(this.generateNormalRandom(
      this.validation.secondaryPairCount.min,
      this.validation.secondaryPairCount.max
    ))

    const primary: CurrencyPairPreference[] = shuffled.slice(0, primaryCount).map(pair => ({
      symbol: pair.symbol,
      strength: this.generateNormalRandom(70, 95),
      category: pair.category,
      frequency: this.generateNormalRandom(8, 15),
      maxPositionSize: this.generateNormalRandom(3, 6)
    }))

    const secondary: CurrencyPairPreference[] = shuffled.slice(primaryCount, primaryCount + secondaryCount).map(pair => ({
      symbol: pair.symbol,
      strength: this.generateNormalRandom(40, 70),
      category: pair.category,
      frequency: this.generateNormalRandom(3, 8),
      maxPositionSize: this.generateNormalRandom(1.5, 3)
    }))

    return { primary, secondary }
  }

  /**
   * Generate risk appetite configuration
   */
  private generateRiskAppetite(archetype: PersonalityArchetype, traits: PersonalityTraits): RiskAppetite {
    const archetypeRisk = PERSONALITY_ARCHETYPES[archetype].riskAppetite
    
    if (archetypeRisk) {
      return {
        ...archetypeRisk,
        baseRiskPerTrade: this.generateNormalRandom(
          Math.max(this.validation.riskLimits.minRiskPerTrade, archetypeRisk.baseRiskPerTrade - 0.2),
          Math.min(this.validation.riskLimits.maxRiskPerTrade, archetypeRisk.baseRiskPerTrade + 0.2)
        )
      }
    }

    // Generate based on risk tolerance trait
    const riskTolerance = traits.riskTolerance / 100
    const baseRisk = this.validation.riskLimits.minRiskPerTrade + 
                    (this.validation.riskLimits.maxRiskPerTrade - this.validation.riskLimits.minRiskPerTrade) * riskTolerance

    return {
      baseRiskPerTrade: Number(baseRisk.toFixed(2)),
      riskVariance: {
        min: Math.max(this.validation.riskLimits.minRiskPerTrade, baseRisk - 0.3),
        max: Math.min(this.validation.riskLimits.maxRiskPerTrade, baseRisk + 0.3)
      },
      maxPortfolioRisk: this.generateNormalRandom(5, 12),
      performanceScaling: {
        winningStreak: this.generateNormalRandom(1.05, 1.3),
        losingStreak: this.generateNormalRandom(0.7, 0.9)
      },
      drawdownAdjustments: {
        mild: this.generateNormalRandom(0.85, 0.95),
        moderate: this.generateNormalRandom(0.7, 0.85),
        severe: this.generateNormalRandom(0.5, 0.7)
      }
    }
  }

  /**
   * Generate personality evolution settings
   */
  private generateEvolution(traits: PersonalityTraits): PersonalityEvolution {
    const improvementRate = this.generateNormalRandom(1, 5) // Points per month
    
    return {
      experienceLevel: this.generateNormalRandom(10, 40), // Start as beginner to intermediate
      improvementRate,
      evolutionTriggers: {
        tradesToNextLevel: Math.floor(this.generateNormalRandom(50, 200)),
        profitThreshold: this.generateNormalRandom(5, 15), // Percentage profit threshold
        timeInMarket: Math.floor(this.generateNormalRandom(1, 6)) // Months
      },
      traitEvolution: {
        improvingTraits: ['confidence', 'discipline', 'adaptability'],
        degradingTraits: ['emotionality']
      },
      seasonalAdjustments: {
        spring: { confidence: 5, adaptability: 3 },
        summer: { patience: -2, emotionality: 3 },
        autumn: { discipline: 4, riskTolerance: -2 },
        winter: { patience: 5, confidence: -3 }
      }
    }
  }

  /**
   * Generate behavioral patterns
   */
  private generateBehavioralPatterns(archetype: PersonalityArchetype, traits: PersonalityTraits): BehavioralPatterns {
    const archetypePatterns = PERSONALITY_ARCHETYPES[archetype].behavioralPatterns
    
    if (archetypePatterns) {
      return archetypePatterns
    }

    // Generate based on traits
    const patience = traits.patience
    const emotionality = traits.emotionality
    const discipline = traits.discipline

    return {
      decisionSpeed: {
        min: Math.floor(this.generateNormalRandom(500, 3000)),
        max: Math.floor(this.generateNormalRandom(3000, 8000)),
        average: Math.floor(this.generateNormalRandom(1500, 5000))
      },
      analysisTime: {
        min: Math.floor(patience * 2 + this.generateNormalRandom(30, 120)),
        max: Math.floor(patience * 8 + this.generateNormalRandom(300, 900)),
        average: Math.floor(patience * 5 + this.generateNormalRandom(180, 600))
      },
      positionManagement: {
        stopLossMovement: Math.round(100 - discipline + this.generateNormalRandom(-10, 10)),
        partialProfitTaking: Math.round(discipline * 0.6 + this.generateNormalRandom(-10, 10)),
        letWinnersRun: Math.round(patience * 0.8 + this.generateNormalRandom(-10, 10))
      },
      emotionalResponses: {
        lossReaction: emotionality > 60 ? 'aggressive' : emotionality < 30 ? 'neutral' : 'conservative',
        winReaction: traits.confidence > 70 ? 'confident' : 'cautious',
        stressResponse: emotionality > 60 ? 'fight' : patience > 70 ? 'freeze' : 'flight'
      }
    }
  }

  /**
   * Generate a complete trading personality
   */
  public generatePersonality(config: PersonalityGenerationConfig, accountId: string): TradingPersonality {
    const { archetype, randomization, evolutionEnabled } = config
    const archetypeTemplate = PERSONALITY_ARCHETYPES[archetype]

    // Generate core components
    const traits = this.generateTraits(archetype, randomization)
    const timePreferences = this.generateTimePreferences(archetype, traits)
    const pairPreferences = this.generatePairPreferences(archetype, traits)
    const riskAppetite = this.generateRiskAppetite(archetype, traits)
    const evolution = evolutionEnabled ? this.generateEvolution(traits) : {
      experienceLevel: 50,
      improvementRate: 0,
      evolutionTriggers: { tradesToNextLevel: 0, profitThreshold: 0, timeInMarket: 0 },
      traitEvolution: { improvingTraits: [], degradingTraits: [] },
      seasonalAdjustments: { spring: {}, summer: {}, autumn: {}, winter: {} }
    }
    const behavioralPatterns = this.generateBehavioralPatterns(archetype, traits)

    // Create personality
    const personality: TradingPersonality = {
      id: `personality_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      name: archetypeTemplate.name || `${archetype.replace(/_/g, ' ')} Trader`,
      description: archetypeTemplate.description || `Generated ${archetype} personality`,
      accountId,
      createdAt: new Date(),
      updatedAt: new Date(),
      isActive: true,
      traits,
      timePreferences,
      pairPreferences,
      riskAppetite,
      evolution,
      behavioralPatterns,
      metadata: {
        archetype,
        compatibility: {},
        performance: {
          totalTrades: 0,
          winRate: 0,
          avgProfitPerTrade: 0,
          maxDrawdown: 0,
          sharpeRatio: 0,
          daysActive: 0,
          lastReviewDate: new Date(),
          trend: 'stable'
        }
      }
    }

    return personality
  }

  /**
   * Generate multiple personalities ensuring diversity
   */
  public generateDiversePersonalities(
    count: number,
    accountIds: string[],
    evolutionEnabled: boolean = true
  ): TradingPersonality[] {
    if (accountIds.length !== count) {
      throw new Error('Number of account IDs must match count')
    }

    const archetypes = Object.keys(PERSONALITY_ARCHETYPES) as PersonalityArchetype[]
    const personalities: TradingPersonality[] = []

    for (let i = 0; i < count; i++) {
      const archetype = archetypes[i % archetypes.length]
      const randomization = this.generateNormalRandom(30, 80) // Moderate to high randomization
      
      const config: PersonalityGenerationConfig = {
        archetype,
        randomization,
        constraints: this.validation,
        evolutionEnabled
      }

      const personality = this.generatePersonality(config, accountIds[i])
      personalities.push(personality)
    }

    return personalities
  }

  /**
   * Validate personality constraints
   */
  public validatePersonality(personality: TradingPersonality): { isValid: boolean; errors: string[] } {
    const errors: string[] = []

    // Validate traits
    for (const [trait, value] of Object.entries(personality.traits)) {
      const bounds = this.validation.traitBounds[trait as keyof PersonalityTraits]
      if (value < bounds.min || value > bounds.max) {
        errors.push(`Trait ${trait} value ${value} is outside bounds [${bounds.min}, ${bounds.max}]`)
      }
    }

    // Validate pair counts
    const primaryCount = personality.pairPreferences.primary.length
    const secondaryCount = personality.pairPreferences.secondary.length

    if (primaryCount < this.validation.primaryPairCount.min || primaryCount > this.validation.primaryPairCount.max) {
      errors.push(`Primary pair count ${primaryCount} is outside bounds [${this.validation.primaryPairCount.min}, ${this.validation.primaryPairCount.max}]`)
    }

    if (secondaryCount < this.validation.secondaryPairCount.min || secondaryCount > this.validation.secondaryPairCount.max) {
      errors.push(`Secondary pair count ${secondaryCount} is outside bounds [${this.validation.secondaryPairCount.min}, ${this.validation.secondaryPairCount.max}]`)
    }

    // Validate risk limits
    const baseRisk = personality.riskAppetite.baseRiskPerTrade
    if (baseRisk < this.validation.riskLimits.minRiskPerTrade || baseRisk > this.validation.riskLimits.maxRiskPerTrade) {
      errors.push(`Base risk ${baseRisk}% is outside bounds [${this.validation.riskLimits.minRiskPerTrade}%, ${this.validation.riskLimits.maxRiskPerTrade}%]`)
    }

    return {
      isValid: errors.length === 0,
      errors
    }
  }
}

/**
 * Default personality generator instance
 */
export const defaultPersonalityGenerator = new PersonalityGenerator()

/**
 * Utility functions for personality management
 */
export const PersonalityUtils = {
  /**
   * Calculate personality compatibility score
   */
  calculateCompatibility(personality1: TradingPersonality, personality2: TradingPersonality): number {
    // Calculate trait differences
    const traitDifferences = Object.keys(personality1.traits).map(trait => {
      const t = trait as keyof PersonalityTraits
      return Math.abs(personality1.traits[t] - personality2.traits[t])
    })

    const avgTraitDifference = traitDifferences.reduce((sum, diff) => sum + diff, 0) / traitDifferences.length

    // Calculate time overlap
    const timeOverlap = this.calculateTimeOverlap(personality1.timePreferences, personality2.timePreferences)

    // Calculate pair overlap
    const pairOverlap = this.calculatePairOverlap(personality1.pairPreferences, personality2.pairPreferences)

    // Compatibility score (0-100, where 100 is most compatible/diverse)
    const compatibilityScore = 100 - (avgTraitDifference * 0.4 + timeOverlap * 0.3 + pairOverlap * 0.3)

    return Math.max(0, Math.min(100, compatibilityScore))
  },

  /**
   * Calculate time overlap between two personalities
   */
  calculateTimeOverlap(prefs1: TradingTimePreferences, prefs2: TradingTimePreferences): number {
    const overlap = prefs1.preferredSessions.filter(session => 
      prefs2.preferredSessions.includes(session)
    ).length

    return (overlap / Math.max(prefs1.preferredSessions.length, prefs2.preferredSessions.length)) * 100
  },

  /**
   * Calculate currency pair overlap between two personalities
   */
  calculatePairOverlap(prefs1: TradingPersonality['pairPreferences'], prefs2: TradingPersonality['pairPreferences']): number {
    const allPairs1 = [...prefs1.primary, ...prefs1.secondary].map(p => p.symbol)
    const allPairs2 = [...prefs2.primary, ...prefs2.secondary].map(p => p.symbol)
    
    const overlap = allPairs1.filter(pair => allPairs2.includes(pair)).length
    const total = new Set([...allPairs1, ...allPairs2]).size

    return (overlap / total) * 100
  },

  /**
   * Generate personality name variations
   */
  generateNameVariations(baseName: string): string[] {
    const variations = [
      baseName,
      `${baseName} Pro`,
      `Advanced ${baseName}`,
      `${baseName} Elite`,
      `${baseName} Specialist`,
      `Dynamic ${baseName}`,
      `Adaptive ${baseName}`
    ]
    
    return variations
  }
}