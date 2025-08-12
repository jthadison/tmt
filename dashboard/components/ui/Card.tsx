/**
 * Reusable card component for dashboard sections
 * @param title - Card title
 * @param children - Card content
 * @param className - Additional CSS classes
 * @returns Card component with consistent styling
 */
interface CardProps {
  title?: string
  children: React.ReactNode
  className?: string
}

export default function Card({ title, children, className = '' }: CardProps) {
  return (
    <div className={`bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6 shadow-sm ${className}`}>
      {title && (
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">{title}</h3>
      )}
      <div className="text-gray-600 dark:text-gray-300">
        {children}
      </div>
    </div>
  )
}