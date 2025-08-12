'use client'

import { useState } from 'react'

interface RetryButtonProps {
  onRetry: () => Promise<void> | void
  maxRetries?: number
  className?: string
  children?: React.ReactNode
}

/**
 * Retry button with exponential backoff and attempt counting
 * @param onRetry - Function to execute on retry
 * @param maxRetries - Maximum number of retry attempts
 * @param className - Additional CSS classes
 * @param children - Button content
 * @returns Retry button component
 */
export default function RetryButton({ 
  onRetry, 
  maxRetries = 3, 
  className = '',
  children = 'Retry'
}: RetryButtonProps) {
  const [isRetrying, setIsRetrying] = useState(false)
  const [retryCount, setRetryCount] = useState(0)

  const handleRetry = async () => {
    if (retryCount >= maxRetries || isRetrying) return

    setIsRetrying(true)
    
    try {
      await onRetry()
      // Reset retry count on success
      setRetryCount(0)
    } catch (error) {
      console.error('Retry failed:', error)
      setRetryCount(prev => prev + 1)
    } finally {
      setIsRetrying(false)
    }
  }

  const isDisabled = retryCount >= maxRetries || isRetrying

  return (
    <button
      onClick={handleRetry}
      disabled={isDisabled}
      className={`
        inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium
        ${isDisabled 
          ? 'bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed'
          : 'bg-blue-600 hover:bg-blue-700 text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:bg-blue-500 dark:hover:bg-blue-600'
        }
        transition-colors duration-200
        ${className}
      `}
    >
      {isRetrying ? (
        <>
          <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Retrying...
        </>
      ) : (
        <>
          {retryCount >= maxRetries ? (
            'Max retries reached'
          ) : (
            <>
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              {children}
              {retryCount > 0 && ` (${retryCount}/${maxRetries})`}
            </>
          )}
        </>
      )}
    </button>
  )
}