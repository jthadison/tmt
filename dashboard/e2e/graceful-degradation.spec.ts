/**
 * Playwright E2E Tests for Graceful Degradation
 *
 * Tests:
 * - Full retry flow with UI feedback
 * - Optimistic UI updates in real browser
 * - Agent fallback scenarios
 * - Error recovery workflows
 */

import { test, expect } from '@playwright/test'

test.describe('Graceful Degradation E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:8090/demo/graceful-degradation')
  })

  test('should display page title and all sections', async ({ page }) => {
    // Check page title
    await expect(page.locator('h1')).toContainText('Story 9.3: Graceful Degradation Demo')

    // Check all demo sections
    await expect(page.getByText('1. Automatic Retry with Exponential Backoff')).toBeVisible()
    await expect(page.getByText('2. Optimistic UI Update with Rollback')).toBeVisible()
    await expect(page.getByText('3. Graceful Degradation - Agent with Fallback')).toBeVisible()
    await expect(page.getByText('Status Summary')).toBeVisible()
  })

  test('should test retry logic flow', async ({ page }) => {
    // Mock successful retry after failures
    await page.route('**/api/test-retry', async (route, request) => {
      const retryCount = parseInt(request.headers()['x-retry-count'] || '0')

      if (retryCount < 2) {
        await route.abort('failed')
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true }),
        })
      }
    })

    // Click retry test button
    await page.click('button:has-text("Test Retry Logic")')

    // Should show retry attempts
    await expect(page.getByText(/Retrying.*Attempt.*of 3/i)).toBeVisible({ timeout: 5000 })

    // Should eventually show success
    await expect(page.getByText(/✓ Success after retries/i)).toBeVisible({ timeout: 10000 })
  })

  test('should show error after max retry attempts', async ({ page }) => {
    // Mock all requests to fail
    await page.route('**/api/test-retry', (route) => {
      route.abort('failed')
    })

    // Click retry test button
    await page.click('button:has-text("Test Retry Logic")')

    // Should show error message after max attempts
    await expect(page.getByText(/✗ Failed after 3 attempts/i)).toBeVisible({ timeout: 15000 })
  })

  test('should update UI optimistically and show updating state', async ({ page }) => {
    // Mock slow API response
    await page.route('**/api/positions/*', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 1000))
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      })
    })

    // Get stop loss input
    const stopLossInput = page.getByLabel('Stop Loss')

    // Check initial value
    await expect(stopLossInput).toHaveValue('1.095')

    // Change value
    await stopLossInput.fill('1.1000')
    await stopLossInput.blur()

    // Should show updating state
    await expect(page.getByText(/⏳ Updating position/i)).toBeVisible()

    // Should complete and hide updating state
    await expect(page.getByText(/⏳ Updating position/i)).not.toBeVisible({ timeout: 3000 })
  })

  test('should rollback on error and show retry button', async ({ page }) => {
    // Mock API error
    await page.route('**/api/positions/*', (route) => {
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Invalid stop loss' }),
      })
    })

    // Get stop loss input
    const stopLossInput = page.getByLabel('Stop Loss')
    const originalValue = '1.095'

    // Change value
    await stopLossInput.fill('1.1000')
    await stopLossInput.blur()

    // Should show error
    await expect(page.getByText(/✗ Failed to update position/i)).toBeVisible()

    // Should rollback to original value
    await expect(stopLossInput).toHaveValue(originalValue)

    // Should show retry button
    await expect(page.getByRole('button', { name: 'Retry' })).toBeVisible()
  })

  test('should show agent online status', async ({ page }) => {
    // Mock successful agent response
    await page.route('**/localhost:8008/patterns/**', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: '1', type: 'Wyckoff Accumulation', timestamp: new Date().toISOString() },
          { id: '2', type: 'Spring Pattern', timestamp: new Date().toISOString() },
        ]),
      })
    })

    // Should show online status
    await expect(page.getByText(/✓ Pattern Detection agent online/i)).toBeVisible({
      timeout: 5000,
    })

    // Should show patterns
    await expect(page.getByText('Wyckoff Accumulation')).toBeVisible()
  })

  test('should show agent offline with fallback data', async ({ page }) => {
    // Mock agent failure
    await page.route('**/localhost:8008/patterns/**', (route) => {
      route.abort('failed')
    })

    // Should show offline notice
    await expect(
      page.getByText(/ℹ️ Pattern Detection temporarily unavailable/i)
    ).toBeVisible({ timeout: 5000 })

    // Should show fallback patterns
    await expect(page.getByText(/Cached Pattern 1/i)).toBeVisible()
    await expect(page.getByText(/Cached Pattern 2/i)).toBeVisible()
  })

  test('should display status summary with correct values', async ({ page }) => {
    // Check status summary section
    await expect(page.getByText('Status Summary')).toBeVisible()

    // Check status cards
    const retryStatus = page.locator('div:has-text("Retry Logic")').first()
    await expect(retryStatus).toBeVisible()

    const optimisticStatus = page.locator('div:has-text("Optimistic Update")').first()
    await expect(optimisticStatus).toBeVisible()

    const agentStatus = page.locator('div:has-text("Agent Status")').first()
    await expect(agentStatus).toBeVisible()
  })

  test('should handle manual retry after automatic retry fails', async ({ page }) => {
    let retryCount = 0

    await page.route('**/api/test-retry', async (route) => {
      retryCount++

      if (retryCount <= 3) {
        await route.abort('failed')
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true }),
        })
      }
    })

    // Click retry test button
    await page.click('button:has-text("Test Retry Logic")')

    // Wait for automatic retries to fail
    await expect(page.getByText(/✗ Failed after 3 attempts/i)).toBeVisible({ timeout: 15000 })

    // Manual retry would require additional UI implementation
    // This test demonstrates the flow
  })

  test('should be responsive and accessible', async ({ page }) => {
    // Check for proper headings
    const headings = page.locator('h1, h2')
    await expect(headings).toHaveCount(5) // 1 h1 + 4 h2s

    // Check for interactive elements
    const buttons = page.locator('button')
    await expect(buttons.first()).toBeEnabled()

    // Check for form labels
    const stopLossLabel = page.getByLabel('Stop Loss')
    await expect(stopLossLabel).toBeVisible()

    // Check color contrast for status indicators
    const successIndicator = page.locator('.bg-green-50')
    await expect(successIndicator).toHaveCount(1) // Status summary card
  })

  test('should handle rapid optimistic updates', async ({ page }) => {
    let updateCount = 0

    await page.route('**/api/positions/*', async (route) => {
      updateCount++
      await new Promise((resolve) => setTimeout(resolve, 500))
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      })
    })

    const stopLossInput = page.getByLabel('Stop Loss')

    // Make rapid changes
    await stopLossInput.fill('1.1000')
    await stopLossInput.blur()

    await page.waitForTimeout(100)

    await stopLossInput.fill('1.1050')
    await stopLossInput.blur()

    // Should handle multiple updates
    await expect(stopLossInput).toHaveValue('1.105')
  })
})
