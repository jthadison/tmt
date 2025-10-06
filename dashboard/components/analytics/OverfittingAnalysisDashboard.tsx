'use client'

import { OverfittingAnalysis } from '@/app/api/analytics/overfitting-analysis/route'

interface Props {
  analysis: OverfittingAnalysis
}

export function OverfittingAnalysisDashboard({ analysis }: Props) {
  const riskConfig = {
    low: { color: 'text-emerald-500', bg: 'bg-emerald-500/10', label: 'Low Risk', border: 'border-emerald-500/30' },
    moderate: { color: 'text-amber-500', bg: 'bg-amber-500/10', label: 'Moderate Risk', border: 'border-amber-500/30' },
    high: { color: 'text-red-500', bg: 'bg-red-500/10', label: 'High Risk', border: 'border-red-500/30' }
  }

  const config = riskConfig[analysis.riskLevel]

  // Determine overfitting score color
  const getScoreColor = (score: number) => {
    if (score < 0.3) return 'text-emerald-500'
    if (score < 0.8) return 'text-amber-500'
    return 'text-red-500'
  }

  // Determine stability color
  const getStabilityColor = (score: number) => {
    if (score > 70) return 'text-emerald-500'
    if (score > 30) return 'text-amber-500'
    return 'text-red-500'
  }

  return (
    <div className="overfitting-analysis bg-card rounded-lg border border-border">
      <div className="p-4 border-b border-border">
        <h3 className="text-lg font-semibold text-foreground">Overfitting Analysis</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Strategy performance validation and overfitting detection
        </p>
      </div>

      <div className="p-6">
        {/* Score Summary */}
        <div className="score-summary grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="text-center p-4 bg-muted/20 rounded-lg">
            <div className="text-sm text-muted-foreground mb-2">Overfitting Score</div>
            <div className={`text-4xl font-bold ${getScoreColor(analysis.overfittingScore)}`}>
              {analysis.overfittingScore.toFixed(2)}
            </div>
            <div className="text-xs text-muted-foreground mt-2">0 = None, 1 = Severe</div>
          </div>

          <div className="text-center p-4 bg-muted/20 rounded-lg">
            <div className="text-sm text-muted-foreground mb-2">Avg Degradation</div>
            <div className="text-4xl font-bold text-red-500">
              {analysis.degradationPercentage.toFixed(1)}%
            </div>
            <div className="text-xs text-muted-foreground mt-2">Across all metrics</div>
          </div>

          <div className="text-center p-4 bg-muted/20 rounded-lg">
            <div className="text-sm text-muted-foreground mb-2">Risk Level</div>
            <div className={`inline-flex items-center px-4 py-2 rounded-lg ${config.bg} border ${config.border} mt-2`}>
              <span className={`text-lg font-semibold ${config.color}`}>
                {config.label}
              </span>
            </div>
          </div>
        </div>

        {/* Stability Score */}
        <div className="mb-6 p-4 bg-muted/20 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-foreground">Performance Stability</div>
              <div className="text-xs text-muted-foreground mt-1">
                Consistency of returns over time
              </div>
            </div>
            <div className="text-center">
              <div className={`text-3xl font-bold ${getStabilityColor(analysis.stabilityScore)}`}>
                {analysis.stabilityScore.toFixed(0)}
              </div>
              <div className="text-xs text-muted-foreground">/ 100</div>
            </div>
          </div>
          <div className="mt-3 h-2 bg-muted rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                analysis.stabilityScore > 70 ? 'bg-emerald-500' :
                analysis.stabilityScore > 30 ? 'bg-amber-500' : 'bg-red-500'
              }`}
              style={{ width: `${analysis.stabilityScore}%` }}
            />
          </div>
        </div>

        {/* Interpretation */}
        <div className={`interpretation p-4 rounded-lg border ${config.bg} ${config.border} mb-6`}>
          <div className="flex items-start gap-2">
            <span className={`text-xl ${config.color}`}>
              {analysis.riskLevel === 'low' ? '✓' : analysis.riskLevel === 'moderate' ? '⚠' : '✗'}
            </span>
            <p className={`text-sm ${config.color} leading-relaxed`}>{analysis.interpretation}</p>
          </div>
        </div>

        {/* Metric Degradation Breakdown */}
        <div className="metric-breakdown mb-6">
          <h4 className="font-semibold text-foreground mb-3">Metric Degradation Breakdown</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left p-2 font-medium text-muted-foreground">Metric</th>
                  <th className="text-right p-2 font-medium text-muted-foreground">Backtest</th>
                  <th className="text-right p-2 font-medium text-muted-foreground">Forward</th>
                  <th className="text-right p-2 font-medium text-muted-foreground">Change</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(analysis.metricDegradation).map(([metric, data]) => (
                  <tr key={metric} className="border-b border-border/50 hover:bg-muted/20 transition-colors">
                    <td className="p-2 capitalize text-foreground">
                      {metric.replace(/([A-Z])/g, ' $1').trim()}
                    </td>
                    <td className="p-2 text-right font-mono text-muted-foreground">
                      {data.backtest.toFixed(2)}
                    </td>
                    <td className="p-2 text-right font-mono text-foreground">
                      {data.forward.toFixed(2)}
                    </td>
                    <td className={`p-2 text-right font-semibold ${
                      data.degradation < 0 ? 'text-red-500' : 'text-emerald-500'
                    }`}>
                      {data.degradation > 0 ? '+' : ''}{data.degradation.toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recommendations */}
        {analysis.recommendations.length > 0 && (
          <div className="recommendations">
            <h4 className="font-semibold text-foreground mb-3 flex items-center gap-2">
              <span className="text-blue-500">💡</span>
              Recommendations
            </h4>
            <ul className="space-y-2">
              {analysis.recommendations.map((rec, index) => (
                <li key={index} className="flex items-start gap-3 p-3 bg-muted/20 rounded-lg hover:bg-muted/30 transition-colors">
                  <span className="text-blue-500 mt-0.5 font-bold">•</span>
                  <span className="text-sm text-foreground leading-relaxed">{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
