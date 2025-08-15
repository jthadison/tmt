"""
OANDA Instrument Information Service
Story 8.2 - Task 2: Implement instrument information service
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import json
from collections import defaultdict

logger = logging.getLogger(__name__)

class InstrumentType(Enum):
    CURRENCY = "CURRENCY"
    CFD = "CFD"
    METAL = "METAL"
    INDEX = "INDEX"
    COMMODITY = "COMMODITY"

class TradingStatus(Enum):
    TRADEABLE = "tradeable"
    HALTED = "halted"
    CLOSED = "closed"
    REDUCED_MARGIN = "reduced_margin"

@dataclass
class InstrumentInfo:
    """Complete instrument information"""
    name: str  # e.g., "EUR_USD"
    display_name: str  # e.g., "EUR/USD"
    type: InstrumentType
    pip_location: int  # -4 for most pairs, -2 for JPY pairs
    display_precision: int
    trade_units_precision: int
    minimum_trade_size: Decimal
    maximum_trade_size: Decimal
    maximum_position_size: Decimal
    margin_rate: Decimal
    commission_rate: Decimal
    minimum_trailing_stop: Optional[Decimal]
    maximum_trailing_stop: Optional[Decimal]
    tags: List[str]  # e.g., ["MAJOR", "FOREX"]
    financing_days_of_week: List[str]
    
    def calculate_pip_value(self, units: Decimal, price: Decimal) -> Decimal:
        """Calculate pip value for given units"""
        pip_size = Decimal(10) ** self.pip_location
        return (units * pip_size) / price

@dataclass
class InstrumentSpread:
    """Current spread information for an instrument"""
    instrument: str
    bid: Decimal
    ask: Decimal
    spread: Decimal
    spread_pips: Decimal
    timestamp: datetime
    liquidity: int  # 1-10 scale
    tradeable: bool
    
    @classmethod
    def calculate_spread(cls, bid: Decimal, ask: Decimal, pip_location: int) -> 'InstrumentSpread':
        """Calculate spread from bid/ask"""
        spread = ask - bid
        pip_size = Decimal(10) ** pip_location
        spread_pips = spread / pip_size
        
        return cls(
            instrument="",  # Will be set by caller
            bid=bid,
            ask=ask,
            spread=spread,
            spread_pips=spread_pips,
            timestamp=datetime.utcnow(),
            liquidity=10,  # Default, will be updated
            tradeable=True
        )

@dataclass
class SpreadHistory:
    """Historical spread data for analysis"""
    instrument: str
    timestamps: List[datetime]
    spreads: List[Decimal]
    average_spread: Decimal
    min_spread: Decimal
    max_spread: Decimal
    current_spread: Decimal
    
    def add_spread(self, spread: Decimal, timestamp: datetime):
        """Add new spread to history"""
        self.spreads.append(spread)
        self.timestamps.append(timestamp)
        
        # Keep only last 1000 entries
        if len(self.spreads) > 1000:
            self.spreads = self.spreads[-1000:]
            self.timestamps = self.timestamps[-1000:]
        
        # Recalculate statistics
        self.current_spread = spread
        self.average_spread = sum(self.spreads) / len(self.spreads)
        self.min_spread = min(self.spreads)
        self.max_spread = max(self.spreads)

class InstrumentCache:
    """Cache for instrument data with TTL"""
    
    def __init__(self, info_ttl_minutes: int = 60, spread_ttl_seconds: int = 5):
        self.info_ttl = timedelta(minutes=info_ttl_minutes)
        self.spread_ttl = timedelta(seconds=spread_ttl_seconds)
        self.instrument_info: Dict[str, InstrumentInfo] = {}
        self.instrument_spreads: Dict[str, InstrumentSpread] = {}
        self.info_timestamps: Dict[str, datetime] = {}
        self.spread_timestamps: Dict[str, datetime] = {}
    
    def get_info(self, instrument: str) -> Optional[InstrumentInfo]:
        """Get cached instrument info if not expired"""
        if instrument not in self.instrument_info:
            return None
        
        if datetime.utcnow() - self.info_timestamps[instrument] > self.info_ttl:
            del self.instrument_info[instrument]
            del self.info_timestamps[instrument]
            return None
        
        return self.instrument_info[instrument]
    
    def set_info(self, instrument: str, info: InstrumentInfo):
        """Set instrument info with timestamp"""
        self.instrument_info[instrument] = info
        self.info_timestamps[instrument] = datetime.utcnow()
    
    def get_spread(self, instrument: str) -> Optional[InstrumentSpread]:
        """Get cached spread if not expired"""
        if instrument not in self.instrument_spreads:
            return None
        
        if datetime.utcnow() - self.spread_timestamps[instrument] > self.spread_ttl:
            del self.instrument_spreads[instrument]
            del self.spread_timestamps[instrument]
            return None
        
        return self.instrument_spreads[instrument]
    
    def set_spread(self, instrument: str, spread: InstrumentSpread):
        """Set spread with timestamp"""
        self.instrument_spreads[instrument] = spread
        self.spread_timestamps[instrument] = datetime.utcnow()

class OandaInstrumentService:
    """Service for managing instrument information and spreads"""
    
    def __init__(self, api_key: str, account_id: str, base_url: str):
        self.api_key = api_key
        self.account_id = account_id
        self.base_url = base_url
        self.cache = InstrumentCache()
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Headers for OANDA API
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Accept-Datetime-Format': 'RFC3339'
        }
        
        # Spread history tracking
        self.spread_history: Dict[str, SpreadHistory] = {}
        
        # Instrument categories
        self.major_pairs = {'EUR_USD', 'GBP_USD', 'USD_JPY', 'USD_CHF', 'USD_CAD', 'AUD_USD', 'NZD_USD'}
        self.minor_pairs = set()
        self.exotic_pairs = set()
        self.metals = {'XAU_USD', 'XAG_USD'}
        self.indices = set()
        
        # Metrics
        self.metrics = {
            'api_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0,
            'last_update': None
        }
    
    async def initialize(self):
        """Initialize the instrument service"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout
            )
        
        # Load initial instrument list
        await self.fetch_all_instruments()
        logger.info("Instrument service initialized")
    
    async def close(self):
        """Close the instrument service"""
        if self.session and not self.session.closed:
            await self.session.close()
        logger.info("Instrument service closed")
    
    async def fetch_all_instruments(self) -> List[InstrumentInfo]:
        """
        Fetch all tradeable instruments
        
        Returns:
            List of InstrumentInfo objects
        """
        self.metrics['api_calls'] += 1
        
        try:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/instruments"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")
                
                data = await response.json()
                instruments = []
                
                for inst_data in data.get('instruments', []):
                    # Determine instrument type
                    inst_type = InstrumentType.CURRENCY  # Default
                    name = inst_data['name']
                    
                    if name.startswith('XAU') or name.startswith('XAG'):
                        inst_type = InstrumentType.METAL
                    elif '_' not in name:
                        inst_type = InstrumentType.INDEX
                    elif name.endswith('_USD') and name not in self.major_pairs and name not in self.metals:
                        inst_type = InstrumentType.CFD
                    
                    # Categorize pairs
                    if inst_type == InstrumentType.CURRENCY:
                        if name not in self.major_pairs:
                            if any(curr in name for curr in ['EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD']):
                                self.minor_pairs.add(name)
                            else:
                                self.exotic_pairs.add(name)
                    
                    instrument = InstrumentInfo(
                        name=inst_data['name'],
                        display_name=inst_data['displayName'],
                        type=inst_type,
                        pip_location=inst_data['pipLocation'],
                        display_precision=inst_data['displayPrecision'],
                        trade_units_precision=inst_data['tradeUnitsPrecision'],
                        minimum_trade_size=Decimal(inst_data['minimumTradeSize']),
                        maximum_trade_size=Decimal(inst_data.get('maximumOrderUnits', '100000000')),
                        maximum_position_size=Decimal(inst_data.get('maximumPositionSize', '100000000')),
                        margin_rate=Decimal(inst_data['marginRate']),
                        commission_rate=Decimal(inst_data.get('commission', {}).get('commission', '0')),
                        minimum_trailing_stop=Decimal(inst_data['minimumTrailingStopDistance']) if 'minimumTrailingStopDistance' in inst_data else None,
                        maximum_trailing_stop=Decimal(inst_data.get('maximumTrailingStopDistance', '0')) if 'maximumTrailingStopDistance' in inst_data else None,
                        tags=inst_data.get('tags', []),
                        financing_days_of_week=inst_data.get('financing', {}).get('financingDaysOfWeek', [])
                    )
                    
                    instruments.append(instrument)
                    self.cache.set_info(name, instrument)
                
                self.metrics['last_update'] = datetime.utcnow()
                return instruments
                
        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"Failed to fetch instruments: {e}")
            raise
    
    async def get_current_prices(self, instruments: List[str]) -> Dict[str, InstrumentSpread]:
        """
        Get current prices and spreads for instruments
        
        Args:
            instruments: List of instrument names
            
        Returns:
            Dict mapping instrument to InstrumentSpread
        """
        # Check cache first
        result = {}
        uncached = []
        
        for instrument in instruments:
            cached = self.cache.get_spread(instrument)
            if cached:
                result[instrument] = cached
                self.metrics['cache_hits'] += 1
            else:
                uncached.append(instrument)
                self.metrics['cache_misses'] += 1
        
        if not uncached:
            return result
        
        # Fetch uncached prices
        self.metrics['api_calls'] += 1
        
        try:
            # OANDA allows up to 200 instruments per request
            instrument_str = ','.join(uncached[:200])
            url = f"{self.base_url}/v3/accounts/{self.account_id}/pricing"
            params = {'instruments': instrument_str}
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")
                
                data = await response.json()
                
                for price_data in data.get('prices', []):
                    instrument = price_data['instrument']
                    
                    # Get instrument info for pip calculation
                    inst_info = self.cache.get_info(instrument)
                    if not inst_info:
                        # Fetch if not cached
                        await self.fetch_all_instruments()
                        inst_info = self.cache.get_info(instrument)
                    
                    if not inst_info:
                        continue
                    
                    # Calculate spread
                    bids = price_data.get('bids', [])
                    asks = price_data.get('asks', [])
                    
                    if bids and asks:
                        bid = Decimal(bids[0]['price'])
                        ask = Decimal(asks[0]['price'])
                        
                        spread = InstrumentSpread.calculate_spread(bid, ask, inst_info.pip_location)
                        spread.instrument = instrument
                        spread.tradeable = price_data.get('tradeable', True)
                        spread.liquidity = min(10, len(bids))  # Simple liquidity measure
                        
                        # Update cache
                        self.cache.set_spread(instrument, spread)
                        result[instrument] = spread
                        
                        # Update spread history
                        self._update_spread_history(instrument, spread.spread_pips)
                
                return result
                
        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"Failed to fetch prices: {e}")
            raise
    
    def _update_spread_history(self, instrument: str, spread_pips: Decimal):
        """Update spread history for an instrument"""
        if instrument not in self.spread_history:
            self.spread_history[instrument] = SpreadHistory(
                instrument=instrument,
                timestamps=[datetime.utcnow()],
                spreads=[spread_pips],
                average_spread=spread_pips,
                min_spread=spread_pips,
                max_spread=spread_pips,
                current_spread=spread_pips
            )
        else:
            self.spread_history[instrument].add_spread(spread_pips, datetime.utcnow())
    
    async def get_instruments_by_type(self, instrument_type: InstrumentType) -> List[InstrumentInfo]:
        """
        Get all instruments of a specific type
        
        Args:
            instrument_type: Type of instruments to fetch
            
        Returns:
            List of InstrumentInfo objects
        """
        all_instruments = list(self.cache.instrument_info.values())
        
        if not all_instruments:
            all_instruments = await self.fetch_all_instruments()
        
        return [inst for inst in all_instruments if inst.type == instrument_type]
    
    async def get_major_pairs(self) -> List[InstrumentInfo]:
        """Get all major currency pairs"""
        result = []
        for name in self.major_pairs:
            info = self.cache.get_info(name)
            if info:
                result.append(info)
        
        if not result:
            await self.fetch_all_instruments()
            for name in self.major_pairs:
                info = self.cache.get_info(name)
                if info:
                    result.append(info)
        
        return result
    
    async def get_spread_summary(self) -> Dict[str, Any]:
        """
        Get spread summary for all tracked instruments
        
        Returns:
            Dict with spread statistics
        """
        summary = {
            'total_instruments': len(self.spread_history),
            'instruments': []
        }
        
        for instrument, history in self.spread_history.items():
            summary['instruments'].append({
                'instrument': instrument,
                'current_spread': float(history.current_spread),
                'average_spread': float(history.average_spread),
                'min_spread': float(history.min_spread),
                'max_spread': float(history.max_spread),
                'samples': len(history.spreads)
            })
        
        return summary
    
    async def is_tradeable(self, instrument: str) -> bool:
        """
        Check if an instrument is currently tradeable
        
        Args:
            instrument: Instrument name
            
        Returns:
            True if tradeable
        """
        spread = self.cache.get_spread(instrument)
        if not spread:
            prices = await self.get_current_prices([instrument])
            spread = prices.get(instrument)
        
        return spread.tradeable if spread else False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics"""
        return self.metrics.copy()