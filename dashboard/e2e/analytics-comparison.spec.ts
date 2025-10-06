import { test, expect } from '@playwright/test'

test.describe('Analytics Comparison Page E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to comparison page
    await page.goto('/analytics/comparison')
  })

  test('should load and display the comparison page', async ({ page }) => {
    // Wait for page to load
    await expect(page.getByText('Forward Test vs. Backtest Comparison')).toBeVisible()
    await expect(page.getByText('Comprehensive analysis of strategy performance validation')).toBeVisible()
  })

  test('should display overview cards with period information', async ({ page }) => {
    // Wait for data to load
    await page.waitForSelector('text=Backtest Period', { timeout: 10000 })

    // Check backtest period card
    await expect(page.getByText('Backtest Period')).toBeVisible()
    await expect(page.getByText(/Days/).first()).toBeVisible()

    // Check forward test period card
    await expect(page.getByText('Forward Test Period')).toBeVisible()

    // Check total trades card
    await expect(page.getByText('Total Trades')).toBeVisible()
  })

  test('should display overfitting analysis dashboard', async ({ page }) => {
    // Wait for overfitting analysis section
    await page.waitForSelector('text=Overfitting Analysis', { timeout: 10000 })

    await expect(page.getByText('Overfitting Analysis')).toBeVisible()
    await expect(page.getByText('Overfitting Score')).toBeVisible()
    await expect(page.getByText('Avg Degradation')).toBeVisible()
    await expect(page.getByText('Risk Level')).toBeVisible()
  })

  test('should show risk level badge with correct styling', async ({ page }) => {
    await page.waitForSelector('text=Risk Level', { timeout: 10000 })

    // Check for risk level badge (Low Risk, Moderate Risk, or High Risk)
    const riskLevelBadge = page.locator('text=/Low Risk|Moderate Risk|High Risk/')
    await expect(riskLevelBadge).toBeVisible()
  })

  test('should display performance stability score', async ({ page }) => {
    await page.waitForSelector('text=Performance Stability', { timeout: 10000 })

    await expect(page.getByText('Performance Stability')).toBeVisible()
    await expect(page.getByText('/ 100')).toBeVisible()

    // Check for stability progress bar
    const progressBar = page.locator('.h-3.bg-muted.rounded-full')
    await expect(progressBar).toBeVisible()
  })

  test('should display metric comparison table', async ({ page }) => {
    await page.waitForSelector('text=Performance Metrics Comparison', { timeout: 10000 })

    await expect(page.getByText('Performance Metrics Comparison')).toBeVisible()

    // Check table headers
    await expect(page.getByText('Metric')).toBeVisible()
    await expect(page.getByText('Backtest')).toBeVisible()
    await expect(page.getByText('Forward Test')).toBeVisible()
    await expect(page.getByText('Variance')).toBeVisible()
    await expect(page.getByText('Status')).toBeVisible()
  })

  test('should display all key metrics in comparison table', async ({ page }) => {
    await page.waitForSelector('text=Win Rate', { timeout: 10000 })

    // Check for all metrics
    await expect(page.getByText('Win Rate')).toBeVisible()
    await expect(page.getByText('Avg Win')).toBeVisible()
    await expect(page.getByText('Avg Loss')).toBeVisible()
    await expect(page.getByText('Profit Factor')).toBeVisible()
    await expect(page.getByText('Max Drawdown')).toBeVisible()
    await expect(page.getByText('Sharpe Ratio')).toBeVisible()
  })

  test('should show variance percentages', async ({ page }) => {
    await page.waitForSelector('text=Performance Metrics Comparison', { timeout: 10000 })

    // Look for percentage values (positive or negative)
    const varianceCells = page.locator('text=/%/')
    const count = await varianceCells.count()
    expect(count).toBeGreaterThan(0)
  })

  test('should display status indicators (✓, ⚠, ✗)', async ({ page }) => {
    await page.waitForSelector('text=Performance Metrics Comparison', { timeout: 10000 })

    // Check for at least one status indicator
    const indicators = page.locator('text=/[✓⚠✗]/')
    const count = await indicators.count()
    expect(count).toBeGreaterThan(0)
  })

  test('should display cumulative returns chart', async ({ page }) => {
    await page.waitForSelector('text=Cumulative Returns Comparison', { timeout: 10000 })

    await expect(page.getByText('Cumulative Returns Comparison')).toBeVisible()
    await expect(page.getByText(/Historical backtest performance/)).toBeVisible()

    // Check for chart container
    const chartContainer = page.locator('.chart-container')
    await expect(chartContainer).toBeVisible()
  })

  test('should display metric degradation breakdown', async ({ page }) => {
    await page.waitForSelector('text=Metric Degradation Breakdown', { timeout: 10000 })

    await expect(page.getByText('Metric Degradation Breakdown')).toBeVisible()

    // Check for degradation table headers
    await expect(page.getByText('Metric').first()).toBeVisible()
    await expect(page.getByText('Backtest').first()).toBeVisible()
    await expect(page.getByText('Forward').first()).toBeVisible()
    await expect(page.getByText('Change').first()).toBeVisible()
  })

  test('should display recommendations section', async ({ page }) => {
    await page.waitForSelector('text=💡', { timeout: 10000 })

    await expect(page.getByText('Recommendations')).toBeVisible()

    // Check for at least one recommendation
    const recommendations = page.locator('ul li')
    const count = await recommendations.count()
    expect(count).toBeGreaterThan(0)
  })

  test('should display analysis methodology section', async ({ page }) => {
    await page.waitForSelector('text=Analysis Methodology', { timeout: 10000 })

    await expect(page.getByText('Analysis Methodology')).toBeVisible()
    await expect(page.getByText('Overfitting Score Calculation')).toBeVisible()
    await expect(page.getByText('Stability Score Calculation')).toBeVisible()
    await expect(page.getByText('Risk Thresholds')).toBeVisible()
  })

  test('should show interpretation text', async ({ page }) => {
    await page.waitForSelector('text=Overfitting Analysis', { timeout: 10000 })

    // Look for interpretation text containing risk assessment
    const interpretation = page.locator('text=/risk.*degradation/i')
    await expect(interpretation).toBeVisible()
  })

  test('should handle loading state gracefully', async ({ page }) => {
    // Navigate to page and immediately check for loading state
    await page.goto('/analytics/comparison')

    // Loading state might appear briefly
    const loadingText = page.getByText('Loading comparison analysis...')

    // Either loading appears or data loads immediately
    try {
      await expect(loadingText).toBeVisible({ timeout: 1000 })
    } catch {
      // Data loaded immediately, which is also valid
      await expect(page.getByText('Forward Test vs. Backtest Comparison')).toBeVisible()
    }
  })

  test('should display variance legend in comparison table', async ({ page }) => {
    await page.waitForSelector('text=Performance Metrics Comparison', { timeout: 10000 })

    // Scroll to legend
    await page.locator('text=<15% variance').scrollIntoViewIfNeeded()

    await expect(page.getByText(/<15% variance/)).toBeVisible()
    await expect(page.getByText(/15-30% variance/)).toBeVisible()
    await expect(page.getByText(/>30% variance/)).toBeVisible()
  })

  test('should be responsive on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/analytics/comparison')

    await page.waitForSelector('text=Forward Test vs. Backtest Comparison', { timeout: 10000 })

    // Page should still be functional on mobile
    await expect(page.getByText('Forward Test vs. Backtest Comparison')).toBeVisible()
    await expect(page.getByText('Overfitting Analysis')).toBeVisible()
  })

  test('should show data sources in methodology section', async ({ page }) => {
    await page.waitForSelector('text=Data Sources', { timeout: 10000 })

    await expect(page.getByText('Data Sources')).toBeVisible()
    await expect(page.getByText(/Backtest:/)).toBeVisible()
    await expect(page.getByText(/Forward Test:/)).toBeVisible()
  })
})
