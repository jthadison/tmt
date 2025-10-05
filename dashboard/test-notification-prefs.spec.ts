import { test, expect } from '@playwright/test'

test.describe('Notification Preferences Page', () => {
  test('should load and display notification preferences page', async ({ page }) => {
    // Navigate to preferences page
    await page.goto('http://localhost:8090/settings/notifications')
    
    // Wait for page to load
    await page.waitForLoadState('networkidle', { timeout: 30000 })
    
    // Check for main heading
    await expect(page.getByText('Notification Preferences')).toBeVisible({ timeout: 10000 })
    
    // Check for key sections
    await expect(page.getByText('Delivery Methods')).toBeVisible()
    await expect(page.getByText('Priority Filtering')).toBeVisible()
    await expect(page.getByText('Quiet Hours')).toBeVisible()
    
    // Take screenshot
    await page.screenshot({ path: 'notification-prefs-test.png', fullPage: true })
    
    console.log('✅ Page loaded successfully!')
  })
  
  test('should show action buttons', async ({ page }) => {
    await page.goto('http://localhost:8090/settings/notifications')
    await page.waitForLoadState('networkidle', { timeout: 30000 })
    
    await expect(page.getByText('Reset to Defaults')).toBeVisible()
    await expect(page.getByText('Export Preferences')).toBeVisible()
    await expect(page.getByText('Import Preferences')).toBeVisible()
  })
})
