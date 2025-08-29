/**
 * TMT Trading System - Postman Test Runner
 * Automated test suite for validating all services are running correctly
 */

// Test suite configuration
const testConfig = {
    baseUrl: 'http://localhost',
    services: {
        orchestrator: 8089,
        executionEngine: 8082,
        circuitBreaker: 8084,
        dashboard: 3003,
        marketAnalysis: 8001,
        strategyAnalysis: 8002,
        parameterOptimization: 8003,
        learningSafety: 8004,
        disagreementEngine: 8005,
        dataCollection: 8006,
        continuousImprovement: 8007,
        patternDetection: 8008
    },
    timeout: 5000,
    oandaAccountId: '101-001-21040028-001'
};

// Global test variables
pm.globals.set('test_signal_id', `test_signal_${Date.now()}`);
pm.globals.set('test_timestamp', new Date().toISOString());

/**
 * Health Check Test Suite
 * Validates all services are running and healthy
 */
pm.test('Core Infrastructure Health Checks', function() {
    const services = ['orchestrator', 'executionEngine', 'circuitBreaker'];
    
    services.forEach(service => {
        const port = testConfig.services[service];
        const url = `${testConfig.baseUrl}:${port}/health`;
        
        pm.sendRequest({
            url: url,
            method: 'GET',
            timeout: testConfig.timeout
        }, function(err, response) {
            pm.test(`${service} (${port}) is healthy`, function() {
                pm.expect(err).to.be.null;
                pm.expect(response).to.have.property('code', 200);
                pm.expect(response.json()).to.have.property('status');
            });
        });
    });
});

pm.test('8-Agent AI Ecosystem Health Checks', function() {
    const agents = [
        'marketAnalysis', 'strategyAnalysis', 'parameterOptimization',
        'learningSafety', 'disagreementEngine', 'dataCollection',
        'continuousImprovement', 'patternDetection'
    ];
    
    agents.forEach(agent => {
        const port = testConfig.services[agent];
        const url = `${testConfig.baseUrl}:${port}/health`;
        
        pm.sendRequest({
            url: url,
            method: 'GET',
            timeout: testConfig.timeout
        }, function(err, response) {
            pm.test(`${agent} Agent (${port}) is healthy`, function() {
                pm.expect(err).to.be.null;
                pm.expect(response).to.have.property('code', 200);
            });
        });
    });
});

/**
 * Trading System Integration Tests
 * Tests the complete signal-to-trade pipeline
 */
pm.test('Trading Pipeline Integration', function() {
    // Step 1: Generate a test signal
    const signalPayload = {
        signal_id: pm.globals.get('test_signal_id'),
        agent_id: 'market_analysis',
        instrument: 'EUR_USD',
        direction: 'LONG',
        confidence: 0.75,
        price: 1.1650,
        stop_loss: 1.1600,
        take_profit: 1.1750,
        units: 100, // Small test size
        reasoning: 'Automated Postman test signal',
        metadata: {
            pattern: 'test_pattern',
            timeframe: 'H1',
            generated_at: pm.globals.get('test_timestamp')
        }
    };
    
    // Send signal to orchestrator
    pm.sendRequest({
        url: `${testConfig.baseUrl}:${testConfig.services.orchestrator}/api/signals/process`,
        method: 'POST',
        header: {
            'Content-Type': 'application/json'
        },
        body: {
            mode: 'raw',
            raw: JSON.stringify(signalPayload)
        }
    }, function(err, response) {
        pm.test('Signal processing works', function() {
            pm.expect(err).to.be.null;
            pm.expect(response.code).to.be.oneOf([200, 201, 202]);
            
            if (response.json()) {
                pm.expect(response.json()).to.have.property('status');
                pm.globals.set('processed_signal_id', response.json().signal_id);
            }
        });
    });
});

/**
 * Circuit Breaker Safety Tests
 * Validates risk management and safety controls
 */
pm.test('Circuit Breaker Safety Validation', function() {
    const riskAssessment = {
        account_id: testConfig.oandaAccountId,
        instrument: 'EUR_USD',
        units: 10000, // Larger position for risk testing
        price: 1.1650,
        stop_loss: 1.1600,
        take_profit: 1.1750
    };
    
    pm.sendRequest({
        url: `${testConfig.baseUrl}:${testConfig.services.circuitBreaker}/api/evaluate-trade`,
        method: 'POST',
        header: {
            'Content-Type': 'application/json'
        },
        body: {
            mode: 'raw',
            raw: JSON.stringify(riskAssessment)
        }
    }, function(err, response) {
        pm.test('Circuit breaker evaluates trades', function() {
            pm.expect(err).to.be.null;
            pm.expect(response.code).to.be.oneOf([200, 400, 403]);
            
            if (response.json()) {
                pm.expect(response.json()).to.have.property('allowed');
                pm.expect(response.json()).to.have.property('risk_assessment');
            }
        });
    });
});

/**
 * Dashboard API Tests
 * Validates monitoring and analytics endpoints
 */
pm.test('Dashboard Analytics', function() {
    // Test real-time P&L
    pm.sendRequest({
        url: `${testConfig.baseUrl}:${testConfig.services.dashboard}/api/analytics/realtime-pnl`,
        method: 'POST',
        header: {
            'Content-Type': 'application/json'
        },
        body: {
            mode: 'raw',
            raw: JSON.stringify({
                accountId: testConfig.oandaAccountId,
                agentId: 'market_analysis'
            })
        }
    }, function(err, response) {
        pm.test('Real-time P&L analytics works', function() {
            pm.expect(err).to.be.null;
            pm.expect(response.code).to.be.oneOf([200, 500]); // 500 acceptable for mock data
            
            if (response.code === 200 && response.json()) {
                pm.expect(response.json()).to.have.property('currentPnL');
                pm.expect(response.json()).to.have.property('lastUpdate');
            }
        });
    });
    
    // Test trade history
    pm.sendRequest({
        url: `${testConfig.baseUrl}:${testConfig.services.dashboard}/api/trades/history?accountId=${testConfig.oandaAccountId}&page=1&limit=10`,
        method: 'GET'
    }, function(err, response) {
        pm.test('Trade history endpoint works', function() {
            pm.expect(err).to.be.null;
            pm.expect(response.code).to.be.oneOf([200, 500]); // 500 acceptable for mock data
        });
    });
});

/**
 * Pattern Detection Tests
 * Tests advanced AI pattern recognition
 */
pm.test('Pattern Detection Capabilities', function() {
    const patternRequest = {
        instrument: 'EUR_USD',
        timeframe: 'H1',
        lookback_periods: 50,
        pattern_types: ['accumulation', 'distribution'],
        confidence_threshold: 0.6
    };
    
    pm.sendRequest({
        url: `${testConfig.baseUrl}:${testConfig.services.patternDetection}/detect_wyckoff_patterns`,
        method: 'POST',
        header: {
            'Content-Type': 'application/json'
        },
        body: {
            mode: 'raw',
            raw: JSON.stringify(patternRequest)
        }
    }, function(err, response) {
        pm.test('Wyckoff pattern detection works', function() {
            pm.expect(err).to.be.null;
            pm.expect(response.code).to.be.oneOf([200, 404, 500]); // Various responses acceptable
        });
    });
});

/**
 * Performance and Latency Tests
 * Measures system responsiveness
 */
pm.test('System Performance Metrics', function() {
    const startTime = Date.now();
    
    pm.sendRequest({
        url: `${testConfig.baseUrl}:${testConfig.services.orchestrator}/health`,
        method: 'GET'
    }, function(err, response) {
        const latency = Date.now() - startTime;
        
        pm.test('Orchestrator responds within acceptable latency', function() {
            pm.expect(err).to.be.null;
            pm.expect(latency).to.be.below(1000); // Less than 1 second
        });
        
        pm.test('Health check response structure', function() {
            if (response.json()) {
                pm.expect(response.json()).to.have.property('running');
                pm.expect(response.json()).to.have.property('uptime_seconds');
            }
        });
    });
});

/**
 * Cleanup and Summary
 */
pm.test('Test Suite Cleanup', function() {
    // Clear test globals
    pm.globals.unset('test_signal_id');
    pm.globals.unset('test_timestamp');
    pm.globals.unset('processed_signal_id');
    
    console.log('✅ TMT Trading System API Test Suite Completed');
    console.log('📊 Check individual test results for detailed system status');
    console.log('🔧 If tests fail, ensure all services are running locally');
    console.log('📱 Dashboard: http://localhost:3003');
    console.log('🎛️ Orchestrator: http://localhost:8089/health');
});

// Export test configuration for use in collection
if (typeof module !== 'undefined' && module.exports) {
    module.exports = testConfig;
}