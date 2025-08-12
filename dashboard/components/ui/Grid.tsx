/**
 * Responsive grid component for layout
 * @param children - Grid items
 * @param cols - Number of columns (responsive)
 * @param className - Additional CSS classes
 * @returns Grid container with responsive columns
 */
interface GridProps {
  children: React.ReactNode
  cols?: {
    default?: number
    sm?: number
    md?: number
    lg?: number
    xl?: number
  }
  className?: string
}

export default function Grid({ 
  children, 
  cols = { default: 1, sm: 1, md: 2, lg: 3, xl: 4 },
  className = '' 
}: GridProps) {
  const gridClasses = [
    `grid gap-6`,
    cols.default && `grid-cols-${cols.default}`,
    cols.sm && `sm:grid-cols-${cols.sm}`,
    cols.md && `md:grid-cols-${cols.md}`,
    cols.lg && `lg:grid-cols-${cols.lg}`,
    cols.xl && `xl:grid-cols-${cols.xl}`,
    className
  ].filter(Boolean).join(' ')

  return (
    <div className={gridClasses}>
      {children}
    </div>
  )
}