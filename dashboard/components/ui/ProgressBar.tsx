/**
 * Progress Bar Component
 * Horizontal progress indicator with label and color variants
 */

import React from 'react'
import { cn } from '@/lib/utils'

export type ProgressBarColor = 'green' | 'red' | 'blue' | 'yellow' | 'gray'

interface ProgressBarProps {
  /** Progress value (0-100) */
  value: number
  /** Progress bar color */
  color?: ProgressBarColor
  /** Optional label to display */
  label?: string
  /** Show percentage label */
  showPercentage?: boolean
  /** Height of the bar */
  height?: 'sm' | 'md' | 'lg'
  /** Optional CSS class name */
  className?: string
}

const colorStyles: Record<ProgressBarColor, string> = {
  green: 'bg-green-500',
  red: 'bg-red-500',
  blue: 'bg-blue-500',
  yellow: 'bg-yellow-500',
  gray: 'bg-gray-500',
}

const heightStyles = {
  sm: 'h-1',
  md: 'h-2',
  lg: 'h-3',
}

/**
 * Progress bar component
 */
export function ProgressBar({
  value,
  color = 'blue',
  label,
  showPercentage = false,
  height = 'md',
  className = '',
}: ProgressBarProps) {
  // Clamp value between 0 and 100
  const clampedValue = Math.max(0, Math.min(100, value))

  return (
    <div className={cn('w-full', className)}>
      {(label || showPercentage) && (
        <div className="flex items-center justify-between mb-1 text-xs text-gray-400">
          {label && <span>{label}</span>}
          {showPercentage && <span>{clampedValue.toFixed(0)}%</span>}
        </div>
      )}
      <div className={cn('w-full bg-gray-700 rounded-full overflow-hidden', heightStyles[height])}>
        <div
          className={cn('h-full rounded-full transition-all duration-300 ease-out', colorStyles[color])}
          style={{ width: `${clampedValue}%` }}
          role="progressbar"
          aria-valuenow={clampedValue}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
    </div>
  )
}

export default ProgressBar
