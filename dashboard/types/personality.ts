/**
 * Trading Personality Types and Interfaces
 */

export enum PersonalityArchetype {
  AGGRESSIVE = 'aggressive',
  CONSERVATIVE = 'conservative',
  BALANCED = 'balanced',
  SCALPER = 'scalper',
  SWING = 'swing',
  MOMENTUM = 'momentum',
  CONTRARIAN = 'contrarian'
}

export interface TradingPersonality {
  id: string
  name: string
  archetype?: PersonalityArchetype
  description: string
  accountId?: string
  
  // Personality traits
  traits: {
    riskTolerance: number // 0-100 scale
    patience: number // 0-100 scale
    confidence: number // 0-100 scale
    emotionality: number // 0-100 scale
    discipline: number // 0-100 scale
    adaptability: number // 0-100 scale
  }
  
  // Time preferences
  timePreferences?: {
    preferredSessions: string[]
    activeHours: { start: number; end: number; timezone: string }
    sessionActivity: { asian: number; london: number; newyork: number; overlap: number }
    weekendActivity: number
    holidayActivity: number
  }
  
  // Pair preferences
  pairPreferences?: {
    primary: Array<{
      symbol: string
      strength: number
      category: string
      frequency: number
      maxPositionSize: number
    }>
    secondary: Array<{
      symbol: string
      strength: number
      category: string
      frequency: number
      maxPositionSize: number
    }>
  }
  
  // Risk appetite
  riskAppetite?: {
    baseRiskPerTrade: number
    riskVariance: { min: number; max: number }
    maxPortfolioRisk: number
    performanceScaling: { winningStreak: number; losingStreak: number }
    drawdownAdjustments: { mild: number; moderate: number; severe: number }
  }
  
  // Evolution settings
  evolution?: {
    [key: string]: any
  }
  
  // Performance metrics
  metrics?: {
    winRate: number
    profitFactor: number
    averageWin: number
    averageLoss: number
    sharpeRatio: number
    maxDrawdown: number
    totalTrades: number
    totalProfit: number
  }
  
  // Metadata
  metadata?: {
    archetype: string
    performance: {
      winRate: number
      totalTrades: number
      avgProfitPerTrade: number
      trend: string
      [key: string]: any
    }
    [key: string]: any
  }
  
  // Status
  isActive: boolean
  lastUsed?: Date
  createdAt: Date
  updatedAt: Date
  
  // Additional properties for flexibility
  [key: string]: any
}

export interface PersonalityTemplate {
  archetype: PersonalityArchetype
  name: string
  description: string
  defaultTraits: {
    riskTolerance: number
    patience: number
    confidence: number
    emotionality: number
    discipline: number
    adaptability: number
  }
  recommendedRiskTolerance: number
  typicalParameters: {
    maxPositionSize: number
    maxDrawdown: number
    profitTarget: number
    stopLoss: number
  }
}

export interface PersonalityPerformance {
  personalityId: string
  period: string // e.g., 'daily', 'weekly', 'monthly'
  startDate: Date
  endDate: Date
  
  trades: {
    total: number
    winning: number
    losing: number
    breakeven: number
  }
  
  returns: {
    gross: number
    net: number
    percentage: number
  }
  
  risk: {
    maxDrawdown: number
    volatility: number
    sharpeRatio: number
    sortinoRatio: number
  }
  
  efficiency: {
    avgTradeTime: number // in minutes
    tradesPerDay: number
    successRate: number
  }
}

export interface PersonalityConfig {
  // Strategy selection weights
  strategyWeights: {
    [strategyName: string]: number // 0-1 weighting
  }
  
  // Risk management overrides
  riskOverrides: {
    maxDailyLoss?: number
    maxPositions?: number
    correlationLimit?: number
  }
  
  // Behavioral modifications
  behaviorMods: {
    newsReaction: 'ignore' | 'cautious' | 'aggressive'
    trendFollowing: number // 0-1 scale
    contrarian: number // 0-1 scale
    meanReversion: number // 0-1 scale
  }
  
  // Learning settings
  learning: {
    enabled: boolean
    adaptationRate: number // 0-1 scale
    memoryDecay: number // 0-1 scale
    performanceThreshold: number // Minimum performance to adapt
  }
}

export type PersonalityMetric = 
  | 'winRate'
  | 'profitFactor' 
  | 'sharpeRatio'
  | 'maxDrawdown'
  | 'averageWin'
  | 'averageLoss'
  | 'totalTrades'
  | 'totalReturn'

export interface PersonalityComparison {
  personalities: TradingPersonality[]
  metrics: PersonalityMetric[]
  period: {
    start: Date
    end: Date
  }
  data: {
    [personalityId: string]: {
      [metric in PersonalityMetric]?: number
    }
  }
}