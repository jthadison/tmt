/**
 * Mini Sparkline Component
 * Displays a compact SVG line chart showing P&L trend
 */

import React from 'react'

interface MiniSparklineProps {
  /** Array of P&L values for the sparkline */
  data: number[]
  /** Width in pixels */
  width?: number
  /** Height in pixels */
  height?: number
  /** Optional CSS class name */
  className?: string
}

/**
 * Mini sparkline component for P&L trend visualization
 */
export function MiniSparkline({
  data,
  width = 80,
  height = 30,
  className = '',
}: MiniSparklineProps) {
  // Need at least 2 points to draw a line
  if (data.length < 2) {
    return (
      <svg width={width} height={height} className={className}>
        <line
          x1={0}
          y1={height / 2}
          x2={width}
          y2={height / 2}
          stroke="#9ca3af"
          strokeWidth="2"
          strokeDasharray="2,2"
        />
      </svg>
    )
  }

  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1 // Avoid division by zero

  // Generate SVG path points
  const points = data.map((value, i) => {
    const x = (i / (data.length - 1)) * width
    const y = height - ((value - min) / range) * height
    return `${x},${y}`
  })

  const path = `M ${points.join(' L ')}`

  // Determine color based on overall trend
  const trend = data[data.length - 1] - data[0]
  const strokeColor = trend > 0 ? '#4ade80' : trend < 0 ? '#f87171' : '#9ca3af'

  return (
    <svg
      width={width}
      height={height}
      className={`inline-block ${className}`}
      aria-label="P&L trend sparkline"
    >
      <path
        d={path}
        fill="none"
        stroke={strokeColor}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export default MiniSparkline
