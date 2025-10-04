/**
 * Badge Component
 * Small status indicators with variants for different states
 */

import React from 'react'
import { cn } from '@/lib/utils'

export type BadgeVariant = 'success' | 'danger' | 'warning' | 'info' | 'neutral'

interface BadgeProps {
  /** Badge content */
  children: React.ReactNode
  /** Visual variant */
  variant?: BadgeVariant
  /** Optional icon to display before text */
  icon?: React.ComponentType<{ className?: string }>
  /** Optional CSS class name */
  className?: string
}

const variantStyles: Record<BadgeVariant, string> = {
  success: 'bg-green-500/10 text-green-400 border-green-500/30',
  danger: 'bg-red-500/10 text-red-400 border-red-500/30',
  warning: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
  info: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  neutral: 'bg-gray-500/10 text-gray-400 border-gray-500/30',
}

/**
 * Badge component for status indicators
 */
export function Badge({
  children,
  variant = 'neutral',
  icon: Icon,
  className = '',
}: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold border',
        variantStyles[variant],
        className
      )}
    >
      {Icon && <Icon className="w-3 h-3" />}
      {children}
    </span>
  )
}

export default Badge
