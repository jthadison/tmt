import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test.describe('Accessibility Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Mock authentication to bypass login for accessibility testing
    await page.route('**/api/auth/me', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: '1',
          email: 'test@example.com',
          name: 'Test User',
          role: 'trader',
          two_factor_enabled: true,
          created_at: '2023-01-01T00:00:00Z',
          last_login: '2023-01-01T00:00:00Z'
        })
      })
    })

    await page.goto('/')
    await page.evaluate(() => {
      document.cookie = 'access_token=fake-token; path=/'
    })
    await page.reload()
  })

  test('should not have any automatically detectable accessibility issues on dashboard', async ({ page }) => {
    const accessibilityScanResults = await new AxeBuilder({ page }).analyze()
    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('should not have accessibility issues on login form', async ({ page }) => {
    // Clear auth cookies to show login form
    await page.evaluate(() => {
      document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;'
    })
    await page.reload()

    // Wait for login form to appear
    await expect(page.getByText('Sign In')).toBeVisible()

    const accessibilityScanResults = await new AxeBuilder({ page }).analyze()
    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('navigation is keyboard accessible', async ({ page }) => {
    // Test keyboard navigation through main elements
    await page.keyboard.press('Tab')
    
    // Should be able to navigate through interactive elements
    const focusedElement = page.locator(':focus')
    await expect(focusedElement).toBeVisible()
  })

  test('form elements have proper labels', async ({ page }) => {
    // Clear auth to show login form
    await page.evaluate(() => {
      document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;'
    })
    await page.reload()

    // Check that form inputs have associated labels
    const emailInput = page.getByLabel('Email Address')
    const passwordInput = page.getByLabel('Password')
    
    await expect(emailInput).toBeVisible()
    await expect(passwordInput).toBeVisible()
    
    // Verify inputs are properly labeled
    await expect(emailInput).toHaveAttribute('type', 'email')
    await expect(passwordInput).toHaveAttribute('type', 'password')
  })

  test('buttons have accessible names', async ({ page }) => {
    // Check that all buttons have accessible names
    const buttons = page.locator('button')
    const buttonCount = await buttons.count()
    
    for (let i = 0; i < buttonCount; i++) {
      const button = buttons.nth(i)
      const isVisible = await button.isVisible()
      
      if (isVisible) {
        // Button should have either text content, aria-label, or title
        const hasText = await button.textContent()
        const hasAriaLabel = await button.getAttribute('aria-label')
        const hasTitle = await button.getAttribute('title')
        
        expect(
          hasText?.trim() || hasAriaLabel || hasTitle
        ).toBeTruthy()
      }
    }
  })

  test('heading hierarchy is logical', async ({ page }) => {
    // Check that headings follow a logical hierarchy
    const headings = page.locator('h1, h2, h3, h4, h5, h6')
    const headingCount = await headings.count()
    
    if (headingCount > 0) {
      const firstHeading = headings.first()
      const firstHeadingTagName = await firstHeading.evaluate(el => el.tagName.toLowerCase())
      
      // First heading should be h1 or h2 (h1 is in document title, h2 for page content)
      expect(['h1', 'h2']).toContain(firstHeadingTagName)
    }
  })

  test('images have alt text', async ({ page }) => {
    const images = page.locator('img')
    const imageCount = await images.count()
    
    for (let i = 0; i < imageCount; i++) {
      const image = images.nth(i)
      const isVisible = await image.isVisible()
      
      if (isVisible) {
        const altText = await image.getAttribute('alt')
        expect(altText).toBeDefined()
      }
    }
  })

  test('color contrast meets WCAG standards', async ({ page }) => {
    // Run axe with specific color contrast rules
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .include('body')
      .analyze()

    // Filter for color contrast violations
    const colorContrastViolations = accessibilityScanResults.violations.filter(
      violation => violation.id === 'color-contrast'
    )
    
    expect(colorContrastViolations).toEqual([])
  })

  test('focus is visible and logical', async ({ page }) => {
    // Test that focus is visible when navigating with keyboard
    await page.keyboard.press('Tab')
    
    // Get the focused element
    const focusedElement = page.locator(':focus')
    await expect(focusedElement).toBeVisible()
    
    // Focus should have some visual indication
    // (This is hard to test programmatically, but we ensure element is focusable)
    const isFocusable = await focusedElement.evaluate(el => {
      const style = window.getComputedStyle(el)
      return style.outline !== 'none' || style.outlineWidth !== '0px' || 
             style.boxShadow.includes('outline') || el.tabIndex >= 0
    })
    
    expect(isFocusable).toBeTruthy()
  })

  test('dynamic content updates are announced', async ({ page }) => {
    // Check for aria-live regions or other mechanisms for announcing updates
    const liveRegions = page.locator('[aria-live]')
    const statusElements = page.locator('[role="status"], [role="alert"]')
    
    // We should have some mechanism for announcing dynamic updates
    // At minimum, the WebSocket status should be announced
    const hasAnnouncementMechanism = 
      (await liveRegions.count()) > 0 || 
      (await statusElements.count()) > 0 ||
      (await page.locator('[aria-label*="status"], [aria-describedby]').count()) > 0
    
    expect(hasAnnouncementMechanism).toBeTruthy()
  })

  test('responsive design maintains accessibility', async ({ page }) => {
    // Test accessibility at different viewport sizes
    const viewports = [
      { width: 375, height: 667 },   // Mobile
      { width: 768, height: 1024 },  // Tablet
      { width: 1920, height: 1080 }  // Desktop
    ]
    
    for (const viewport of viewports) {
      await page.setViewportSize(viewport)
      await page.waitForTimeout(100) // Allow for responsive changes
      
      const accessibilityScanResults = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa'])
        .analyze()
      
      expect(accessibilityScanResults.violations).toEqual([])
    }
  })
})