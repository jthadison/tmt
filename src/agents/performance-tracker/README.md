# Performance Tracker Agent

Real-time performance tracking and analytics system for trading accounts with comprehensive P&L monitoring, metrics calculation, and reporting capabilities.

## Features

- **Real-time P&L Tracking**: Live unrealized and realized P&L calculations
- **Performance Metrics**: Win rate, profit factor, Sharpe ratio, maximum drawdown
- **Account Comparison**: Ranking and comparative analysis across multiple accounts  
- **Report Generation**: Daily, weekly, monthly, and custom period reports
- **Data Export**: CSV, JSON, PDF, and Excel export formats
- **Tax Reporting**: IRS Form 8949 compliant export
- **Data Retention**: Automated archival and 2-year retention policy
- **WebSocket Streaming**: Real-time dashboard updates

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone and navigate to the performance tracker
cd src/agents/performance-tracker

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f performance-tracker

# Stop services
docker-compose down
```

### Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost:5432/trading_db"
export REDIS_URL="redis://localhost:6379/0"

# Run database migrations
alembic upgrade head

# Start the application
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Documentation

Once running, access the interactive API documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

#### P&L Tracking
- `GET /api/v1/performance/pnl/{account_id}` - Real-time P&L snapshot
- `GET /api/v1/performance/metrics/{account_id}` - Performance metrics

#### Reports
- `POST /api/v1/performance/report` - Generate performance reports
- `GET /api/v1/performance/history/{account_id}` - Historical data

#### Account Comparison
- `POST /api/v1/performance/compare` - Compare account performance
- `GET /api/v1/performance/compare/best-worst` - Best/worst performers
- `GET /api/v1/performance/heatmap` - Performance heatmap data

#### Data Export
- `POST /api/v1/performance/export` - Export data in various formats

#### Data Management
- `POST /api/v1/performance/retention/apply` - Apply retention policies
- `POST /api/v1/performance/retention/backup` - Create backups
- `GET /api/v1/performance/retention/integrity` - Verify data integrity

## WebSocket Streaming

Connect to real-time performance updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'pnl_update') {
        // Handle P&L updates
        console.log(data.data);
    }
};
```

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/trading_db

# Redis (for caching and background tasks)
REDIS_URL=redis://localhost:6379/0

# Application
LOG_LEVEL=info
ENVIRONMENT=production
PORT=8000

# Market Data (optional)
MARKET_DATA_PROVIDER=mt5
MT5_SERVER=broker.server.com
MT5_LOGIN=12345
MT5_PASSWORD=password
```

### Docker Environment

```yaml
# docker-compose.override.yml
version: '3.8'
services:
  performance-tracker:
    environment:
      - LOG_LEVEL=debug
      - ENVIRONMENT=development
```

## Database Schema

The system uses PostgreSQL with TimescaleDB for time-series data:

### Core Tables
- `trade_performance` - Individual trade records
- `performance_metrics` - Calculated metrics by period
- `performance_snapshots` - Real-time P&L snapshots
- `account_rankings` - Performance rankings

### Key Features
- Automatic partitioning by time
- Optimized indexes for queries
- Data retention policies
- Backup and archival systems

## Development

### Running Tests

```bash
# Install test dependencies
pip install -e .[test]

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest tests/test_metrics_calculator.py
pytest tests/test_integration.py
```

### Code Quality

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Lint code
flake8 app/ tests/

# Type checking
mypy app/
```

## Monitoring

### Health Checks

```bash
# Application health
curl http://localhost:8000/health

# Container health (if using Docker)
docker-compose ps
```

### Metrics & Logging

The application provides:
- Structured logging with request IDs
- Prometheus metrics (when enabled)
- Performance monitoring
- Error tracking

Access monitoring (with monitoring profile):
```bash
docker-compose --profile monitoring up -d

# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

## Performance Considerations

### Database Optimization
- Use connection pooling
- Regular VACUUM and ANALYZE
- Monitor slow queries
- Implement read replicas for reporting

### Caching Strategy
- Redis for frequently accessed data
- Application-level caching
- Query result caching
- WebSocket connection management

### Scaling
- Horizontal scaling with load balancers
- Separate read/write workloads
- Background task processing
- Database partitioning

## Security

### Best Practices
- API authentication and authorization
- Database connection encryption
- Input validation and sanitization
- Rate limiting
- CORS configuration

### Data Protection
- Sensitive data encryption at rest
- Secure backup procedures
- Access logging and auditing
- Compliance with financial regulations

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Check database connectivity
   docker-compose logs postgres
   
   # Verify connection string
   echo $DATABASE_URL
   ```

2. **High Memory Usage**
   ```bash
   # Monitor container resources
   docker stats performance-tracker-agent
   
   # Check for memory leaks
   docker-compose exec performance-tracker py-spy top --pid 1
   ```

3. **Slow Queries**
   ```sql
   -- Enable query logging in PostgreSQL
   ALTER SYSTEM SET log_statement = 'all';
   SELECT pg_reload_conf();
   ```

### Support

For issues and feature requests:
1. Check the application logs
2. Review the API documentation  
3. Run the test suite
4. Check database connectivity
5. Verify environment configuration

## Architecture

The Performance Tracker Agent follows a modular architecture:

```
app/
├── main.py              # FastAPI application & routing
├── models.py           # SQLAlchemy models & schemas
├── pnl_tracker.py      # Real-time P&L calculation
├── metrics_calculator.py  # Performance metrics
├── report_generator.py    # Report generation
├── account_comparison.py  # Account ranking & comparison
├── export_manager.py      # Data export functionality
├── data_retention.py      # Data archival & retention
└── market_data.py         # Market data integration
```

### Design Principles
- **Separation of Concerns**: Each module handles specific functionality
- **Async-First**: Built for high-concurrency workloads
- **Data Integrity**: ACID compliance and validation
- **Performance**: Optimized queries and caching
- **Observability**: Comprehensive logging and metrics