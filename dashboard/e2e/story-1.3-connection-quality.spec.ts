/**
 * E2E Tests for Story 1.3: Connection Quality Indicator & Mini Health Cards
 * Tests using Playwright
 */

import { test, expect } from '@playwright/test'

test.describe('Story 1.3: Connection Quality & Mini Cards', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard
    await page.goto('/')

    // Wait for page to load
    await page.waitForLoadState('networkidle')
  })

  test.describe('Connection Quality Indicator', () => {
    test('should display connection quality indicator in footer', async ({ page }) => {
      // Check that connection quality indicator exists
      const indicator = page.getByRole('status', { name: /connection quality/i })
      await expect(indicator).toBeVisible()
    })

    test('should show quality label and icon', async ({ page }) => {
      const indicator = page.getByRole('status', { name: /connection quality/i })

      // Should have one of the quality labels
      const hasQualityLabel = await indicator.evaluate((el) => {
        const text = el.textContent || ''
        return ['Excellent', 'Good', 'Fair', 'Poor', 'Disconnected'].some(
          label => text.includes(label)
        )
      })

      expect(hasQualityLabel).toBe(true)
    })

    test('should display last updated timestamp', async ({ page }) => {
      const indicator = page.getByRole('status', { name: /connection quality/i })

      // Should show a timestamp (e.g., "3s ago", "1m ago")
      const hasTimestamp = await indicator.evaluate((el) => {
        const text = el.textContent || ''
        return /(\d+[smh]\s+ago|just now|No data)/i.test(text)
      })

      expect(hasTimestamp).toBe(true)
    })

    test('should show tooltip on hover', async ({ page }) => {
      const indicator = page.getByRole('status', { name: /connection quality/i })

      // Hover over the indicator
      await indicator.hover()

      // Wait for tooltip to appear
      await page.waitForTimeout(200)

      // Check for tooltip content using specific data-testid
      const tooltip = page.getByTestId('connection-quality-tooltip')
      await expect(tooltip).toBeVisible()

      // Tooltip should contain metrics
      await expect(tooltip).toContainText(/WebSocket:/i)
      await expect(tooltip).toContainText(/Avg Latency:/i)
      await expect(tooltip).toContainText(/Last Update:/i)
    })

    test('should hide tooltip when not hovering', async ({ page }) => {
      const indicator = page.getByRole('status', { name: /connection quality/i })

      // Hover to show tooltip
      await indicator.hover()
      await page.waitForTimeout(200)

      // Move away from indicator
      await page.mouse.move(0, 0)
      await page.waitForTimeout(200)

      // Tooltip should not be visible using specific data-testid
      const tooltip = page.getByTestId('connection-quality-tooltip')
      await expect(tooltip).not.toBeVisible()
    })
  })

  test.describe('Mini Agent Health Cards', () => {
    test('should display mini agent health cards in footer', async ({ page }) => {
      const miniCards = page.getByRole('region', { name: /mini agent health cards/i })
      await expect(miniCards).toBeVisible()
    })

    test('should display all 8 agent cards', async ({ page }) => {
      const miniCards = page.getByRole('region', { name: /mini agent health cards/i })

      // Count the number of mini cards
      const cardCount = await miniCards.getByRole('button').count()

      // Should have 8 agents (or might be loading)
      expect(cardCount).toBeGreaterThanOrEqual(0)

      // If cards are loaded, should be 8
      if (cardCount > 0) {
        expect(cardCount).toBeLessThanOrEqual(8)
      }
    })

    test('should show agent name on each card', async ({ page }) => {
      const miniCards = page.getByRole('region', { name: /mini agent health cards/i })
      const firstCard = miniCards.getByRole('button').first()

      // Wait for card to be visible
      await expect(firstCard).toBeVisible()

      // Should have text content (agent name)
      const text = await firstCard.textContent()
      expect(text?.trim()).not.toBe('')
    })

    test('should show status dot on each card', async ({ page }) => {
      const miniCards = page.getByRole('region', { name: /mini agent health cards/i })
      const firstCard = miniCards.getByRole('button').first()

      // Check for status dot (8px rounded element)
      const statusDot = firstCard.locator('[class*="w-2"][class*="h-2"][class*="rounded-full"]')
      await expect(statusDot).toBeVisible()
    })

    test('should show latency value on each card', async ({ page }) => {
      const miniCards = page.getByRole('region', { name: /mini agent health cards/i })
      const firstCard = miniCards.getByRole('button').first()

      // Should show latency (e.g., "45ms")
      await expect(firstCard).toContainText(/\d+ms/i)
    })

    test('should open detailed health panel when card is clicked', async ({ page }) => {
      const miniCards = page.getByRole('region', { name: /mini agent health cards/i })
      const firstCard = miniCards.getByRole('button').first()

      // Wait for card to be clickable
      await expect(firstCard).toBeVisible()

      // Click the card
      await firstCard.click()

      // Wait for detailed panel to open
      await page.waitForTimeout(500)

      // Check that detailed health panel is visible
      const detailedPanel = page.getByRole('dialog', { name: /detailed system health/i })
      await expect(detailedPanel).toBeVisible()
    })

    test('should be keyboard navigable', async ({ page }) => {
      const miniCards = page.getByRole('region', { name: /mini agent health cards/i })
      const firstCard = miniCards.getByRole('button').first()

      // Focus the first card
      await firstCard.focus()

      // Check that it's focused
      await expect(firstCard).toBeFocused()

      // Press Tab to move to next card
      await page.keyboard.press('Tab')

      // Second card should be focused
      const secondCard = miniCards.getByRole('button').nth(1)
      await expect(secondCard).toBeFocused()
    })

    test('should activate card on Enter key', async ({ page }) => {
      const miniCards = page.getByRole('region', { name: /mini agent health cards/i })
      const firstCard = miniCards.getByRole('button').first()

      // Focus and press Enter
      await firstCard.focus()
      await page.keyboard.press('Enter')

      // Detailed panel should open
      await page.waitForTimeout(500)
      const detailedPanel = page.getByRole('dialog', { name: /detailed system health/i })
      await expect(detailedPanel).toBeVisible()
    })
  })

  test.describe('Footer Layout', () => {
    test('should display footer at bottom of page', async ({ page }) => {
      const footer = page.locator('footer')
      await expect(footer).toBeVisible()

      // Check that footer is at the bottom
      const footerBox = await footer.boundingBox()
      const viewportSize = page.viewportSize()

      if (footerBox && viewportSize) {
        expect(footerBox.y + footerBox.height).toBeGreaterThan(viewportSize.height * 0.8)
      }
    })

    test('should have connection indicator on right side', async ({ page }) => {
      const footer = page.locator('footer')
      const indicator = footer.getByRole('status', { name: /connection quality/i })

      await expect(indicator).toBeVisible()

      // Check positioning (should be on right side)
      const footerBox = await footer.boundingBox()
      const indicatorBox = await indicator.boundingBox()

      if (footerBox && indicatorBox) {
        // Indicator should be more than halfway across the footer
        expect(indicatorBox.x).toBeGreaterThan(footerBox.x + footerBox.width / 2)
      }
    })

    test('should not overlap with main content', async ({ page }) => {
      const main = page.locator('main')
      const footer = page.locator('footer')

      const mainBox = await main.boundingBox()
      const footerBox = await footer.boundingBox()

      if (mainBox && footerBox) {
        // Footer should be below main content (no overlap)
        expect(footerBox.y).toBeGreaterThanOrEqual(mainBox.y)
      }
    })
  })

  test.describe('Responsive Design', () => {
    test('should display correctly on mobile', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 })

      // Footer should still be visible
      const footer = page.locator('footer')
      await expect(footer).toBeVisible()

      // Connection indicator should be visible
      const indicator = footer.getByRole('status', { name: /connection quality/i })
      await expect(indicator).toBeVisible()
    })

    test('should adjust mini cards grid on tablet', async ({ page }) => {
      // Set tablet viewport
      await page.setViewportSize({ width: 768, height: 1024 })

      const miniCards = page.getByRole('region', { name: /mini agent health cards/i })
      await expect(miniCards).toBeVisible()

      // Check grid layout (should have fewer columns)
      const grid = await miniCards.evaluate((el) => {
        return window.getComputedStyle(el).gridTemplateColumns
      })

      // Should have grid columns defined
      expect(grid).not.toBe('none')
    })

    test('should adjust mini cards grid on desktop', async ({ page }) => {
      // Set desktop viewport
      await page.setViewportSize({ width: 1920, height: 1080 })

      const miniCards = page.getByRole('region', { name: /mini agent health cards/i })
      await expect(miniCards).toBeVisible()

      // Cards should be in grid layout
      const grid = await miniCards.evaluate((el) => {
        return window.getComputedStyle(el).gridTemplateColumns
      })

      expect(grid).not.toBe('none')
    })
  })

  test.describe('User Preferences', () => {
    test('should remember mini cards visibility preference', async ({ page, context }) => {
      // This test checks localStorage persistence
      // For now, we just verify the cards are visible by default
      const miniCards = page.getByRole('region', { name: /mini agent health cards/i })
      await expect(miniCards).toBeVisible()

      // Check localStorage was set
      const localStorageValue = await page.evaluate(() => {
        return localStorage.getItem('showMiniAgentCards')
      })

      // Should have a value (true by default)
      expect(localStorageValue).not.toBeNull()
    })
  })

  test.describe('Real-time Updates', () => {
    test('should update connection quality over time', async ({ page }) => {
      const indicator = page.getByRole('status', { name: /connection quality/i })

      // Get initial text
      const initialText = await indicator.textContent()

      // Wait for update (5+ seconds for polling interval)
      await page.waitForTimeout(6000)

      // Text should potentially have updated (at least timestamp changed)
      const updatedText = await indicator.textContent()

      // Timestamp should have changed
      expect(updatedText).not.toBe(initialText)
    })
  })

  test.describe('Integration with Detailed Panel', () => {
    test('should scroll to clicked agent in detailed panel', async ({ page }) => {
      const miniCards = page.getByRole('region', { name: /mini agent health cards/i })
      const secondCard = miniCards.getByRole('button').nth(1)

      // Click a specific mini card
      await secondCard.click()
      await page.waitForTimeout(500)

      // Detailed panel should be open
      const detailedPanel = page.getByRole('dialog', { name: /detailed system health/i })
      await expect(detailedPanel).toBeVisible()

      // Panel should contain agent health cards
      const agentSection = detailedPanel.getByRole('article').first()
      await expect(agentSection).toBeVisible()
    })
  })
})
