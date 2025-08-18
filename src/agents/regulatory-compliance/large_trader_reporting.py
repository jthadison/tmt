"""
Large Trader Reporting System - Story 8.15

Monitors and reports on large trader thresholds including:
- Volume threshold tracking
- Large trader identification (LTID)
- SEC Form 13H filing
- Daily trading volume monitoring
- Position aggregation across accounts
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import structlog
from collections import defaultdict
import json

logger = structlog.get_logger(__name__)


class ThresholdType(Enum):
    """Types of large trader thresholds"""
    DAILY_VOLUME = "daily_volume"  # $20 million per day
    MONTHLY_VOLUME = "monthly_volume"  # $200 million per month
    QUARTERLY_VOLUME = "quarterly_volume"  # Quarterly reporting
    POSITION_SIZE = "position_size"  # Large position thresholds


class LTIDStatus(Enum):
    """Large Trader ID status"""
    NOT_REQUIRED = "not_required"
    PENDING_APPLICATION = "pending_application"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class FilingStatus(Enum):
    """Filing status for reports"""
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    FILED = "filed"
    LATE = "late"
    AMENDED = "amended"


@dataclass
class TradingVolume:
    """Trading volume for monitoring"""
    account_id: str
    date: date
    instrument: str
    volume_shares: Decimal
    volume_dollars: Decimal
    transaction_count: int
    market_value: Decimal
    side: str  # 'buy', 'sell', 'both'
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LargeTraderRecord:
    """Record for large trader monitoring"""
    ltid: Optional[str]
    entity_name: str
    entity_type: str  # 'individual', 'corporation', 'partnership', etc.
    identification_number: str  # EIN, SSN, etc.
    account_ids: Set[str]
    registration_date: Optional[datetime]
    status: LTIDStatus
    daily_threshold: Decimal
    monthly_threshold: Decimal
    current_daily_volume: Decimal = Decimal('0')
    current_monthly_volume: Decimal = Decimal('0')
    ytd_volume: Decimal = Decimal('0')
    last_filing_date: Optional[datetime] = None
    next_filing_due: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThresholdBreach:
    """Record of threshold breach"""
    breach_id: str
    ltid: Optional[str]
    account_ids: Set[str]
    threshold_type: ThresholdType
    breach_date: datetime
    threshold_value: Decimal
    actual_value: Decimal
    excess_amount: Decimal
    instruments_involved: List[str]
    requires_filing: bool
    filing_deadline: Optional[datetime] = None
    is_resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Form13H:
    """SEC Form 13H data"""
    filing_id: str
    ltid: str
    reporting_period_start: date
    reporting_period_end: date
    filing_date: datetime
    entity_information: Dict[str, Any]
    account_information: List[Dict[str, Any]]
    trading_activity_summary: Dict[str, Any]
    large_positions: List[Dict[str, Any]]
    status: FilingStatus
    metadata: Dict[str, Any] = field(default_factory=dict)


class LargeTraderReportingSystem:
    """Main large trader reporting system"""
    
    # SEC Large Trader Thresholds
    DAILY_VOLUME_THRESHOLD = Decimal('20000000')  # $20 million
    MONTHLY_VOLUME_THRESHOLD = Decimal('200000000')  # $200 million
    POSITION_THRESHOLD = Decimal('200000000')  # $200 million position value
    
    # Filing deadlines
    FORM_13H_FILING_DAYS = 45  # Days after end of calendar quarter
    DAILY_FILING_DAYS = 1  # T+1 for daily filings when required
    
    def __init__(self):
        self.large_traders: Dict[str, LargeTraderRecord] = {}
        self.trading_volumes: Dict[str, List[TradingVolume]] = defaultdict(list)
        self.threshold_breaches: Dict[str, List[ThresholdBreach]] = defaultdict(list)
        self.form_13h_filings: Dict[str, List[Form13H]] = defaultdict(list)
        self.volume_aggregator = VolumeAggregator()
        self.threshold_monitor = ThresholdMonitor()
        self.filing_generator = FilingGenerator()
        
    async def initialize(self):
        """Initialize large trader reporting system"""
        logger.info("Initializing large trader reporting system")
        await self.volume_aggregator.initialize()
        await self.threshold_monitor.initialize()
        await self.filing_generator.initialize()
        
    async def register_large_trader(self, entity_name: str, entity_type: str,
                                   identification_number: str, account_ids: Set[str],
                                   ltid: Optional[str] = None) -> LargeTraderRecord:
        """Register a large trader"""
        trader_key = identification_number
        
        trader = LargeTraderRecord(
            ltid=ltid,
            entity_name=entity_name,
            entity_type=entity_type,
            identification_number=identification_number,
            account_ids=account_ids,
            registration_date=datetime.now() if ltid else None,
            status=LTIDStatus.ACTIVE if ltid else LTIDStatus.NOT_REQUIRED,
            daily_threshold=self.DAILY_VOLUME_THRESHOLD,
            monthly_threshold=self.MONTHLY_VOLUME_THRESHOLD
        )
        
        self.large_traders[trader_key] = trader
        
        logger.info(f"Registered large trader: {entity_name} (LTID: {ltid})")
        return trader
        
    async def record_trading_volume(self, account_id: str, trade_date: date,
                                   instrument: str, volume_shares: Decimal,
                                   volume_dollars: Decimal, side: str):
        """Record trading volume for monitoring"""
        trading_volume = TradingVolume(
            account_id=account_id,
            date=trade_date,
            instrument=instrument,
            volume_shares=volume_shares,
            volume_dollars=volume_dollars,
            transaction_count=1,
            market_value=volume_dollars,
            side=side
        )
        
        self.trading_volumes[account_id].append(trading_volume)
        
        # Aggregate volumes across related accounts
        await self.volume_aggregator.aggregate_volumes(account_id, trading_volume)
        
        # Check thresholds
        await self.threshold_monitor.check_thresholds(account_id, trading_volume)
        
    async def check_large_trader_thresholds(self, identification_number: str) -> Dict[str, Any]:
        """Check if entity meets large trader thresholds"""
        if identification_number not in self.large_traders:
            return {'requires_ltid': False, 'reason': 'Not registered'}
        
        trader = self.large_traders[identification_number]
        
        # Aggregate volumes across all accounts
        daily_volume = await self._calculate_daily_volume(trader.account_ids)
        monthly_volume = await self._calculate_monthly_volume(trader.account_ids)
        
        trader.current_daily_volume = daily_volume
        trader.current_monthly_volume = monthly_volume
        
        # Check thresholds
        exceeds_daily = daily_volume >= self.DAILY_VOLUME_THRESHOLD
        exceeds_monthly = monthly_volume >= self.MONTHLY_VOLUME_THRESHOLD
        
        requires_ltid = exceeds_daily or exceeds_monthly
        
        if requires_ltid and trader.status == LTIDStatus.NOT_REQUIRED:
            trader.status = LTIDStatus.PENDING_APPLICATION
            await self._create_threshold_breach(
                trader, ThresholdType.DAILY_VOLUME if exceeds_daily else ThresholdType.MONTHLY_VOLUME,
                daily_volume if exceeds_daily else monthly_volume
            )
        
        return {
            'requires_ltid': requires_ltid,
            'exceeds_daily': exceeds_daily,
            'exceeds_monthly': exceeds_monthly,
            'daily_volume': float(daily_volume),
            'monthly_volume': float(monthly_volume),
            'daily_threshold': float(self.DAILY_VOLUME_THRESHOLD),
            'monthly_threshold': float(self.MONTHLY_VOLUME_THRESHOLD),
            'current_status': trader.status.value
        }
        
    async def _calculate_daily_volume(self, account_ids: Set[str]) -> Decimal:
        """Calculate daily trading volume across accounts"""
        today = date.today()
        total_volume = Decimal('0')
        
        for account_id in account_ids:
            today_volumes = [
                tv for tv in self.trading_volumes[account_id]
                if tv.date == today
            ]
            total_volume += sum(tv.volume_dollars for tv in today_volumes)
        
        return total_volume
        
    async def _calculate_monthly_volume(self, account_ids: Set[str]) -> Decimal:
        """Calculate monthly trading volume across accounts"""
        today = date.today()
        month_start = date(today.year, today.month, 1)
        total_volume = Decimal('0')
        
        for account_id in account_ids:
            month_volumes = [
                tv for tv in self.trading_volumes[account_id]
                if tv.date >= month_start
            ]
            total_volume += sum(tv.volume_dollars for tv in month_volumes)
        
        return total_volume
        
    async def _create_threshold_breach(self, trader: LargeTraderRecord,
                                      threshold_type: ThresholdType, actual_value: Decimal):
        """Create threshold breach record"""
        threshold_value = (self.DAILY_VOLUME_THRESHOLD if threshold_type == ThresholdType.DAILY_VOLUME
                          else self.MONTHLY_VOLUME_THRESHOLD)
        
        breach = ThresholdBreach(
            breach_id=f"breach_{trader.identification_number}_{datetime.now().timestamp()}",
            ltid=trader.ltid,
            account_ids=trader.account_ids,
            threshold_type=threshold_type,
            breach_date=datetime.now(),
            threshold_value=threshold_value,
            actual_value=actual_value,
            excess_amount=actual_value - threshold_value,
            instruments_involved=[],  # Would be populated with actual instruments
            requires_filing=True,
            filing_deadline=datetime.now() + timedelta(days=self.FORM_13H_FILING_DAYS)
        )
        
        self.threshold_breaches[trader.identification_number].append(breach)
        
        logger.warning(f"Large trader threshold breach: {breach.breach_id}")
        
    async def generate_form_13h(self, identification_number: str,
                               reporting_period_start: date,
                               reporting_period_end: date) -> Form13H:
        """Generate SEC Form 13H filing"""
        if identification_number not in self.large_traders:
            raise ValueError(f"Large trader not found: {identification_number}")
        
        trader = self.large_traders[identification_number]
        
        # Aggregate trading activity for the period
        trading_summary = await self._aggregate_trading_activity(
            trader.account_ids, reporting_period_start, reporting_period_end
        )
        
        # Get large positions
        large_positions = await self._identify_large_positions(
            trader.account_ids, reporting_period_end
        )
        
        form_13h = Form13H(
            filing_id=f"13H_{trader.ltid}_{reporting_period_end.strftime('%Y%m%d')}",
            ltid=trader.ltid or 'PENDING',
            reporting_period_start=reporting_period_start,
            reporting_period_end=reporting_period_end,
            filing_date=datetime.now(),
            entity_information={
                'name': trader.entity_name,
                'type': trader.entity_type,
                'identification_number': trader.identification_number,
                'ltid': trader.ltid
            },
            account_information=[
                {
                    'account_id': account_id,
                    'broker': 'Trading Platform',  # Would get from account data
                    'account_type': 'margin'  # Would get from account data
                }
                for account_id in trader.account_ids
            ],
            trading_activity_summary=trading_summary,
            large_positions=large_positions,
            status=FilingStatus.PENDING
        )
        
        self.form_13h_filings[identification_number].append(form_13h)
        
        logger.info(f"Generated Form 13H: {form_13h.filing_id}")
        return form_13h
        
    async def _aggregate_trading_activity(self, account_ids: Set[str],
                                         start_date: date, end_date: date) -> Dict[str, Any]:
        """Aggregate trading activity for reporting period"""
        total_volume = Decimal('0')
        total_transactions = 0
        instruments = set()
        
        for account_id in account_ids:
            period_volumes = [
                tv for tv in self.trading_volumes[account_id]
                if start_date <= tv.date <= end_date
            ]
            
            for tv in period_volumes:
                total_volume += tv.volume_dollars
                total_transactions += tv.transaction_count
                instruments.add(tv.instrument)
        
        return {
            'total_volume_dollars': float(total_volume),
            'total_transactions': total_transactions,
            'unique_instruments': len(instruments),
            'instruments': list(instruments),
            'period_start': start_date.isoformat(),
            'period_end': end_date.isoformat()
        }
        
    async def _identify_large_positions(self, account_ids: Set[str],
                                       as_of_date: date) -> List[Dict[str, Any]]:
        """Identify large positions for reporting"""
        # This would integrate with position management system
        # For now, return placeholder data
        return [
            {
                'instrument': 'AAPL',
                'position_value': 250000000.0,
                'shares': 1000000,
                'percentage_of_class': 0.5
            }
        ]
        
    async def check_filing_requirements(self, identification_number: str) -> Dict[str, Any]:
        """Check filing requirements for a large trader"""
        if identification_number not in self.large_traders:
            return {'filing_required': False}
        
        trader = self.large_traders[identification_number]
        
        # Check for outstanding breaches
        outstanding_breaches = [
            b for b in self.threshold_breaches[identification_number]
            if b.requires_filing and not b.is_resolved
        ]
        
        # Check quarterly filing requirements
        today = date.today()
        last_quarter_end = self._get_last_quarter_end(today)
        filing_due = last_quarter_end + timedelta(days=self.FORM_13H_FILING_DAYS)
        
        recent_filings = [
            f for f in self.form_13h_filings[identification_number]
            if f.reporting_period_end >= last_quarter_end
        ]
        
        quarterly_filing_required = (trader.status == LTIDStatus.ACTIVE and
                                   not recent_filings and
                                   today <= filing_due)
        
        return {
            'filing_required': len(outstanding_breaches) > 0 or quarterly_filing_required,
            'quarterly_filing_due': quarterly_filing_required,
            'quarterly_deadline': filing_due.isoformat() if quarterly_filing_required else None,
            'outstanding_breaches': len(outstanding_breaches),
            'breach_details': [
                {
                    'breach_id': b.breach_id,
                    'type': b.threshold_type.value,
                    'deadline': b.filing_deadline.isoformat() if b.filing_deadline else None
                }
                for b in outstanding_breaches
            ]
        }
        
    def _get_last_quarter_end(self, current_date: date) -> date:
        """Get the last quarter end date"""
        year = current_date.year
        month = current_date.month
        
        if month <= 3:
            return date(year - 1, 12, 31)
        elif month <= 6:
            return date(year, 3, 31)
        elif month <= 9:
            return date(year, 6, 30)
        else:
            return date(year, 9, 30)
            
    async def get_large_trader_summary(self, identification_number: str) -> Dict[str, Any]:
        """Get summary for a large trader"""
        if identification_number not in self.large_traders:
            return {}
        
        trader = self.large_traders[identification_number]
        
        return {
            'ltid': trader.ltid,
            'entity_name': trader.entity_name,
            'status': trader.status.value,
            'account_count': len(trader.account_ids),
            'daily_volume': float(trader.current_daily_volume),
            'monthly_volume': float(trader.current_monthly_volume),
            'ytd_volume': float(trader.ytd_volume),
            'exceeds_thresholds': (trader.current_daily_volume >= self.DAILY_VOLUME_THRESHOLD or
                                 trader.current_monthly_volume >= self.MONTHLY_VOLUME_THRESHOLD),
            'threshold_breaches': len(self.threshold_breaches[identification_number]),
            'form_13h_filings': len(self.form_13h_filings[identification_number]),
            'next_filing_due': trader.next_filing_due.isoformat() if trader.next_filing_due else None
        }


class VolumeAggregator:
    """Aggregates trading volumes across accounts"""
    
    def __init__(self):
        self.daily_aggregates: Dict[str, Dict[date, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
        self.monthly_aggregates: Dict[str, Dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
        
    async def initialize(self):
        """Initialize volume aggregator"""
        logger.info("Initialized volume aggregator")
        
    async def aggregate_volumes(self, account_id: str, volume: TradingVolume):
        """Aggregate volumes for an account"""
        # Daily aggregation
        self.daily_aggregates[account_id][volume.date] += volume.volume_dollars
        
        # Monthly aggregation
        month_key = f"{volume.date.year}-{volume.date.month:02d}"
        self.monthly_aggregates[account_id][month_key] += volume.volume_dollars
        
    async def get_aggregated_volume(self, account_ids: Set[str], period: str) -> Decimal:
        """Get aggregated volume across accounts for a period"""
        total_volume = Decimal('0')
        
        if period == 'daily':
            today = date.today()
            for account_id in account_ids:
                total_volume += self.daily_aggregates[account_id][today]
        elif period == 'monthly':
            today = date.today()
            month_key = f"{today.year}-{today.month:02d}"
            for account_id in account_ids:
                total_volume += self.monthly_aggregates[account_id][month_key]
        
        return total_volume


class ThresholdMonitor:
    """Monitors large trader thresholds"""
    
    def __init__(self):
        self.threshold_checks: Dict[str, List[Dict]] = defaultdict(list)
        
    async def initialize(self):
        """Initialize threshold monitor"""
        logger.info("Initialized threshold monitor")
        
    async def check_thresholds(self, account_id: str, volume: TradingVolume):
        """Check if trading volume triggers thresholds"""
        # This would check against registered large traders
        # and create alerts when thresholds are approached or breached
        
        check_result = {
            'account_id': account_id,
            'date': volume.date,
            'volume': volume.volume_dollars,
            'threshold_approached': volume.volume_dollars >= LargeTraderReportingSystem.DAILY_VOLUME_THRESHOLD * Decimal('0.8'),
            'threshold_breached': volume.volume_dollars >= LargeTraderReportingSystem.DAILY_VOLUME_THRESHOLD,
            'timestamp': datetime.now()
        }
        
        self.threshold_checks[account_id].append(check_result)
        
        if check_result['threshold_breached']:
            logger.warning(f"Large trader threshold breached for account {account_id}")


class FilingGenerator:
    """Generates regulatory filings"""
    
    def __init__(self):
        self.filing_templates: Dict[str, str] = {}
        
    async def initialize(self):
        """Initialize filing generator"""
        logger.info("Initialized filing generator")
        
    async def generate_form_13h_xml(self, form_13h: Form13H) -> str:
        """Generate Form 13H in XML format"""
        # This would generate the actual SEC XML format
        # For now, return JSON representation
        form_data = {
            'filing_id': form_13h.filing_id,
            'ltid': form_13h.ltid,
            'reporting_period': {
                'start': form_13h.reporting_period_start.isoformat(),
                'end': form_13h.reporting_period_end.isoformat()
            },
            'entity_information': form_13h.entity_information,
            'account_information': form_13h.account_information,
            'trading_activity': form_13h.trading_activity_summary,
            'large_positions': form_13h.large_positions
        }
        
        return json.dumps(form_data, indent=2)
        
    async def validate_filing(self, form_13h: Form13H) -> Dict[str, Any]:
        """Validate a Form 13H filing"""
        errors = []
        warnings = []
        
        # Basic validation
        if not form_13h.ltid or form_13h.ltid == 'PENDING':
            errors.append("LTID is required for filing")
            
        if not form_13h.entity_information.get('name'):
            errors.append("Entity name is required")
            
        if not form_13h.account_information:
            errors.append("At least one account must be reported")
            
        # Data validation
        trading_activity = form_13h.trading_activity_summary
        if trading_activity.get('total_volume_dollars', 0) < 20000000:
            warnings.append("Trading volume below large trader threshold")
            
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'validation_date': datetime.now().isoformat()
        }