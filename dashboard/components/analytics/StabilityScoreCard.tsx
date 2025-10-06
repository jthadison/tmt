'use client'

interface Props {
  score: number
  className?: string
}

export function StabilityScoreCard({ score, className = '' }: Props) {
  const getScoreColor = (score: number) => {
    if (score > 70) return {
      color: 'text-emerald-500',
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/30',
      progressBg: 'bg-emerald-500'
    }
    if (score > 30) return {
      color: 'text-amber-500',
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/30',
      progressBg: 'bg-amber-500'
    }
    return {
      color: 'text-red-500',
      bg: 'bg-red-500/10',
      border: 'border-red-500/30',
      progressBg: 'bg-red-500'
    }
  }

  const getStabilityLabel = (score: number) => {
    if (score > 70) return 'Stable'
    if (score > 30) return 'Moderate'
    return 'Unstable'
  }

  const colors = getScoreColor(score)
  const label = getStabilityLabel(score)

  return (
    <div className={`stability-score-card bg-card rounded-lg border border-border p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="text-sm font-medium text-muted-foreground">Performance Stability</h4>
          <p className="text-xs text-muted-foreground mt-1">Consistency over time periods</p>
        </div>
        <div className={`px-3 py-1 rounded-full ${colors.bg} border ${colors.border}`}>
          <span className={`text-sm font-semibold ${colors.color}`}>{label}</span>
        </div>
      </div>

      <div className="flex items-end gap-4 mb-4">
        <div className={`text-5xl font-bold ${colors.color}`}>
          {score.toFixed(0)}
        </div>
        <div className="text-muted-foreground mb-2">
          <span className="text-lg">/ 100</span>
        </div>
      </div>

      <div className="space-y-2">
        <div className="h-3 bg-muted rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${colors.progressBg}`}
            style={{ width: `${score}%` }}
          />
        </div>

        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Unstable ({`<`}30)</span>
          <span>Moderate (30-70)</span>
          <span>Stable ({`>`}70)</span>
        </div>
      </div>

      <div className={`mt-4 p-3 rounded-lg ${colors.bg} border ${colors.border}`}>
        <p className={`text-xs ${colors.color}`}>
          {score > 70 && 'Strategy shows consistent performance across different time periods with low variance.'}
          {score > 30 && score <= 70 && 'Strategy shows moderate performance consistency. Monitor for increased volatility.'}
          {score <= 30 && 'Strategy shows unstable performance with high variance. Consider reducing exposure or reviewing strategy parameters.'}
        </p>
      </div>
    </div>
  )
}
