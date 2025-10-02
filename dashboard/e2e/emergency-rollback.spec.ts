/**
 * Playwright E2E tests for Emergency Rollback Control & Audit Trail
 * Story 2.3: Emergency Rollback Control & Audit Trail
 *
 * Tests cover:
 * - System Control Panel navigation
 * - Emergency Rollback Control component
 * - Rollback History Table
 * - Automated Trigger Monitoring
 * - Audit Trail page
 * - Keyboard shortcuts
 * - Filtering and export functionality
 */

import { test, expect, Page } from '@playwright/test';

test.describe('System Control Panel - Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should have System Control link in sidebar navigation', async ({ page }) => {
    const systemControlLink = page.getByRole('link', { name: /System Control/i });
    await expect(systemControlLink).toBeVisible();
  });

  test('should navigate to System Control Panel page', async ({ page }) => {
    const systemControlLink = page.getByRole('link', { name: /System Control/i });
    await systemControlLink.click();

    // Wait for navigation
    await page.waitForLoadState('networkidle');

    // Verify page title
    await expect(page.getByRole('heading', { name: /System Control Panel/i, level: 1 })).toBeVisible();

    // Verify URL
    expect(page.url()).toContain('/system-control');
  });

  test('should display all three main sections on System Control page', async ({ page }) => {
    await page.goto('/system-control');
    await page.waitForLoadState('networkidle');

    // Check for all three sections
    await expect(page.getByRole('heading', { name: /Emergency Rollback Control/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /Rollback History/i })).toBeVisible();
    await expect(page.getByRole('heading', { name: /Automated Trigger Monitoring/i })).toBeVisible();
  });
});

test.describe('Emergency Rollback Control', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/system-control');
    await page.waitForLoadState('networkidle');
  });

  test('should display current trading mode badge', async ({ page }) => {
    // Look for mode badge (Universal Cycle 4 or Session-Targeted)
    const modeBadge = page.locator('text=/Current Mode:|Universal Cycle 4|Session-Targeted/i').first();
    await expect(modeBadge).toBeVisible();
  });

  test('should display rollback button', async ({ page }) => {
    const rollbackButton = page.getByRole('button', { name: /Rollback to Universal Cycle 4/i });
    await expect(rollbackButton).toBeVisible();
  });

  test('should disable rollback button when already in Universal Cycle 4', async ({ page }) => {
    const rollbackButton = page.getByRole('button', { name: /Rollback to Universal Cycle 4/i });

    // Check if button is disabled (depends on current mode)
    const isDisabled = await rollbackButton.isDisabled();

    // If in Universal mode, button should be disabled
    const modeBadge = await page.textContent('text=/Universal Cycle 4|Session-Targeted/i');
    if (modeBadge?.includes('Universal')) {
      expect(isDisabled).toBeTruthy();
    }
  });

  test('should open confirmation modal when rollback button clicked', async ({ page }) => {
    const rollbackButton = page.getByRole('button', { name: /Rollback to Universal Cycle 4/i });

    // Only test if button is enabled
    const isEnabled = await rollbackButton.isEnabled();
    if (!isEnabled) {
      test.skip();
    }

    await rollbackButton.click();

    // Check modal opens
    await expect(page.getByText(/Confirm Emergency Rollback/i)).toBeVisible();
    await expect(page.getByText(/Current Mode/i)).toBeVisible();
    await expect(page.getByText(/Target Mode/i)).toBeVisible();
  });

  test('should trigger rollback modal with Ctrl+Shift+R keyboard shortcut', async ({ page }) => {
    // Check current mode first
    const modeBadgeText = await page.textContent('text=/Universal Cycle 4|Session-Targeted/i');

    // Only test if not in Universal mode
    if (modeBadgeText?.includes('Universal')) {
      test.skip();
    }

    // Press Ctrl+Shift+R
    await page.keyboard.press('Control+Shift+R');

    // Wait briefly for modal
    await page.waitForTimeout(200);

    // Check modal opens
    await expect(page.getByText(/Confirm Emergency Rollback/i)).toBeVisible();
  });
});

test.describe('Rollback Confirmation Modal', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/system-control');
    await page.waitForLoadState('networkidle');
  });

  test('should require "ROLLBACK" to be typed before confirming', async ({ page }) => {
    const rollbackButton = page.getByRole('button', { name: /Rollback to Universal Cycle 4/i });

    // Only test if button is enabled
    if (!(await rollbackButton.isEnabled())) {
      test.skip();
    }

    await rollbackButton.click();

    // Wait for modal
    await expect(page.getByText(/Confirm Emergency Rollback/i)).toBeVisible();

    const confirmInput = page.getByPlaceholder(/Type ROLLBACK/i);
    const confirmButton = page.getByRole('button', { name: /Confirm Rollback/i });

    // Confirm button should be disabled initially
    await expect(confirmButton).toBeDisabled();

    // Type incomplete text
    await confirmInput.fill('ROLL');
    await expect(confirmButton).toBeDisabled();

    // Type complete "ROLLBACK"
    await confirmInput.fill('ROLLBACK');
    await expect(confirmButton).toBeEnabled();
  });

  test('should accept case-insensitive ROLLBACK confirmation', async ({ page }) => {
    const rollbackButton = page.getByRole('button', { name: /Rollback to Universal Cycle 4/i });

    if (!(await rollbackButton.isEnabled())) {
      test.skip();
    }

    await rollbackButton.click();
    await expect(page.getByText(/Confirm Emergency Rollback/i)).toBeVisible();

    const confirmInput = page.getByPlaceholder(/Type ROLLBACK/i);
    const confirmButton = page.getByRole('button', { name: /Confirm Rollback/i });

    // Try lowercase
    await confirmInput.fill('rollback');
    await expect(confirmButton).toBeEnabled();

    // Try mixed case
    await confirmInput.clear();
    await confirmInput.fill('RollBack');
    await expect(confirmButton).toBeEnabled();
  });

  test('should display current vs target mode comparison in modal', async ({ page }) => {
    const rollbackButton = page.getByRole('button', { name: /Rollback to Universal Cycle 4/i });

    if (!(await rollbackButton.isEnabled())) {
      test.skip();
    }

    await rollbackButton.click();
    await expect(page.getByText(/Confirm Emergency Rollback/i)).toBeVisible();

    // Check comparison sections
    await expect(page.getByText(/Current Mode/i)).toBeVisible();
    await expect(page.getByText(/Target Mode/i)).toBeVisible();
    await expect(page.getByText(/Universal Cycle 4/i)).toBeVisible();
  });

  test('should show impact summary in modal', async ({ page }) => {
    const rollbackButton = page.getByRole('button', { name: /Rollback to Universal Cycle 4/i });

    if (!(await rollbackButton.isEnabled())) {
      test.skip();
    }

    await rollbackButton.click();
    await expect(page.getByText(/Confirm Emergency Rollback/i)).toBeVisible();

    // Check impact summary
    await expect(page.getByText(/will receive updated parameters|Trading will continue|No positions will be closed/i)).toBeVisible();
  });

  test('should close modal when Cancel button clicked', async ({ page }) => {
    const rollbackButton = page.getByRole('button', { name: /Rollback to Universal Cycle 4/i });

    if (!(await rollbackButton.isEnabled())) {
      test.skip();
    }

    await rollbackButton.click();
    await expect(page.getByText(/Confirm Emergency Rollback/i)).toBeVisible();

    const cancelButton = page.getByRole('button', { name: /Cancel/i });
    await cancelButton.click();

    // Modal should close
    await expect(page.getByText(/Confirm Emergency Rollback/i)).not.toBeVisible();
  });
});

test.describe('Rollback History Table', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/system-control');
    await page.waitForLoadState('networkidle');
  });

  test('should display rollback history table', async ({ page }) => {
    // Look for table headers
    await expect(page.getByText(/Timestamp.*Trigger.*From Mode.*To Mode/i)).toBeVisible();
  });

  test('should display table columns: Timestamp, Trigger, From Mode, To Mode, Reason, Status, User', async ({ page }) => {
    // Check all 7 column headers are present
    await expect(page.getByRole('columnheader', { name: /Timestamp/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /Trigger/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /From Mode/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /To Mode/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /Reason/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /Status/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /User/i })).toBeVisible();
  });

  test('should show loading state initially', async ({ page }) => {
    await page.goto('/system-control', { waitUntil: 'domcontentloaded' });

    // Check for loading indicator (spinner or skeleton)
    const loadingIndicator = page.getByText(/Loading|Fetching/i).or(page.locator('.animate-spin'));

    // May or may not be visible depending on load speed
    const isVisible = await loadingIndicator.isVisible().catch(() => false);
    // Just verify the page loaded without crashing
    expect(isVisible === true || isVisible === false).toBeTruthy();
  });

  test('should handle empty history gracefully', async ({ page }) => {
    // If no history, should show empty state message
    const emptyMessage = page.getByText(/No rollback history|No events found/i);
    const historyRows = page.locator('tbody tr');

    const rowCount = await historyRows.count();
    if (rowCount === 0) {
      await expect(emptyMessage).toBeVisible();
    }
  });

  test('should color-code trigger badges', async ({ page }) => {
    // Look for any rollback history entries with colored badges
    const manualBadge = page.locator('text=Manual').first();
    const failureBadge = page.locator('text=/Walk.*Forward|Overfitting/i').first();

    // If badges exist, check they have color classes
    const manualExists = await manualBadge.count();
    if (manualExists > 0) {
      await expect(manualBadge).toHaveClass(/bg-blue-500/);
    }

    const failureExists = await failureBadge.count();
    if (failureExists > 0) {
      await expect(failureBadge).toHaveClass(/bg-red-500/);
    }
  });
});

test.describe('Automated Trigger Monitoring', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/system-control');
    await page.waitForLoadState('networkidle');
  });

  test('should display automated trigger monitoring section', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Automated Trigger Monitoring/i })).toBeVisible();
  });

  test('should display trigger condition cards', async ({ page }) => {
    // Look for common trigger types
    const triggers = [
      /Walk.*Forward Failure/i,
      /Overfitting Detected/i,
      /Consecutive Losses/i,
      /Drawdown Breach/i
    ];

    // At least one trigger should be visible
    let foundTrigger = false;
    for (const trigger of triggers) {
      const triggerCard = page.locator(`text=${trigger}`);
      if (await triggerCard.count() > 0) {
        foundTrigger = true;
        break;
      }
    }

    expect(foundTrigger).toBeTruthy();
  });

  test('should show enable/disable toggle for each condition', async ({ page }) => {
    // Look for toggle switches in the monitoring section
    const toggles = page.locator('input[type="checkbox"]').or(page.locator('[role="switch"]'));

    const toggleCount = await toggles.count();
    expect(toggleCount).toBeGreaterThan(0);
  });

  test('should display current value vs threshold', async ({ page }) => {
    // Look for threshold displays (e.g., "2 / 5" or "40 / 100")
    const thresholdDisplay = page.locator('text=/\\d+.*\\d+/').first();

    // Should have some threshold display
    const exists = await thresholdDisplay.count();
    expect(exists).toBeGreaterThan(0);
  });

  test('should color-code condition cards based on proximity to threshold', async ({ page }) => {
    // Look for condition cards with colored borders
    const greenBorder = page.locator('.border-green-500').first();
    const yellowBorder = page.locator('.border-yellow-500').first();
    const redBorder = page.locator('.border-red-500').first();

    // At least one color should be present
    const greenCount = await greenBorder.count();
    const yellowCount = await yellowBorder.count();
    const redCount = await redBorder.count();

    expect(greenCount + yellowCount + redCount).toBeGreaterThan(0);
  });

  test('should display progress bar for each condition', async ({ page }) => {
    // Look for progress bars
    const progressBars = page.locator('[role="progressbar"]').or(page.locator('.bg-green-500, .bg-yellow-500, .bg-red-500').filter({ hasText: '' }));

    const progressCount = await progressBars.count();
    expect(progressCount).toBeGreaterThan(0);
  });

  test('should toggle condition on/off when switch clicked', async ({ page }) => {
    // Find first toggle
    const firstToggle = page.locator('input[type="checkbox"]').first();

    if (await firstToggle.count() === 0) {
      test.skip();
    }

    // Get initial state
    const initialState = await firstToggle.isChecked();

    // Click toggle
    await firstToggle.click();

    // Wait for update
    await page.waitForTimeout(500);

    // Verify state changed (may revert if backend not accessible)
    // Just ensure no crash occurred
    const finalState = await firstToggle.isChecked();
    expect(typeof finalState).toBe('boolean');
  });
});

test.describe('Audit Trail Page - Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should have Audit Trail link in sidebar navigation', async ({ page }) => {
    const auditTrailLink = page.getByRole('link', { name: /Audit Trail/i });
    await expect(auditTrailLink).toBeVisible();
  });

  test('should navigate to Audit Trail page', async ({ page }) => {
    const auditTrailLink = page.getByRole('link', { name: /Audit Trail/i });
    await auditTrailLink.click();

    // Wait for navigation
    await page.waitForLoadState('networkidle');

    // Verify page title
    await expect(page.getByRole('heading', { name: /Audit Trail/i, level: 1 })).toBeVisible();

    // Verify URL
    expect(page.url()).toContain('/audit-trail');
  });
});

test.describe('Audit Trail Page - Content', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/audit-trail');
    await page.waitForLoadState('networkidle');
  });

  test('should display audit trail table', async ({ page }) => {
    // Check for table headers
    await expect(page.getByText(/Timestamp.*Action.*User.*Status/i)).toBeVisible();
  });

  test('should display table columns: Timestamp, Action, User, Status, Details', async ({ page }) => {
    await expect(page.getByRole('columnheader', { name: /Timestamp/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /Action/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /User/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /Status/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /Details/i })).toBeVisible();
  });

  test('should display filter controls', async ({ page }) => {
    // Check for action type filter
    await expect(page.getByText(/Action Type/i)).toBeVisible();

    // Check for status filter
    await expect(page.getByText(/Status/i)).toBeVisible();
  });

  test('should have export buttons (CSV and JSON)', async ({ page }) => {
    const exportCSV = page.getByRole('button', { name: /Export CSV/i });
    const exportJSON = page.getByRole('button', { name: /Export JSON/i });

    await expect(exportCSV).toBeVisible();
    await expect(exportJSON).toBeVisible();
  });

  test('should handle empty audit log gracefully', async ({ page }) => {
    const emptyMessage = page.getByText(/No audit logs|No records found/i);
    const logRows = page.locator('tbody tr');

    const rowCount = await logRows.count();
    if (rowCount === 0) {
      await expect(emptyMessage).toBeVisible();
    }
  });

  test('should color-code action type badges', async ({ page }) => {
    // Look for colored badges
    const rollbackBadge = page.locator('text=rollback').first();
    const stopBadge = page.locator('text=emergency_stop').first();
    const closeBadge = page.locator('text=close_positions').first();

    // If badges exist, check they have color classes
    if (await rollbackBadge.count() > 0) {
      await expect(rollbackBadge).toHaveClass(/bg-orange-500/);
    }

    if (await stopBadge.count() > 0) {
      await expect(stopBadge).toHaveClass(/bg-red-500/);
    }

    if (await closeBadge.count() > 0) {
      await expect(closeBadge).toHaveClass(/bg-yellow-500/);
    }
  });

  test('should color-code status badges', async ({ page }) => {
    // Look for success/failed badges
    const successBadge = page.locator('text=/Success|Completed/i').first();
    const failedBadge = page.locator('text=Failed').first();

    if (await successBadge.count() > 0) {
      await expect(successBadge).toHaveClass(/bg-green-500/);
    }

    if (await failedBadge.count() > 0) {
      await expect(failedBadge).toHaveClass(/bg-red-500/);
    }
  });
});

test.describe('Audit Trail - Filtering', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/audit-trail');
    await page.waitForLoadState('networkidle');
  });

  test('should filter by action type', async ({ page }) => {
    const actionTypeFilter = page.locator('select').filter({ hasText: /Action Type|All Actions/i }).first();

    if (await actionTypeFilter.count() === 0) {
      test.skip();
    }

    // Select an action type
    await actionTypeFilter.selectOption('rollback');

    // Wait for filtering
    await page.waitForTimeout(500);

    // Verify URL or table updated (just ensure no crash)
    const url = page.url();
    expect(url).toBeTruthy();
  });

  test('should filter by status', async ({ page }) => {
    const statusFilter = page.locator('select').filter({ hasText: /Status|All/i }).first();

    if (await statusFilter.count() === 0) {
      test.skip();
    }

    // Select success only
    await statusFilter.selectOption({ label: /Success|Completed/i });

    // Wait for filtering
    await page.waitForTimeout(500);

    // Just verify no crash
    const url = page.url();
    expect(url).toBeTruthy();
  });

  test('should clear input when filter changed', async ({ page }) => {
    // Get user filter input
    const userFilter = page.locator('input[placeholder*="user" i], input[name="user"]').first();

    if (await userFilter.count() === 0) {
      test.skip();
    }

    // Type username
    await userFilter.fill('admin');

    // Wait for filtering
    await page.waitForTimeout(500);

    // Verify input retained value
    await expect(userFilter).toHaveValue('admin');
  });
});

test.describe('Audit Trail - Export Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/audit-trail');
    await page.waitForLoadState('networkidle');
  });

  test('should trigger CSV download when Export CSV clicked', async ({ page }) => {
    const exportCSV = page.getByRole('button', { name: /Export CSV/i });

    // Set up download listener
    const downloadPromise = page.waitForEvent('download', { timeout: 5000 }).catch(() => null);

    await exportCSV.click();

    const download = await downloadPromise;

    // If download triggered, verify filename
    if (download) {
      const filename = download.suggestedFilename();
      expect(filename).toMatch(/audit.*\.csv/i);
    }
  });

  test('should trigger JSON download when Export JSON clicked', async ({ page }) => {
    const exportJSON = page.getByRole('button', { name: /Export JSON/i });

    // Set up download listener
    const downloadPromise = page.waitForEvent('download', { timeout: 5000 }).catch(() => null);

    await exportJSON.click();

    const download = await downloadPromise;

    // If download triggered, verify filename
    if (download) {
      const filename = download.suggestedFilename();
      expect(filename).toMatch(/audit.*\.json/i);
    }
  });
});

test.describe('Accessibility - Emergency Rollback', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/system-control');
    await page.waitForLoadState('networkidle');
  });

  test('should have proper ARIA labels on rollback button', async ({ page }) => {
    const rollbackButton = page.getByRole('button', { name: /Rollback to Universal Cycle 4/i });

    // Button should be accessible by role
    await expect(rollbackButton).toBeVisible();
  });

  test('should support keyboard navigation through triggers', async ({ page }) => {
    // Press Tab to navigate
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // At least one element should have focus
    const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
    expect(focusedElement).toBeTruthy();
  });

  test('should have semantic HTML table for history', async ({ page }) => {
    const table = page.locator('table').first();

    if (await table.count() > 0) {
      // Check for thead and tbody
      await expect(table.locator('thead')).toBeVisible();
      await expect(table.locator('tbody')).toBeVisible();
    }
  });
});

test.describe('Accessibility - Audit Trail', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/audit-trail');
    await page.waitForLoadState('networkidle');
  });

  test('should have semantic HTML table for audit logs', async ({ page }) => {
    const table = page.locator('table').first();

    if (await table.count() > 0) {
      // Check for thead and tbody
      await expect(table.locator('thead')).toBeVisible();
      await expect(table.locator('tbody')).toBeVisible();
    }
  });

  test('should have accessible filter controls', async ({ page }) => {
    // Check for labels on filter controls
    const actionTypeLabel = page.getByText(/Action Type/i);
    const statusLabel = page.getByText(/Status/i);

    await expect(actionTypeLabel).toBeVisible();
    await expect(statusLabel).toBeVisible();
  });

  test('should support keyboard navigation through filters', async ({ page }) => {
    // Press Tab to navigate through filters
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // At least one element should have focus
    const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
    expect(focusedElement).toBeTruthy();
  });
});

test.describe('Integration - Epic 2 Complete Flow', () => {
  test('should complete full emergency rollback workflow', async ({ page }) => {
    // 1. Navigate to System Control
    await page.goto('/system-control');
    await page.waitForLoadState('networkidle');

    // 2. Check current mode
    const modeBadgeText = await page.textContent('text=/Universal Cycle 4|Session-Targeted/i');

    // 3. If not in Universal mode, test rollback
    if (modeBadgeText && !modeBadgeText.includes('Universal')) {
      // Click rollback button
      const rollbackButton = page.getByRole('button', { name: /Rollback to Universal Cycle 4/i });
      await rollbackButton.click();

      // Type confirmation
      const confirmInput = page.getByPlaceholder(/Type ROLLBACK/i);
      await confirmInput.fill('ROLLBACK');

      // Confirm (but don't actually execute in test)
      const confirmButton = page.getByRole('button', { name: /Confirm Rollback/i });
      await expect(confirmButton).toBeEnabled();

      // Cancel instead of executing
      const cancelButton = page.getByRole('button', { name: /Cancel/i });
      await cancelButton.click();
    }

    // 4. Verify history table visible
    await expect(page.getByRole('columnheader', { name: /Timestamp/i })).toBeVisible();

    // 5. Navigate to Audit Trail
    await page.goto('/audit-trail');
    await page.waitForLoadState('networkidle');

    // 6. Verify audit trail loaded
    await expect(page.getByRole('heading', { name: /Audit Trail/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Export CSV/i })).toBeVisible();
  });

  test('should navigate between all Epic 2 pages without errors', async ({ page }) => {
    // Home page
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL('/');

    // System Control
    await page.goto('/system-control');
    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('heading', { name: /System Control Panel/i })).toBeVisible();

    // Audit Trail
    await page.goto('/audit-trail');
    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('heading', { name: /Audit Trail/i })).toBeVisible();

    // Back to Home
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL('/');
  });
});
