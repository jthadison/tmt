/**
 * Integration Tests for Graceful Degradation
 *
 * Tests:
 * - End-to-end retry flow
 * - Optimistic UI with real components
 * - Agent fallback with UI updates
 * - WebSocket fallback to polling
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import GracefulDegradationDemo from '@/app/demo/graceful-degradation/page'

describe('Graceful Degradation Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('Retry Logic Integration', () => {
    it('should display retry attempts and success message', async () => {
      let attempts = 0

      global.fetch = jest.fn().mockImplementation((url) => {
        if (url.includes('/api/test-retry')) {
          attempts++
          if (attempts < 3) {
            return Promise.reject(new Error('Network error'))
          }
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ success: true }),
          })
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({}),
        })
      })

      render(<GracefulDegradationDemo />)

      const retryButton = screen.getByText('Test Retry Logic')
      fireEvent.click(retryButton)

      // Should eventually show success
      await waitFor(
        () => {
          expect(screen.getByText(/✓ Success after retries/i)).toBeInTheDocument()
        },
        { timeout: 10000 }
      )

      expect(attempts).toBe(3)
    })

    it('should show error message after max attempts', async () => {
      global.fetch = jest.fn().mockImplementation((url) => {
        if (url.includes('/api/test-retry')) {
          return Promise.reject(new Error('Network error'))
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({}),
        })
      })

      render(<GracefulDegradationDemo />)

      const retryButton = screen.getByText('Test Retry Logic')
      fireEvent.click(retryButton)

      await waitFor(
        () => {
          expect(screen.getByText(/✗ Failed after 3 attempts/i)).toBeInTheDocument()
        },
        { timeout: 10000 }
      )
    })
  })

  describe('Optimistic UI Integration', () => {
    it('should update UI immediately and show updating state', async () => {
      global.fetch = jest.fn().mockImplementation((url) => {
        if (url.includes('/api/positions/')) {
          return new Promise((resolve) =>
            setTimeout(
              () =>
                resolve({
                  ok: true,
                  json: () => Promise.resolve({ success: true }),
                }),
              1000
            )
          )
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({}),
        })
      })

      render(<GracefulDegradationDemo />)

      const stopLossInput = screen.getByLabelText('Stop Loss')

      // Initial value
      expect(stopLossInput).toHaveValue(1.095)

      // Change value
      fireEvent.change(stopLossInput, { target: { value: '1.1000' } })

      // Should update immediately
      expect(stopLossInput).toHaveValue(1.1)

      // Should show updating state
      await waitFor(() => {
        expect(screen.getByText(/⏳ Updating position/i)).toBeInTheDocument()
      })

      // Should eventually complete
      await waitFor(
        () => {
          expect(screen.queryByText(/⏳ Updating position/i)).not.toBeInTheDocument()
        },
        { timeout: 2000 }
      )
    })

    it('should rollback on error and show retry button', async () => {
      global.fetch = jest.fn().mockImplementation((url) => {
        if (url.includes('/api/positions/')) {
          return Promise.resolve({
            ok: false,
            status: 400,
            json: () => Promise.resolve({ error: 'Invalid stop loss' }),
          })
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({}),
        })
      })

      render(<GracefulDegradationDemo />)

      const stopLossInput = screen.getByLabelText('Stop Loss')
      const originalValue = 1.095

      // Change value
      fireEvent.change(stopLossInput, { target: { value: '1.1000' } })

      // Should show error
      await waitFor(() => {
        expect(screen.getByText(/✗ Failed to update position/i)).toBeInTheDocument()
      })

      // Should rollback to original value
      expect(stopLossInput).toHaveValue(originalValue)

      // Should show retry button
      expect(screen.getByText('Retry')).toBeInTheDocument()
    })
  })

  describe('Agent Fallback Integration', () => {
    it('should show online status when agent is available', async () => {
      global.fetch = jest.fn().mockImplementation((url) => {
        if (url.includes('localhost:8008')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve([
                { id: '1', type: 'Wyckoff Accumulation', timestamp: new Date() },
              ]),
          })
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({}),
        })
      })

      render(<GracefulDegradationDemo />)

      await waitFor(() => {
        expect(screen.getByText(/✓ Pattern Detection agent online/i)).toBeInTheDocument()
      })
    })

    it('should show fallback notice when agent is offline', async () => {
      global.fetch = jest.fn().mockImplementation((url) => {
        if (url.includes('localhost:8008')) {
          return Promise.reject(new Error('Agent offline'))
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({}),
        })
      })

      render(<GracefulDegradationDemo />)

      await waitFor(() => {
        expect(
          screen.getByText(/ℹ️ Pattern Detection temporarily unavailable/i)
        ).toBeInTheDocument()
      })

      // Should still show fallback patterns
      expect(screen.getByText(/Cached Pattern 1/i)).toBeInTheDocument()
      expect(screen.getByText(/Cached Pattern 2/i)).toBeInTheDocument()
    })
  })

  describe('Status Summary', () => {
    it('should display correct status indicators', async () => {
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({}),
      })

      render(<GracefulDegradationDemo />)

      // Check status summary section exists
      expect(screen.getByText('Status Summary')).toBeInTheDocument()

      // Check individual status cards
      expect(screen.getByText('Retry Logic')).toBeInTheDocument()
      expect(screen.getByText('Optimistic Update')).toBeInTheDocument()
      expect(screen.getByText('Agent Status')).toBeInTheDocument()
    })
  })

  describe('Page Rendering', () => {
    it('should render all demo sections without crashing', () => {
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({}),
      })

      render(<GracefulDegradationDemo />)

      // Check main sections
      expect(screen.getByText(/Story 9.3: Graceful Degradation Demo/i)).toBeInTheDocument()
      expect(
        screen.getByText(/1. Automatic Retry with Exponential Backoff/i)
      ).toBeInTheDocument()
      expect(screen.getByText(/2. Optimistic UI Update with Rollback/i)).toBeInTheDocument()
      expect(
        screen.getByText(/3. Graceful Degradation - Agent with Fallback/i)
      ).toBeInTheDocument()
    })

    it('should have all interactive elements', () => {
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({}),
      })

      render(<GracefulDegradationDemo />)

      // Check buttons
      expect(screen.getByText('Test Retry Logic')).toBeInTheDocument()

      // Check input fields
      expect(screen.getByLabelText('Stop Loss')).toBeInTheDocument()
      expect(screen.getByLabelText('Status')).toBeInTheDocument()
    })
  })
})
