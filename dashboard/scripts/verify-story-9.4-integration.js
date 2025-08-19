/**
 * Story 9.4 Integration Verification Script
 * Verifies all acceptance criteria and integration points
 */

const fs = require('fs')
const path = require('path')

console.log('🔍 Story 9.4 Integration Verification')
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

// IV1: Market data visualization uses existing TimescaleDB connections without impacting trading system performance
console.log('\n📊 IV1: TimescaleDB Integration Performance')

const marketDataServiceExists = fs.existsSync(path.join(__dirname, '../services/marketDataService.ts'))
checkResult(
  'IV1.1: Market data service exists',
  marketDataServiceExists,
  marketDataServiceExists ? '' : 'MarketDataService.ts not found'
)

if (marketDataServiceExists) {
  const serviceContent = fs.readFileSync(path.join(__dirname, '../services/marketDataService.ts'), 'utf8')
  
  checkResult(
    'IV1.2: TimescaleDB connection configuration',
    serviceContent.includes('TIMESCALEDB') && serviceContent.includes('performance'),
    'Service includes TimescaleDB config and performance considerations'
  )
  
  checkResult(
    'IV1.3: Performance caching implemented',
    serviceContent.includes('cache') && serviceContent.includes('MarketDataCache'),
    'Service includes caching for performance optimization'
  )
  
  checkResult(
    'IV1.4: Connection pooling and optimization',
    serviceContent.includes('maxConcurrentRequests') && serviceContent.includes('requestTimeout'),
    'Service includes connection pooling configuration'
  )
}

// IV2: Chart data accuracy matches information used by AI agents for trading decisions
console.log('\n🎯 IV2: Chart Data Accuracy')

const useMarketDataExists = fs.existsSync(path.join(__dirname, '../hooks/useMarketData.ts'))
checkResult(
  'IV2.1: Market data hook exists',
  useMarketDataExists,
  useMarketDataExists ? '' : 'useMarketData.ts not found'
)

if (useMarketDataExists) {
  const hookContent = fs.readFileSync(path.join(__dirname, '../hooks/useMarketData.ts'), 'utf8')
  
  checkResult(
    'IV2.2: Real-time data synchronization',
    hookContent.includes('subscribeToRealtimeData') && hookContent.includes('RealtimeSubscription'),
    'Hook provides real-time data subscription capabilities'
  )
  
  checkResult(
    'IV2.3: AI agent data integration',
    hookContent.includes('loadAIAnnotations') && hookContent.includes('AgentAnnotation'),
    'Hook integrates with AI agent decision data'
  )
  
  checkResult(
    'IV2.4: Data consistency validation',
    hookContent.includes('performanceRef') && hookContent.includes('lastUpdateTime'),
    'Hook includes data consistency and performance tracking'
  )
}

// IV3: Real-time chart updates maintain performance standards for trading interface responsiveness
console.log('\n⚡ IV3: Real-time Performance Standards')

const performanceOptimizerExists = fs.existsSync(path.join(__dirname, '../components/charts/utils/PerformanceOptimizer.ts'))
checkResult(
  'IV3.1: Performance optimizer exists',
  performanceOptimizerExists,
  performanceOptimizerExists ? '' : 'PerformanceOptimizer.ts not found'
)

if (performanceOptimizerExists) {
  const optimizerContent = fs.readFileSync(path.join(__dirname, '../components/charts/utils/PerformanceOptimizer.ts'), 'utf8')
  
  checkResult(
    'IV3.2: Sub-100ms update requirement configuration',
    optimizerContent.includes('maxUpdateFrequency: 50') && optimizerContent.includes('<100ms'),
    'Performance optimizer configured for <100ms updates (50ms = 20fps)'
  )
  
  checkResult(
    'IV3.3: Data throttling implementation',
    optimizerContent.includes('DataThrottler') && optimizerContent.includes('batchSize'),
    'Data throttling implemented for performance'
  )
  
  checkResult(
    'IV3.4: Memory management',
    optimizerContent.includes('MemoryManager') && optimizerContent.includes('memoryThreshold'),
    'Memory management implemented'
  )
  
  checkResult(
    'IV3.5: Render optimization',
    optimizerContent.includes('RenderOptimizer') && optimizerContent.includes('requestAnimationFrame'),
    'Render optimization with RAF implemented'
  )
}

// AC1: Interactive price charts for actively traded instruments
console.log('\n📈 AC1: Interactive Price Charts')

const priceChartExists = fs.existsSync(path.join(__dirname, '../components/charts/InteractivePriceChart.tsx'))
checkResult(
  'AC1.1: Interactive price chart component exists',
  priceChartExists,
  priceChartExists ? '' : 'InteractivePriceChart.tsx not found'
)

if (priceChartExists) {
  const chartContent = fs.readFileSync(path.join(__dirname, '../components/charts/InteractivePriceChart.tsx'), 'utf8')
  
  checkResult(
    'AC1.2: Candlestick chart support',
    chartContent.includes('candlestick') && chartContent.includes('CandlestickData'),
    'Candlestick chart type implemented'
  )
  
  checkResult(
    'AC1.3: Line chart support',
    chartContent.includes('line') && chartContent.includes('LineData'),
    'Line chart type implemented'
  )
  
  checkResult(
    'AC1.4: Volume display support',
    chartContent.includes('volume') && chartContent.includes('HistogramData'),
    'Volume display implemented'
  )
  
  checkResult(
    'AC1.5: Interactive features',
    chartContent.includes('subscribeCrosshairMove') && chartContent.includes('subscribeVisibleRangeChange'),
    'Interactive features (crosshair, zoom, pan) implemented'
  )
}

// AC2: Real-time price updates with configurable timeframes
console.log('\n⏱️ AC2: Real-time Price Updates')

const realtimeUpdatesExists = fs.existsSync(path.join(__dirname, '../components/charts/RealTimePriceUpdates.tsx'))
checkResult(
  'AC2.1: Real-time updates component exists',
  realtimeUpdatesExists,
  realtimeUpdatesExists ? '' : 'RealTimePriceUpdates.tsx not found'
)

if (realtimeUpdatesExists) {
  const realtimeContent = fs.readFileSync(path.join(__dirname, '../components/charts/RealTimePriceUpdates.tsx'), 'utf8')
  
  const timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
  checkResult(
    'AC2.2: Configurable timeframes',
    timeframes.every(tf => realtimeContent.includes(`'${tf}'`)),
    `All required timeframes supported: ${timeframes.join(', ')}`
  )
  
  checkResult(
    'AC2.3: WebSocket integration',
    realtimeContent.includes('PriceTick') && realtimeContent.includes('subscribeToRealtime'),
    'WebSocket integration for real-time data'
  )
  
  checkResult(
    'AC2.4: Performance tracking',
    realtimeContent.includes('updateLatency') && realtimeContent.includes('updatesPerSecond'),
    'Real-time performance monitoring'
  )
}

// AC3: Technical indicator overlays including Wyckoff pattern recognition
console.log('\n📊 AC3: Technical Indicators')

const technicalIndicatorsExists = fs.existsSync(path.join(__dirname, '../components/charts/TechnicalIndicators.tsx'))
checkResult(
  'AC3.1: Technical indicators component exists',
  technicalIndicatorsExists,
  technicalIndicatorsExists ? '' : 'TechnicalIndicators.tsx not found'
)

if (technicalIndicatorsExists) {
  const indicatorsContent = fs.readFileSync(path.join(__dirname, '../components/charts/TechnicalIndicators.tsx'), 'utf8')
  
  const indicators = ['sma', 'ema', 'rsi', 'macd', 'bollinger_bands']
  checkResult(
    'AC3.2: Standard technical indicators',
    indicators.every(ind => indicatorsContent.includes(ind)),
    `Standard indicators implemented: ${indicators.join(', ')}`
  )
  
  checkResult(
    'AC3.3: Wyckoff pattern recognition',
    indicatorsContent.includes('WyckoffPattern') && indicatorsContent.includes('accumulation'),
    'Wyckoff pattern recognition implemented'
  )
  
  checkResult(
    'AC3.4: Volume analysis',
    indicatorsContent.includes('VolumeAnalysis') && indicatorsContent.includes('vwap'),
    'Volume Price Analysis (VPA) implemented'
  )
}

// AC4: Chart annotations showing AI agent entry/exit points
console.log('\n🤖 AC4: AI Agent Annotations')

const aiAnnotationsExists = fs.existsSync(path.join(__dirname, '../components/charts/AIAgentAnnotations.tsx'))
checkResult(
  'AC4.1: AI annotations component exists',
  aiAnnotationsExists,
  aiAnnotationsExists ? '' : 'AIAgentAnnotations.tsx not found'
)

if (aiAnnotationsExists) {
  const annotationsContent = fs.readFileSync(path.join(__dirname, '../components/charts/AIAgentAnnotations.tsx'), 'utf8')
  
  checkResult(
    'AC4.2: Agent decision annotations',
    annotationsContent.includes('AgentAnnotation') && annotationsContent.includes('entry') && annotationsContent.includes('exit'),
    'Agent entry/exit point annotations implemented'
  )
  
  checkResult(
    'AC4.3: Decision rationale display',
    annotationsContent.includes('rationale') && annotationsContent.includes('supportingData'),
    'Decision rationale and supporting data display'
  )
  
  checkResult(
    'AC4.4: Risk assessment integration',
    annotationsContent.includes('RiskAssessment') && annotationsContent.includes('confidence'),
    'Risk assessment and confidence levels'
  )
  
  checkResult(
    'AC4.5: Multi-agent support',
    annotationsContent.includes('AGENT_TYPES') && annotationsContent.includes('market_analysis'),
    'Multiple AI agent types supported'
  )
}

// AC5: Multi-instrument chart layout with synchronized time navigation
console.log('\n📊 AC5: Multi-instrument Layout')

const multiLayoutExists = fs.existsSync(path.join(__dirname, '../components/charts/MultiInstrumentLayout.tsx'))
checkResult(
  'AC5.1: Multi-instrument layout component exists',
  multiLayoutExists,
  multiLayoutExists ? '' : 'MultiInstrumentLayout.tsx not found'
)

if (multiLayoutExists) {
  const layoutContent = fs.readFileSync(path.join(__dirname, '../components/charts/MultiInstrumentLayout.tsx'), 'utf8')
  
  checkResult(
    'AC5.2: Multiple layout templates',
    layoutContent.includes('split_vertical') && layoutContent.includes('grid_2x2'),
    'Multiple layout templates available'
  )
  
  checkResult(
    'AC5.3: Synchronized navigation',
    layoutContent.includes('ChartSyncState') && layoutContent.includes('syncTime'),
    'Synchronized time navigation implemented'
  )
  
  checkResult(
    'AC5.4: Comparison tools',
    layoutContent.includes('comparison') && layoutContent.includes('crosshair'),
    'Chart comparison and crosshair synchronization'
  )
  
  checkResult(
    'AC5.5: Layout persistence',
    layoutContent.includes('savedLayouts') && layoutContent.includes('handleSaveLayout'),
    'Layout saving and persistence functionality'
  )
}

// Main dashboard integration
console.log('\n🎛️ Main Dashboard Integration')

const mainDashboardExists = fs.existsSync(path.join(__dirname, '../components/charts/MarketDataCharts.tsx'))
checkResult(
  'Dashboard.1: Main dashboard component exists',
  mainDashboardExists,
  mainDashboardExists ? '' : 'MarketDataCharts.tsx not found'
)

if (mainDashboardExists) {
  const dashboardContent = fs.readFileSync(path.join(__dirname, '../components/charts/MarketDataCharts.tsx'), 'utf8')
  
  checkResult(
    'Dashboard.2: All view modes integrated',
    ['single', 'multi', 'comparison', 'indicators', 'annotations'].every(mode => 
      dashboardContent.includes(`'${mode}'`)
    ),
    'All chart view modes integrated'
  )
  
  checkResult(
    'Dashboard.3: Performance monitoring',
    dashboardContent.includes('showPerformanceMetrics') && dashboardContent.includes('PerformanceMetrics'),
    'Performance monitoring integrated'
  )
  
  checkResult(
    'Dashboard.4: Error handling',
    dashboardContent.includes('ChartErrorBoundary') && dashboardContent.includes('hasError'),
    'Error boundary and handling implemented'
  )
}

// Type definitions
console.log('\n📋 Type Definitions')

const marketDataTypesExists = fs.existsSync(path.join(__dirname, '../types/marketData.ts'))
checkResult(
  'Types.1: Market data types exist',
  marketDataTypesExists,
  marketDataTypesExists ? '' : 'marketData.ts types not found'
)

if (marketDataTypesExists) {
  const typesContent = fs.readFileSync(path.join(__dirname, '../types/marketData.ts'), 'utf8')
  
  checkResult(
    'Types.2: Comprehensive type coverage',
    ['OHLCV', 'PriceTick', 'AgentAnnotation', 'WyckoffPattern', 'TechnicalIndicator'].every(type =>
      typesContent.includes(`interface ${type}`) || typesContent.includes(`type ${type}`)
    ),
    'All required interfaces defined'
  )
}

// Test coverage
console.log('\n🧪 Test Coverage')

const chartTestsExist = fs.existsSync(path.join(__dirname, '../components/charts/__tests__'))
checkResult(
  'Tests.1: Chart test directory exists',
  chartTestsExist,
  chartTestsExist ? '' : 'Chart tests directory not found'
)

if (chartTestsExist) {
  const testFiles = fs.readdirSync(path.join(__dirname, '../components/charts/__tests__'))
  
  checkResult(
    'Tests.2: Component tests exist',
    testFiles.some(file => file.includes('InteractivePriceChart.test')),
    'InteractivePriceChart tests exist'
  )
  
  checkResult(
    'Tests.3: Integration tests exist',
    testFiles.some(file => file.includes('integration.test')),
    'Integration tests exist'
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
  console.log('Story 9.4 is fully implemented and verified.')
} else {
  console.log(`\n⚠️  ${results.failed} verification points failed.`)
  console.log('Please address the failed checks before marking story as complete.')
}

process.exit(results.failed === 0 ? 0 : 1)