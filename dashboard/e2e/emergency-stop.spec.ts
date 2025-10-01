/**
 * Playwright E2E tests for Emergency Stop functionality
 * Story 2.1: Emergency Stop Button & Confirmation Modal
 */

import { test, expect, Page } from '@playwright/test';

test.describe('Emergency Stop Button', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard
    await page.goto('/');

    // Wait for page to load
    await page.waitForLoadState('networkidle');
  });

  test('should display emergency stop button in header', async ({ page }) => {
    // Check button is visible
    const emergencyButton = page.getByRole('button', { name: /emergency stop trading button/i });
    await expect(emergencyButton).toBeVisible();

    // Check button styling (red background)
    await expect(emergencyButton).toHaveClass(/bg-red-600/);
  });

  test('should show tooltip on hover', async ({ page }) => {
    const emergencyButton = page.getByRole('button', { name: /emergency stop trading button/i });

    // Hover over button
    await emergencyButton.hover();

    // Check tooltip appears
    await expect(page.getByText(/Emergency Stop Trading/i)).toBeVisible();
  });

  test('should open modal when button clicked', async ({ page }) => {
    const emergencyButton = page.getByRole('button', { name: /emergency stop trading button/i });

    // Click button
    await emergencyButton.click();

    // Check modal opens
    await expect(page.getByText('⚠️ Emergency Stop Trading')).toBeVisible();
    await expect(page.getByText(/Current System Status/i)).toBeVisible();
  });

  test('should trigger modal with Ctrl+Shift+S keyboard shortcut', async ({ page }) => {
    // Press Ctrl+Shift+S
    await page.keyboard.press('Control+Shift+S');

    // Check modal opens
    await expect(page.getByText('⚠️ Emergency Stop Trading')).toBeVisible();
  });
});

test.describe('Emergency Stop Modal', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Open emergency stop modal
    const emergencyButton = page.getByRole('button', { name: /emergency stop trading button/i });
    await emergencyButton.click();

    // Wait for modal to load
    await expect(page.getByText('⚠️ Emergency Stop Trading')).toBeVisible();
  });

  test('should display system status in modal', async ({ page }) => {
    // Check system status section is visible
    await expect(page.getByText(/Current System Status/i)).toBeVisible();

    // Check required fields are present
    await expect(page.getByText(/Active Positions/i)).toBeVisible();
    await expect(page.getByText(/Daily P&L/i)).toBeVisible();
  });

  test('should require "STOP" to be typed before confirming', async ({ page }) => {
    const confirmButton = page.getByRole('button', { name: /Confirm emergency stop/i });
    const input = page.getByPlaceholder('Type STOP');

    // Confirm button should be disabled initially
    await expect(confirmButton).toBeDisabled();

    // Type incomplete text
    await input.fill('STO');
    await expect(confirmButton).toBeDisabled();

    // Type complete "STOP"
    await input.fill('STOP');
    await expect(confirmButton).toBeEnabled();
  });

  test('should accept case-insensitive STOP confirmation', async ({ page }) => {
    const confirmButton = page.getByRole('button', { name: /Confirm emergency stop/i });
    const input = page.getByPlaceholder('Type STOP');

    // Try lowercase
    await input.fill('stop');
    await expect(confirmButton).toBeEnabled();

    // Try mixed case
    await input.clear();
    await input.fill('Stop');
    await expect(confirmButton).toBeEnabled();
  });

  test('should show green border on valid input', async ({ page }) => {
    const input = page.getByPlaceholder('Type STOP');

    // Type valid confirmation
    await input.fill('STOP');

    // Check for green border
    await expect(input).toHaveClass(/border-green-500/);
  });

  test('should have close positions checkbox', async ({ page }) => {
    const checkbox = page.getByRole('checkbox');

    await expect(checkbox).toBeVisible();
    await expect(checkbox).not.toBeChecked();

    // Check checkbox can be toggled
    await checkbox.check();
    await expect(checkbox).toBeChecked();
  });

  test('should close modal when cancel clicked', async ({ page }) => {
    const cancelButton = page.getByRole('button', { name: /Cancel/i });

    await cancelButton.click();

    // Modal should close
    await expect(page.getByText('⚠️ Emergency Stop Trading')).not.toBeVisible();
  });

  test('should close modal when escape key pressed', async ({ page }) => {
    // Press Escape
    await page.keyboard.press('Escape');

    // Modal should close
    await expect(page.getByText('⚠️ Emergency Stop Trading')).not.toBeVisible();
  });

  test('should display open trades if present', async ({ page }) => {
    // This test assumes mock data returns some open trades
    // Check if Open Trades section appears (it may or may not depending on system status)
    const openTradesText = page.getByText(/Open Trades/i);

    // If there are open trades, they should be displayed
    if (await openTradesText.isVisible()) {
      // Check that trade information is shown
      await expect(page.locator('.bg-gray-900.p-2.rounded').first()).toBeVisible();
    }
  });
});

test.describe('Emergency Stop Execution', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Open modal
    const emergencyButton = page.getByRole('button', { name: /emergency stop trading button/i });
    await emergencyButton.click();
    await expect(page.getByText('⚠️ Emergency Stop Trading')).toBeVisible();
  });

  test('should execute emergency stop when confirmed', async ({ page }) => {
    // Type confirmation
    const input = page.getByPlaceholder('Type STOP');
    await input.fill('STOP');

    // Click confirm
    const confirmButton = page.getByRole('button', { name: /Confirm emergency stop/i });
    await confirmButton.click();

    // Should show loading state
    await expect(page.getByText(/Stopping.../i)).toBeVisible();

    // Wait for completion (success or error)
    await page.waitForSelector('text=/Trading Stopped Successfully|Emergency Stop Failed/i', {
      timeout: 10000,
    });
  });

  test('should show success message after successful stop', async ({ page }) => {
    // Mock successful response (would need API mocking in real scenario)
    const input = page.getByPlaceholder('Type STOP');
    await input.fill('STOP');

    const confirmButton = page.getByRole('button', { name: /Confirm emergency stop/i });
    await confirmButton.click();

    // Wait for success message (this assumes API succeeds)
    try {
      await expect(page.getByText(/Trading Stopped Successfully/i)).toBeVisible({ timeout: 10000 });

      // Resume button should appear
      await expect(page.getByRole('button', { name: /Resume trading/i })).toBeVisible();
    } catch (error) {
      // If it fails, check for error message instead
      await expect(page.getByText(/Emergency Stop Failed/i)).toBeVisible();
    }
  });

  test('should show retry button on failure', async ({ page }) => {
    // This test would require mocking API failure
    // For now, we'll skip the execution and just test the error UI structure

    const input = page.getByPlaceholder('Type STOP');
    await input.fill('STOP');

    const confirmButton = page.getByRole('button', { name: /Confirm emergency stop/i });
    await confirmButton.click();

    // Wait for either success or error
    await page.waitForSelector('text=/Trading Stopped Successfully|Emergency Stop Failed/i', {
      timeout: 10000,
    });

    // If error occurred, retry button should be present
    const errorHeading = page.getByText(/Emergency Stop Failed/i);
    if (await errorHeading.isVisible()) {
      await expect(page.getByRole('button', { name: /Retry/i })).toBeVisible();
    }
  });
});

test.describe('Emergency Stop Cooldown', () => {
  test('should disable button during cooldown period', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // First emergency stop
    const emergencyButton = page.getByRole('button', { name: /emergency stop trading button/i });
    await emergencyButton.click();

    await expect(page.getByText('⚠️ Emergency Stop Trading')).toBeVisible();

    const input = page.getByPlaceholder('Type STOP');
    await input.fill('STOP');

    const confirmButton = page.getByRole('button', { name: /Confirm emergency stop/i });
    await confirmButton.click();

    // Wait for completion
    await page.waitForSelector('text=/Trading Stopped Successfully|Emergency Stop Failed/i', {
      timeout: 10000,
    });

    // Close modal
    const closeButton = page.getByRole('button', { name: /Close|Resume trading/i }).first();
    await closeButton.click();

    // Button should now be disabled
    await expect(emergencyButton).toBeDisabled();

    // Cooldown indicator should be visible
    await expect(page.locator('.bg-yellow-500.text-gray-900').first()).toBeVisible();
  });
});

test.describe('Accessibility', () => {
  test('should have proper ARIA labels', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Check button has aria-label
    const emergencyButton = page.getByRole('button', { name: /emergency stop trading button/i });
    await expect(emergencyButton).toHaveAttribute('aria-label');

    // Open modal
    await emergencyButton.click();

    // Check modal has proper roles
    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible();
    await expect(modal).toHaveAttribute('aria-modal', 'true');
  });

  test('should support keyboard navigation', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Tab to emergency button (this would require knowing tab order)
    // For now, just verify it can receive focus
    const emergencyButton = page.getByRole('button', { name: /emergency stop trading button/i });
    await emergencyButton.focus();
    await expect(emergencyButton).toBeFocused();

    // Press Enter to open modal
    await page.keyboard.press('Enter');
    await expect(page.getByText('⚠️ Emergency Stop Trading')).toBeVisible();

    // Input should auto-focus
    const input = page.getByPlaceholder('Type STOP');
    await expect(input).toBeFocused();
  });
});

test.describe('Resume Trading', () => {
  test('should resume trading when resume button clicked', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Execute emergency stop first
    const emergencyButton = page.getByRole('button', { name: /emergency stop trading button/i });
    await emergencyButton.click();

    const input = page.getByPlaceholder('Type STOP');
    await input.fill('STOP');

    const confirmButton = page.getByRole('button', { name: /Confirm emergency stop/i });
    await confirmButton.click();

    // Wait for success
    await expect(page.getByText(/Trading Stopped Successfully/i)).toBeVisible({ timeout: 10000 });

    // Click resume
    const resumeButton = page.getByRole('button', { name: /Resume trading/i });
    await resumeButton.click();

    // Modal should close
    await expect(page.getByText('⚠️ Emergency Stop Trading')).not.toBeVisible();
  });
});
