/**
 * Test utilities and mock data for session monitoring components
 */

export const mockForwardTestMetrics = {
  walkForwardStability: 34.4,
  outOfSampleValidation: 17.4,
  overfittingScore: 0.634,
  kurtosisExposure: 20.316,
  monthsOfData: 6
}

export const mockGoodForwardTestMetrics = {
  walkForwardStability: 75.5,
  outOfSampleValidation: 68.2,
  overfittingScore: 0.25,
  kurtosisExposure: 8.5,
  monthsOfData: 12
}

export const createMockSessionData = (overrides: Partial<any> = {}) => ({
  session: 'london' as const,
  name: 'London Session',
  timezone: 'GMT (UTC+0)',
  hours: '07:00-16:00 GMT',
  status: 'active' as const,
  metrics: {
    winRate: 72.1,
    avgRiskReward: 3.2,
    totalTrades: 62,
    profitFactor: 1.85,
    maxDrawdown: -2.8,
    confidenceThreshold: 72,
    positionSizeReduction: 28,
    currentPhase: 3,
    capitalAllocation: 50,
    ...overrides.metrics
  },
  recentTrades: [
    {
      id: '1',
      type: 'BUY',
      pair: 'EUR/USD',
      size: 10000,
      time: '14:30',
      pnl: 125.50,
      entry: 1.0850,
      exit: 1.0875,
      duration: '2h 15m'
    },
    {
      id: '2',
      type: 'SELL',
      pair: 'GBP/USD',
      size: 8500,
      time: '13:45',
      pnl: -45.25,
      entry: 1.2650,
      exit: 1.2665,
      duration: '45m'
    }
  ],
  positionSizing: {
    stabilityFactor: 0.55,
    validationFactor: 0.35,
    volatilityFactor: 0.95,
    totalReduction: 0.28,
    maxPosition: 4.0,
    currentRisk: 1.2,
    ...overrides.positionSizing
  },
  ...overrides
})

export const mockMultipleSessionData = [
  createMockSessionData({
    session: 'sydney',
    name: 'Sydney Session',
    timezone: 'AEDT (UTC+11)',
    hours: '22:00-07:00 GMT',
    status: 'inactive',
    metrics: {
      winRate: 65.2,
      avgRiskReward: 2.8,
      totalTrades: 45,
      profitFactor: 1.45,
      maxDrawdown: -4.2,
      confidenceThreshold: 78,
      positionSizeReduction: 35,
      currentPhase: 2,
      capitalAllocation: 25
    },
    positionSizing: {
      stabilityFactor: 0.45,
      validationFactor: 0.25,
      volatilityFactor: 0.85,
      totalReduction: 0.35,
      maxPosition: 2.5,
      currentRisk: 0.75
    }
  }),
  createMockSessionData({
    session: 'tokyo',
    name: 'Tokyo Session',
    timezone: 'JST (UTC+9)',
    hours: '00:00-09:00 GMT',
    status: 'upcoming',
    metrics: {
      winRate: 85.0,
      avgRiskReward: 4.0,
      totalTrades: 38,
      profitFactor: 2.15,
      maxDrawdown: -1.5,
      confidenceThreshold: 85,
      positionSizeReduction: 15,
      currentPhase: 4,
      capitalAllocation: 100
    },
    positionSizing: {
      stabilityFactor: 0.75,
      validationFactor: 0.65,
      volatilityFactor: 1.0,
      totalReduction: 0.15,
      maxPosition: 8.0,
      currentRisk: 2.0
    }
  }),
  createMockSessionData(), // London (default)
  createMockSessionData({
    session: 'new_york',
    name: 'New York Session',
    timezone: 'EST (UTC-5)',
    hours: '13:00-22:00 GMT',
    status: 'upcoming',
    metrics: {
      winRate: 70.5,
      avgRiskReward: 2.8,
      totalTrades: 58,
      profitFactor: 1.65,
      maxDrawdown: -3.5,
      confidenceThreshold: 70,
      positionSizeReduction: 32,
      currentPhase: 3,
      capitalAllocation: 50
    },
    positionSizing: {
      stabilityFactor: 0.50,
      validationFactor: 0.30,
      volatilityFactor: 0.90,
      totalReduction: 0.32,
      maxPosition: 3.8,
      currentRisk: 1.1
    }
  }),
  createMockSessionData({
    session: 'overlap',
    name: 'Overlap Sessions',
    timezone: 'GMT (UTC+0)',
    hours: '13:00-16:00, 00:00-02:00 GMT',
    status: 'inactive',
    metrics: {
      winRate: 68.8,
      avgRiskReward: 2.9,
      totalTrades: 28,
      profitFactor: 1.58,
      maxDrawdown: -2.9,
      confidenceThreshold: 70,
      positionSizeReduction: 30,
      currentPhase: 3,
      capitalAllocation: 50
    },
    positionSizing: {
      stabilityFactor: 0.52,
      validationFactor: 0.32,
      volatilityFactor: 0.92,
      totalReduction: 0.30,
      maxPosition: 4.2,
      currentRisk: 1.3
    }
  })
]

export const mockFetchSuccess = (data: any) => {
  return jest.fn().mockResolvedValue({
    ok: true,
    json: async () => data
  })
}

export const mockFetchError = (error: string = 'API Error') => {
  return jest.fn().mockRejectedValue(new Error(error))
}

export const mockFetchFailure = (status: number = 500, statusText: string = 'Internal Server Error') => {
  return jest.fn().mockResolvedValue({
    ok: false,
    status,
    statusText
  })
}

export const expectMetricColorClass = (element: HTMLElement, metric: number, thresholds: { good: number, ok: number }) => {
  if (metric >= thresholds.good) {
    expect(element).toHaveClass('text-green-400')
  } else if (metric >= thresholds.ok) {
    expect(element).toHaveClass('text-yellow-400')
  } else {
    expect(element).toHaveClass('text-red-400')
  }
}

export const expectFactorColorClass = (element: HTMLElement, factor: number) => {
  if (factor > 0.8) {
    expect(element).toHaveClass('text-green-400')
  } else if (factor > 0.5) {
    expect(element).toHaveClass('text-yellow-400')
  } else {
    expect(element).toHaveClass('text-red-400')
  }
}

export const expectProgressBarColor = (element: HTMLElement, factor: number) => {
  if (factor > 0.8) {
    expect(element).toHaveClass('bg-green-500')
  } else if (factor > 0.5) {
    expect(element).toHaveClass('bg-yellow-500')
  } else {
    expect(element).toHaveClass('bg-red-500')
  }
}

export const createMockTrade = (overrides: Partial<any> = {}) => ({
  id: '1',
  type: 'BUY',
  pair: 'EUR/USD',
  size: 10000,
  time: '14:30',
  pnl: 125.50,
  entry: 1.0850,
  exit: 1.0875,
  duration: '2h 15m',
  ...overrides
})

export const waitForAsyncUpdates = () => new Promise(resolve => setTimeout(resolve, 0))

export const mockTimezone = (date: string) => {
  jest.useFakeTimers()
  jest.setSystemTime(new Date(date))
  return () => jest.useRealTimers()
}

export const sessionTimeTests = {
  sydney: '2024-01-15T02:00:00.000Z',    // 02:00 GMT - Sydney active
  tokyo: '2024-01-15T05:00:00.000Z',     // 05:00 GMT - Tokyo active
  london: '2024-01-15T10:00:00.000Z',    // 10:00 GMT - London active
  newYork: '2024-01-15T18:00:00.000Z',   // 18:00 GMT - New York active
  overlap: '2024-01-15T14:00:00.000Z'    // 14:00 GMT - London/NY overlap
}