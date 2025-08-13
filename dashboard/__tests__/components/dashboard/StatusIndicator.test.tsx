import { render, screen } from '@testing-library/react'
import { StatusIndicator, calculateAccountStatus } from '@/components/dashboard/StatusIndicator'
import { AccountStatus } from '@/types/account'

describe('StatusIndicator', () => {
  it('renders healthy status correctly', () => {
    render(<StatusIndicator status="healthy" />)
    
    const statusElement = screen.getByRole('status', { name: 'Account status: Healthy' })
    expect(statusElement).toBeInTheDocument()
    
    // Check for green indicator
    const indicator = statusElement.querySelector('.bg-green-500')
    expect(indicator).toBeInTheDocument()
  })

  it('renders warning status correctly', () => {
    render(<StatusIndicator status="warning" />)
    
    const statusElement = screen.getByRole('status', { name: 'Account status: Warning' })
    expect(statusElement).toBeInTheDocument()
    
    // Check for yellow indicator
    const indicator = statusElement.querySelector('.bg-yellow-500')
    expect(indicator).toBeInTheDocument()
  })

  it('renders danger status correctly', () => {
    render(<StatusIndicator status="danger" />)
    
    const statusElement = screen.getByRole('status', { name: 'Account status: Danger' })
    expect(statusElement).toBeInTheDocument()
    
    // Check for red indicator
    const indicator = statusElement.querySelector('.bg-red-500')
    expect(indicator).toBeInTheDocument()
  })

  it('shows status text when showText is true', () => {
    render(<StatusIndicator status="healthy" showText />)
    
    expect(screen.getByText('Healthy')).toBeInTheDocument()
  })

  it('does not show status text by default', () => {
    render(<StatusIndicator status="healthy" />)
    
    expect(screen.queryByText('Healthy')).not.toBeInTheDocument()
  })

  it('applies correct size classes for small size', () => {
    render(<StatusIndicator status="healthy" size="sm" />)
    
    const statusElement = screen.getByRole('status')
    const indicator = statusElement.querySelector('.w-2.h-2')
    expect(indicator).toBeInTheDocument()
  })

  it('applies correct size classes for large size', () => {
    render(<StatusIndicator status="healthy" size="lg" />)
    
    const statusElement = screen.getByRole('status')
    const indicator = statusElement.querySelector('.w-4.h-4')
    expect(indicator).toBeInTheDocument()
  })

  it('adds pulse animation for warning status', () => {
    render(<StatusIndicator status="warning" />)
    
    const statusElement = screen.getByRole('status')
    const indicator = statusElement.querySelector('.animate-pulse')
    expect(indicator).toBeInTheDocument()
  })

  it('adds pulse animation for danger status', () => {
    render(<StatusIndicator status="danger" />)
    
    const statusElement = screen.getByRole('status')
    const indicator = statusElement.querySelector('.animate-pulse')
    expect(indicator).toBeInTheDocument()
  })

  it('does not add pulse animation for healthy status', () => {
    render(<StatusIndicator status="healthy" />)
    
    const statusElement = screen.getByRole('status')
    const indicator = statusElement.querySelector('.animate-pulse')
    expect(indicator).not.toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(<StatusIndicator status="healthy" className="custom-class" />)
    
    expect(container.firstChild).toHaveClass('custom-class')
  })
})

describe('calculateAccountStatus', () => {
  it('returns danger for drawdown > 80%', () => {
    const status = calculateAccountStatus(85, 0, 0)
    expect(status).toBe('danger')
  })

  it('returns warning for drawdown 50-80%', () => {
    const status = calculateAccountStatus(65, 0, 0)
    expect(status).toBe('warning')
  })

  it('returns warning for significant daily losses', () => {
    const status = calculateAccountStatus(30, -1500, 0)
    expect(status).toBe('warning')
  })

  it('returns healthy for low drawdown and positive P&L', () => {
    const status = calculateAccountStatus(25, 500, 1000)
    expect(status).toBe('healthy')
  })

  it('returns healthy for low drawdown and minor negative P&L', () => {
    const status = calculateAccountStatus(25, -200, -500)
    expect(status).toBe('healthy')
  })

  it('prioritizes drawdown over daily P&L for danger status', () => {
    const status = calculateAccountStatus(90, 500, 1000) // High drawdown but positive P&L
    expect(status).toBe('danger')
  })

  it('handles edge case of exactly 50% drawdown', () => {
    const status = calculateAccountStatus(50, 0, 0)
    expect(status).toBe('warning')
  })

  it('handles edge case of exactly 80% drawdown', () => {
    const status = calculateAccountStatus(80, 0, 0)
    expect(status).toBe('warning')
  })

  it('handles edge case of exactly -1000 daily P&L', () => {
    const status = calculateAccountStatus(30, -1000, 0)
    expect(status).toBe('warning')
  })
})