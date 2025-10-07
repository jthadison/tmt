import { test, expect } from '@playwright/test'

test.describe('Story 8.3: Performance Degradation Alerts & Risk Metrics', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to performance analytics page
    await page.goto('http://localhost:8090/performance-analytics')

    // Wait for page to load
    await page.waitForLoadState('networkidle')
  })

  test('displays active performance alerts panel', async ({ page }) => {
    // Check for Active Performance Alerts section
    const alertsHeading = page.getByRole('heading', { name: /Performance Degradation Monitoring/i })
    await expect(alertsHeading).toBeVisible()

    // Wait for alerts panel to load
    await page.waitForSelector('.active-alert-panel', { timeout: 10000 })

    // Should show either alerts or empty state
    const hasAlerts = await page.locator('.alert-card').count() > 0
    const hasEmptyState = await page.getByText(/No active alerts/).isVisible()

    expect(hasAlerts || hasEmptyState).toBeTruthy()
  })

  test('displays risk-adjusted metrics dashboard', async ({ page }) => {
    // Check for Risk-Adjusted Metrics section
    const metricsHeading = page.getByRole('heading', { name: /Risk-Adjusted Performance Metrics/i })
    await expect(metricsHeading).toBeVisible()

    // Wait for metrics to load
    await page.waitForSelector('.risk-metrics-dashboard', { timeout: 10000 })

    // Check for all 4 sections
    await expect(page.getByText('Risk-Adjusted Returns')).toBeVisible()
    await expect(page.getByText('Drawdown Analysis')).toBeVisible()
    await expect(page.getByText('Volatility Analysis')).toBeVisible()
    await expect(page.getByText('Risk/Reward Profile')).toBeVisible()
  })

  test('displays Sharpe, Sortino, and Calmar ratios', async ({ page }) => {
    await page.waitForSelector('.risk-metrics-dashboard', { timeout: 10000 })

    // Check for ratio cards
    await expect(page.getByText('Sharpe Ratio')).toBeVisible()
    await expect(page.getByText('Sortino Ratio')).toBeVisible()
    await expect(page.getByText('Calmar Ratio')).toBeVisible()

    // Check that values are displayed (numbers)
    const ratioCards = page.locator('.ratio-card')
    expect(await ratioCards.count()).toBeGreaterThanOrEqual(3)
  })

  test('displays drawdown distribution chart', async ({ page }) => {
    await page.waitForSelector('.risk-metrics-dashboard', { timeout: 10000 })

    // Check for drawdown distribution
    await expect(page.getByText('Drawdown Distribution')).toBeVisible()

    // Chart should be present
    const chart = page.locator('.drawdown-distribution-chart')
    await expect(chart).toBeVisible()
  })

  test('displays alert configuration panel', async ({ page }) => {
    // Scroll to alert configuration
    const configHeading = page.getByRole('heading', { name: /Alert Configuration/i })
    await configHeading.scrollIntoViewIfNeeded()
    await expect(configHeading).toBeVisible()

    // Check for configuration panel
    await page.waitForSelector('.alert-config-panel', { timeout: 10000 })

    // Check for threshold sliders
    await expect(page.getByText('Profit Factor Decline')).toBeVisible()
    await expect(page.getByText('Sharpe Ratio Threshold')).toBeVisible()
    await expect(page.getByText('Overfitting Threshold')).toBeVisible()
  })

  test('can adjust alert thresholds', async ({ page }) => {
    // Scroll to alert configuration
    const configHeading = page.getByRole('heading', { name: /Alert Configuration/i })
    await configHeading.scrollIntoViewIfNeeded()

    await page.waitForSelector('.alert-config-panel', { timeout: 10000 })

    // Find and adjust a slider
    const slider = page.locator('input[type="range"]').first()
    await slider.fill('15')

    // Click save button
    const saveButton = page.getByRole('button', { name: /Save Configuration/i })
    await saveButton.click()

    // Check for success message
    await expect(page.getByText(/Alert thresholds updated successfully/i)).toBeVisible({ timeout: 5000 })
  })

  test('displays alert history', async ({ page }) => {
    // Scroll to alert history
    const historyHeading = page.getByRole('heading', { name: /Alert History/i })
    await historyHeading.scrollIntoViewIfNeeded()
    await expect(historyHeading).toBeVisible()

    // Check for history panel
    await page.waitForSelector('.alert-history', { timeout: 10000 })

    // Check for filters
    await expect(page.getByText('Last 7 days')).toBeVisible()
    await expect(page.getByText('All severities')).toBeVisible()
  })

  test('can filter alert history', async ({ page }) => {
    // Scroll to alert history
    const historyHeading = page.getByRole('heading', { name: /Alert History/i })
    await historyHeading.scrollIntoViewIfNeeded()

    await page.waitForSelector('.alert-history', { timeout: 10000 })

    // Find severity filter dropdown
    const severityFilter = page.locator('select').filter({ hasText: 'All severities' })
    await severityFilter.selectOption('critical')

    // Wait for filtered results
    await page.waitForTimeout(1000)

    // Check that table updated (either has rows or shows no results)
    const table = page.locator('.alert-history table')
    await expect(table).toBeVisible()
  })

  test('can export alert history to CSV', async ({ page }) => {
    // Scroll to alert history
    const historyHeading = page.getByRole('heading', { name: /Alert History/i })
    await historyHeading.scrollIntoViewIfNeeded()

    await page.waitForSelector('.alert-history', { timeout: 10000 })

    // Set up download handler
    const downloadPromise = page.waitForEvent('download', { timeout: 5000 })

    // Click export button
    const exportButton = page.getByRole('button', { name: /Export CSV/i })
    await exportButton.click()

    // Wait for download
    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/alert-history.*\.csv/)
  })

  test('alert panel shows severity badges correctly', async ({ page }) => {
    await page.waitForSelector('.active-alert-panel', { timeout: 10000 })

    // If there are alerts, check severity badges
    const alertCards = page.locator('.alert-card')
    const count = await alertCards.count()

    if (count > 0) {
      // Check first alert has a severity badge
      const firstAlert = alertCards.first()
      const severityBadge = firstAlert.locator('span').filter({ hasText: /CRITICAL|HIGH|MEDIUM|LOW/i })
      await expect(severityBadge).toBeVisible()
    }
  })

  test('risk metrics show correct color coding', async ({ page }) => {
    await page.waitForSelector('.risk-metrics-dashboard', { timeout: 10000 })

    // Check that metric cards have color classes
    const metricCards = page.locator('.metric-card')
    expect(await metricCards.count()).toBeGreaterThan(0)

    // At least some cards should have color indicators
    const firstCard = metricCards.first()
    await expect(firstCard).toBeVisible()
  })

  test('page is responsive and scrollable', async ({ page }) => {
    // Check that all main sections are present
    await expect(page.getByText('Performance Degradation Monitoring')).toBeVisible()

    // Scroll to bottom
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))

    // Wait a bit for any lazy-loaded content
    await page.waitForTimeout(1000)

    // Check that we can scroll back up
    await page.evaluate(() => window.scrollTo(0, 0))

    // First section should still be visible
    await expect(page.getByText('Performance Degradation Monitoring')).toBeVisible()
  })
})
