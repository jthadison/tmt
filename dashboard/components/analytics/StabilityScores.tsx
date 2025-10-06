/**
 * Stability Scores Component - Story 8.1
 * Walk-forward stability and overfitting analysis
 */

'use client'

import React from 'react'
import { StabilityMetrics } from '@/types/analytics'
import { TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react'

interface StabilityScoresProps {
  metrics: StabilityMetrics
}

export const StabilityScores: React.FC<StabilityScoresProps> = ({ metrics }) => {
  const { walkForwardScore, overfittingScore, outOfSampleValidation } = metrics

  const getWalkForwardColor = (score: number) => {
    if (score > 70) return 'bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20'
    if (score > 30)
      return 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/20'
    return 'bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20'
  }

  const getOverfittingColor = (score: number) => {
    if (score < 0.3) return 'bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20'
    if (score < 0.8)
      return 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/20'
    return 'bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20'
  }

  const getWalkForwardIcon = (score: number) => {
    if (score > 70) return <CheckCircle className="w-6 h-6" />
    if (score > 30) return <AlertTriangle className="w-6 h-6" />
    return <AlertTriangle className="w-6 h-6" />
  }

  const getOverfittingIcon = (score: number) => {
    if (score < 0.3) return <CheckCircle className="w-6 h-6" />
    if (score < 0.8) return <AlertTriangle className="w-6 h-6" />
    return <AlertTriangle className="w-6 h-6" />
  }

  const getWalkForwardInterpretation = (score: number) => {
    if (score > 70) return 'Excellent consistency across time periods'
    if (score > 30) return 'Acceptable performance stability'
    return 'Needs improvement - inconsistent performance'
  }

  const getOverfittingInterpretation = (score: number) => {
    if (score < 0.3) return 'Low overfitting risk - good generalization'
    if (score < 0.8) return 'Moderate overfitting risk - monitor closely'
    return 'High overfitting risk - strategy may not generalize'
  }

  const getValidationInterpretation = (score: number) => {
    if (score > 85) return 'Strong generalization to unseen data'
    if (score > 70) return 'Good out-of-sample performance'
    return 'Limited out-of-sample validation'
  }

  return (
    <div className="stability-scores">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Walk-Forward Stability */}
        <div
          className={`score-card p-6 rounded-lg border ${getWalkForwardColor(walkForwardScore)}`}
        >
          <div className="flex items-start justify-between mb-3">
            <h4 className="text-sm font-medium">Walk-Forward Stability</h4>
            {getWalkForwardIcon(walkForwardScore)}
          </div>

          <div className="text-4xl font-bold mb-2">{walkForwardScore.toFixed(0)}</div>

          <div className="text-xs opacity-90 mb-3">
            {getWalkForwardInterpretation(walkForwardScore)}
          </div>

          {/* Progress bar */}
          <div className="w-full bg-black/10 dark:bg-white/10 rounded-full h-2">
            <div
              className="h-2 rounded-full transition-all duration-500"
              style={{
                width: `${walkForwardScore}%`,
                backgroundColor: 'currentColor',
              }}
            />
          </div>

          <div className="mt-3 text-xs opacity-75">
            {walkForwardScore > 70 && '✓ Performance consistent over time'}
            {walkForwardScore <= 70 && walkForwardScore > 30 && '⚠ Some performance variation'}
            {walkForwardScore <= 30 && '✗ High performance inconsistency'}
          </div>
        </div>

        {/* Overfitting Score */}
        <div className={`score-card p-6 rounded-lg border ${getOverfittingColor(overfittingScore)}`}>
          <div className="flex items-start justify-between mb-3">
            <h4 className="text-sm font-medium">Overfitting Score</h4>
            {getOverfittingIcon(overfittingScore)}
          </div>

          <div className="text-4xl font-bold mb-2">{overfittingScore.toFixed(2)}</div>

          <div className="text-xs opacity-90 mb-3">
            {getOverfittingInterpretation(overfittingScore)}
          </div>

          {/* Progress bar (inverted - lower is better) */}
          <div className="w-full bg-black/10 dark:bg-white/10 rounded-full h-2">
            <div
              className="h-2 rounded-full transition-all duration-500"
              style={{
                width: `${Math.min(100, overfittingScore * 100)}%`,
                backgroundColor: 'currentColor',
              }}
            />
          </div>

          <div className="mt-3 text-xs opacity-75">
            {overfittingScore < 0.3 && '✓ Low overfitting risk'}
            {overfittingScore >= 0.3 && overfittingScore < 0.8 && '⚠ Moderate overfitting risk'}
            {overfittingScore >= 0.8 && '✗ High overfitting detected'}
          </div>
        </div>

        {/* Out-of-Sample Validation */}
        <div className="score-card p-6 rounded-lg border bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20">
          <div className="flex items-start justify-between mb-3">
            <h4 className="text-sm font-medium">Out-of-Sample Validation</h4>
            <TrendingUp className="w-6 h-6" />
          </div>

          <div className="text-4xl font-bold mb-2">{outOfSampleValidation.toFixed(0)}%</div>

          <div className="text-xs opacity-90 mb-3">
            {getValidationInterpretation(outOfSampleValidation)}
          </div>

          {/* Progress bar */}
          <div className="w-full bg-black/10 dark:bg-white/10 rounded-full h-2">
            <div
              className="h-2 rounded-full transition-all duration-500"
              style={{
                width: `${outOfSampleValidation}%`,
                backgroundColor: 'currentColor',
              }}
            />
          </div>

          <div className="mt-3 text-xs opacity-75">
            {outOfSampleValidation > 85 && '✓ Strong generalization'}
            {outOfSampleValidation <= 85 && outOfSampleValidation > 70 && '✓ Good validation'}
            {outOfSampleValidation <= 70 && '⚠ Limited validation'}
          </div>
        </div>
      </div>

      {/* Explanation section */}
      <div className="mt-6 p-4 bg-muted/50 rounded-lg border border-border">
        <h5 className="text-sm font-semibold mb-2">Understanding These Metrics</h5>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-muted-foreground">
          <div>
            <strong className="text-foreground">Walk-Forward Stability:</strong> Measures how
            consistent your trading performance is across different time periods. Higher scores
            indicate more reliable results.
          </div>
          <div>
            <strong className="text-foreground">Overfitting Score:</strong> Indicates whether your
            strategy is too closely fitted to historical data. Lower scores are better, showing your
            strategy can adapt to new market conditions.
          </div>
          <div>
            <strong className="text-foreground">Out-of-Sample Validation:</strong> Shows what
            percentage of your in-sample performance is retained on unseen data. Higher percentages
            indicate better generalization.
          </div>
        </div>
      </div>
    </div>
  )
}
