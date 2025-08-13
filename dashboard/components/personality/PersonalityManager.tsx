'use client'

import { useState, useMemo } from 'react'
import { TradingPersonality, PersonalityArchetype } from '@/types/personality'

/**
 * Mock personality data for development
 */
const MOCK_PERSONALITIES: TradingPersonality[] = [
  {
    id: 'personality_1',
    name: 'Conservative Scalper',
    description: 'Risk-averse trader focused on quick, small profits with major currency pairs',
    accountId: 'acc_001',
    createdAt: new Date('2024-01-15'),
    updatedAt: new Date('2024-02-01'),
    isActive: true,
    traits: {
      riskTolerance: 25,
      patience: 35,
      confidence: 60,
      emotionality: 20,
      discipline: 85,
      adaptability: 50
    },
    timePreferences: {
      preferredSessions: ['london', 'newyork'],
      activeHours: { start: 7, end: 16, timezone: 'UTC' },
      sessionActivity: { asian: 20, london: 90, newyork: 95, overlap: 100 },
      weekendActivity: 10,
      holidayActivity: 25
    },
    pairPreferences: {
      primary: [
        { symbol: 'EURUSD', strength: 85, category: 'major', frequency: 12, maxPositionSize: 3.5 },
        { symbol: 'GBPUSD', strength: 78, category: 'major', frequency: 10, maxPositionSize: 3.0 }
      ],
      secondary: [
        { symbol: 'USDJPY', strength: 65, category: 'major', frequency: 6, maxPositionSize: 2.0 },
        { symbol: 'USDCHF', strength: 58, category: 'major', frequency: 4, maxPositionSize: 1.5 }
      ]
    },
    riskAppetite: {
      baseRiskPerTrade: 0.8,
      riskVariance: { min: 0.5, max: 1.2 },
      maxPortfolioRisk: 5.0,
      performanceScaling: { winningStreak: 1.1, losingStreak: 0.8 },
      drawdownAdjustments: { mild: 0.9, moderate: 0.7, severe: 0.5 }
    },
    evolution: {
      experienceLevel: 45,
      improvementRate: 2.5,
      evolutionTriggers: { tradesToNextLevel: 150, profitThreshold: 10, timeInMarket: 3 },
      traitEvolution: { improvingTraits: ['confidence', 'discipline'], degradingTraits: ['emotionality'] },
      seasonalAdjustments: { spring: {}, summer: {}, autumn: {}, winter: {} }
    },
    behavioralPatterns: {
      decisionSpeed: { min: 1500, max: 4000, average: 2500 },
      analysisTime: { min: 120, max: 600, average: 300 },
      positionManagement: { stopLossMovement: 20, partialProfitTaking: 80, letWinnersRun: 30 },
      emotionalResponses: { lossReaction: 'neutral', winReaction: 'cautious', stressResponse: 'freeze' }
    },
    metadata: {
      archetype: 'conservative_scalper',
      compatibility: {},
      performance: {
        totalTrades: 234,
        winRate: 73.2,
        avgProfitPerTrade: 45.50,
        maxDrawdown: -5.2,
        sharpeRatio: 1.8,
        daysActive: 90,
        lastReviewDate: new Date(),
        trend: 'improving'
      }
    }
  },
  {
    id: 'personality_2',
    name: 'Aggressive Swing Trader',
    description: 'High-risk trader seeking larger moves with diverse currency pairs',
    accountId: 'acc_002',
    createdAt: new Date('2024-01-20'),
    updatedAt: new Date('2024-02-03'),
    isActive: true,
    traits: {
      riskTolerance: 80,
      patience: 70,
      confidence: 85,
      emotionality: 45,
      discipline: 65,
      adaptability: 80
    },
    timePreferences: {
      preferredSessions: ['london', 'newyork', 'overlap'],
      activeHours: { start: 8, end: 21, timezone: 'UTC' },
      sessionActivity: { asian: 30, london: 85, newyork: 90, overlap: 95 },
      weekendActivity: 25,
      holidayActivity: 40
    },
    pairPreferences: {
      primary: [
        { symbol: 'GBPJPY', strength: 90, category: 'minor', frequency: 15, maxPositionSize: 5.0 },
        { symbol: 'EURJPY', strength: 88, category: 'minor', frequency: 14, maxPositionSize: 4.5 },
        { symbol: 'AUDUSD', strength: 82, category: 'major', frequency: 12, maxPositionSize: 4.0 }
      ],
      secondary: [
        { symbol: 'NZDUSD', strength: 70, category: 'major', frequency: 8, maxPositionSize: 3.0 },
        { symbol: 'USDCAD', strength: 68, category: 'major', frequency: 7, maxPositionSize: 2.5 }
      ]
    },
    riskAppetite: {
      baseRiskPerTrade: 1.8,
      riskVariance: { min: 1.2, max: 2.0 },
      maxPortfolioRisk: 12.0,
      performanceScaling: { winningStreak: 1.3, losingStreak: 0.7 },
      drawdownAdjustments: { mild: 0.95, moderate: 0.8, severe: 0.6 }
    },
    evolution: {
      experienceLevel: 68,
      improvementRate: 3.2,
      evolutionTriggers: { tradesToNextLevel: 85, profitThreshold: 15, timeInMarket: 2 },
      traitEvolution: { improvingTraits: ['adaptability', 'confidence'], degradingTraits: ['emotionality'] },
      seasonalAdjustments: { spring: {}, summer: {}, autumn: {}, winter: {} }
    },
    behavioralPatterns: {
      decisionSpeed: { min: 800, max: 2500, average: 1500 },
      analysisTime: { min: 180, max: 900, average: 450 },
      positionManagement: { stopLossMovement: 60, partialProfitTaking: 40, letWinnersRun: 85 },
      emotionalResponses: { lossReaction: 'aggressive', winReaction: 'confident', stressResponse: 'fight' }
    },
    metadata: {
      archetype: 'aggressive_swing_trader',
      compatibility: {},
      performance: {
        totalTrades: 189,
        winRate: 68.5,
        avgProfitPerTrade: 78.20,
        maxDrawdown: -12.1,
        sharpeRatio: 1.4,
        daysActive: 75,
        lastReviewDate: new Date(),
        trend: 'stable'
      }
    }
  },
  {
    id: 'personality_3',
    name: 'Evening Range Trader',
    description: 'Focuses on Asian session range trading with patient approach',
    accountId: 'acc_003',
    createdAt: new Date('2024-01-25'),
    updatedAt: new Date('2024-02-05'),
    isActive: false,
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
    },
    pairPreferences: {
      primary: [
        { symbol: 'USDJPY', strength: 88, category: 'major', frequency: 10, maxPositionSize: 3.5 },
        { symbol: 'AUDUSD', strength: 82, category: 'major', frequency: 9, maxPositionSize: 3.0 }
      ],
      secondary: [
        { symbol: 'NZDUSD', strength: 65, category: 'major', frequency: 5, maxPositionSize: 2.0 },
        { symbol: 'AUDCAD', strength: 58, category: 'minor', frequency: 4, maxPositionSize: 1.5 }
      ]
    },
    riskAppetite: {
      baseRiskPerTrade: 1.2,
      riskVariance: { min: 0.8, max: 1.6 },
      maxPortfolioRisk: 8.0,
      performanceScaling: { winningStreak: 1.05, losingStreak: 0.95 },
      drawdownAdjustments: { mild: 0.95, moderate: 0.85, severe: 0.7 }
    },
    evolution: {
      experienceLevel: 52,
      improvementRate: 1.8,
      evolutionTriggers: { tradesToNextLevel: 120, profitThreshold: 12, timeInMarket: 4 },
      traitEvolution: { improvingTraits: ['patience', 'discipline'], degradingTraits: ['emotionality'] },
      seasonalAdjustments: { spring: {}, summer: {}, autumn: {}, winter: {} }
    },
    behavioralPatterns: {
      decisionSpeed: { min: 2000, max: 6000, average: 3500 },
      analysisTime: { min: 300, max: 1200, average: 600 },
      positionManagement: { stopLossMovement: 25, partialProfitTaking: 70, letWinnersRun: 65 },
      emotionalResponses: { lossReaction: 'neutral', winReaction: 'cautious', stressResponse: 'freeze' }
    },
    metadata: {
      archetype: 'evening_range_trader',
      compatibility: {},
      performance: {
        totalTrades: 156,
        winRate: 71.8,
        avgProfitPerTrade: 52.30,
        maxDrawdown: -6.8,
        sharpeRatio: 1.6,
        daysActive: 65,
        lastReviewDate: new Date(),
        trend: 'improving'
      }
    }
  }
]

/**
 * Props for PersonalityManager component
 */
interface PersonalityManagerProps {
  /** Loading state */
  loading?: boolean
  /** Error message */
  error?: string
}

/**
 * Main personality management interface
 * Provides comprehensive management of trading personalities including creation,
 * editing, monitoring, and analysis of personality performance and behavior.
 */
export function PersonalityManager({
  loading = false,
  error
}: PersonalityManagerProps) {
  const [personalities] = useState<TradingPersonality[]>(MOCK_PERSONALITIES)
  const [selectedPersonality, setSelectedPersonality] = useState<TradingPersonality | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'details' | 'performance' | 'evolution' | 'settings'>('overview')
  const [filterStatus, setFilterStatus] = useState<'all' | 'active' | 'inactive'>('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState<'name' | 'created' | 'performance' | 'experience'>('created')

  // Filter and sort personalities
  const filteredPersonalities = useMemo(() => {
    let filtered = personalities

    // Apply status filter
    if (filterStatus !== 'all') {
      filtered = filtered.filter(p => 
        filterStatus === 'active' ? p.isActive : !p.isActive
      )
    }

    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(p =>
        p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.metadata.archetype.toLowerCase().includes(searchTerm.toLowerCase())
      )
    }

    // Apply sorting
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name)
        case 'created':
          return b.createdAt.getTime() - a.createdAt.getTime()
        case 'performance':
          return b.metadata.performance.winRate - a.metadata.performance.winRate
        case 'experience':
          return b.evolution.experienceLevel - a.evolution.experienceLevel
        default:
          return 0
      }
    })

    return filtered
  }, [personalities, filterStatus, searchTerm, sortBy])

  // Calculate summary statistics
  const stats = useMemo(() => {
    const active = personalities.filter(p => p.isActive).length
    const avgWinRate = personalities.reduce((sum, p) => sum + p.metadata.performance.winRate, 0) / personalities.length
    const avgExperience = personalities.reduce((sum, p) => sum + p.evolution.experienceLevel, 0) / personalities.length
    const totalTrades = personalities.reduce((sum, p) => sum + p.metadata.performance.totalTrades, 0)

    return {
      total: personalities.length,
      active,
      inactive: personalities.length - active,
      avgWinRate: avgWinRate.toFixed(1),
      avgExperience: avgExperience.toFixed(0),
      totalTrades
    }
  }, [personalities])

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      signDisplay: amount !== 0 ? 'always' : 'never'
    }).format(amount)
  }

  // const formatPercentage = (value: number): string => {
  //   return new Intl.NumberFormat('en-US', {
  //     style: 'percent',
  //     minimumFractionDigits: 1,
  //     maximumFractionDigits: 1,
  //     signDisplay: value !== 0 ? 'always' : 'never'
  //   }).format(value / 100)
  // }

  const getArchetypeIcon = (archetype: PersonalityArchetype): string => {
    const icons: Record<PersonalityArchetype, string> = {
      conservative_scalper: '🛡️',
      aggressive_swing_trader: '⚡',
      morning_momentum_trader: '🌅',
      evening_range_trader: '🌙',
      news_reaction_trader: '📰',
      technical_pattern_trader: '📊',
      carry_trade_specialist: '💰',
      volatility_hunter: '🎯',
      risk_averse_conservative: '🐌',
      balanced_opportunist: '⚖️'
    }
    return icons[archetype] || '🤖'
  }

  const getTrendIcon = (trend: string): string => {
    switch (trend) {
      case 'improving': return '📈'
      case 'declining': return '📉'
      case 'stable': return '➡️'
      default: return '➡️'
    }
  }

  const getTrendColor = (trend: string): string => {
    switch (trend) {
      case 'improving': return 'text-green-400'
      case 'declining': return 'text-red-400'
      case 'stable': return 'text-yellow-400'
      default: return 'text-gray-400'
    }
  }

  // Loading state
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-700 rounded w-64 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="bg-gray-750 rounded-lg p-6">
                <div className="h-6 bg-gray-700 rounded mb-2"></div>
                <div className="h-8 bg-gray-700 rounded"></div>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="bg-gray-750 rounded-lg p-6">
                <div className="h-6 bg-gray-700 rounded mb-4"></div>
                <div className="space-y-3">
                  {Array.from({ length: 4 }).map((_, j) => (
                    <div key={j} className="h-4 bg-gray-700 rounded"></div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-6">
        <div className="text-red-400 font-medium">Error Loading Personalities</div>
        <div className="text-red-200 text-sm mt-1">{error}</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white">Trading Personality Manager</h2>
          <p className="text-gray-400 text-sm">
            Manage and monitor AI trading personalities for anti-detection
          </p>
        </div>
        <div className="flex gap-3">
          <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors">
            + Create Personality
          </button>
          <button className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors">
            Bulk Generate
          </button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-gray-750 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-gray-400 text-sm">Total Personalities</div>
              <div className="text-2xl font-bold text-white">{stats.total}</div>
            </div>
            <div className="text-blue-400 text-2xl">🤖</div>
          </div>
          <div className="text-green-400 text-sm mt-2">
            {stats.active} active • {stats.inactive} inactive
          </div>
        </div>

        <div className="bg-gray-750 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-gray-400 text-sm">Average Win Rate</div>
              <div className="text-2xl font-bold text-white">{stats.avgWinRate}%</div>
            </div>
            <div className="text-green-400 text-2xl">🎯</div>
          </div>
          <div className="text-gray-500 text-sm mt-2">
            Across all personalities
          </div>
        </div>

        <div className="bg-gray-750 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-gray-400 text-sm">Average Experience</div>
              <div className="text-2xl font-bold text-white">{stats.avgExperience}</div>
            </div>
            <div className="text-yellow-400 text-2xl">📊</div>
          </div>
          <div className="text-gray-500 text-sm mt-2">
            Out of 100 levels
          </div>
        </div>

        <div className="bg-gray-750 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-gray-400 text-sm">Total Trades</div>
              <div className="text-2xl font-bold text-white">{stats.totalTrades.toLocaleString()}</div>
            </div>
            <div className="text-purple-400 text-2xl">📈</div>
          </div>
          <div className="text-gray-500 text-sm mt-2">
            Combined activity
          </div>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="flex flex-col sm:flex-row gap-4 bg-gray-750 rounded-lg p-4">
        <div className="flex-1">
          <input
            type="text"
            placeholder="Search personalities..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
          />
        </div>
        
        <div className="flex gap-2">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as typeof filterStatus)}
            className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
            className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
          >
            <option value="created">Created Date</option>
            <option value="name">Name</option>
            <option value="performance">Performance</option>
            <option value="experience">Experience</option>
          </select>
        </div>
      </div>

      {/* Personality Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredPersonalities.map((personality) => (
          <div
            key={personality.id}
            onClick={() => setSelectedPersonality(personality)}
            className={`
              bg-gray-750 rounded-lg p-6 border cursor-pointer transition-all hover:scale-105
              ${selectedPersonality?.id === personality.id ? 'border-blue-500 ring-2 ring-blue-500/20' : 'border-gray-700 hover:border-gray-600'}
              ${!personality.isActive ? 'opacity-60' : ''}
            `}
          >
            {/* Header */}
            <div className="flex justify-between items-start mb-4">
              <div className="flex items-center gap-3">
                <div className="text-2xl">{getArchetypeIcon(personality.metadata.archetype)}</div>
                <div>
                  <h3 className="text-white font-medium">{personality.name}</h3>
                  <div className="text-gray-400 text-sm">{personality.accountId}</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${personality.isActive ? 'bg-green-400' : 'bg-gray-500'}`}></div>
                <span className={getTrendColor(personality.metadata.performance.trend)}>
                  {getTrendIcon(personality.metadata.performance.trend)}
                </span>
              </div>
            </div>

            {/* Description */}
            <p className="text-gray-300 text-sm mb-4 line-clamp-2">
              {personality.description}
            </p>

            {/* Key Metrics */}
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <div className="text-gray-400 text-xs">Win Rate</div>
                <div className="text-white font-medium">{personality.metadata.performance.winRate.toFixed(1)}%</div>
              </div>
              <div>
                <div className="text-gray-400 text-xs">Experience</div>
                <div className="text-white font-medium">{personality.evolution.experienceLevel}/100</div>
              </div>
              <div>
                <div className="text-gray-400 text-xs">Trades</div>
                <div className="text-white font-medium">{personality.metadata.performance.totalTrades}</div>
              </div>
              <div>
                <div className="text-gray-400 text-xs">Avg P&L</div>
                <div className={`font-medium ${personality.metadata.performance.avgProfitPerTrade >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatCurrency(personality.metadata.performance.avgProfitPerTrade)}
                </div>
              </div>
            </div>

            {/* Risk Profile */}
            <div className="bg-gray-700 rounded p-3 mb-4">
              <div className="text-gray-400 text-xs mb-2">Risk Profile</div>
              <div className="flex justify-between items-center">
                <span className="text-white text-sm">
                  {personality.riskAppetite.baseRiskPerTrade.toFixed(1)}% per trade
                </span>
                <span className={`px-2 py-1 rounded text-xs ${
                  personality.riskAppetite.baseRiskPerTrade > 1.5 ? 'bg-red-900/30 text-red-400' :
                  personality.riskAppetite.baseRiskPerTrade > 1.0 ? 'bg-yellow-900/30 text-yellow-400' :
                  'bg-green-900/30 text-green-400'
                }`}>
                  {personality.riskAppetite.baseRiskPerTrade > 1.5 ? 'Aggressive' :
                   personality.riskAppetite.baseRiskPerTrade > 1.0 ? 'Moderate' : 'Conservative'}
                </span>
              </div>
            </div>

            {/* Trait Summary */}
            <div className="space-y-2">
              <div className="text-gray-400 text-xs">Key Traits</div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="bg-gray-700 rounded px-2 py-1 text-center">
                  <div className="text-gray-300">Risk</div>
                  <div className="text-white font-medium">{personality.traits.riskTolerance}</div>
                </div>
                <div className="bg-gray-700 rounded px-2 py-1 text-center">
                  <div className="text-gray-300">Disc</div>
                  <div className="text-white font-medium">{personality.traits.discipline}</div>
                </div>
                <div className="bg-gray-700 rounded px-2 py-1 text-center">
                  <div className="text-gray-300">Conf</div>
                  <div className="text-white font-medium">{personality.traits.confidence}</div>
                </div>
              </div>
            </div>

            {/* Active Sessions */}
            <div className="mt-4 pt-4 border-t border-gray-600">
              <div className="text-gray-400 text-xs mb-2">Active Sessions</div>
              <div className="flex gap-1">
                {personality.timePreferences.preferredSessions.map((session) => (
                  <span
                    key={session}
                    className="px-2 py-1 bg-blue-900/30 text-blue-400 rounded text-xs capitalize"
                  >
                    {session === 'newyork' ? 'NY' : session}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* No Results */}
      {filteredPersonalities.length === 0 && (
        <div className="bg-gray-750 rounded-lg p-8 text-center">
          <div className="text-gray-400 text-lg">No Personalities Found</div>
          <div className="text-gray-500 text-sm mt-2">
            Try adjusting your search criteria or create a new personality
          </div>
        </div>
      )}

      {/* Selected Personality Detail Panel */}
      {selectedPersonality && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden">
            {/* Modal Header */}
            <div className="flex justify-between items-center p-6 border-b border-gray-700">
              <div className="flex items-center gap-3">
                <div className="text-2xl">{getArchetypeIcon(selectedPersonality.metadata.archetype)}</div>
                <div>
                  <h3 className="text-xl font-bold text-white">{selectedPersonality.name}</h3>
                  <div className="text-gray-400 text-sm">{selectedPersonality.metadata.archetype.replace(/_/g, ' ')}</div>
                </div>
              </div>
              <button
                onClick={() => setSelectedPersonality(null)}
                className="text-gray-400 hover:text-white p-2 hover:bg-gray-700 rounded"
              >
                ✕
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-8rem)]">
              {/* Tab Navigation */}
              <div className="flex bg-gray-700 rounded-lg p-1 mb-6">
                {[
                  { id: 'overview', label: '📊 Overview' },
                  { id: 'details', label: '🎯 Details' },
                  { id: 'performance', label: '📈 Performance' },
                  { id: 'evolution', label: '🌱 Evolution' },
                  { id: 'settings', label: '⚙️ Settings' }
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as typeof activeTab)}
                    className={`flex-1 px-3 py-2 rounded text-sm transition-colors ${
                      activeTab === tab.id 
                        ? 'bg-blue-600 text-white' 
                        : 'text-gray-300 hover:text-white hover:bg-gray-600'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Tab Content */}
              {activeTab === 'overview' && (
                <div className="space-y-6">
                  {/* Quick Stats */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-gray-750 rounded-lg p-4">
                      <div className="text-gray-400 text-sm">Status</div>
                      <div className={`font-medium ${selectedPersonality.isActive ? 'text-green-400' : 'text-red-400'}`}>
                        {selectedPersonality.isActive ? 'Active' : 'Inactive'}
                      </div>
                    </div>
                    <div className="bg-gray-750 rounded-lg p-4">
                      <div className="text-gray-400 text-sm">Win Rate</div>
                      <div className="text-white font-medium">{selectedPersonality.metadata.performance.winRate.toFixed(1)}%</div>
                    </div>
                    <div className="bg-gray-750 rounded-lg p-4">
                      <div className="text-gray-400 text-sm">Total Trades</div>
                      <div className="text-white font-medium">{selectedPersonality.metadata.performance.totalTrades}</div>
                    </div>
                    <div className="bg-gray-750 rounded-lg p-4">
                      <div className="text-gray-400 text-sm">Experience</div>
                      <div className="text-white font-medium">{selectedPersonality.evolution.experienceLevel}/100</div>
                    </div>
                  </div>

                  {/* Description */}
                  <div className="bg-gray-750 rounded-lg p-4">
                    <h4 className="text-white font-medium mb-2">Description</h4>
                    <p className="text-gray-300">{selectedPersonality.description}</p>
                  </div>

                  {/* Personality Traits Radar */}
                  <div className="bg-gray-750 rounded-lg p-4">
                    <h4 className="text-white font-medium mb-4">Personality Traits</h4>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      {Object.entries(selectedPersonality.traits).map(([trait, value]) => (
                        <div key={trait} className="space-y-2">
                          <div className="flex justify-between">
                            <span className="text-gray-300 text-sm capitalize">{trait.replace(/([A-Z])/g, ' $1')}</span>
                            <span className="text-white text-sm font-medium">{value}</span>
                          </div>
                          <div className="w-full bg-gray-600 rounded-full h-2">
                            <div
                              className="bg-blue-500 h-2 rounded-full transition-all"
                              style={{ width: `${value}%` }}
                            ></div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'details' && (
                <div className="space-y-6">
                  {/* Currency Pairs */}
                  <div className="bg-gray-750 rounded-lg p-4">
                    <h4 className="text-white font-medium mb-4">Currency Pair Preferences</h4>
                    <div className="grid md:grid-cols-2 gap-6">
                      <div>
                        <h5 className="text-green-400 font-medium mb-3">Primary Pairs</h5>
                        <div className="space-y-3">
                          {selectedPersonality.pairPreferences.primary.map((pair) => (
                            <div key={pair.symbol} className="flex justify-between items-center bg-gray-700 rounded p-3">
                              <div>
                                <div className="text-white font-medium">{pair.symbol}</div>
                                <div className="text-gray-400 text-sm">{pair.frequency} trades/month</div>
                              </div>
                              <div className="text-right">
                                <div className="text-white text-sm">Strength: {pair.strength}</div>
                                <div className="text-gray-400 text-sm">Max: {pair.maxPositionSize}%</div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div>
                        <h5 className="text-blue-400 font-medium mb-3">Secondary Pairs</h5>
                        <div className="space-y-3">
                          {selectedPersonality.pairPreferences.secondary.map((pair) => (
                            <div key={pair.symbol} className="flex justify-between items-center bg-gray-700 rounded p-3">
                              <div>
                                <div className="text-white font-medium">{pair.symbol}</div>
                                <div className="text-gray-400 text-sm">{pair.frequency} trades/month</div>
                              </div>
                              <div className="text-right">
                                <div className="text-white text-sm">Strength: {pair.strength}</div>
                                <div className="text-gray-400 text-sm">Max: {pair.maxPositionSize}%</div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Trading Times */}
                  <div className="bg-gray-750 rounded-lg p-4">
                    <h4 className="text-white font-medium mb-4">Trading Time Preferences</h4>
                    <div className="grid md:grid-cols-2 gap-6">
                      <div>
                        <h5 className="text-gray-400 text-sm mb-3">Session Activity Levels</h5>
                        <div className="space-y-3">
                          {Object.entries(selectedPersonality.timePreferences.sessionActivity).map(([session, activity]) => (
                            <div key={session} className="space-y-2">
                              <div className="flex justify-between">
                                <span className="text-gray-300 capitalize">{session}</span>
                                <span className="text-white">{activity}%</span>
                              </div>
                              <div className="w-full bg-gray-600 rounded-full h-2">
                                <div
                                  className="bg-blue-500 h-2 rounded-full"
                                  style={{ width: `${activity}%` }}
                                ></div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div>
                        <h5 className="text-gray-400 text-sm mb-3">Active Hours</h5>
                        <div className="bg-gray-700 rounded p-3">
                          <div className="text-white text-lg">
                            {selectedPersonality.timePreferences.activeHours.start}:00 - {selectedPersonality.timePreferences.activeHours.end}:00
                          </div>
                          <div className="text-gray-400 text-sm">
                            {selectedPersonality.timePreferences.activeHours.timezone}
                          </div>
                        </div>
                        <div className="mt-4 space-y-2">
                          <div className="flex justify-between">
                            <span className="text-gray-300">Weekend Activity</span>
                            <span className="text-white">{selectedPersonality.timePreferences.weekendActivity}%</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-300">Holiday Activity</span>
                            <span className="text-white">{selectedPersonality.timePreferences.holidayActivity}%</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Add other tab content as needed */}
              {activeTab === 'performance' && (
                <div className="text-center py-8 text-gray-400">
                  Performance analytics panel coming soon...
                </div>
              )}

              {activeTab === 'evolution' && (
                <div className="text-center py-8 text-gray-400">
                  Evolution tracking panel coming soon...
                </div>
              )}

              {activeTab === 'settings' && (
                <div className="text-center py-8 text-gray-400">
                  Settings configuration panel coming soon...
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}