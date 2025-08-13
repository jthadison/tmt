import { render, screen } from '@testing-library/react'
import { PnLDisplay, AnimatedPnLDisplay } from '@/components/dashboard/PnLDisplay'
import { PnLMetrics } from '@/types/account'

const mockPositivePnL: PnLMetrics = {
  daily: 250.50,
  weekly: 1200.75,
  total: 5000.00,
  percentage: 5.25
}

const mockNegativePnL: PnLMetrics = {
  daily: -150.25,
  weekly: -800.50,
  total: -2500.00,
  percentage: -2.75
}

const mockZeroPnL: PnLMetrics = {
  daily: 0,
  weekly: 0,
  total: 0,
  percentage: 0
}

describe('PnLDisplay', () => {
  describe('Compact Mode (default)', () => {
    it('displays positive P&L with correct formatting and colors', () => {
      render(<PnLDisplay pnl={mockPositivePnL} />)
      
      expect(screen.getByText('P&L')).toBeInTheDocument()
      expect(screen.getByText('+$5,000.00')).toBeInTheDocument()
      expect(screen.getByText('+5.25%')).toBeInTheDocument()
      expect(screen.getByText('Today')).toBeInTheDocument()
      expect(screen.getByText('+$250.50')).toBeInTheDocument()
      
      // Check green color for positive P&L
      const totalPnL = screen.getByText('+$5,000.00')
      expect(totalPnL).toHaveClass('text-green-400')
    })

    it('displays negative P&L with correct formatting and colors', () => {
      render(<PnLDisplay pnl={mockNegativePnL} />)
      
      expect(screen.getByText('-$2,500.00')).toBeInTheDocument()
      expect(screen.getByText('-2.75%')).toBeInTheDocument()
      expect(screen.getByText('-$150.25')).toBeInTheDocument()
      
      // Check red color for negative P&L
      const totalPnL = screen.getByText('-$2,500.00')
      expect(totalPnL).toHaveClass('text-red-400')
    })

    it('displays zero P&L with correct formatting and colors', () => {
      render(<PnLDisplay pnl={mockZeroPnL} />)
      
      expect(screen.getByText('$0.00')).toBeInTheDocument()
      expect(screen.getByText('0.00%')).toBeInTheDocument()
      
      // Check gray color for zero P&L
      const totalPnL = screen.getByText('$0.00')
      expect(totalPnL).toHaveClass('text-gray-400')
    })
  })

  describe('Detailed Mode', () => {
    it('displays detailed P&L breakdown', () => {
      render(<PnLDisplay pnl={mockPositivePnL} detailed />)
      
      expect(screen.getByText('Profit & Loss')).toBeInTheDocument()
      expect(screen.getByText('Total P&L')).toBeInTheDocument()
      expect(screen.getByText('Daily')).toBeInTheDocument()
      expect(screen.getByText('Weekly')).toBeInTheDocument()
      
      expect(screen.getByText('+$5,000.00')).toBeInTheDocument()
      expect(screen.getByText('+$250.50')).toBeInTheDocument()
      expect(screen.getByText('+$1,200.75')).toBeInTheDocument()
      expect(screen.getByText('+5.25%')).toBeInTheDocument()
    })

    it('displays trend icons for positive/negative values', () => {
      render(<PnLDisplay pnl={mockPositivePnL} detailed />)
      
      // Check for upward trend icons (↗)
      expect(screen.getAllByText('↗')).toHaveLength(3) // total, daily, weekly
    })

    it('displays trend icons for negative values', () => {
      render(<PnLDisplay pnl={mockNegativePnL} detailed />)
      
      // Check for downward trend icons (↘)
      expect(screen.getAllByText('↘')).toHaveLength(3) // total, daily, weekly
    })

    it('displays neutral trend icon for zero values', () => {
      render(<PnLDisplay pnl={mockZeroPnL} detailed />)
      
      // Check for neutral trend icons (→)
      expect(screen.getAllByText('→')).toHaveLength(3) // total, daily, weekly
    })

    it('applies correct background colors based on P&L', () => {
      const { container } = render(<PnLDisplay pnl={mockPositivePnL} detailed />)
      
      // Should have green background for positive P&L
      const totalPnLContainer = container.querySelector('.bg-green-500\\/10')
      expect(totalPnLContainer).toBeInTheDocument()
    })
  })

  describe('Custom className', () => {
    it('applies custom className', () => {
      const { container } = render(<PnLDisplay pnl={mockPositivePnL} className="custom-class" />)
      
      expect(container.firstChild).toHaveClass('custom-class')
    })
  })
})

describe('AnimatedPnLDisplay', () => {
  it('renders PnLDisplay component', () => {
    render(<AnimatedPnLDisplay pnl={mockPositivePnL} />)
    
    expect(screen.getByText('P&L')).toBeInTheDocument()
    expect(screen.getByText('+$5,000.00')).toBeInTheDocument()
  })

  it('shows animation when P&L changes', () => {
    const previousPnL: PnLMetrics = {
      daily: 200,
      weekly: 1000,
      total: 4000,
      percentage: 4.0
    }
    
    const { container } = render(
      <AnimatedPnLDisplay 
        pnl={mockPositivePnL} 
        previousPnL={previousPnL} 
      />
    )
    
    // Should have pulse animation when values change
    expect(container.firstChild).toHaveClass('animate-pulse')
  })

  it('does not show animation when P&L unchanged', () => {
    const { container } = render(
      <AnimatedPnLDisplay 
        pnl={mockPositivePnL} 
        previousPnL={mockPositivePnL} 
      />
    )
    
    // Should not have pulse animation when values are the same
    expect(container.firstChild).not.toHaveClass('animate-pulse')
  })

  it('shows real-time update indicator when values change', () => {
    const previousPnL: PnLMetrics = {
      daily: 200,
      weekly: 1000,
      total: 4000,
      percentage: 4.0
    }
    
    const { container } = render(
      <AnimatedPnLDisplay 
        pnl={mockPositivePnL} 
        previousPnL={previousPnL} 
      />
    )
    
    // Should show update indicator
    const updateIndicator = container.querySelector('.animate-ping')
    expect(updateIndicator).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(
      <AnimatedPnLDisplay 
        pnl={mockPositivePnL} 
        className="custom-class"
      />
    )
    
    expect(container.firstChild).toHaveClass('custom-class')
  })
})