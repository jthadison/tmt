/**
 * Risk Appetite Variance Engine
 * 
 * This service manages dynamic risk appetite adjustments for trading personalities,
 * implementing sophisticated position sizing that varies between 0.5%-2% per trade
 * based on personality traits, performance metrics, market conditions, and
 * psychological factors to simulate realistic human trader behavior.
 */

import {
  TradingPersonality,
  PersonalityTraits,
  RiskAppetite,
  PersonalityPerformance
} from '../types/personality'

/**
 * Market condition assessment for risk adjustment
 */
interface MarketConditions {
  volatility: 'very_low' | 'low' | 'medium' | 'high' | 'very_high'
  trend: 'strong_uptrend' | 'weak_uptrend' | 'sideways' | 'weak_downtrend' | 'strong_downtrend'
  liquidity: 'very_low' | 'low' | 'medium' | 'high' | 'very_high'
  newsImpact: 'none' | 'low' | 'medium' | 'high' | 'extreme'
  sessionType: 'asian' | 'london' | 'newyork' | 'overlap' | 'weekend'
  economicEvents: Array<{ importance: 'low' | 'medium' | 'high'; timeToEvent: number }>
}

/**
 * Performance-based risk adjustment factors
 */
interface PerformanceFactors {
  recentWinRate: number // Last 20 trades
  consecutiveWins: number
  consecutiveLosses: number
  currentDrawdown: number
  monthlyReturn: number
  sharpeRatio: number
  maxConsecutiveLosses: number
  profitFactor: number
  daysInDrawdown: number
}

/**
 * Psychological state affecting risk appetite
 */
interface PsychologicalState {
  confidence: number // 0-100, current confidence level
  stress: number // 0-100, current stress level
  fatigue: number // 0-100, mental fatigue level
  excitement: number // 0-100, market excitement level
  fear: number // 0-100, fear level
  overconfidence: number // 0-100, overconfidence risk
  revengeTrading: number // 0-100, revenge trading tendency
}

/**
 * Risk adjustment calculation result
 */
interface RiskAdjustmentResult {
  baseRisk: number // Base risk per trade (0.5-2.0%)
  adjustedRisk: number // Final adjusted risk
  variance: { min: number; max: number } // Risk variance range
  adjustmentFactors: {
    performance: number // -0.5 to +0.5
    market: number // -0.3 to +0.3
    psychological: number // -0.4 to +0.4
    time: number // -0.2 to +0.2
    pair: number // -0.1 to +0.1
  }
  reasoning: string[] // Human-readable explanations
  warnings: string[] // Risk warnings
  recommendations: string[]
}

/**
 * Dynamic risk sizing configuration
 */
interface RiskSizingConfig {
  baseRiskPercent: number
  maxRiskPercent: number
  minRiskPercent: number
  varianceRange: number
  adaptationSpeed: 'slow' | 'medium' | 'fast'
  safeguards: {
    maxDailyRisk: number
    maxWeeklyRisk: number
    maxMonthlyRisk: number
    maxDrawdownLimit: number
    consecutiveLossLimit: number
  }
}

/**
 * Risk Appetite Variance Engine
 */
export class RiskAppetiteEngine {
  
  private readonly defaultConfig: RiskSizingConfig = {
    baseRiskPercent: 1.0,
    maxRiskPercent: 2.0,
    minRiskPercent: 0.5,
    varianceRange: 0.3,
    adaptationSpeed: 'medium',
    safeguards: {
      maxDailyRisk: 5.0,
      maxWeeklyRisk: 10.0,
      maxMonthlyRisk: 20.0,
      maxDrawdownLimit: 15.0,
      consecutiveLossLimit: 5
    }
  }

  /**
   * Calculate dynamic risk appetite for a trade
   */
  public calculateRiskAppetite(
    personality: TradingPersonality,
    marketConditions: MarketConditions,
    performanceFactors: PerformanceFactors,
    psychologicalState: PsychologicalState,
    tradingPair: string,
    timeOfDay: number = new Date().getHours()
  ): RiskAdjustmentResult {
    
    // Start with personality base risk
    const baseRisk = personality.riskAppetite.baseRiskPerTrade
    
    // Calculate individual adjustment factors
    const performanceAdjustment = this.calculatePerformanceAdjustment(
      personality.traits, 
      performanceFactors,
      personality.riskAppetite
    )
    
    const marketAdjustment = this.calculateMarketConditionAdjustment(
      personality.traits,
      marketConditions
    )
    
    const psychologicalAdjustment = this.calculatePsychologicalAdjustment(
      personality.traits,
      psychologicalState
    )
    
    const timeAdjustment = this.calculateTimeBasedAdjustment(
      personality.timePreferences,
      timeOfDay,
      marketConditions.sessionType
    )
    
    const pairAdjustment = this.calculatePairSpecificAdjustment(
      personality.pairPreferences,
      tradingPair
    )

    // Combine all adjustments
    const totalAdjustment = 
      performanceAdjustment + 
      marketAdjustment + 
      psychologicalAdjustment + 
      timeAdjustment + 
      pairAdjustment

    // Apply adjustment with bounds
    let adjustedRisk = baseRisk + (baseRisk * totalAdjustment)
    adjustedRisk = Math.max(0.3, Math.min(2.5, adjustedRisk))
    
    // Calculate variance range
    const varianceMultiplier = this.calculateVarianceMultiplier(personality.traits, psychologicalState)
    const variance = {
      min: Math.max(0.3, adjustedRisk - (adjustedRisk * varianceMultiplier)),
      max: Math.min(2.5, adjustedRisk + (adjustedRisk * varianceMultiplier))
    }

    // Generate reasoning and recommendations
    const reasoning = this.generateReasoning(
      performanceAdjustment, marketAdjustment, psychologicalAdjustment, 
      timeAdjustment, pairAdjustment
    )
    
    const warnings = this.generateWarnings(
      adjustedRisk, performanceFactors, psychologicalState, marketConditions
    )
    
    const recommendations = this.generateRecommendations(
      personality.traits, performanceFactors, psychologicalState
    )

    return {
      baseRisk,
      adjustedRisk,
      variance,
      adjustmentFactors: {
        performance: performanceAdjustment,
        market: marketAdjustment,
        psychological: psychologicalAdjustment,
        time: timeAdjustment,
        pair: pairAdjustment
      },
      reasoning,
      warnings,
      recommendations
    }
  }

  /**
   * Calculate performance-based risk adjustment
   */
  private calculatePerformanceAdjustment(
    traits: PersonalityTraits,
    performance: PerformanceFactors,
    riskAppetite: RiskAppetite
  ): number {
    let adjustment = 0

    // Win rate adjustment
    if (performance.recentWinRate > 70) {
      adjustment += 0.15 * (traits.confidence / 100)
    } else if (performance.recentWinRate < 40) {
      adjustment -= 0.2 * (1 - traits.emotionality / 100)
    }

    // Consecutive wins/losses
    if (performance.consecutiveWins > 3) {
      const overconfidenceRisk = (performance.consecutiveWins - 3) * 0.05
      adjustment += Math.min(0.2, overconfidenceRisk * (1 - traits.discipline / 100))
    }
    
    if (performance.consecutiveLosses > 2) {
      const fearFactor = (performance.consecutiveLosses - 2) * 0.08
      adjustment -= Math.min(0.3, fearFactor * (traits.emotionality / 100))
    }

    // Drawdown adjustment
    const drawdownImpact = Math.abs(performance.currentDrawdown) / 20 // Normalize to 0-1
    adjustment -= drawdownImpact * 0.4 * (1 - traits.discipline / 100)

    // Monthly return adjustment
    if (performance.monthlyReturn > 10) {
      adjustment += 0.1 * (traits.riskTolerance / 100)
    } else if (performance.monthlyReturn < -5) {
      adjustment -= 0.15 * (traits.emotionality / 100)
    }

    // Apply performance scaling from risk appetite
    if (performance.consecutiveWins > 0) {
      adjustment *= riskAppetite.performanceScaling.winningStreak
    } else if (performance.consecutiveLosses > 0) {
      adjustment *= riskAppetite.performanceScaling.losingStreak
    }

    return Math.max(-0.5, Math.min(0.5, adjustment))
  }

  /**
   * Calculate market condition-based risk adjustment
   */
  private calculateMarketConditionAdjustment(
    traits: PersonalityTraits,
    market: MarketConditions
  ): number {
    let adjustment = 0

    // Volatility adjustment
    switch (market.volatility) {
      case 'very_low':
        adjustment -= 0.1 * (1 - traits.patience / 100)
        break
      case 'low':
        adjustment -= 0.05 * (1 - traits.patience / 100)
        break
      case 'high':
        adjustment += 0.1 * (traits.riskTolerance / 100) - 0.05 * (traits.emotionality / 100)
        break
      case 'very_high':
        adjustment += 0.15 * (traits.riskTolerance / 100) - 0.1 * (traits.emotionality / 100)
        break
    }

    // Liquidity adjustment
    if (market.liquidity === 'very_low' || market.liquidity === 'low') {
      adjustment -= 0.08 * (1 - traits.adaptability / 100)
    }

    // News impact adjustment
    switch (market.newsImpact) {
      case 'high':
        adjustment += 0.05 * (traits.adaptability / 100) - 0.1 * (traits.emotionality / 100)
        break
      case 'extreme':
        adjustment -= 0.15 * (1 - traits.discipline / 100)
        break
    }

    // Economic events adjustment
    const highImportanceEvents = market.economicEvents.filter(e => e.importance === 'high')
    if (highImportanceEvents.length > 0) {
      const timeToEvent = Math.min(...highImportanceEvents.map(e => e.timeToEvent))
      if (timeToEvent < 2) { // Within 2 hours
        adjustment -= 0.1 * (1 - traits.adaptability / 100)
      }
    }

    return Math.max(-0.3, Math.min(0.3, adjustment))
  }

  /**
   * Calculate psychological state-based risk adjustment
   */
  private calculatePsychologicalAdjustment(
    traits: PersonalityTraits,
    psychological: PsychologicalState
  ): number {
    let adjustment = 0

    // Confidence adjustment
    if (psychological.confidence > 80) {
      adjustment += 0.1 * (1 - traits.discipline / 100)
    } else if (psychological.confidence < 30) {
      adjustment -= 0.15
    }

    // Stress adjustment
    if (psychological.stress > 70) {
      adjustment -= 0.2 * (traits.emotionality / 100)
    }

    // Fatigue adjustment
    if (psychological.fatigue > 60) {
      adjustment -= 0.1 * (1 - traits.discipline / 100)
    }

    // Overconfidence adjustment
    if (psychological.overconfidence > 60) {
      adjustment -= 0.15 * (psychological.overconfidence / 100)
    }

    // Fear adjustment
    if (psychological.fear > 50) {
      adjustment -= 0.1 * (psychological.fear / 100)
    }

    // Revenge trading detection
    if (psychological.revengeTrading > 40) {
      adjustment -= 0.25 * (psychological.revengeTrading / 100)
    }

    return Math.max(-0.4, Math.min(0.4, adjustment))
  }

  /**
   * Calculate time-based risk adjustment
   */
  private calculateTimeBasedAdjustment(
    timePreferences: any,
    currentHour: number,
    sessionType: MarketConditions['sessionType']
  ): number {
    let adjustment = 0

    // Session activity alignment
    const sessionActivity = timePreferences.sessionActivity[sessionType] || 50
    if (sessionActivity > 80) {
      adjustment += 0.05 // More active during preferred session
    } else if (sessionActivity < 30) {
      adjustment -= 0.1 // Less active during non-preferred session
    }

    // Time of day fatigue (simplified model)
    const hoursFromStart = this.calculateHoursFromSessionStart(currentHour, sessionType)
    if (hoursFromStart > 6) {
      adjustment -= 0.05 * (hoursFromStart - 6) // Fatigue penalty
    }

    // Weekend adjustment
    if (sessionType === 'weekend') {
      adjustment -= 0.1 // Generally reduce risk on weekends
    }

    return Math.max(-0.2, Math.min(0.2, adjustment))
  }

  /**
   * Calculate pair-specific risk adjustment
   */
  private calculatePairSpecificAdjustment(
    pairPreferences: any,
    tradingPair: string
  ): number {
    // Find pair in preferences
    const primaryPair = pairPreferences.primary.find((p: any) => p.symbol === tradingPair)
    const secondaryPair = pairPreferences.secondary.find((p: any) => p.symbol === tradingPair)
    
    if (primaryPair) {
      // Primary pairs get slight risk increase based on strength
      return (primaryPair.strength - 70) / 1000 // -0.03 to +0.025
    } else if (secondaryPair) {
      // Secondary pairs get slight risk decrease
      return (secondaryPair.strength - 60) / 2000 // -0.015 to +0.0075
    } else {
      // Unknown pairs get risk decrease
      return -0.05
    }
  }

  /**
   * Calculate variance multiplier based on personality
   */
  private calculateVarianceMultiplier(
    traits: PersonalityTraits,
    psychological: PsychologicalState
  ): number {
    // Base variance from emotional volatility
    let variance = (traits.emotionality + psychological.stress) / 200 // 0 to 1
    
    // Discipline reduces variance
    variance *= (1 - traits.discipline / 200) // Reduce by up to 50%
    
    // Confidence affects variance (too much or too little increases it)
    const confidenceDeviation = Math.abs(traits.confidence - 50) / 50
    variance += confidenceDeviation * 0.1
    
    // Bound variance between 5% and 25%
    return Math.max(0.05, Math.min(0.25, variance))
  }

  /**
   * Generate human-readable reasoning for risk adjustment
   */
  private generateReasoning(
    performance: number,
    market: number,
    psychological: number,
    time: number,
    pair: number
  ): string[] {
    const reasoning: string[] = []

    if (Math.abs(performance) > 0.1) {
      reasoning.push(`Performance factor: ${performance > 0 ? 'increasing' : 'decreasing'} risk by ${Math.abs(performance * 100).toFixed(1)}%`)
    }

    if (Math.abs(market) > 0.05) {
      reasoning.push(`Market conditions: ${market > 0 ? 'supporting higher' : 'requiring lower'} risk exposure`)
    }

    if (Math.abs(psychological) > 0.05) {
      reasoning.push(`Psychological state: ${psychological > 0 ? 'boosting confidence' : 'increasing caution'}`)
    }

    if (Math.abs(time) > 0.03) {
      reasoning.push(`Time factors: ${time > 0 ? 'favorable' : 'unfavorable'} for current session`)
    }

    if (Math.abs(pair) > 0.02) {
      reasoning.push(`Pair preference: ${pair > 0 ? 'preferred' : 'less favored'} currency pair`)
    }

    return reasoning
  }

  /**
   * Generate risk warnings
   */
  private generateWarnings(
    adjustedRisk: number,
    performance: PerformanceFactors,
    psychological: PsychologicalState,
    market: MarketConditions
  ): string[] {
    const warnings: string[] = []

    if (adjustedRisk > 1.8) {
      warnings.push('High risk per trade - consider reducing position size')
    }

    if (performance.consecutiveLosses > 3) {
      warnings.push('Multiple consecutive losses detected - exercise extra caution')
    }

    if (performance.currentDrawdown < -10) {
      warnings.push('Significant drawdown - consider reducing risk until recovery')
    }

    if (psychological.revengeTrading > 50) {
      warnings.push('Revenge trading tendency detected - take a break')
    }

    if (psychological.overconfidence > 70) {
      warnings.push('Overconfidence detected - maintain disciplined risk management')
    }

    if (market.volatility === 'very_high' && market.newsImpact === 'extreme') {
      warnings.push('Extreme market conditions - consider avoiding new positions')
    }

    return warnings
  }

  /**
   * Generate recommendations
   */
  private generateRecommendations(
    traits: PersonalityTraits,
    performance: PerformanceFactors,
    psychological: PsychologicalState
  ): string[] {
    const recommendations: string[] = []

    if (performance.recentWinRate < 40 && traits.emotionality > 60) {
      recommendations.push('Consider taking a trading break to reset psychological state')
    }

    if (psychological.stress > 70) {
      recommendations.push('Implement stress management techniques before next trade')
    }

    if (performance.consecutiveLosses > 2 && traits.discipline < 60) {
      recommendations.push('Review and strictly follow risk management rules')
    }

    if (psychological.confidence < 30) {
      recommendations.push('Start with smaller positions to rebuild confidence')
    }

    if (performance.sharpeRatio < 0.5) {
      recommendations.push('Review strategy effectiveness and consider adjustments')
    }

    return recommendations
  }

  /**
   * Apply drawdown-based risk adjustments
   */
  public applyDrawdownAdjustments(
    currentRisk: number,
    drawdownPercent: number,
    riskAppetite: RiskAppetite
  ): number {
    const absDrawdown = Math.abs(drawdownPercent)
    
    let adjustment = 1.0
    
    if (absDrawdown > 20) {
      adjustment = riskAppetite.drawdownAdjustments.severe
    } else if (absDrawdown > 10) {
      adjustment = riskAppetite.drawdownAdjustments.moderate
    } else if (absDrawdown > 5) {
      adjustment = riskAppetite.drawdownAdjustments.mild
    }

    return currentRisk * adjustment
  }

  /**
   * Calculate portfolio-level risk constraints
   */
  public calculatePortfolioRiskConstraints(
    personality: TradingPersonality,
    currentPositions: Array<{ pair: string; riskPercent: number }>,
    proposedRisk: number
  ): { 
    allowTrade: boolean
    maxAllowedRisk: number
    portfolioRisk: number
    reasoning: string
  } {
    const currentPortfolioRisk = currentPositions.reduce((sum, pos) => sum + pos.riskPercent, 0)
    const totalRiskWithNewTrade = currentPortfolioRisk + proposedRisk
    
    const maxPortfolioRisk = personality.riskAppetite.maxPortfolioRisk
    
    if (totalRiskWithNewTrade <= maxPortfolioRisk) {
      return {
        allowTrade: true,
        maxAllowedRisk: proposedRisk,
        portfolioRisk: totalRiskWithNewTrade,
        reasoning: 'Trade approved - within portfolio risk limits'
      }
    } else {
      const maxAllowed = Math.max(0, maxPortfolioRisk - currentPortfolioRisk)
      return {
        allowTrade: maxAllowed > 0.3, // Minimum viable trade size
        maxAllowedRisk: maxAllowed,
        portfolioRisk: currentPortfolioRisk + maxAllowed,
        reasoning: maxAllowed > 0.3 
          ? `Risk reduced to maintain portfolio limits` 
          : 'Trade rejected - portfolio risk limit exceeded'
      }
    }
  }

  /**
   * Simulate risk appetite evolution over time
   */
  public simulateRiskEvolution(
    personality: TradingPersonality,
    timeFrameDays: number,
    averagePerformance: number
  ): Array<{ day: number; baseRisk: number; reason: string }> {
    const evolution: Array<{ day: number; baseRisk: number; reason: string }> = []
    let currentRisk = personality.riskAppetite.baseRiskPerTrade
    
    // Simulate gradual risk evolution
    const evolutionRate = personality.evolution.improvementRate / 100 // Convert to daily rate
    
    for (let day = 1; day <= timeFrameDays; day++) {
      let dailyChange = 0
      let reason = 'No change'
      
      // Experience-based evolution
      if (day % 30 === 0) { // Monthly review
        if (averagePerformance > 5) {
          dailyChange = evolutionRate * 0.1 // Increase risk with good performance
          reason = 'Monthly review: Good performance, increasing risk tolerance'
        } else if (averagePerformance < -5) {
          dailyChange = -evolutionRate * 0.15 // Decrease risk with poor performance
          reason = 'Monthly review: Poor performance, reducing risk tolerance'
        }
      }
      
      // Trait-based evolution
      if (personality.traits.adaptability > 70 && day % 90 === 0) {
        dailyChange += evolutionRate * 0.05
        reason += ' | High adaptability driving gradual risk increase'
      }
      
      currentRisk = Math.max(0.5, Math.min(2.0, currentRisk + dailyChange))
      
      if (dailyChange !== 0 || day % 30 === 0) {
        evolution.push({ day, baseRisk: currentRisk, reason })
      }
    }
    
    return evolution
  }

  /**
   * Utility function to calculate hours from session start
   */
  private calculateHoursFromSessionStart(currentHour: number, sessionType: MarketConditions['sessionType']): number {
    const sessionStarts = {
      asian: 21,
      london: 7,
      newyork: 12,
      overlap: 13,
      weekend: 0
    }
    
    const startHour = sessionStarts[sessionType]
    let diff = currentHour - startHour
    if (diff < 0) diff += 24
    
    return diff
  }
}

/**
 * Default risk appetite engine instance
 */
export const defaultRiskAppetiteEngine = new RiskAppetiteEngine()

/**
 * Utility functions for risk appetite management
 */
export const RiskAppetiteUtils = {
  /**
   * Validate risk appetite configuration
   */
  validateRiskAppetite(riskAppetite: RiskAppetite): { isValid: boolean; errors: string[] } {
    const errors: string[] = []
    
    if (riskAppetite.baseRiskPerTrade < 0.3 || riskAppetite.baseRiskPerTrade > 2.5) {
      errors.push('Base risk per trade must be between 0.3% and 2.5%')
    }
    
    if (riskAppetite.riskVariance.min >= riskAppetite.riskVariance.max) {
      errors.push('Risk variance minimum must be less than maximum')
    }
    
    if (riskAppetite.maxPortfolioRisk > 25) {
      errors.push('Maximum portfolio risk should not exceed 25%')
    }
    
    return { isValid: errors.length === 0, errors }
  },

  /**
   * Calculate Kelly criterion optimal position size
   */
  calculateKellyOptimal(winRate: number, avgWin: number, avgLoss: number): number {
    if (winRate <= 0 || winRate >= 100 || avgWin <= 0 || avgLoss <= 0) {
      return 0.01 // 1% fallback
    }
    
    const winProb = winRate / 100
    const lossProb = 1 - winProb
    const winLossRatio = avgWin / avgLoss
    
    const kellyCriterion = (winProb * winLossRatio - lossProb) / winLossRatio
    
    // Apply Kelly fraction (typically 25-50% of full Kelly)
    return Math.max(0.005, Math.min(0.02, kellyCriterion * 0.25))
  },

  /**
   * Analyze risk appetite trends
   */
  analyzeRiskTrends(
    riskHistory: Array<{ date: Date; risk: number; performance: number }>
  ): {
    trend: 'increasing' | 'decreasing' | 'stable'
    volatility: 'low' | 'medium' | 'high'
    correlation: number // Risk vs performance correlation
  } {
    if (riskHistory.length < 10) {
      return { trend: 'stable', volatility: 'low', correlation: 0 }
    }
    
    // Calculate trend
    const recent = riskHistory.slice(-10)
    const early = riskHistory.slice(0, 10)
    const recentAvg = recent.reduce((sum, r) => sum + r.risk, 0) / recent.length
    const earlyAvg = early.reduce((sum, r) => sum + r.risk, 0) / early.length
    
    let trend: 'increasing' | 'decreasing' | 'stable'
    if (recentAvg > earlyAvg + 0.1) trend = 'increasing'
    else if (recentAvg < earlyAvg - 0.1) trend = 'decreasing'
    else trend = 'stable'
    
    // Calculate volatility
    const riskValues = riskHistory.map(r => r.risk)
    const avgRisk = riskValues.reduce((sum, r) => sum + r, 0) / riskValues.length
    const variance = riskValues.reduce((sum, r) => sum + Math.pow(r - avgRisk, 2), 0) / riskValues.length
    const stdDev = Math.sqrt(variance)
    
    let volatility: 'low' | 'medium' | 'high'
    if (stdDev < 0.1) volatility = 'low'
    else if (stdDev < 0.2) volatility = 'medium'
    else volatility = 'high'
    
    // Calculate correlation between risk and performance
    const correlation = this.calculateCorrelation(
      riskHistory.map(r => r.risk),
      riskHistory.map(r => r.performance)
    )
    
    return { trend, volatility, correlation }
  },

  /**
   * Calculate correlation coefficient
   */
  calculateCorrelation(x: number[], y: number[]): number {
    if (x.length !== y.length || x.length === 0) return 0
    
    const n = x.length
    const sumX = x.reduce((sum, val) => sum + val, 0)
    const sumY = y.reduce((sum, val) => sum + val, 0)
    const sumXY = x.reduce((sum, val, i) => sum + val * y[i], 0)
    const sumX2 = x.reduce((sum, val) => sum + val * val, 0)
    const sumY2 = y.reduce((sum, val) => sum + val * val, 0)
    
    const numerator = n * sumXY - sumX * sumY
    const denominator = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY))
    
    return denominator === 0 ? 0 : numerator / denominator
  }
}