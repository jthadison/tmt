# Internal API Documentation

## Overview

The TMT system uses a microservices architecture with well-defined internal APIs for communication between agents and system components. This document provides comprehensive API specifications for all internal services.

## API Architecture

### Service Communication Patterns
- **Synchronous**: REST APIs for request-response operations
- **Asynchronous**: Event-driven messaging for real-time updates
- **Streaming**: WebSocket connections for live data feeds

### Authentication & Authorization
All internal APIs use JWT-based authentication with service-to-service certificates for secure communication.

## Agent APIs

### Circuit Breaker Agent API

#### Base URL
```
http://circuit-breaker-agent:8001/api/v1
```

#### Emergency Stop Operations

**POST /emergency-stop**
```json
{
  "request": {
    "reason": "string",
    "triggered_by": "string",
    "scope": "system|account|agent",
    "target_id": "string (optional)"
  },
  "response": {
    "success": true,
    "stop_id": "uuid",
    "timestamp": "2025-01-18T10:30:00Z",
    "affected_components": ["agent1", "agent2"]
  }
}
```

**GET /emergency-stops**
```json
{
  "response": {
    "active_stops": [
      {
        "stop_id": "uuid",
        "reason": "string",
        "triggered_by": "string",
        "timestamp": "2025-01-18T10:30:00Z",
        "scope": "system",
        "status": "active|resolved"
      }
    ]
  }
}
```

**DELETE /emergency-stop/{stop_id}**
```json
{
  "request": {
    "authorized_by": "string",
    "resolution_reason": "string"
  },
  "response": {
    "success": true,
    "resolved_at": "2025-01-18T10:35:00Z"
  }
}
```

#### Risk Monitoring

**GET /risk-status**
```json
{
  "response": {
    "overall_risk_level": "low|medium|high|critical",
    "account_risks": [
      {
        "account_id": "string",
        "risk_level": "low|medium|high",
        "risk_factors": ["drawdown", "exposure"],
        "metrics": {
          "current_drawdown": 0.05,
          "daily_var": 0.02,
          "exposure_ratio": 0.3
        }
      }
    ],
    "system_health": {
      "agent_status": {
        "market_analysis": "healthy",
        "risk_management": "healthy",
        "execution_engine": "warning"
      }
    }
  }
}
```

### Market Analysis Agent API

#### Base URL
```
http://market-analysis-agent:8002/api/v1
```

#### Signal Generation

**POST /generate-signal**
```json
{
  "request": {
    "instrument": "EUR_USD",
    "timeframe": "H1",
    "market_data": {
      "price_data": [],
      "volume_data": [],
      "indicators": {}
    }
  },
  "response": {
    "signal": {
      "signal_id": "uuid",
      "instrument": "EUR_USD",
      "direction": "LONG|SHORT",
      "confidence": 0.85,
      "entry_price": 1.0850,
      "stop_loss": 1.0820,
      "take_profit": 1.0910,
      "risk_reward_ratio": 2.0,
      "timestamp": "2025-01-18T10:30:00Z",
      "analysis": {
        "wyckoff_phase": "accumulation_phase_d",
        "volume_confirmation": true,
        "order_blocks": [],
        "fair_value_gaps": []
      }
    }
  }
}
```

**GET /signals**
```json
{
  "parameters": {
    "instrument": "string (optional)",
    "date_from": "2025-01-17T00:00:00Z",
    "date_to": "2025-01-18T23:59:59Z",
    "status": "pending|executed|cancelled"
  },
  "response": {
    "signals": [
      {
        "signal_id": "uuid",
        "instrument": "EUR_USD",
        "direction": "LONG",
        "confidence": 0.85,
        "status": "executed",
        "generated_at": "2025-01-18T10:30:00Z",
        "executed_at": "2025-01-18T10:31:00Z"
      }
    ],
    "total_count": 25,
    "page": 1,
    "page_size": 20
  }
}
```

#### Market State Detection

**GET /market-state/{instrument}**
```json
{
  "response": {
    "instrument": "EUR_USD",
    "current_state": "trending|ranging|volatile|quiet",
    "trend_direction": "bullish|bearish|sideways",
    "volatility_level": "low|medium|high",
    "volume_profile": {
      "poc": 1.0850,
      "value_area_high": 1.0870,
      "value_area_low": 1.0830
    },
    "support_resistance": {
      "support_levels": [1.0800, 1.0780],
      "resistance_levels": [1.0900, 1.0920]
    },
    "updated_at": "2025-01-18T10:30:00Z"
  }
}
```

### Risk Management Agent API

#### Base URL
```
http://risk-management-agent:8003/api/v1
```

#### Position Risk Assessment

**POST /assess-position-risk**
```json
{
  "request": {
    "account_id": "string",
    "instrument": "EUR_USD",
    "direction": "LONG|SHORT",
    "size": 10000,
    "entry_price": 1.0850,
    "stop_loss": 1.0820,
    "take_profit": 1.0910
  },
  "response": {
    "risk_assessment": {
      "approved": true,
      "risk_score": 0.3,
      "risk_amount": 300.00,
      "risk_percentage": 1.5,
      "position_impact": {
        "new_exposure": 0.35,
        "correlation_impact": 0.1,
        "margin_usage": 0.25
      },
      "recommendations": [
        "Position size approved",
        "Consider tightening stop loss"
      ]
    }
  }
}
```

**GET /portfolio-risk/{account_id}**
```json
{
  "response": {
    "account_id": "string",
    "overall_risk": {
      "total_exposure": 0.45,
      "var_95": 0.025,
      "max_drawdown": 0.08,
      "sharpe_ratio": 1.2
    },
    "position_risks": [
      {
        "instrument": "EUR_USD",
        "direction": "LONG",
        "size": 10000,
        "unrealized_pnl": 150.00,
        "risk_contribution": 0.15
      }
    ],
    "correlation_matrix": {
      "EUR_USD": {
        "GBP_USD": 0.75,
        "AUD_USD": 0.65
      }
    }
  }
}
```

### Execution Engine API

#### Base URL
```
http://execution-engine:8004/api/v1
```

#### Trade Execution

**POST /execute-trade**
```json
{
  "request": {
    "signal_id": "uuid",
    "account_id": "string",
    "instrument": "EUR_USD",
    "direction": "LONG|SHORT",
    "size": 10000,
    "order_type": "market|limit|stop",
    "price": 1.0850,
    "stop_loss": 1.0820,
    "take_profit": 1.0910,
    "personality_variance": {
      "timing_delay": 2000,
      "size_variance": 0.05,
      "level_variance": 0.0002
    }
  },
  "response": {
    "execution_result": {
      "trade_id": "uuid",
      "status": "executed|pending|failed",
      "fill_price": 1.0851,
      "fill_time": "2025-01-18T10:31:15Z",
      "slippage": 0.0001,
      "commission": 2.50,
      "platform_order_id": "string"
    }
  }
}
```

**GET /trade-status/{trade_id}**
```json
{
  "response": {
    "trade_id": "uuid",
    "account_id": "string",
    "instrument": "EUR_USD",
    "status": "open|closed|cancelled",
    "entry_details": {
      "price": 1.0851,
      "time": "2025-01-18T10:31:15Z",
      "size": 10000
    },
    "current_pnl": 125.00,
    "unrealized_pnl": 125.00,
    "stop_loss": 1.0820,
    "take_profit": 1.0910
  }
}
```

#### Position Management

**PUT /modify-position/{trade_id}**
```json
{
  "request": {
    "stop_loss": 1.0830,
    "take_profit": 1.0920,
    "partial_close": {
      "size": 5000,
      "reason": "partial_profits"
    }
  },
  "response": {
    "modification_result": {
      "success": true,
      "updated_at": "2025-01-18T11:00:00Z",
      "new_stop_loss": 1.0830,
      "new_take_profit": 1.0920
    }
  }
}
```

## System APIs

### Performance Tracker API

#### Base URL
```
http://performance-tracker:8005/api/v1
```

#### Performance Metrics

**GET /performance/{account_id}**
```json
{
  "parameters": {
    "date_from": "2025-01-01T00:00:00Z",
    "date_to": "2025-01-18T23:59:59Z",
    "timeframe": "daily|weekly|monthly"
  },
  "response": {
    "account_performance": {
      "total_return": 0.125,
      "annualized_return": 0.156,
      "sharpe_ratio": 1.25,
      "max_drawdown": 0.065,
      "win_rate": 0.58,
      "profit_factor": 1.45,
      "total_trades": 245,
      "avg_trade_duration": "4h 25m"
    },
    "daily_performance": [
      {
        "date": "2025-01-18",
        "pnl": 125.50,
        "return": 0.00125,
        "trades": 3,
        "win_rate": 0.67
      }
    ]
  }
}
```

### Compliance Agent API

#### Base URL
```
http://compliance-agent:8006/api/v1
```

#### Rule Validation

**POST /validate-action**
```json
{
  "request": {
    "account_id": "string",
    "action_type": "trade_entry|trade_exit|position_modification",
    "action_details": {
      "instrument": "EUR_USD",
      "size": 10000,
      "direction": "LONG"
    }
  },
  "response": {
    "validation_result": {
      "approved": true,
      "compliance_score": 0.95,
      "violated_rules": [],
      "warnings": [
        "Approaching daily loss limit"
      ],
      "required_actions": []
    }
  }
}
```

## Data Streaming APIs

### Real-time Market Data Stream

#### WebSocket Endpoint
```
ws://market-data-stream:8080/stream
```

#### Subscription Message
```json
{
  "action": "subscribe",
  "instruments": ["EUR_USD", "GBP_USD"],
  "data_types": ["prices", "volume", "indicators"]
}
```

#### Market Data Message
```json
{
  "type": "price_update",
  "instrument": "EUR_USD",
  "timestamp": "2025-01-18T10:30:15.123Z",
  "bid": 1.0849,
  "ask": 1.0851,
  "volume": 1500
}
```

### System Event Stream

#### WebSocket Endpoint
```
ws://event-stream:8081/events
```

#### Event Message Format
```json
{
  "event_type": "signal_generated|trade_executed|risk_alert",
  "timestamp": "2025-01-18T10:30:15.123Z",
  "source": "market_analysis_agent",
  "data": {
    "signal_id": "uuid",
    "instrument": "EUR_USD",
    "confidence": 0.85
  }
}
```

## Error Handling

### Standard Error Response Format
```json
{
  "error": {
    "code": "RISK_001",
    "message": "Position size exceeds risk limits",
    "details": {
      "requested_size": 50000,
      "max_allowed_size": 25000,
      "current_exposure": 0.45
    },
    "timestamp": "2025-01-18T10:30:00Z",
    "request_id": "uuid"
  }
}
```

### Common Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| AUTH_001 | Invalid authentication token | 401 |
| AUTH_002 | Insufficient permissions | 403 |
| RISK_001 | Position size exceeds limits | 400 |
| RISK_002 | Maximum exposure exceeded | 400 |
| EXEC_001 | Trade execution failed | 500 |
| EXEC_002 | Platform connection error | 503 |
| DATA_001 | Invalid market data | 400 |
| DATA_002 | Market data unavailable | 503 |

## Rate Limiting

### Default Rate Limits
- **Authentication endpoints**: 5 requests/minute
- **Trade execution**: 100 requests/minute per account
- **Market data**: 1000 requests/minute
- **Performance queries**: 200 requests/minute

### Rate Limit Headers
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1642518000
```

## API Versioning

### Version Strategy
- **URL-based versioning**: `/api/v1/`, `/api/v2/`
- **Backward compatibility**: Maintained for 2 major versions
- **Deprecation notice**: 6 months advance notice for breaking changes

### Version Migration Guide
- v1 → v2 migration instructions available at `/docs/api-migration/v1-to-v2.md`
- Breaking changes documented with migration examples
- Automated migration tools available for common patterns

## Monitoring and Observability

### Health Check Endpoints
All services provide standardized health check endpoints:

**GET /health**
```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2025-01-18T10:30:00Z",
  "version": "1.2.3",
  "dependencies": {
    "database": "healthy",
    "message_broker": "healthy",
    "external_apis": "degraded"
  }
}
```

### Metrics Collection
- Request/response times for all endpoints
- Error rates and success rates by endpoint
- Throughput metrics (requests per second)
- Business metrics (trades executed, signals generated)

For OpenAPI specifications and interactive documentation, see the Swagger endpoints available at each service's `/docs` path.