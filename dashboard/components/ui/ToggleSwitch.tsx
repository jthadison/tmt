'use client'

import { useState } from 'react'

interface ToggleSwitchProps {
  id?: string
  checked: boolean
  onChange: (checked: boolean) => void | Promise<void>
  disabled?: boolean
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  label?: string
  description?: string
}

export default function ToggleSwitch({
  id,
  checked,
  onChange,
  disabled = false,
  size = 'md',
  loading = false,
  label,
  description,
}: ToggleSwitchProps) {
  const [isChanging, setIsChanging] = useState(false)

  const handleToggle = async () => {
    if (disabled || isChanging) return

    setIsChanging(true)
    try {
      await onChange(!checked)
    } finally {
      setIsChanging(false)
    }
  }

  // Size configurations
  const sizeConfig = {
    sm: {
      container: 'w-8 h-4',
      thumb: 'w-3 h-3',
      translate: 'translate-x-4'
    },
    md: {
      container: 'w-11 h-6',
      thumb: 'w-5 h-5',
      translate: 'translate-x-5'
    },
    lg: {
      container: 'w-14 h-7',
      thumb: 'w-6 h-6',
      translate: 'translate-x-7'
    }
  }

  const config = sizeConfig[size]
  const isActive = checked
  const isDisabled = disabled || isChanging

  return (
    <div className="flex items-center space-x-3">
      {/* Toggle Switch */}
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        aria-disabled={isDisabled}
        onClick={handleToggle}
        disabled={isDisabled}
        className={`
          relative inline-flex items-center ${config.container} rounded-full
          transition-colors duration-200 ease-in-out focus:outline-none
          focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900
          ${isActive
            ? 'bg-blue-600'
            : 'bg-gray-600'
          }
          ${isDisabled
            ? 'opacity-50 cursor-not-allowed'
            : 'cursor-pointer hover:bg-opacity-80'
          }
        `}
      >
        {/* Thumb */}
        <span
          className={`
            ${config.thumb} bg-white rounded-full shadow-lg
            transform transition-transform duration-200 ease-in-out
            flex items-center justify-center
            ${isActive ? config.translate : 'translate-x-0.5'}
          `}
        >
          {/* Loading spinner */}
          {(loading || isChanging) && (
            <div className="animate-spin w-2 h-2 border border-gray-400 border-t-transparent rounded-full" />
          )}
        </span>
      </button>

      {/* Label and Description */}
      {(label || description) && (
        <div className="flex-1">
          {label && (
            <label
              htmlFor={id}
              className={`text-sm font-medium text-gray-300 ${!isDisabled ? 'cursor-pointer' : 'cursor-not-allowed'}`}
            >
              {label}
            </label>
          )}
          {description && (
            <p className="text-xs text-gray-400 mt-1">
              {description}
            </p>
          )}
        </div>
      )}

      {/* Status Indicator */}
      {(loading || isChanging) && (
        <div className="flex items-center space-x-1">
          <div className="animate-spin w-3 h-3 border border-blue-500 border-t-transparent rounded-full" />
          <span className="text-xs text-blue-400">Syncing...</span>
        </div>
      )}
    </div>
  )
}