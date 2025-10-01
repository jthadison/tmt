/**
 * SparkLine Component
 * Lightweight latency trend visualization
 */

'use client'

import React, { useMemo } from 'react'

interface SparkLineProps {
  data: number[]
  width?: number
  height?: number
  className?: string
}

/**
 * Renders a simple SVG sparkline chart for latency trends
 */
export default function SparkLine({
  data,
  width = 100,
  height = 30,
  className = ''
}: SparkLineProps) {
  // Calculate path points from data
  const pathData = useMemo(() => {
    if (data.length === 0) return ''

    const max = Math.max(...data, 1) // Prevent division by zero
    const min = Math.min(...data, 0)
    const range = max - min || 1

    const points = data.map((value, index) => {
      const x = (index / (data.length - 1 || 1)) * width
      const y = height - ((value - min) / range) * height
      return `${x},${y}`
    })

    return `M ${points.join(' L ')}`
  }, [data, width, height])

  // Determine color based on average latency
  const color = useMemo(() => {
    if (data.length === 0) return 'stroke-gray-600'

    const avg = data.reduce((sum, val) => sum + val, 0) / data.length

    if (avg < 100) return 'stroke-green-400'
    if (avg <= 300) return 'stroke-yellow-400'
    return 'stroke-red-400'
  }, [data])

  // Show placeholder if no data
  if (data.length === 0) {
    return (
      <svg
        width={width}
        height={height}
        className={className}
        aria-label="No latency data available"
      >
        <line
          x1="0"
          y1={height / 2}
          x2={width}
          y2={height / 2}
          className="stroke-gray-700"
          strokeWidth="1"
          strokeDasharray="2,2"
        />
      </svg>
    )
  }

  return (
    <svg
      width={width}
      height={height}
      className={className}
      aria-label={`Latency trend: ${data.length} data points`}
    >
      <path
        d={pathData}
        fill="none"
        className={`${color} transition-colors duration-300`}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
