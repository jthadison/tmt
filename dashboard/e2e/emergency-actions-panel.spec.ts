/**
 * Playwright E2E tests for Emergency Actions Panel
 * Story 2.2: Emergency Actions Panel & Circuit Breaker Dashboard
 */

import { test, expect, Page } from '@playwright/test';

test.describe('Emergency Actions Panel', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard
    await page.goto('/');

    // Wait for page to load
    await page.waitForLoadState('networkidle');
  });

  test('should display emergency actions button in header', async ({ page }) => {
    // Check button is visible with data attribute
    const emergencyActionsButton = page.locator('[data-emergency-actions-button]');
    await expect(emergencyActionsButton).toBeVisible();

    // Check button styling (amber background)
    await expect(emergencyActionsButton).toHaveClass(/bg-amber-600/);

    // Check button text
    await expect(emergencyActionsButton).toContainText('Emergency Actions');
  });

  test('should show tooltip on hover', async ({ page }) => {
    const emergencyActionsButton = page.locator('[data-emergency-actions-button]');

    // Hover over button
    await emergencyActionsButton.hover();

    // Check tooltip appears
    await expect(page.getByText(/Emergency Actions Panel.*Alt\+E/i)).toBeVisible();
  });

  test('should open panel when button clicked', async ({ page }) => {
    const emergencyActionsButton = page.locator('[data-emergency-actions-button]');

    // Click button
    await emergencyActionsButton.click();

    // Wait for panel animation
    await page.waitForTimeout(350);

    // Check panel opens with title
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText('Emergency Actions', { exact: true })).toBeVisible();

    // Check quick actions are visible
    await expect(page.getByRole('button', { name: /Stop Trading/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Close All Positions/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Emergency Rollback/i })).toBeVisible();
  });

  test('should trigger panel with Alt+E keyboard shortcut', async ({ page }) => {
    // Press Alt+E
    await page.keyboard.press('Alt+E');

    // Wait for panel animation
    await page.waitForTimeout(350);

    // Check panel opens
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText('Emergency Actions', { exact: true })).toBeVisible();
  });

  test('should toggle panel with Alt+E (open and close)', async ({ page }) => {
    // Open panel
    await page.keyboard.press('Alt+E');
    await page.waitForTimeout(350);
    await expect(page.getByRole('dialog')).toBeVisible();

    // Close panel
    await page.keyboard.press('Alt+E');
    await page.waitForTimeout(350);
    await expect(page.getByRole('dialog')).not.toBeVisible();
  });

  test('should close panel when clicking backdrop', async ({ page }) => {
    const emergencyActionsButton = page.locator('[data-emergency-actions-button]');

    // Open panel
    await emergencyActionsButton.click();
    await page.waitForTimeout(350);
    await expect(page.getByRole('dialog')).toBeVisible();

    // Click backdrop (semi-transparent overlay)
    await page.locator('.fixed.inset-0.bg-black\\/50').click();

    // Wait for panel to close
    await page.waitForTimeout(350);
    await expect(page.getByRole('dialog')).not.toBeVisible();
  });

  test('should close panel when clicking close button (X)', async ({ page }) => {
    const emergencyActionsButton = page.locator('[data-emergency-actions-button]');

    // Open panel
    await emergencyActionsButton.click();
    await page.waitForTimeout(350);
    await expect(page.getByRole('dialog')).toBeVisible();

    // Find and click close button
    const closeButton = page.getByRole('button', { name: /close panel/i });
    await closeButton.click();

    // Wait for panel to close
    await page.waitForTimeout(350);
    await expect(page.getByRole('dialog')).not.toBeVisible();
  });

  test('should close panel when pressing Escape key', async ({ page }) => {
    const emergencyActionsButton = page.locator('[data-emergency-actions-button]');

    // Open panel
    await emergencyActionsButton.click();
    await page.waitForTimeout(350);
    await expect(page.getByRole('dialog')).toBeVisible();

    // Press Escape
    await page.keyboard.press('Escape');

    // Wait for panel to close
    await page.waitForTimeout(350);
    await expect(page.getByRole('dialog')).not.toBeVisible();
  });

  test('should display Circuit Breaker widget with thresholds', async ({ page }) => {
    const emergencyActionsButton = page.locator('[data-emergency-actions-button]');

    // Open panel
    await emergencyActionsButton.click();
    await page.waitForTimeout(350);

    // Check Circuit Breaker section exists
    await expect(page.getByText('Circuit Breakers')).toBeVisible();

    // Check for threshold displays (even if loading or error)
    const circuitBreakerWidget = page.locator('.bg-gray-800.rounded-lg').last();
    await expect(circuitBreakerWidget).toBeVisible();
  });

  test('should show help tooltip when clicking help button', async ({ page }) => {
    const emergencyActionsButton = page.locator('[data-emergency-actions-button]');

    // Open panel
    await emergencyActionsButton.click();
    await page.waitForTimeout(350);

    // Find and click help button (?)
    const helpButton = page.getByRole('button', { name: /show keyboard shortcuts/i });
    await helpButton.click();

    // Check help content appears
    await expect(page.getByText('Keyboard Shortcuts')).toBeVisible();
    await expect(page.getByText(/Alt\+E/)).toBeVisible();
    await expect(page.getByText(/Ctrl\+Shift\+S/)).toBeVisible();
    await expect(page.getByText(/Ctrl\+Shift\+C/)).toBeVisible();
    await expect(page.getByText(/Ctrl\+Shift\+R/)).toBeVisible();
  });

  test('should display all three quick action buttons with correct colors', async ({ page }) => {
    const emergencyActionsButton = page.locator('[data-emergency-actions-button]');

    // Open panel
    await emergencyActionsButton.click();
    await page.waitForTimeout(350);

    // Check Stop Trading (red)
    const stopButton = page.getByRole('button', { name: /Stop Trading/i });
    await expect(stopButton).toBeVisible();
    await expect(stopButton).toHaveClass(/bg-red-600/);

    // Check Close All Positions (orange)
    const closeButton = page.getByRole('button', { name: /Close All Positions/i });
    await expect(closeButton).toBeVisible();
    await expect(closeButton).toHaveClass(/bg-orange-600/);

    // Check Emergency Rollback (purple)
    const rollbackButton = page.getByRole('button', { name: /Emergency Rollback/i });
    await expect(rollbackButton).toBeVisible();
    await expect(rollbackButton).toHaveClass(/bg-purple-600/);
  });

  test('should display keyboard shortcuts on quick action buttons', async ({ page }) => {
    const emergencyActionsButton = page.locator('[data-emergency-actions-button]');

    // Open panel
    await emergencyActionsButton.click();
    await page.waitForTimeout(350);

    // Check shortcuts are displayed on buttons
    await expect(page.getByText('Ctrl+Shift+S')).toBeVisible();
    await expect(page.getByText('Ctrl+Shift+C')).toBeVisible();
    await expect(page.getByText('Ctrl+Shift+R')).toBeVisible();
  });
});

test.describe('Close Positions Modal', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Open emergency actions panel
    await page.keyboard.press('Alt+E');
    await page.waitForTimeout(350);
  });

  test('should open Close Positions modal when clicking quick action', async ({ page }) => {
    // Click Close All Positions button
    const closeButton = page.getByRole('button', { name: /Close All Positions/i });
    await closeButton.click();

    // Wait for modal
    await page.waitForTimeout(200);

    // Check modal opens
    await expect(page.getByText('⚠️ Close All Positions')).toBeVisible();
    await expect(page.getByText(/Current Open Positions/i)).toBeVisible();
  });

  test('should trigger Close Positions modal with Ctrl+Shift+C when panel is open', async ({ page }) => {
    // Press Ctrl+Shift+C
    await page.keyboard.press('Control+Shift+C');

    // Wait for modal
    await page.waitForTimeout(200);

    // Check modal opens
    await expect(page.getByText('⚠️ Close All Positions')).toBeVisible();
  });

  test('should require typed "CLOSE" confirmation', async ({ page }) => {
    // Open modal
    const closeButton = page.getByRole('button', { name: /Close All Positions/i });
    await closeButton.click();
    await page.waitForTimeout(200);

    // Find confirmation input
    const confirmInput = page.getByPlaceholder(/Type CLOSE/i);
    await expect(confirmInput).toBeVisible();

    // Confirm button should be disabled initially
    const confirmButton = page.getByRole('button', { name: /Close All Positions$/i }).last();
    await expect(confirmButton).toBeDisabled();

    // Type "CLOSE"
    await confirmInput.fill('CLOSE');

    // Confirm button should now be enabled
    await expect(confirmButton).toBeEnabled();
  });

  test('should show cancel button and allow cancellation', async ({ page }) => {
    // Open modal
    const closeButton = page.getByRole('button', { name: /Close All Positions/i });
    await closeButton.click();
    await page.waitForTimeout(200);

    // Find and click cancel button
    const cancelButton = page.getByRole('button', { name: /Cancel/i });
    await expect(cancelButton).toBeVisible();
    await cancelButton.click();

    // Modal should close
    await page.waitForTimeout(200);
    await expect(page.getByText('⚠️ Close All Positions')).not.toBeVisible();
  });
});

test.describe('Emergency Rollback Modal', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Open emergency actions panel
    await page.keyboard.press('Alt+E');
    await page.waitForTimeout(350);
  });

  test('should open Emergency Rollback modal when clicking quick action', async ({ page }) => {
    // Click Emergency Rollback button
    const rollbackButton = page.getByRole('button', { name: /Emergency Rollback/i });
    await rollbackButton.click();

    // Wait for modal
    await page.waitForTimeout(200);

    // Check modal opens
    await expect(page.getByText('⚠️ Emergency Rollback')).toBeVisible();
    await expect(page.getByText(/Rollback Configuration/i)).toBeVisible();
  });

  test('should trigger Emergency Rollback modal with Ctrl+Shift+R when panel is open', async ({ page }) => {
    // Press Ctrl+Shift+R
    await page.keyboard.press('Control+Shift+R');

    // Wait for modal
    await page.waitForTimeout(200);

    // Check modal opens
    await expect(page.getByText('⚠️ Emergency Rollback')).toBeVisible();
  });

  test('should have mode selection dropdown', async ({ page }) => {
    // Open modal
    const rollbackButton = page.getByRole('button', { name: /Emergency Rollback/i });
    await rollbackButton.click();
    await page.waitForTimeout(200);

    // Check dropdown exists
    const dropdown = page.locator('#target-mode');
    await expect(dropdown).toBeVisible();

    // Check dropdown has options
    await expect(dropdown).toHaveValue(/universal|session/);
  });

  test('should require typed "ROLLBACK" confirmation', async ({ page }) => {
    // Open modal
    const rollbackButton = page.getByRole('button', { name: /Emergency Rollback/i });
    await rollbackButton.click();
    await page.waitForTimeout(200);

    // Find confirmation input
    const confirmInput = page.getByPlaceholder(/Type ROLLBACK/i);
    await expect(confirmInput).toBeVisible();

    // Confirm button should be disabled initially
    const confirmButton = page.getByRole('button', { name: /Execute Rollback/i });
    await expect(confirmButton).toBeDisabled();

    // Type "ROLLBACK"
    await confirmInput.fill('ROLLBACK');

    // Confirm button should now be enabled
    await expect(confirmButton).toBeEnabled();
  });
});

test.describe('Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should have proper ARIA attributes for panel', async ({ page }) => {
    const emergencyActionsButton = page.locator('[data-emergency-actions-button]');

    // Open panel
    await emergencyActionsButton.click();
    await page.waitForTimeout(350);

    // Check dialog role
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();

    // Check aria-modal
    await expect(dialog).toHaveAttribute('aria-modal', 'true');

    // Check aria-labelledby
    await expect(dialog).toHaveAttribute('aria-labelledby', 'emergency-panel-title');
  });

  test('should support keyboard navigation within panel', async ({ page }) => {
    const emergencyActionsButton = page.locator('[data-emergency-actions-button]');

    // Open panel
    await emergencyActionsButton.click();
    await page.waitForTimeout(350);

    // Tab through interactive elements
    await page.keyboard.press('Tab'); // Help button
    await page.keyboard.press('Tab'); // Close button
    await page.keyboard.press('Tab'); // Stop Trading button
    await page.keyboard.press('Tab'); // Close Positions button
    await page.keyboard.press('Tab'); // Emergency Rollback button

    // Press Enter on focused element (should be Emergency Rollback)
    await page.keyboard.press('Enter');

    // Wait for rollback modal
    await page.waitForTimeout(200);

    // Check rollback modal opened
    await expect(page.getByText('⚠️ Emergency Rollback')).toBeVisible();
  });

  test('should have proper ARIA labels for buttons', async ({ page }) => {
    const emergencyActionsButton = page.locator('[data-emergency-actions-button]');
    await expect(emergencyActionsButton).toHaveAttribute('aria-label', 'Open emergency actions panel');
  });
});
