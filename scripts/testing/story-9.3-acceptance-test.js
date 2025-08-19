/**
 * Story 9.3 Acceptance Criteria Testing Script
 * OANDA Account Information Display
 * 
 * This script validates all 5 acceptance criteria for Story 9.3:
 * AC1: Account overview dashboard showing balance, equity, margin for all connected OANDA accounts
 * AC2: Real-time updates with visual indicators for active data streams
 * AC3: Trading limits and utilization tracking
 * AC4: Historical performance charts with multiple timeframes
 * AC5: Multi-account summary view with drill-down capability
 */

const { chromium } = require('playwright')
const path = require('path')

class Story93AcceptanceTest {
  constructor() {
    this.browser = null
    this.page = null
    this.results = {
      ac1: { passed: false, details: [] },
      ac2: { passed: false, details: [] },
      ac3: { passed: false, details: [] },
      ac4: { passed: false, details: [] },
      ac5: { passed: false, details: [] }
    }
  }

  async setup() {
    console.log('🚀 Setting up Story 9.3 Acceptance Tests...')
    
    this.browser = await chromium.launch({ 
      headless: false,
      slowMo: 1000 
    })
    
    this.page = await this.browser.newPage()
    
    // Set viewport for consistent testing
    await this.page.setViewportSize({ width: 1440, height: 900 })
    
    // Navigate to OANDA dashboard
    await this.page.goto('http://localhost:3000/oanda')
    
    // Wait for page to load
    await this.page.waitForTimeout(3000)
    
    console.log('✅ Setup completed')
  }

  async testAC1_AccountOverviewDashboard() {
    console.log('\n📊 Testing AC1: Account Overview Dashboard')
    
    try {
      // Check if summary view is displayed by default
      const summaryView = await this.page.isVisible('[data-testid="multi-account-summary"]') || 
                         await this.page.isVisible('h2:has-text("Portfolio Overview")')
      
      if (summaryView) {
        this.results.ac1.details.push('✅ Portfolio summary view is displayed')
      }

      // Navigate to accounts grid view
      await this.page.click('button:has-text("Accounts")')
      await this.page.waitForTimeout(1000)

      // Check for account cards displaying key metrics
      const accountCards = await this.page.locator('[data-testid="account-card"]').count() ||
                          await this.page.locator('.account-overview-card, [class*="Card"]:has(h3)').count()

      if (accountCards > 0) {
        this.results.ac1.details.push(`✅ Found ${accountCards} account overview cards`)

        // Check for required account information in cards
        const balanceVisible = await this.page.isVisible('text=/Balance|balance/i')
        const equityVisible = await this.page.isVisible('text=/Equity|NAV/i')
        const marginVisible = await this.page.isVisible('text=/Margin/i')

        if (balanceVisible) this.results.ac1.details.push('✅ Balance information displayed')
        if (equityVisible) this.results.ac1.details.push('✅ Equity/NAV information displayed')
        if (marginVisible) this.results.ac1.details.push('✅ Margin information displayed')

        // Check for account identification
        const accountIds = await this.page.isVisible('text=/ID:|Account/i')
        const accountTypes = await this.page.isVisible('text=/LIVE|DEMO|MT4/i')
        const currencies = await this.page.isVisible('text=/USD|EUR|GBP/i')

        if (accountIds) this.results.ac1.details.push('✅ Account IDs displayed')
        if (accountTypes) this.results.ac1.details.push('✅ Account types displayed')
        if (currencies) this.results.ac1.details.push('✅ Account currencies displayed')

        this.results.ac1.passed = balanceVisible && equityVisible && marginVisible
      } else {
        this.results.ac1.details.push('❌ No account cards found')
      }

    } catch (error) {
      this.results.ac1.details.push(`❌ Error testing AC1: ${error.message}`)
    }

    console.log(`AC1 Result: ${this.results.ac1.passed ? '✅ PASSED' : '❌ FAILED'}`)
    this.results.ac1.details.forEach(detail => console.log(`   ${detail}`))
  }

  async testAC2_RealTimeUpdates() {
    console.log('\n🔄 Testing AC2: Real-time Updates with Visual Indicators')
    
    try {
      // Check for live data indicators
      const liveIndicator = await this.page.isVisible('text=/Live|last updated|updating/i')
      
      if (liveIndicator) {
        this.results.ac2.details.push('✅ Live data indicators present')
      }

      // Check for connection status display
      const connectionStatus = await this.page.isVisible('text=/Connection Status|connected|disconnected/i')
      
      if (connectionStatus) {
        this.results.ac2.details.push('✅ Connection status indicators present')
      }

      // Check for refresh functionality
      const refreshButton = await this.page.isVisible('button:has-text("Refresh")')
      
      if (refreshButton) {
        this.results.ac2.details.push('✅ Manual refresh button available')
        
        // Test refresh functionality
        await this.page.click('button:has-text("Refresh")')
        await this.page.waitForTimeout(2000)
        
        const refreshingIndicator = await this.page.isVisible('text=/Refreshing|Updating/i')
        if (refreshingIndicator) {
          this.results.ac2.details.push('✅ Refresh state indicator working')
        }
      }

      // Check for timestamp display
      const timestamp = await this.page.isVisible('text=/Last updated:|updated:/i')
      
      if (timestamp) {
        this.results.ac2.details.push('✅ Last update timestamp displayed')
      }

      // Check for real-time data subscription
      const wsIndicators = await this.page.evaluate(() => {
        // Check if real-time data hooks are working
        const hasLiveData = document.querySelector('[data-live="true"]') !== null ||
                           document.body.textContent.includes('Live') ||
                           document.body.textContent.includes('Real-time')
        return hasLiveData
      })

      if (wsIndicators) {
        this.results.ac2.details.push('✅ Real-time data subscription indicators found')
      }

      this.results.ac2.passed = liveIndicator && connectionStatus && refreshButton

    } catch (error) {
      this.results.ac2.details.push(`❌ Error testing AC2: ${error.message}`)
    }

    console.log(`AC2 Result: ${this.results.ac2.passed ? '✅ PASSED' : '❌ FAILED'}`)
    this.results.ac2.details.forEach(detail => console.log(`   ${detail}`))
  }

  async testAC3_TradingLimitsTracking() {
    console.log('\n📈 Testing AC3: Trading Limits and Utilization Tracking')
    
    try {
      // First, navigate to charts view to see trading limits
      const chartsButton = await this.page.isVisible('button:has-text("Charts")')
      
      if (chartsButton) {
        // Need to select an account first
        const accountCard = await this.page.locator('.account-overview-card, [class*="Card"]:has(h3)').first()
        if (await accountCard.count() > 0) {
          await accountCard.click()
          await this.page.waitForTimeout(2000)
        }
      }

      // Check for margin utilization displays
      const marginUtilization = await this.page.isVisible('text=/Margin Utilization|margin.*utilization/i')
      
      if (marginUtilization) {
        this.results.ac3.details.push('✅ Margin utilization tracking displayed')
      }

      // Check for margin level indicators
      const marginLevel = await this.page.isVisible('text=/Margin Level/i')
      
      if (marginLevel) {
        this.results.ac3.details.push('✅ Margin level indicators present')
      }

      // Check for trading limits section
      const tradingLimits = await this.page.isVisible('text=/Trading Limits|Max Position|Max Trades|Drawdown/i')
      
      if (tradingLimits) {
        this.results.ac3.details.push('✅ Trading limits section found')
        
        // Check for specific limit types
        const positionLimits = await this.page.isVisible('text=/Max Position Size|Position.*Size/i')
        const tradeLimits = await this.page.isVisible('text=/Max.*Trades|Open.*Trades/i')
        const drawdownLimits = await this.page.isVisible('text=/Drawdown|Loss.*Limit/i')
        
        if (positionLimits) this.results.ac3.details.push('✅ Position size limits displayed')
        if (tradeLimits) this.results.ac3.details.push('✅ Trade count limits displayed')
        if (drawdownLimits) this.results.ac3.details.push('✅ Drawdown limits displayed')
      }

      // Check for utilization bars/indicators
      const utilizationBars = await this.page.locator('[style*="width"]').count()
      
      if (utilizationBars > 0) {
        this.results.ac3.details.push('✅ Utilization progress bars/indicators found')
      }

      // Check for risk indicators
      const riskIndicators = await this.page.isVisible('text=/Risk Score|risk.*score/i')
      
      if (riskIndicators) {
        this.results.ac3.details.push('✅ Risk scoring indicators present')
      }

      this.results.ac3.passed = marginUtilization && (tradingLimits || marginLevel)

    } catch (error) {
      this.results.ac3.details.push(`❌ Error testing AC3: ${error.message}`)
    }

    console.log(`AC3 Result: ${this.results.ac3.passed ? '✅ PASSED' : '❌ FAILED'}`)
    this.results.ac3.details.forEach(detail => console.log(`   ${detail}`))
  }

  async testAC4_HistoricalPerformanceCharts() {
    console.log('\n📊 Testing AC4: Historical Performance Charts')
    
    try {
      // Ensure we're in charts view
      const chartsButton = await this.page.isVisible('button:has-text("Charts")')
      
      if (chartsButton && !await this.page.isVisible('text=/Back to Grid/i')) {
        // Select an account if not already selected
        await this.page.click('button:has-text("Accounts")')
        await this.page.waitForTimeout(1000)
        
        const accountCard = await this.page.locator('.account-overview-card, [class*="Card"]:has(h3)').first()
        if (await accountCard.count() > 0) {
          await accountCard.click()
          await this.page.waitForTimeout(2000)
        }
      }

      // Check for chart canvas/SVG elements
      const chartElements = await this.page.locator('svg, canvas, [class*="chart"]').count()
      
      if (chartElements > 0) {
        this.results.ac4.details.push(`✅ Found ${chartElements} chart elements`)
      }

      // Check for chart type tabs
      const chartTabs = await this.page.isVisible('text=/Balance|Equity|Drawdown|P&L/i')
      
      if (chartTabs) {
        this.results.ac4.details.push('✅ Chart type selection tabs found')
        
        // Test switching between chart types
        const balanceTab = await this.page.locator('button:has-text("Balance")').first()
        if (await balanceTab.count() > 0) {
          await balanceTab.click()
          await this.page.waitForTimeout(1000)
          this.results.ac4.details.push('✅ Balance chart tab functional')
        }
      }

      // Check for timeframe selector
      const timeframeSelector = await this.page.isVisible('text=/Time Frame|1H|1D|1W|1M/i')
      
      if (timeframeSelector) {
        this.results.ac4.details.push('✅ Timeframe selector present')
        
        // Test timeframe switching
        const dayButton = await this.page.locator('button:has-text("1D")').first()
        if (await dayButton.count() > 0) {
          await dayButton.click()
          await this.page.waitForTimeout(1000)
          this.results.ac4.details.push('✅ Timeframe switching functional')
        }
      }

      // Check for performance metrics
      const performanceMetrics = await this.page.isVisible('text=/Total Return|Sharpe Ratio|Win Rate|Profit Factor/i')
      
      if (performanceMetrics) {
        this.results.ac4.details.push('✅ Performance metrics displayed')
      }

      // Check for chart interactivity (tooltips, hover)
      const interactiveElements = await this.page.locator('circle, rect, [class*="tooltip"]').count()
      
      if (interactiveElements > 0) {
        this.results.ac4.details.push('✅ Interactive chart elements found')
      }

      this.results.ac4.passed = chartElements > 0 && (chartTabs || timeframeSelector)

    } catch (error) {
      this.results.ac4.details.push(`❌ Error testing AC4: ${error.message}`)
    }

    console.log(`AC4 Result: ${this.results.ac4.passed ? '✅ PASSED' : '❌ FAILED'}`)
    this.results.ac4.details.forEach(detail => console.log(`   ${detail}`))
  }

  async testAC5_MultiAccountSummary() {
    console.log('\n📋 Testing AC5: Multi-account Summary with Drill-down')
    
    try {
      // Navigate to summary view
      await this.page.click('button:has-text("Summary")')
      await this.page.waitForTimeout(2000)

      // Check for portfolio overview
      const portfolioOverview = await this.page.isVisible('text=/Portfolio Overview|Total Balance|Total Equity/i')
      
      if (portfolioOverview) {
        this.results.ac5.details.push('✅ Portfolio overview section present')
      }

      // Check for aggregated metrics
      const aggregatedMetrics = await this.page.isVisible('text=/Total Balance|Total Equity|Unrealized P&L|Daily P&L/i')
      
      if (aggregatedMetrics) {
        this.results.ac5.details.push('✅ Aggregated portfolio metrics displayed')
      }

      // Check for account health breakdown
      const healthBreakdown = await this.page.isVisible('text=/Account Health|Health Breakdown|healthy|warning|danger/i')
      
      if (healthBreakdown) {
        this.results.ac5.details.push('✅ Account health status breakdown present')
      }

      // Check for currency breakdown
      const currencyBreakdown = await this.page.isVisible('text=/Currency Breakdown|USD|EUR/i')
      
      if (currencyBreakdown) {
        this.results.ac5.details.push('✅ Currency breakdown section found')
      }

      // Test drill-down functionality
      const drillDownButtons = await this.page.locator('button:has-text("View"), [class*="cursor-pointer"]').count()
      
      if (drillDownButtons > 0) {
        this.results.ac5.details.push(`✅ Found ${drillDownButtons} drill-down interactive elements`)
        
        // Test clicking on a drill-down element
        const viewAllButton = await this.page.locator('button:has-text("View All Accounts")').first()
        if (await viewAllButton.count() > 0) {
          await viewAllButton.click()
          await this.page.waitForTimeout(2000)
          
          // Should navigate to accounts grid
          const gridView = await this.page.isVisible('button:has-text("Summary")')
          if (gridView) {
            this.results.ac5.details.push('✅ Drill-down navigation functional')
            
            // Navigate back to summary
            await this.page.click('button:has-text("Summary")')
            await this.page.waitForTimeout(1000)
          }
        }
      }

      // Check for quick action buttons
      const quickActions = await this.page.isVisible('text=/Quick Actions|View All|View Warnings|View High Risk/i')
      
      if (quickActions) {
        this.results.ac5.details.push('✅ Quick action buttons present')
      }

      // Check for detailed metrics toggle
      const detailedMetrics = await this.page.isVisible('text=/Detailed Metrics|Margin Information|Position Summary/i')
      
      if (detailedMetrics) {
        this.results.ac5.details.push('✅ Detailed metrics section available')
      }

      this.results.ac5.passed = portfolioOverview && aggregatedMetrics && drillDownButtons > 0

    } catch (error) {
      this.results.ac5.details.push(`❌ Error testing AC5: ${error.message}`)
    }

    console.log(`AC5 Result: ${this.results.ac5.passed ? '✅ PASSED' : '❌ FAILED'}`)
    this.results.ac5.details.forEach(detail => console.log(`   ${detail}`))
  }

  async generateReport() {
    console.log('\n📄 Generating Acceptance Test Report...')
    
    const timestamp = new Date().toISOString()
    const passedCount = Object.values(this.results).filter(r => r.passed).length
    const totalCount = Object.keys(this.results).length
    
    const report = {
      story: 'Story 9.3 - OANDA Account Information Display',
      timestamp,
      summary: {
        total: totalCount,
        passed: passedCount,
        failed: totalCount - passedCount,
        success_rate: `${((passedCount / totalCount) * 100).toFixed(1)}%`
      },
      acceptance_criteria: {
        ac1: {
          title: 'Account overview dashboard showing balance, equity, margin for all connected OANDA accounts',
          ...this.results.ac1
        },
        ac2: {
          title: 'Real-time updates with visual indicators for active data streams',
          ...this.results.ac2
        },
        ac3: {
          title: 'Trading limits and utilization tracking',
          ...this.results.ac3
        },
        ac4: {
          title: 'Historical performance charts with multiple timeframes',
          ...this.results.ac4
        },
        ac5: {
          title: 'Multi-account summary view with drill-down capability',
          ...this.results.ac5
        }
      }
    }

    // Save report to file
    const fs = require('fs')
    const reportPath = path.join(__dirname, '../../test-results', `story-9.3-acceptance-test-${Date.now()}.json`)
    
    // Ensure test-results directory exists
    const testResultsDir = path.dirname(reportPath)
    if (!fs.existsSync(testResultsDir)) {
      fs.mkdirSync(testResultsDir, { recursive: true })
    }
    
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2))
    
    console.log(`\n📊 STORY 9.3 ACCEPTANCE TEST RESULTS`)
    console.log(`=====================================`)
    console.log(`Success Rate: ${report.summary.success_rate}`)
    console.log(`Passed: ${report.summary.passed}/${report.summary.total}`)
    console.log(`Failed: ${report.summary.failed}/${report.summary.total}`)
    console.log(`\nReport saved to: ${reportPath}`)
    
    return report
  }

  async cleanup() {
    if (this.browser) {
      await this.browser.close()
    }
  }

  async run() {
    try {
      await this.setup()
      await this.testAC1_AccountOverviewDashboard()
      await this.testAC2_RealTimeUpdates()
      await this.testAC3_TradingLimitsTracking()
      await this.testAC4_HistoricalPerformanceCharts()
      await this.testAC5_MultiAccountSummary()
      
      const report = await this.generateReport()
      
      // Return overall success
      const allPassed = Object.values(this.results).every(r => r.passed)
      console.log(`\n${allPassed ? '🎉 ALL ACCEPTANCE CRITERIA PASSED!' : '⚠️  SOME ACCEPTANCE CRITERIA FAILED'}`)
      
      return allPassed
      
    } catch (error) {
      console.error('❌ Test execution failed:', error)
      return false
    } finally {
      await this.cleanup()
    }
  }
}

// Run the test if called directly
if (require.main === module) {
  const test = new Story93AcceptanceTest()
  test.run().then(success => {
    process.exit(success ? 0 : 1)
  }).catch(error => {
    console.error('Fatal error:', error)
    process.exit(1)
  })
}

module.exports = Story93AcceptanceTest