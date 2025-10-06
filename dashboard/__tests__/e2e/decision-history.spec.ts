/**
 * Playwright E2E tests for Agent Decision History & Pattern Detection
 * Story 7.2: End-to-End Tests
 */

import { test, expect } from '@playwright/test';

test.describe('Agent Decision History & Pattern Detection', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to decision history demo page
    await page.goto('http://localhost:3003/intelligence/decision-history');
  });

  test('should display page title and description', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Agent Decision History & Pattern Detection');
    await expect(page.getByText('Story 7.2')).toBeVisible();
  });

  test('should display agent decision history card with attribution', async ({ page }) => {
    // Wait for the card to be visible
    await expect(page.getByTestId('agent-decision-history-card').first()).toBeVisible();

    // Check header is present
    await expect(page.getByText('Agent Decision History')).toBeVisible();
  });

  test('should display primary agent information', async ({ page }) => {
    const card = page.getByTestId('agent-decision-history-card').first();

    // Primary agent name
    await expect(card.getByText('Market Analysis')).toBeVisible();

    // Confidence meter
    await expect(card.getByTestId('confidence-meter')).toBeVisible();

    // Reasoning points
    await expect(card.getByText(/Strong bullish momentum/)).toBeVisible();
    await expect(card.getByText(/Price broke above resistance/)).toBeVisible();
  });

  test('should display confirming agents section', async ({ page }) => {
    const card = page.getByTestId('agent-decision-history-card').first();

    // Confirming agents header
    await expect(card.getByText(/Confirming Agents/)).toBeVisible();

    // Confirming agent name
    await expect(card.getByText('Pattern Detection')).toBeVisible();
  });

  test('should display consensus percentage', async ({ page }) => {
    const card = page.getByTestId('agent-decision-history-card').first();

    await expect(card.getByText('Consensus at Trade Time')).toBeVisible();
    await expect(card.getByText('78%')).toBeVisible();
  });

  test('should display session context', async ({ page }) => {
    const card = page.getByTestId('agent-decision-history-card').first();

    await expect(card.getByText('Session')).toBeVisible();
    await expect(card.getByText('London Session')).toBeVisible();
  });

  test('should display outcome badge', async ({ page }) => {
    const card = page.getByTestId('agent-decision-history-card').first();

    await expect(card.getByTestId('outcome-badge')).toBeVisible();
    await expect(card.getByText('WIN')).toBeVisible();
    await expect(card.getByText(/\+\$125\.50/)).toBeVisible();
  });

  test('should display pattern detected section', async ({ page }) => {
    const card = page.getByTestId('agent-decision-history-card').first();

    await expect(card.getByText('Pattern Detected')).toBeVisible();
    await expect(card.getByText('Wyckoff Accumulation Phase E')).toBeVisible();

    // Key levels
    await expect(card.getByText('Entry:')).toBeVisible();
    await expect(card.getByText('Target:')).toBeVisible();
    await expect(card.getByText('Stop Loss:')).toBeVisible();
  });

  test('should display empty state for trade without attribution', async ({ page }) => {
    // Scroll to second example
    const cards = page.getByTestId('agent-decision-history-card');
    await expect(cards.nth(1)).toBeVisible();

    await expect(cards.nth(1).getByText(/No agent attribution data available/)).toBeVisible();
  });

  test('should open similar patterns modal when button clicked', async ({ page }) => {
    // Click "View Similar Wyckoff Patterns" button
    await page.getByRole('button', { name: /View Similar Wyckoff Patterns/i }).click();

    // Modal should be visible
    await expect(page.getByTestId('similar-patterns-modal')).toBeVisible();

    // Modal title
    await expect(page.getByText('Similar Patterns: Wyckoff Accumulation')).toBeVisible();
  });

  test('should display pattern statistics in modal', async ({ page }) => {
    // Open modal
    await page.getByRole('button', { name: /View Similar Wyckoff Patterns/i }).click();

    // Wait for modal to load
    await expect(page.getByTestId('similar-patterns-modal')).toBeVisible();

    // Check for stat cards
    await expect(page.getByText('Win Rate')).toBeVisible();
    await expect(page.getByText('Avg Profit')).toBeVisible();
    await expect(page.getByText('Avg Loss')).toBeVisible();
    await expect(page.getByText('Total Trades')).toBeVisible();
  });

  test('should close modal when close button clicked', async ({ page }) => {
    // Open modal
    await page.getByRole('button', { name: /View Similar Wyckoff Patterns/i }).click();
    await expect(page.getByTestId('similar-patterns-modal')).toBeVisible();

    // Click close button
    await page.getByRole('button', { name: /Close modal/i }).click();

    // Modal should be hidden
    await expect(page.getByTestId('similar-patterns-modal')).not.toBeVisible();
  });

  test('should close modal when clicking outside', async ({ page }) => {
    // Open modal
    await page.getByRole('button', { name: /View Similar Wyckoff Patterns/i }).click();
    await expect(page.getByTestId('similar-patterns-modal')).toBeVisible();

    // Click on backdrop (outside modal content)
    await page.locator('.fixed.inset-0').click({ position: { x: 10, y: 10 } });

    // Modal should be hidden
    await expect(page.getByTestId('similar-patterns-modal')).not.toBeVisible();
  });

  test('should display feature overview section', async ({ page }) => {
    await expect(page.getByText('Story 7.2 Features')).toBeVisible();

    // Feature cards
    await expect(page.getByText('Agent Decision History')).toBeVisible();
    await expect(page.getByText('Pattern Detection Overlays')).toBeVisible();
    await expect(page.getByText('Pattern Tooltips')).toBeVisible();
    await expect(page.getByText('Similar Patterns Modal')).toBeVisible();
  });

  test('should display all implemented status badges', async ({ page }) => {
    const implementedBadges = page.getByText('Implemented');
    const count = await implementedBadges.count();

    expect(count).toBe(4); // 4 features implemented
  });

  test('should show different pattern types in modal', async ({ page }) => {
    // Open Spring patterns modal
    await page.getByRole('button', { name: /View Similar Spring Patterns/i }).click();

    await expect(page.getByTestId('similar-patterns-modal')).toBeVisible();
    await expect(page.getByText('Similar Patterns: Spring')).toBeVisible();
  });

  test('should handle mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Page should still be visible and functional
    await expect(page.getByText('Agent Decision History & Pattern Detection')).toBeVisible();

    const card = page.getByTestId('agent-decision-history-card').first();
    await expect(card).toBeVisible();

    // Confirming agents should stack on mobile
    const confirmingAgents = card.getByTestId(/confirming-agent-/);
    await expect(confirmingAgents.first()).toBeVisible();
  });

  test('should display confidence meters with correct styling', async ({ page }) => {
    const card = page.getByTestId('agent-decision-history-card').first();
    const confidenceMeters = card.getByTestId('confidence-meter');

    // At least one confidence meter should be visible
    await expect(confidenceMeters.first()).toBeVisible();

    // Confidence bar should be visible
    const confidenceBar = card.getByTestId('confidence-bar').first();
    await expect(confidenceBar).toBeVisible();

    // Bar should have width based on confidence (85%)
    const width = await confidenceBar.evaluate((el) => getComputedStyle(el).width);
    expect(width).not.toBe('0px');
  });

  test('should navigate between examples', async ({ page }) => {
    // Scroll to second example
    await page.getByText('Example 2: Trade Without Agent Attribution').scrollIntoViewIfNeeded();

    const secondCard = page.getByTestId('agent-decision-history-card').nth(1);
    await expect(secondCard).toBeInViewport();
  });

  test('should have accessible elements', async ({ page }) => {
    // Check for proper ARIA labels
    const outcomeBadge = page.getByTestId('outcome-badge').first();
    await expect(outcomeBadge).toBeVisible();

    // Confidence meter should have progress bar role
    const progressBar = page.getByRole('progressbar').first();
    await expect(progressBar).toBeVisible();
  });

  test('should load without JavaScript errors', async ({ page }) => {
    const errors: string[] = [];

    page.on('pageerror', (error) => {
      errors.push(error.message);
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    expect(errors).toHaveLength(0);
  });

  test('should perform well on load', async ({ page }) => {
    const startTime = Date.now();

    await page.goto('http://localhost:3003/intelligence/decision-history');
    await page.waitForLoadState('networkidle');

    const loadTime = Date.now() - startTime;

    // Page should load in under 3 seconds
    expect(loadTime).toBeLessThan(3000);
  });
});
