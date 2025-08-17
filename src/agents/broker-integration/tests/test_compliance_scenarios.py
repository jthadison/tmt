"""
Compliance Test Scenarios for Broker Integration
Story 8.12 - Task 5: Create compliance test scenarios (AC: 6)
"""
import pytest
import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

# Test imports
import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from broker_adapter import (
    BrokerAdapter, UnifiedOrder, UnifiedPosition, UnifiedAccountSummary,
    OrderType, OrderSide, OrderState, PositionSide, TimeInForce,
    BrokerCapability, PriceTick, OrderResult
)
from unified_errors import (
    StandardBrokerError, StandardErrorCode, ErrorSeverity, ErrorCategory
)

logger = logging.getLogger(__name__)


class ComplianceRule(Enum):
    """Compliance rules to enforce"""
    FIFO_ENFORCEMENT = "fifo_enforcement"
    ANTI_HEDGING = "anti_hedging"
    LEVERAGE_LIMITS = "leverage_limits"
    PDT_RULE = "pattern_day_trader_rule"
    WASH_SALE_RULE = "wash_sale_rule"
    POSITION_LIMITS = "position_limits"
    ACCOUNT_BALANCE_MINIMUM = "account_balance_minimum"
    MARGIN_REQUIREMENTS = "margin_requirements"
    REGULATORY_RESTRICTIONS = "regulatory_restrictions"


class ComplianceEngine:
    """Compliance validation engine for testing"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.violations = []
        self.positions = {}  # instrument -> list of positions
        self.orders_history = []
        self.account_balance = Decimal('10000.00')
        self.used_margin = Decimal('0.00')
        self.day_trades_count = 0
        self.account_type = self.config.get('account_type', 'standard')
        
        # Compliance settings
        self.fifo_enabled = self.config.get('fifo_enabled', True)
        self.hedging_allowed = self.config.get('hedging_allowed', False)
        self.max_leverage = self.config.get('max_leverage', 50)
        self.min_account_balance = self.config.get('min_account_balance', Decimal('2000.00'))
        self.pdt_threshold = self.config.get('pdt_threshold', 25000)  # $25k for PDT
        
    def validate_order(self, order: UnifiedOrder, account: UnifiedAccountSummary = None) -> List[str]:
        """Validate order against compliance rules"""
        violations = []
        
        # FIFO compliance check
        if self.fifo_enabled:
            fifo_violations = self._check_fifo_compliance(order)
            violations.extend(fifo_violations)
            
        # Anti-hedging check
        if not self.hedging_allowed:
            hedging_violations = self._check_anti_hedging(order)
            violations.extend(hedging_violations)
            
        # Leverage limits check
        leverage_violations = self._check_leverage_limits(order, account)
        violations.extend(leverage_violations)
        
        # Margin requirements check
        margin_violations = self._check_margin_requirements(order, account)
        violations.extend(margin_violations)
        
        # Position limits check
        position_violations = self._check_position_limits(order)
        violations.extend(position_violations)
        
        # Pattern Day Trader rule check
        pdt_violations = self._check_pdt_rule(order, account)
        violations.extend(pdt_violations)
        
        return violations
        
    def _check_fifo_compliance(self, order: UnifiedOrder) -> List[str]:
        """Check FIFO compliance for closing orders"""
        violations = []
        
        if order.side == OrderSide.SELL and order.instrument in self.positions:
            positions = self.positions[order.instrument]
            
            # For FIFO, must close oldest position first
            if positions:
                oldest_position = min(positions, key=lambda p: p.creation_time)
                
                # In real implementation, would check if this order closes the oldest position
                # For testing purposes, we'll simulate this check
                if len(positions) > 1:
                    violations.append(f"FIFO violation: Must close oldest position first for {order.instrument}")
                    
        return violations
        
    def _check_anti_hedging(self, order: UnifiedOrder) -> List[str]:
        """Check anti-hedging compliance"""
        violations = []
        
        if order.instrument in self.positions:
            existing_positions = self.positions[order.instrument]
            
            for position in existing_positions:
                # Check if new order would create a hedge
                if ((order.side == OrderSide.BUY and position.side == PositionSide.SHORT) or
                    (order.side == OrderSide.SELL and position.side == PositionSide.LONG)):
                    violations.append(f"Anti-hedging violation: Cannot hedge existing {position.side.value} position in {order.instrument}")
                    
        return violations
        
    def _check_leverage_limits(self, order: UnifiedOrder, account: UnifiedAccountSummary = None) -> List[str]:
        """Check leverage limits"""
        violations = []
        
        if account:
            # Calculate position value
            estimated_price = Decimal('1.1000')  # Mock price
            position_value = order.units * estimated_price
            
            # Calculate leverage
            available_balance = account.balance - self.used_margin
            if available_balance > 0:
                leverage = position_value / available_balance
                
                if leverage > self.max_leverage:
                    violations.append(f"Leverage violation: Calculated leverage {leverage:.2f} exceeds maximum {self.max_leverage}")
                    
        return violations
        
    def _check_margin_requirements(self, order: UnifiedOrder, account: UnifiedAccountSummary = None) -> List[str]:
        """Check margin requirements"""
        violations = []
        
        if account:
            # Calculate required margin (simplified)
            estimated_price = Decimal('1.1000')
            position_value = order.units * estimated_price
            required_margin = position_value * Decimal('0.02')  # 2% margin requirement
            
            if account.available_margin < required_margin:
                violations.append(f"Insufficient margin: Required {required_margin}, available {account.available_margin}")
                
        return violations
        
    def _check_position_limits(self, order: UnifiedOrder) -> List[str]:
        """Check position size limits"""
        violations = []
        
        max_position_size = self.config.get('max_position_size', {})
        instrument_limit = max_position_size.get(order.instrument, Decimal('10000000'))
        
        # Calculate total position size after this order
        current_size = Decimal('0')
        if order.instrument in self.positions:
            current_size = sum(pos.units for pos in self.positions[order.instrument])
            
        new_total = current_size + order.units
        
        if new_total > instrument_limit:
            violations.append(f"Position limit violation: Total position {new_total} exceeds limit {instrument_limit} for {order.instrument}")
            
        return violations
        
    def _check_pdt_rule(self, order: UnifiedOrder, account: UnifiedAccountSummary = None) -> List[str]:
        """Check Pattern Day Trader rule"""
        violations = []
        
        if account and account.balance < self.pdt_threshold:
            # Check if this would be a day trade
            today = datetime.now(timezone.utc).date()
            
            # Count day trades today
            day_trades_today = len([
                o for o in self.orders_history 
                if o.creation_time.date() == today and self._is_day_trade(o)
            ])
            
            if day_trades_today >= 3:  # PDT rule: max 3 day trades in 5 business days
                violations.append(f"PDT violation: Account balance ${account.balance} below ${self.pdt_threshold} threshold, day trade limit exceeded")
                
        return violations
        
    def _is_day_trade(self, order: UnifiedOrder) -> bool:
        """Check if order constitutes a day trade"""
        # Simplified day trade detection
        return order.order_type == OrderType.MARKET
        
    def add_position(self, position: UnifiedPosition):
        """Add position to tracking"""
        if position.instrument not in self.positions:
            self.positions[position.instrument] = []
        self.positions[position.instrument].append(position)
        
    def remove_position(self, instrument: str, position_id: str):
        """Remove position from tracking"""
        if instrument in self.positions:
            self.positions[instrument] = [
                p for p in self.positions[instrument] 
                if p.position_id != position_id
            ]
            
    def add_order_to_history(self, order: UnifiedOrder):
        """Add order to history for compliance tracking"""
        self.orders_history.append(order)
        
    def get_compliance_report(self) -> Dict[str, Any]:
        """Generate compliance report"""
        return {
            'total_violations': len(self.violations),
            'violation_types': list(set(v.split(':')[0] for v in self.violations)),
            'recent_violations': self.violations[-10:],
            'compliance_settings': {
                'fifo_enabled': self.fifo_enabled,
                'hedging_allowed': self.hedging_allowed,
                'max_leverage': self.max_leverage,
                'min_account_balance': float(self.min_account_balance),
                'pdt_threshold': self.pdt_threshold
            },
            'account_status': {
                'balance': float(self.account_balance),
                'used_margin': float(self.used_margin),
                'day_trades_count': self.day_trades_count,
                'account_type': self.account_type
            }
        }


class ComplianceTestAdapter(BrokerAdapter):
    """Broker adapter with compliance testing capabilities"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._broker_name = "compliance_test"
        self.compliance_engine = ComplianceEngine(config.get('compliance', {}))
        self.order_counter = 0
        
    @property
    def broker_name(self) -> str:
        return self._broker_name
        
    @property
    def broker_display_name(self) -> str:
        return "Compliance Test Adapter"
        
    @property
    def api_version(self) -> str:
        return "test_v1"
        
    @property
    def capabilities(self) -> set:
        capabilities = {
            BrokerCapability.MARKET_ORDERS,
            BrokerCapability.LIMIT_ORDERS,
            BrokerCapability.STOP_ORDERS,
            BrokerCapability.NETTING
        }
        
        # Add hedging capability if allowed
        if self.compliance_engine.hedging_allowed:
            capabilities.add(BrokerCapability.HEDGING)
        else:
            capabilities.add(BrokerCapability.FIFO_ONLY)
            
        return capabilities
        
    @property
    def supported_instruments(self) -> List[str]:
        return ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD"]
        
    @property
    def supported_order_types(self) -> List[OrderType]:
        return [OrderType.MARKET, OrderType.LIMIT, OrderType.STOP]
        
    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        return True
        
    async def disconnect(self) -> bool:
        return True
        
    async def health_check(self) -> Dict[str, Any]:
        return {
            'status': 'healthy',
            'compliance_report': self.compliance_engine.get_compliance_report()
        }
        
    async def get_broker_info(self):
        return {'name': self.broker_name}
        
    async def get_account_summary(self, account_id: Optional[str] = None) -> UnifiedAccountSummary:
        return UnifiedAccountSummary(
            account_id=account_id or "compliance_test_account",
            account_name="Compliance Test Account",
            currency="USD",
            balance=self.compliance_engine.account_balance,
            available_margin=self.compliance_engine.account_balance - self.compliance_engine.used_margin,
            used_margin=self.compliance_engine.used_margin,
            unrealized_pl=Decimal("100.00"),
            nav=self.compliance_engine.account_balance + Decimal("100.00")
        )
        
    async def get_accounts(self) -> List[UnifiedAccountSummary]:
        return [await self.get_account_summary()]
        
    async def place_order(self, order: UnifiedOrder) -> OrderResult:
        """Place order with compliance validation"""
        # Get account summary for compliance checks
        account = await self.get_account_summary()
        
        # Validate compliance
        violations = self.compliance_engine.validate_order(order, account)
        
        if violations:
            # Return failure result with compliance violations
            return OrderResult(
                success=False,
                error_code="COMPLIANCE_VIOLATION",
                error_message="; ".join(violations),
                order_id=order.order_id
            )
            
        # Add to order history
        self.compliance_engine.add_order_to_history(order)
        
        # Simulate successful order
        self.order_counter += 1
        return OrderResult(
            success=True,
            order_id=f"compliance_order_{self.order_counter}",
            client_order_id=order.client_order_id,
            order_state=OrderState.FILLED,
            fill_price=Decimal("1.1000"),
            filled_units=order.units
        )
        
    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> OrderResult:
        return OrderResult(success=True, order_id=order_id)
        
    async def cancel_order(self, order_id: str, reason: Optional[str] = None) -> OrderResult:
        return OrderResult(success=True, order_id=order_id)
        
    async def get_order(self, order_id: str) -> Optional[UnifiedOrder]:
        return None
        
    async def get_orders(self, **kwargs) -> List[UnifiedOrder]:
        return []
        
    async def get_position(self, instrument: str, account_id: Optional[str] = None) -> Optional[UnifiedPosition]:
        positions = self.compliance_engine.positions.get(instrument, [])
        return positions[0] if positions else None
        
    async def get_positions(self, account_id: Optional[str] = None) -> List[UnifiedPosition]:
        all_positions = []
        for positions in self.compliance_engine.positions.values():
            all_positions.extend(positions)
        return all_positions
        
    async def close_position(self, instrument: str, units: Optional[Decimal] = None, account_id: Optional[str] = None) -> OrderResult:
        return OrderResult(success=True, order_id="close_order")
        
    async def get_current_price(self, instrument: str) -> Optional[PriceTick]:
        return PriceTick(
            instrument=instrument,
            bid=Decimal("1.1000"),
            ask=Decimal("1.1002"),
            timestamp=datetime.now(timezone.utc)
        )
        
    async def get_current_prices(self, instruments: List[str]) -> Dict[str, PriceTick]:
        if not instruments:
            raise ValueError("Instruments list is required")
        return {
            instrument: await self.get_current_price(instrument)
            for instrument in instruments
        }
        
    async def stream_prices(self, instruments: List[str]):
        for instrument in instruments:
            yield await self.get_current_price(instrument)
            
    async def get_historical_data(self, **kwargs) -> List[Dict[str, Any]]:
        return []
        
    async def get_transactions(self, **kwargs) -> List[Dict[str, Any]]:
        return []
        
    def map_error(self, broker_error: Exception) -> StandardBrokerError:
        return StandardBrokerError(
            error_code=StandardErrorCode.UNKNOWN_ERROR,
            message=str(broker_error)
        )


class TestFIFOCompliance:
    """Test FIFO compliance enforcement"""
    
    @pytest.fixture
    def fifo_adapter(self):
        """Adapter with FIFO enforcement enabled"""
        return ComplianceTestAdapter({
            'compliance': {
                'fifo_enabled': True,
                'hedging_allowed': False
            }
        })
        
    @pytest.mark.asyncio
    async def test_fifo_order_acceptance(self, fifo_adapter):
        """Test that FIFO compliant orders are accepted"""
        order = UnifiedOrder(
            order_id="fifo_test_1",
            client_order_id="client_fifo_1",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("1000")
        )
        
        result = await fifo_adapter.place_order(order)
        assert result.success is True
        
    @pytest.mark.asyncio
    async def test_fifo_violation_detection(self, fifo_adapter):
        """Test detection of FIFO violations"""
        # Create existing positions to test FIFO
        position1 = UnifiedPosition(
            position_id="pos_1",
            instrument="EUR_USD",
            side=PositionSide.LONG,
            units=Decimal("1000"),
            average_price=Decimal("1.1000"),
            creation_time=datetime.now(timezone.utc) - timedelta(hours=2)
        )
        
        position2 = UnifiedPosition(
            position_id="pos_2",
            instrument="EUR_USD",
            side=PositionSide.LONG,
            units=Decimal("1000"),
            average_price=Decimal("1.1020"),
            creation_time=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        
        fifo_adapter.compliance_engine.add_position(position1)
        fifo_adapter.compliance_engine.add_position(position2)
        
        # Try to place sell order (should trigger FIFO check)
        order = UnifiedOrder(
            order_id="fifo_violation_test",
            client_order_id="client_fifo_violation",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.SELL,
            units=Decimal("500")
        )
        
        result = await fifo_adapter.place_order(order)
        
        # Should detect FIFO violation when multiple positions exist
        assert result.success is False
        assert "FIFO violation" in result.error_message


class TestAntiHedgingCompliance:
    """Test anti-hedging compliance enforcement"""
    
    @pytest.fixture
    def anti_hedge_adapter(self):
        """Adapter with anti-hedging enabled"""
        return ComplianceTestAdapter({
            'compliance': {
                'fifo_enabled': True,
                'hedging_allowed': False
            }
        })
        
    @pytest.mark.asyncio
    async def test_anti_hedging_violation(self, anti_hedge_adapter):
        """Test detection of hedging attempts"""
        # Create existing long position
        long_position = UnifiedPosition(
            position_id="long_pos",
            instrument="EUR_USD",
            side=PositionSide.LONG,
            units=Decimal("1000"),
            average_price=Decimal("1.1000")
        )
        
        anti_hedge_adapter.compliance_engine.add_position(long_position)
        
        # Try to create short position (hedge)
        hedge_order = UnifiedOrder(
            order_id="hedge_test",
            client_order_id="client_hedge",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.SELL,
            units=Decimal("2000")  # Would create net short position
        )
        
        result = await anti_hedge_adapter.place_order(hedge_order)
        
        assert result.success is False
        assert "Anti-hedging violation" in result.error_message
        
    @pytest.mark.asyncio
    async def test_position_increase_allowed(self, anti_hedge_adapter):
        """Test that increasing existing position is allowed"""
        # Create existing long position
        long_position = UnifiedPosition(
            position_id="long_pos",
            instrument="EUR_USD",
            side=PositionSide.LONG,
            units=Decimal("1000"),
            average_price=Decimal("1.1000")
        )
        
        anti_hedge_adapter.compliance_engine.add_position(long_position)
        
        # Add to long position (not hedging)
        add_order = UnifiedOrder(
            order_id="add_test",
            client_order_id="client_add",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("500")
        )
        
        result = await anti_hedge_adapter.place_order(add_order)
        assert result.success is True


class TestLeverageLimits:
    """Test leverage limit compliance"""
    
    @pytest.fixture
    def leverage_adapter(self):
        """Adapter with leverage limits"""
        return ComplianceTestAdapter({
            'compliance': {
                'max_leverage': 10,  # Low leverage for testing
                'fifo_enabled': False,
                'hedging_allowed': True
            }
        })
        
    @pytest.mark.asyncio
    async def test_leverage_limit_enforcement(self, leverage_adapter):
        """Test that leverage limits are enforced"""
        # Set low account balance to trigger leverage limit
        leverage_adapter.compliance_engine.account_balance = Decimal("1000.00")
        
        # Try to place large order that would exceed leverage
        large_order = UnifiedOrder(
            order_id="leverage_test",
            client_order_id="client_leverage",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("20000")  # Would create high leverage
        )
        
        result = await leverage_adapter.place_order(large_order)
        
        assert result.success is False
        assert "Leverage violation" in result.error_message
        
    @pytest.mark.asyncio
    async def test_acceptable_leverage(self, leverage_adapter):
        """Test that acceptable leverage orders are allowed"""
        # Set reasonable account balance
        leverage_adapter.compliance_engine.account_balance = Decimal("10000.00")
        
        # Place reasonable size order
        reasonable_order = UnifiedOrder(
            order_id="reasonable_test",
            client_order_id="client_reasonable",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("5000")  # Reasonable leverage
        )
        
        result = await leverage_adapter.place_order(reasonable_order)
        assert result.success is True


class TestMarginRequirements:
    """Test margin requirement compliance"""
    
    @pytest.fixture
    def margin_adapter(self):
        """Adapter for margin testing"""
        return ComplianceTestAdapter({
            'compliance': {
                'fifo_enabled': False,
                'hedging_allowed': True
            }
        })
        
    @pytest.mark.asyncio
    async def test_insufficient_margin_rejection(self, margin_adapter):
        """Test rejection of orders with insufficient margin"""
        # Set low available margin
        margin_adapter.compliance_engine.account_balance = Decimal("1000.00")
        margin_adapter.compliance_engine.used_margin = Decimal("950.00")
        
        # Try to place order requiring more margin than available
        large_order = UnifiedOrder(
            order_id="margin_test",
            client_order_id="client_margin",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("10000")  # Requires significant margin
        )
        
        result = await margin_adapter.place_order(large_order)
        
        assert result.success is False
        assert "Insufficient margin" in result.error_message
        
    @pytest.mark.asyncio
    async def test_sufficient_margin_acceptance(self, margin_adapter):
        """Test acceptance of orders with sufficient margin"""
        # Set good available margin
        margin_adapter.compliance_engine.account_balance = Decimal("10000.00")
        margin_adapter.compliance_engine.used_margin = Decimal("1000.00")
        
        # Place reasonable order
        reasonable_order = UnifiedOrder(
            order_id="margin_ok_test",
            client_order_id="client_margin_ok",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("1000")
        )
        
        result = await margin_adapter.place_order(reasonable_order)
        assert result.success is True


class TestPatternDayTraderRule:
    """Test Pattern Day Trader rule compliance"""
    
    @pytest.fixture
    def pdt_adapter(self):
        """Adapter for PDT testing"""
        return ComplianceTestAdapter({
            'compliance': {
                'pdt_threshold': 25000,  # $25k PDT threshold
                'fifo_enabled': False,
                'hedging_allowed': True
            }
        })
        
    @pytest.mark.asyncio
    async def test_pdt_rule_for_small_account(self, pdt_adapter):
        """Test PDT rule enforcement for accounts below threshold"""
        # Set account balance below PDT threshold
        pdt_adapter.compliance_engine.account_balance = Decimal("5000.00")
        
        # Add multiple day trades to history
        for i in range(3):
            day_trade = UnifiedOrder(
                order_id=f"day_trade_{i}",
                client_order_id=f"client_day_{i}",
                instrument="EUR_USD",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                units=Decimal("1000"),
                creation_time=datetime.now(timezone.utc)
            )
            pdt_adapter.compliance_engine.add_order_to_history(day_trade)
            
        # Try to place another day trade
        new_day_trade = UnifiedOrder(
            order_id="pdt_violation_test",
            client_order_id="client_pdt_violation",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("1000")
        )
        
        result = await pdt_adapter.place_order(new_day_trade)
        
        assert result.success is False
        assert "PDT violation" in result.error_message
        
    @pytest.mark.asyncio
    async def test_pdt_rule_exemption_for_large_account(self, pdt_adapter):
        """Test PDT rule exemption for accounts above threshold"""
        # Set account balance above PDT threshold
        pdt_adapter.compliance_engine.account_balance = Decimal("30000.00")
        
        # Place day trade (should be allowed)
        day_trade = UnifiedOrder(
            order_id="pdt_exempt_test",
            client_order_id="client_pdt_exempt",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("1000")
        )
        
        result = await pdt_adapter.place_order(day_trade)
        assert result.success is True


class TestPositionLimits:
    """Test position size limit compliance"""
    
    @pytest.fixture
    def position_limit_adapter(self):
        """Adapter with position limits"""
        return ComplianceTestAdapter({
            'compliance': {
                'max_position_size': {
                    'EUR_USD': Decimal('5000'),
                    'GBP_USD': Decimal('3000')
                },
                'fifo_enabled': False,
                'hedging_allowed': True
            }
        })
        
    @pytest.mark.asyncio
    async def test_position_limit_enforcement(self, position_limit_adapter):
        """Test enforcement of position size limits"""
        # Create existing position near limit
        existing_position = UnifiedPosition(
            position_id="existing_pos",
            instrument="EUR_USD",
            side=PositionSide.LONG,
            units=Decimal("4000"),
            average_price=Decimal("1.1000")
        )
        
        position_limit_adapter.compliance_engine.add_position(existing_position)
        
        # Try to add more that would exceed limit
        large_order = UnifiedOrder(
            order_id="position_limit_test",
            client_order_id="client_position_limit",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("2000")  # Would exceed 5000 limit
        )
        
        result = await position_limit_adapter.place_order(large_order)
        
        assert result.success is False
        assert "Position limit violation" in result.error_message
        
    @pytest.mark.asyncio
    async def test_position_within_limits(self, position_limit_adapter):
        """Test acceptance of positions within limits"""
        # Place order within limits
        small_order = UnifiedOrder(
            order_id="position_ok_test",
            client_order_id="client_position_ok",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("1000")  # Well within 5000 limit
        )
        
        result = await position_limit_adapter.place_order(small_order)
        assert result.success is True


class TestRegulatoryRestrictions:
    """Test regulatory restriction compliance"""
    
    @pytest.fixture
    def regulatory_adapter(self):
        """Adapter with regulatory restrictions"""
        return ComplianceTestAdapter({
            'compliance': {
                'fifo_enabled': True,
                'hedging_allowed': False,
                'max_leverage': 30,
                'min_account_balance': Decimal('10000.00')
            }
        })
        
    @pytest.mark.asyncio
    async def test_account_balance_minimum(self, regulatory_adapter):
        """Test minimum account balance requirements"""
        # Set account balance below minimum
        regulatory_adapter.compliance_engine.account_balance = Decimal("5000.00")
        
        # Check compliance report
        health = await regulatory_adapter.health_check()
        compliance_report = health['compliance_report']
        
        assert compliance_report['account_status']['balance'] < float(regulatory_adapter.compliance_engine.min_account_balance)
        
    @pytest.mark.asyncio
    async def test_comprehensive_compliance_check(self, regulatory_adapter):
        """Test comprehensive compliance validation"""
        # Create scenario that triggers multiple compliance checks
        order = UnifiedOrder(
            order_id="comprehensive_test",
            client_order_id="client_comprehensive",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("1000")
        )
        
        # Get account info
        account = await regulatory_adapter.get_account_summary()
        
        # Run compliance validation
        violations = regulatory_adapter.compliance_engine.validate_order(order, account)
        
        # Should have no violations for a reasonable order
        assert len(violations) == 0
        
        result = await regulatory_adapter.place_order(order)
        assert result.success is True


class TestComplianceReporting:
    """Test compliance reporting functionality"""
    
    @pytest.fixture
    def reporting_adapter(self):
        """Adapter for compliance reporting"""
        return ComplianceTestAdapter({})
        
    @pytest.mark.asyncio
    async def test_compliance_report_generation(self, reporting_adapter):
        """Test generation of compliance reports"""
        # Execute some orders to generate data
        for i in range(3):
            order = UnifiedOrder(
                order_id=f"report_test_{i}",
                client_order_id=f"client_report_{i}",
                instrument="EUR_USD",
                order_type=OrderType.MARKET,
                side=OrderSide.BUY,
                units=Decimal("1000")
            )
            await reporting_adapter.place_order(order)
            
        # Get compliance report
        report = reporting_adapter.compliance_engine.get_compliance_report()
        
        assert 'total_violations' in report
        assert 'compliance_settings' in report
        assert 'account_status' in report
        assert report['compliance_settings']['fifo_enabled'] is True
        
    @pytest.mark.asyncio
    async def test_audit_trail_validation(self, reporting_adapter):
        """Test audit trail for compliance tracking"""
        # Place orders with different compliance outcomes
        valid_order = UnifiedOrder(
            order_id="audit_valid",
            client_order_id="client_audit_valid",
            instrument="EUR_USD",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            units=Decimal("1000")
        )
        
        result = await reporting_adapter.place_order(valid_order)
        assert result.success is True
        
        # Check that order was added to history
        assert len(reporting_adapter.compliance_engine.orders_history) == 1
        assert reporting_adapter.compliance_engine.orders_history[0].order_id == "audit_valid"


if __name__ == "__main__":
    # Run compliance tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short"
    ])