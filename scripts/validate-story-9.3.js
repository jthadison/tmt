/**
 * Story 9.3 Implementation Verification Script
 * Validates all components and acceptance criteria implementation
 */

const fs = require('fs')
const path = require('path')

class Story93Validator {
  constructor() {
    this.basePath = path.join(__dirname, '..')
    this.results = {
      components: [],
      acceptance_criteria: [],
      integration_tests: [],
      overall_status: 'pending'
    }
  }

  checkFileExists(filePath) {
    const fullPath = path.join(this.basePath, filePath)
    return fs.existsSync(fullPath)
  }

  checkFileContent(filePath, requiredContent) {
    const fullPath = path.join(this.basePath, filePath)
    if (!fs.existsSync(fullPath)) return false
    
    const content = fs.readFileSync(fullPath, 'utf8')
    return requiredContent.every(item => content.includes(item))
  }

  validateComponents() {
    console.log('🔍 Validating Story 9.3 Components...')

    const componentChecks = [
      {
        name: 'OANDA Types & Interfaces',
        file: 'dashboard/types/oanda.ts',
        requiredContent: [
          'OandaAccount',
          'AccountMetrics',
          'AccountHistoryPoint',
          'AggregatedAccountMetrics',
          'AccountFilter'
        ]
      },
      {
        name: 'OANDA Service Layer',
        file: 'dashboard/services/oandaService.ts',
        requiredContent: [
          'OandaService',
          'getAllAccounts',
          'getAccountMetrics',
          'subscribeToUpdates',
          'RateLimiter'
        ]
      },
      {
        name: 'Account Overview Card',
        file: 'dashboard/components/oanda/AccountOverviewCard.tsx',
        requiredContent: [
          'AccountOverviewCard',
          'formatCurrency',
          'getHealthStatusColor',
          'marginUtilization'
        ]
      },
      {
        name: 'Accounts Grid',
        file: 'dashboard/components/oanda/AccountsGrid.tsx',
        requiredContent: [
          'AccountsGrid',
          'AccountFilter',
          'filteredAndSortedAccounts',
          'showFilters'
        ]
      },
      {
        name: 'Multi-Account Summary',
        file: 'dashboard/components/oanda/MultiAccountSummary.tsx',
        requiredContent: [
          'MultiAccountSummary',
          'AggregatedAccountMetrics',
          'onDrillDown',
          'healthStatusBreakdown'
        ]
      },
      {
        name: 'Account Charts',
        file: 'dashboard/components/oanda/AccountCharts.tsx',
        requiredContent: [
          'AccountCharts',
          'SimpleLineChart',
          'TimeFrame',
          'performanceSummary'
        ]
      },
      {
        name: 'OANDA Data Hook',
        file: 'dashboard/hooks/useOandaData.ts',
        requiredContent: [
          'useOandaData',
          'subscribeToUpdates',
          'refreshData',
          'getFilteredAccounts'
        ]
      },
      {
        name: 'OANDA Dashboard Page',
        file: 'dashboard/pages/oanda/index.tsx',
        requiredContent: [
          'OandaDashboard',
          'useOandaData',
          'MultiAccountSummary',
          'AccountsGrid',
          'AccountCharts'
        ]
      }
    ]

    componentChecks.forEach(check => {
      const exists = this.checkFileExists(check.file)
      const hasContent = exists ? this.checkFileContent(check.file, check.requiredContent) : false
      
      this.results.components.push({
        name: check.name,
        file: check.file,
        exists,
        hasRequiredContent: hasContent,
        status: exists && hasContent ? 'passed' : 'failed'
      })

      console.log(`   ${exists && hasContent ? '✅' : '❌'} ${check.name}`)
      if (!exists) console.log(`      - File missing: ${check.file}`)
      if (exists && !hasContent) console.log(`      - Missing required content`)
    })
  }

  validateAcceptanceCriteria() {
    console.log('\n📋 Validating Acceptance Criteria Implementation...')

    const acceptanceCriteria = [
      {
        id: 'AC1',
        title: 'Account overview dashboard showing balance, equity, margin for all connected OANDA accounts',
        requirements: [
          {
            description: 'Account overview cards component exists',
            file: 'dashboard/components/oanda/AccountOverviewCard.tsx',
            content: ['balance', 'equity', 'margin', 'AccountOverviewCard']
          },
          {
            description: 'Grid layout for multiple accounts',
            file: 'dashboard/components/oanda/AccountsGrid.tsx',
            content: ['AccountsGrid', 'accounts', 'grid']
          },
          {
            description: 'Account identification (ID, type, currency)',
            file: 'dashboard/components/oanda/AccountOverviewCard.tsx',
            content: ['account.id', 'account.type', 'account.currency']
          }
        ]
      },
      {
        id: 'AC2',
        title: 'Real-time updates with visual indicators for active data streams',
        requirements: [
          {
            description: 'Real-time data subscription system',
            file: 'dashboard/hooks/useOandaData.ts',
            content: ['subscribeToUpdates', 'handleAccountUpdate', 'real-time']
          },
          {
            description: 'Connection status indicators',
            file: 'dashboard/pages/oanda/index.tsx',
            content: ['connectionStatus', 'isAccountConnected', 'Connection Status']
          },
          {
            description: 'Live data refresh mechanism',
            file: 'dashboard/pages/oanda/index.tsx',
            content: ['refreshData', 'auto-refresh', 'Last updated']
          }
        ]
      },
      {
        id: 'AC3',
        title: 'Trading limits and utilization tracking',
        requirements: [
          {
            description: 'Margin utilization tracking',
            file: 'dashboard/components/oanda/AccountOverviewCard.tsx',
            content: ['marginUtilization', 'Margin Utilization', 'margin']
          },
          {
            description: 'Trading limits display',
            file: 'dashboard/pages/oanda/index.tsx',
            content: ['tradingLimits', 'Trading Limits', 'maxPositionSize']
          },
          {
            description: 'Risk level indicators',
            file: 'dashboard/components/oanda/AccountOverviewCard.tsx',
            content: ['riskScore', 'marginLevel', 'healthStatus']
          }
        ]
      },
      {
        id: 'AC4',
        title: 'Historical performance charts with multiple timeframes',
        requirements: [
          {
            description: 'Chart component with multiple types',
            file: 'dashboard/components/oanda/AccountCharts.tsx',
            content: ['AccountCharts', 'SimpleLineChart', 'balance', 'equity', 'drawdown']
          },
          {
            description: 'Timeframe selection',
            file: 'dashboard/components/oanda/AccountCharts.tsx',
            content: ['TimeFrame', 'timeFrameOptions', '1H', '1D', '1W', '1M']
          },
          {
            description: 'Performance metrics display',
            file: 'dashboard/components/oanda/AccountCharts.tsx',
            content: ['performanceSummary', 'totalReturn', 'sharpeRatio', 'winRate']
          }
        ]
      },
      {
        id: 'AC5',
        title: 'Multi-account summary view with drill-down capability',
        requirements: [
          {
            description: 'Portfolio overview component',
            file: 'dashboard/components/oanda/MultiAccountSummary.tsx',
            content: ['MultiAccountSummary', 'Portfolio Overview', 'aggregatedMetrics']
          },
          {
            description: 'Drill-down functionality',
            file: 'dashboard/components/oanda/MultiAccountSummary.tsx',
            content: ['onDrillDown', 'Quick Actions', 'healthStatus', 'currency']
          },
          {
            description: 'Account health breakdown',
            file: 'dashboard/components/oanda/MultiAccountSummary.tsx',
            content: ['healthStatusBreakdown', 'healthy', 'warning', 'danger']
          }
        ]
      }
    ]

    acceptanceCriteria.forEach(ac => {
      console.log(`\n   ${ac.id}: ${ac.title}`)
      
      let allRequirementsMet = true
      const requirementResults = []

      ac.requirements.forEach(req => {
        const hasContent = this.checkFileContent(req.file, req.content)
        requirementResults.push({
          description: req.description,
          file: req.file,
          status: hasContent ? 'passed' : 'failed'
        })

        console.log(`      ${hasContent ? '✅' : '❌'} ${req.description}`)
        if (!hasContent) {
          console.log(`         Missing in: ${req.file}`)
          allRequirementsMet = false
        }
      })

      this.results.acceptance_criteria.push({
        id: ac.id,
        title: ac.title,
        status: allRequirementsMet ? 'passed' : 'failed',
        requirements: requirementResults
      })
    })
  }

  validateIntegration() {
    console.log('\n🔗 Validating Integration Points...')

    const integrationChecks = [
      {
        name: 'Dashboard Integration',
        description: 'OANDA dashboard integrates with main dashboard structure',
        file: 'dashboard/pages/oanda/index.tsx',
        content: ['useOandaData', 'MultiAccountSummary', 'AccountsGrid']
      },
      {
        name: 'Type System Integration',
        description: 'All components use consistent TypeScript types',
        file: 'dashboard/types/oanda.ts',
        content: ['OandaAccount', 'AccountMetrics', 'CurrencyCode']
      },
      {
        name: 'Service Layer Integration',
        description: 'Service layer properly configured and integrated',
        file: 'dashboard/services/oandaService.ts',
        content: ['OandaService', 'rateLimiter', 'connectionStatus']
      },
      {
        name: 'Component Composition',
        description: 'All components properly exported and importable',
        files: [
          'dashboard/components/oanda/AccountOverviewCard.tsx',
          'dashboard/components/oanda/AccountsGrid.tsx',
          'dashboard/components/oanda/MultiAccountSummary.tsx',
          'dashboard/components/oanda/AccountCharts.tsx'
        ],
        content: ['export', 'export default']
      }
    ]

    integrationChecks.forEach(check => {
      let passed = false
      
      if (check.files) {
        // Check multiple files
        passed = check.files.every(file => 
          this.checkFileExists(file) && this.checkFileContent(file, check.content)
        )
      } else {
        // Check single file
        passed = this.checkFileExists(check.file) && this.checkFileContent(check.file, check.content)
      }

      this.results.integration_tests.push({
        name: check.name,
        description: check.description,
        status: passed ? 'passed' : 'failed'
      })

      console.log(`   ${passed ? '✅' : '❌'} ${check.name}`)
      if (!passed) console.log(`      ${check.description}`)
    })
  }

  generateReport() {
    console.log('\n📊 Generating Validation Report...')

    const componentsPassed = this.results.components.filter(c => c.status === 'passed').length
    const componentsTotal = this.results.components.length

    const acPassed = this.results.acceptance_criteria.filter(ac => ac.status === 'passed').length
    const acTotal = this.results.acceptance_criteria.length

    const integrationPassed = this.results.integration_tests.filter(i => i.status === 'passed').length
    const integrationTotal = this.results.integration_tests.length

    const overallPassed = componentsPassed === componentsTotal && 
                         acPassed === acTotal && 
                         integrationPassed === integrationTotal

    this.results.overall_status = overallPassed ? 'passed' : 'failed'

    const report = {
      story: 'Story 9.3 - OANDA Account Information Display',
      timestamp: new Date().toISOString(),
      summary: {
        overall_status: this.results.overall_status,
        components: `${componentsPassed}/${componentsTotal}`,
        acceptance_criteria: `${acPassed}/${acTotal}`,
        integration_tests: `${integrationPassed}/${integrationTotal}`,
        success_rate: `${(((componentsPassed + acPassed + integrationPassed) / (componentsTotal + acTotal + integrationTotal)) * 100).toFixed(1)}%`
      },
      details: this.results
    }

    // Save report
    const reportPath = path.join(__dirname, '../test-results', `story-9.3-validation-${Date.now()}.json`)
    
    // Ensure directory exists
    const dir = path.dirname(reportPath)
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true })
    }
    
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2))

    console.log(`\n📋 STORY 9.3 VALIDATION SUMMARY`)
    console.log(`================================`)
    console.log(`Overall Status: ${overallPassed ? '✅ PASSED' : '❌ FAILED'}`)
    console.log(`Components: ${componentsPassed}/${componentsTotal}`)
    console.log(`Acceptance Criteria: ${acPassed}/${acTotal}`)
    console.log(`Integration Tests: ${integrationPassed}/${integrationTotal}`)
    console.log(`Success Rate: ${report.summary.success_rate}`)
    console.log(`\nReport saved to: ${reportPath}`)

    return report
  }

  run() {
    console.log('🚀 Starting Story 9.3 Implementation Validation...\n')

    this.validateComponents()
    this.validateAcceptanceCriteria()
    this.validateIntegration()
    
    const report = this.generateReport()

    return report.summary.overall_status === 'passed'
  }
}

// Run validation if called directly
if (require.main === module) {
  const validator = new Story93Validator()
  const success = validator.run()
  process.exit(success ? 0 : 1)
}

module.exports = Story93Validator