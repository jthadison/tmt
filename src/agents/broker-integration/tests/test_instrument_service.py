"""
Tests for Instrument Service - Story 8.2
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import datetime, timedelta
import aiohttp

from ..instrument_service import (
    OandaInstrumentService,
    InstrumentInfo,
    InstrumentSpread,
    SpreadHistory,
    InstrumentCache,
    InstrumentType,
    TradingStatus
)

class TestInstrumentCache:
    """Test InstrumentCache functionality"""
    
    def test_cache_initialization(self):
        """Test cache initialization"""
        cache = InstrumentCache(info_ttl_minutes=30, spread_ttl_seconds=10)
        
        assert cache.info_ttl == timedelta(minutes=30)
        assert cache.spread_ttl == timedelta(seconds=10)
        assert len(cache.instrument_info) == 0
        assert len(cache.instrument_spreads) == 0
    
    def test_instrument_info_cache(self):
        """Test instrument info caching"""
        cache = InstrumentCache(info_ttl_minutes=1)
        
        # Create test instrument info
        info = InstrumentInfo(
            name="EUR_USD",
            display_name="EUR/USD",
            type=InstrumentType.CURRENCY,
            pip_location=-4,
            display_precision=5,
            trade_units_precision=0,
            minimum_trade_size=Decimal("1"),
            maximum_trade_size=Decimal("100000000"),
            maximum_position_size=Decimal("100000000"),
            margin_rate=Decimal("0.02"),
            commission_rate=Decimal("0"),
            minimum_trailing_stop=None,
            maximum_trailing_stop=None,
            tags=["MAJOR", "FOREX"],
            financing_days_of_week=["MON", "TUE", "WED", "THU", "FRI"]
        )
        
        # Set and get
        cache.set_info("EUR_USD", info)
        retrieved = cache.get_info("EUR_USD")
        
        assert retrieved == info
        assert "EUR_USD" in cache.info_timestamps
    
    def test_instrument_info_expiration(self):
        """Test instrument info expiration"""
        cache = InstrumentCache(info_ttl_minutes=0.001)  # Very short TTL
        
        info = InstrumentInfo(
            name="EUR_USD",
            display_name="EUR/USD", 
            type=InstrumentType.CURRENCY,
            pip_location=-4,
            display_precision=5,
            trade_units_precision=0,
            minimum_trade_size=Decimal("1"),
            maximum_trade_size=Decimal("100000000"),
            maximum_position_size=Decimal("100000000"),
            margin_rate=Decimal("0.02"),
            commission_rate=Decimal("0"),
            minimum_trailing_stop=None,
            maximum_trailing_stop=None,
            tags=["MAJOR"],
            financing_days_of_week=[]
        )
        
        cache.set_info("EUR_USD", info)
        
        # Should be available immediately
        assert cache.get_info("EUR_USD") == info
        
        # Wait for expiration
        import time
        time.sleep(0.1)
        
        # Should be expired
        assert cache.get_info("EUR_USD") is None
    
    def test_spread_cache(self):
        """Test spread caching"""
        cache = InstrumentCache(spread_ttl_seconds=5)
        
        # Create test spread
        spread = InstrumentSpread(
            instrument="EUR_USD",
            bid=Decimal("1.1000"),
            ask=Decimal("1.1002"),
            spread=Decimal("0.0002"),
            spread_pips=Decimal("2.0"),
            timestamp=datetime.utcnow(),
            liquidity=10,
            tradeable=True
        )
        
        # Set and get
        cache.set_spread("EUR_USD", spread)
        retrieved = cache.get_spread("EUR_USD")
        
        assert retrieved == spread
        assert "EUR_USD" in cache.spread_timestamps

class TestInstrumentSpread:
    """Test InstrumentSpread functionality"""
    
    def test_calculate_spread_eur_usd(self):
        """Test spread calculation for EUR/USD"""
        spread = InstrumentSpread.calculate_spread(
            bid=Decimal("1.1000"),
            ask=Decimal("1.1002"),
            pip_location=-4
        )
        
        assert spread.bid == Decimal("1.1000")
        assert spread.ask == Decimal("1.1002")
        assert spread.spread == Decimal("0.0002")
        assert spread.spread_pips == Decimal("2.0")
    
    def test_calculate_spread_usd_jpy(self):
        """Test spread calculation for USD/JPY"""
        spread = InstrumentSpread.calculate_spread(
            bid=Decimal("110.000"),
            ask=Decimal("110.025"),
            pip_location=-2
        )
        
        assert spread.spread == Decimal("0.025")
        assert spread.spread_pips == Decimal("2.5")
    
    def test_calculate_spread_gold(self):
        """Test spread calculation for Gold (XAU/USD)"""
        spread = InstrumentSpread.calculate_spread(
            bid=Decimal("1900.50"),
            ask=Decimal("1900.80"),
            pip_location=-1
        )
        
        assert spread.spread == Decimal("0.30")
        assert spread.spread_pips == Decimal("3.0")

class TestSpreadHistory:
    """Test SpreadHistory functionality"""
    
    def test_add_spread(self):
        """Test adding spread to history"""
        history = SpreadHistory(
            instrument="EUR_USD",
            timestamps=[],
            spreads=[],
            average_spread=Decimal("0"),
            min_spread=Decimal("0"),
            max_spread=Decimal("0"),
            current_spread=Decimal("0")
        )
        
        # Add first spread
        timestamp1 = datetime.utcnow()
        history.add_spread(Decimal("2.0"), timestamp1)
        
        assert len(history.spreads) == 1
        assert history.current_spread == Decimal("2.0")
        assert history.average_spread == Decimal("2.0")
        assert history.min_spread == Decimal("2.0")
        assert history.max_spread == Decimal("2.0")
        
        # Add second spread
        timestamp2 = datetime.utcnow()
        history.add_spread(Decimal("3.0"), timestamp2)
        
        assert len(history.spreads) == 2
        assert history.current_spread == Decimal("3.0")
        assert history.average_spread == Decimal("2.5")
        assert history.min_spread == Decimal("2.0")
        assert history.max_spread == Decimal("3.0")
    
    def test_spread_history_limit(self):
        """Test spread history size limit"""
        history = SpreadHistory(
            instrument="EUR_USD",
            timestamps=[],
            spreads=[],
            average_spread=Decimal("0"),
            min_spread=Decimal("0"),
            max_spread=Decimal("0"),
            current_spread=Decimal("0")
        )
        
        # Add more than 1000 spreads
        for i in range(1100):
            timestamp = datetime.utcnow() - timedelta(minutes=i)
            spread_value = Decimal(f"{i % 10 + 1}.0")
            history.add_spread(spread_value, timestamp)
        
        # Should be limited to 1000
        assert len(history.spreads) == 1000
        assert len(history.timestamps) == 1000

class TestInstrumentInfo:
    """Test InstrumentInfo functionality"""
    
    def test_calculate_pip_value_eur_usd(self):
        """Test pip value calculation for EUR/USD"""
        info = InstrumentInfo(
            name="EUR_USD",
            display_name="EUR/USD",
            type=InstrumentType.CURRENCY,
            pip_location=-4,
            display_precision=5,
            trade_units_precision=0,
            minimum_trade_size=Decimal("1"),
            maximum_trade_size=Decimal("100000000"),
            maximum_position_size=Decimal("100000000"),
            margin_rate=Decimal("0.02"),
            commission_rate=Decimal("0"),
            minimum_trailing_stop=None,
            maximum_trailing_stop=None,
            tags=["MAJOR"],
            financing_days_of_week=[]
        )
        
        # For 10,000 units at 1.1000 price
        pip_value = info.calculate_pip_value(Decimal("10000"), Decimal("1.1000"))
        
        # Pip size = 0.0001, so pip value = (10000 * 0.0001) / 1.1000
        expected = (Decimal("10000") * Decimal("0.0001")) / Decimal("1.1000")
        assert abs(pip_value - expected) < Decimal("0.01")
    
    def test_calculate_pip_value_usd_jpy(self):
        """Test pip value calculation for USD/JPY"""
        info = InstrumentInfo(
            name="USD_JPY",
            display_name="USD/JPY",
            type=InstrumentType.CURRENCY,
            pip_location=-2,
            display_precision=3,
            trade_units_precision=0,
            minimum_trade_size=Decimal("1"),
            maximum_trade_size=Decimal("100000000"),
            maximum_position_size=Decimal("100000000"),
            margin_rate=Decimal("0.02"),
            commission_rate=Decimal("0"),
            minimum_trailing_stop=None,
            maximum_trailing_stop=None,
            tags=["MAJOR"],
            financing_days_of_week=[]
        )
        
        # For 10,000 units at 110.00 price
        pip_value = info.calculate_pip_value(Decimal("10000"), Decimal("110.00"))
        
        # Pip size = 0.01, so pip value = (10000 * 0.01) / 110.00
        expected = (Decimal("10000") * Decimal("0.01")) / Decimal("110.00")
        assert abs(pip_value - expected) < Decimal("0.01")

class TestOandaInstrumentService:
    """Test OandaInstrumentService functionality"""
    
    @pytest.fixture
    def instrument_service(self):
        """Create test instrument service"""
        return OandaInstrumentService(
            api_key="test-api-key",
            account_id="test-account",
            base_url="https://api-test.oanda.com"
        )
    
    @pytest.fixture
    def mock_session(self):
        """Create mock aiohttp session"""
        session = AsyncMock(spec=aiohttp.ClientSession)
        session.closed = False
        return session
    
    def create_mock_instruments_response(self):
        """Create mock instruments API response"""
        return {
            "instruments": [
                {
                    "name": "EUR_USD",
                    "displayName": "EUR/USD",
                    "pipLocation": -4,
                    "displayPrecision": 5,
                    "tradeUnitsPrecision": 0,
                    "minimumTradeSize": "1",
                    "maximumOrderUnits": "100000000",
                    "maximumPositionSize": "100000000",
                    "marginRate": "0.02",
                    "commission": {"commission": "0"},
                    "minimumTrailingStopDistance": "5.0",
                    "maximumTrailingStopDistance": "10000.0",
                    "tags": ["MAJOR", "FOREX"],
                    "financing": {
                        "financingDaysOfWeek": ["MON", "TUE", "WED", "THU", "FRI"]
                    }
                },
                {
                    "name": "XAU_USD",
                    "displayName": "Gold/USD",
                    "pipLocation": -1,
                    "displayPrecision": 2,
                    "tradeUnitsPrecision": 0,
                    "minimumTradeSize": "1",
                    "marginRate": "0.05",
                    "tags": ["METAL"],
                    "financing": {"financingDaysOfWeek": []}
                }
            ]
        }
    
    def create_mock_pricing_response(self):
        """Create mock pricing API response"""
        return {
            "prices": [
                {
                    "instrument": "EUR_USD",
                    "tradeable": True,
                    "bids": [{"price": "1.10000", "liquidity": 10000}],
                    "asks": [{"price": "1.10020", "liquidity": 10000}]
                },
                {
                    "instrument": "GBP_USD",
                    "tradeable": True,
                    "bids": [{"price": "1.25000", "liquidity": 8000}],
                    "asks": [{"price": "1.25030", "liquidity": 8000}]
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_initialization(self, instrument_service):
        """Test instrument service initialization"""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            # Mock instruments fetch
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = self.create_mock_instruments_response()
            mock_session.get.return_value.__aenter__.return_value = mock_response
            
            await instrument_service.initialize()
            
            assert instrument_service.session is not None
            assert instrument_service.metrics['api_calls'] == 1  # Called fetch_all_instruments
    
    @pytest.mark.asyncio
    async def test_fetch_all_instruments(self, instrument_service, mock_session):
        """Test fetching all instruments"""
        instrument_service.session = mock_session
        
        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = self.create_mock_instruments_response()
        
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        # Test
        instruments = await instrument_service.fetch_all_instruments()
        
        # Assertions
        assert len(instruments) == 2
        
        # Check EUR/USD
        eur_usd = instruments[0]
        assert eur_usd.name == "EUR_USD"
        assert eur_usd.display_name == "EUR/USD"
        assert eur_usd.type == InstrumentType.CURRENCY
        assert eur_usd.pip_location == -4
        assert eur_usd.margin_rate == Decimal("0.02")
        assert "MAJOR" in eur_usd.tags
        
        # Check Gold
        gold = instruments[1]
        assert gold.name == "XAU_USD"
        assert gold.type == InstrumentType.METAL
        assert gold.pip_location == -1
        assert gold.margin_rate == Decimal("0.05")
        
        # Check caching
        cached_eur = instrument_service.cache.get_info("EUR_USD")
        assert cached_eur == eur_usd
        
        # Check metrics
        assert instrument_service.metrics['api_calls'] == 1
        assert instrument_service.metrics['last_update'] is not None
    
    @pytest.mark.asyncio
    async def test_get_current_prices(self, instrument_service, mock_session):
        """Test getting current prices"""
        instrument_service.session = mock_session
        
        # Setup instrument info in cache first
        eur_usd_info = InstrumentInfo(
            name="EUR_USD",
            display_name="EUR/USD",
            type=InstrumentType.CURRENCY,
            pip_location=-4,
            display_precision=5,
            trade_units_precision=0,
            minimum_trade_size=Decimal("1"),
            maximum_trade_size=Decimal("100000000"),
            maximum_position_size=Decimal("100000000"),
            margin_rate=Decimal("0.02"),
            commission_rate=Decimal("0"),
            minimum_trailing_stop=None,
            maximum_trailing_stop=None,
            tags=["MAJOR"],
            financing_days_of_week=[]
        )
        instrument_service.cache.set_info("EUR_USD", eur_usd_info)
        
        gbp_usd_info = InstrumentInfo(
            name="GBP_USD",
            display_name="GBP/USD",
            type=InstrumentType.CURRENCY,
            pip_location=-4,
            display_precision=5,
            trade_units_precision=0,
            minimum_trade_size=Decimal("1"),
            maximum_trade_size=Decimal("100000000"),
            maximum_position_size=Decimal("100000000"),
            margin_rate=Decimal("0.02"),
            commission_rate=Decimal("0"),
            minimum_trailing_stop=None,
            maximum_trailing_stop=None,
            tags=["MAJOR"],
            financing_days_of_week=[]
        )
        instrument_service.cache.set_info("GBP_USD", gbp_usd_info)
        
        # Mock pricing response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = self.create_mock_pricing_response()
        
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        # Test
        spreads = await instrument_service.get_current_prices(["EUR_USD", "GBP_USD"])
        
        # Assertions
        assert len(spreads) == 2
        
        # Check EUR/USD spread
        eur_spread = spreads["EUR_USD"]
        assert eur_spread.instrument == "EUR_USD"
        assert eur_spread.bid == Decimal("1.10000")
        assert eur_spread.ask == Decimal("1.10020")
        assert eur_spread.spread == Decimal("0.00020")
        assert eur_spread.spread_pips == Decimal("2.0")
        assert eur_spread.tradeable is True
        
        # Check GBP/USD spread
        gbp_spread = spreads["GBP_USD"]
        assert gbp_spread.instrument == "GBP_USD"
        assert gbp_spread.spread_pips == Decimal("3.0")
        
        # Check caching
        cached_eur = instrument_service.cache.get_spread("EUR_USD")
        assert cached_eur == eur_spread
        
        # Check spread history
        assert "EUR_USD" in instrument_service.spread_history
        assert "GBP_USD" in instrument_service.spread_history
    
    @pytest.mark.asyncio
    async def test_get_current_prices_with_cache(self, instrument_service, mock_session):
        """Test getting current prices with cache hits"""
        instrument_service.session = mock_session
        
        # Create cached spread
        cached_spread = InstrumentSpread(
            instrument="EUR_USD",
            bid=Decimal("1.10000"),
            ask=Decimal("1.10020"),
            spread=Decimal("0.00020"),
            spread_pips=Decimal("2.0"),
            timestamp=datetime.utcnow(),
            liquidity=10,
            tradeable=True
        )
        instrument_service.cache.set_spread("EUR_USD", cached_spread)
        
        # Test with cached data
        spreads = await instrument_service.get_current_prices(["EUR_USD"])
        
        # Should return cached data without API call
        assert len(spreads) == 1
        assert spreads["EUR_USD"] == cached_spread
        assert instrument_service.metrics['cache_hits'] == 1
        assert instrument_service.metrics['cache_misses'] == 0
        
        # No API call should be made
        mock_session.get.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_instruments_by_type(self, instrument_service, mock_session):
        """Test filtering instruments by type"""
        instrument_service.session = mock_session
        
        # Mock instruments response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = self.create_mock_instruments_response()
        
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        # Fetch all instruments first
        await instrument_service.fetch_all_instruments()
        
        # Test getting currency instruments
        currency_instruments = await instrument_service.get_instruments_by_type(InstrumentType.CURRENCY)
        assert len(currency_instruments) == 1
        assert currency_instruments[0].name == "EUR_USD"
        
        # Test getting metal instruments
        metal_instruments = await instrument_service.get_instruments_by_type(InstrumentType.METAL)
        assert len(metal_instruments) == 1
        assert metal_instruments[0].name == "XAU_USD"
    
    @pytest.mark.asyncio
    async def test_get_major_pairs(self, instrument_service, mock_session):
        """Test getting major pairs"""
        instrument_service.session = mock_session
        
        # Setup cached major pair
        eur_usd_info = InstrumentInfo(
            name="EUR_USD",
            display_name="EUR/USD",
            type=InstrumentType.CURRENCY,
            pip_location=-4,
            display_precision=5,
            trade_units_precision=0,
            minimum_trade_size=Decimal("1"),
            maximum_trade_size=Decimal("100000000"),
            maximum_position_size=Decimal("100000000"),
            margin_rate=Decimal("0.02"),
            commission_rate=Decimal("0"),
            minimum_trailing_stop=None,
            maximum_trailing_stop=None,
            tags=["MAJOR"],
            financing_days_of_week=[]
        )
        instrument_service.cache.set_info("EUR_USD", eur_usd_info)
        
        # Test
        major_pairs = await instrument_service.get_major_pairs()
        
        assert len(major_pairs) == 1
        assert major_pairs[0].name == "EUR_USD"
    
    @pytest.mark.asyncio
    async def test_is_tradeable(self, instrument_service, mock_session):
        """Test checking if instrument is tradeable"""
        instrument_service.session = mock_session
        
        # Create cached spread
        tradeable_spread = InstrumentSpread(
            instrument="EUR_USD",
            bid=Decimal("1.10000"),
            ask=Decimal("1.10020"),
            spread=Decimal("0.00020"),
            spread_pips=Decimal("2.0"),
            timestamp=datetime.utcnow(),
            liquidity=10,
            tradeable=True
        )
        instrument_service.cache.set_spread("EUR_USD", tradeable_spread)
        
        # Test
        is_tradeable = await instrument_service.is_tradeable("EUR_USD")
        assert is_tradeable is True
        
        # Test with non-tradeable instrument
        non_tradeable_spread = InstrumentSpread(
            instrument="GBP_USD",
            bid=Decimal("1.25000"),
            ask=Decimal("1.25030"),
            spread=Decimal("0.00030"),
            spread_pips=Decimal("3.0"),
            timestamp=datetime.utcnow(),
            liquidity=5,
            tradeable=False
        )
        instrument_service.cache.set_spread("GBP_USD", non_tradeable_spread)
        
        is_tradeable = await instrument_service.is_tradeable("GBP_USD")
        assert is_tradeable is False
    
    @pytest.mark.asyncio
    async def test_get_spread_summary(self, instrument_service):
        """Test getting spread summary"""
        # Add some spread history
        history1 = SpreadHistory(
            instrument="EUR_USD",
            timestamps=[datetime.utcnow()],
            spreads=[Decimal("2.0")],
            average_spread=Decimal("2.0"),
            min_spread=Decimal("2.0"),
            max_spread=Decimal("2.0"),
            current_spread=Decimal("2.0")
        )
        
        history2 = SpreadHistory(
            instrument="GBP_USD",
            timestamps=[datetime.utcnow()],
            spreads=[Decimal("3.0")],
            average_spread=Decimal("3.0"),
            min_spread=Decimal("3.0"),
            max_spread=Decimal("3.0"),
            current_spread=Decimal("3.0")
        )
        
        instrument_service.spread_history["EUR_USD"] = history1
        instrument_service.spread_history["GBP_USD"] = history2
        
        # Test
        summary = await instrument_service.get_spread_summary()
        
        assert summary['total_instruments'] == 2
        assert len(summary['instruments']) == 2
        
        # Check EUR_USD entry
        eur_entry = next(inst for inst in summary['instruments'] if inst['instrument'] == 'EUR_USD')
        assert eur_entry['current_spread'] == 2.0
        assert eur_entry['average_spread'] == 2.0
        assert eur_entry['samples'] == 1
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, instrument_service, mock_session):
        """Test API error handling"""
        instrument_service.session = mock_session
        
        # Mock API error
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.text.return_value = "Bad Request"
        
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        # Test
        with pytest.raises(Exception) as exc_info:
            await instrument_service.fetch_all_instruments()
        
        assert "API error 400" in str(exc_info.value)
        assert instrument_service.metrics['errors'] == 1
    
    @pytest.mark.asyncio
    async def test_close(self, instrument_service, mock_session):
        """Test instrument service cleanup"""
        instrument_service.session = mock_session
        
        await instrument_service.close()
        
        mock_session.close.assert_called_once()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])