/**
 * Tests for MiniSparkline component
 */

import React from 'react'
import { render } from '@testing-library/react'
import '@testing-library/jest-dom'
import { MiniSparkline } from '@/components/charts/MiniSparkline'

describe('MiniSparkline', () => {
  it('renders SVG with correct dimensions', () => {
    const data = [100, 110, 105, 115, 120]
    const { container } = render(
      <MiniSparkline data={data} width={80} height={30} />
    )

    const svg = container.querySelector('svg')
    expect(svg).toBeInTheDocument()
    expect(svg).toHaveAttribute('width', '80')
    expect(svg).toHaveAttribute('height', '30')
  })

  it('renders green line for upward trend', () => {
    const data = [100, 110, 120, 130, 140] // Upward trend
    const { container } = render(<MiniSparkline data={data} />)

    const path = container.querySelector('path')
    expect(path).toHaveAttribute('stroke', '#4ade80') // Green color
  })

  it('renders red line for downward trend', () => {
    const data = [140, 130, 120, 110, 100] // Downward trend
    const { container } = render(<MiniSparkline data={data} />)

    const path = container.querySelector('path')
    expect(path).toHaveAttribute('stroke', '#f87171') // Red color
  })

  it('renders gray line for flat trend', () => {
    const data = [100, 100, 100, 100, 100] // Flat trend
    const { container } = render(<MiniSparkline data={data} />)

    const path = container.querySelector('path')
    expect(path).toHaveAttribute('stroke', '#9ca3af') // Gray color
  })

  it('renders dashed line when data is insufficient', () => {
    const data = [100] // Only 1 point
    const { container } = render(<MiniSparkline data={data} width={80} height={30} />)

    const line = container.querySelector('line')
    expect(line).toBeInTheDocument()
    expect(line).toHaveAttribute('stroke-dasharray', '2,2')
  })

  it('applies custom className', () => {
    const data = [100, 110, 120]
    const { container } = render(
      <MiniSparkline data={data} className="custom-class" />
    )

    const svg = container.querySelector('svg')
    expect(svg).toHaveClass('custom-class')
  })

  it('has proper accessibility label', () => {
    const data = [100, 110, 120]
    const { container } = render(<MiniSparkline data={data} />)

    const svg = container.querySelector('svg')
    expect(svg).toHaveAttribute('aria-label', 'P&L trend sparkline')
  })

  it('generates correct path for data points', () => {
    const data = [100, 200, 150]
    const { container } = render(
      <MiniSparkline data={data} width={100} height={50} />
    )

    const path = container.querySelector('path')
    const pathData = path?.getAttribute('d')

    // Path should start with 'M' (move to) command
    expect(pathData).toMatch(/^M /)
    // Path should contain 'L' (line to) commands
    expect(pathData).toMatch(/L/)
  })
})
