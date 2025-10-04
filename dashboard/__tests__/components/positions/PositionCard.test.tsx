/**
 * PositionCard Component Tests
 */

import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { PositionCard } from '@/components/positions/PositionCard'
import { Position } from '@/types/positions'

const mockPosition: Position = {
  id: '123',
  accountId: 'ACC-001',
  instrument: 'EUR_USD',
  direction: 'long',
  units: 10000,
  entryPrice: 1.0800,
  currentPrice: 1.0850,
  stopLoss: 1.0750,
  takeProfit: 1.0900,
  unrealizedPL: 50,
  unrealizedPLPercentage: 0.46,
  openTime: new Date().toISOString(),
  agentSource: 'Market Analysis',
  positionAge: '2h 34m',
  progressToTP: 50,
  progressToSL: 0,
  isNearTP: false,
  isNearSL: false,
}

describe('PositionCard', () => {
  const mockOnClose = jest.fn()
  const mockOnModify = jest.fn()
  const mockOnClick = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should render position details correctly', () => {
    render(
      <PositionCard
        position={mockPosition}
        onClose={mockOnClose}
        onModify={mockOnModify}
        onClick={mockOnClick}
      />
    )

    expect(screen.getByText('EUR/USD')).toBeInTheDocument()
    expect(screen.getByText('LONG')).toBeInTheDocument()
    expect(screen.getByText('10,000 units')).toBeInTheDocument()
    expect(screen.getByText('2h 34m')).toBeInTheDocument()
    expect(screen.getByText('Market Analysis')).toBeInTheDocument()
  })

  it('should display winning position with green styling', () => {
    const { container } = render(
      <PositionCard
        position={mockPosition}
        onClose={mockOnClose}
        onModify={mockOnModify}
        onClick={mockOnClick}
      />
    )

    const card = container.firstChild as HTMLElement
    expect(card).toHaveClass('border-green-500')
  })

  it('should display losing position with red styling', () => {
    const losingPosition = { ...mockPosition, unrealizedPL: -50 }
    const { container } = render(
      <PositionCard
        position={losingPosition}
        onClose={mockOnClose}
        onModify={mockOnModify}
        onClick={mockOnClick}
      />
    )

    const card = container.firstChild as HTMLElement
    expect(card).toHaveClass('border-red-500')
  })

  it('should call onClick when card is clicked', () => {
    const { container } = render(
      <PositionCard
        position={mockPosition}
        onClose={mockOnClose}
        onModify={mockOnModify}
        onClick={mockOnClick}
      />
    )

    fireEvent.click(container.firstChild as HTMLElement)
    expect(mockOnClick).toHaveBeenCalledWith(mockPosition)
  })

  it('should call onClose when close button is clicked', () => {
    render(
      <PositionCard
        position={mockPosition}
        onClose={mockOnClose}
        onModify={mockOnModify}
        onClick={mockOnClick}
      />
    )

    const closeButton = screen.getByLabelText('Close position')
    fireEvent.click(closeButton)

    expect(mockOnClose).toHaveBeenCalledWith('123')
    expect(mockOnClick).not.toHaveBeenCalled() // Should not trigger card click
  })

  it('should call onModify when modify button is clicked', () => {
    render(
      <PositionCard
        position={mockPosition}
        onClose={mockOnClose}
        onModify={mockOnModify}
        onClick={mockOnClick}
      />
    )

    const modifyButton = screen.getByLabelText('Modify position')
    fireEvent.click(modifyButton)

    expect(mockOnModify).toHaveBeenCalledWith('123')
    expect(mockOnClick).not.toHaveBeenCalled() // Should not trigger card click
  })

  it('should display progress bars when SL/TP are set', () => {
    render(
      <PositionCard
        position={mockPosition}
        onClose={mockOnClose}
        onModify={mockOnModify}
        onClick={mockOnClick}
      />
    )

    expect(screen.getByText('50% to TP')).toBeInTheDocument()
    expect(screen.getByText('0% to SL')).toBeInTheDocument()
  })

  it('should handle position without SL/TP', () => {
    const positionWithoutTargets = {
      ...mockPosition,
      stopLoss: undefined,
      takeProfit: undefined,
    }

    render(
      <PositionCard
        position={positionWithoutTargets}
        onClose={mockOnClose}
        onModify={mockOnModify}
        onClick={mockOnClick}
      />
    )

    expect(screen.queryByText(/% to TP/)).not.toBeInTheDocument()
    expect(screen.queryByText(/% to SL/)).not.toBeInTheDocument()
  })
})
