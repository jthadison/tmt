"""
Test configuration and fixtures
"""

import pytest
from datetime import datetime
from decimal import Decimal

from ..app.models import TradingAccount, TradeOrder, Position, NewsEvent
from ..app.prop_firm_configs import PropFirm, AccountPhase, TradingPlatform
from ..app.rules_engine import RulesEngine, ComplianceMonitor


@pytest.fixture
def rules_engine():
    """Create rules engine for testing"""
    return RulesEngine()


@pytest.fixture
def compliance_monitor(rules_engine):
    """Create compliance monitor for testing"""
    return ComplianceMonitor(rules_engine)


@pytest.fixture
def dna_funded_account():
    """Create DNA Funded test account"""
    return TradingAccount(
        account_id="test_dna_001",
        prop_firm=PropFirm.DNA_FUNDED,
        account_phase=AccountPhase.FUNDED,
        initial_balance=Decimal("50000"),
        current_balance=Decimal("51500"),
        platform=TradingPlatform.TRADELOCKER,
        status="compliant",
        created_at=datetime.utcnow(),
        daily_pnl=Decimal("150.00"),
        total_drawdown=Decimal("0.00"),
        open_positions=2,
        trading_days_completed=15
    )


@pytest.fixture
def funding_pips_account():
    """Create Funding Pips test account"""
    return TradingAccount(
        account_id="test_fp_001",
        prop_firm=PropFirm.FUNDING_PIPS,
        account_phase=AccountPhase.EVALUATION,
        initial_balance=Decimal("25000"),
        current_balance=Decimal("26200"),
        platform=TradingPlatform.DXTRADE,
        status="compliant",
        created_at=datetime.utcnow(),
        daily_pnl=Decimal("50.00"),
        total_drawdown=Decimal("0.00"),
        open_positions=1,
        trading_days_completed=8
    )


@pytest.fixture
def the_funded_trader_account():
    """Create The Funded Trader test account"""
    return TradingAccount(
        account_id="test_tft_001",
        prop_firm=PropFirm.THE_FUNDED_TRADER,
        account_phase=AccountPhase.FUNDED,
        initial_balance=Decimal("100000"),
        current_balance=Decimal("105000"),
        platform=TradingPlatform.TRADELOCKER,
        status="compliant",
        created_at=datetime.utcnow(),
        daily_pnl=Decimal("200.00"),
        total_drawdown=Decimal("0.00"),
        open_positions=3,
        trading_days_completed=25
    )


@pytest.fixture
def sample_trade_order():
    """Create sample trade order"""
    return TradeOrder(
        account_id="test_account",
        symbol="EURUSD",
        side="buy",
        order_type="market",
        quantity=Decimal("1.0"),  # 1 lot
        stop_loss=Decimal("1.0950"),
        take_profit=Decimal("1.1050")
    )


@pytest.fixture
def sample_position():
    """Create sample position"""
    return Position(
        position_id="pos_001",
        account_id="test_account",
        symbol="EURUSD",
        side="buy",
        quantity=Decimal("1.0"),
        entry_price=Decimal("1.1000"),
        current_price=Decimal("1.1025"),
        unrealized_pnl=Decimal("25.00"),
        opened_at=datetime.utcnow()
    )


@pytest.fixture
def high_impact_news_event():
    """Create high-impact news event"""
    return NewsEvent(
        event_id="nfp_001",
        title="Non-Farm Payrolls",
        currency="USD",
        impact="high",
        forecast="200K",
        previous="190K",
        timestamp=datetime.utcnow()
    )


@pytest.fixture
def multiple_positions():
    """Create multiple test positions"""
    return [
        Position(
            position_id="pos_001",
            account_id="test_account",
            symbol="EURUSD",
            side="buy",
            quantity=Decimal("1.0"),
            entry_price=Decimal("1.1000"),
            current_price=Decimal("1.1025"),
            unrealized_pnl=Decimal("25.00"),
            opened_at=datetime.utcnow()
        ),
        Position(
            position_id="pos_002",
            account_id="test_account",
            symbol="GBPUSD",
            side="sell",
            quantity=Decimal("0.5"),
            entry_price=Decimal("1.2500"),
            current_price=Decimal("1.2480"),
            unrealized_pnl=Decimal("10.00"),
            opened_at=datetime.utcnow()
        )
    ]