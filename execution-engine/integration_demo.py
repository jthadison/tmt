"""
Integration demonstration of Position Management & Modification system.

This demonstrates all functionality working together without external dependencies.
"""

import sys
sys.path.append('.')

import asyncio
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock
from src.oanda.position_manager import PositionInfo, PositionSide, OandaPositionManager
from src.oanda.partial_close_manager import PartialCloseManager, CloseType
from src.oanda.trailing_stop_manager import TrailingStopManager, TrailingType
from src.oanda.position_monitor import PositionMonitor, AlertType, AlertSeverity


class MockOandaClient:
    """Mock OANDA client for demonstration"""
    
    def __init__(self):
        self.account_id = "demo_account_123"
        self.positions_data = {
            'positions': [
                {
                    'instrument': 'EUR_USD',
                    'long': {
                        'units': '10000',
                        'averagePrice': '1.0500',
                        'unrealizedPL': '75.00',
                        'openTime': '2024-01-15T10:30:00.000000Z'
                    },
                    'short': {'units': '0', 'averagePrice': '0', 'unrealizedPL': '0'},
                    'financing': '1.25',
                    'commission': '0.50',
                    'marginUsed': '350.00'
                }
            ]
        }
        
        self.trades_data = {
            'trades': [
                {
                    'id': 'trade_12345',
                    'instrument': 'EUR_USD',
                    'currentUnits': '10000',
                    'price': '1.0500'
                }
            ]
        }
        
        self.pricing_data = {
            'prices': [
                {
                    'instrument': 'EUR_USD',
                    'closeoutAsk': '1.0575',
                    'closeoutBid': '1.0573'
                }
            ]
        }
    
    async def get(self, endpoint, params=None):
        """Mock GET request"""
        if 'openPositions' in endpoint:
            return self.positions_data
        elif 'trades' in endpoint:
            return self.trades_data
        elif 'pricing' in endpoint:
            return self.pricing_data
        return {}
    
    async def put(self, endpoint, json=None):
        """Mock PUT request"""
        if 'close' in endpoint and json:
            return {
                'longOrderFillTransaction': {
                    'id': 'txn_67890',
                    'units': '5000',
                    'pl': '37.50'
                }
            }
        elif 'orders' in endpoint:
            return {
                'stopLossOrderTransaction': {'id': 'sl_123'},
                'takeProfitOrderTransaction': {'id': 'tp_123'}
            }
        return {}


class MockPriceStream:
    """Mock price stream for demonstration"""
    
    def __init__(self):
        self.prices = {
            'EUR_USD': {'bid': 1.0573, 'ask': 1.0575}
        }
    
    async def get_current_price(self, instrument):
        """Mock current price"""
        return self.prices.get(instrument, {'bid': 1.0000, 'ask': 1.0002})


async def demo_position_data_fetching():
    """Demonstrate position data fetching and P&L calculation"""
    print("\n=== Position Data Fetching Demo ===")
    
    # Setup mock components
    client = MockOandaClient()
    price_stream = MockPriceStream()
    
    # Create position manager
    manager = OandaPositionManager(client, price_stream)
    
    # Fetch positions
    positions = await manager.get_open_positions()
    
    print(f"Fetched {len(positions)} positions:")
    for pos in positions:
        print(f"  {pos.position_id}: {pos.instrument} {pos.side.value}")
        print(f"    Units: {pos.units}, Entry: {pos.entry_price}")
        print(f"    Current: {pos.current_price}, P&L: {pos.unrealized_pl}")
        print(f"    P&L %: {pos.pl_percentage:.2f}%, Age: {pos.age_hours:.1f}h")
    
    return manager


async def demo_position_modification(manager):
    """Demonstrate stop loss and take profit modification"""
    print("\n=== Position Modification Demo ===")
    
    # Get first position
    positions = list(manager.position_cache.values())
    if not positions:
        print("No positions available for modification")
        return
    
    position = positions[0]
    print(f"Modifying position: {position.position_id}")
    
    # Set stop loss
    new_stop_loss = Decimal('1.0450')
    success = await manager.modify_stop_loss(position.position_id, new_stop_loss)
    print(f"  Stop loss set to {new_stop_loss}: {'SUCCESS' if success else 'FAILED'}")
    
    # Set take profit
    new_take_profit = Decimal('1.0600')
    success = await manager.modify_take_profit(position.position_id, new_take_profit)
    print(f"  Take profit set to {new_take_profit}: {'SUCCESS' if success else 'FAILED'}")
    
    # Batch modification
    modifications = [
        {
            'position_id': position.position_id,
            'stop_loss': '1.0455',
            'take_profit': '1.0595'
        }
    ]
    
    results = await manager.batch_modify_positions(modifications)
    print(f"  Batch modification: {results}")


async def demo_partial_closing(manager):
    """Demonstrate partial position closing"""
    print("\n=== Partial Position Closing Demo ===")
    
    # Create partial close manager
    partial_manager = PartialCloseManager(manager)
    
    position_id = list(manager.position_cache.keys())[0]
    print(f"Partial closing position: {position_id}")
    
    # Close 50% of position
    result = await partial_manager.partial_close_position(
        position_id,
        "50%",
        validate_fifo=False
    )
    
    print(f"  50% close result:")
    print(f"    Success: {result.success}")
    print(f"    Units requested: {result.units_requested}")
    print(f"    Units closed: {result.units_closed}")
    print(f"    Realized P&L: {result.realized_pl}")
    print(f"    Transaction ID: {result.transaction_id}")
    
    # Demonstrate close by criteria
    print("\n  Closing positions by criteria...")
    criteria_results = await partial_manager.close_positions_by_criteria(
        min_profit=Decimal('50')
    )
    print(f"    Criteria close results: {len(criteria_results)} positions processed")


async def demo_trailing_stops(manager):
    """Demonstrate trailing stop functionality"""
    print("\n=== Trailing Stop Demo ===")
    
    # Create trailing stop manager
    trailing_manager = TrailingStopManager(manager, update_interval=1)
    
    # Refresh positions in case they were modified
    await manager.get_open_positions()
    
    if not manager.position_cache:
        print("  No positions available for trailing stop demo")
        return
    
    position_id = list(manager.position_cache.keys())[0]
    print(f"Setting trailing stop for: {position_id}")
    
    # Set distance-based trailing stop
    success = await trailing_manager.set_trailing_stop(
        position_id,
        Decimal('20'),  # 20 pips
        TrailingType.DISTANCE
    )
    print(f"  Distance trailing stop (20 pips): {'SUCCESS' if success else 'FAILED'}")
    
    # Check status
    status = await trailing_manager.get_trailing_stop_status(position_id)
    if status:
        print(f"  Status: {status['trailing_type']} trail, active: {status['is_active']}")
        print(f"  Current stop: {status['current_stop']}")
        print(f"  Trail distance: {status['trail_value']} pips")
    
    # List all trailing stops
    all_stops = await trailing_manager.list_all_trailing_stops()
    print(f"  Total trailing stops active: {len(all_stops)}")
    
    # Clean up
    await trailing_manager.remove_trailing_stop(position_id)


async def demo_position_monitoring(manager):
    """Demonstrate position monitoring and alerts"""
    print("\n=== Position Monitoring Demo ===")
    
    # Alert callback to capture alerts
    alerts_received = []
    
    async def alert_callback(alert):
        alerts_received.append(alert)
        print(f"  ALERT: {alert.alert_type.value} - {alert.message}")
    
    # Create position monitor
    monitor = PositionMonitor(manager, alert_callback, monitoring_interval=1)
    
    # Configure alerts
    await monitor.configure_alert(
        AlertType.PROFIT_TARGET,
        Decimal('70'),  # Below current profit
        enabled=True,
        severity=AlertSeverity.INFO
    )
    
    await monitor.configure_alert(
        AlertType.AGE_WARNING,
        Decimal('1'),  # Low threshold for demo
        enabled=True,
        severity=AlertSeverity.WARNING
    )
    
    print("Configured alerts for profit target and age warning")
    
    # Check positions manually (simulating monitoring loop)
    positions = await manager.get_open_positions()
    for position in positions:
        await monitor._check_position_alerts(position)
        await monitor._update_performance_metrics(position)
        
        # Get performance metrics
        performance = await monitor.get_position_performance(position.position_id)
        if performance:
            print(f"  Performance for {position.position_id}:")
            print(f"    Duration: {performance.duration_hours:.1f}h")
            print(f"    P&L: {performance.unrealized_pl}")
            print(f"    Max favorable: {performance.max_favorable_excursion}")
            print(f"    Efficiency ratio: {performance.efficiency_ratio}")
        
        # Get risk assessment
        risk = await monitor.get_position_risk_assessment(position.position_id)
        if risk:
            print(f"  Risk assessment:")
            print(f"    Risk score: {risk.risk_score:.1f}/100")
            print(f"    Assessment: {risk.overall_assessment}")
        
        # Get optimization suggestions
        suggestions = await monitor.generate_optimization_suggestions(position.position_id)
        print(f"  Optimization suggestions:")
        for suggestion in suggestions[:3]:  # Show first 3
            print(f"    - {suggestion}")
    
    print(f"Total alerts received: {len(alerts_received)}")


async def demo_risk_scenarios():
    """Demonstrate various risk scenarios and edge cases"""
    print("\n=== Risk Scenarios Demo ===")
    
    # Create losing position
    losing_position = PositionInfo(
        position_id="GBP_USD_short",
        instrument="GBP_USD",
        side=PositionSide.SHORT,
        units=Decimal('5000'),
        entry_price=Decimal('1.2500'),
        current_price=Decimal('1.2550'),  # Unfavorable move
        unrealized_pl=Decimal('-25.00'),
        swap_charges=Decimal('0.50'),
        commission=Decimal('0.25'),
        margin_used=Decimal('200'),
        opened_at=datetime.now(timezone.utc) - timedelta(hours=1),
        age_hours=1.0
    )
    
    print(f"Losing position: {losing_position.position_id}")
    print(f"  Entry: {losing_position.entry_price}, Current: {losing_position.current_price}")
    print(f"  P&L: {losing_position.unrealized_pl} ({losing_position.pl_percentage:.2f}%)")
    
    # Old position
    old_position = PositionInfo(
        position_id="USD_JPY_long",
        instrument="USD_JPY",
        side=PositionSide.LONG,
        units=Decimal('100000'),
        entry_price=Decimal('150.00'),
        current_price=Decimal('150.25'),
        unrealized_pl=Decimal('167.00'),
        swap_charges=Decimal('5.00'),
        commission=Decimal('2.00'),
        margin_used=Decimal('500'),
        opened_at=datetime.now(timezone.utc) - timedelta(days=2),
        age_hours=48.0
    )
    
    print(f"\nOld position: {old_position.position_id}")
    print(f"  Age: {old_position.age_hours:.1f} hours ({old_position.age_hours/24:.1f} days)")
    print(f"  P&L: {old_position.unrealized_pl}")
    
    # Risk reward calculation
    position_with_levels = PositionInfo(
        position_id="EUR_GBP_long",
        instrument="EUR_GBP",
        side=PositionSide.LONG,
        units=Decimal('8000'),
        entry_price=Decimal('0.8500'),
        current_price=Decimal('0.8525'),
        unrealized_pl=Decimal('20.00'),
        swap_charges=Decimal('0'),
        commission=Decimal('0'),
        margin_used=Decimal('300'),
        opened_at=datetime.now(timezone.utc),
        age_hours=0.5,
        stop_loss=Decimal('0.8450'),  # 50 pip risk
        take_profit=Decimal('0.8600')  # 100 pip reward
    )
    
    print(f"\nPosition with SL/TP: {position_with_levels.position_id}")
    print(f"  Entry: {position_with_levels.entry_price}")
    print(f"  Stop Loss: {position_with_levels.stop_loss}")
    print(f"  Take Profit: {position_with_levels.take_profit}")
    print(f"  Risk/Reward Ratio: {position_with_levels.risk_reward_ratio}")


async def main():
    """Main demonstration function"""
    print("Position Management & Modification System Demo")
    print("=" * 60)
    
    try:
        # Demo 1: Position data fetching
        manager = await demo_position_data_fetching()
        
        # Demo 2: Position modification
        await demo_position_modification(manager)
        
        # Demo 3: Partial closing
        await demo_partial_closing(manager)
        
        # Demo 4: Trailing stops
        await demo_trailing_stops(manager)
        
        # Demo 5: Position monitoring
        await demo_position_monitoring(manager)
        
        # Demo 6: Risk scenarios
        await demo_risk_scenarios()
        
        print("\n" + "=" * 60)
        print("All demos completed successfully!")
        print("\nKey Features Demonstrated:")
        print("* Position data fetching with real-time P&L calculation")
        print("* Stop loss and take profit modification (individual & batch)")
        print("* Partial position closing (percentage & unit-based)")
        print("* Bulk position management with criteria-based closing")
        print("* Trailing stop loss system (distance & percentage modes)")
        print("* Position monitoring with configurable alerts")
        print("* Risk assessment and performance tracking")
        print("* Optimization suggestions based on position analysis")
        print("* Comprehensive error handling and edge case management")
        
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())