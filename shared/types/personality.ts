/**
 * Trading Personality System - Core Type Definitions
 * 
 * This module defines the comprehensive type system for trading personalities
 * used in the anti-detection system. Each personality represents a unique
 * behavioral profile that makes accounts appear as different human traders.
 */

/**
 * Core personality traits that define trading behavior
 */
export interface PersonalityTraits {
  /** Risk tolerance level (0-100, where 0 is extremely conservative, 100 is extremely aggressive) */
  riskTolerance: number
  /** Patience level (0-100, affects trade holding time and frequency) */
  patience: number
  /** Confidence level (0-100, affects position sizing and trade conviction) */
  confidence: number
  /** Emotionality (0-100, affects reaction to wins/losses) */
  emotionality: number
  /** Discipline level (0-100, affects adherence to rules and strategy) */
  discipline: number
  /** Adaptability (0-100, affects response to changing market conditions) */
  adaptability: number
}

/**
 * Trading time preferences for different market sessions
 */
export interface TradingTimePreferences {
  /** Preferred trading sessions */
  preferredSessions: Array<'asian' | 'london' | 'newyork' | 'overlap'>
  /** Active trading hours (UTC, 0-23) */
  activeHours: {
    start: number
    end: number
    timezone: string
  }
  /** Session activity levels (0-100) */
  sessionActivity: {
    asian: number
    london: number
    newyork: number
    overlap: number
  }
  /** Weekend trading preference (0-100) */
  weekendActivity: number
  /** Holiday trading preference (0-100) */
  holidayActivity: number
}

/**
 * Currency pair preference with strength weighting
 */
export interface CurrencyPairPreference {
  /** Currency pair symbol (e.g., 'EURUSD') */
  symbol: string
  /** Preference strength (0-100) */
  strength: number
  /** Pair category */
  category: 'major' | 'minor' | 'exotic'
  /** Trading frequency for this pair (trades per week) */
  frequency: number
  /** Maximum position size for this pair (percentage of account) */
  maxPositionSize: number
}

/**
 * Risk appetite configuration with variance ranges
 */
export interface RiskAppetite {
  /** Base risk per trade (percentage of account balance) */
  baseRiskPerTrade: number
  /** Risk variance range (min/max deviation from base) */
  riskVariance: {
    min: number // Minimum risk percentage (e.g., 0.5%)
    max: number // Maximum risk percentage (e.g., 2.0%)
  }
  /** Maximum portfolio risk (total open positions) */
  maxPortfolioRisk: number
  /** Risk scaling factors based on account performance */
  performanceScaling: {
    winningStreak: number // Risk increase multiplier during winning streaks
    losingStreak: number  // Risk decrease multiplier during losing streaks
  }
  /** Drawdown risk adjustments */
  drawdownAdjustments: {
    mild: number    // Risk adjustment for 5-10% drawdown
    moderate: number // Risk adjustment for 10-20% drawdown
    severe: number   // Risk adjustment for >20% drawdown
  }
}

/**
 * Personality evolution parameters for skill improvement simulation
 */
export interface PersonalityEvolution {
  /** Current experience level (0-100) */
  experienceLevel: number
  /** Skill improvement rate (points per month) */
  improvementRate: number
  /** Evolution triggers and thresholds */
  evolutionTriggers: {
    tradesToNextLevel: number
    profitThreshold: number
    timeInMarket: number // months
  }
  /** Trait evolution patterns */
  traitEvolution: {
    /** Which traits improve over time */
    improvingTraits: Array<keyof PersonalityTraits>
    /** Which traits may degrade without practice */
    degradingTraits: Array<keyof PersonalityTraits>
  }
  /** Seasonal adjustments */
  seasonalAdjustments: {
    spring: Partial<PersonalityTraits>
    summer: Partial<PersonalityTraits>
    autumn: Partial<PersonalityTraits>
    winter: Partial<PersonalityTraits>
  }
}

/**
 * Behavioral patterns that define decision-making style
 */
export interface BehavioralPatterns {
  /** Decision speed (milliseconds delay before trade execution) */
  decisionSpeed: {
    min: number
    max: number
    average: number
  }
  /** Chart analysis time (seconds spent analyzing before trading) */
  analysisTime: {
    min: number
    max: number
    average: number
  }
  /** Position management style */
  positionManagement: {
    /** Tendency to move stop losses (0-100) */
    stopLossMovement: number
    /** Tendency to take partial profits (0-100) */
    partialProfitTaking: number
    /** Tendency to let winners run (0-100) */
    letWinnersRun: number
  }
  /** Emotional response patterns */
  emotionalResponses: {
    /** Reaction to consecutive losses */
    lossReaction: 'aggressive' | 'conservative' | 'neutral'
    /** Reaction to big wins */
    winReaction: 'confident' | 'cautious' | 'neutral'
    /** Stress response under pressure */
    stressResponse: 'fight' | 'flight' | 'freeze'
  }
}

/**
 * Pre-defined personality archetypes
 */
export type PersonalityArchetype = 
  | 'conservative_scalper'      // Low risk, quick trades, major pairs only
  | 'aggressive_swing_trader'   // High risk, longer holds, diverse pairs
  | 'morning_momentum_trader'   // Active during London/NY open, momentum focused
  | 'evening_range_trader'      // Active during Asian session, range trading
  | 'news_reaction_trader'      // Reacts quickly to economic events
  | 'technical_pattern_trader'  // Focuses on chart patterns, methodical
  | 'carry_trade_specialist'    // Long-term positions, interest rate focused
  | 'volatility_hunter'         // Seeks high volatility, exotic pairs
  | 'risk_averse_conservative'  // Minimal risk, major pairs, slow growth
  | 'balanced_opportunist'      // Balanced approach, adapts to conditions

/**
 * Personality performance tracking
 */
export interface PersonalityPerformance {
  /** Total trades executed with this personality */
  totalTrades: number
  /** Win rate percentage */
  winRate: number
  /** Average profit per trade */
  avgProfitPerTrade: number
  /** Maximum drawdown experienced */
  maxDrawdown: number
  /** Sharpe ratio for this personality */
  sharpeRatio: number
  /** Days active */
  daysActive: number
  /** Last performance review date */
  lastReviewDate: Date
  /** Performance trend (improving, declining, stable) */
  trend: 'improving' | 'declining' | 'stable'
}

/**
 * Complete trading personality profile
 */
export interface TradingPersonality {
  /** Unique personality identifier */
  id: string
  /** Human-readable personality name */
  name: string
  /** Personality description */
  description: string
  /** Account ID this personality is assigned to */
  accountId: string
  /** Creation timestamp */
  createdAt: Date
  /** Last updated timestamp */
  updatedAt: Date
  /** Whether this personality is currently active */
  isActive: boolean
  
  /** Core personality traits */
  traits: PersonalityTraits
  /** Trading time preferences */
  timePreferences: TradingTimePreferences
  /** Currency pair preferences */
  pairPreferences: {
    primary: CurrencyPairPreference[]   // 2-3 primary pairs
    secondary: CurrencyPairPreference[] // 2-3 secondary pairs
  }
  /** Risk appetite configuration */
  riskAppetite: RiskAppetite
  /** Evolution and skill improvement settings */
  evolution: PersonalityEvolution
  /** Behavioral decision-making patterns */
  behavioralPatterns: BehavioralPatterns
  
  /** Personality metadata */
  metadata: {
    /** Personality archetype */
    archetype: PersonalityArchetype
    /** Compatibility with other personalities */
    compatibility: Record<string, number>
    /** Performance tracking */
    performance: PersonalityPerformance
  }
}

/**
 * Personality validation rules and constraints
 */
export interface PersonalityValidation {
  /** Minimum and maximum values for traits */
  traitBounds: Record<keyof PersonalityTraits, { min: number; max: number }>
  /** Required number of primary pairs */
  primaryPairCount: { min: number; max: number }
  /** Required number of secondary pairs */
  secondaryPairCount: { min: number; max: number }
  /** Risk limits */
  riskLimits: {
    minRiskPerTrade: number
    maxRiskPerTrade: number
    maxPortfolioRisk: number
  }
  /** Time preference constraints */
  timeConstraints: {
    minActiveHours: number
    maxActiveHours: number
  }
}

/**
 * Personality generation configuration
 */
export interface PersonalityGenerationConfig {
  /** Base archetype to generate from */
  archetype: PersonalityArchetype
  /** Randomization level (0-100) */
  randomization: number
  /** Constraints and limits */
  constraints: PersonalityValidation
  /** Evolution settings */
  evolutionEnabled: boolean
  /** Custom trait weights */
  traitWeights?: Partial<PersonalityTraits>
}

/**
 * Personality template for bulk generation
 */
export interface PersonalityTemplate {
  /** Template identifier */
  id: string
  /** Template name */
  name: string
  /** Template description */
  description: string
  /** Base configuration */
  config: PersonalityGenerationConfig
  /** Template tags for categorization */
  tags: string[]
  /** Creation date */
  createdAt: Date
}

/**
 * Personality analytics and monitoring
 */
export interface PersonalityAnalytics {
  /** Personality diversity metrics across accounts */
  diversityMetrics: {
    traitVariance: number
    timeOverlapReduction: number
    pairDistribution: number
    riskDistribution: number
  }
  /** Detection risk assessment */
  detectionRisk: {
    overallRisk: 'low' | 'medium' | 'high'
    riskFactors: string[]
    recommendations: string[]
  }
  /** Performance comparison across personalities */
  performanceComparison: Record<string, PersonalityPerformance>
}