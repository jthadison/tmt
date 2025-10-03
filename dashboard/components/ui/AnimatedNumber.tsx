/**
 * Animated Number Component
 * Smoothly animates number changes using framer-motion
 */

import React from 'react'
import { motion, useSpring, useTransform } from 'framer-motion'

interface AnimatedNumberProps {
  /** The numeric value to display */
  value: number
  /** Format function to convert number to string */
  format?: (n: number) => string
  /** Animation duration in seconds */
  duration?: number
  /** Optional CSS class name */
  className?: string
}

/**
 * Animated number component with smooth transitions
 */
export function AnimatedNumber({
  value,
  format = (n) => n.toFixed(2),
  duration = 0.3,
  className = '',
}: AnimatedNumberProps) {
  const spring = useSpring(value, {
    stiffness: 100,
    damping: 30,
    duration: duration * 1000,
  })

  const display = useTransform(spring, (current) => format(current))

  // Update spring value when prop changes
  React.useEffect(() => {
    spring.set(value)
  }, [spring, value])

  return (
    <motion.span className={className} aria-live="polite">
      {display}
    </motion.span>
  )
}

export default AnimatedNumber
