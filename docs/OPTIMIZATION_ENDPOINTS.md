# Market Analysis Optimization Endpoints

## Overview

The Market Analysis service provides comprehensive optimization capabilities through dedicated endpoints. These endpoints allow for signal performance analysis, confidence threshold optimization, and system monitoring.

**Service URL:** `http://localhost:8001`

## Available Optimization Endpoints

### 1. Analysis Endpoints

#### `POST /optimization/analyze`
Analyzes current signal performance and identifies optimization opportunities.

**Request:**
```bash
curl -X POST http://localhost:8001/optimization/analyze
```

**Response:**
```json
{
  "analysis_status": "completed",
  "timestamp": "2025-09-15T15:30:00.123456",
  "analysis_result": {
    "data_summary": {
      "signals_analyzed": 30,
      "executions_analyzed": 19,
      "conversion_rate": 63.33,
      "analysis_period_days": 7,
      "win_rate": 36.84,
      "avg_pnl": 0.04
    },
    "confidence_analysis": {
      "high_confidence": {
        "count": 12,
        "avg_confidence": 82.5,
        "conversion_rate": 30.0
      },
      "medium_confidence": {
        "count": 10,
        "avg_confidence": 69.2,
        "conversion_rate": 15.0
      },
      "low_confidence": {
        "count": 8,
        "avg_confidence": 58.1,
        "conversion_rate": 5.0
      }
    },
    "optimization_opportunities": [
      "Increase confidence threshold to 72% for better conversion",
      "Focus on accumulation and spring patterns (higher win rate)",
      "Consider reducing position size for lower confidence signals"
    ]
  }
}
```

#### `POST /optimization/optimize-threshold`
Optimizes confidence threshold based on historical performance.

**Request:**
```bash
curl -X POST http://localhost:8001/optimization/optimize-threshold
```

**Response:**
```json
{
  "optimization_status": "completed",
  "timestamp": "2025-09-15T15:35:00.123456",
  "recommendation": {
    "current_threshold": 70.0,
    "recommended_threshold": 72.5,
    "expected_improvement": 8.3,
    "confidence_level": 85.0,
    "implementation_priority": "medium",
    "reasoning": "Analysis of 30 real signals shows threshold increase from 70.0% to 72.5% would improve conversion rate by 8.3% based on observed performance patterns.",
    "projected_metrics": {
      "current_conversions": 19,
      "projected_conversions": 21,
      "risk_reduction": "15.2%",
      "expected_win_rate": "68.4%"
    }
  }
}
```

### 2. Implementation Endpoints

#### `POST /optimization/implement`
Implements optimized confidence threshold.

**Request:**
```bash
curl -X POST "http://localhost:8001/optimization/implement?threshold=72.5&dry_run=false"
```

**Parameters:**
- `threshold` (float): New confidence threshold (40.0-95.0)
- `dry_run` (boolean): Test implementation without applying changes

**Response:**
```json
{
  "implementation_status": "success",
  "timestamp": "2025-09-15T15:40:00.123456",
  "changes": {
    "old_threshold": 70.0,
    "new_threshold": 72.5,
    "change_magnitude": 2.5,
    "implementation_time": "2025-09-15T15:40:00.123456",
    "affected_components": [
      "signal_generator",
      "confidence_evaluator",
      "execution_filter"
    ],
    "rollback_available": true,
    "monitoring_enabled": true
  },
  "monitoring_recommendation": "Monitor performance for 24-48 hours"
}
```

### 3. Monitoring Endpoints

#### `GET /optimization/monitor?hours=24`
Monitors optimization performance.

**Request:**
```bash
curl "http://localhost:8001/optimization/monitor?hours=24"
```

**Response:**
```json
{
  "monitoring_status": "completed",
  "timestamp": "2025-09-15T16:00:00.123456",
  "monitoring_result": {
    "monitoring_period_hours": 24,
    "performance_metrics": {
      "signals_generated": 20,
      "signals_executed": 5,
      "conversion_rate": 25.0,
      "win_rate": 60.0,
      "avg_pnl": 12.5
    },
    "trend_analysis": {
      "conversion_trend": "stable",
      "performance_trend": "improving",
      "threshold_effectiveness": "good"
    },
    "recommendations": [
      "Continue monitoring for another 24 hours",
      "Performance metrics within expected range",
      "No immediate adjustments needed"
    ],
    "alerts": []
  }
}
```

### 4. Status and Reporting Endpoints

#### `GET /optimization/status`
Gets current optimization status and configuration.

**Request:**
```bash
curl http://localhost:8001/optimization/status
```

**Response:**
```json
{
  "optimization_capabilities": {
    "signal_quality_analyzer": true,
    "threshold_optimizer": true,
    "enhanced_detector": true,
    "quality_monitor": true
  },
  "current_configuration": {
    "confidence_threshold": 72.5,
    "optimization_active": true,
    "monitoring_enabled": true,
    "auto_adjustment": false
  },
  "current_performance": {
    "signals_today": 228,
    "conversion_rate": 25.0,
    "win_rate": 60.0,
    "analysis_period_days": 7,
    "total_signals": 30,
    "total_executions": 19
  },
  "optimization_history": [
    {
      "timestamp": "2025-09-13T15:40:00.123456",
      "old_threshold": 68.0,
      "new_threshold": 70.0,
      "improvement": 5.2,
      "status": "successful"
    }
  ]
}
```

#### `GET /optimization/report`
Gets comprehensive optimization report with detailed analysis.

**Request:**
```bash
curl http://localhost:8001/optimization/report
```

**Response:**
```json
{
  "report_status": "completed",
  "timestamp": "2025-09-15T16:10:00.123456",
  "optimization_report": {
    "report_period": {
      "start_date": "2025-09-08T16:10:00.123456",
      "end_date": "2025-09-15T16:10:00.123456",
      "total_days": 7
    },
    "signal_performance": {
      "total_signals": 30,
      "executed_signals": 19,
      "conversion_rate": 63.33,
      "avg_confidence": 57.38
    },
    "execution_performance": {
      "total_pnl": 0.04,
      "avg_pnl_per_trade": 0.002,
      "profitable_trades": 7,
      "win_rate": 36.84
    },
    "optimization_recommendations": {
      "primary_recommendation": "Increase confidence threshold to 72.5% for improved conversion quality",
      "secondary_recommendations": [
        "Focus on accumulation and spring patterns",
        "Implement dynamic position sizing based on confidence",
        "Add volatility filter for better entry timing"
      ],
      "expected_improvements": {
        "conversion_rate_improvement": "8.3%",
        "win_rate_improvement": "4.7%",
        "risk_reduction": "12.5%"
      }
    },
    "pattern_analysis": {
      "most_profitable": "wyckoff_spring",
      "least_profitable": "vpa_confirmation",
      "pattern_distribution": {
        "accumulation": 25,
        "spring": 18,
        "markup": 22,
        "distribution": 15
      }
    }
  }
}
```

## Usage Examples

### Python Integration

```python
import aiohttp
import asyncio

class MarketAnalysisOptimizer:
    def __init__(self):
        self.base_url = "http://localhost:8001"

    async def analyze_performance(self):
        """Get current signal performance analysis"""
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/optimization/analyze") as response:
                return await response.json()

    async def optimize_threshold(self):
        """Get threshold optimization recommendation"""
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/optimization/optimize-threshold") as response:
                return await response.json()

    async def implement_threshold(self, threshold: float, dry_run: bool = False):
        """Implement new confidence threshold"""
        params = {"threshold": threshold, "dry_run": dry_run}
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/optimization/implement", params=params) as response:
                return await response.json()

    async def get_comprehensive_report(self):
        """Get detailed optimization report"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/optimization/report") as response:
                return await response.json()

# Usage example
async def main():
    optimizer = MarketAnalysisOptimizer()

    # 1. Analyze current performance
    analysis = await optimizer.analyze_performance()
    print(f"Current conversion rate: {analysis['analysis_result']['data_summary']['conversion_rate']}%")

    # 2. Get optimization recommendation
    recommendation = await optimizer.optimize_threshold()
    new_threshold = recommendation['recommendation']['recommended_threshold']
    print(f"Recommended threshold: {new_threshold}%")

    # 3. Test implementation (dry run)
    test_result = await optimizer.implement_threshold(new_threshold, dry_run=True)
    print(f"Dry run status: {test_result['implementation_status']}")

    # 4. Get comprehensive report
    report = await optimizer.get_comprehensive_report()
    signal_perf = report['optimization_report']['signal_performance']
    print(f"Total signals analyzed: {signal_perf['total_signals']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Shell Script Integration

```bash
#!/bin/bash
# optimization_workflow.sh

BASE_URL="http://localhost:8001"

echo "Starting optimization workflow..."

# 1. Analyze current performance
echo "Analyzing current performance..."
curl -s -X POST "$BASE_URL/optimization/analyze" | python -m json.tool > analysis.json
CONVERSION_RATE=$(python -c "import json; print(json.load(open('analysis.json'))['analysis_result']['data_summary']['conversion_rate'])")
echo "Current conversion rate: $CONVERSION_RATE%"

# 2. Get threshold recommendation
echo "Getting threshold recommendation..."
curl -s -X POST "$BASE_URL/optimization/optimize-threshold" | python -m json.tool > recommendation.json
NEW_THRESHOLD=$(python -c "import json; print(json.load(open('recommendation.json'))['recommendation']['recommended_threshold'])")
echo "Recommended threshold: $NEW_THRESHOLD%"

# 3. Test implementation
echo "Testing implementation (dry run)..."
curl -s -X POST "$BASE_URL/optimization/implement?threshold=$NEW_THRESHOLD&dry_run=true" | python -m json.tool > test_result.json
STATUS=$(python -c "import json; print(json.load(open('test_result.json'))['implementation_status'])")
echo "Test status: $STATUS"

# 4. Get comprehensive report
echo "Generating comprehensive report..."
curl -s "$BASE_URL/optimization/report" | python -m json.tool > optimization_report.json
echo "Report saved to optimization_report.json"

echo "Optimization workflow completed!"
```

## Error Handling

### Common Error Responses

#### Service Unavailable
```json
{
  "optimization_capabilities": {
    "signal_quality_analyzer": false,
    "threshold_optimizer": false,
    "enhanced_detector": false,
    "quality_monitor": false
  },
  "error": "Service initialization failed",
  "timestamp": "2025-09-15T16:15:00.123456"
}
```

#### Invalid Threshold Parameter
```json
{
  "implementation_status": "error",
  "timestamp": "2025-09-15T16:16:00.123456",
  "error": "Threshold must be between 40.0 and 95.0"
}
```

### Error Handling Best Practices

```python
async def safe_optimization_call(endpoint: str, **params):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"http://localhost:8001{endpoint}", params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_data = await response.json()
                    logger.error(f"Optimization API error: {error_data.get('error', 'Unknown error')}")
                    return None
    except aiohttp.ClientError as e:
        logger.error(f"Connection error to optimization service: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in optimization call: {e}")
        return None
```

## Data Sources

The optimization endpoints analyze data from multiple sources:

1. **Real Signal Data:** From signal generation logs and cache files
2. **OANDA Trade History:** Actual trade execution results
3. **Market Analysis Metrics:** Live performance tracking
4. **Optimization History:** Previous optimization attempts and results

## Performance Considerations

- **Analysis Duration:** Full analysis takes 1-3 seconds
- **Data Volume:** Analyzes up to 500 recent trades and signals
- **Caching:** Results are cached for 5-10 minutes to improve performance
- **Concurrent Requests:** Service handles up to 10 concurrent optimization requests

## Integration with External Systems

### With Optimization Script
```python
# Use endpoints instead of trying to fetch raw signal data
report = await session.get("http://localhost:8001/optimization/report")
analysis = await session.post("http://localhost:8001/optimization/analyze")
```

### With Dashboard
```typescript
// Fetch optimization status for dashboard display
const optimizationStatus = await fetch('/api/optimization/status');
const report = await fetch('/api/optimization/report');
```

### With Monitoring Systems
```python
# Health check for monitoring
async def check_optimization_health():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8001/optimization/status") as response:
                if response.status == 200:
                    data = await response.json()
                    return data['optimization_capabilities']
    except:
        return {"all_services": False}
```

---

**Last Updated:** September 15, 2025
**Service Version:** Market Analysis Agent v1.0.0
**Port:** 8001