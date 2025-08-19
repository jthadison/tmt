# Story 9.3: OANDA Account Information Display

**Epic**: Trading Operations Dashboard Implementation  
**Story ID**: 9.3  
**Priority**: High  
**Effort**: 10 points  

## User Story

As a **trading system operator**,  
I want **comprehensive OANDA account information and real-time balance updates**,  
so that **I can monitor account health, margin usage, and trading capacity across all connected accounts**.

## Acceptance Criteria

1. **AC1**: Account overview dashboard showing balance, equity, margin available, and margin used for all connected OANDA accounts
2. **AC2**: Real-time updates of account metrics with visual indicators for margin warnings and account health
3. **AC3**: Account-specific trading limits and current utilization displaying risk management status
4. **AC4**: Historical account performance charts showing balance trends and drawdown analysis
5. **AC5**: Multi-account summary view with aggregated metrics and individual account drill-down capability

## Integration Verification

- **IV1**: OANDA API integration maintains existing rate limits and does not affect current trading operations
- **IV2**: Account data display accurately reflects information used by existing trading agents
- **IV3**: Real-time balance updates synchronize correctly with actual trading activities

## Technical Notes

- Integrates with OANDA API for real-time account data
- Must respect OANDA API rate limits
- Multi-account support with aggregation capabilities
- Visual indicators for risk management (margin warnings)
- Historical data visualization for trend analysis

## Dependencies

- Story 9.1: Dashboard Infrastructure (real-time foundation)
- OANDA API access and authentication
- Existing account management system
- Chart/visualization libraries

## Definition of Done

- [ ] Account overview dashboard implemented for all connected accounts
- [ ] Real-time balance updates with visual health indicators
- [ ] Trading limits and utilization tracking
- [ ] Historical performance charts implemented
- [ ] Multi-account summary with drill-down functionality
- [ ] All integration verification points passed
- [ ] OANDA API rate limit compliance verified
- [ ] Security review for account data handling completed
- [ ] Unit and integration tests passing
- [ ] Documentation updated