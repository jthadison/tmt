'use client'

import React, { useState } from 'react'
import Card from '@/components/ui/Card'

type TradingSession = 'sydney' | 'tokyo' | 'london' | 'new_york' | 'overlap'

interface SessionData {
  session: TradingSession
  name: string
  positionSizing: {
    stabilityFactor: number
    validationFactor: number
    volatilityFactor: number
    totalReduction: number
    maxPosition: number
    currentRisk: number
  }
  metrics: {
    positionSizeReduction: number
    currentPhase: number
    capitalAllocation: number
  }
}

interface PositionSizingMonitorProps {
  sessionData: SessionData[]
  currentSession: TradingSession
}

const PositionSizingMonitor: React.FC<PositionSizingMonitorProps> = ({
  sessionData,
  currentSession
}) => {
  const [selectedFactorView, setSelectedFactorView] = useState<'all' | 'stability' | 'validation' | 'volatility'>('all')

  const currentSessionData = sessionData.find(s => s.session === currentSession)

  if (!currentSessionData) return null

  const ForwardTestMetrics = {
    walkForwardStability: 34.4,
    outOfSampleValidation: 17.4,
    overfittingScore: 0.634,
    kurtosisExposure: 20.316,
    monthsOfData: 6
  }

  const getFactorColor = (factor: number) => {
    if (factor > 0.8) return 'text-green-400'
    if (factor > 0.5) return 'text-yellow-400'
    return 'text-red-400'
  }

  const getFactorBgColor = (factor: number) => {
    if (factor > 0.8) return 'bg-green-500'
    if (factor > 0.5) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const getPhaseInfo = (phase: number) => {
    switch (phase) {
      case 1: return { label: 'Phase 1', capital: 10, requirements: 'Stability ≥50, Validation ≥50' }
      case 2: return { label: 'Phase 2', capital: 25, requirements: 'Stability ≥60, Validation ≥60' }
      case 3: return { label: 'Phase 3', capital: 50, requirements: 'Stability ≥70, Validation ≥70' }
      case 4: return { label: 'Phase 4', capital: 100, requirements: 'Stability ≥80, Validation ≥80' }
      default: return { label: 'Phase 1', capital: 10, requirements: 'Stability ≥50, Validation ≥50' }
    }
  }

  const phaseInfo = getPhaseInfo(currentSessionData.metrics.currentPhase)

  // Calculate what the position size would be without reductions
  const basePositionSize = 10000 // Example base size
  const adjustedSize = basePositionSize * currentSessionData.positionSizing.totalReduction

  return (
    <Card
      title={
        <div className="flex items-center justify-between">
          <span>Position Sizing Monitor - {currentSessionData.name}</span>
          <div className="flex space-x-1">
            {(['all', 'stability', 'validation', 'volatility'] as const).map((view) => (
              <button
                key={view}
                onClick={() => setSelectedFactorView(view)}
                className={`px-2 py-1 text-xs rounded transition-colors capitalize ${
                  selectedFactorView === view
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                }`}
              >
                {view}
              </button>
            ))}
          </div>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Position Size Impact Visualization */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-gray-300">Position Size Impact</h4>
            <div className="text-xs text-gray-500">
              Base → Adjusted Size
            </div>
          </div>

          <div className="bg-gray-800 p-4 rounded">
            <div className="flex items-center space-x-4 mb-4">
              <div className="text-center">
                <div className="text-xs text-gray-400 mb-1">Base Size</div>
                <div className="text-lg font-bold text-blue-400">
                  {basePositionSize.toLocaleString()}
                </div>
                <div className="text-xs text-gray-500">units</div>
              </div>

              <div className="flex-1 flex items-center space-x-2">
                <div className="flex-1 bg-gray-700 rounded-full h-3">
                  <div
                    className="bg-red-500 h-3 rounded-full transition-all relative"
                    style={{ width: `${(1 - currentSessionData.positionSizing.totalReduction) * 100}%` }}
                  >
                    <div className="absolute -top-6 right-0 text-xs text-red-400 font-bold">
                      -{((1 - currentSessionData.positionSizing.totalReduction) * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>
              </div>

              <div className="text-center">
                <div className="text-xs text-gray-400 mb-1">Final Size</div>
                <div className="text-lg font-bold text-red-400">
                  {adjustedSize.toLocaleString()}
                </div>
                <div className="text-xs text-gray-500">units</div>
              </div>
            </div>

            <div className="grid grid-cols-4 gap-2 text-xs">
              <div className="text-center">
                <div className="text-gray-400">Total Reduction</div>
                <div className="text-red-400 font-bold">
                  {((1 - currentSessionData.positionSizing.totalReduction) * 100).toFixed(1)}%
                </div>
              </div>
              <div className="text-center">
                <div className="text-gray-400">Max Position</div>
                <div className="text-blue-400 font-bold">
                  {currentSessionData.positionSizing.maxPosition}%
                </div>
              </div>
              <div className="text-center">
                <div className="text-gray-400">Risk Per Trade</div>
                <div className="text-yellow-400 font-bold">
                  {currentSessionData.positionSizing.currentRisk}%
                </div>
              </div>
              <div className="text-center">
                <div className="text-gray-400">Capital Phase</div>
                <div className="text-orange-400 font-bold">
                  {currentSessionData.metrics.capitalAllocation}%
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Reduction Factor Breakdown */}
        {(selectedFactorView === 'all' || selectedFactorView === 'stability') && (
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-gray-300">Stability Factor Impact</h4>
            <div className="bg-gray-800 p-4 rounded">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <span className="text-sm text-gray-400">Walk-Forward Stability: </span>
                  <span className="text-white font-bold">{ForwardTestMetrics.walkForwardStability}/100</span>
                </div>
                <div className={`text-sm font-bold px-2 py-1 rounded ${
                  currentSessionData.positionSizing.stabilityFactor > 0.5 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-red-500/20 text-red-400'
                }`}>
                  LOW STABILITY
                </div>
              </div>

              <div className="flex items-center space-x-4">
                <div className="flex-1 bg-gray-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${getFactorBgColor(currentSessionData.positionSizing.stabilityFactor)}`}
                    style={{ width: `${currentSessionData.positionSizing.stabilityFactor * 100}%` }}
                  ></div>
                </div>
                <div className={`text-sm font-bold ${getFactorColor(currentSessionData.positionSizing.stabilityFactor)}`}>
                  {(currentSessionData.positionSizing.stabilityFactor * 100).toFixed(0)}%
                </div>
              </div>

              <div className="text-xs text-gray-500 mt-2">
                Reduces position size by {((1 - currentSessionData.positionSizing.stabilityFactor) * 100).toFixed(0)}% due to poor walk-forward performance
              </div>
            </div>
          </div>
        )}

        {(selectedFactorView === 'all' || selectedFactorView === 'validation') && (
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-gray-300">Validation Factor Impact</h4>
            <div className="bg-gray-800 p-4 rounded">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <span className="text-sm text-gray-400">Out-of-Sample Validation: </span>
                  <span className="text-white font-bold">{ForwardTestMetrics.outOfSampleValidation}/100</span>
                </div>
                <div className="text-sm font-bold px-2 py-1 rounded bg-red-500/20 text-red-400">
                  POOR VALIDATION
                </div>
              </div>

              <div className="flex items-center space-x-4">
                <div className="flex-1 bg-gray-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${getFactorBgColor(currentSessionData.positionSizing.validationFactor)}`}
                    style={{ width: `${currentSessionData.positionSizing.validationFactor * 100}%` }}
                  ></div>
                </div>
                <div className={`text-sm font-bold ${getFactorColor(currentSessionData.positionSizing.validationFactor)}`}>
                  {(currentSessionData.positionSizing.validationFactor * 100).toFixed(0)}%
                </div>
              </div>

              <div className="text-xs text-gray-500 mt-2">
                Reduces position size by {((1 - currentSessionData.positionSizing.validationFactor) * 100).toFixed(0)}% due to poor out-of-sample results
              </div>
            </div>
          </div>
        )}

        {(selectedFactorView === 'all' || selectedFactorView === 'volatility') && (
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-gray-300">Volatility Factor Impact</h4>
            <div className="bg-gray-800 p-4 rounded">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <span className="text-sm text-gray-400">Market Volatility: </span>
                  <span className="text-white font-bold">Normal</span>
                </div>
                <div className="text-sm font-bold px-2 py-1 rounded bg-blue-500/20 text-blue-400">
                  NORMAL VOLATILITY
                </div>
              </div>

              <div className="flex items-center space-x-4">
                <div className="flex-1 bg-gray-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${getFactorBgColor(currentSessionData.positionSizing.volatilityFactor)}`}
                    style={{ width: `${currentSessionData.positionSizing.volatilityFactor * 100}%` }}
                  ></div>
                </div>
                <div className={`text-sm font-bold ${getFactorColor(currentSessionData.positionSizing.volatilityFactor)}`}>
                  {(currentSessionData.positionSizing.volatilityFactor * 100).toFixed(0)}%
                </div>
              </div>

              <div className="text-xs text-gray-500 mt-2">
                {currentSessionData.positionSizing.volatilityFactor >= 1.0
                  ? 'Normal volatility - no size reduction applied'
                  : `Reduces position size by ${((1 - currentSessionData.positionSizing.volatilityFactor) * 100).toFixed(0)}% due to elevated volatility`
                }
              </div>
            </div>
          </div>
        )}

        {/* Capital Allocation Phase */}
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-gray-300">Capital Allocation Phase</h4>
          <div className="bg-gray-800 p-4 rounded">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-lg font-bold text-orange-400">{phaseInfo.label}</div>
                <div className="text-sm text-gray-400">{phaseInfo.requirements}</div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-orange-400">{phaseInfo.capital}%</div>
                <div className="text-xs text-gray-400">Capital Allocation</div>
              </div>
            </div>

            {/* Phase Progress Indicators */}
            <div className="grid grid-cols-4 gap-2">
              {[1, 2, 3, 4].map((phase) => (
                <div
                  key={phase}
                  className={`text-center p-2 rounded transition-all ${
                    phase <= currentSessionData.metrics.currentPhase
                      ? 'bg-orange-500/20 border border-orange-500/50'
                      : 'bg-gray-700 border border-gray-600'
                  }`}
                >
                  <div className={`text-xs font-bold ${
                    phase <= currentSessionData.metrics.currentPhase ? 'text-orange-400' : 'text-gray-500'
                  }`}>
                    Phase {phase}
                  </div>
                  <div className={`text-xs ${
                    phase <= currentSessionData.metrics.currentPhase ? 'text-orange-300' : 'text-gray-600'
                  }`}>
                    {[10, 25, 50, 100][phase - 1]}%
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded">
              <div className="text-sm text-yellow-400 font-medium mb-1">⚠️ Phase Advancement Requirements</div>
              <div className="text-xs text-gray-300">
                To advance to Phase {currentSessionData.metrics.currentPhase + 1}: Walk-forward stability ≥{50 + (currentSessionData.metrics.currentPhase * 10)}
                and out-of-sample validation ≥{50 + (currentSessionData.metrics.currentPhase * 10)}
              </div>
              <div className="text-xs text-gray-400 mt-1">
                Current: Stability {ForwardTestMetrics.walkForwardStability}, Validation {ForwardTestMetrics.outOfSampleValidation}
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="flex flex-wrap gap-2">
          <button className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded transition-colors">
            Update Metrics
          </button>
          <button className="px-3 py-2 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded transition-colors">
            View Forward Tests
          </button>
          <button className="px-3 py-2 bg-yellow-600 hover:bg-yellow-700 text-white text-sm rounded transition-colors">
            Emergency Rollback
          </button>
          <button className="px-3 py-2 bg-green-600 hover:bg-green-700 text-white text-sm rounded transition-colors">
            Export Report
          </button>
        </div>
      </div>
    </Card>
  )
}

export default PositionSizingMonitor