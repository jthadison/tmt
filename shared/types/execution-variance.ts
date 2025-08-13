/**
 * Execution Variance Types
 * 
 * Type definitions for the execution variance engine that introduces
 * natural human-like imperfections into trade execution.
 */

export interface Signal {
  id: string
  symbol: string
  direction: 'long' | 'short'
  size: number
  entryPrice: number
  stopLoss: number
  takeProfit: number
  confidence: number
  generatedAt: Date
  accountId: string
  personalityId: string
}

export interface MarketConditions {
  volatility: number // ATR ratio
  spread: number
  liquidity: 'low' | 'medium' | 'high'
  session: 'asian' | 'london' | 'newyork' | 'overlap'
  isNewsTime: boolean
  gapSize?: number // For weekend gaps
  timestamp: Date
}

export interface ExecutionVariance {
  signalId: string
  accountId: string
  personalityId: string
  
  // Original Signal
  originalSignal: {
    symbol: string
    direction: 'long' | 'short'
    size: number
    entryPrice: number
    stopLoss: number
    takeProfit: number
    confidence: number
    generatedAt: Date
  }
  
  // Applied Variances
  variances: {
    entryTiming: {
      originalDelay: 0
      appliedDelay: number        // 1-30 seconds
      reason: string              // "personality_hesitation", "market_volatility"
    }
    positionSize: {
      originalSize: number
      adjustedSize: number        // Rounded to human-friendly
      roundingMethod: 'up' | 'down' | 'nearest'
      reason: string
    }
    stopLoss: {
      originalLevel: number
      adjustedLevel: number       // +/- 1-3 pips
      variance: number
      reason: string
    }
    takeProfit: {
      originalLevel: number
      adjustedLevel: number       // +/- 1-3 pips
      variance: number
      reason: string
    }
    execution: {
      microDelay: number          // 100-500ms
      skipSignal: boolean         // 5% chance
      skipReason?: string
    }
  }
  
  // Execution Results
  execution: {
    actualEntryTime: Date
    actualEntryPrice: number
    slippage: number
    executionLatency: number
    success: boolean
    errorReason?: string
  }
  
  appliedAt: Date
}

export interface VarianceProfile {
  personalityId: string
  
  // Timing Preferences
  timing: {
    baseDelay: number             // Base delay in seconds
    volatilityMultiplier: number  // Higher vol = more delay
    sessionPreferences: Record<string, number> // Session-specific delays
    marketOpenBehavior: 'eager' | 'cautious' | 'avoiding'
  }
  
  // Sizing Preferences
  sizing: {
    preferredIncrements: number[] // [0.01, 0.05, 0.1, 0.25, 0.5, 1.0]
    roundingBias: 'up' | 'down' | 'nearest' | 'psychological'
    maxDeviation: number          // Max deviation from suggested size
    accountSizeImpact: number     // How account size affects sizing
  }
  
  // Level Placement
  levels: {
    stopLossVariance: {
      min: number                 // Min pips variance
      max: number                 // Max pips variance
      bias: 'conservative' | 'aggressive' | 'neutral'
    }
    takeProfitVariance: {
      min: number
      max: number
      bias: 'greedy' | 'cautious' | 'neutral'
    }
    roundNumberAvoidance: number  // 0-1, how much to avoid round numbers
  }
  
  // Skip Behavior
  skipping: {
    baseSkipRate: number          // Base 5% skip rate
    skipTriggers: string[]        // Conditions that increase skip rate
    skipReasons: string[]         // Pool of human-like reasons
    consecutiveSkipLimit: number  // Max consecutive skips
  }
  
  // Weekend Behavior
  weekend: {
    tradeSundayOpen: boolean
    sundayRiskReduction: number   // Risk reduction factor
    gapTradingPreference: 'avoid' | 'fade' | 'follow'
    weekendNewsReaction: 'ignore' | 'cautious' | 'opportunistic'
  }
}

export interface VarianceMetrics {
  accountId: string
  period: {
    start: Date
    end: Date
  }
  
  // Timing Metrics
  timing: {
    averageDelay: number
    delayStandardDeviation: number
    delayDistribution: Record<string, number> // Histogram
  }
  
  // Sizing Metrics
  sizing: {
    roundingAccuracy: number      // How often sizes are rounded
    sizeDeviationAverage: number
    preferredSizeUsage: Record<string, number>
  }
  
  // Skip Metrics
  skipping: {
    actualSkipRate: number
    skipReasonDistribution: Record<string, number>
    consecutiveSkipPatterns: number[]
  }
  
  // Execution Quality
  execution: {
    averageSlippage: number
    executionSuccessRate: number
    latencyDistribution: Record<string, number>
  }
}

export interface TimingVarianceConfig {
  personalityId: string
  baseDelay: number
  volatilityThreshold: number
  sessionMultipliers: Record<string, number>
  newsProximityFactor: number
  consistencyLevel: number
}

export interface SizingVarianceConfig {
  personalityId: string
  preferredIncrements: number[]
  roundingBias: 'up' | 'down' | 'nearest' | 'psychological'
  maxDeviationPercent: number
  accountSizeThresholds: { small: number; medium: number; large: number }
}

export interface LevelVarianceConfig {
  personalityId: string
  stopLossRange: { min: number; max: number }
  takeProfitRange: { min: number; max: number }
  roundNumberAvoidance: number
  marketConditionImpact: number
}

export interface SkipConfig {
  personalityId: string
  baseSkipRate: number
  skipTriggers: {
    highVolatility: boolean
    lowConfidence: boolean
    consecutiveLosses: boolean
    marketOpen: boolean
    news: boolean
  }
  skipReasons: string[]
  maxConsecutiveSkips: number
}

export interface WeekendConfig {
  personalityId: string
  tradeSundayOpen: boolean
  sundayRiskMultiplier: number
  gapStrategy: 'avoid' | 'fade' | 'follow'
  newsReactionStyle: 'ignore' | 'cautious' | 'opportunistic'
}