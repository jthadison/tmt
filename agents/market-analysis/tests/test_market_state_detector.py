"""
Tests for Market State Detection components
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import numpy as np
from unittest.mock import Mock, patch, AsyncMock

# Import components to test
from app.market_state_detector import (
    MarketRegimeClassifier,
    MarketState
)
from app.session_detector import (
    TradingSessionDetector,
    TradingSession
)
from app.economic_event_monitor import (
    EconomicEventMonitor,
    EconomicEvent,
    EventImportance
)
from app.correlation_analyzer import (
    CorrelationAnalyzer,
    CorrelationAnomaly
)
from app.volatility_analyzer import (
    VolatilityAnalyzer,
    VolatilityRegime,
    VolatilityMetrics
)
from app.parameter_adjustment_engine import (
    ParameterAdjustmentEngine,
    TradingParameters,
    AdjustmentReason
)
from app.market_state_agent import MarketStateAgent


class TestMarketRegimeClassifier:
    """Test market regime classification"""
    
    @pytest.fixture
    def classifier(self):
        return MarketRegimeClassifier()
    
    @pytest.fixture
    def trending_price_data(self):
        """Generate trending price data"""
        prices = []
        base_price = 1.1000
        for i in range(100):
            prices.append({
                'timestamp': datetime.now(timezone.utc) - timedelta(hours=100-i),
                'open': base_price + (i * 0.0002),
                'high': base_price + (i * 0.0002) + 0.0005,
                'low': base_price + (i * 0.0002) - 0.0003,
                'close': base_price + (i * 0.0002) + 0.0001
            })
        return prices
    
    @pytest.fixture
    def ranging_price_data(self):
        """Generate ranging price data"""
        prices = []
        base_price = 1.1000
        for i in range(100):
            oscillation = 0.0010 * np.sin(i * 0.5)
            prices.append({
                'timestamp': datetime.now(timezone.utc) - timedelta(hours=100-i),
                'open': base_price + oscillation,
                'high': base_price + oscillation + 0.0005,
                'low': base_price + oscillation - 0.0005,
                'close': base_price + oscillation + 0.0001
            })
        return prices
    
    def test_trending_market_detection(self, classifier, trending_price_data):
        """Test detection of trending market"""
        volume_data = [{'volume': 1000000} for _ in range(100)]
        
        result = classifier.classify_market_regime(trending_price_data, volume_data)
        
        assert result['regime'] in ['trending', 'volatile_trending']
        assert result['confidence'] > 60
        assert 'indicators' in result
        assert 'characteristics' in result
    
    def test_ranging_market_detection(self, classifier, ranging_price_data):
        """Test detection of ranging market"""
        volume_data = [{'volume': 1000000} for _ in range(100)]
        
        result = classifier.classify_market_regime(ranging_price_data, volume_data)
        
        assert result['regime'] in ['ranging', 'volatile_ranging']
        assert result['confidence'] > 50
        assert result['indicators']['range_factor'] > 0.5
    
    def test_insufficient_data_handling(self, classifier):
        """Test handling of insufficient data"""
        price_data = [{'close': 1.1000} for _ in range(5)]
        volume_data = []
        
        result = classifier.classify_market_regime(price_data, volume_data)
        
        assert result['regime'] == 'insufficient_data'
        assert result['confidence'] == 0.0
    
    def test_volatility_calculation(self, classifier, trending_price_data):
        """Test historical volatility calculation"""
        volatility = classifier.calculate_historical_volatility(trending_price_data)
        
        assert volatility > 0
        assert volatility < 100  # Reasonable volatility percentage
    
    def test_adx_calculation(self, classifier, trending_price_data):
        """Test ADX calculation"""
        adx = classifier.calculate_adx(trending_price_data)
        
        assert adx >= 0
        assert adx <= 100
    
    def test_ma_slope_calculation(self, classifier, trending_price_data):
        """Test moving average slope calculation"""
        slopes = classifier.calculate_ma_slopes(trending_price_data)
        
        assert 20 in slopes
        assert 50 in slopes
        assert all(isinstance(v, float) for v in slopes.values())


class TestTradingSessionDetector:
    """Test trading session detection"""
    
    @pytest.fixture
    def detector(self):
        return TradingSessionDetector()
    
    def test_london_session_detection(self, detector):
        """Test London session detection"""
        # 10:00 UTC - middle of London session
        timestamp = datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
        
        session = detector.detect_current_session(timestamp)
        
        assert session.name == 'london'
        assert session.type == 'single'
        assert session.expected_volatility == 'high'
    
    def test_london_ny_overlap_detection(self, detector):
        """Test London-NY overlap detection"""
        # 14:00 UTC - London-NY overlap
        timestamp = datetime(2024, 1, 15, 14, 0, tzinfo=timezone.utc)
        
        session = detector.detect_current_session(timestamp)
        
        assert session.name == 'london_ny'
        assert session.type == 'overlap'
        assert session.expected_volatility == 'very_high'
    
    def test_asian_session_detection(self, detector):
        """Test Asian session detection (overnight)"""
        # 23:00 UTC - Asian session
        timestamp = datetime(2024, 1, 15, 23, 0, tzinfo=timezone.utc)
        
        session = detector.detect_current_session(timestamp)
        
        assert session.name == 'asian'
        assert session.type == 'single'
    
    def test_weekend_detection(self, detector):
        """Test weekend market closure detection"""
        # Saturday
        timestamp = datetime(2024, 1, 13, 12, 0, tzinfo=timezone.utc)
        
        session = detector.detect_current_session(timestamp)
        
        assert session.name == 'weekend'
        assert session.type == 'closed'
        assert session.expected_volatility == 'none'
    
    def test_best_trading_times(self, detector):
        """Test best trading times for currency pairs"""
        times = detector.get_best_trading_times('EURUSD')
        
        assert len(times) > 0
        assert any('london' in t['session'] for t in times)
        assert any('overlap' in t.get('session', '') for t in times)
    
    def test_session_volatility_multiplier(self, detector):
        """Test volatility multiplier calculation"""
        overlap_session = TradingSession(
            name='london_ny',
            type='overlap',
            characteristics={},
            expected_volatility='very_high',
            typical_volume='very_high'
        )
        
        multiplier = detector.calculate_session_volatility_multiplier(overlap_session)
        
        assert multiplier > 1.0  # Overlap should increase multiplier


class TestEconomicEventMonitor:
    """Test economic event monitoring"""
    
    @pytest.fixture
    def monitor(self):
        return EconomicEventMonitor()
    
    @pytest.mark.asyncio
    async def test_get_upcoming_events(self, monitor):
        """Test fetching upcoming events"""
        events = await monitor.get_upcoming_events(hours_ahead=24)
        
        assert isinstance(events, list)
        # Since we're using simulated data, we should get some events
        if events:
            event = events[0]
            assert hasattr(event, 'event_name')
            assert hasattr(event, 'importance')
            assert hasattr(event, 'restriction_window')
    
    def test_trading_restriction_check(self, monitor):
        """Test trading restriction checking"""
        # Create a test event
        event = EconomicEvent(
            event_id='test',
            event_name='Non Farm Payrolls',
            country='United States',
            currency='USD',
            event_time=datetime.now(timezone.utc) + timedelta(minutes=15),
            importance=EventImportance.HIGH,
            restriction_window={
                'start': datetime.now(timezone.utc) - timedelta(minutes=15),
                'end': datetime.now(timezone.utc) + timedelta(minutes=45)
            },
            affected_pairs=['EURUSD', 'GBPUSD']
        )
        
        monitor.cached_events = [event]
        monitor.cache_timestamp = datetime.now(timezone.utc)
        
        # Check restriction for affected pair
        restriction = monitor.is_trading_restricted('EURUSD')
        
        assert restriction['restricted'] == True
        assert 'Non Farm Payrolls' in restriction['reason']
    
    def test_event_impact_analysis(self, monitor):
        """Test event impact analysis"""
        event = EconomicEvent(
            event_id='test',
            event_name='GDP',
            country='United States',
            currency='USD',
            event_time=datetime.now(timezone.utc),
            importance=EventImportance.HIGH,
            actual_value=Decimal('2.5'),
            forecast_value=Decimal('2.0')
        )
        
        analysis = monitor.get_event_impact_analysis(event)
        
        assert analysis['event_name'] == 'GDP'
        assert analysis['importance'] == 'high'
        assert 'deviation' in analysis
        assert analysis['deviation']['direction'] == 'above'


class TestCorrelationAnalyzer:
    """Test correlation analysis"""
    
    @pytest.fixture
    def analyzer(self):
        return CorrelationAnalyzer()
    
    @pytest.fixture
    def price_data_dict(self):
        """Generate correlated price data"""
        data = {}
        base_prices = np.random.randn(100) * 0.01 + 1.1000
        
        # EURUSD - base
        data['EURUSD'] = [
            {'close': price, 'timestamp': datetime.now(timezone.utc)}
            for price in base_prices
        ]
        
        # GBPUSD - positively correlated
        gbp_prices = base_prices * 1.2 + np.random.randn(100) * 0.002
        data['GBPUSD'] = [
            {'close': price, 'timestamp': datetime.now(timezone.utc)}
            for price in gbp_prices
        ]
        
        # USDCHF - negatively correlated
        chf_prices = 0.9 - (base_prices - 1.1) * 0.8 + np.random.randn(100) * 0.002
        data['USDCHF'] = [
            {'close': price, 'timestamp': datetime.now(timezone.utc)}
            for price in chf_prices
        ]
        
        return data
    
    def test_correlation_matrix_calculation(self, analyzer, price_data_dict):
        """Test correlation matrix calculation"""
        matrix = analyzer.calculate_correlation_matrix(price_data_dict, period=50)
        
        assert 'EURUSD' in matrix
        assert 'GBPUSD' in matrix['EURUSD']
        assert matrix['EURUSD']['EURUSD'] == 1.0
        
        # Check for expected correlations
        eurusd_gbpusd = matrix['EURUSD']['GBPUSD']
        assert eurusd_gbpusd > 0.5  # Should be positively correlated
        
        eurusd_usdchf = matrix['EURUSD']['USDCHF']
        assert eurusd_usdchf < -0.3  # Should be negatively correlated
    
    def test_correlation_anomaly_detection(self, analyzer):
        """Test anomaly detection"""
        current_correlations = {
            'EURUSD': {'GBPUSD': 0.2, 'USDCHF': -0.3},
            'GBPUSD': {'EURUSD': 0.2, 'USDCHF': -0.4},
            'USDCHF': {'EURUSD': -0.3, 'GBPUSD': -0.4}
        }
        
        # Set expected correlations
        analyzer.expected_correlations = {
            ('EURUSD', 'GBPUSD'): 0.75,
            ('EURUSD', 'USDCHF'): -0.95
        }
        
        anomalies = analyzer.detect_correlation_anomalies(current_correlations)
        
        assert len(anomalies) > 0
        assert any(a.severity in ['high', 'extreme'] for a in anomalies)
    
    def test_correlation_clusters(self, analyzer):
        """Test correlation cluster identification"""
        correlation_matrix = {
            'EURUSD': {'EURUSD': 1.0, 'GBPUSD': 0.8, 'AUDUSD': 0.75, 'USDJPY': -0.2},
            'GBPUSD': {'EURUSD': 0.8, 'GBPUSD': 1.0, 'AUDUSD': 0.72, 'USDJPY': -0.1},
            'AUDUSD': {'EURUSD': 0.75, 'GBPUSD': 0.72, 'AUDUSD': 1.0, 'USDJPY': -0.15},
            'USDJPY': {'EURUSD': -0.2, 'GBPUSD': -0.1, 'AUDUSD': -0.15, 'USDJPY': 1.0}
        }
        
        clusters = analyzer.identify_correlation_clusters(correlation_matrix, threshold=0.7)
        
        assert len(clusters) > 0
        # EURUSD, GBPUSD, AUDUSD should be in same cluster
        assert any(all(pair in cluster for pair in ['EURUSD', 'GBPUSD', 'AUDUSD'])
                  for cluster in clusters)


class TestVolatilityAnalyzer:
    """Test volatility analysis"""
    
    @pytest.fixture
    def analyzer(self):
        return VolatilityAnalyzer()
    
    @pytest.fixture
    def volatile_price_data(self):
        """Generate volatile price data"""
        prices = []
        base_price = 1.1000
        for i in range(100):
            volatility = 0.002 * (1 + 0.5 * np.sin(i * 0.1))
            change = np.random.randn() * volatility
            prices.append({
                'timestamp': datetime.now(timezone.utc) - timedelta(hours=100-i),
                'open': base_price + change,
                'high': base_price + change + abs(np.random.randn() * volatility),
                'low': base_price + change - abs(np.random.randn() * volatility),
                'close': base_price + change + np.random.randn() * volatility * 0.5
            })
            base_price += change
        return prices
    
    def test_atr_calculation(self, analyzer, volatile_price_data):
        """Test ATR calculation"""
        atr = analyzer.calculate_atr(volatile_price_data, period=14)
        
        assert atr > 0
        assert isinstance(atr, float)
    
    def test_comprehensive_volatility_metrics(self, analyzer, volatile_price_data):
        """Test comprehensive volatility calculation"""
        metrics = analyzer.calculate_comprehensive_volatility(volatile_price_data)
        
        assert isinstance(metrics, VolatilityMetrics)
        assert 14 in metrics.atr_values
        assert metrics.historical_volatility > 0
        assert 0 <= metrics.volatility_percentile <= 100
        assert metrics.volatility_regime in VolatilityRegime
    
    def test_volatility_expansion_detection(self, analyzer):
        """Test volatility expansion detection"""
        # Create returns with expanding volatility
        returns = np.random.randn(40) * 0.001  # Low volatility
        returns = np.append(returns, np.random.randn(20) * 0.003)  # Higher volatility
        
        expansion = analyzer.detect_volatility_expansion(returns.tolist())
        
        assert isinstance(expansion, bool)
    
    def test_volatility_clustering(self, analyzer, volatile_price_data):
        """Test volatility cluster detection"""
        clusters = analyzer.detect_volatility_clusters(volatile_price_data)
        
        assert isinstance(clusters, list)
        for cluster in clusters:
            assert len(cluster) == 2  # Start and end times
            assert isinstance(cluster[0], datetime)
            assert isinstance(cluster[1], datetime)
    
    def test_garch_forecast(self, analyzer):
        """Test GARCH volatility forecast"""
        returns = np.random.randn(100) * 0.01
        
        forecast = analyzer.calculate_garch_forecast(returns.tolist())
        
        if forecast is not None:
            assert forecast > 0
            assert forecast < 200  # Reasonable volatility percentage


class TestParameterAdjustmentEngine:
    """Test parameter adjustment system"""
    
    @pytest.fixture
    def engine(self):
        return ParameterAdjustmentEngine()
    
    def test_regime_based_adjustment(self, engine):
        """Test regime-based parameter adjustment"""
        market_state = {
            'regime': 'trending',
            'volatility_regime': 'normal'
        }
        
        adjustment = engine.adjust_parameters_for_market_state(market_state)
        
        assert adjustment.adjusted_params.stop_loss_atr_multiple > engine.base_parameters.stop_loss_atr_multiple
        assert adjustment.adjusted_params.holding_time_multiplier > engine.base_parameters.holding_time_multiplier
    
    def test_volatility_based_adjustment(self, engine):
        """Test volatility-based parameter adjustment"""
        market_state = {
            'regime': 'ranging',
            'volatility_regime': 'very_high'
        }
        
        adjustment = engine.adjust_parameters_for_market_state(market_state)
        
        assert adjustment.adjusted_params.position_size_percentage < engine.base_parameters.position_size_percentage
        assert adjustment.adjusted_params.stop_loss_atr_multiple > engine.base_parameters.stop_loss_atr_multiple
    
    def test_economic_event_adjustment(self, engine):
        """Test economic event parameter adjustment"""
        market_state = {
            'regime': 'trending',
            'economic_events': [
                {'importance': 'high', 'event_name': 'Non Farm Payrolls'},
                {'importance': 'high', 'event_name': 'FOMC'}
            ]
        }
        
        adjustment = engine.adjust_parameters_for_market_state(market_state)
        
        # Multiple high-impact events should reduce risk
        assert adjustment.adjusted_params.position_size_percentage < 0.5
        assert adjustment.adjusted_params.max_signals_per_week < engine.base_parameters.max_signals_per_week
    
    def test_parameter_limits(self, engine):
        """Test that parameter adjustments respect limits"""
        market_state = {
            'regime': 'volatile',
            'volatility_regime': 'extreme',
            'correlation_breakdown': {'severity': 'extreme'}
        }
        
        adjustment = engine.adjust_parameters_for_market_state(market_state)
        
        # Check all parameters are within limits
        params = adjustment.adjusted_params
        limits = engine.adjustment_limits
        
        assert limits['stop_loss_atr_multiple']['min'] <= params.stop_loss_atr_multiple <= limits['stop_loss_atr_multiple']['max']
        assert limits['position_size_percentage']['min'] <= params.position_size_percentage <= limits['position_size_percentage']['max']
        assert limits['max_signals_per_week']['min'] <= params.max_signals_per_week <= limits['max_signals_per_week']['max']


class TestMarketStateAgent:
    """Test main market state agent integration"""
    
    @pytest.fixture
    def agent(self):
        return MarketStateAgent()
    
    @pytest.fixture
    def sample_price_data(self):
        """Generate sample price data for multiple instruments"""
        data = {}
        instruments = ['EURUSD', 'GBPUSD', 'USDJPY']
        
        for instrument in instruments:
            prices = []
            base_price = 1.1000 if 'EUR' in instrument else 1.3000 if 'GBP' in instrument else 110.00
            
            for i in range(100):
                change = np.random.randn() * 0.001
                prices.append({
                    'timestamp': datetime.now(timezone.utc) - timedelta(hours=100-i),
                    'open': base_price,
                    'high': base_price + abs(change),
                    'low': base_price - abs(change),
                    'close': base_price + change * 0.5
                })
                base_price += change
            
            data[instrument] = prices
        
        return data
    
    @pytest.mark.asyncio
    async def test_analyze_market_state(self, agent, sample_price_data):
        """Test comprehensive market state analysis"""
        state = await agent.analyze_market_state(sample_price_data)
        
        assert isinstance(state, MarketState)
        assert state.regime in ['trending', 'ranging', 'volatile', 'quiet', 'transitional',
                               'volatile_trending', 'volatile_ranging']
        assert 0 <= state.confidence <= 100
        assert state.session
        assert state.volatility
        assert state.parameter_adjustments
    
    def test_trading_restrictions(self, agent):
        """Test trading restriction checking"""
        # Set a mock state with extreme volatility
        agent.current_state = MarketState(
            regime='volatile',
            confidence=85.0,
            session={'name': 'london'},
            volatility={'regime': 'extreme'},
            correlations={},
            economic_events=[],
            timestamp=datetime.now(timezone.utc),
            indicators={},
            parameter_adjustments={}
        )
        
        restrictions = agent.check_trading_restrictions('EURUSD')
        
        assert restrictions['restricted'] == True
        assert any(r['type'] == 'volatility' for r in restrictions['restrictions'])
    
    def test_state_summary(self, agent):
        """Test state summary generation"""
        agent.current_state = MarketState(
            regime='trending',
            confidence=75.0,
            session={'name': 'london', 'type': 'single'},
            volatility={'regime': 'normal', 'percentile': 50.0, 'expansion': False, 'contraction': False},
            correlations={'anomalies': [], 'breakdown_analysis': {'severity': 'none'}},
            economic_events=[],
            timestamp=datetime.now(timezone.utc),
            indicators={},
            parameter_adjustments={}
        )
        
        summary = agent.get_state_summary()
        
        assert summary['status'] == 'active'
        assert summary['market_regime']['type'] == 'trending'
        assert summary['volatility']['regime'] == 'normal'
        assert 'current_parameters' in summary
    
    @pytest.mark.asyncio
    async def test_event_publishing(self, agent):
        """Test state change event publishing"""
        published_events = []
        
        async def mock_publisher(event):
            published_events.append(event)
        
        agent.register_event_publisher(mock_publisher)
        
        # Create initial state
        agent.current_state = None
        new_state = MarketState(
            regime='trending',
            confidence=80.0,
            session={'name': 'london'},
            volatility={'regime': 'normal'},
            correlations={},
            economic_events=[],
            timestamp=datetime.now(timezone.utc),
            indicators={},
            parameter_adjustments={}
        )
        
        await agent._check_state_changes(new_state)
        
        assert len(published_events) > 0
        assert published_events[0]['event_type'] == 'market.state.changed'