import { AlertOctagon, RefreshCw, ExternalLink } from 'lucide-react'
import { useEffect, useState } from 'react'

interface CriticalErrorStateProps {
  title: string
  description: string
  impact: string
  onRetry: () => void
  autoRetrySeconds?: number
  supportLink?: string
}

export function CriticalErrorState({
  title,
  description,
  impact,
  onRetry,
  autoRetrySeconds = 15,
  supportLink = '/support',
}: CriticalErrorStateProps) {
  const [countdown, setCountdown] = useState(autoRetrySeconds)

  useEffect(() => {
    if (countdown <= 0) {
      onRetry()
      return
    }

    const timer = setTimeout(() => setCountdown(countdown - 1), 1000)
    return () => clearTimeout(timer)
  }, [countdown, onRetry])

  const progress = ((autoRetrySeconds - countdown) / autoRetrySeconds) * 100

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-6">
      <div className="max-w-2xl w-full bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8">
        <div className="text-center">
          {/* Error Icon */}
          <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full mb-4">
            <AlertOctagon className="h-10 w-10 text-red-600 dark:text-red-400" />
          </div>

          {/* What Happened */}
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            {title}
          </h1>

          {/* Description */}
          <p className="text-gray-700 dark:text-gray-300 mb-4">
            {description}
          </p>

          {/* Why It Matters */}
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-900 rounded-lg p-4 mb-6">
            <p className="text-sm text-yellow-900 dark:text-yellow-100">
              <strong>⚠️ Important:</strong> {impact}
            </p>
          </div>

          {/* Auto-Retry Progress */}
          <div className="mb-6">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              Reconnecting automatically in {countdown} seconds...
            </p>
            <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-600 dark:bg-blue-500 transition-all duration-1000 ease-linear"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* Recovery Options */}
          <div className="flex items-center justify-center gap-4">
            <button
              onClick={onRetry}
              className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
            >
              <RefreshCw className="h-5 w-5" />
              Retry Now
            </button>

            <a
              href={supportLink}
              className="inline-flex items-center gap-2 px-6 py-3 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-900 dark:text-white rounded-lg font-medium transition-colors"
            >
              Contact Support
              <ExternalLink className="h-4 w-4" />
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
