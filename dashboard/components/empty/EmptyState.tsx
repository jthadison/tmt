import { Inbox, Search } from 'lucide-react'

interface EmptyStateProps {
  type: 'no-data' | 'no-results'
  title: string
  description: string
  action?: {
    label: string
    onClick: () => void
  }
  secondaryAction?: {
    label: string
    onClick: () => void
  }
}

export function EmptyState({ type, title, description, action, secondaryAction }: EmptyStateProps) {
  const Icon = type === 'no-data' ? Inbox : Search
  const iconColor = type === 'no-data' ? 'text-gray-400' : 'text-blue-400'

  return (
    <div className="flex flex-col items-center justify-center p-12 text-center">
      <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-800 mb-4`}>
        <Icon className={`h-8 w-8 ${iconColor}`} />
      </div>

      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
        {title}
      </h3>

      <p className="text-sm text-gray-600 dark:text-gray-400 max-w-md mb-6">
        {description}
      </p>

      {action && (
        <div className="flex items-center gap-3">
          <button
            onClick={action.onClick}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
          >
            {action.label}
          </button>

          {secondaryAction && (
            <button
              onClick={secondaryAction.onClick}
              className="px-6 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-900 dark:text-white rounded-lg font-medium transition-colors"
            >
              {secondaryAction.label}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
