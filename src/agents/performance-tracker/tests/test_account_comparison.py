"""Tests for account comparison and ranking system."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..app.models import Base, TradePerformance, PerformanceMetrics, PeriodType, TradeStatus
from ..app.account_comparison import PerformanceRankingAlgorithm, AccountComparisonSystem


@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def ranking_algorithm():
    """Create ranking algorithm instance."""
    return PerformanceRankingAlgorithm()


def test_ranking_score_calculation(ranking_algorithm):
    """Test ranking score calculation."""
    score = ranking_algorithm.calculate_ranking_score(
        total_return=Decimal("0.15"),      # 15% return
        sharpe_ratio=Decimal("1.5"),       # Good risk-adjusted return
        sortino_ratio=Decimal("2.0"),      # Excellent downside risk
        max_drawdown=Decimal("0.05"),      # 5% drawdown
        profit_factor=Decimal("2.0"),      # Good profit factor
        win_rate=Decimal("65.0"),          # 65% win rate
        total_trades=100                   # Good activity level
    )
    
    assert isinstance(score, Decimal)
    assert 0 <= score <= 100
    assert score > 70  # Should score highly with these metrics


def test_return_scoring(ranking_algorithm):
    """Test return component scoring."""
    # Test different return levels
    high_return_score = ranking_algorithm._score_return(Decimal("0.50"))  # 50%
    medium_return_score = ranking_algorithm._score_return(Decimal("0.15"))  # 15%
    low_return_score = ranking_algorithm._score_return(Decimal("0.05"))   # 5%
    negative_return_score = ranking_algorithm._score_return(Decimal("-0.10"))  # -10%
    
    assert high_return_score > medium_return_score > low_return_score
    assert negative_return_score == Decimal("0")


def test_risk_adjusted_return_scoring(ranking_algorithm):
    """Test risk-adjusted return scoring."""
    excellent_sharpe = ranking_algorithm._score_risk_adjusted_return(
        Decimal("2.5"), None  # Excellent Sharpe ratio
    )
    good_sharpe = ranking_algorithm._score_risk_adjusted_return(
        Decimal("1.2"), None  # Good Sharpe ratio
    )
    poor_sharpe = ranking_algorithm._score_risk_adjusted_return(
        Decimal("-0.5"), None  # Poor Sharpe ratio
    )
    
    assert excellent_sharpe > good_sharpe > poor_sharpe
    assert excellent_sharpe == 100  # Should max out


def test_consistency_scoring(ranking_algorithm):
    """Test consistency component scoring."""
    low_drawdown_score = ranking_algorithm._score_consistency(
        Decimal("0.02"), Decimal("0.01")  # 2% drawdown, 1% volatility
    )
    high_drawdown_score = ranking_algorithm._score_consistency(
        Decimal("0.25"), Decimal("0.15")  # 25% drawdown, 15% volatility
    )
    
    assert low_drawdown_score > high_drawdown_score
    assert high_drawdown_score < 20  # Should score poorly with high drawdown


def test_efficiency_scoring(ranking_algorithm):
    """Test efficiency component scoring."""
    high_efficiency = ranking_algorithm._score_efficiency(
        Decimal("3.5"), Decimal("75.0")  # High profit factor and win rate
    )
    low_efficiency = ranking_algorithm._score_efficiency(
        Decimal("0.8"), Decimal("35.0")  # Low profit factor and win rate
    )
    
    assert high_efficiency > low_efficiency
    assert low_efficiency < 30  # Should score poorly


def test_activity_scoring(ranking_algorithm):
    """Test activity level scoring."""
    optimal_activity = ranking_algorithm._score_activity(100)  # Optimal range
    low_activity = ranking_algorithm._score_activity(20)      # Too low
    over_activity = ranking_algorithm._score_activity(500)    # Too high
    no_activity = ranking_algorithm._score_activity(0)       # No trades
    
    assert optimal_activity == 100
    assert optimal_activity > low_activity > no_activity
    assert optimal_activity > over_activity
    assert no_activity == 0


@pytest.mark.asyncio
async def test_account_rankings_calculation(db_session):
    """Test account rankings calculation."""
    comparison_system = AccountComparisonSystem(db_session)
    
    # Create test accounts with different performance
    account_ids = [uuid4() for _ in range(3)]
    
    # Create performance data for each account
    start_date = datetime.utcnow() - timedelta(days=30)
    end_date = datetime.utcnow()
    
    for i, account_id in enumerate(account_ids):
        # Create trades with different performance levels
        for j in range(10):
            pnl = Decimal("50.0") * (i + 1)  # Different performance per account
            if j > 6:  # Some losing trades
                pnl = -pnl / 2
                
            trade = TradePerformance(
                trade_id=uuid4(),
                account_id=account_id,
                symbol="EURUSD",
                entry_time=start_date + timedelta(days=j),
                exit_time=start_date + timedelta(days=j) + timedelta(hours=2),
                entry_price=Decimal("1.1000"),
                exit_price=Decimal("1.1050") if pnl > 0 else Decimal("1.0950"),
                position_size=Decimal("1.0"),
                pnl=pnl,
                status=TradeStatus.CLOSED.value
            )
            db_session.add(trade)
    
    db_session.commit()
    
    # Calculate rankings
    rankings = await comparison_system.calculate_account_rankings(
        account_ids, start_date, end_date, PeriodType.MONTHLY
    )
    
    assert len(rankings) == 3
    assert rankings[0].performance_rank == 1  # Best performer
    assert rankings[-1].performance_rank == 3  # Worst performer
    
    # Verify ranking scores are ordered
    for i in range(len(rankings) - 1):
        assert rankings[i].ranking_score >= rankings[i + 1].ranking_score


@pytest.mark.asyncio
async def test_best_worst_performers_identification(db_session):
    """Test identification of best and worst performers."""
    comparison_system = AccountComparisonSystem(db_session)
    
    account_ids = [uuid4() for _ in range(5)]
    start_date = datetime.utcnow() - timedelta(days=30)
    end_date = datetime.utcnow()
    
    # Create performance data with clear best/worst
    performance_levels = [100, 75, 50, 25, 10]  # Different P&L levels
    
    for i, (account_id, pnl_level) in enumerate(zip(account_ids, performance_levels)):
        trade = TradePerformance(
            trade_id=uuid4(),
            account_id=account_id,
            symbol="EURUSD",
            entry_time=start_date,
            exit_time=start_date + timedelta(hours=1),
            entry_price=Decimal("1.1000"),
            exit_price=Decimal("1.1000") + (Decimal(str(pnl_level)) / 10000),
            position_size=Decimal("1.0"),
            pnl=Decimal(str(pnl_level)),
            status=TradeStatus.CLOSED.value
        )
        db_session.add(trade)
    
    db_session.commit()
    
    performers = await comparison_system.get_best_worst_performers(
        account_ids, start_date, end_date
    )
    
    assert "best_performer" in performers
    assert "worst_performer" in performers
    assert "median_performer" in performers
    
    # Best performer should have highest P&L
    assert performers["best_performer"].total_pnl == Decimal("100")
    # Worst performer should have lowest P&L
    assert performers["worst_performer"].total_pnl == Decimal("10")


@pytest.mark.asyncio
async def test_performance_heatmap_generation(db_session):
    """Test performance heatmap data generation."""
    comparison_system = AccountComparisonSystem(db_session)
    
    account_ids = [uuid4() for _ in range(4)]
    start_date = datetime.utcnow() - timedelta(days=7)
    end_date = datetime.utcnow()
    
    # Create varied performance data
    pnl_values = [200, 150, 100, 50]
    
    for account_id, pnl in zip(account_ids, pnl_values):
        trade = TradePerformance(
            trade_id=uuid4(),
            account_id=account_id,
            symbol="EURUSD",
            entry_time=start_date,
            exit_time=start_date + timedelta(hours=1),
            entry_price=Decimal("1.1000"),
            exit_price=Decimal("1.1000") + (Decimal(str(pnl)) / 10000),
            position_size=Decimal("1.0"),
            pnl=Decimal(str(pnl)),
            status=TradeStatus.CLOSED.value
        )
        db_session.add(trade)
    
    db_session.commit()
    
    heatmap_data = await comparison_system.generate_performance_heatmap_data(
        account_ids, start_date, end_date, "total_pnl"
    )
    
    assert "accounts" in heatmap_data
    assert "data" in heatmap_data
    assert "statistics" in heatmap_data
    
    assert len(heatmap_data["data"]) == 4
    assert heatmap_data["statistics"]["max"] == 200.0
    assert heatmap_data["statistics"]["min"] == 50.0


@pytest.mark.asyncio
async def test_relative_performance_calculation(db_session):
    """Test relative performance calculation."""
    comparison_system = AccountComparisonSystem(db_session)
    
    target_account = uuid4()
    benchmark_accounts = [uuid4() for _ in range(4)]
    
    start_date = datetime.utcnow() - timedelta(days=30)
    end_date = datetime.utcnow()
    
    # Target account performance: 150
    target_trade = TradePerformance(
        trade_id=uuid4(),
        account_id=target_account,
        symbol="EURUSD",
        entry_time=start_date,
        exit_time=start_date + timedelta(hours=1),
        pnl=Decimal("150"),
        status=TradeStatus.CLOSED.value
    )
    db_session.add(target_trade)
    
    # Benchmark accounts: 100, 120, 80, 110 (mean = 102.5)
    benchmark_pnls = [100, 120, 80, 110]
    
    for account_id, pnl in zip(benchmark_accounts, benchmark_pnls):
        trade = TradePerformance(
            trade_id=uuid4(),
            account_id=account_id,
            symbol="EURUSD",
            entry_time=start_date,
            exit_time=start_date + timedelta(hours=1),
            pnl=Decimal(str(pnl)),
            status=TradeStatus.CLOSED.value
        )
        db_session.add(trade)
    
    db_session.commit()
    
    relative_perf = await comparison_system.calculate_relative_performance(
        target_account, benchmark_accounts, start_date, end_date
    )
    
    assert "relative_metrics" in relative_perf
    assert relative_perf["relative_metrics"]["excess_return"] == 47.5  # 150 - 102.5
    assert relative_perf["relative_metrics"]["outperformance"] is True
    assert relative_perf["relative_metrics"]["z_score"] > 0  # Above average


@pytest.mark.asyncio
async def test_performance_anomaly_detection(db_session):
    """Test detection of anomalous performance."""
    comparison_system = AccountComparisonSystem(db_session)
    
    account_ids = [uuid4() for _ in range(6)]
    start_date = datetime.utcnow() - timedelta(days=30)
    end_date = datetime.utcnow()
    
    # Normal performance: 90-110, Anomaly: 300 (extreme positive), -200 (extreme negative)
    pnl_values = [100, 95, 105, 110, 300, -200]
    
    for account_id, pnl in zip(account_ids, pnl_values):
        trade = TradePerformance(
            trade_id=uuid4(),
            account_id=account_id,
            symbol="EURUSD",
            entry_time=start_date,
            exit_time=start_date + timedelta(hours=1),
            pnl=Decimal(str(pnl)),
            status=TradeStatus.CLOSED.value
        )
        db_session.add(trade)
    
    db_session.commit()
    
    anomalies = await comparison_system.detect_performance_anomalies(
        account_ids, start_date, end_date, z_score_threshold=2.0
    )
    
    assert "anomalous_accounts" in anomalies
    assert len(anomalies["anomalous_accounts"]) == 2  # Should detect 2 anomalies
    
    # Check anomaly types
    anomaly_types = [a["anomaly_type"] for a in anomalies["anomalous_accounts"]]
    assert "positive" in anomaly_types
    assert "negative" in anomaly_types


def test_percentile_rank_calculation():
    """Test percentile rank calculation helper function."""
    comparison_system = AccountComparisonSystem(None)
    
    benchmark_values = [10, 20, 30, 40, 50]
    
    # Test various positions
    assert comparison_system._calculate_percentile_rank(15, benchmark_values) == 20.0  # 20th percentile
    assert comparison_system._calculate_percentile_rank(35, benchmark_values) == 60.0  # 60th percentile
    assert comparison_system._calculate_percentile_rank(55, benchmark_values) == 100.0  # 100th percentile
    assert comparison_system._calculate_percentile_rank(5, benchmark_values) == 0.0   # 0th percentile