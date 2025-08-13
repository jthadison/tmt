/**
 * Main Execution Variance Engine
 * 
 * Orchestrates all variance engines to apply human-like imperfections
 * to algorithmic trading signals before execution.
 */

import {
  Signal,
  MarketConditions,
  ExecutionVariance,
  VarianceProfile,
  VarianceMetrics
} from '../types/execution-variance'
import { TradingPersonality } from '../types/personality'

import { TimingVarianceEngine } from './timing-variance-engine'
import { SizingVarianceEngine } from './sizing-variance-engine'
import { LevelVarianceEngine } from './level-variance-engine'
import { SignalSkipEngine } from './signal-skip-engine'
import { MicroDelayEngine, OrderAction } from './micro-delay-engine'
import { WeekendBehaviorEngine } from './weekend-behavior-engine'

export class ExecutionVarianceEngine {
  private timingEngine = new TimingVarianceEngine()
  private sizingEngine = new SizingVarianceEngine()
  private levelEngine = new LevelVarianceEngine()
  private skipEngine = new SignalSkipEngine()
  private delayEngine = new MicroDelayEngine()
  private weekendEngine = new WeekendBehaviorEngine()
  
  private varianceHistory = new Map<string, ExecutionVariance[]>()
  private profiles = new Map<string, VarianceProfile>()
  
  /**
   * Initialize variance engine with personality
   */
  public async initializePersonality(personality: TradingPersonality): Promise<void> {
    // Register personality with all sub-engines
    this.timingEngine.registerPersonality(personality)
    this.sizingEngine.registerPersonality(personality)
    this.levelEngine.registerPersonality(personality)
    this.skipEngine.registerPersonality(personality)
    this.delayEngine.registerPersonality(personality)
    this.weekendEngine.registerPersonality(personality)
    
    // Create variance profile
    const profile = this.createVarianceProfile(personality)
    this.profiles.set(personality.id, profile)
    
    // Initialize history
    this.varianceHistory.set(personality.id, [])
  }
  
  /**
   * Apply complete variance to a trading signal
   */
  public async applyVariance(
    signal: Signal,
    marketConditions: MarketConditions,
    personality: TradingPersonality,
    accountBalance: number = 10000
  ): Promise<ExecutionVariance | null> {
    // First check if signal should be skipped
    const executionResult = this.skipEngine.shouldSkipSignal(signal, marketConditions, personality)
    
    if (executionResult.skipSignal) {
      // Signal skipped - return null to indicate no execution
      return null
    }
    
    // Apply all variance components
    const [
      entryTiming,
      positionSize,
      stopLoss,
      takeProfit
    ] = await Promise.all([
      this.timingEngine.applyTimingVariance(signal, marketConditions, personality),
      this.sizingEngine.applyPositionSizeVariance(signal, personality, accountBalance),
      this.levelEngine.applyStopLossVariance(signal, marketConditions, personality),
      this.levelEngine.applyTakeProfitVariance(signal, marketConditions, personality)
    ])
    
    // Create execution variance record
    const variance: ExecutionVariance = {
      signalId: signal.id,
      accountId: signal.accountId,
      personalityId: signal.personalityId,
      originalSignal: {
        symbol: signal.symbol,
        direction: signal.direction,
        size: signal.size,
        entryPrice: signal.entryPrice,
        stopLoss: signal.stopLoss,
        takeProfit: signal.takeProfit,
        confidence: signal.confidence,
        generatedAt: signal.generatedAt
      },
      variances: {
        entryTiming,
        positionSize,
        stopLoss,
        takeProfit,
        execution: executionResult
      },
      execution: {
        actualEntryTime: new Date(Date.now() + entryTiming.appliedDelay * 1000),
        actualEntryPrice: signal.entryPrice, // Would be updated after actual execution
        slippage: 0, // Would be calculated after execution
        executionLatency: executionResult.microDelay,
        success: false, // Would be updated after execution attempt
        errorReason: undefined
      },
      appliedAt: new Date()
    }
    
    // Store variance record
    this.storeVarianceRecord(personality.id, variance)
    
    return variance
  }
  
  /**
   * Apply micro delay to order modification
   */
  public async applyOrderDelay(
    action: OrderAction,
    personalityId: string,
    marketConditions?: MarketConditions
  ): Promise<number> {
    const delayResult = await this.delayEngine.applyDelay(
      action,
      personalityId,
      marketConditions
    )
    
    return delayResult.delay
  }
  
  /**
   * Check weekend behavior for personality
   */
  public shouldTradeWeekend(
    personalityId: string,
    gapSize: number = 0,
    hasWeekendNews: boolean = false
  ): boolean {
    return this.weekendEngine.shouldTradeSundayOpen(personalityId, gapSize, hasWeekendNews)
  }
  
  /**
   * Create variance profile from personality
   */
  private createVarianceProfile(personality: TradingPersonality): VarianceProfile {
    return {
      personalityId: personality.id,
      timing: {
        baseDelay: 2 + (personality.traits.patience / 100) * 6,
        volatilityMultiplier: 1.0 + (personality.traits.emotionality / 100) * 0.8,
        sessionPreferences: {
          asian: personality.timePreferences.sessionActivity.asian > 70 ? 0.8 : 1.2,
          london: personality.timePreferences.sessionActivity.london > 70 ? 0.9 : 1.1,
          newyork: personality.timePreferences.sessionActivity.newyork > 70 ? 0.85 : 1.15,
          overlap: personality.timePreferences.sessionActivity.overlap > 80 ? 0.7 : 1.3
        },
        marketOpenBehavior: personality.traits.adaptability > 70 ? 'eager' : 
                           personality.traits.emotionality > 60 ? 'cautious' : 'avoiding'
      },
      sizing: {
        preferredIncrements: [0.01, 0.05, 0.1, 0.25, 0.5, 1.0],
        roundingBias: personality.traits.confidence > 75 ? 'up' :
                     personality.traits.emotionality > 60 ? 'down' : 'nearest',
        maxDeviation: 0.15 + (personality.traits.adaptability / 100) * 0.15,
        accountSizeImpact: personality.traits.discipline / 100
      },
      levels: {
        stopLossVariance: {
          min: Math.max(0.5, 1 - personality.traits.discipline / 100 * 0.5),
          max: Math.min(5, 3 + personality.traits.emotionality / 100 * 1.5),
          bias: personality.traits.riskTolerance < 40 ? 'conservative' :
                personality.traits.riskTolerance > 70 ? 'aggressive' : 'neutral'
        },
        takeProfitVariance: {
          min: Math.max(0.3, 1 - personality.traits.patience / 100 * 0.8),
          max: Math.min(4, 3 + personality.traits.confidence / 100 * 1.2),
          bias: personality.traits.patience > 80 ? 'cautious' :
                personality.traits.confidence > 70 ? 'greedy' : 'neutral'
        },
        roundNumberAvoidance: 0.3 + (personality.traits.discipline / 100) * 0.5 + 
                             (personality.traits.adaptability / 100) * 0.2
      },
      skipping: {
        baseSkipRate: Math.max(0.02, Math.min(0.12, 
          0.05 - (personality.traits.discipline / 100) * 0.02 + 
          (personality.traits.emotionality / 100) * 0.03
        )),
        skipTriggers: [
          personality.traits.emotionality > 50 ? 'high_volatility' : '',
          personality.traits.confidence < 70 ? 'low_confidence' : '',
          personality.traits.emotionality > 60 ? 'consecutive_losses' : ''
        ].filter(t => t !== ''),
        skipReasons: [
          'second_guessing_signal', 'waiting_for_confirmation', 'market_uncertainty',
          personality.traits.emotionality > 60 ? 'low_confidence_period' : '',
          personality.traits.discipline > 70 ? 'risk_management_pause' : '',
          personality.traits.patience > 70 ? 'waiting_for_better_entry' : ''
        ].filter(r => r !== ''),
        consecutiveSkipLimit: personality.traits.discipline > 80 ? 2 : 
                             personality.traits.patience > 80 ? 4 : 3
      },
      weekend: {
        tradeSundayOpen: Math.random() < (0.3 + 
          (personality.traits.riskTolerance / 100) * 0.4 + 
          (personality.traits.adaptability / 100) * 0.3),
        sundayRiskReduction: personality.traits.discipline > 70 ? 
          0.5 + Math.random() * 0.3 : 0.3 + Math.random() * 1.0,
        gapTradingPreference: personality.traits.confidence > 70 && personality.traits.riskTolerance > 60 ? 'follow' :
                             personality.traits.adaptability > 70 && personality.traits.confidence > 60 ? 'fade' : 'avoid',
        weekendNewsReaction: personality.traits.patience > 80 && personality.traits.emotionality < 40 ? 'ignore' :
                           personality.traits.adaptability > 70 && personality.traits.emotionality > 50 ? 'opportunistic' : 'cautious'
      }
    }
  }
  
  /**
   * Store variance record in history
   */
  private storeVarianceRecord(personalityId: string, variance: ExecutionVariance): void {
    const history = this.varianceHistory.get(personalityId) || []
    history.push(variance)
    
    // Keep only last 1000 records
    if (history.length > 1000) {
      history.shift()
    }
    
    this.varianceHistory.set(personalityId, history)
  }
  
  /**
   * Calculate variance metrics for a personality
   */
  public calculateVarianceMetrics(
    personalityId: string,
    startDate: Date,
    endDate: Date
  ): VarianceMetrics {
    const history = this.varianceHistory.get(personalityId) || []
    const periodHistory = history.filter(v => 
      v.appliedAt >= startDate && v.appliedAt <= endDate
    )
    
    if (periodHistory.length === 0) {
      // Return empty metrics
      return {
        accountId: '',
        period: { start: startDate, end: endDate },
        timing: {
          averageDelay: 0,
          delayStandardDeviation: 0,
          delayDistribution: {}
        },
        sizing: {
          roundingAccuracy: 0,
          sizeDeviationAverage: 0,
          preferredSizeUsage: {}
        },
        skipping: {
          actualSkipRate: 0,
          skipReasonDistribution: {},
          consecutiveSkipPatterns: []
        },
        execution: {
          averageSlippage: 0,
          executionSuccessRate: 0,
          latencyDistribution: {}
        }
      }
    }
    
    // Calculate timing metrics
    const delays = periodHistory.map(v => v.variances.entryTiming.appliedDelay)
    const averageDelay = delays.reduce((sum, d) => sum + d, 0) / delays.length
    const delayVariance = delays.reduce((sum, d) => sum + Math.pow(d - averageDelay, 2), 0) / delays.length
    const delayStandardDeviation = Math.sqrt(delayVariance)
    
    // Calculate sizing metrics
    const sizeDeviations = periodHistory.map(v => 
      Math.abs(v.variances.positionSize.adjustedSize - v.variances.positionSize.originalSize) / 
      v.variances.positionSize.originalSize
    )
    const sizeDeviationAverage = sizeDeviations.reduce((sum, d) => sum + d, 0) / sizeDeviations.length
    
    // Calculate skip metrics (from skip engine)
    const skipStats = this.skipEngine.getSkipStats(personalityId)
    
    // Calculate execution metrics
    const successfulExecutions = periodHistory.filter(v => v.execution.success).length
    const executionSuccessRate = successfulExecutions / periodHistory.length
    const slippages = periodHistory.map(v => v.execution.slippage)
    const averageSlippage = slippages.reduce((sum, s) => sum + s, 0) / slippages.length
    
    return {
      accountId: periodHistory[0]?.accountId || '',
      period: { start: startDate, end: endDate },
      timing: {
        averageDelay,
        delayStandardDeviation,
        delayDistribution: this.calculateDelayDistribution(delays)
      },
      sizing: {
        roundingAccuracy: this.calculateRoundingAccuracy(periodHistory),
        sizeDeviationAverage,
        preferredSizeUsage: this.calculateSizeUsage(periodHistory)
      },
      skipping: {
        actualSkipRate: skipStats.actualSkipRate,
        skipReasonDistribution: skipStats.reasonDistribution,
        consecutiveSkipPatterns: []
      },
      execution: {
        averageSlippage,
        executionSuccessRate,
        latencyDistribution: this.calculateLatencyDistribution(periodHistory)
      }
    }
  }
  
  /**
   * Calculate delay distribution histogram
   */
  private calculateDelayDistribution(delays: number[]): Record<string, number> {
    const buckets = { '1-5s': 0, '6-10s': 0, '11-20s': 0, '21-30s': 0 }
    
    delays.forEach(delay => {
      if (delay <= 5) buckets['1-5s']++
      else if (delay <= 10) buckets['6-10s']++
      else if (delay <= 20) buckets['11-20s']++
      else buckets['21-30s']++
    })
    
    return buckets
  }
  
  /**
   * Calculate rounding accuracy
   */
  private calculateRoundingAccuracy(history: ExecutionVariance[]): number {
    const roundedCount = history.filter(v => 
      v.variances.positionSize.adjustedSize !== v.variances.positionSize.originalSize
    ).length
    
    return roundedCount / history.length
  }
  
  /**
   * Calculate size usage distribution
   */
  private calculateSizeUsage(history: ExecutionVariance[]): Record<string, number> {
    const usage: Record<string, number> = {}
    
    history.forEach(v => {
      const size = v.variances.positionSize.adjustedSize.toString()
      usage[size] = (usage[size] || 0) + 1
    })
    
    return usage
  }
  
  /**
   * Calculate latency distribution
   */
  private calculateLatencyDistribution(history: ExecutionVariance[]): Record<string, number> {
    const buckets = { '100-200ms': 0, '201-300ms': 0, '301-400ms': 0, '401-500ms': 0 }
    
    history.forEach(v => {
      const latency = v.execution.executionLatency
      if (latency <= 200) buckets['100-200ms']++
      else if (latency <= 300) buckets['201-300ms']++
      else if (latency <= 400) buckets['301-400ms']++
      else buckets['401-500ms']++
    })
    
    return buckets
  }
  
  /**
   * Get variance profile for personality
   */
  public getVarianceProfile(personalityId: string): VarianceProfile | undefined {
    return this.profiles.get(personalityId)
  }
  
  /**
   * Validate variance engine performance
   */
  public validateVarianceEngine(personalityId: string): {
    isValid: boolean
    issues: string[]
    recommendations: string[]
  } {
    const issues: string[] = []
    const recommendations: string[] = []
    
    // Validate skip rate
    const skipValidation = this.skipEngine.validateSkipRate(personalityId)
    if (!skipValidation.isValid) {
      issues.push(`Skip rate out of bounds: ${skipValidation.actualRate} vs target ${skipValidation.targetRate}`)
    }
    
    // Validate delay performance
    const delayValidation = this.delayEngine.validateDelayPerformance(personalityId)
    if (!delayValidation.isValid) {
      issues.push(...delayValidation.issues)
    }
    
    // Validate weekend behavior
    const weekendValidation = this.weekendEngine.validateWeekendBehavior(personalityId)
    if (!weekendValidation.isValid) {
      issues.push(...weekendValidation.issues)
    }
    
    // Add recommendations based on issues
    if (issues.length > 0) {
      recommendations.push('Consider re-initializing personality configuration')
      recommendations.push('Monitor variance patterns for detection risk')
    }
    
    return {
      isValid: issues.length === 0,
      issues,
      recommendations
    }
  }
  
  /**
   * Reset all variance engines for a personality
   */
  public resetPersonality(personalityId: string): void {
    this.timingEngine.resetPersonality(personalityId)
    this.sizingEngine.resetPersonality(personalityId)
    this.levelEngine.resetPersonality(personalityId)
    this.skipEngine.resetPersonality(personalityId)
    this.delayEngine.resetPersonality(personalityId)
    this.weekendEngine.resetPersonality(personalityId)
    
    this.profiles.delete(personalityId)
    this.varianceHistory.delete(personalityId)
  }
  
  /**
   * Get comprehensive stats for all variance engines
   */
  public getComprehensiveStats(personalityId: string): {
    timing: ReturnType<typeof this.timingEngine.getTimingStats>
    sizing: ReturnType<typeof this.sizingEngine.getSizingStats>
    levels: ReturnType<typeof this.levelEngine.getLevelStats>
    skipping: ReturnType<typeof this.skipEngine.getSkipStats>
    delays: ReturnType<typeof this.delayEngine.getDelayStats>
    weekend: ReturnType<typeof this.weekendEngine.getWeekendStats>
  } {
    return {
      timing: this.timingEngine.getTimingStats(personalityId),
      sizing: this.sizingEngine.getSizingStats(personalityId),
      levels: this.levelEngine.getLevelStats(personalityId),
      skipping: this.skipEngine.getSkipStats(personalityId),
      delays: this.delayEngine.getDelayStats(personalityId),
      weekend: this.weekendEngine.getWeekendStats(personalityId)
    }
  }
}