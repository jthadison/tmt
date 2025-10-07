import { AlertTriangle, RefreshCw } from 'lucide-react'

interface ComponentErrorStateProps {
  error: Error
  onRetry: () => void
  title?: string
  description?: string
  impact?: string
}

export function ComponentErrorState({
  error,
  onRetry,
  title = 'Unable to load component',
  description = 'An unexpected error occurred while loading this section.',
  impact = 'Other dashboard features are still available.',
}: ComponentErrorStateProps) {
  return (
    <div className="border border-red-200 dark:border-red-900 rounded-lg p-6 bg-red-50 dark:bg-red-950/20">
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-6 w-6 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />

        <div className="flex-1">
          {/* What Happened */}
          <h3 className="text-lg font-semibold text-red-900 dark:text-red-100 mb-2">
            {title}
          </h3>

          {/* Description */}
          <p className="text-sm text-red-800 dark:text-red-200 mb-2">
            {description}
          </p>

          {/* Why It Matters */}
          <p className="text-sm text-red-700 dark:text-red-300 mb-4">
            <strong>Impact:</strong> {impact}
          </p>

          {/* Recovery Options */}
          <div className="flex items-center gap-3">
            <button
              onClick={onRetry}
              className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded font-medium transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
              Retry
            </button>

            <button
              onClick={() => window.location.reload()}
              className="text-sm text-red-700 dark:text-red-300 hover:underline"
            >
              Reload Page
            </button>
          </div>

          {/* Technical Details (collapsed by default) */}
          {process.env.NODE_ENV === 'development' && (
            <details className="mt-4">
              <summary className="text-xs text-red-600 dark:text-red-400 cursor-pointer">
                Technical Details (Development Only)
              </summary>
              <pre className="mt-2 p-2 bg-red-100 dark:bg-red-900/30 rounded text-xs text-red-900 dark:text-red-100 overflow-auto">
                {error.message}
                {'\n\n'}
                {error.stack}
              </pre>
            </details>
          )}
        </div>
      </div>
    </div>
  )
}
