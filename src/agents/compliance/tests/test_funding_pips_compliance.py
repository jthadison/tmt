"""
Comprehensive tests for Funding Pips compliance implementation.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.agents.compliance.app.funding_pips import (
    FundingPipsCompliance, 
    FundingPipsWarningLevel,
    FundingPipsConfig
)
from src.agents.compliance.app.daily_loss_tracker import DailyLossTracker
from src.agents.compliance.app.static_drawdown_monitor import StaticDrawdownMonitor
from src.agents.compliance.app.stop_loss_enforcer import MandatoryStopLossEnforcer
from src.agents.compliance.app.weekend_closure import WeekendClosureAutomation
from src.agents.compliance.app.minimum_hold_time import MinimumHoldTimeEnforcer
from src.agents.compliance.app.models import Account, Trade, Position


@pytest.fixture
def mock_account():
    """Create mock trading account for testing."""
    return Account(
        account_id="TEST_ACCOUNT_001",
        prop_firm="Funding Pips",
        balance=Decimal('100000.00'),
        initial_balance=Decimal('100000.00'),
        daily_pnl=Decimal('0.00'),
        unrealized_pnl=Decimal('0.00'),
        daily_trades_count=0
    )


@pytest.fixture
def mock_trade():
    """Create mock trade for testing."""
    return Trade(
        symbol="EURUSD",
        direction="buy",
        entry_price=Decimal('1.0950'),
        position_size=Decimal('0.1'),
        stop_loss=Decimal('1.0930'),
        take_profit=Decimal('1.0970')
    )


@pytest.fixture
def mock_position():
    """Create mock position for testing."""
    return Position(
        position_id="POS_001",
        account_id="TEST_ACCOUNT_001",
        symbol="EURUSD",
        direction="buy",
        size=Decimal('0.1'),
        entry_price=Decimal('1.0950'),
        stop_loss=Decimal('1.0930'),
        open_time=datetime.utcnow(),
        unrealized_pnl=Decimal('0.00')
    )


class TestFundingPipsCompliance:
    """Test Funding Pips compliance engine."""
    
    def test_initialization(self):
        """Test compliance engine initialization."""
        compliance = FundingPipsCompliance()
        
        assert compliance.config.prop_firm == "Funding Pips"
        assert compliance.config.risk_management["daily_loss_limit"] == 0.04
        assert compliance.config.risk_management["max_drawdown"] == 0.08
    
    def test_validate_trade_with_valid_trade(self, mock_account, mock_trade):
        """Test trade validation with compliant trade."""
        compliance = FundingPipsCompliance()
        
        result = compliance.validate_trade(mock_account, mock_trade)
        
        assert result.approved is True
        assert len(result.violations) == 0
    
    def test_validate_trade_missing_stop_loss(self, mock_account, mock_trade):
        """Test trade validation with missing stop loss."""
        compliance = FundingPipsCompliance()
        mock_trade.stop_loss = None
        
        result = compliance.validate_trade(mock_account, mock_trade)
        
        assert result.approved is False
        assert any("stop loss" in v["message"].lower() for v in result.violations)
    
    def test_validate_trade_excessive_risk(self, mock_account, mock_trade):
        """Test trade validation with excessive risk."""
        compliance = FundingPipsCompliance()
        
        # Set stop loss too far (more than 2% risk)
        mock_trade.stop_loss = Decimal('1.0500')  # Very wide stop loss
        
        result = compliance.validate_trade(mock_account, mock_trade)
        
        assert result.approved is False
        assert any("risk" in v["message"].lower() for v in result.violations)
    
    def test_static_drawdown_calculation(self, mock_account):
        """Test static drawdown calculation."""
        compliance = FundingPipsCompliance()
        
        # Simulate loss
        mock_account.balance = Decimal('95000.00')
        mock_account.unrealized_pnl = Decimal('-1000.00')
        
        # Should be 6% drawdown: (100000 - 94000) / 100000
        drawdown_exceeded = compliance._check_static_drawdown(mock_account)
        
        assert drawdown_exceeded is False  # 6% is below 8% limit
        
        # Test with excessive drawdown
        mock_account.balance = Decimal('90000.00')
        mock_account.unrealized_pnl = Decimal('-2000.00')  # Total equity: 88000
        
        drawdown_exceeded = compliance._check_static_drawdown(mock_account)
        assert drawdown_exceeded is True  # 12% exceeds 8% limit
    
    def test_daily_loss_warning_levels(self, mock_account, mock_trade):
        """Test daily loss warning level detection."""
        compliance = FundingPipsCompliance()
        
        # Test at 80% warning level (3.2% of 100k = 3200)
        mock_account.daily_pnl = Decimal('-3200.00')
        
        violation, message, severity = compliance._check_daily_loss(mock_account, mock_trade)
        assert violation is True
        assert severity == "info"
        assert "80%" in message
        
        # Test at 95% warning level (3.8% of 100k = 3800)
        mock_account.daily_pnl = Decimal('-3800.00')
        
        violation, message, severity = compliance._check_daily_loss(mock_account, mock_trade)
        assert violation is True
        assert severity == "warning"
        assert "95%" in message
    
    def test_dashboard_data_generation(self, mock_account):
        """Test compliance dashboard data generation."""
        compliance = FundingPipsCompliance()
        
        dashboard_data = compliance.get_compliance_dashboard_data(mock_account)
        
        assert dashboard_data["prop_firm"] == "Funding Pips"
        assert "daily_loss" in dashboard_data
        assert "drawdown" in dashboard_data
        assert "rules" in dashboard_data
        assert "compliance_score" in dashboard_data
        
        # Check daily loss data structure
        daily_loss = dashboard_data["daily_loss"]
        assert "current" in daily_loss
        assert "limit" in daily_loss
        assert "status" in daily_loss
    
    def test_compliance_score_calculation(self, mock_account):
        """Test compliance score calculation."""
        compliance = FundingPipsCompliance()
        
        # Good account should have high score
        score = compliance._calculate_compliance_score(mock_account)
        assert score >= 90
        
        # Account with losses should have lower score
        mock_account.daily_pnl = Decimal('-3500.00')  # 3.5% daily loss
        score = compliance._calculate_compliance_score(mock_account)
        assert score < 90


class TestDailyLossTracker:
    """Test daily loss tracking system."""
    
    def test_initialization(self):
        """Test daily loss tracker initialization."""
        tracker = DailyLossTracker()
        
        assert tracker.daily_limit == Decimal('0.04')
        assert FundingPipsWarningLevel.LEVEL_80 in tracker.warning_levels
    
    @pytest.mark.asyncio
    async def test_daily_pnl_update_profit(self, mock_account):
        """Test daily P&L update with profit."""
        tracker = DailyLossTracker()
        
        # Update with profit
        alert = await tracker.update_daily_pnl(mock_account, Decimal('500.00'))
        
        assert alert is None  # No alert for profit
        assert mock_account.daily_pnl == Decimal('500.00')
    
    @pytest.mark.asyncio
    async def test_daily_pnl_update_warning_levels(self, mock_account):
        """Test daily P&L update with warning levels."""
        tracker = DailyLossTracker()
        
        # Update with 80% warning level loss
        warning_loss = Decimal('-3200.00')  # 3.2% of 100k
        alert = await tracker.update_daily_pnl(mock_account, warning_loss)
        
        assert alert is not None
        assert alert.warning_level == FundingPipsWarningLevel.LEVEL_80
        assert alert.requires_action is False
        
        # Update with critical level loss
        mock_account.daily_pnl = Decimal('0.00')  # Reset
        critical_loss = Decimal('-4000.00')  # 4% of 100k
        alert = await tracker.update_daily_pnl(mock_account, critical_loss)
        
        assert alert.warning_level == FundingPipsWarningLevel.CRITICAL
        assert alert.requires_action is True
    
    def test_can_trade_blocked_account(self, mock_account):
        """Test trading permission for blocked account."""
        tracker = DailyLossTracker()
        
        # Block account
        tracker.blocked_accounts.add(mock_account.account_id)
        
        can_trade, reason = tracker.can_trade(mock_account.account_id)
        
        assert can_trade is False
        assert "blocked" in reason.lower()
    
    def test_emergency_override(self, mock_account):
        """Test emergency trading override."""
        tracker = DailyLossTracker()
        
        # Block account first
        tracker.blocked_accounts.add(mock_account.account_id)
        
        # Create emergency override
        override_data = tracker.create_emergency_override(
            mock_account.account_id,
            "Market volatility emergency",
            duration_minutes=30
        )
        
        assert override_data["account_id"] == mock_account.account_id
        assert override_data["reason"] == "Market volatility emergency"
        
        # Should be able to trade now
        can_trade, reason = tracker.can_trade(mock_account.account_id)
        assert can_trade is True


class TestStaticDrawdownMonitor:
    """Test static drawdown monitoring system."""
    
    def test_initialization(self):
        """Test drawdown monitor initialization."""
        monitor = StaticDrawdownMonitor()
        
        assert monitor.max_drawdown == Decimal('0.08')
        assert len(monitor.warning_thresholds) == 3
    
    @pytest.mark.asyncio
    async def test_drawdown_monitoring_safe_account(self, mock_account):
        """Test drawdown monitoring with safe account."""
        monitor = StaticDrawdownMonitor()
        
        alert = await monitor.monitor_drawdown(mock_account)
        
        assert alert is None  # No alert for safe account
    
    @pytest.mark.asyncio
    async def test_drawdown_monitoring_warning_levels(self, mock_account):
        """Test drawdown monitoring with warning levels."""
        monitor = StaticDrawdownMonitor()
        
        # Set account to warning level (6.5% drawdown)
        mock_account.balance = Decimal('93500.00')
        
        alert = await monitor.monitor_drawdown(mock_account)
        
        assert alert is not None
        assert alert.severity.value == "warning"
        assert alert.drawdown_percentage == 6.5
    
    @pytest.mark.asyncio
    async def test_drawdown_monitoring_violation(self, mock_account):
        """Test drawdown monitoring with violation."""
        monitor = StaticDrawdownMonitor()
        
        # Set account to violation level (9% drawdown)
        mock_account.balance = Decimal('91000.00')
        
        alert = await monitor.monitor_drawdown(mock_account)
        
        assert alert.severity.value == "violation"
        assert alert.requires_immediate_action is True
        assert mock_account.account_id in monitor.blocked_accounts
    
    def test_trade_validation_blocked_account(self, mock_account, mock_trade):
        """Test trade validation for blocked account."""
        monitor = StaticDrawdownMonitor()
        
        # Block account
        monitor.blocked_accounts.add(mock_account.account_id)
        
        allowed, reason = monitor.validate_trade_impact(mock_account, mock_trade)
        
        assert allowed is False
        assert "blocked" in reason.lower()
    
    def test_recovery_metrics_calculation(self, mock_account):
        """Test recovery metrics calculation."""
        monitor = StaticDrawdownMonitor()
        
        # Set account with 5% drawdown
        mock_account.balance = Decimal('95000.00')
        
        recovery_metrics = monitor.get_recovery_metrics(mock_account)
        
        assert recovery_metrics["current_drawdown_pct"] == 5.0
        assert recovery_metrics["recovery_needed_amount"] == 5000.0
        assert recovery_metrics["break_even_target"] == 100000.0


class TestMandatoryStopLossEnforcer:
    """Test mandatory stop-loss enforcement."""
    
    def test_initialization(self):
        """Test stop-loss enforcer initialization."""
        enforcer = MandatoryStopLossEnforcer()
        
        assert enforcer.config.max_risk_per_trade == Decimal('0.02')
        assert enforcer.config.auto_calculate is True
    
    def test_validate_trade_with_stop_loss(self, mock_account, mock_trade):
        """Test trade validation with proper stop loss."""
        enforcer = MandatoryStopLossEnforcer()
        
        result = enforcer.validate_trade_stop_loss(mock_account, mock_trade)
        
        assert result.valid is True
        assert result.risk_percentage < 2.0
    
    def test_validate_trade_missing_stop_loss(self, mock_account, mock_trade):
        """Test trade validation with missing stop loss."""
        enforcer = MandatoryStopLossEnforcer()
        mock_trade.stop_loss = None
        
        result = enforcer.validate_trade_stop_loss(mock_account, mock_trade)
        
        assert result.valid is False
        assert result.calculated_sl is not None
        assert result.recommended_sl is not None
    
    def test_optimal_stop_loss_calculation(self, mock_account, mock_trade):
        """Test optimal stop loss calculation."""
        enforcer = MandatoryStopLossEnforcer()
        
        optimal_sl = enforcer._calculate_optimal_stop_loss(mock_account, mock_trade)
        
        # Should be calculated based on 2% risk
        expected_risk = mock_account.balance * Decimal('0.02')  # 2000
        price_distance = expected_risk / mock_trade.position_size  # 2000 / 0.1 = 20000 pips
        expected_sl = mock_trade.entry_price - (price_distance / 10000)  # Convert to price
        
        assert abs(optimal_sl - expected_sl) < Decimal('0.0001')
    
    def test_position_stop_loss_addition(self, mock_account, mock_position):
        """Test adding stop loss to existing position."""
        enforcer = MandatoryStopLossEnforcer()
        mock_position.stop_loss = None
        
        success, calculated_sl, error = enforcer.add_stop_loss_to_existing_position(
            mock_account, mock_position
        )
        
        assert success is True
        assert calculated_sl is not None
        assert error is None


class TestWeekendClosureAutomation:
    """Test weekend closure automation."""
    
    def test_initialization(self):
        """Test weekend closure automation initialization."""
        automation = WeekendClosureAutomation()
        
        assert automation.closure_time == "16:50"
        assert automation.grace_period_minutes == 5
    
    @pytest.mark.asyncio
    async def test_schedule_weekend_closure(self, mock_account, mock_position):
        """Test scheduling weekend closure."""
        automation = WeekendClosureAutomation()
        
        positions = [mock_position]
        closure_events = await automation.schedule_weekend_closure(mock_account, positions)
        
        assert len(closure_events) == 1
        assert closure_events[0].account_id == mock_account.account_id
        assert closure_events[0].position_id == mock_position.position_id
        assert closure_events[0].closure_reason.value == "weekend_compliance"
    
    def test_manual_override_creation(self, mock_account):
        """Test manual override creation."""
        automation = WeekendClosureAutomation()
        
        override_data = automation.create_manual_override(
            mock_account.account_id,
            "Extended trading session required",
            duration_hours=48
        )
        
        assert override_data["account_id"] == mock_account.account_id
        assert override_data["reason"] == "Extended trading session required"
        assert mock_account.account_id in automation.override_accounts
    
    def test_weekend_closure_status(self, mock_account):
        """Test weekend closure status reporting."""
        automation = WeekendClosureAutomation()
        
        status = automation.get_weekend_closure_status(mock_account.account_id)
        
        assert status["account_id"] == mock_account.account_id
        assert "next_closure_time" in status
        assert "hours_until_closure" in status
        assert status["closure_required"] is True


class TestMinimumHoldTimeEnforcer:
    """Test minimum hold time enforcement."""
    
    def test_initialization(self):
        """Test minimum hold time enforcer initialization."""
        enforcer = MinimumHoldTimeEnforcer()
        
        assert enforcer.minimum_hold_seconds == 60
    
    def test_position_tracking(self, mock_position):
        """Test position hold time tracking."""
        enforcer = MinimumHoldTimeEnforcer()
        
        enforcer.track_position_open(mock_position)
        
        assert mock_position.position_id in enforcer.position_timers
    
    def test_hold_time_compliance_check(self, mock_position):
        """Test hold time compliance checking."""
        enforcer = MinimumHoldTimeEnforcer()
        
        # New position - should not meet minimum
        mock_position.open_time = datetime.utcnow()
        enforcer.track_position_open(mock_position)
        
        compliant, violation = enforcer.check_hold_time_compliance(mock_position)
        
        assert compliant is False
        assert violation is not None
        assert violation.time_remaining > 0
        
        # Old position - should meet minimum
        mock_position.open_time = datetime.utcnow() - timedelta(minutes=2)
        enforcer.position_timers[mock_position.position_id] = mock_position.open_time
        
        compliant, violation = enforcer.check_hold_time_compliance(mock_position)
        assert compliant is True
        assert violation is None
    
    def test_closure_validation(self, mock_position):
        """Test position closure validation."""
        enforcer = MinimumHoldTimeEnforcer()
        
        # New position
        mock_position.open_time = datetime.utcnow()
        enforcer.track_position_open(mock_position)
        
        allowed, reason, seconds_remaining = enforcer.validate_closure_request(
            mock_position, "manual"
        )
        
        assert allowed is False
        assert reason is not None
        assert seconds_remaining is not None
        assert seconds_remaining <= 60
    
    def test_exemption_handling(self, mock_position):
        """Test closure exemption handling."""
        enforcer = MinimumHoldTimeEnforcer()
        
        # New position with stop loss exemption
        mock_position.open_time = datetime.utcnow()
        enforcer.track_position_open(mock_position)
        
        allowed, reason, seconds_remaining = enforcer.validate_closure_request(
            mock_position, "stop_loss"
        )
        
        assert allowed is True
        assert reason is not None
        assert "exemption" in reason.lower()
        assert mock_position.position_id in enforcer.exempted_positions
    
    def test_emergency_override(self, mock_position):
        """Test emergency override creation."""
        enforcer = MinimumHoldTimeEnforcer()
        
        override_data = enforcer.create_emergency_override(
            mock_position.position_id,
            "Market volatility emergency closure",
            "risk_manager"
        )
        
        assert override_data["position_id"] == mock_position.position_id
        assert override_data["reason"] == "Market volatility emergency closure"
        assert mock_position.position_id in enforcer.exempted_positions
    
    def test_position_status_display(self, mock_position):
        """Test position status display data."""
        enforcer = MinimumHoldTimeEnforcer()
        
        # New position
        mock_position.open_time = datetime.utcnow()
        enforcer.track_position_open(mock_position)
        
        status = enforcer.get_position_hold_status(mock_position)
        
        assert status["position_id"] == mock_position.position_id
        assert status["status"] == "under_minimum"
        assert status["can_close"] is False
        assert status["time_remaining_seconds"] > 0
        assert status["elapsed_time_display"] is not None


# Integration tests

class TestIntegration:
    """Integration tests for multiple components."""
    
    @pytest.mark.asyncio
    async def test_complete_trade_workflow(self, mock_account, mock_trade):
        """Test complete trade workflow with all compliance checks."""
        # Initialize all components
        funding_pips = FundingPipsCompliance()
        daily_tracker = DailyLossTracker()
        drawdown_monitor = StaticDrawdownMonitor()
        stop_loss_enforcer = MandatoryStopLossEnforcer()
        hold_time_enforcer = MinimumHoldTimeEnforcer()
        
        # 1. Pre-trade validation
        validation_result = funding_pips.validate_trade(mock_account, mock_trade)
        assert validation_result.approved is True
        
        # 2. Daily loss check
        can_trade, reason = daily_tracker.can_trade(mock_account.account_id)
        assert can_trade is True
        
        # 3. Drawdown validation
        drawdown_allowed, drawdown_reason = drawdown_monitor.validate_trade_impact(
            mock_account, mock_trade
        )
        assert drawdown_allowed is True
        
        # 4. Stop loss validation
        sl_result = stop_loss_enforcer.validate_trade_stop_loss(mock_account, mock_trade)
        assert sl_result.valid is True
        
        # 5. Simulate position opening
        mock_position = Position(
            position_id="TEST_POS_001",
            account_id=mock_account.account_id,
            symbol=mock_trade.symbol,
            direction=mock_trade.direction,
            size=mock_trade.position_size,
            entry_price=mock_trade.entry_price,
            stop_loss=mock_trade.stop_loss,
            open_time=datetime.utcnow(),
            unrealized_pnl=Decimal('0.00')
        )
        
        hold_time_enforcer.track_position_open(mock_position)
        
        # 6. Immediate closure attempt should fail
        closure_allowed, closure_reason, time_remaining = hold_time_enforcer.validate_closure_request(
            mock_position, "manual"
        )
        assert closure_allowed is False
        assert time_remaining is not None
        
        # 7. Emergency closure should work
        hold_time_enforcer.create_emergency_override(
            mock_position.position_id,
            "Emergency market conditions"
        )
        
        closure_allowed, closure_reason, time_remaining = hold_time_enforcer.validate_closure_request(
            mock_position, "emergency"
        )
        assert closure_allowed is True
    
    def test_compliance_score_integration(self, mock_account):
        """Test integrated compliance score calculation."""
        funding_pips = FundingPipsCompliance()
        
        # Test with various account states
        scenarios = [
            # (daily_pnl, balance, expected_score_range)
            (Decimal('0'), Decimal('100000'), (95, 100)),
            (Decimal('-2000'), Decimal('100000'), (85, 95)),
            (Decimal('-3500'), Decimal('95000'), (70, 85)),
            (Decimal('-4000'), Decimal('92000'), (50, 70))
        ]
        
        for daily_pnl, balance, score_range in scenarios:
            mock_account.daily_pnl = daily_pnl
            mock_account.balance = balance
            mock_account.unrealized_pnl = Decimal('0')
            
            dashboard_data = funding_pips.get_compliance_dashboard_data(mock_account)
            score = dashboard_data["compliance_score"]
            
            assert score_range[0] <= score <= score_range[1], \
                f"Score {score} not in range {score_range} for daily_pnl={daily_pnl}, balance={balance}"


# Performance tests

class TestPerformance:
    """Performance tests for compliance components."""
    
    def test_validation_performance(self, mock_account, mock_trade):
        """Test validation performance meets sub-50ms requirement."""
        import time
        
        funding_pips = FundingPipsCompliance()
        
        # Run multiple validations and measure time
        start_time = time.time()
        iterations = 100
        
        for _ in range(iterations):
            result = funding_pips.validate_trade(mock_account, mock_trade)
            assert result.approved is True
        
        total_time = time.time() - start_time
        avg_time_ms = (total_time / iterations) * 1000
        
        # Should be well under 50ms per validation
        assert avg_time_ms < 10, f"Validation too slow: {avg_time_ms}ms > 10ms target"
    
    def test_dashboard_data_performance(self, mock_account):
        """Test dashboard data generation performance."""
        import time
        
        funding_pips = FundingPipsCompliance()
        
        start_time = time.time()
        iterations = 50
        
        for _ in range(iterations):
            dashboard_data = funding_pips.get_compliance_dashboard_data(mock_account)
            assert "compliance_score" in dashboard_data
        
        total_time = time.time() - start_time
        avg_time_ms = (total_time / iterations) * 1000
        
        # Dashboard should update within 1 second
        assert avg_time_ms < 20, f"Dashboard generation too slow: {avg_time_ms}ms > 20ms target"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])