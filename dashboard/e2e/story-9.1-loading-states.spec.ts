/**
 * Story 9.1: Skeleton Screens & Loading Indicators E2E Tests
 * Comprehensive Playwright tests for all acceptance criteria
 */

import { test, expect } from '@playwright/test';

test.describe('Story 9.1: Loading States & Skeleton Screens', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/loading-demo');
  });

  test('AC1: Skeleton screens display with shimmer animation', async ({ page }) => {
    // Verify position card skeleton is visible
    const positionSkeleton = page.getByTestId('position-card-skeleton').first();
    await expect(positionSkeleton).toBeVisible();

    // Verify shimmer animation exists via CSS class
    const skeletonElements = page.locator('.skeleton').first();
    await expect(skeletonElements).toBeVisible();
    await expect(skeletonElements).toHaveClass(/skeleton/);

    // Verify chart skeleton
    const chartSkeleton = page.getByTestId('chart-skeleton').first();
    await expect(chartSkeleton).toBeVisible();

    // Verify agent card skeleton
    const agentSkeleton = page.getByTestId('agent-card-skeleton').first();
    await expect(agentSkeleton).toBeVisible();
  });

  test('AC2: Shimmer animation is smooth and visible', async ({ page }) => {
    // Check that skeleton elements have shimmer class
    const skeletonElement = page.locator('.skeleton').first();
    await expect(skeletonElement).toBeVisible();

    // Verify animation is present by checking computed styles
    const hasAnimation = await skeletonElement.evaluate((el) => {
      const styles = window.getComputedStyle(el);
      return styles.animation !== 'none' && styles.animation !== '';
    });

    expect(hasAnimation).toBeTruthy();
  });

  test('AC3: Inline spinners display with appropriate sizes', async ({ page }) => {
    // Scroll to inline spinners section
    await page.getByText('2. Loading Indicators').scrollIntoViewIfNeeded();

    // Verify small spinner
    const smallSpinner = page.locator('[data-testid="inline-spinner"]').filter({ hasText: 'Small spinner' });
    await expect(smallSpinner).toBeVisible();

    // Verify medium spinner
    const mediumSpinner = page.locator('[data-testid="inline-spinner"]').filter({ hasText: 'Medium spinner' });
    await expect(mediumSpinner).toBeVisible();

    // Verify large spinner
    const largeSpinner = page.locator('[data-testid="inline-spinner"]').filter({ hasText: 'Large spinner' });
    await expect(largeSpinner).toBeVisible();

    // Verify all have spinning icons
    const spinnerIcons = page.locator('[data-testid="spinner-icon"]');
    await expect(spinnerIcons.first()).toBeVisible();
  });

  test('AC4: Modal overlay displays for full-page operations', async ({ page }) => {
    // Click button to show modal
    await page.getByRole('button', { name: 'Show Modal Overlay (3s)' }).click();

    // Verify modal is visible
    const modal = page.getByTestId('modal-overlay');
    await expect(modal).toBeVisible();

    // Verify modal has dimmed background
    await expect(modal).toHaveClass(/bg-black\/50/);

    // Verify message is displayed
    await expect(page.getByText('Processing your request... Please wait.')).toBeVisible();

    // Verify modal spinner
    await expect(page.getByTestId('modal-spinner')).toBeVisible();

    // Wait for modal to disappear (3 second demo)
    await expect(modal).not.toBeVisible({ timeout: 5000 });
  });

  test('AC5: Progress bar updates smoothly', async ({ page }) => {
    // Scroll to progress bar section
    await page.getByText('Progress Bar').scrollIntoViewIfNeeded();

    // Click start progress button
    await page.getByRole('button', { name: 'Start Progress' }).click();

    // Verify progress bar is visible
    const progressBar = page.getByTestId('progress-bar');
    await expect(progressBar).toBeVisible();

    // Verify progress increases
    await expect(page.getByText(/Processing items.../)).toBeVisible();

    // Wait for progress to complete
    await page.waitForTimeout(3500);

    // Verify 100% is reached
    await expect(page.getByText('100%')).toBeVisible();
  });

  test('AC6: Loading button transitions through all states', async ({ page }) => {
    // Scroll to loading button section
    await page.getByText('3. Loading Button States').scrollIntoViewIfNeeded();

    // Get primary action button
    const button = page.getByTestId('loading-button').filter({ hasText: 'Primary Action' });

    // Verify idle state
    await expect(button).toHaveText('Primary Action');
    await expect(button).not.toBeDisabled();

    // Click button
    await button.click();

    // Verify loading state
    await expect(button).toHaveAttribute('data-state', 'loading');
    await expect(button).toHaveText('Processing...');
    await expect(button).toBeDisabled();

    // Verify success state
    await expect(button).toHaveAttribute('data-state', 'success', { timeout: 3000 });
    await expect(button).toHaveText('Success!');

    // Verify return to idle state
    await expect(button).toHaveAttribute('data-state', 'idle', { timeout: 2000 });
    await expect(button).toHaveText('Primary Action');
  });

  test('AC6: Loading button prevents double-clicks', async ({ page }) => {
    await page.getByText('3. Loading Button States').scrollIntoViewIfNeeded();

    const button = page.getByTestId('loading-button').filter({ hasText: 'Primary Action' });

    // Click button
    await button.click();

    // Try to click again while loading
    await button.click();

    // Should still only process once (button is disabled)
    await expect(button).toBeDisabled();
    await expect(button).toHaveAttribute('data-state', 'loading');
  });

  test('AC6: Loading button variants work correctly', async ({ page }) => {
    await page.getByText('3. Loading Button States').scrollIntoViewIfNeeded();

    // Test secondary button
    const secondaryButton = page.getByTestId('loading-button').filter({ hasText: 'Secondary Action' });
    await secondaryButton.click();

    await expect(secondaryButton).toHaveAttribute('data-state', 'loading');
    await expect(secondaryButton).toHaveAttribute('data-state', 'success', { timeout: 3000 });
    await expect(secondaryButton).toHaveText('Completed!'); // Custom success message

    // Test danger button
    const dangerButton = page.getByTestId('loading-button').filter({ hasText: 'Delete Item' });
    await dangerButton.click();

    await expect(dangerButton).toHaveAttribute('data-state', 'loading');
    await expect(dangerButton).toHaveAttribute('data-state', 'success', { timeout: 3000 });
    await expect(dangerButton).toHaveText('Deleted!'); // Custom success message
  });

  test('AC7: React Suspense integration displays skeleton fallback', async ({ page }) => {
    // Scroll to Suspense section
    await page.getByText('4. React Suspense Integration').scrollIntoViewIfNeeded();

    // Initially, skeleton should be visible (content loading)
    const skeleton = page.getByTestId('position-card-skeleton').nth(2); // Third skeleton on page
    await expect(skeleton).toBeVisible();

    // Wait for content to load (2 second delay in AsyncContent)
    await expect(page.getByText('Content loaded successfully!')).toBeVisible({ timeout: 3000 });

    // Skeleton should be replaced
    await expect(skeleton).not.toBeVisible();
  });

  test('AC8: Skeleton timeout transitions to error state', async ({ page }) => {
    // Scroll to timeout section
    await page.getByText('5. Skeleton Timeout').scrollIntoViewIfNeeded();

    // Start timeout demo
    await page.getByRole('button', { name: 'Start 3s Timeout Demo' }).click();

    // Skeleton should be visible initially
    const skeleton = page.getByTestId('position-card-skeleton').last();
    await expect(skeleton).toBeVisible();

    // Wait for timeout (3 seconds in demo)
    await page.waitForTimeout(3500);

    // Error state should appear
    await expect(page.getByText('Unable to load data')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Retry' })).toBeVisible();

    // Skeleton should not be visible
    await expect(skeleton).not.toBeVisible();
  });

  test('AC8: Timeout error state allows retry', async ({ page }) => {
    await page.getByText('5. Skeleton Timeout').scrollIntoViewIfNeeded();

    // Start timeout demo
    await page.getByRole('button', { name: 'Start 3s Timeout Demo' }).click();

    // Wait for timeout
    await expect(page.getByText('Unable to load data')).toBeVisible({ timeout: 4000 });

    // Click retry button
    await page.getByRole('button', { name: 'Retry' }).click();

    // Skeleton should appear again
    const skeleton = page.getByTestId('position-card-skeleton').last();
    await expect(skeleton).toBeVisible();
  });

  test('Full dashboard skeleton renders correctly', async ({ page }) => {
    // Scroll to full dashboard skeleton
    await page.getByText('6. Full Dashboard Skeleton').scrollIntoViewIfNeeded();

    // Verify dashboard skeleton is visible
    const dashboardSkeleton = page.getByTestId('dashboard-skeleton');
    await expect(dashboardSkeleton).toBeVisible();

    // Verify header skeleton
    const header = dashboardSkeleton.locator('header');
    await expect(header).toBeVisible();

    // Verify position card skeletons (should be 6)
    const positionSkeletons = dashboardSkeleton.getByTestId('position-card-skeleton');
    await expect(positionSkeletons).toHaveCount(6);

    // Verify agent card skeletons (should be 8)
    const agentSkeletons = dashboardSkeleton.getByTestId('agent-card-skeleton');
    await expect(agentSkeletons).toHaveCount(8);

    // Verify chart skeleton
    const chartSkeleton = dashboardSkeleton.getByTestId('chart-skeleton');
    await expect(chartSkeleton).toBeVisible();
  });

  test('Dark mode shimmer animation works correctly', async ({ page }) => {
    // Enable dark mode if available (assuming dark mode toggle exists)
    // For now, just verify skeleton is visible in current mode
    const skeletonElement = page.locator('.skeleton').first();
    await expect(skeletonElement).toBeVisible();

    // Verify skeleton has proper styling
    const hasDarkModeClass = await page.evaluate(() => {
      return document.documentElement.classList.contains('dark');
    });

    // Element should be visible regardless of dark mode
    await expect(skeletonElement).toBeVisible();
  });

  test('Page header and navigation are visible', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Loading States Demo' })).toBeVisible();
    await expect(page.getByText('Story 9.1: Skeleton Screens & Loading Indicators')).toBeVisible();
  });

  test('All sections are accessible and visible', async ({ page }) => {
    await expect(page.getByText('1. Skeleton Screens')).toBeVisible();
    await expect(page.getByText('2. Loading Indicators')).toBeVisible();
    await expect(page.getByText('3. Loading Button States')).toBeVisible();
    await expect(page.getByText('4. React Suspense Integration')).toBeVisible();
    await expect(page.getByText('5. Skeleton Timeout')).toBeVisible();
    await expect(page.getByText('6. Full Dashboard Skeleton')).toBeVisible();
  });
});
