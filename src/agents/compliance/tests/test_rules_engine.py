"""
Test cases for the Rules Engine
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from ..app.models import ViolationType, ComplianceStatus, NewsEvent
from ..app.prop_firm_configs import PropFirm


class TestRulesEngine:
    """Test the core rules validation engine"""
    
    @pytest.mark.asyncio
    async def test_validate_compliant_trade(self, rules_engine, dna_funded_account, sample_trade_order):
        """Test validation of a compliant trade"""
        result = await rules_engine.validate_trade(
            account=dna_funded_account,
            trade_order=sample_trade_order
        )
        
        assert result.is_valid
        assert result.compliance_status == ComplianceStatus.COMPLIANT
        assert len(result.violations) == 0
        assert "complies with all prop firm rules" in result.reason
    
    @pytest.mark.asyncio
    async def test_daily_loss_limit_violation(self, rules_engine, dna_funded_account, sample_trade_order):
        """Test daily loss limit violation"""
        # Set account to exceed daily loss limit (5% of $50,000 = $2,500)
        dna_funded_account.daily_pnl = Decimal("-2600.00")
        
        result = await rules_engine.validate_trade(
            account=dna_funded_account,
            trade_order=sample_trade_order
        )
        
        assert not result.is_valid
        assert result.compliance_status == ComplianceStatus.SUSPENDED
        assert ViolationType.DAILY_LOSS_EXCEEDED in result.violations
        assert "daily_loss_limit" in result.details
    
    @pytest.mark.asyncio
    async def test_max_drawdown_violation(self, rules_engine, dna_funded_account, sample_trade_order):
        """Test maximum drawdown violation"""
        # Set current balance to exceed max drawdown (10% of $50,000 = $5,000)
        dna_funded_account.current_balance = Decimal("44500.00")  # $5,500 drawdown
        
        result = await rules_engine.validate_trade(
            account=dna_funded_account,
            trade_order=sample_trade_order
        )
        
        assert not result.is_valid
        assert result.compliance_status == ComplianceStatus.SUSPENDED
        assert ViolationType.MAX_DRAWDOWN_EXCEEDED in result.violations
        assert "max_drawdown_limit" in result.details
    
    @pytest.mark.asyncio
    async def test_max_positions_violation(self, rules_engine, dna_funded_account, sample_trade_order, multiple_positions):
        """Test maximum concurrent positions violation"""
        # DNA Funded allows 5 positions, create scenario with 5 existing positions
        positions = multiple_positions * 3  # 6 positions total
        
        result = await rules_engine.validate_trade(
            account=dna_funded_account,
            trade_order=sample_trade_order,
            current_positions=positions
        )
        
        assert not result.is_valid
        assert ViolationType.MAX_POSITIONS_EXCEEDED in result.violations
        assert "max_positions_allowed" in result.details
    
    @pytest.mark.asyncio
    async def test_news_blackout_violation(self, rules_engine, dna_funded_account, sample_trade_order):
        """Test news trading restriction violation"""
        # Create high-impact news event in 1 minute (within 2-minute buffer)
        news_event = NewsEvent(
            event_id="test_nfp",
            title="Non-Farm Payrolls",
            currency="USD",
            impact="high",
            timestamp=datetime.utcnow() + timedelta(minutes=1)
        )
        
        result = await rules_engine.validate_trade(
            account=dna_funded_account,
            trade_order=sample_trade_order,
            upcoming_news=[news_event]
        )
        
        assert not result.is_valid
        assert ViolationType.NEWS_BLACKOUT_VIOLATION in result.violations
        assert "blocked_news_event" in result.details
    
    @pytest.mark.asyncio
    async def test_funding_pips_stop_loss_requirement(self, rules_engine, funding_pips_account, sample_trade_order):
        """Test Funding Pips mandatory stop-loss requirement"""
        # Remove stop loss from trade order
        sample_trade_order.stop_loss = None
        sample_trade_order.account_id = funding_pips_account.account_id
        
        result = await rules_engine.validate_trade(
            account=funding_pips_account,
            trade_order=sample_trade_order
        )
        
        assert not result.is_valid
        assert ViolationType.MISSING_STOP_LOSS in result.violations
        assert result.details["stop_loss_required"] is True
    
    @pytest.mark.asyncio
    async def test_position_size_violation(self, rules_engine, dna_funded_account, sample_trade_order):
        """Test position size violation"""
        # Set account balance to exactly $50k to use 10 lots tier, then exceed it
        dna_funded_account.current_balance = Decimal("50000.00")
        sample_trade_order.quantity = Decimal("11.0")  # Exceed 10 lots for $50k account
        
        result = await rules_engine.validate_trade(
            account=dna_funded_account,
            trade_order=sample_trade_order
        )
        
        assert not result.is_valid
        assert ViolationType.POSITION_SIZE_VIOLATION in result.violations
        assert "max_lot_size" in result.details
    
    @pytest.mark.asyncio
    async def test_warning_thresholds(self, rules_engine, dna_funded_account, sample_trade_order):
        """Test warning thresholds at 80% of limits"""
        # Set daily P&L to 80% of daily loss limit
        daily_limit = dna_funded_account.initial_balance * Decimal("0.05")  # 5%
        dna_funded_account.daily_pnl = -daily_limit * Decimal("0.8")  # 80% of limit
        
        result = await rules_engine.validate_trade(
            account=dna_funded_account,
            trade_order=sample_trade_order
        )
        
        assert result.is_valid  # Still valid but with warnings
        assert result.compliance_status == ComplianceStatus.WARNING
        assert len(result.warnings) > 0
        assert any("daily loss limit" in warning for warning in result.warnings)
    
    @pytest.mark.asyncio
    async def test_multiple_violations(self, rules_engine, dna_funded_account, sample_trade_order, multiple_positions):
        """Test handling of multiple simultaneous violations"""
        # Set up multiple violations
        dna_funded_account.daily_pnl = Decimal("-2600.00")  # Exceed daily limit
        dna_funded_account.current_balance = Decimal("44500.00")  # Exceed drawdown
        sample_trade_order.quantity = Decimal("5.0")  # Exceed position size
        
        result = await rules_engine.validate_trade(
            account=dna_funded_account,
            trade_order=sample_trade_order,
            current_positions=multiple_positions * 3  # Too many positions
        )
        
        assert not result.is_valid
        assert result.compliance_status == ComplianceStatus.SUSPENDED
        assert len(result.violations) >= 3
        assert ViolationType.DAILY_LOSS_EXCEEDED in result.violations
        assert ViolationType.MAX_DRAWDOWN_EXCEEDED in result.violations
    
    @pytest.mark.asyncio
    async def test_funding_pips_static_drawdown(self, rules_engine, funding_pips_account, sample_trade_order):
        """Test Funding Pips static drawdown calculation (vs trailing)"""
        # Funding Pips uses static drawdown, not trailing
        funding_pips_account.current_balance = Decimal("22900.00")  # $2,100 loss on $25,000
        
        result = await rules_engine.validate_trade(
            account=funding_pips_account,
            trade_order=sample_trade_order
        )
        
        # Should still be valid as 8% of $25,000 = $2,000, so $2,100 exceeds limit
        assert not result.is_valid
        assert ViolationType.MAX_DRAWDOWN_EXCEEDED in result.violations
        assert result.details["trailing_drawdown"] is False
    
    @pytest.mark.asyncio
    async def test_the_funded_trader_scaling_rules(self, rules_engine, the_funded_trader_account, sample_trade_order):
        """Test The Funded Trader scaling plan rules"""
        result = await rules_engine.validate_trade(
            account=the_funded_trader_account,
            trade_order=sample_trade_order
        )
        
        # Should include scaling information in details
        assert result.is_valid
        assert "consistency_rules" in result.details or result.compliance_status == ComplianceStatus.COMPLIANT


class TestComplianceMonitor:
    """Test the compliance monitoring functionality"""
    
    @pytest.mark.asyncio
    async def test_update_account_pnl_compliant(self, compliance_monitor, dna_funded_account):
        """Test P&L update for compliant account"""
        realized_pnl = Decimal("100.00")
        unrealized_pnl = Decimal("50.00")
        
        is_compliant = await compliance_monitor.update_account_pnl(
            account=dna_funded_account,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl
        )
        
        assert is_compliant
        assert dna_funded_account.daily_pnl == Decimal("250.00")  # 150 + 100
        assert dna_funded_account.current_balance == Decimal("51600.00")  # 51500 + 100
    
    @pytest.mark.asyncio
    async def test_update_account_pnl_violation(self, compliance_monitor, dna_funded_account):
        """Test P&L update that triggers violation"""
        # Large loss that would exceed daily limit
        realized_pnl = Decimal("-3000.00")
        
        is_compliant = await compliance_monitor.update_account_pnl(
            account=dna_funded_account,
            realized_pnl=realized_pnl,
            unrealized_pnl=Decimal("0.00")
        )
        
        assert not is_compliant
        assert dna_funded_account.status == ComplianceStatus.SUSPENDED
        assert dna_funded_account.daily_pnl <= -dna_funded_account.initial_balance * Decimal("0.05")
    
    @pytest.mark.asyncio
    async def test_reset_daily_pnl(self, compliance_monitor, dna_funded_account):
        """Test daily P&L reset"""
        original_days = dna_funded_account.trading_days_completed
        
        await compliance_monitor.reset_daily_pnl(dna_funded_account)
        
        assert dna_funded_account.daily_pnl == Decimal("0.00")
        assert dna_funded_account.trading_days_completed == original_days + 1
        assert dna_funded_account.last_reset_date is not None
    
    @pytest.mark.asyncio
    async def test_check_position_hold_time_valid(self, compliance_monitor, funding_pips_account, sample_position):
        """Test position hold time validation - valid"""
        # Set position opened more than 1 minute ago
        sample_position.opened_at = datetime.utcnow() - timedelta(minutes=2)
        
        can_close = await compliance_monitor.check_position_hold_time(
            account=funding_pips_account,
            position=sample_position
        )
        
        assert can_close
    
    @pytest.mark.asyncio
    async def test_check_position_hold_time_invalid(self, compliance_monitor, funding_pips_account, sample_position):
        """Test position hold time validation - invalid"""
        # Set position opened less than 1 minute ago
        sample_position.opened_at = datetime.utcnow() - timedelta(seconds=30)
        
        can_close = await compliance_monitor.check_position_hold_time(
            account=funding_pips_account,
            position=sample_position
        )
        
        assert not can_close
    
    @pytest.mark.asyncio
    async def test_no_hold_time_requirement(self, compliance_monitor, dna_funded_account, sample_position):
        """Test account with no hold time requirement"""
        # DNA Funded has no minimum hold time
        sample_position.opened_at = datetime.utcnow()  # Just opened
        
        can_close = await compliance_monitor.check_position_hold_time(
            account=dna_funded_account,
            position=sample_position
        )
        
        assert can_close  # Should allow immediate close


class TestPropFirmSpecificRules:
    """Test prop firm specific rule implementations"""
    
    @pytest.mark.asyncio
    async def test_dna_funded_consistency_rules(self, rules_engine, dna_funded_account, sample_trade_order):
        """Test DNA Funded consistency rules"""
        result = await rules_engine.validate_trade(
            account=dna_funded_account,
            trade_order=sample_trade_order
        )
        
        # DNA Funded has specific consistency requirements
        assert result.is_valid or result.compliance_status in [ComplianceStatus.COMPLIANT, ComplianceStatus.WARNING]
    
    @pytest.mark.asyncio
    async def test_funding_pips_risk_per_trade(self, rules_engine, funding_pips_account, sample_trade_order):
        """Test Funding Pips 2% risk per trade rule"""
        # Large position that might exceed 2% risk
        sample_trade_order.quantity = Decimal("10.0")  # 10 lots on $25k account
        sample_trade_order.account_id = funding_pips_account.account_id
        
        result = await rules_engine.validate_trade(
            account=funding_pips_account,
            trade_order=sample_trade_order
        )
        
        # Might violate position size due to risk calculation
        if not result.is_valid:
            assert ViolationType.POSITION_SIZE_VIOLATION in result.violations
        
        assert "max_risk_per_trade" in result.details
    
    @pytest.mark.asyncio
    async def test_the_funded_trader_buffer_time(self, rules_engine, the_funded_trader_account, sample_trade_order):
        """Test The Funded Trader 5-minute news buffer"""
        # Create news event in 3 minutes (within 5-minute buffer)
        news_event = NewsEvent(
            event_id="test_fomc",
            title="FOMC Rate Decision",
            currency="USD",
            impact="high",
            timestamp=datetime.utcnow() + timedelta(minutes=3)
        )
        
        result = await rules_engine.validate_trade(
            account=the_funded_trader_account,
            trade_order=sample_trade_order,
            upcoming_news=[news_event]
        )
        
        assert not result.is_valid
        assert ViolationType.NEWS_BLACKOUT_VIOLATION in result.violations