"""
Pattern Day Trading (PDT) Monitoring System - Story 8.15

Monitors and enforces PDT rules including:
- Day trade detection and counting
- Account equity requirements ($25,000 minimum)
- PDT rule violations tracking
- Trading restrictions enforcement
- Margin call monitoring
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

logger = structlog.get_logger(__name__)


class PDTStatus(Enum):
    """PDT account status"""
    NON_PDT = "non_pdt"  # Not a pattern day trader
    PDT = "pdt"  # Pattern day trader
    PDT_PENDING = "pdt_pending"  # Close to PDT threshold
    PDT_RESTRICTED = "pdt_restricted"  # Trading restricted due to violations
    PDT_CALL = "pdt_call"  # In margin call


class TradeType(Enum):
    """Types of trades for PDT monitoring"""
    DAY_TRADE = "day_trade"
    OVERNIGHT = "overnight"
    SWING_TRADE = "swing_trade"


class ViolationType(Enum):
    """Types of PDT violations"""
    MINIMUM_EQUITY = "minimum_equity"  # Below $25,000
    DAY_TRADE_LIMIT = "day_trade_limit"  # Exceeded day trade limit
    MARGIN_CALL = "margin_call"  # Failed to meet margin call
    GOOD_FAITH = "good_faith"  # Good faith violation
    FREE_RIDING = "free_riding"  # Free riding violation


@dataclass
class DayTrade:
    """Represents a day trade"""
    trade_id: str
    account_id: str
    instrument: str
    open_time: datetime
    open_price: Decimal
    open_quantity: Decimal
    close_time: datetime
    close_price: Decimal
    close_quantity: Decimal
    profit_loss: Decimal
    trade_date: date
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PDTViolation:
    """Represents a PDT rule violation"""
    violation_id: str
    account_id: str
    violation_type: ViolationType
    violation_date: datetime
    description: str
    current_equity: Decimal
    required_equity: Decimal
    day_trade_count: int
    restriction_start: Optional[datetime] = None
    restriction_end: Optional[datetime] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccountPDTStatus:
    """PDT status for an account"""
    account_id: str
    status: PDTStatus
    current_equity: Decimal
    day_trades_rolling_5days: int
    day_trades_today: int
    total_day_trades_ytd: int
    last_pdt_reset: datetime
    is_margin_account: bool
    has_options_approval: bool
    violations: List[PDTViolation] = field(default_factory=list)
    restrictions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PDTAlert:
    """Alert for PDT-related events"""
    alert_id: str
    account_id: str
    alert_type: str
    severity: str  # 'info', 'warning', 'critical'
    message: str
    timestamp: datetime
    requires_action: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class PDTMonitoringSystem:
    """Main PDT monitoring system"""
    
    # PDT Rules Constants
    PDT_MINIMUM_EQUITY = Decimal('25000')
    DAY_TRADE_LIMIT_NON_PDT = 3  # 3 day trades in 5 business days for non-PDT
    ROLLING_WINDOW_DAYS = 5  # 5 business day rolling window
    PDT_CALL_DAYS = 5  # Days to meet margin call
    
    def __init__(self):
        self.account_statuses: Dict[str, AccountPDTStatus] = {}
        self.day_trades: Dict[str, List[DayTrade]] = defaultdict(list)
        self.violations: Dict[str, List[PDTViolation]] = defaultdict(list)
        self.alerts: Dict[str, List[PDTAlert]] = defaultdict(list)
        self.trade_tracker = DayTradeTracker()
        self.violation_monitor = ViolationMonitor()
        self.restriction_enforcer = RestrictionEnforcer()
        
    async def initialize(self):
        """Initialize PDT monitoring system"""
        logger.info("Initializing PDT monitoring system")
        await self.trade_tracker.initialize()
        await self.violation_monitor.initialize()
        await self.restriction_enforcer.initialize()
        
    async def update_account_status(self, account_id: str, equity: Decimal,
                                   is_margin: bool = True, has_options: bool = False):
        """Update account PDT status"""
        if account_id not in self.account_statuses:
            self.account_statuses[account_id] = AccountPDTStatus(
                account_id=account_id,
                status=PDTStatus.NON_PDT,
                current_equity=equity,
                day_trades_rolling_5days=0,
                day_trades_today=0,
                total_day_trades_ytd=0,
                last_pdt_reset=datetime.now(),
                is_margin_account=is_margin,
                has_options_approval=has_options
            )
        else:
            self.account_statuses[account_id].current_equity = equity
            self.account_statuses[account_id].is_margin_account = is_margin
            self.account_statuses[account_id].has_options_approval = has_options
        
        # Check PDT status
        await self._evaluate_pdt_status(account_id)
        
    async def record_trade(self, account_id: str, instrument: str,
                          open_time: datetime, open_price: Decimal, open_quantity: Decimal,
                          close_time: datetime, close_price: Decimal, close_quantity: Decimal):
        """Record a trade and check if it's a day trade"""
        # Check if it's a day trade (opened and closed same day)
        if open_time.date() == close_time.date():
            day_trade = DayTrade(
                trade_id=f"dt_{account_id}_{datetime.now().timestamp()}",
                account_id=account_id,
                instrument=instrument,
                open_time=open_time,
                open_price=open_price,
                open_quantity=open_quantity,
                close_time=close_time,
                close_price=close_price,
                close_quantity=close_quantity,
                profit_loss=(close_price - open_price) * min(open_quantity, close_quantity),
                trade_date=open_time.date()
            )
            
            self.day_trades[account_id].append(day_trade)
            
            # Update day trade counts
            await self._update_day_trade_counts(account_id)
            
            # Check for violations
            await self._check_pdt_violations(account_id)
            
            logger.info(f"Recorded day trade: {day_trade.trade_id}")
            
            return day_trade
        
        return None
        
    async def _update_day_trade_counts(self, account_id: str):
        """Update rolling day trade counts"""
        if account_id not in self.account_statuses:
            return
        
        status = self.account_statuses[account_id]
        today = date.today()
        
        # Count day trades today
        status.day_trades_today = len([
            dt for dt in self.day_trades[account_id]
            if dt.trade_date == today
        ])
        
        # Count day trades in rolling 5-day window
        five_days_ago = today - timedelta(days=self.ROLLING_WINDOW_DAYS)
        status.day_trades_rolling_5days = len([
            dt for dt in self.day_trades[account_id]
            if dt.trade_date > five_days_ago
        ])
        
        # Count total YTD
        year_start = date(today.year, 1, 1)
        status.total_day_trades_ytd = len([
            dt for dt in self.day_trades[account_id]
            if dt.trade_date >= year_start
        ])
        
    async def _evaluate_pdt_status(self, account_id: str):
        """Evaluate and update PDT status"""
        status = self.account_statuses[account_id]
        
        # Check if account is already marked as PDT
        if status.day_trades_rolling_5days > self.DAY_TRADE_LIMIT_NON_PDT:
            if status.status != PDTStatus.PDT:
                status.status = PDTStatus.PDT
                await self._create_alert(
                    account_id,
                    "PDT_DESIGNATION",
                    "critical",
                    f"Account designated as Pattern Day Trader. Minimum equity requirement: ${self.PDT_MINIMUM_EQUITY}"
                )
            
            # Check minimum equity for PDT accounts
            if status.current_equity < self.PDT_MINIMUM_EQUITY:
                if status.status != PDTStatus.PDT_CALL:
                    status.status = PDTStatus.PDT_CALL
                    await self._create_pdt_margin_call(account_id)
        
        # Check if approaching PDT limit
        elif status.day_trades_rolling_5days == self.DAY_TRADE_LIMIT_NON_PDT:
            status.status = PDTStatus.PDT_PENDING
            await self._create_alert(
                account_id,
                "PDT_WARNING",
                "warning",
                f"Warning: Account has made {status.day_trades_rolling_5days} day trades in 5 days. "
                f"One more will trigger PDT designation."
            )
        
        # Check for restrictions
        active_violations = [v for v in self.violations[account_id] if v.is_active]
        if active_violations:
            status.status = PDTStatus.PDT_RESTRICTED
            
    async def _check_pdt_violations(self, account_id: str):
        """Check for PDT rule violations"""
        status = self.account_statuses[account_id]
        
        # Check day trade limit for non-PDT accounts
        if status.status == PDTStatus.NON_PDT:
            if status.day_trades_rolling_5days > self.DAY_TRADE_LIMIT_NON_PDT:
                await self._create_violation(
                    account_id,
                    ViolationType.DAY_TRADE_LIMIT,
                    f"Exceeded day trade limit ({status.day_trades_rolling_5days} trades in 5 days)"
                )
        
        # Check minimum equity for PDT accounts
        elif status.status in [PDTStatus.PDT, PDTStatus.PDT_CALL]:
            if status.current_equity < self.PDT_MINIMUM_EQUITY:
                await self._create_violation(
                    account_id,
                    ViolationType.MINIMUM_EQUITY,
                    f"Account equity ${status.current_equity} below PDT minimum ${self.PDT_MINIMUM_EQUITY}"
                )
        
    async def _create_violation(self, account_id: str, violation_type: ViolationType,
                                description: str):
        """Create a PDT violation"""
        status = self.account_statuses[account_id]
        
        violation = PDTViolation(
            violation_id=f"viol_{account_id}_{datetime.now().timestamp()}",
            account_id=account_id,
            violation_type=violation_type,
            violation_date=datetime.now(),
            description=description,
            current_equity=status.current_equity,
            required_equity=self.PDT_MINIMUM_EQUITY if violation_type == ViolationType.MINIMUM_EQUITY else Decimal('0'),
            day_trade_count=status.day_trades_rolling_5days
        )
        
        # Set restriction periods based on violation type
        if violation_type == ViolationType.DAY_TRADE_LIMIT:
            violation.restriction_start = datetime.now()
            violation.restriction_end = datetime.now() + timedelta(days=90)  # 90-day restriction
        elif violation_type == ViolationType.MINIMUM_EQUITY:
            violation.restriction_start = datetime.now()
            violation.restriction_end = datetime.now() + timedelta(days=self.PDT_CALL_DAYS)
        
        self.violations[account_id].append(violation)
        status.violations.append(violation)
        
        logger.warning(f"PDT violation created: {violation.violation_id}")
        
        # Apply restrictions
        await self.restriction_enforcer.apply_restriction(account_id, violation)
        
    async def _create_pdt_margin_call(self, account_id: str):
        """Create PDT margin call"""
        status = self.account_statuses[account_id]
        deficit = self.PDT_MINIMUM_EQUITY - status.current_equity
        
        await self._create_alert(
            account_id,
            "PDT_MARGIN_CALL",
            "critical",
            f"PDT Margin Call: Account must deposit ${deficit} within {self.PDT_CALL_DAYS} business days. "
            f"Current equity: ${status.current_equity}, Required: ${self.PDT_MINIMUM_EQUITY}"
        )
        
    async def _create_alert(self, account_id: str, alert_type: str, severity: str,
                           message: str, requires_action: bool = True):
        """Create PDT alert"""
        alert = PDTAlert(
            alert_id=f"alert_{account_id}_{datetime.now().timestamp()}",
            account_id=account_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            timestamp=datetime.now(),
            requires_action=requires_action
        )
        
        self.alerts[account_id].append(alert)
        logger.info(f"PDT alert created: {alert.alert_id}")
        
        return alert
        
    async def check_trade_permission(self, account_id: str, is_day_trade: bool = False) -> Dict[str, Any]:
        """Check if account is allowed to make a trade"""
        if account_id not in self.account_statuses:
            return {'allowed': True, 'reason': 'Account not monitored'}
        
        status = self.account_statuses[account_id]
        
        # Check for active restrictions
        if status.status == PDTStatus.PDT_RESTRICTED:
            active_restrictions = [v for v in status.violations if v.is_active]
            if active_restrictions:
                return {
                    'allowed': False,
                    'reason': f"Account restricted due to: {active_restrictions[0].description}",
                    'restriction_end': active_restrictions[0].restriction_end
                }
        
        # Check day trade limits for non-PDT accounts
        if is_day_trade and status.status == PDTStatus.NON_PDT:
            if status.day_trades_rolling_5days >= self.DAY_TRADE_LIMIT_NON_PDT:
                return {
                    'allowed': False,
                    'reason': f"Day trade limit exceeded ({self.DAY_TRADE_LIMIT_NON_PDT} in 5 days)",
                    'current_count': status.day_trades_rolling_5days
                }
        
        # Check PDT margin call status
        if status.status == PDTStatus.PDT_CALL:
            return {
                'allowed': True,  # Can trade but with warning
                'warning': f"Account in PDT margin call. Must meet ${self.PDT_MINIMUM_EQUITY} requirement",
                'current_equity': float(status.current_equity)
            }
        
        return {'allowed': True, 'reason': 'Trade permitted'}
        
    async def get_pdt_summary(self, account_id: str) -> Dict[str, Any]:
        """Get PDT summary for an account"""
        if account_id not in self.account_statuses:
            return {}
        
        status = self.account_statuses[account_id]
        
        return {
            'account_id': account_id,
            'pdt_status': status.status.value,
            'current_equity': float(status.current_equity),
            'day_trades_today': status.day_trades_today,
            'day_trades_5day': status.day_trades_rolling_5days,
            'day_trades_ytd': status.total_day_trades_ytd,
            'is_pdt': status.status in [PDTStatus.PDT, PDTStatus.PDT_CALL, PDTStatus.PDT_RESTRICTED],
            'has_violations': len(status.violations) > 0,
            'active_violations': [
                {
                    'type': v.violation_type.value,
                    'date': v.violation_date.isoformat(),
                    'description': v.description
                }
                for v in status.violations if v.is_active
            ],
            'restrictions': status.restrictions,
            'can_day_trade': status.day_trades_rolling_5days < self.DAY_TRADE_LIMIT_NON_PDT
                            or status.status == PDTStatus.PDT and status.current_equity >= self.PDT_MINIMUM_EQUITY
        }
        
    async def reset_pdt_status(self, account_id: str):
        """Reset PDT status (administrative action)"""
        if account_id in self.account_statuses:
            status = self.account_statuses[account_id]
            status.status = PDTStatus.NON_PDT
            status.last_pdt_reset = datetime.now()
            
            # Deactivate violations
            for violation in status.violations:
                violation.is_active = False
            
            logger.info(f"PDT status reset for account: {account_id}")


class DayTradeTracker:
    """Tracks and identifies day trades"""
    
    def __init__(self):
        self.open_positions: Dict[str, List[Dict]] = defaultdict(list)
        self.closed_trades: Dict[str, List[DayTrade]] = defaultdict(list)
        
    async def initialize(self):
        """Initialize day trade tracker"""
        logger.info("Initialized day trade tracker")
        
    async def track_order(self, account_id: str, instrument: str,
                         order_type: str, quantity: Decimal, price: Decimal,
                         timestamp: datetime) -> Optional[DayTrade]:
        """Track an order and identify day trades"""
        if order_type == 'buy':
            # Add to open positions
            self.open_positions[account_id].append({
                'instrument': instrument,
                'quantity': quantity,
                'price': price,
                'timestamp': timestamp
            })
        elif order_type == 'sell':
            # Check for matching buy on same day
            today_opens = [
                pos for pos in self.open_positions[account_id]
                if pos['instrument'] == instrument
                and pos['timestamp'].date() == timestamp.date()
            ]
            
            if today_opens:
                # This is a day trade
                open_pos = today_opens[0]  # Use FIFO
                trade_quantity = min(quantity, open_pos['quantity'])
                
                day_trade = DayTrade(
                    trade_id=f"dt_{timestamp.timestamp()}",
                    account_id=account_id,
                    instrument=instrument,
                    open_time=open_pos['timestamp'],
                    open_price=open_pos['price'],
                    open_quantity=trade_quantity,
                    close_time=timestamp,
                    close_price=price,
                    close_quantity=trade_quantity,
                    profit_loss=(price - open_pos['price']) * trade_quantity,
                    trade_date=timestamp.date()
                )
                
                # Update or remove the open position
                open_pos['quantity'] -= trade_quantity
                if open_pos['quantity'] <= 0:
                    self.open_positions[account_id].remove(open_pos)
                
                self.closed_trades[account_id].append(day_trade)
                return day_trade
        
        return None


class ViolationMonitor:
    """Monitors PDT violations"""
    
    def __init__(self):
        self.active_violations: Dict[str, List[PDTViolation]] = defaultdict(list)
        
    async def initialize(self):
        """Initialize violation monitor"""
        logger.info("Initialized violation monitor")
        
    async def check_violations(self, account_id: str, status: AccountPDTStatus) -> List[PDTViolation]:
        """Check for PDT violations"""
        violations = []
        
        # Check various violation conditions
        if status.status == PDTStatus.PDT and status.current_equity < PDTMonitoringSystem.PDT_MINIMUM_EQUITY:
            violations.append(self._create_equity_violation(account_id, status))
        
        if status.status == PDTStatus.NON_PDT and status.day_trades_rolling_5days > PDTMonitoringSystem.DAY_TRADE_LIMIT_NON_PDT:
            violations.append(self._create_limit_violation(account_id, status))
        
        return violations
        
    def _create_equity_violation(self, account_id: str, status: AccountPDTStatus) -> PDTViolation:
        """Create minimum equity violation"""
        return PDTViolation(
            violation_id=f"eq_viol_{datetime.now().timestamp()}",
            account_id=account_id,
            violation_type=ViolationType.MINIMUM_EQUITY,
            violation_date=datetime.now(),
            description=f"PDT account below minimum equity requirement",
            current_equity=status.current_equity,
            required_equity=PDTMonitoringSystem.PDT_MINIMUM_EQUITY,
            day_trade_count=status.day_trades_rolling_5days
        )
        
    def _create_limit_violation(self, account_id: str, status: AccountPDTStatus) -> PDTViolation:
        """Create day trade limit violation"""
        return PDTViolation(
            violation_id=f"limit_viol_{datetime.now().timestamp()}",
            account_id=account_id,
            violation_type=ViolationType.DAY_TRADE_LIMIT,
            violation_date=datetime.now(),
            description=f"Exceeded day trade limit for non-PDT account",
            current_equity=status.current_equity,
            required_equity=Decimal('0'),
            day_trade_count=status.day_trades_rolling_5days
        )


class RestrictionEnforcer:
    """Enforces trading restrictions for PDT violations"""
    
    def __init__(self):
        self.restrictions: Dict[str, List[Dict]] = defaultdict(list)
        
    async def initialize(self):
        """Initialize restriction enforcer"""
        logger.info("Initialized restriction enforcer")
        
    async def apply_restriction(self, account_id: str, violation: PDTViolation):
        """Apply trading restrictions based on violation"""
        restriction = {
            'violation_id': violation.violation_id,
            'type': violation.violation_type.value,
            'start': violation.restriction_start,
            'end': violation.restriction_end,
            'description': self._get_restriction_description(violation)
        }
        
        self.restrictions[account_id].append(restriction)
        logger.info(f"Applied restriction for account {account_id}: {restriction['description']}")
        
    def _get_restriction_description(self, violation: PDTViolation) -> str:
        """Get restriction description based on violation type"""
        if violation.violation_type == ViolationType.DAY_TRADE_LIMIT:
            return "Day trading restricted for 90 days"
        elif violation.violation_type == ViolationType.MINIMUM_EQUITY:
            return f"Must deposit funds to meet ${PDTMonitoringSystem.PDT_MINIMUM_EQUITY} requirement"
        elif violation.violation_type == ViolationType.MARGIN_CALL:
            return "Trading restricted until margin call is met"
        else:
            return "Trading restricted due to violation"
            
    async def check_restriction(self, account_id: str) -> Optional[Dict]:
        """Check if account has active restrictions"""
        if account_id not in self.restrictions:
            return None
        
        active_restrictions = [
            r for r in self.restrictions[account_id]
            if r['end'] is None or r['end'] > datetime.now()
        ]
        
        if active_restrictions:
            return active_restrictions[0]
        
        return None