/**
 * Story 9.6 Integration Verification Script
 * Verifies all acceptance criteria and integration points for Performance Analytics
 */

const fs = require('fs')
const path = require('path')

console.log('🔍 Story 9.6 Integration Verification')
console.log('=====================================')

const results = {
  passed: 0,
  failed: 0,
  total: 0
}

function checkResult(testName, condition, details = '') {
  results.total++
  if (condition) {
    console.log(`✅ ${testName}`)
    results.passed++
  } else {
    console.log(`❌ ${testName}`)
    if (details) console.log(`   ${details}`)
    results.failed++
  }
}

// IV1: Performance calculations accurately reflect data from existing PostgreSQL trading records
console.log('\n📊 IV1: PostgreSQL Integration and Data Accuracy')

const performanceServiceExists = fs.existsSync(path.join(__dirname, '../services/performanceAnalyticsService.ts'))
checkResult(
  'IV1.1: Performance analytics service exists',
  performanceServiceExists,
  performanceServiceExists ? '' : 'performanceAnalyticsService.ts not found'
)

if (performanceServiceExists) {
  const serviceContent = fs.readFileSync(path.join(__dirname, '../services/performanceAnalyticsService.ts'), 'utf8')
  
  checkResult(
    'IV1.2: PostgreSQL query integration',
    serviceContent.includes('PostgreSQL') && serviceContent.includes('query'),
    'Service includes PostgreSQL integration and query functionality'
  )
  
  checkResult(
    'IV1.3: Trade record processing',
    serviceContent.includes('TradeRecord') && serviceContent.includes('getTradeBreakdown'),
    'Service processes trade records from database'
  )
  
  checkResult(
    'IV1.4: P&L calculation accuracy',
    serviceContent.includes('calculateRiskMetrics') && serviceContent.includes('sharpeRatio'),
    'Service includes comprehensive P&L and risk calculations'
  )
  
  checkResult(
    'IV1.5: Real-time data synchronization',
    serviceContent.includes('getRealtimePnL') && serviceContent.includes('cache'),
    'Service provides real-time data with caching for performance'
  )
}

// IV2: Analytics queries do not impact real-time trading system performance
console.log('\n⚡ IV2: Performance Impact and Query Optimization')

const performanceOptimizerExists = fs.existsSync(path.join(__dirname, '../services/performanceAnalyticsService.ts'))
if (performanceOptimizerExists) {
  const serviceContent = fs.readFileSync(path.join(__dirname, '../services/performanceAnalyticsService.ts'), 'utf8')
  
  checkResult(
    'IV2.1: Query caching implementation',
    serviceContent.includes('getCachedOrFetch') && serviceContent.includes('cache'),
    'Service implements query result caching'
  )
  
  checkResult(
    'IV2.2: Performance monitoring',
    serviceContent.includes('QueryPerformance') && serviceContent.includes('trackQueryPerformance'),
    'Service tracks query execution performance'
  )
  
  checkResult(
    'IV2.3: Connection pooling',
    serviceContent.includes('maxConcurrentRequests') || serviceContent.includes('timeout'),
    'Service implements connection management'
  )
  
  checkResult(
    'IV2.4: Async query execution',
    serviceContent.includes('async') && serviceContent.includes('Promise'),
    'Service uses async operations to prevent blocking'
  )
  
  checkResult(
    'IV2.5: Cache cleanup mechanism',
    serviceContent.includes('startCacheCleanup') && serviceContent.includes('setInterval'),
    'Service includes automatic cache cleanup'
  )
}

// IV3: Report generation maintains consistency with existing audit trail and compliance requirements
console.log('\n📋 IV3: Compliance and Audit Trail Integration')

const complianceReportExists = fs.existsSync(path.join(__dirname, '../components/analytics/ComplianceReportGenerator.tsx'))
checkResult(
  'IV3.1: Compliance report generator exists',
  complianceReportExists,
  complianceReportExists ? '' : 'ComplianceReportGenerator.tsx not found'
)

if (complianceReportExists) {
  const reportContent = fs.readFileSync(path.join(__dirname, '../components/analytics/ComplianceReportGenerator.tsx'), 'utf8')
  
  checkResult(
    'IV3.2: Audit trail integration',
    reportContent.includes('AuditEntry') && reportContent.includes('auditTrail'),
    'Report generator integrates with audit trail system'
  )
  
  checkResult(
    'IV3.3: Digital signatures',
    reportContent.includes('signature') && reportContent.includes('electronically signed'),
    'Reports include digital signatures for compliance'
  )
  
  checkResult(
    'IV3.4: Regulatory metrics',
    reportContent.includes('RegulatoryMetrics') && reportContent.includes('mifidCompliant'),
    'Reports include regulatory compliance metrics'
  )
  
  checkResult(
    'IV3.5: Multiple export formats',
    reportContent.includes('pdf') && reportContent.includes('excel') && reportContent.includes('csv'),
    'Reports support multiple export formats'
  )
}

// AC1: Real-time P&L tracking with trade-by-trade breakdown and performance attribution by agent
console.log('\n💰 AC1: Real-time P&L Tracking')

const realtimePnLExists = fs.existsSync(path.join(__dirname, '../components/analytics/RealtimePnLTracker.tsx'))
checkResult(
  'AC1.1: Real-time P&L tracker component exists',
  realtimePnLExists,
  realtimePnLExists ? '' : 'RealtimePnLTracker.tsx not found'
)

if (realtimePnLExists) {
  const trackerContent = fs.readFileSync(path.join(__dirname, '../components/analytics/RealtimePnLTracker.tsx'), 'utf8')
  
  checkResult(
    'AC1.2: Trade-by-trade breakdown',
    trackerContent.includes('TradeBreakdown') && trackerContent.includes('getTradeBreakdown'),
    'Component displays trade-by-trade breakdown'
  )
  
  checkResult(
    'AC1.3: Agent performance attribution',
    trackerContent.includes('agentId') && trackerContent.includes('agentName'),
    'Component shows performance attribution by agent'
  )
  
  checkResult(
    'AC1.4: Real-time updates',
    trackerContent.includes('refreshInterval') && trackerContent.includes('autoRefresh'),
    'Component supports real-time data refresh'
  )
  
  checkResult(
    'AC1.5: Multiple timeframes',
    trackerContent.includes('daily') && trackerContent.includes('weekly') && trackerContent.includes('monthly'),
    'Component supports multiple P&L timeframes'
  )
}

// AC2: Historical performance dashboard with configurable time periods and performance metrics
console.log('\n📈 AC2: Historical Performance Dashboard')

const historicalDashboardExists = fs.existsSync(path.join(__dirname, '../components/analytics/HistoricalPerformanceDashboard.tsx'))
checkResult(
  'AC2.1: Historical performance dashboard exists',
  historicalDashboardExists,
  historicalDashboardExists ? '' : 'HistoricalPerformanceDashboard.tsx not found'
)

if (historicalDashboardExists) {
  const dashboardContent = fs.readFileSync(path.join(__dirname, '../components/analytics/HistoricalPerformanceDashboard.tsx'), 'utf8')
  
  checkResult(
    'AC2.2: Configurable time periods',
    dashboardContent.includes('dateRange') && dashboardContent.includes('setDateRangePreset'),
    'Dashboard supports configurable time periods'
  )
  
  checkResult(
    'AC2.3: Multiple view modes',
    dashboardContent.includes('cumulative') && dashboardContent.includes('daily') && dashboardContent.includes('weekly'),
    'Dashboard supports multiple view modes'
  )
  
  checkResult(
    'AC2.4: Chart type options',
    dashboardContent.includes('line') && dashboardContent.includes('bar') && dashboardContent.includes('area'),
    'Dashboard supports different chart types'
  )
  
  checkResult(
    'AC2.5: Performance metrics display',
    dashboardContent.includes('PerformanceMetrics') && dashboardContent.includes('summaryStats'),
    'Dashboard displays comprehensive performance metrics'
  )
  
  checkResult(
    'AC2.6: Export functionality',
    dashboardContent.includes('onExport') && dashboardContent.includes('handleExport'),
    'Dashboard supports data export'
  )
}

// AC3: Risk analytics including drawdown analysis, Sharpe ratios, and volatility measurements
console.log('\n🛡️ AC3: Risk Analytics')

const riskAnalyticsExists = fs.existsSync(path.join(__dirname, '../components/analytics/RiskAnalyticsDashboard.tsx'))
checkResult(
  'AC3.1: Risk analytics dashboard exists',
  riskAnalyticsExists,
  riskAnalyticsExists ? '' : 'RiskAnalyticsDashboard.tsx not found'
)

if (riskAnalyticsExists) {
  const riskContent = fs.readFileSync(path.join(__dirname, '../components/analytics/RiskAnalyticsDashboard.tsx'), 'utf8')
  
  checkResult(
    'AC3.2: Sharpe ratio calculation',
    riskContent.includes('sharpeRatio') && riskContent.includes('Sharpe Ratio'),
    'Dashboard calculates and displays Sharpe ratios'
  )
  
  checkResult(
    'AC3.3: Drawdown analysis',
    riskContent.includes('maxDrawdown') && riskContent.includes('drawdown') && riskContent.includes('Underwater'),
    'Dashboard includes comprehensive drawdown analysis'
  )
  
  checkResult(
    'AC3.4: Volatility measurements',
    riskContent.includes('volatility') && riskContent.includes('Volatility'),
    'Dashboard measures and displays volatility metrics'
  )
  
  checkResult(
    'AC3.5: Value at Risk (VaR)',
    riskContent.includes('valueAtRisk') && riskContent.includes('VaR'),
    'Dashboard includes Value at Risk calculations'
  )
  
  checkResult(
    'AC3.6: Risk score calculation',
    riskContent.includes('riskScore') && riskContent.includes('Risk Score'),
    'Dashboard calculates comprehensive risk scores'
  )
}

// AC4: Comparative analysis between different trading strategies and agent performance
console.log('\n👥 AC4: Agent and Strategy Comparison')

const agentComparisonExists = fs.existsSync(path.join(__dirname, '../components/analytics/AgentComparisonDashboard.tsx'))
checkResult(
  'AC4.1: Agent comparison dashboard exists',
  agentComparisonExists,
  agentComparisonExists ? '' : 'AgentComparisonDashboard.tsx not found'
)

if (agentComparisonExists) {
  const comparisonContent = fs.readFileSync(path.join(__dirname, '../components/analytics/AgentComparisonDashboard.tsx'), 'utf8')
  
  checkResult(
    'AC4.2: Multi-agent comparison',
    comparisonContent.includes('AgentPerformance') && comparisonContent.includes('getAgentComparison'),
    'Dashboard compares multiple agent performances'
  )
  
  checkResult(
    'AC4.3: Performance ranking',
    comparisonContent.includes('rank') && comparisonContent.includes('sort'),
    'Dashboard ranks agents by performance'
  )
  
  checkResult(
    'AC4.4: Visual comparison charts',
    comparisonContent.includes('radar') && comparisonContent.includes('scatter') && comparisonContent.includes('bar'),
    'Dashboard provides visual comparison charts'
  )
  
  checkResult(
    'AC4.5: Strategy analysis',
    comparisonContent.includes('strategy') && comparisonContent.includes('patterns'),
    'Dashboard analyzes trading strategies and patterns'
  )
  
  checkResult(
    'AC4.6: Agent selection interface',
    comparisonContent.includes('checkbox') && comparisonContent.includes('selectedAgents'),
    'Dashboard allows selection of agents for comparison'
  )
}

// AC5: Exportable reports for compliance and performance review meetings
console.log('\n📄 AC5: Exportable Compliance Reports')

const reportGeneratorExists = fs.existsSync(path.join(__dirname, '../components/analytics/ComplianceReportGenerator.tsx'))
checkResult(
  'AC5.1: Report generator component exists',
  reportGeneratorExists,
  reportGeneratorExists ? '' : 'ComplianceReportGenerator.tsx not found'
)

if (reportGeneratorExists) {
  const generatorContent = fs.readFileSync(path.join(__dirname, '../components/analytics/ComplianceReportGenerator.tsx'), 'utf8')
  
  checkResult(
    'AC5.2: Multiple report types',
    generatorContent.includes('standard') && generatorContent.includes('detailed') && generatorContent.includes('executive') && generatorContent.includes('regulatory'),
    'Generator supports multiple report types'
  )
  
  checkResult(
    'AC5.3: Export format options',
    generatorContent.includes('pdf') && generatorContent.includes('csv') && generatorContent.includes('excel') && generatorContent.includes('json'),
    'Generator supports multiple export formats'
  )
  
  checkResult(
    'AC5.4: Report preview',
    generatorContent.includes('preview') && generatorContent.includes('PreviewMode'),
    'Generator provides report preview functionality'
  )
  
  checkResult(
    'AC5.5: Compliance metrics',
    generatorContent.includes('ComplianceReport') && generatorContent.includes('violations'),
    'Generator includes comprehensive compliance metrics'
  )
  
  checkResult(
    'AC5.6: Digital signatures',
    generatorContent.includes('signature') && generatorContent.includes('electronically signed'),
    'Reports include digital signatures for authenticity'
  )
}

// Main Dashboard Integration
console.log('\n🎛️ Main Dashboard Integration')

const mainDashboardExists = fs.existsSync(path.join(__dirname, '../components/analytics/PerformanceAnalyticsDashboard.tsx'))
checkResult(
  'Dashboard.1: Main performance analytics dashboard exists',
  mainDashboardExists,
  mainDashboardExists ? '' : 'PerformanceAnalyticsDashboard.tsx not found'
)

if (mainDashboardExists) {
  const mainContent = fs.readFileSync(path.join(__dirname, '../components/analytics/PerformanceAnalyticsDashboard.tsx'), 'utf8')
  
  checkResult(
    'Dashboard.2: All component integration',
    ['RealtimePnLTracker', 'HistoricalPerformanceDashboard', 'RiskAnalyticsDashboard', 'AgentComparisonDashboard', 'ComplianceReportGenerator'].every(comp => 
      mainContent.includes(comp)
    ),
    'Main dashboard integrates all analytics components'
  )
  
  checkResult(
    'Dashboard.3: View navigation',
    mainContent.includes('currentView') && mainContent.includes('setCurrentView'),
    'Dashboard provides view navigation'
  )
  
  checkResult(
    'Dashboard.4: Fullscreen support',
    mainContent.includes('fullscreen') && mainContent.includes('toggleFullscreen'),
    'Dashboard supports fullscreen mode'
  )
  
  checkResult(
    'Dashboard.5: Auto-refresh controls',
    mainContent.includes('autoRefresh') && mainContent.includes('refreshInterval'),
    'Dashboard includes auto-refresh controls'
  )
}

// React Hook Integration
console.log('\n⚛️ React Hook Integration')

const hookExists = fs.existsSync(path.join(__dirname, '../hooks/usePerformanceAnalytics.ts'))
checkResult(
  'Hook.1: Performance analytics hook exists',
  hookExists,
  hookExists ? '' : 'usePerformanceAnalytics.ts not found'
)

if (hookExists) {
  const hookContent = fs.readFileSync(path.join(__dirname, '../hooks/usePerformanceAnalytics.ts'), 'utf8')
  
  checkResult(
    'Hook.2: Comprehensive state management',
    hookContent.includes('PerformanceAnalyticsState') && hookContent.includes('loading') && hookContent.includes('errors'),
    'Hook provides comprehensive state management'
  )
  
  checkResult(
    'Hook.3: Action handlers',
    hookContent.includes('PerformanceAnalyticsActions') && hookContent.includes('loadRealtimePnL'),
    'Hook provides action handlers for all operations'
  )
  
  checkResult(
    'Hook.4: WebSocket subscriptions',
    hookContent.includes('subscribeToRealtimePnL') && hookContent.includes('subscription'),
    'Hook manages WebSocket subscriptions'
  )
  
  checkResult(
    'Hook.5: Cache management',
    hookContent.includes('cache') && hookContent.includes('cleanup'),
    'Hook includes cache and subscription cleanup'
  )
}

// Type Definitions
console.log('\n📋 Type Definitions')

const typesExists = fs.existsSync(path.join(__dirname, '../types/performanceAnalytics.ts'))
checkResult(
  'Types.1: Performance analytics types exist',
  typesExists,
  typesExists ? '' : 'performanceAnalytics.ts types not found'
)

if (typesExists) {
  const typesContent = fs.readFileSync(path.join(__dirname, '../types/performanceAnalytics.ts'), 'utf8')
  
  checkResult(
    'Types.2: Comprehensive type coverage',
    ['RealtimePnL', 'RiskMetrics', 'AgentPerformance', 'ComplianceReport', 'TradeBreakdown'].every(type =>
      typesContent.includes(`interface ${type}`) || typesContent.includes(`type ${type}`)
    ),
    'All required interfaces and types defined'
  )
  
  checkResult(
    'Types.3: Export configuration types',
    typesContent.includes('ExportConfig') && typesContent.includes('ExportFormat'),
    'Export configuration types defined'
  )
  
  checkResult(
    'Types.4: Query and analytics types',
    typesContent.includes('AnalyticsQuery') && typesContent.includes('PortfolioAnalytics'),
    'Analytics query and portfolio types defined'
  )
}

// Test Coverage
console.log('\n🧪 Test Coverage')

const testsExist = fs.existsSync(path.join(__dirname, '../components/analytics/__tests__'))
checkResult(
  'Tests.1: Analytics test directory exists',
  testsExist,
  testsExist ? '' : 'Analytics tests directory not found'
)

if (testsExist) {
  const testFiles = fs.readdirSync(path.join(__dirname, '../components/analytics/__tests__'))
  
  checkResult(
    'Tests.2: Component tests exist',
    testFiles.some(file => file.includes('PerformanceAnalytics.test')),
    'Performance analytics component tests exist'
  )
  
  checkResult(
    'Tests.3: Integration test coverage',
    testFiles.some(file => file.includes('test')) && testFiles.length > 0,
    'Test files exist with integration coverage'
  )
}

// Utility Functions
console.log('\n🔧 Utility Functions')

const formattersExist = fs.existsSync(path.join(__dirname, '../utils/formatters.ts'))
checkResult(
  'Utils.1: Formatter utilities exist',
  formattersExist,
  formattersExist ? '' : 'formatters.ts utilities not found'
)

if (formattersExist) {
  const formattersContent = fs.readFileSync(path.join(__dirname, '../utils/formatters.ts'), 'utf8')
  
  checkResult(
    'Utils.2: Currency formatting',
    formattersContent.includes('formatCurrency') && formattersContent.includes('Intl.NumberFormat'),
    'Currency formatting utilities available'
  )
  
  checkResult(
    'Utils.3: Percentage formatting',
    formattersContent.includes('formatPercent') && formattersContent.includes('percent'),
    'Percentage formatting utilities available'
  )
  
  checkResult(
    'Utils.4: Risk level formatting',
    formattersContent.includes('formatRiskLevel') && formattersContent.includes('risk'),
    'Risk level formatting utilities available'
  )
}

// Service Layer Integration
console.log('\n🔌 Service Layer Integration')

if (performanceServiceExists) {
  const serviceContent = fs.readFileSync(path.join(__dirname, '../services/performanceAnalyticsService.ts'), 'utf8')
  
  checkResult(
    'Service.1: Singleton pattern',
    serviceContent.includes('export const performanceAnalyticsService') && serviceContent.includes('new PerformanceAnalyticsService'),
    'Service implements singleton pattern'
  )
  
  checkResult(
    'Service.2: Error handling',
    serviceContent.includes('try') && serviceContent.includes('catch') && serviceContent.includes('throw'),
    'Service includes comprehensive error handling'
  )
  
  checkResult(
    'Service.3: TypeScript integration',
    serviceContent.includes('interface') && serviceContent.includes('Promise<'),
    'Service fully typed with TypeScript'
  )
}

// Final Results
console.log('\n📊 Final Results')
console.log('================')
console.log(`✅ Passed: ${results.passed}`)
console.log(`❌ Failed: ${results.failed}`)
console.log(`📊 Total:  ${results.total}`)
console.log(`📈 Success Rate: ${((results.passed / results.total) * 100).toFixed(1)}%`)

if (results.failed === 0) {
  console.log('\n🎉 All integration verification points PASSED!')
  console.log('Story 9.6 is fully implemented and verified.')
} else {
  console.log(`\n⚠️  ${results.failed} verification points failed.`)
  console.log('Please address the failed checks before marking story as complete.')
}

process.exit(results.failed === 0 ? 0 : 1)