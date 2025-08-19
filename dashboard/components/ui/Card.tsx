import React from 'react'

/**
 * Reusable card component for dashboard sections
 * @param title - Card title
 * @param children - Card content
 * @param className - Additional CSS classes
 * @param onClick - Optional click handler
 * @returns Card component with consistent styling
 */
interface CardProps {
  title?: string | React.ReactNode
  children: React.ReactNode
  className?: string
  onClick?: () => void
}

function Card({ title, children, className = '', onClick }: CardProps) {
  return (
    <div 
      className={`bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-6 shadow-sm ${onClick ? 'cursor-pointer hover:shadow-md transition-shadow' : ''} ${className}`}
      onClick={onClick}
    >
      {title && (
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">{title}</h3>
      )}
      <div className="text-gray-600 dark:text-gray-300">
        {children}
      </div>
    </div>
  )
}

export default Card
export { Card }
export type { CardProps }