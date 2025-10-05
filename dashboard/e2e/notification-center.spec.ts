import { test, expect } from '@playwright/test'

test.describe('Notification Center', () => {
  test('should load dashboard with notification bell without errors', async ({ page }) => {
    // Track console errors
    const errors: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })

    // Track page errors
    page.on('pageerror', error => {
      errors.push(error.message)
    })

    // Navigate to dashboard
    await page.goto('http://localhost:8090')

    // Wait for page to load
    await page.waitForLoadState('networkidle')

    // Check that notification bell icon exists
    const notificationBell = page.getByRole('button', { name: 'Notifications' })
    await expect(notificationBell).toBeVisible()

    // Verify no console or page errors related to notifications
    const notificationErrors = errors.filter(e =>
      e.toLowerCase().includes('notification') ||
      e.toLowerCase().includes('818.js') ||
      e.toLowerCase().includes('date-fns')
    )

    expect(notificationErrors).toHaveLength(0)

    console.log('All errors:', errors)
  })

  test('should open notification panel when bell is clicked', async ({ page }) => {
    await page.goto('http://localhost:8090')
    await page.waitForLoadState('networkidle')

    // Click notification bell
    const notificationBell = page.getByRole('button', { name: 'Notifications' })
    await notificationBell.click()

    // Verify panel opens
    const panel = page.getByRole('dialog', { name: /notifications/i })
    await expect(panel).toBeVisible()

    // Verify empty state message
    await expect(page.getByText(/no notifications/i)).toBeVisible()
    await expect(page.getByText(/you're all caught up!/i)).toBeVisible()
  })

  test('should have Mark All Read and Clear All buttons', async ({ page }) => {
    await page.goto('http://localhost:8090')
    await page.waitForLoadState('networkidle')

    // Open notification panel
    const notificationBell = page.getByRole('button', { name: 'Notifications' })
    await notificationBell.click()

    // Check buttons exist
    await expect(page.getByRole('button', { name: /mark all read/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /clear all/i })).toBeVisible()
  })
})
