/**
 * Playwright E2E Tests for Agent Disagreement Visualization
 * Story 7.1: Agent Disagreement Visualization & Confidence Meters
 */

import { test, expect, Page } from '@playwright/test';

// Mock disagreement data matching our implementation
const mockDisagreementData = {
  symbol: 'EUR_USD',
  timestamp: Date.now(),
  consensusPercentage: 75,
  finalDecision: 'BUY',
  thresholdMet: true,
  requiredThreshold: 70,
  agentPositions: [
    {
      agentId: 'market-analysis',
      agentName: 'Market Analysis',
      action: 'BUY',
      confidence: 85,
      reasoning: [
        'Strong bullish momentum detected (RSI: 72)',
        'Price broke above resistance at 1.0850 with high volume',
        'London session showing optimal conditions'
      ],
      timestamp: Date.now()
    },
    {
      agentId: 'pattern-detection',
      agentName: 'Pattern Detection',
      action: 'BUY',
      confidence: 78,
      reasoning: [
        'Wyckoff accumulation Phase E detected',
        'Sign of Strength (SOS) confirmed'
      ],
      timestamp: Date.now()
    },
    {
      agentId: 'strategy-analysis',
      agentName: 'Strategy Analysis',
      action: 'NEUTRAL',
      confidence: 45,
      reasoning: [
        'Recent win rate below target (62% vs 70%)',
        'Suggest caution until performance improves'
      ],
      timestamp: Date.now()
    },
    {
      agentId: 'parameter-optimization',
      agentName: 'Parameter Optimization',
      action: 'BUY',
      confidence: 72,
      reasoning: [
        'Risk parameters optimized for current volatility',
        'Position sizing favorable'
      ],
      timestamp: Date.now()
    },
    {
      agentId: 'learning-safety',
      agentName: 'Learning Safety',
      action: 'BUY',
      confidence: 80,
      reasoning: [
        'No anomalies detected in market data',
        'Circuit breakers all clear'
      ],
      timestamp: Date.now()
    },
    {
      agentId: 'disagreement-engine',
      agentName: 'Disagreement Engine',
      action: 'BUY',
      confidence: 75,
      reasoning: [
        'Consensus threshold met at 75%',
        'Agent agreement within acceptable range'
      ],
      timestamp: Date.now()
    },
    {
      agentId: 'data-collection',
      agentName: 'Data Collection',
      action: 'BUY',
      confidence: 70,
      reasoning: [
        'Data quality verified across all sources',
        'No missing or corrupt data points'
      ],
      timestamp: Date.now()
    },
    {
      agentId: 'continuous-improvement',
      agentName: 'Continuous Improvement',
      action: 'SELL',
      confidence: 55,
      reasoning: [
        'Recent performance metrics showing decline',
        'Recommend defensive position'
      ],
      timestamp: Date.now()
    }
  ]
};

test.describe('Agent Disagreement Panel E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Mock the disagreement API endpoint
    await page.route('**/disagreement/current/EUR_USD', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDisagreementData)
      });
    });

    // Navigate to a test page with the AgentDisagreementPanel
    // Note: You'll need to create this test page or integrate with existing page
    await page.goto('/test/agent-disagreement');
  });

  test('should display panel when expanded', async ({ page }) => {
    // Find and click the expand button/trigger
    const expandButton = page.getByRole('button', { name: /view.*disagreement/i });
    await expandButton.click();

    // Verify panel is visible
    const panel = page.locator('[class*="agent-disagreement-panel"]');
    await expect(panel).toBeVisible();
  });

  test('should display consensus meter with correct percentage', async ({ page }) => {
    await page.getByRole('button', { name: /view.*disagreement/i }).click();

    // Check consensus percentage is displayed
    const consensusPercentage = page.getByTestId('consensus-percentage');
    await expect(consensusPercentage).toContainText('75%');

    // Verify consensus meter is visible
    const consensusMeter = page.getByTestId('consensus-meter');
    await expect(consensusMeter).toBeVisible();

    // Check the color is correct (light green for 75%)
    await expect(consensusPercentage).toHaveCSS('color', 'rgb(132, 204, 22)');
  });

  test('should display agent agreement count', async ({ page }) => {
    await page.getByRole('button', { name: /view.*disagreement/i }).click();

    // Verify agent agreement text
    await expect(page.getByText('6 of 8 agents agree')).toBeVisible();
  });

  test('should display threshold information', async ({ page }) => {
    await page.getByRole('button', { name: /view.*disagreement/i }).click();

    // Check threshold text in consensus meter
    await expect(page.getByText('Threshold: 70%')).toBeVisible();
  });

  test('should display final decision badge', async ({ page }) => {
    await page.getByRole('button', { name: /view.*disagreement/i }).click();

    // Verify decision badge is present
    const decisionBadge = page.getByTestId('decision-badge');
    await expect(decisionBadge).toBeVisible();

    // Check decision text
    const decisionText = page.getByTestId('decision-text');
    await expect(decisionText).toContainText('BUY');

    // Verify checkmark icon for threshold met
    const checkIcon = page.getByTestId('check-icon');
    await expect(checkIcon).toBeVisible();

    // Check threshold met message
    await expect(page.getByTestId('threshold-met')).toContainText('Threshold met (75% ≥ 70% required)');
  });

  test('should display all 8 agent position cards', async ({ page }) => {
    await page.getByRole('button', { name: /view.*disagreement/i }).click();

    // Verify all 8 agent cards are present
    const agentCards = page.getByTestId('agent-position-card');
    await expect(agentCards).toHaveCount(8);
  });

  test('should display agent names correctly', async ({ page }) => {
    await page.getByRole('button', { name: /view.*disagreement/i }).click();

    // Check specific agent names (use .first() to handle duplicates in test info panel)
    await expect(page.getByText('Market Analysis').first()).toBeVisible();
    await expect(page.getByText('Pattern Detection').first()).toBeVisible();
    await expect(page.getByText('Strategy Analysis').first()).toBeVisible();
    await expect(page.getByText('Parameter Optimization').first()).toBeVisible();
    await expect(page.getByText('Learning Safety').first()).toBeVisible();
    await expect(page.getByText('Disagreement Engine').first()).toBeVisible();
    await expect(page.getByText('Data Collection').first()).toBeVisible();
    await expect(page.getByText('Continuous Improvement').first()).toBeVisible();
  });

  test('should display agent icons', async ({ page }) => {
    await page.getByRole('button', { name: /view.*disagreement/i }).click();

    // Verify agent icons are present
    const agentIcons = page.getByTestId('agent-icon');
    await expect(agentIcons).toHaveCount(8);
  });

  test('should display confidence meters with correct colors', async ({ page }) => {
    await page.getByRole('button', { name: /view.*disagreement/i }).click();

    // Check high confidence (85%) - should be light green
    await expect(page.getByText('85% - High')).toBeVisible();

    // Check medium confidence (78%) - should be light green
    await expect(page.getByText('78% - High')).toBeVisible();

    // Check low confidence (45%) - should be orange
    await expect(page.getByText('45% - Low')).toBeVisible();

    // Verify confidence bars are present
    const confidenceBars = page.getByTestId('confidence-bar');
    await expect(confidenceBars.first()).toBeVisible();
  });

  test('should display agent reasoning bullets', async ({ page }) => {
    await page.getByRole('button', { name: /view.*disagreement/i }).click();

    // Check specific reasoning text from different agents
    await expect(page.getByText('Strong bullish momentum detected (RSI: 72)')).toBeVisible();
    await expect(page.getByText('Wyckoff accumulation Phase E detected')).toBeVisible();
    await expect(page.getByText('Recent win rate below target (62% vs 70%)')).toBeVisible();
  });

  test('should display BUY actions in green', async ({ page }) => {
    await page.getByRole('button', { name: /view.*disagreement/i }).click();

    // Find BUY action badges and verify green color
    const buyBadges = page.locator('text=BUY').first();
    await expect(buyBadges).toHaveClass(/text-green/);
  });

  test('should display SELL actions in red', async ({ page }) => {
    await page.getByRole('button', { name: /view.*disagreement/i }).click();

    // Find SELL action badge and verify red color
    const sellBadge = page.locator('text=SELL').first();
    await expect(sellBadge).toHaveClass(/text-red/);
  });

  test('should display NEUTRAL actions in gray', async ({ page }) => {
    await page.getByRole('button', { name: /view.*disagreement/i }).click();

    // Find NEUTRAL action badge and verify gray color
    const neutralBadge = page.locator('text=NEUTRAL').first();
    await expect(neutralBadge).toHaveClass(/text-gray/);
  });

  test('should display timestamps', async ({ page }) => {
    await page.getByRole('button', { name: /view.*disagreement/i }).click();

    // Verify timestamp format is present (HH:MM:SS)
    await expect(page.locator('text=/\\d{1,2}:\\d{2}:\\d{2}/').first()).toBeVisible();
  });

  test('should show loading state initially', async ({ page }) => {
    // Delay the API response to see loading state
    await page.route('**/disagreement/current/EUR_USD', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDisagreementData)
      });
    });

    await page.goto('/test/agent-disagreement');
    await page.getByRole('button', { name: /view.*disagreement/i }).click();

    // Check for loading indicator
    await expect(page.getByText(/loading.*disagreement/i)).toBeVisible();

    // Wait for data to load
    await expect(page.getByText('Agent Consensus')).toBeVisible({ timeout: 3000 });
  });

  test('should display error state on API failure', async ({ page }) => {
    // Mock API failure
    await page.route('**/disagreement/current/EUR_USD', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal server error' })
      });
    });

    await page.goto('/test/agent-disagreement');
    await page.getByRole('button', { name: /view.*disagreement/i }).click();

    // Verify error message is displayed
    await expect(page.getByText(/failed.*disagreement/i)).toBeVisible();
  });

  test('should hide panel when collapsed', async ({ page }) => {
    await page.getByRole('button', { name: /view.*disagreement/i }).click();

    // Verify panel is visible
    const panel = page.locator('[class*="agent-disagreement-panel"]');
    await expect(panel).toBeVisible();

    // Click to collapse
    await page.getByRole('button', { name: /hide.*disagreement/i }).click();

    // Verify panel is hidden
    await expect(panel).not.toBeVisible();
  });

  test('should display grid layout for agent cards', async ({ page }) => {
    await page.getByRole('button', { name: /view.*disagreement/i }).click();

    // Verify grid layout class is present
    const agentPositionsContainer = page.locator('.agent-positions > div').first();
    await expect(agentPositionsContainer).toHaveClass(/grid/);
  });

  test('should be responsive on mobile viewports', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    await page.getByRole('button', { name: /view.*disagreement/i }).click();

    // Verify panel is still visible and functional
    const panel = page.locator('[class*="agent-disagreement-panel"]');
    await expect(panel).toBeVisible();

    // Check that agent cards are displayed (should stack on mobile)
    const agentCards = page.getByTestId('agent-position-card');
    await expect(agentCards).toHaveCount(8);
  });

  test('should update consensus meter color based on percentage', async ({ page }) => {
    // Test with different consensus percentages
    const testCases = [
      { percentage: 45, color: 'rgb(239, 68, 68)' }, // Red <50%
      { percentage: 65, color: 'rgb(234, 179, 8)' }, // Yellow 50-69%
      { percentage: 85, color: 'rgb(132, 204, 22)' }, // Light Green 70-89%
      { percentage: 95, color: 'rgb(34, 197, 94)' } // Dark Green 90-100%
    ];

    for (const testCase of testCases) {
      await page.route('**/disagreement/current/EUR_USD', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            ...mockDisagreementData,
            consensusPercentage: testCase.percentage
          })
        });
      });

      await page.reload();
      await page.getByRole('button', { name: /view.*disagreement/i }).click();

      const consensusPercentage = page.getByTestId('consensus-percentage');
      await expect(consensusPercentage).toContainText(`${testCase.percentage}%`);
      await expect(consensusPercentage).toHaveCSS('color', testCase.color);

      // Close panel for next iteration
      await page.getByRole('button', { name: /hide.*disagreement/i }).click();
    }
  });

  test('should display correct threshold status', async ({ page }) => {
    // Test threshold not met scenario
    await page.route('**/disagreement/current/EUR_USD', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ...mockDisagreementData,
          consensusPercentage: 55,
          thresholdMet: false
        })
      });
    });

    await page.goto('/test/agent-disagreement');
    await page.getByRole('button', { name: /view.*disagreement/i }).click();

    // Verify warning icon is shown
    const warningIcon = page.getByTestId('warning-icon');
    await expect(warningIcon).toBeVisible();

    // Check threshold not met message
    await expect(page.getByTestId('threshold-not-met')).toContainText('Threshold NOT met');
  });

  test('should handle accessibility requirements', async ({ page }) => {
    await page.getByRole('button', { name: /view.*disagreement/i }).click();

    // Check ARIA labels on consensus meter
    const consensusMeter = page.locator('[aria-label*="Consensus"]');
    await expect(consensusMeter).toBeVisible();

    // Check ARIA attributes on confidence bars
    const confidenceBar = page.getByRole('progressbar').first();
    await expect(confidenceBar).toHaveAttribute('aria-valuenow');
    await expect(confidenceBar).toHaveAttribute('aria-valuemin', '0');
    await expect(confidenceBar).toHaveAttribute('aria-valuemax', '100');
  });
});
