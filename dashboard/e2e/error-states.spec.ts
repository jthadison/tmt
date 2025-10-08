import { test, expect } from '@playwright/test'

test.describe('Error States & Empty States', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/error-states-demo')
  })

  test('page renders correctly with all sections', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Error States & Empty States Demo' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Toast Notifications' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Component Error State (Inline)' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Critical Error State (Full Page)' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Error Boundary (React Error Catching)' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Form Validation Errors with Suggestions' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Empty State - No Data' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Empty State - No Results (Filtered)' })).toBeVisible()
  })

  test('toast notifications appear and can be dismissed', async ({ page }) => {
    // Show error toast
    await page.getByRole('button', { name: 'Show Error Toast' }).click()
    await expect(page.getByText('This is an error toast notification')).toBeVisible()

    // Toast should have dismiss button
    const dismissButton = page.locator('button[aria-label="Dismiss notification"]').first()
    await dismissButton.click()

    // Toast should disappear
    await expect(page.getByText('This is an error toast notification')).not.toBeVisible()
  })

  test('component error state displays inline with retry functionality', async ({ page }) => {
    // Show component error
    await page.getByRole('button', { name: /show component error/i }).click()

    // Error should be visible
    await expect(page.getByText('Unable to load EUR_USD position data')).toBeVisible()
    await expect(page.getByText(/trading server is temporarily unavailable/i)).toBeVisible()
    await expect(page.getByText(/impact:/i)).toBeVisible()

    // Retry button should be visible
    const retryButton = page.getByRole('button', { name: /retry/i }).first()
    await expect(retryButton).toBeVisible()

    // Click retry
    await retryButton.click()

    // Error should be hidden
    await expect(page.getByText('Unable to load EUR_USD position data')).not.toBeVisible()
  })

  test('critical error state displays full-page with countdown', async ({ page }) => {
    // Show critical error
    await page.getByRole('button', { name: /show critical error/i }).click()

    // Should see full-page error
    await expect(page.getByText('Connection Lost')).toBeVisible()
    await expect(page.getByText(/unable to connect to the trading system/i)).toBeVisible()
    await expect(page.getByText(/you cannot open new positions/i)).toBeVisible()

    // Should see countdown
    await expect(page.getByText(/reconnecting automatically in \d+ seconds/i)).toBeVisible()

    // Should have retry button
    await expect(page.getByRole('button', { name: /retry now/i })).toBeVisible()

    // Should have contact support link
    await expect(page.getByRole('link', { name: /contact support/i })).toBeVisible()

    // Click retry to hide
    await page.getByRole('button', { name: /retry now/i }).click()
  })

  test('error boundary catches React errors', async ({ page }) => {
    // Show error boundary test
    await page.getByRole('button', { name: /show error boundary test/i }).click()

    // Should see error message
    await expect(page.getByText(/something went wrong/i)).toBeVisible()
    await expect(page.getByText(/unexpected error occurred/i)).toBeVisible()

    // Should have Try Again button
    const tryAgainButton = page.getByRole('button', { name: /try again/i }).first()
    await expect(tryAgainButton).toBeVisible()

    // Should have Reload Page button
    await expect(page.getByRole('button', { name: /reload page/i })).toBeVisible()
  })

  test('form validation displays errors with suggestions', async ({ page }) => {
    // Enter invalid stop loss (negative value)
    await page.fill('input[name="stopLoss"]', '-50')
    await page.fill('input[name="takeProfit"]', '60')

    // Submit form
    await page.getByRole('button', { name: /submit form/i }).click()

    // Should see validation error
    await expect(page.getByText(/stop loss must be a positive value/i)).toBeVisible()

    // Should see suggestion
    await expect(page.getByText(/suggestion:/i)).toBeVisible()
    await expect(page.getByText(/try 20\.00 for a 2% stop loss/i)).toBeVisible()

    // Fix the error
    await page.fill('input[name="stopLoss"]', '20')

    // Submit again
    await page.getByRole('button', { name: /submit form/i }).click()

    // Should see success toast
    await expect(page.getByText(/form submitted successfully/i)).toBeVisible()
  })

  test('empty state - no data displays correctly', async ({ page }) => {
    // Empty state should be visible by default
    await expect(page.getByText('No Open Positions')).toBeVisible()
    await expect(page.getByText(/you haven't opened any positions yet/i)).toBeVisible()

    // Should have action buttons
    await expect(page.getByRole('button', { name: /view available signals/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /learn about trading/i })).toBeVisible()

    // Click action button
    await page.getByRole('button', { name: /view available signals/i }).click()

    // Should show toast notification
    await expect(page.getByText(/would navigate to signals page/i)).toBeVisible()
  })

  test('empty state - no results (filtered) displays correctly', async ({ page }) => {
    // Scroll to no results section
    await page.getByText('Empty State - No Results (Filtered)').scrollIntoViewIfNeeded()

    // Empty state should be visible by default
    await expect(page.getByText('No Positions Match Your Filters')).toBeVisible()
    await expect(page.getByText(/symbol: gbp_usd/i)).toBeVisible()

    // Should have action buttons
    const clearFiltersButton = page.getByRole('button', { name: /clear all filters/i }).last()
    await expect(clearFiltersButton).toBeVisible()

    // Click clear filters
    await clearFiltersButton.click()

    // Should show toast notification
    await expect(page.getByText(/all filters have been cleared/i)).toBeVisible()
  })

  test('all toast types display with correct styling', async ({ page }) => {
    // Show all toast types
    await page.getByRole('button', { name: 'Show Error Toast' }).click()
    await page.waitForTimeout(100)
    await page.getByRole('button', { name: 'Show Warning Toast' }).click()
    await page.waitForTimeout(100)
    await page.getByRole('button', { name: 'Show Info Toast' }).click()
    await page.waitForTimeout(100)
    await page.getByRole('button', { name: 'Show Success Toast' }).click()

    // All toasts should be visible (max 3 + newest one)
    await expect(page.getByText('This is an error toast notification')).toBeVisible()
    await expect(page.getByText('This is a warning toast notification')).toBeVisible()
    await expect(page.getByText('This is an info toast notification')).toBeVisible()
    await expect(page.getByText('This is a success toast notification')).toBeVisible()
  })

  test('form validation clears when valid data is entered', async ({ page }) => {
    // Enter invalid data
    await page.fill('input[name="stopLoss"]', '-50')
    await page.getByRole('button', { name: /submit form/i }).click()

    // Error should be visible
    await expect(page.getByText(/stop loss must be a positive value/i)).toBeVisible()

    // Enter valid data
    await page.fill('input[name="stopLoss"]', '20')
    await page.fill('input[name="takeProfit"]', '60')

    // Click outside to trigger validation
    await page.getByRole('heading', { name: 'Form Validation Errors with Suggestions' }).click()

    // Submit form
    await page.getByRole('button', { name: /submit form/i }).click()

    // Success toast should appear
    await expect(page.getByText(/form submitted successfully/i)).toBeVisible()

    // Error should not be visible
    await expect(page.getByText(/stop loss must be a positive value/i)).not.toBeVisible()
  })

  test('component error state has reload page button', async ({ page }) => {
    // Show component error
    await page.getByRole('button', { name: /show component error/i }).click()

    // Should see reload page button
    const reloadButton = page.getByRole('button', { name: /reload page/i }).first()
    await expect(reloadButton).toBeVisible()

    // Note: We don't actually click it as it would reload the page
  })

  test('empty states toggle correctly', async ({ page }) => {
    // No data empty state should be visible
    await expect(page.getByText('No Open Positions')).toBeVisible()

    // Click hide button
    await page.getByRole('button', { name: /hide empty state/i }).first().click()

    // Empty state should be hidden
    await expect(page.getByText('No Open Positions')).not.toBeVisible()

    // Click show again
    await page.getByRole('button', { name: /show empty state/i }).first().click()

    // Empty state should be visible again
    await expect(page.getByText('No Open Positions')).toBeVisible()
  })
})
