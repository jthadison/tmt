// k6 Performance Test Script for Adaptive Trading System
// Tests critical trading system endpoints under load

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('error_rate');

// Test configuration
export let options = {
  stages: [
    { duration: '30s', target: 10 },   // Ramp up
    { duration: '1m', target: 50 },    // Stay at moderate load
    { duration: '2m', target: 100 },   // Scale to target load
    { duration: '2m', target: 100 },   // Stay at target load
    { duration: '30s', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests must be below 500ms
    http_req_failed: ['rate<0.01'],   // Error rate must be below 1%
    error_rate: ['rate<0.01'],        // Custom error rate
  },
};

// Base URL (can be overridden with environment variable)
const BASE_URL = __ENV.BASE_URL || 'http://localhost:3000';

// Test data
const testUser = {
  username: 'test_user',
  password: 'test_password_123'
};

export default function () {
  // Test 1: Dashboard Health Check
  testHealthEndpoint();
  
  // Test 2: API Endpoints (when implemented)
  // testAPIEndpoints();
  
  // Test 3: WebSocket Connections (when implemented)  
  // testWebSocketConnections();
  
  sleep(1); // Wait 1 second between iterations
}

function testHealthEndpoint() {
  const response = http.get(`${BASE_URL}/api/health`);
  
  const isSuccess = check(response, {
    'Health endpoint status is 200': (r) => r.status === 200,
    'Health endpoint response time < 200ms': (r) => r.timings.duration < 200,
    'Health endpoint returns valid JSON': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.data && body.data.status;
      } catch (e) {
        return false;
      }
    },
    'Health endpoint correlation ID present': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.correlation_id && body.correlation_id.length > 0;
      } catch (e) {
        return false;
      }
    }
  });
  
  errorRate.add(!isSuccess);
}

// Future test functions (to be implemented when services are ready)

function testAPIEndpoints() {
  // Test trading API endpoints
  // - Authentication endpoints
  // - Account management endpoints
  // - Trading signal endpoints
  // - Risk management endpoints
}

function testWebSocketConnections() {
  // Test real-time data connections
  // - Market data streams
  // - Trading notifications
  // - System status updates
}

// Setup function (runs once before all tests)
export function setup() {
  console.log('Performance test setup...');
  console.log(`Testing against: ${BASE_URL}`);
  
  // Verify services are available
  const healthCheck = http.get(`${BASE_URL}/api/health`);
  if (healthCheck.status !== 200) {
    console.error('Services not available for testing');
    throw new Error('Pre-test health check failed');
  }
  
  return { baseUrl: BASE_URL };
}

// Teardown function (runs once after all tests)
export function teardown(data) {
  console.log('Performance test teardown...');
  console.log('Test completed successfully');
}

// Handle summary
export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'performance-results.json': JSON.stringify(data),
  };
}

function textSummary(data, options = {}) {
  const indent = options.indent || '';
  const enableColors = options.enableColors || false;
  
  let summary = '\n' + indent + '✓ Performance Test Summary\n';
  summary += indent + '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n';
  
  // Request metrics
  summary += indent + 'HTTP Request Metrics:\n';
  summary += indent + `  Total Requests: ${data.metrics.http_reqs.values.count}\n`;
  summary += indent + `  Failed Requests: ${data.metrics.http_req_failed.values.rate * 100}%\n`;
  summary += indent + `  Average Duration: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms\n`;
  summary += indent + `  95th Percentile: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms\n`;
  summary += indent + `  99th Percentile: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms\n\n`;
  
  // Virtual user metrics
  summary += indent + 'Virtual User Metrics:\n';
  summary += indent + `  Peak VUs: ${data.metrics.vus_max.values.value}\n`;
  summary += indent + `  Test Duration: ${(data.state.testRunDurationMs / 1000).toFixed(1)}s\n\n`;
  
  // Threshold results
  summary += indent + 'Threshold Results:\n';
  Object.entries(data.thresholds).forEach(([threshold, result]) => {
    const status = result.ok ? '✓' : '✗';
    const color = result.ok ? '\x1b[32m' : '\x1b[31m';
    const reset = '\x1b[0m';
    
    if (enableColors) {
      summary += indent + `  ${color}${status}${reset} ${threshold}\n`;
    } else {
      summary += indent + `  ${status} ${threshold}\n`;
    }
  });
  
  summary += '\n';
  return summary;
}