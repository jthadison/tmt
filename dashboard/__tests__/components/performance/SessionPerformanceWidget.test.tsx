/**
 * Tests for SessionPerformanceWidget component
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { SessionPerformanceWidget } from '@/components/performance/SessionPerformanceWidget'
import { useSessionPerformance } from '@/hooks/useSessionPerformance'
import { TradingSession } from '@/types/session'

// Mock the hooks
jest.mock('@/hooks/useSessionPerformance')
jest.mock('date-fns', () => ({
  ...jest.requireActual('date-fns'),
  format: jest.fn((date) => new Date(date).toISOString().split('T')[0]),
  startOfDay: jest.fn((date) => date),
  endOfDay: jest.fn((date) => date),
  startOfWeek: jest.fn((date) => date),
  startOfMonth: jest.fn((date) => date)
}))

const mockUseSessionPerformance = useSessionPerformance as jest.MockedFunction<typeof useSessionPerformance>

describe('SessionPerformanceWidget', () => {
  const mockSessions = [
    {
      session: TradingSession.LONDON,
      totalPnL: 1250.50,
      tradeCount: 15,
      winCount: 10,
      winRate: 66.67,
      confidenceThreshold: 72,
      isActive: true
    },
    {
      session: TradingSession.NEW_YORK,
      totalPnL: -350.25,
      tradeCount: 8,
      winCount: 3,
      winRate: 37.5,
      confidenceThreshold: 70,
      isActive: false
    },
    {
      session: TradingSession.TOKYO,
      totalPnL: 800.00,
      tradeCount: 12,
      winCount: 9,
      winRate: 75,
      confidenceThreshold: 85,
      isActive: false
    }
  ]

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders loading state correctly', () => {
    mockUseSessionPerformance.mockReturnValue({
      sessions: [],
      activeSession: null,
      isLoading: true,
      error: null,
      refetch: jest.fn()
    })

    render(<SessionPerformanceWidget />)
    expect(screen.getByText('Session Performance')).toBeInTheDocument()
  })

  it('renders session rows with correct data', () => {
    mockUseSessionPerformance.mockReturnValue({
      sessions: mockSessions,
      activeSession: TradingSession.LONDON,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    })

    render(<SessionPerformanceWidget />)

    // Check session names are rendered
    expect(screen.getByText('London')).toBeInTheDocument()
    expect(screen.getByText('New York')).toBeInTheDocument()
    expect(screen.getByText('Tokyo')).toBeInTheDocument()

    // Check P&L values
    expect(screen.getByText('$1,250.50')).toBeInTheDocument()
    expect(screen.getByText('-$350.25')).toBeInTheDocument()
    expect(screen.getByText('$800.00')).toBeInTheDocument()
  })

  it('displays active session indicator', () => {
    mockUseSessionPerformance.mockReturnValue({
      sessions: mockSessions,
      activeSession: TradingSession.LONDON,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    })

    render(<SessionPerformanceWidget />)

    // Active indicator should be present for London session
    const londonRow = screen.getByText('London').closest('button')
    const activeIndicator = londonRow?.querySelector('.animate-pulse')
    expect(activeIndicator).toBeInTheDocument()
  })

  it('shows error message when error occurs', () => {
    mockUseSessionPerformance.mockReturnValue({
      sessions: [],
      activeSession: null,
      isLoading: false,
      error: 'Failed to fetch session data',
      refetch: jest.fn()
    })

    render(<SessionPerformanceWidget />)
    expect(screen.getByText('Failed to fetch session data')).toBeInTheDocument()
  })

  it('shows no data message when sessions array is empty', () => {
    mockUseSessionPerformance.mockReturnValue({
      sessions: [],
      activeSession: null,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    })

    render(<SessionPerformanceWidget />)
    expect(screen.getByText('No session data available for selected date range')).toBeInTheDocument()
  })

  it('handles date range filter changes', async () => {
    const mockRefetch = jest.fn()
    mockUseSessionPerformance.mockReturnValue({
      sessions: mockSessions,
      activeSession: TradingSession.LONDON,
      isLoading: false,
      error: null,
      refetch: mockRefetch
    })

    render(<SessionPerformanceWidget />)

    // Click "This Week" filter
    const weekButton = screen.getByText('This Week')
    fireEvent.click(weekButton)

    // Should call refetch when date range changes
    await waitFor(() => {
      expect(mockRefetch).toHaveBeenCalled()
    })
  })

  it('exports CSV when export button is clicked', () => {
    mockUseSessionPerformance.mockReturnValue({
      sessions: mockSessions,
      activeSession: TradingSession.LONDON,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    })

    // Mock document.createElement and related DOM methods
    const createElementSpy = jest.spyOn(document, 'createElement')
    const appendChildSpy = jest.spyOn(document.body, 'appendChild').mockImplementation()
    const removeChildSpy = jest.spyOn(document.body, 'removeChild').mockImplementation()

    render(<SessionPerformanceWidget />)

    const exportButton = screen.getByText('Export CSV')
    fireEvent.click(exportButton)

    // Verify CSV creation
    expect(createElementSpy).toHaveBeenCalledWith('a')

    // Cleanup
    createElementSpy.mockRestore()
    appendChildSpy.mockRestore()
    removeChildSpy.mockRestore()
  })
})
