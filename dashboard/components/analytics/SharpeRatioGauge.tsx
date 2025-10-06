/**
 * Sharpe Ratio Gauge Component - Story 8.1
 * Semi-circular gauge with color-coded thresholds
 */

'use client'

import React from 'react'

interface SharpeRatioGaugeProps {
  value: number
  thresholdLevel: 'outstanding' | 'excellent' | 'good' | 'acceptable' | 'poor'
  interpretation: string
}

interface ThresholdConfig {
  color: string
  label: string
  min: number
}

const thresholdConfigs: Record<string, ThresholdConfig> = {
  outstanding: { color: '#059669', label: 'Outstanding', min: 2.0 },
  excellent: { color: '#10b981', label: 'Excellent', min: 1.5 },
  good: { color: '#eab308', label: 'Good', min: 1.0 },
  acceptable: { color: '#f59e0b', label: 'Acceptable', min: 0.5 },
  poor: { color: '#ef4444', label: 'Poor', min: 0 },
}

interface GaugeArcProps {
  startAngle: number
  endAngle: number
  color: string
  opacity: number
}

const GaugeArc: React.FC<GaugeArcProps> = ({ startAngle, endAngle, color, opacity }) => {
  const centerX = 100
  const centerY = 100
  const radius = 70
  const thickness = 15

  // Convert angles to radians (0 degrees = right, counter-clockwise)
  const startRad = ((180 - startAngle) * Math.PI) / 180
  const endRad = ((180 - endAngle) * Math.PI) / 180

  // Calculate path coordinates
  const outerStartX = centerX + radius * Math.cos(startRad)
  const outerStartY = centerY - radius * Math.sin(startRad)
  const outerEndX = centerX + radius * Math.cos(endRad)
  const outerEndY = centerY - radius * Math.sin(endRad)

  const innerRadius = radius - thickness
  const innerStartX = centerX + innerRadius * Math.cos(startRad)
  const innerStartY = centerY - innerRadius * Math.sin(startRad)
  const innerEndX = centerX + innerRadius * Math.cos(endRad)
  const innerEndY = centerY - innerRadius * Math.sin(endRad)

  const largeArcFlag = endAngle - startAngle > 180 ? 1 : 0

  const pathData = `
    M ${outerStartX} ${outerStartY}
    A ${radius} ${radius} 0 ${largeArcFlag} 0 ${outerEndX} ${outerEndY}
    L ${innerEndX} ${innerEndY}
    A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 1 ${innerStartX} ${innerStartY}
    Z
  `

  return <path d={pathData} fill={color} opacity={opacity} />
}

export const SharpeRatioGauge: React.FC<SharpeRatioGaugeProps> = ({
  value,
  thresholdLevel,
  interpretation,
}) => {
  const config = thresholdConfigs[thresholdLevel]

  // Calculate needle angle (0-180 degrees for 0-3 scale)
  const clampedValue = Math.max(0, Math.min(3, value))
  const angle = (clampedValue / 3) * 180

  // Calculate needle end point
  const centerX = 100
  const centerY = 100
  const needleLength = 60
  const needleRad = ((180 - angle) * Math.PI) / 180
  const needleEndX = centerX + needleLength * Math.cos(needleRad)
  const needleEndY = centerY - needleLength * Math.sin(needleRad)

  return (
    <div className="sharpe-ratio-gauge w-full">
      {/* Gauge SVG */}
      <svg viewBox="0 0 200 120" className="w-full max-w-md mx-auto">
        {/* Background arcs (threshold bands) */}
        <GaugeArc startAngle={0} endAngle={30} color="#ef4444" opacity={0.3} />
        <GaugeArc startAngle={30} endAngle={60} color="#f59e0b" opacity={0.3} />
        <GaugeArc startAngle={60} endAngle={90} color="#eab308" opacity={0.3} />
        <GaugeArc startAngle={90} endAngle={150} color="#10b981" opacity={0.3} />
        <GaugeArc startAngle={150} endAngle={180} color="#059669" opacity={0.3} />

        {/* Needle */}
        <g>
          <line
            x1={centerX}
            y1={centerY}
            x2={needleEndX}
            y2={needleEndY}
            stroke={config.color}
            strokeWidth="3"
            strokeLinecap="round"
          />
          <circle cx={centerX} cy={centerY} r="5" fill={config.color} />
        </g>

        {/* Value labels */}
        <text x="25" y="115" fontSize="10" fill="currentColor" className="fill-muted-foreground">
          0
        </text>
        <text x="95" y="25" fontSize="10" fill="currentColor" className="fill-muted-foreground">
          1.5
        </text>
        <text x="170" y="115" fontSize="10" fill="currentColor" className="fill-muted-foreground">
          3
        </text>

        {/* Threshold markers */}
        <circle cx="25" cy="105" r="2" fill="#ef4444" />
        <circle cx="62" cy="50" r="2" fill="#f59e0b" />
        <circle cx="100" cy="30" r="2" fill="#eab308" />
        <circle cx="138" cy="50" r="2" fill="#10b981" />
        <circle cx="175" cy="105" r="2" fill="#059669" />
      </svg>

      {/* Value display */}
      <div className="text-center mt-4">
        <div className="text-4xl font-bold" style={{ color: config.color }}>
          {value.toFixed(2)}
        </div>
        <div className="text-lg font-semibold mt-1" style={{ color: config.color }}>
          {config.label}
        </div>
        <div className="text-sm text-muted-foreground mt-2 px-4">{interpretation}</div>
      </div>

      {/* Threshold legend */}
      <div className="threshold-legend mt-6">
        <div className="grid grid-cols-5 gap-2 text-xs">
          {Object.entries(thresholdConfigs).map(([key, cfg]) => (
            <div key={key} className="flex flex-col items-center gap-1">
              <div className="w-4 h-4 rounded" style={{ backgroundColor: cfg.color }} />
              <span className="text-muted-foreground">{cfg.label}</span>
              <span className="text-muted-foreground text-[10px]">
                {cfg.min === 0 ? '<0.5' : `>${cfg.min}`}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
