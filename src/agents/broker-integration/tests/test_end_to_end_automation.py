"""
End-to-End Test Automation for Broker Integration
Story 8.12 - Task 6: Build end-to-end test automation with CI/CD integration (AC: 7, 8)
"""
import pytest
import asyncio
import json
import time
import logging
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict

# Test imports
import sys
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from broker_adapter import (
    BrokerAdapter, UnifiedOrder, UnifiedPosition, UnifiedAccountSummary,
    OrderType, OrderSide, OrderState, PositionSide, TimeInForce,
    BrokerCapability, PriceTick, OrderResult
)
from unified_errors import StandardBrokerError, StandardErrorCode

logger = logging.getLogger(__name__)


@dataclass
class TestScenario:
    """Represents an end-to-end test scenario"""
    name: str
    description: str
    steps: List[Dict[str, Any]]
    expected_outcomes: List[Dict[str, Any]]
    prerequisites: List[str] = None
    cleanup_required: bool = True
    timeout_seconds: int = 300
    retry_count: int = 3


@dataclass
class TestExecution:
    """Tracks test execution results"""
    scenario_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "running"  # running, passed, failed, skipped
    steps_completed: int = 0
    total_steps: int = 0
    error_message: Optional[str] = None
    execution_data: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'scenario_name': self.scenario_name,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status,
            'steps_completed': self.steps_completed,
            'total_steps': self.total_steps,
            'duration_seconds': (self.end_time - self.start_time).total_seconds() if self.end_time else None,
            'error_message': self.error_message,
            'execution_data': self.execution_data or {}
        }


class E2ETestRunner:
    """End-to-end test runner with comprehensive automation"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.test_executions: List[TestExecution] = []
        self.test_data_cleanup = []
        self.performance_metrics = {}
        
    async def run_scenario(self, scenario: TestScenario, adapter: BrokerAdapter) -> TestExecution:
        """Run a complete end-to-end test scenario"""
        execution = TestExecution(
            scenario_name=scenario.name,
            start_time=datetime.now(timezone.utc),
            total_steps=len(scenario.steps),
            execution_data={}
        )
        
        self.test_executions.append(execution)
        
        try:
            logger.info(f"Starting E2E scenario: {scenario.name}")
            
            # Check prerequisites
            if scenario.prerequisites:
                await self._check_prerequisites(scenario.prerequisites, adapter)
                
            # Execute steps
            for i, step in enumerate(scenario.steps):
                logger.info(f"Executing step {i+1}/{len(scenario.steps)}: {step.get('name', 'Unnamed step')}")
                
                step_result = await self._execute_step(step, adapter, execution)
                execution.execution_data[f"step_{i+1}"] = step_result
                execution.steps_completed += 1
                
            # Validate outcomes
            await self._validate_outcomes(scenario.expected_outcomes, execution, adapter)
            
            execution.status = "passed"
            execution.end_time = datetime.now(timezone.utc)
            
            logger.info(f"E2E scenario completed successfully: {scenario.name}")
            
        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            execution.end_time = datetime.now(timezone.utc)
            
            logger.error(f"E2E scenario failed: {scenario.name} - {e}")
            
        finally:
            # Cleanup if required
            if scenario.cleanup_required:
                await self._cleanup_test_data(execution, adapter)
                
        return execution
        
    async def _execute_step(self, step: Dict[str, Any], adapter: BrokerAdapter, execution: TestExecution) -> Dict[str, Any]:
        """Execute a single test step"""
        step_type = step.get('type')
        step_data = step.get('data', {})
        
        if step_type == 'place_order':
            return await self._step_place_order(step_data, adapter)
        elif step_type == 'get_account_summary':
            return await self._step_get_account_summary(step_data, adapter)
        elif step_type == 'get_positions':
            return await self._step_get_positions(step_data, adapter)
        elif step_type == 'get_current_price':
            return await self._step_get_current_price(step_data, adapter)
        elif step_type == 'wait':
            return await self._step_wait(step_data)
        elif step_type == 'validate_performance':
            return await self._step_validate_performance(step_data, execution)
        elif step_type == 'close_position':
            return await self._step_close_position(step_data, adapter)
        else:
            raise ValueError(f"Unknown step type: {step_type}")
            
    async def _step_place_order(self, data: Dict[str, Any], adapter: BrokerAdapter) -> Dict[str, Any]:
        """Execute place order step"""
        order = UnifiedOrder(
            order_id=data['order_id'],
            client_order_id=data.get('client_order_id', data['order_id']),
            instrument=data['instrument'],
            order_type=OrderType(data['order_type']),
            side=OrderSide(data['side']),
            units=Decimal(str(data['units'])),
            price=Decimal(str(data['price'])) if data.get('price') else None
        )
        
        start_time = time.perf_counter()
        result = await adapter.place_order(order)
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        
        return {
            'order_id': order.order_id,
            'result': {
                'success': result.success,
                'order_id': result.order_id,
                'error_message': result.error_message
            },
            'latency_ms': latency_ms
        }
        
    async def _step_get_account_summary(self, data: Dict[str, Any], adapter: BrokerAdapter) -> Dict[str, Any]:
        """Execute get account summary step"""
        account_id = data.get('account_id')
        
        start_time = time.perf_counter()
        summary = await adapter.get_account_summary(account_id)
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        
        return {
            'account_id': summary.account_id,
            'balance': float(summary.balance),
            'available_margin': float(summary.available_margin),
            'latency_ms': latency_ms
        }
        
    async def _step_get_positions(self, data: Dict[str, Any], adapter: BrokerAdapter) -> Dict[str, Any]:
        """Execute get positions step"""
        account_id = data.get('account_id')
        
        start_time = time.perf_counter()
        positions = await adapter.get_positions(account_id)
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        
        return {
            'position_count': len(positions),
            'positions': [
                {
                    'instrument': pos.instrument,
                    'side': pos.side.value,
                    'units': float(pos.units)
                }
                for pos in positions
            ],
            'latency_ms': latency_ms
        }
        
    async def _step_get_current_price(self, data: Dict[str, Any], adapter: BrokerAdapter) -> Dict[str, Any]:
        """Execute get current price step"""
        instrument = data['instrument']
        
        start_time = time.perf_counter()
        price = await adapter.get_current_price(instrument)
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        
        return {
            'instrument': instrument,
            'price_available': price is not None,
            'bid': float(price.bid) if price else None,
            'ask': float(price.ask) if price else None,
            'latency_ms': latency_ms
        }
        
    async def _step_wait(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute wait step"""
        wait_seconds = data.get('seconds', 1)
        await asyncio.sleep(wait_seconds)
        
        return {
            'waited_seconds': wait_seconds
        }
        
    async def _step_validate_performance(self, data: Dict[str, Any], execution: TestExecution) -> Dict[str, Any]:
        """Validate performance metrics"""
        max_latency = data.get('max_latency_ms', 1000)
        
        # Collect latency data from previous steps
        latencies = []
        for step_key, step_data in execution.execution_data.items():
            if 'latency_ms' in step_data:
                latencies.append(step_data['latency_ms'])
                
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        max_latency_observed = max(latencies) if latencies else 0
        
        performance_ok = max_latency_observed <= max_latency
        
        return {
            'performance_check': 'passed' if performance_ok else 'failed',
            'avg_latency_ms': avg_latency,
            'max_latency_ms': max_latency_observed,
            'max_allowed_ms': max_latency,
            'total_operations': len(latencies)
        }
        
    async def _step_close_position(self, data: Dict[str, Any], adapter: BrokerAdapter) -> Dict[str, Any]:
        """Execute close position step"""
        instrument = data['instrument']
        units = Decimal(str(data['units'])) if data.get('units') else None
        
        start_time = time.perf_counter()
        result = await adapter.close_position(instrument, units)
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        
        return {
            'instrument': instrument,
            'result': {
                'success': result.success,
                'order_id': result.order_id
            },
            'latency_ms': latency_ms
        }
        
    async def _check_prerequisites(self, prerequisites: List[str], adapter: BrokerAdapter):
        """Check test prerequisites"""
        for prereq in prerequisites:
            if prereq == 'authenticated':
                if not adapter.is_authenticated:
                    raise RuntimeError("Adapter must be authenticated")
            elif prereq == 'healthy':
                health = await adapter.health_check()
                if health.get('status') != 'healthy':
                    raise RuntimeError("Adapter health check failed")
                    
    async def _validate_outcomes(self, expected_outcomes: List[Dict[str, Any]], execution: TestExecution, adapter: BrokerAdapter):
        """Validate expected test outcomes"""
        for outcome in expected_outcomes:
            outcome_type = outcome.get('type')
            expected_value = outcome.get('expected')
            
            if outcome_type == 'all_orders_successful':
                # Check that all order placements were successful
                order_results = [
                    step_data.get('result', {}) 
                    for step_data in execution.execution_data.values()
                    if 'result' in step_data and 'success' in step_data['result']
                ]
                
                failed_orders = [r for r in order_results if not r.get('success')]
                if failed_orders:
                    raise AssertionError(f"Expected all orders to succeed, but {len(failed_orders)} failed")
                    
            elif outcome_type == 'performance_within_limits':
                # Check performance is within expected limits
                performance_steps = [
                    step_data 
                    for step_data in execution.execution_data.values()
                    if 'performance_check' in step_data
                ]
                
                failed_performance = [p for p in performance_steps if p['performance_check'] != 'passed']
                if failed_performance:
                    raise AssertionError(f"Performance checks failed: {failed_performance}")
                    
    async def _cleanup_test_data(self, execution: TestExecution, adapter: BrokerAdapter):
        """Clean up test data after execution"""
        try:
            # Close any remaining test positions
            positions = await adapter.get_positions()
            for position in positions:
                if 'test' in position.position_id.lower():
                    await adapter.close_position(position.instrument)
                    
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")
            
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.test_executions)
        passed_tests = len([e for e in self.test_executions if e.status == 'passed'])
        failed_tests = len([e for e in self.test_executions if e.status == 'failed'])
        
        # Calculate performance metrics
        all_latencies = []
        for execution in self.test_executions:
            for step_data in execution.execution_data.values():
                if 'latency_ms' in step_data:
                    all_latencies.append(step_data['latency_ms'])
                    
        avg_latency = sum(all_latencies) / len(all_latencies) if all_latencies else 0
        max_latency = max(all_latencies) if all_latencies else 0
        
        return {
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            'performance': {
                'avg_latency_ms': avg_latency,
                'max_latency_ms': max_latency,
                'total_operations': len(all_latencies)
            },
            'executions': [execution.to_dict() for execution in self.test_executions],
            'generated_at': datetime.now(timezone.utc).isoformat()
        }


class MockE2EAdapter(BrokerAdapter):
    """Mock adapter for E2E testing"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._broker_name = "e2e_test"
        self.is_authenticated = True
        self.connection_status = 'connected'
        self.order_counter = 0
        self.positions = {}
        
    @property
    def broker_name(self) -> str:
        return self._broker_name
        
    @property
    def broker_display_name(self) -> str:
        return "E2E Test Adapter"
        
    @property
    def api_version(self) -> str:
        return "test_v1"
        
    @property
    def capabilities(self) -> set:
        return {BrokerCapability.MARKET_ORDERS, BrokerCapability.LIMIT_ORDERS}
        
    @property
    def supported_instruments(self) -> List[str]:
        return ["EUR_USD", "GBP_USD"]
        
    @property
    def supported_order_types(self) -> List[OrderType]:
        return [OrderType.MARKET, OrderType.LIMIT]
        
    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        await asyncio.sleep(0.01)  # Simulate network delay
        return True
        
    async def disconnect(self) -> bool:
        return True
        
    async def health_check(self) -> Dict[str, Any]:
        await asyncio.sleep(0.005)
        return {'status': 'healthy'}
        
    async def get_broker_info(self):
        return {'name': self.broker_name}
        
    async def get_account_summary(self, account_id: Optional[str] = None) -> UnifiedAccountSummary:
        await asyncio.sleep(0.01)
        
        return UnifiedAccountSummary(
            account_id=account_id or "e2e_test_account",
            account_name="E2E Test Account",
            currency="USD",
            balance=Decimal("10000.00"),
            available_margin=Decimal("9500.00"),
            used_margin=Decimal("500.00")
        )
        
    async def get_accounts(self) -> List[UnifiedAccountSummary]:
        return [await self.get_account_summary()]
        
    async def place_order(self, order: UnifiedOrder) -> OrderResult:
        await asyncio.sleep(0.02)  # Simulate order processing
        
        self.order_counter += 1
        
        # Simulate occasional failures for testing
        if 'fail' in order.order_id.lower():
            return OrderResult(
                success=False,
                error_code="SIMULATED_FAILURE",
                error_message="Simulated order failure for testing"
            )
            
        result = OrderResult(
            success=True,
            order_id=f"e2e_order_{self.order_counter}",
            client_order_id=order.client_order_id,
            order_state=OrderState.FILLED,
            fill_price=Decimal("1.1000"),
            filled_units=order.units
        )
        
        # Add position for tracking
        if order.instrument not in self.positions:
            self.positions[order.instrument] = []
            
        position = UnifiedPosition(
            position_id=result.order_id,
            instrument=order.instrument,
            side=PositionSide.LONG if order.side == OrderSide.BUY else PositionSide.SHORT,
            units=order.units,
            average_price=result.fill_price
        )
        self.positions[order.instrument].append(position)
        
        return result
        
    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> OrderResult:
        await asyncio.sleep(0.01)
        return OrderResult(success=True, order_id=order_id)
        
    async def cancel_order(self, order_id: str, reason: Optional[str] = None) -> OrderResult:
        await asyncio.sleep(0.01)
        return OrderResult(success=True, order_id=order_id)
        
    async def get_order(self, order_id: str) -> Optional[UnifiedOrder]:
        await asyncio.sleep(0.01)
        return None
        
    async def get_orders(self, **kwargs) -> List[UnifiedOrder]:
        await asyncio.sleep(0.01)
        return []
        
    async def get_position(self, instrument: str, account_id: Optional[str] = None) -> Optional[UnifiedPosition]:
        await asyncio.sleep(0.01)
        positions = self.positions.get(instrument, [])
        return positions[0] if positions else None
        
    async def get_positions(self, account_id: Optional[str] = None) -> List[UnifiedPosition]:
        await asyncio.sleep(0.01)
        all_positions = []
        for positions in self.positions.values():
            all_positions.extend(positions)
        return all_positions
        
    async def close_position(self, instrument: str, units: Optional[Decimal] = None, account_id: Optional[str] = None) -> OrderResult:
        await asyncio.sleep(0.02)
        
        # Remove position from tracking
        if instrument in self.positions:
            self.positions[instrument] = []
            
        return OrderResult(
            success=True,
            order_id=f"close_order_{self.order_counter}",
            fill_price=Decimal("1.1010"),
            filled_units=units or Decimal("1000")
        )
        
    async def get_current_price(self, instrument: str) -> Optional[PriceTick]:
        await asyncio.sleep(0.005)
        
        return PriceTick(
            instrument=instrument,
            bid=Decimal("1.1000"),
            ask=Decimal("1.1002"),
            timestamp=datetime.now(timezone.utc)
        )
        
    async def get_current_prices(self, instruments: List[str]) -> Dict[str, PriceTick]:
        if not instruments:
            raise ValueError("Instruments list required")
            
        prices = {}
        for instrument in instruments:
            prices[instrument] = await self.get_current_price(instrument)
        return prices
        
    async def stream_prices(self, instruments: List[str]):
        for instrument in instruments:
            yield await self.get_current_price(instrument)
            
    async def get_historical_data(self, **kwargs) -> List[Dict[str, Any]]:
        await asyncio.sleep(0.01)
        return []
        
    async def get_transactions(self, **kwargs) -> List[Dict[str, Any]]:
        await asyncio.sleep(0.01)
        return []
        
    def map_error(self, broker_error: Exception) -> StandardBrokerError:
        return StandardBrokerError(
            error_code=StandardErrorCode.UNKNOWN_ERROR,
            message=str(broker_error)
        )


class TestE2EScenarios:
    """End-to-end test scenarios"""
    
    @pytest.fixture
    def e2e_adapter(self):
        """E2E test adapter"""
        return MockE2EAdapter({})
        
    @pytest.fixture
    def e2e_runner(self):
        """E2E test runner"""
        return E2ETestRunner()
        
    @pytest.mark.asyncio
    async def test_complete_trade_lifecycle(self, e2e_adapter, e2e_runner):
        """Test complete trade lifecycle from order to close"""
        scenario = TestScenario(
            name="Complete Trade Lifecycle",
            description="Test full trade lifecycle: authenticate -> get account -> place order -> check position -> close position",
            steps=[
                {
                    'type': 'get_account_summary',
                    'name': 'Get account summary',
                    'data': {}
                },
                {
                    'type': 'place_order',
                    'name': 'Place market order',
                    'data': {
                        'order_id': 'e2e_lifecycle_test',
                        'instrument': 'EUR_USD',
                        'order_type': 'market',
                        'side': 'buy',
                        'units': 1000
                    }
                },
                {
                    'type': 'get_positions',
                    'name': 'Check positions after order',
                    'data': {}
                },
                {
                    'type': 'close_position',
                    'name': 'Close position',
                    'data': {
                        'instrument': 'EUR_USD',
                        'units': 1000
                    }
                },
                {
                    'type': 'validate_performance',
                    'name': 'Validate performance',
                    'data': {
                        'max_latency_ms': 100
                    }
                }
            ],
            expected_outcomes=[
                {'type': 'all_orders_successful', 'expected': True},
                {'type': 'performance_within_limits', 'expected': True}
            ],
            prerequisites=['authenticated', 'healthy']
        )
        
        execution = await e2e_runner.run_scenario(scenario, e2e_adapter)
        
        assert execution.status == 'passed'
        assert execution.steps_completed == len(scenario.steps)
        assert execution.error_message is None
        
    @pytest.mark.asyncio
    async def test_multi_instrument_trading(self, e2e_adapter, e2e_runner):
        """Test trading across multiple instruments"""
        scenario = TestScenario(
            name="Multi-Instrument Trading",
            description="Test trading multiple instruments simultaneously",
            steps=[
                {
                    'type': 'get_current_price',
                    'name': 'Get EUR_USD price',
                    'data': {'instrument': 'EUR_USD'}
                },
                {
                    'type': 'get_current_price',
                    'name': 'Get GBP_USD price',
                    'data': {'instrument': 'GBP_USD'}
                },
                {
                    'type': 'place_order',
                    'name': 'Place EUR_USD order',
                    'data': {
                        'order_id': 'e2e_eur_usd_test',
                        'instrument': 'EUR_USD',
                        'order_type': 'market',
                        'side': 'buy',
                        'units': 1000
                    }
                },
                {
                    'type': 'place_order',
                    'name': 'Place GBP_USD order',
                    'data': {
                        'order_id': 'e2e_gbp_usd_test',
                        'instrument': 'GBP_USD',
                        'order_type': 'market',
                        'side': 'buy',
                        'units': 500
                    }
                },
                {
                    'type': 'get_positions',
                    'name': 'Check all positions',
                    'data': {}
                }
            ],
            expected_outcomes=[
                {'type': 'all_orders_successful', 'expected': True}
            ]
        )
        
        execution = await e2e_runner.run_scenario(scenario, e2e_adapter)
        
        assert execution.status == 'passed'
        assert execution.execution_data['step_5']['position_count'] == 2  # Two positions created
        
    @pytest.mark.asyncio
    async def test_error_handling_scenario(self, e2e_adapter, e2e_runner):
        """Test error handling in E2E scenarios"""
        scenario = TestScenario(
            name="Error Handling Test",
            description="Test proper handling of order failures",
            steps=[
                {
                    'type': 'place_order',
                    'name': 'Place successful order',
                    'data': {
                        'order_id': 'e2e_success_test',
                        'instrument': 'EUR_USD',
                        'order_type': 'market',
                        'side': 'buy',
                        'units': 1000
                    }
                },
                {
                    'type': 'place_order',
                    'name': 'Place failing order',
                    'data': {
                        'order_id': 'e2e_fail_test',  # Contains 'fail' to trigger failure
                        'instrument': 'EUR_USD',
                        'order_type': 'market',
                        'side': 'buy',
                        'units': 1000
                    }
                }
            ],
            expected_outcomes=[],  # Don't expect all orders to succeed
            cleanup_required=False
        )
        
        execution = await e2e_runner.run_scenario(scenario, e2e_adapter)
        
        assert execution.status == 'passed'
        assert execution.execution_data['step_1']['result']['success'] is True
        assert execution.execution_data['step_2']['result']['success'] is False
        
    @pytest.mark.asyncio
    async def test_performance_monitoring(self, e2e_adapter, e2e_runner):
        """Test performance monitoring in E2E scenarios"""
        scenario = TestScenario(
            name="Performance Monitoring",
            description="Test that operations complete within performance thresholds",
            steps=[
                {
                    'type': 'place_order',
                    'name': 'Performance test order 1',
                    'data': {
                        'order_id': 'e2e_perf_test_1',
                        'instrument': 'EUR_USD',
                        'order_type': 'market',
                        'side': 'buy',
                        'units': 1000
                    }
                },
                {
                    'type': 'place_order',
                    'name': 'Performance test order 2',
                    'data': {
                        'order_id': 'e2e_perf_test_2',
                        'instrument': 'GBP_USD',
                        'order_type': 'market',
                        'side': 'buy',
                        'units': 1000
                    }
                },
                {
                    'type': 'validate_performance',
                    'name': 'Check performance metrics',
                    'data': {
                        'max_latency_ms': 50  # Strict requirement
                    }
                }
            ],
            expected_outcomes=[
                {'type': 'performance_within_limits', 'expected': True}
            ]
        )
        
        execution = await e2e_runner.run_scenario(scenario, e2e_adapter)
        
        assert execution.status == 'passed'
        performance_data = execution.execution_data['step_3']
        assert performance_data['performance_check'] == 'passed'
        assert performance_data['total_operations'] == 2


class TestE2EReporting:
    """Test E2E reporting and CI/CD integration"""
    
    @pytest.fixture
    def e2e_runner_with_data(self):
        """E2E runner with test data"""
        runner = E2ETestRunner()
        
        # Add mock executions
        execution1 = TestExecution(
            scenario_name="Test Scenario 1",
            start_time=datetime.now(timezone.utc) - timedelta(minutes=5),
            end_time=datetime.now(timezone.utc) - timedelta(minutes=4),
            status="passed",
            steps_completed=3,
            total_steps=3,
            execution_data={
                'step_1': {'latency_ms': 25},
                'step_2': {'latency_ms': 30},
                'step_3': {'latency_ms': 15}
            }
        )
        
        execution2 = TestExecution(
            scenario_name="Test Scenario 2",
            start_time=datetime.now(timezone.utc) - timedelta(minutes=3),
            end_time=datetime.now(timezone.utc) - timedelta(minutes=2),
            status="failed",
            steps_completed=2,
            total_steps=4,
            error_message="Simulated failure",
            execution_data={
                'step_1': {'latency_ms': 45},
                'step_2': {'latency_ms': 100}
            }
        )
        
        runner.test_executions = [execution1, execution2]
        return runner
        
    def test_test_report_generation(self, e2e_runner_with_data):
        """Test generation of comprehensive test reports"""
        report = e2e_runner_with_data.generate_test_report()
        
        # Check report structure
        assert 'summary' in report
        assert 'performance' in report
        assert 'executions' in report
        assert 'generated_at' in report
        
        # Check summary data
        summary = report['summary']
        assert summary['total_tests'] == 2
        assert summary['passed_tests'] == 1
        assert summary['failed_tests'] == 1
        assert summary['success_rate'] == 50.0
        
        # Check performance data
        performance = report['performance']
        assert performance['total_operations'] == 5
        assert performance['avg_latency_ms'] == 43.0  # (25+30+15+45+100)/5
        assert performance['max_latency_ms'] == 100.0
        
        # Check execution details
        executions = report['executions']
        assert len(executions) == 2
        assert executions[0]['status'] == 'passed'
        assert executions[1]['status'] == 'failed'
        
    def test_ci_cd_integration_format(self, e2e_runner_with_data):
        """Test that report format is suitable for CI/CD integration"""
        report = e2e_runner_with_data.generate_test_report()
        
        # Should be serializable to JSON for CI/CD systems
        json_report = json.dumps(report, indent=2)
        assert len(json_report) > 0
        
        # Should contain key metrics for CI/CD decisions
        assert report['summary']['success_rate'] <= 100
        assert 'failed_tests' in report['summary']
        assert 'avg_latency_ms' in report['performance']
        
        # Test execution details should be present for debugging
        for execution in report['executions']:
            assert 'scenario_name' in execution
            assert 'status' in execution
            assert 'duration_seconds' in execution or execution['status'] == 'running'


class TestE2ERegressionSuite:
    """End-to-end regression test suite"""
    
    @pytest.fixture
    def regression_adapter(self):
        """Adapter for regression testing"""
        return MockE2EAdapter({})
        
    @pytest.fixture
    def regression_runner(self):
        """Runner for regression tests"""
        return E2ETestRunner()
        
    @pytest.mark.asyncio
    async def test_regression_test_suite(self, regression_adapter, regression_runner):
        """Test complete regression suite execution"""
        scenarios = [
            TestScenario(
                name="Basic Order Placement",
                description="Regression test for basic order placement",
                steps=[
                    {
                        'type': 'place_order',
                        'name': 'Basic market order',
                        'data': {
                            'order_id': 'regression_basic',
                            'instrument': 'EUR_USD',
                            'order_type': 'market',
                            'side': 'buy',
                            'units': 1000
                        }
                    }
                ],
                expected_outcomes=[
                    {'type': 'all_orders_successful', 'expected': True}
                ]
            ),
            TestScenario(
                name="Account Information Retrieval",
                description="Regression test for account information",
                steps=[
                    {
                        'type': 'get_account_summary',
                        'name': 'Get account info',
                        'data': {}
                    }
                ],
                expected_outcomes=[]
            )
        ]
        
        # Run all scenarios
        results = []
        for scenario in scenarios:
            execution = await regression_runner.run_scenario(scenario, regression_adapter)
            results.append(execution)
            
        # Verify all scenarios passed
        assert all(result.status == 'passed' for result in results)
        
        # Generate regression report
        report = regression_runner.generate_test_report()
        assert report['summary']['success_rate'] == 100.0


if __name__ == "__main__":
    # Run E2E tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short"
    ])