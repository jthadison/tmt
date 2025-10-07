'use client'

import { Component, ErrorInfo, ReactNode } from 'react'
import { AlertOctagon, RefreshCw } from 'lucide-react'
import { logError } from '@/lib/api/errors'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface State {
  hasError: boolean
  error?: Error
}

/**
 * Error boundary component to catch and handle React errors
 * Implements 4-part error message design:
 * 1. What Happened (clear description)
 * 2. Why It Matters (impact)
 * 3. Next Steps (user guidance)
 * 4. Recovery Options (actionable buttons)
 */
class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error
    }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error to error tracking service
    logError(error, { errorInfo, componentStack: errorInfo.componentStack })

    // Call optional error handler
    this.props.onError?.(error, errorInfo)
  }

  resetError = () => {
    this.setState({ hasError: false, error: undefined })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 p-6">
          <div className="text-center max-w-2xl mx-auto bg-white dark:bg-gray-900 rounded-lg shadow-xl p-8">
            {/* Error Icon */}
            <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full mb-4">
              <AlertOctagon className="h-10 w-10 text-red-600 dark:text-red-400" />
            </div>

            {/* 1. What Happened */}
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              Something Went Wrong
            </h2>

            {/* Description */}
            <p className="text-gray-700 dark:text-gray-300 mb-4">
              An unexpected error occurred while loading this section of the dashboard.
            </p>

            {/* 2. Why It Matters (Impact) */}
            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-900 rounded-lg p-4 mb-6">
              <p className="text-sm text-yellow-900 dark:text-yellow-100">
                <strong>⚠️ Impact:</strong> This error affects only this section. Other dashboard features remain available.
              </p>
            </div>

            {/* 3. Next Steps */}
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
              Try refreshing the page or click &quot;Try Again&quot; to reload this section. If the problem persists, contact support.
            </p>

            {/* 4. Recovery Options */}
            <div className="flex items-center justify-center gap-4">
              <button
                onClick={this.resetError}
                className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
              >
                <RefreshCw className="h-5 w-5" />
                Try Again
              </button>
              <button
                onClick={() => window.location.reload()}
                className="inline-flex items-center gap-2 px-6 py-3 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-900 dark:text-white rounded-lg font-medium transition-colors"
              >
                Reload Page
              </button>
            </div>

            {/* Technical Details (Development Only) */}
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="mt-6 text-left">
                <summary className="cursor-pointer text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">
                  Technical Details (Development Only)
                </summary>
                <pre className="mt-2 text-xs bg-gray-100 dark:bg-gray-800 p-4 rounded overflow-auto max-h-64">
                  {this.state.error.message}
                  {'\n\n'}
                  {this.state.error.stack}
                </pre>
              </details>
            )}
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
export { ErrorBoundary }
export type { Props as ErrorBoundaryProps }