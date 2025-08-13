/**
 * Personality Evolution Engine
 * 
 * This service simulates realistic personality evolution for trading accounts,
 * modeling how trader behavior, skills, and risk appetite change over time
 * based on experience, performance, market exposure, and psychological factors.
 * This creates believable growth patterns that help avoid AI detection.
 */

import {
  TradingPersonality,
  PersonalityTraits,
  PersonalityEvolution,
  PersonalityPerformance,
  RiskAppetite,
  TradingTimePreferences,
  BehavioralPatterns
} from '../types/personality'

/**
 * Experience milestone triggers for evolution
 */
interface ExperienceMilestone {
  tradesRequired: number
  timeRequired: number // days
  profitRequired: number // percentage
  description: string
  traitChanges: Partial<PersonalityTraits>
  skillImprovements: string[]
  newCapabilities: string[]
}

/**
 * Market cycle experience tracking
 */
interface MarketCycleExperience {
  bullMarket: { trades: number; exposure: number; performance: number }
  bearMarket: { trades: number; exposure: number; performance: number }
  sidewaysMarket: { trades: number; exposure: number; performance: number }
  volatileMarket: { trades: number; exposure: number; performance: number }
  newsEvents: { count: number; successRate: number }
  drawdownRecoveries: { count: number; averageTime: number }
}

/**
 * Skill development tracking
 */
interface SkillDevelopment {
  technicalAnalysis: number // 0-100
  fundamentalAnalysis: number // 0-100
  riskManagement: number // 0-100
  emotionalControl: number // 0-100
  marketTiming: number // 0-100
  positionSizing: number // 0-100
  pairSelection: number // 0-100
  newsTrading: number // 0-100
  trendFollowing: number // 0-100
  counterTrend: number // 0-100
}

/**
 * Evolution event with detailed context
 */
interface EvolutionEvent {
  id: string
  timestamp: Date
  eventType: 'milestone_reached' | 'skill_improvement' | 'trait_evolution' | 'crisis_adaptation' | 'market_cycle_completion'
  trigger: string
  previousState: Partial<TradingPersonality>
  newState: Partial<TradingPersonality>
  impactDescription: string
  evolutionScore: number // 0-100, significance of change
  reversible: boolean
}

/**
 * Evolution configuration parameters
 */
interface EvolutionConfig {
  speed: 'very_slow' | 'slow' | 'medium' | 'fast' | 'very_fast'
  realism: 'low' | 'medium' | 'high' // How realistic evolution patterns should be
  volatility: 'stable' | 'moderate' | 'dynamic' // How much personality can change
  crisisImpact: 'minimal' | 'moderate' | 'significant' // Response to major losses
  plateauProbability: number // 0-1, chance of skill plateaus
  regressionProbability: number // 0-1, chance of temporary skill regression
}

/**
 * Evolution prediction result
 */
interface EvolutionPrediction {
  timeframe: string
  expectedChanges: Array<{
    trait: keyof PersonalityTraits | 'skill' | 'risk_appetite'
    direction: 'increase' | 'decrease' | 'stable'
    magnitude: 'small' | 'medium' | 'large'
    probability: number
    reasoning: string
  }>
  milestones: Array<{
    description: string
    estimatedDate: Date
    requirements: string[]
  }>
  risks: Array<{
    risk: string
    probability: number
    mitigation: string
  }>
}

/**
 * Personality Evolution Engine
 */
export class PersonalityEvolutionEngine {
  
  private readonly experienceMilestones: ExperienceMilestone[] = [
    {
      tradesRequired: 50,
      timeRequired: 30,
      profitRequired: 5,
      description: 'Beginner milestone - Basic trading consistency',
      traitChanges: {
        confidence: 5,
        discipline: 8,
        emotionality: -3
      },
      skillImprovements: ['Basic risk management', 'Platform familiarity'],
      newCapabilities: ['Stop loss consistency', 'Basic position sizing']
    },
    {
      tradesRequired: 150,
      timeRequired: 90,
      profitRequired: 10,
      description: 'Novice milestone - Pattern recognition development',
      traitChanges: {
        confidence: 8,
        patience: 10,
        adaptability: 5,
        emotionality: -5
      },
      skillImprovements: ['Technical analysis basics', 'Market timing improvement'],
      newCapabilities: ['Trend identification', 'Support/resistance recognition']
    },
    {
      tradesRequired: 300,
      timeRequired: 180,
      profitRequired: 20,
      description: 'Intermediate milestone - Strategy refinement',
      traitChanges: {
        discipline: 10,
        adaptability: 8,
        riskTolerance: 5,
        emotionality: -8
      },
      skillImprovements: ['Advanced technical analysis', 'Multiple timeframe analysis'],
      newCapabilities: ['Strategy backtesting', 'Market correlation understanding']
    },
    {
      tradesRequired: 500,
      timeRequired: 300,
      profitRequired: 35,
      description: 'Advanced milestone - Risk management mastery',
      traitChanges: {
        discipline: 15,
        confidence: 10,
        adaptability: 12,
        emotionality: -10
      },
      skillImprovements: ['Portfolio management', 'Advanced risk assessment'],
      newCapabilities: ['Multi-pair trading', 'Correlation-based sizing']
    },
    {
      tradesRequired: 1000,
      timeRequired: 540,
      profitRequired: 60,
      description: 'Expert milestone - Market intuition development',
      traitChanges: {
        confidence: 15,
        adaptability: 15,
        patience: 12,
        riskTolerance: 8,
        emotionality: -12
      },
      skillImprovements: ['Market psychology understanding', 'News impact prediction'],
      newCapabilities: ['Institutional flow reading', 'Economic event trading']
    }
  ]

  private readonly defaultConfig: EvolutionConfig = {
    speed: 'medium',
    realism: 'high',
    volatility: 'moderate',
    crisisImpact: 'moderate',
    plateauProbability: 0.3,
    regressionProbability: 0.15
  }

  /**
   * Process personality evolution based on trading activity and performance
   */
  public processEvolution(
    personality: TradingPersonality,
    tradingActivity: {
      totalTrades: number
      daysSinceStart: number
      totalReturn: number
      recentPerformance: number[]
      marketCycleExperience: MarketCycleExperience
      skillMetrics: SkillDevelopment
    },
    config: Partial<EvolutionConfig> = {}
  ): {
    evolvedPersonality: TradingPersonality
    evolutionEvents: EvolutionEvent[]
    predictions: EvolutionPrediction
  } {
    const activeConfig = { ...this.defaultConfig, ...config }
    const evolutionEvents: EvolutionEvent[] = []
    let evolvedPersonality = { ...personality }

    // Check for milestone achievements
    const milestoneEvents = this.checkMilestoneAchievements(
      evolvedPersonality,
      tradingActivity,
      activeConfig
    )
    evolutionEvents.push(...milestoneEvents)

    // Apply milestone changes
    for (const event of milestoneEvents) {
      evolvedPersonality = this.applyEvolutionEvent(evolvedPersonality, event)
    }

    // Process gradual skill improvements
    const skillEvents = this.processSkillEvolution(
      evolvedPersonality,
      tradingActivity,
      activeConfig
    )
    evolutionEvents.push(...skillEvents)

    // Apply skill changes
    for (const event of skillEvents) {
      evolvedPersonality = this.applyEvolutionEvent(evolvedPersonality, event)
    }

    // Process trait evolution based on experience
    const traitEvents = this.processTraitEvolution(
      evolvedPersonality,
      tradingActivity,
      activeConfig
    )
    evolutionEvents.push(...traitEvents)

    // Apply trait changes
    for (const event of traitEvents) {
      evolvedPersonality = this.applyEvolutionEvent(evolvedPersonality, event)
    }

    // Process crisis adaptations (if applicable)
    const crisisEvents = this.processCrisisAdaptation(
      evolvedPersonality,
      tradingActivity.recentPerformance,
      activeConfig
    )
    evolutionEvents.push(...crisisEvents)

    // Apply crisis adaptations
    for (const event of crisisEvents) {
      evolvedPersonality = this.applyEvolutionEvent(evolvedPersonality, event)
    }

    // Generate evolution predictions
    const predictions = this.generateEvolutionPredictions(
      evolvedPersonality,
      tradingActivity,
      activeConfig
    )

    return {
      evolvedPersonality,
      evolutionEvents,
      predictions
    }
  }

  /**
   * Check for milestone achievements
   */
  private checkMilestoneAchievements(
    personality: TradingPersonality,
    activity: any,
    config: EvolutionConfig
  ): EvolutionEvent[] {
    const events: EvolutionEvent[] = []
    const currentLevel = personality.evolution.experienceLevel

    for (const milestone of this.experienceMilestones) {
      // Check if milestone requirements are met
      const tradesQualified = activity.totalTrades >= milestone.tradesRequired
      const timeQualified = activity.daysSinceStart >= milestone.timeRequired
      const profitQualified = activity.totalReturn >= milestone.profitRequired

      // Check if milestone hasn't been achieved yet
      const levelQualified = currentLevel < (milestone.tradesRequired / 10) // Rough level mapping

      if (tradesQualified && timeQualified && profitQualified && levelQualified) {
        const event: EvolutionEvent = {
          id: `milestone_${milestone.tradesRequired}_${Date.now()}`,
          timestamp: new Date(),
          eventType: 'milestone_reached',
          trigger: milestone.description,
          previousState: {
            traits: { ...personality.traits },
            evolution: { ...personality.evolution }
          },
          newState: {
            traits: this.applyTraitChanges(personality.traits, milestone.traitChanges),
            evolution: {
              ...personality.evolution,
              experienceLevel: Math.min(100, personality.evolution.experienceLevel + 10)
            }
          },
          impactDescription: `Achieved ${milestone.description}. Gained skills: ${milestone.skillImprovements.join(', ')}`,
          evolutionScore: 75,
          reversible: false
        }
        events.push(event)
      }
    }

    return events
  }

  /**
   * Process gradual skill evolution
   */
  private processSkillEvolution(
    personality: TradingPersonality,
    activity: any,
    config: EvolutionConfig
  ): EvolutionEvent[] {
    const events: EvolutionEvent[] = []
    
    // Calculate skill improvement rate based on config and personality
    const baseImprovementRate = personality.evolution.improvementRate
    const speedMultiplier = this.getSpeedMultiplier(config.speed)
    const actualRate = baseImprovementRate * speedMultiplier

    // Check if enough time has passed for improvement
    const daysSinceLastEvolution = this.calculateDaysSinceLastEvolution(personality)
    if (daysSinceLastEvolution < 30) return events // Monthly skill updates

    // Determine which skills should improve
    const skillImprovements = this.calculateSkillImprovements(
      personality,
      activity,
      actualRate,
      config
    )

    if (skillImprovements.length > 0) {
      const event: EvolutionEvent = {
        id: `skill_improvement_${Date.now()}`,
        timestamp: new Date(),
        eventType: 'skill_improvement',
        trigger: 'Monthly skill development review',
        previousState: {
          traits: { ...personality.traits }
        },
        newState: {
          traits: this.applySkillBasedTraitChanges(personality.traits, skillImprovements)
        },
        impactDescription: `Skill improvements: ${skillImprovements.join(', ')}`,
        evolutionScore: 25,
        reversible: false
      }
      events.push(event)
    }

    return events
  }

  /**
   * Process trait evolution based on trading experience
   */
  private processTraitEvolution(
    personality: TradingPersonality,
    activity: any,
    config: EvolutionConfig
  ): EvolutionEvent[] {
    const events: EvolutionEvent[] = []
    
    // Calculate trait changes based on recent performance and market exposure
    const traitChanges = this.calculateTraitEvolution(
      personality,
      activity,
      config
    )

    if (Object.keys(traitChanges).length > 0) {
      const event: EvolutionEvent = {
        id: `trait_evolution_${Date.now()}`,
        timestamp: new Date(),
        eventType: 'trait_evolution',
        trigger: 'Natural trait evolution from trading experience',
        previousState: {
          traits: { ...personality.traits }
        },
        newState: {
          traits: this.applyTraitChanges(personality.traits, traitChanges)
        },
        impactDescription: this.describeTraitChanges(traitChanges),
        evolutionScore: 35,
        reversible: true
      }
      events.push(event)
    }

    return events
  }

  /**
   * Process crisis adaptation (major losses, drawdowns)
   */
  private processCrisisAdaptation(
    personality: TradingPersonality,
    recentPerformance: number[],
    config: EvolutionConfig
  ): EvolutionEvent[] {
    const events: EvolutionEvent[] = []
    
    // Detect crisis conditions
    const consecutiveLosses = this.countConsecutiveLosses(recentPerformance)
    const maxDrawdown = this.calculateMaxDrawdown(recentPerformance)
    const recentReturn = recentPerformance.slice(-30).reduce((sum, p) => sum + p, 0)

    // Crisis thresholds
    const isMajorCrisis = consecutiveLosses >= 5 || maxDrawdown <= -15 || recentReturn <= -20
    const isMinorCrisis = consecutiveLosses >= 3 || maxDrawdown <= -8 || recentReturn <= -10

    if (isMajorCrisis || isMinorCrisis) {
      const adaptations = this.calculateCrisisAdaptations(
        personality,
        isMajorCrisis,
        config
      )

      if (Object.keys(adaptations).length > 0) {
        const event: EvolutionEvent = {
          id: `crisis_adaptation_${Date.now()}`,
          timestamp: new Date(),
          eventType: 'crisis_adaptation',
          trigger: isMajorCrisis ? 'Major trading crisis detected' : 'Minor trading setback',
          previousState: {
            traits: { ...personality.traits },
            riskAppetite: { ...personality.riskAppetite }
          },
          newState: {
            traits: this.applyTraitChanges(personality.traits, adaptations.traitChanges || {}),
            riskAppetite: adaptations.riskChanges ? 
              { ...personality.riskAppetite, ...adaptations.riskChanges } : 
              personality.riskAppetite
          },
          impactDescription: adaptations.description,
          evolutionScore: isMajorCrisis ? 60 : 40,
          reversible: true
        }
        events.push(event)
      }
    }

    return events
  }

  /**
   * Apply trait changes to existing traits
   */
  private applyTraitChanges(
    currentTraits: PersonalityTraits,
    changes: Partial<PersonalityTraits>
  ): PersonalityTraits {
    const newTraits = { ...currentTraits }
    
    for (const [trait, change] of Object.entries(changes)) {
      if (change !== undefined) {
        const key = trait as keyof PersonalityTraits
        newTraits[key] = Math.max(0, Math.min(100, currentTraits[key] + change))
      }
    }
    
    return newTraits
  }

  /**
   * Apply evolution event to personality
   */
  private applyEvolutionEvent(
    personality: TradingPersonality,
    event: EvolutionEvent
  ): TradingPersonality {
    const updated = { ...personality }
    
    if (event.newState.traits) {
      updated.traits = { ...event.newState.traits }
    }
    
    if (event.newState.evolution) {
      updated.evolution = { ...updated.evolution, ...event.newState.evolution }
    }
    
    if (event.newState.riskAppetite) {
      updated.riskAppetite = { ...updated.riskAppetite, ...event.newState.riskAppetite }
    }
    
    // Update metadata
    updated.updatedAt = new Date()
    updated.metadata.performance.lastReviewDate = new Date()
    
    return updated
  }

  /**
   * Calculate skill-based trait improvements
   */
  private calculateSkillImprovements(
    personality: TradingPersonality,
    activity: any,
    improvementRate: number,
    config: EvolutionConfig
  ): string[] {
    const improvements: string[] = []
    
    // Determine which skills should improve based on trading activity
    if (activity.totalTrades > 100 && personality.traits.discipline < 80) {
      improvements.push('Risk Management')
    }
    
    if (activity.marketCycleExperience.newsEvents.count > 20 && personality.traits.adaptability < 75) {
      improvements.push('News Trading')
    }
    
    if (activity.totalReturn > 15 && personality.traits.confidence < 85) {
      improvements.push('Technical Analysis')
    }
    
    // Apply plateau probability
    if (Math.random() < config.plateauProbability) {
      improvements.splice(0, Math.floor(improvements.length / 2)) // Remove some improvements
    }
    
    return improvements
  }

  /**
   * Apply skill-based trait changes
   */
  private applySkillBasedTraitChanges(
    traits: PersonalityTraits,
    skillImprovements: string[]
  ): PersonalityTraits {
    const changes: Partial<PersonalityTraits> = {}
    
    for (const skill of skillImprovements) {
      switch (skill) {
        case 'Risk Management':
          changes.discipline = (changes.discipline || 0) + 3
          changes.emotionality = (changes.emotionality || 0) - 2
          break
        case 'Technical Analysis':
          changes.confidence = (changes.confidence || 0) + 2
          changes.patience = (changes.patience || 0) + 1
          break
        case 'News Trading':
          changes.adaptability = (changes.adaptability || 0) + 3
          changes.riskTolerance = (changes.riskTolerance || 0) + 1
          break
      }
    }
    
    return this.applyTraitChanges(traits, changes)
  }

  /**
   * Calculate natural trait evolution
   */
  private calculateTraitEvolution(
    personality: TradingPersonality,
    activity: any,
    config: EvolutionConfig
  ): Partial<PersonalityTraits> {
    const changes: Partial<PersonalityTraits> = {}
    const evolutionSettings = personality.evolution
    
    // Apply trait evolution based on configured improving/degrading traits
    for (const trait of evolutionSettings.traitEvolution.improvingTraits) {
      const currentValue = personality.traits[trait]
      if (currentValue < 95) { // Leave room for improvement
        const improvement = Math.random() * 2 + 0.5 // 0.5-2.5 point improvement
        changes[trait] = improvement
      }
    }
    
    for (const trait of evolutionSettings.traitEvolution.degradingTraits) {
      const currentValue = personality.traits[trait]
      if (currentValue > 5) { // Leave room for degradation
        const degradation = -(Math.random() * 1.5 + 0.2) // 0.2-1.7 point decrease
        changes[trait] = degradation
      }
    }
    
    // Apply seasonal adjustments
    const currentSeason = this.getCurrentSeason()
    const seasonalAdjustments = evolutionSettings.seasonalAdjustments[currentSeason]
    
    for (const [trait, adjustment] of Object.entries(seasonalAdjustments)) {
      const key = trait as keyof PersonalityTraits
      changes[key] = (changes[key] || 0) + (adjustment || 0)
    }
    
    return changes
  }

  /**
   * Calculate crisis adaptations
   */
  private calculateCrisisAdaptations(
    personality: TradingPersonality,
    isMajorCrisis: boolean,
    config: EvolutionConfig
  ): {
    traitChanges?: Partial<PersonalityTraits>
    riskChanges?: Partial<RiskAppetite>
    description: string
  } {
    const impactMultiplier = config.crisisImpact === 'minimal' ? 0.5 : 
                            config.crisisImpact === 'moderate' ? 1.0 : 1.5
    
    const magnitude = isMajorCrisis ? 1.5 : 1.0
    const totalImpact = impactMultiplier * magnitude
    
    const adaptations: any = {}
    
    if (isMajorCrisis) {
      adaptations.traitChanges = {
        emotionality: 5 * totalImpact,
        confidence: -8 * totalImpact,
        riskTolerance: -10 * totalImpact,
        discipline: 3 * totalImpact
      }
      
      adaptations.riskChanges = {
        baseRiskPerTrade: personality.riskAppetite.baseRiskPerTrade * (1 - 0.3 * totalImpact)
      }
      
      adaptations.description = 'Major crisis triggered defensive adaptations: reduced risk tolerance, increased caution'
    } else {
      adaptations.traitChanges = {
        emotionality: 2 * totalImpact,
        confidence: -3 * totalImpact,
        discipline: 2 * totalImpact
      }
      
      adaptations.description = 'Minor setback triggered mild defensive adjustments'
    }
    
    return adaptations
  }

  /**
   * Generate evolution predictions
   */
  private generateEvolutionPredictions(
    personality: TradingPersonality,
    activity: any,
    config: EvolutionConfig
  ): EvolutionPrediction {
    const timeframe = '3-6 months'
    const expectedChanges: EvolutionPrediction['expectedChanges'] = []
    
    // Predict trait changes based on current trajectory
    const currentLevel = personality.evolution.experienceLevel
    
    if (currentLevel < 50) {
      expectedChanges.push({
        trait: 'confidence',
        direction: 'increase',
        magnitude: 'medium',
        probability: 0.8,
        reasoning: 'Continued trading experience should build confidence'
      })
      
      expectedChanges.push({
        trait: 'discipline',
        direction: 'increase',
        magnitude: 'small',
        probability: 0.7,
        reasoning: 'Learning from mistakes improves discipline'
      })
    }
    
    if (currentLevel > 70) {
      expectedChanges.push({
        trait: 'risk_appetite',
        direction: 'increase',
        magnitude: 'small',
        probability: 0.6,
        reasoning: 'Experienced traders typically increase risk appetite gradually'
      })
    }
    
    // Generate milestone predictions
    const milestones: EvolutionPrediction['milestones'] = []
    
    for (const milestone of this.experienceMilestones) {
      if (activity.totalTrades < milestone.tradesRequired) {
        const tradesNeeded = milestone.tradesRequired - activity.totalTrades
        const estimatedDays = tradesNeeded * 2 // Assuming ~0.5 trades per day
        
        milestones.push({
          description: milestone.description,
          estimatedDate: new Date(Date.now() + estimatedDays * 24 * 60 * 60 * 1000),
          requirements: [
            `${tradesNeeded} more trades`,
            `${Math.max(0, milestone.profitRequired - activity.totalReturn)}% additional profit`,
            `${Math.max(0, milestone.timeRequired - activity.daysSinceStart)} more days experience`
          ]
        })
        break // Only show next milestone
      }
    }
    
    // Generate risk predictions
    const risks: EvolutionPrediction['risks'] = []
    
    if (personality.traits.emotionality > 60) {
      risks.push({
        risk: 'Emotional trading decisions during market stress',
        probability: 0.4,
        mitigation: 'Implement cooling-off periods and automated risk management'
      })
    }
    
    if (personality.evolution.experienceLevel > 80 && personality.traits.confidence > 80) {
      risks.push({
        risk: 'Overconfidence leading to excessive risk-taking',
        probability: 0.3,
        mitigation: 'Regular strategy reviews and position size limits'
      })
    }
    
    return {
      timeframe,
      expectedChanges,
      milestones,
      risks
    }
  }

  /**
   * Utility functions
   */
  private getSpeedMultiplier(speed: EvolutionConfig['speed']): number {
    const multipliers = {
      very_slow: 0.5,
      slow: 0.75,
      medium: 1.0,
      fast: 1.25,
      very_fast: 1.5
    }
    return multipliers[speed]
  }

  private calculateDaysSinceLastEvolution(personality: TradingPersonality): number {
    const lastUpdate = personality.updatedAt
    const now = new Date()
    return Math.floor((now.getTime() - lastUpdate.getTime()) / (24 * 60 * 60 * 1000))
  }

  private getCurrentSeason(): 'spring' | 'summer' | 'autumn' | 'winter' {
    const month = new Date().getMonth()
    if (month >= 2 && month <= 4) return 'spring'
    if (month >= 5 && month <= 7) return 'summer'
    if (month >= 8 && month <= 10) return 'autumn'
    return 'winter'
  }

  private countConsecutiveLosses(performance: number[]): number {
    let count = 0
    for (let i = performance.length - 1; i >= 0; i--) {
      if (performance[i] < 0) count++
      else break
    }
    return count
  }

  private calculateMaxDrawdown(performance: number[]): number {
    let peak = 0
    let maxDrawdown = 0
    let cumulative = 0
    
    for (const pnl of performance) {
      cumulative += pnl
      peak = Math.max(peak, cumulative)
      const drawdown = (cumulative - peak) / Math.max(peak, 1) * 100
      maxDrawdown = Math.min(maxDrawdown, drawdown)
    }
    
    return maxDrawdown
  }

  private describeTraitChanges(changes: Partial<PersonalityTraits>): string {
    const descriptions: string[] = []
    
    for (const [trait, change] of Object.entries(changes)) {
      if (change && Math.abs(change) > 1) {
        const direction = change > 0 ? 'increased' : 'decreased'
        descriptions.push(`${trait} ${direction} by ${Math.abs(change).toFixed(1)} points`)
      }
    }
    
    return descriptions.join(', ') || 'Minor trait adjustments'
  }

  /**
   * Simulate personality evolution over time period
   */
  public simulateEvolutionOverTime(
    personality: TradingPersonality,
    daysToSimulate: number,
    averageDailyTrades: number = 0.5,
    averageDailyReturn: number = 0.1
  ): {
    dailySnapshots: Array<{ day: number; personality: TradingPersonality; events: EvolutionEvent[] }>
    summary: {
      totalEvents: number
      majorMilestones: number
      traitChanges: Record<keyof PersonalityTraits, number>
      finalExperienceLevel: number
    }
  } {
    const snapshots: Array<{ day: number; personality: TradingPersonality; events: EvolutionEvent[] }> = []
    let currentPersonality = { ...personality }
    let totalTrades = 0
    let totalReturn = 0
    let allEvents: EvolutionEvent[] = []
    
    for (let day = 1; day <= daysToSimulate; day++) {
      // Simulate daily trading activity
      const dailyTrades = Math.floor(Math.random() * 2 + averageDailyTrades)
      const dailyReturn = (Math.random() - 0.4) * 2 + averageDailyReturn // Slight positive bias
      
      totalTrades += dailyTrades
      totalReturn += dailyReturn
      
      // Check for evolution every 30 days
      if (day % 30 === 0) {
        const mockActivity = {
          totalTrades,
          daysSinceStart: day,
          totalReturn,
          recentPerformance: Array(30).fill(0).map(() => Math.random() * 2 - 0.5),
          marketCycleExperience: {
            bullMarket: { trades: totalTrades * 0.3, exposure: 0.3, performance: 0.8 },
            bearMarket: { trades: totalTrades * 0.2, exposure: 0.2, performance: -0.2 },
            sidewaysMarket: { trades: totalTrades * 0.4, exposure: 0.4, performance: 0.1 },
            volatileMarket: { trades: totalTrades * 0.1, exposure: 0.1, performance: 0.3 },
            newsEvents: { count: Math.floor(day / 10), successRate: 0.6 },
            drawdownRecoveries: { count: 2, averageTime: 15 }
          },
          skillMetrics: {
            technicalAnalysis: Math.min(100, 30 + day * 0.1),
            fundamentalAnalysis: Math.min(100, 20 + day * 0.05),
            riskManagement: Math.min(100, 40 + day * 0.08),
            emotionalControl: Math.min(100, 35 + day * 0.06),
            marketTiming: Math.min(100, 25 + day * 0.07),
            positionSizing: Math.min(100, 30 + day * 0.09),
            pairSelection: Math.min(100, 20 + day * 0.04),
            newsTrading: Math.min(100, 15 + day * 0.03),
            trendFollowing: Math.min(100, 35 + day * 0.08),
            counterTrend: Math.min(100, 10 + day * 0.02)
          }
        }
        
        const evolutionResult = this.processEvolution(currentPersonality, mockActivity)
        currentPersonality = evolutionResult.evolvedPersonality
        allEvents.push(...evolutionResult.evolutionEvents)
        
        snapshots.push({
          day,
          personality: { ...currentPersonality },
          events: evolutionResult.evolutionEvents
        })
      }
    }
    
    // Calculate summary
    const initialTraits = personality.traits
    const finalTraits = currentPersonality.traits
    const traitChanges: Record<keyof PersonalityTraits, number> = {
      riskTolerance: finalTraits.riskTolerance - initialTraits.riskTolerance,
      patience: finalTraits.patience - initialTraits.patience,
      confidence: finalTraits.confidence - initialTraits.confidence,
      emotionality: finalTraits.emotionality - initialTraits.emotionality,
      discipline: finalTraits.discipline - initialTraits.discipline,
      adaptability: finalTraits.adaptability - initialTraits.adaptability
    }
    
    return {
      dailySnapshots: snapshots,
      summary: {
        totalEvents: allEvents.length,
        majorMilestones: allEvents.filter(e => e.eventType === 'milestone_reached').length,
        traitChanges,
        finalExperienceLevel: currentPersonality.evolution.experienceLevel
      }
    }
  }
}

/**
 * Default personality evolution engine instance
 */
export const defaultPersonalityEvolutionEngine = new PersonalityEvolutionEngine()

/**
 * Utility functions for personality evolution
 */
export const PersonalityEvolutionUtils = {
  /**
   * Analyze evolution trajectory
   */
  analyzeEvolutionTrajectory(events: EvolutionEvent[]): {
    growthRate: 'slow' | 'steady' | 'rapid'
    stability: 'volatile' | 'stable' | 'very_stable'
    direction: 'improving' | 'declining' | 'stagnant'
  } {
    if (events.length === 0) {
      return { growthRate: 'slow', stability: 'stable', direction: 'stagnant' }
    }
    
    const positiveEvents = events.filter(e => e.evolutionScore > 50).length
    const totalEvents = events.length
    const recentEvents = events.slice(-5)
    
    // Determine growth rate
    let growthRate: 'slow' | 'steady' | 'rapid'
    if (totalEvents > 10) growthRate = 'rapid'
    else if (totalEvents > 5) growthRate = 'steady'
    else growthRate = 'slow'
    
    // Determine stability
    const evolutionScores = events.map(e => e.evolutionScore)
    const avgScore = evolutionScores.reduce((sum, score) => sum + score, 0) / evolutionScores.length
    const variance = evolutionScores.reduce((sum, score) => sum + Math.pow(score - avgScore, 2), 0) / evolutionScores.length
    
    let stability: 'volatile' | 'stable' | 'very_stable'
    if (variance > 400) stability = 'volatile'
    else if (variance > 200) stability = 'stable'
    else stability = 'very_stable'
    
    // Determine direction
    const recentPositive = recentEvents.filter(e => e.evolutionScore > 50).length
    let direction: 'improving' | 'declining' | 'stagnant'
    if (recentPositive / Math.max(recentEvents.length, 1) > 0.6) direction = 'improving'
    else if (recentPositive / Math.max(recentEvents.length, 1) < 0.4) direction = 'declining'
    else direction = 'stagnant'
    
    return { growthRate, stability, direction }
  },

  /**
   * Calculate personality maturity score
   */
  calculateMaturityScore(personality: TradingPersonality): number {
    const traits = personality.traits
    const evolution = personality.evolution
    
    // Weighted score based on key traits and experience
    const disciplineWeight = 0.3
    const confidenceWeight = 0.2
    const adaptabilityWeight = 0.2
    const experienceWeight = 0.2
    const emotionalControlWeight = 0.1 // Inverse of emotionality
    
    const score = 
      (traits.discipline * disciplineWeight) +
      (traits.confidence * confidenceWeight) +
      (traits.adaptability * adaptabilityWeight) +
      (evolution.experienceLevel * experienceWeight) +
      ((100 - traits.emotionality) * emotionalControlWeight)
    
    return Math.round(score)
  },

  /**
   * Generate personality evolution report
   */
  generateEvolutionReport(
    initialPersonality: TradingPersonality,
    currentPersonality: TradingPersonality,
    events: EvolutionEvent[]
  ): {
    summary: string
    keyMilestones: string[]
    traitProgression: Array<{ trait: string; change: number; percentage: number }>
    recommendations: string[]
  } {
    const traitProgression: Array<{ trait: string; change: number; percentage: number }> = []
    
    for (const trait of Object.keys(initialPersonality.traits) as Array<keyof PersonalityTraits>) {
      const initial = initialPersonality.traits[trait]
      const current = currentPersonality.traits[trait]
      const change = current - initial
      const percentage = (change / initial) * 100
      
      traitProgression.push({
        trait,
        change,
        percentage
      })
    }
    
    const milestones = events
      .filter(e => e.eventType === 'milestone_reached')
      .map(e => e.impactDescription)
    
    const maturityGain = this.calculateMaturityScore(currentPersonality) - 
                        this.calculateMaturityScore(initialPersonality)
    
    const summary = `Personality evolved through ${events.length} events, gaining ${maturityGain} maturity points. ` +
                   `Experience level increased from ${initialPersonality.evolution.experienceLevel} to ${currentPersonality.evolution.experienceLevel}.`
    
    const recommendations: string[] = []
    
    if (currentPersonality.traits.emotionality > 60) {
      recommendations.push('Focus on emotional control development through mindfulness training')
    }
    
    if (currentPersonality.traits.discipline < 70) {
      recommendations.push('Strengthen rule-following through systematic approach implementation')
    }
    
    if (currentPersonality.evolution.experienceLevel < 50) {
      recommendations.push('Continue building experience through consistent trading activity')
    }
    
    return {
      summary,
      keyMilestones: milestones,
      traitProgression,
      recommendations
    }
  }
}