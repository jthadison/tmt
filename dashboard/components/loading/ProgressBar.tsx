/**
 * Progress Bar Component
 * Story 9.1: Progress indicator for known-duration tasks
 */

interface ProgressBarProps {
  progress: number; // 0-100
  message: string;
  showPercentage?: boolean;
  className?: string;
}

export function ProgressBar({
  progress,
  message,
  showPercentage = true,
  className = '',
}: ProgressBarProps) {
  // Clamp progress between 0 and 100
  const clampedProgress = Math.max(0, Math.min(100, progress));

  return (
    <div className={`w-full ${className}`} data-testid="progress-bar">
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {message}
        </span>
        {showPercentage && (
          <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
            {Math.round(clampedProgress)}%
          </span>
        )}
      </div>
      <div
        className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={clampedProgress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={message}
      >
        <div
          className="h-full bg-blue-600 dark:bg-blue-500 transition-all duration-300 ease-out"
          style={{ width: `${clampedProgress}%` }}
          data-testid="progress-bar-fill"
        />
      </div>
    </div>
  );
}
