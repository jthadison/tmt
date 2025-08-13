'use client'

import { AccountStatus } from '@/types/account'

/**
 * Props for StatusIndicator component
 */
interface StatusIndicatorProps {
  /** Current account status */
  status: AccountStatus
  /** Additional CSS classes */
  className?: string
  /** Show status text alongside indicator */
  showText?: boolean
  /** Size variant */
  size?: 'sm' | 'md' | 'lg'
}

/**
 * Traffic light status indicator component (green/yellow/red)
 * Provides visual indication of account health with animations
 */
export function StatusIndicator({ 
  status, 
  className = '', 
  showText = false,
  size = 'md'
}: StatusIndicatorProps) {
  const getStatusConfig = (status: AccountStatus) => {
    switch (status) {
      case 'healthy':
        return {
          color: 'bg-green-500',
          shadowColor: 'shadow-green-500/50',
          textColor: 'text-green-400',
          label: 'Healthy',
          ariaLabel: 'Account status: Healthy'
        }
      case 'warning':
        return {
          color: 'bg-yellow-500',
          shadowColor: 'shadow-yellow-500/50',
          textColor: 'text-yellow-400',
          label: 'Warning',
          ariaLabel: 'Account status: Warning'
        }
      case 'danger':
        return {
          color: 'bg-red-500',
          shadowColor: 'shadow-red-500/50',
          textColor: 'text-red-400',
          label: 'Danger',
          ariaLabel: 'Account status: Danger'
        }
      default:
        return {
          color: 'bg-gray-500',
          shadowColor: 'shadow-gray-500/50',
          textColor: 'text-gray-400',
          label: 'Unknown',
          ariaLabel: 'Account status: Unknown'
        }
    }
  }

  const getSizeClasses = (size: 'sm' | 'md' | 'lg') => {
    switch (size) {
      case 'sm':
        return {
          indicator: 'w-2 h-2',
          text: 'text-xs'
        }
      case 'md':
        return {
          indicator: 'w-3 h-3',
          text: 'text-sm'
        }
      case 'lg':
        return {
          indicator: 'w-4 h-4',
          text: 'text-base'
        }
    }
  }

  const config = getStatusConfig(status)
  const sizeClasses = getSizeClasses(size)

  // Add pulse animation for warning and danger states
  const shouldPulse = status === 'warning' || status === 'danger'

  return (
    <div 
      className={`flex items-center gap-2 ${className}`}
      role="status"
      aria-label={config.ariaLabel}
    >
      {/* Status Indicator Circle */}
      <div
        className={`
          ${sizeClasses.indicator}
          ${config.color}
          rounded-full
          ${shouldPulse ? 'animate-pulse' : ''}
          shadow-lg ${config.shadowColor}
          transition-all duration-300
        `}
        aria-hidden="true"
      />
      
      {/* Status Text (optional) */}
      {showText && (
        <span 
          className={`
            ${sizeClasses.text}
            ${config.textColor}
            font-medium
            select-none
          `}
        >
          {config.label}
        </span>
      )}
    </div>
  )
}

/**
 * Utility function to determine account status based on metrics
 * Implements the health status logic defined in the story requirements
 */
export function calculateAccountStatus(
  drawdownPercentage: number,
  dailyPnL: number,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _totalPnL: number
): AccountStatus {
  // Red (Danger): Drawdown > 80% of limit
  if (drawdownPercentage > 80) {
    return 'danger'
  }
  
  // Yellow (Warning): Drawdown >= 50% of limit, or significant daily losses
  if (drawdownPercentage >= 50 || dailyPnL <= -1000) {
    return 'warning'
  }
  
  // Green (Healthy): Drawdown < 50% of limit, P&L positive or minor negative
  return 'healthy'
}