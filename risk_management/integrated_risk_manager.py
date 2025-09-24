"""
Integrated Risk Management System
Combines tail risk controls with existing risk management
"""

import asyncio
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from tail_risk_controls import TailRiskController, TailRiskLevel
from agents.market_analysis.config import (
    ParameterMode, get_current_parameters, emergency_rollback
)

logger = logging.getLogger(__name__)

class IntegratedRiskManager:
    """Unified risk management system with tail risk controls"""

    def __init__(self, config: Dict):
        self.config = config

        # Initialize tail risk controller
        self.tail_risk_controller = TailRiskController(config)

        # Risk limits (calibrated for September 2025 issues)
        self.risk_limits = {
            'max_daily_loss': config.get('max_daily_loss', 2000),
            'max_position_size': config.get('max_position_size', 10000),
            'max_concurrent_positions': config.get('max_concurrent_positions', 5),
            'max_leverage': config.get('max_leverage', 10),
            'max_correlation_exposure': config.get('max_correlation_exposure', 0.7)
        }

        # Current state
        self.daily_pnl = 0.0
        self.open_positions = {}
        self.recent_trades = []
        self.is_trading_halted = False
        self.halt_reason = ""

        # Monitoring
        self.last_risk_check = datetime.utcnow()
        self.risk_events = []

    async def pre_trade_risk_check(self, trade_request: Dict) -> Tuple[bool, Dict]:
        """Comprehensive pre-trade risk validation"""

        logger.info(f"Pre-trade risk check for {trade_request.get('instrument', 'Unknown')}")

        # Initialize response
        risk_check_result = {
            'approved': True,
            'adjusted_size': trade_request.get('size', 0),
            'stop_loss': None,
            'checks': {},
            'warnings': [],
            'rejections': []
        }

        # 1. Check if trading is halted
        if self.is_trading_halted:
            risk_check_result['approved'] = False
            risk_check_result['rejections'].append(f"Trading halted: {self.halt_reason}")
            return False, risk_check_result

        # 2. Tail risk check
        should_halt, halt_reason = self.tail_risk_controller.should_halt_trading()
        if should_halt:
            risk_check_result['approved'] = False
            risk_check_result['rejections'].append(f"Tail risk halt: {halt_reason}")
            self.halt_trading(halt_reason)
            return False, risk_check_result

        risk_check_result['checks']['tail_risk'] = 'PASS'

        # 3. Daily loss limit check
        if abs(self.daily_pnl) >= self.risk_limits['max_daily_loss']:
            risk_check_result['approved'] = False
            risk_check_result['rejections'].append(
                f"Daily loss limit reached: ${abs(self.daily_pnl):.0f} >= ${self.risk_limits['max_daily_loss']}"
            )
            return False, risk_check_result

        risk_check_result['checks']['daily_loss'] = 'PASS'

        # 4. Position limit check
        if len(self.open_positions) >= self.risk_limits['max_concurrent_positions']:
            risk_check_result['approved'] = False
            risk_check_result['rejections'].append(
                f"Max positions reached: {len(self.open_positions)}/{self.risk_limits['max_concurrent_positions']}"
            )
            return False, risk_check_result

        risk_check_result['checks']['position_limit'] = 'PASS'

        # 5. Consecutive loss check
        trade_allowed = self.tail_risk_controller.check_max_consecutive_losses(
            {'pnl': 0}  # Placeholder - actual P&L tracked post-trade
        )
        if not trade_allowed:
            risk_check_result['approved'] = False
            risk_check_result['rejections'].append(
                f"Consecutive losses exceed limit: {self.tail_risk_controller.consecutive_losses}"
            )
            return False, risk_check_result

        risk_check_result['checks']['consecutive_losses'] = 'PASS'

        # 6. Position size adjustment for tail risk
        base_size = trade_request.get('size', self.risk_limits['max_position_size'])
        instrument = trade_request.get('instrument', 'Unknown')
        current_price = trade_request.get('price', 1.0)

        size_adjustment = self.tail_risk_controller.calculate_position_size_adjustment(
            base_size, instrument, current_price
        )

        adjusted_size = size_adjustment.final_size
        risk_check_result['adjusted_size'] = adjusted_size

        # Add warning if size was reduced
        if adjusted_size < base_size * 0.9:
            risk_check_result['warnings'].append(
                f"Position size reduced {(1-adjusted_size/base_size)*100:.0f}% due to: {size_adjustment.reduction_reason}"
            )

        risk_check_result['checks']['position_sizing'] = 'ADJUSTED'

        # 7. Calculate dynamic stop loss
        direction = trade_request.get('direction', 'long')
        atr = trade_request.get('atr', current_price * 0.001)  # Default 0.1% if not provided

        stop_loss = self.tail_risk_controller.calculate_dynamic_stop_loss(
            current_price, direction, atr
        )

        risk_check_result['stop_loss'] = {
            'price': stop_loss.stop_price,
            'distance': stop_loss.final_stop_distance,
            'protection_level': stop_loss.protection_level
        }

        risk_check_result['checks']['stop_loss'] = 'CALCULATED'

        # 8. Check correlation exposure
        correlation_exposure = self._calculate_correlation_exposure(instrument)
        if correlation_exposure > self.risk_limits['max_correlation_exposure']:
            risk_check_result['warnings'].append(
                f"High correlation exposure: {correlation_exposure:.2f}"
            )
            # Reduce size further for correlation risk
            adjusted_size *= 0.7
            risk_check_result['adjusted_size'] = adjusted_size

        risk_check_result['checks']['correlation'] = 'PASS' if correlation_exposure <= 0.7 else 'WARNING'

        # 9. Extreme event check
        if self.tail_risk_controller.extreme_events_24h >= 2:
            risk_check_result['warnings'].append(
                f"Multiple extreme events today: {self.tail_risk_controller.extreme_events_24h}"
            )

        # 10. Final approval
        if risk_check_result['rejections']:
            risk_check_result['approved'] = False
        else:
            risk_check_result['approved'] = True

        # Log risk check result
        logger.info(f"Risk check result: Approved={risk_check_result['approved']}, "
                   f"Size={base_size:.0f}->{adjusted_size:.0f}")

        return risk_check_result['approved'], risk_check_result

    async def post_trade_update(self, trade_result: Dict):
        """Update risk metrics after trade completion"""

        # Update daily P&L
        pnl = trade_result.get('pnl', 0)
        self.daily_pnl += pnl

        # Update recent trades
        self.recent_trades.append(trade_result)
        if len(self.recent_trades) > 100:
            self.recent_trades = self.recent_trades[-100:]

        # Update tail risk metrics
        returns_series = pd.Series([t['pnl'] for t in self.recent_trades])
        self.tail_risk_controller.calculate_tail_risk_metrics(returns_series)

        # Check for extreme event
        if abs(pnl) > 0:
            return_pct = pnl / trade_result.get('position_value', 10000)
            is_extreme = self.tail_risk_controller.detect_extreme_event(return_pct)

            if is_extreme:
                await self._handle_extreme_event(trade_result)

        # Update consecutive losses
        self.tail_risk_controller.check_max_consecutive_losses(trade_result)

        # Check if we need to trigger emergency measures
        await self._check_emergency_conditions()

        # Update open positions
        if trade_result.get('action') == 'open':
            self.open_positions[trade_result['trade_id']] = trade_result
        elif trade_result.get('action') == 'close':
            self.open_positions.pop(trade_result.get('trade_id'), None)

    async def _handle_extreme_event(self, trade_result: Dict):
        """Handle extreme event detection"""

        logger.warning(f"Extreme event detected: {trade_result}")

        # Add to risk events
        self.risk_events.append({
            'timestamp': datetime.utcnow(),
            'type': 'extreme_event',
            'details': trade_result
        })

        # Check if we need to reduce exposure
        if self.tail_risk_controller.extreme_events_24h >= 3:
            logger.critical("Multiple extreme events - triggering protective measures")

            # Switch to emergency conservative parameters
            from agents.market_analysis.config import emergency_rollback
            emergency_rollback("Multiple extreme events detected")

            # Notify all systems
            await self._notify_emergency_mode()

    async def _check_emergency_conditions(self):
        """Check for emergency conditions requiring immediate action"""

        emergency_triggered = False
        emergency_reasons = []

        # Check tail risk metrics
        if self.tail_risk_controller.current_metrics:
            metrics = self.tail_risk_controller.current_metrics

            # Critical kurtosis (like September 2025)
            if metrics.kurtosis > 20:
                emergency_triggered = True
                emergency_reasons.append(f"Critical kurtosis: {metrics.kurtosis:.1f}")

            # Severe drawdown
            if metrics.max_drawdown_24h < -0.08:
                emergency_triggered = True
                emergency_reasons.append(f"Severe drawdown: {metrics.max_drawdown_24h:.1%}")

        # Check daily loss
        if abs(self.daily_pnl) > self.risk_limits['max_daily_loss'] * 1.5:
            emergency_triggered = True
            emergency_reasons.append(f"Extreme daily loss: ${abs(self.daily_pnl):.0f}")

        # Check consecutive losses
        if self.tail_risk_controller.consecutive_losses >= 12:
            emergency_triggered = True
            emergency_reasons.append(f"Excessive consecutive losses: {self.tail_risk_controller.consecutive_losses}")

        if emergency_triggered:
            logger.critical(f"EMERGENCY CONDITIONS DETECTED: {', '.join(emergency_reasons)}")
            await self._activate_emergency_protocol(emergency_reasons)

    async def _activate_emergency_protocol(self, reasons: List[str]):
        """Activate emergency risk protocol"""

        logger.critical("ACTIVATING EMERGENCY RISK PROTOCOL")

        # 1. Halt all trading
        self.halt_trading(f"Emergency: {', '.join(reasons)}")

        # 2. Switch to emergency conservative parameters
        emergency_rollback(f"Emergency protocol: {reasons[0]}")

        # 3. Close high-risk positions
        await self._close_high_risk_positions()

        # 4. Notify all systems
        await self._notify_emergency_mode()

        # 5. Log emergency event
        self.risk_events.append({
            'timestamp': datetime.utcnow(),
            'type': 'emergency_protocol',
            'reasons': reasons,
            'actions': [
                'Trading halted',
                'Emergency parameters activated',
                'High-risk positions closed'
            ]
        })

    async def _close_high_risk_positions(self):
        """Close positions with high risk exposure"""

        logger.info("Closing high-risk positions...")

        positions_to_close = []

        for trade_id, position in self.open_positions.items():
            # Criteria for high-risk positions
            if (abs(position.get('unrealized_pnl', 0)) > 1000 or
                position.get('leverage', 1) > 5 or
                position.get('time_open_hours', 0) > 24):

                positions_to_close.append(trade_id)
                logger.info(f"Marking position {trade_id} for closure")

        # Note: Actual closure would be handled by execution engine
        return positions_to_close

    async def _notify_emergency_mode(self):
        """Notify all systems of emergency mode activation"""

        notification = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'EMERGENCY_MODE_ACTIVATED',
            'tail_risk_level': self.tail_risk_controller.current_metrics.tail_risk_level.value
            if self.tail_risk_controller.current_metrics else 'UNKNOWN',
            'consecutive_losses': self.tail_risk_controller.consecutive_losses,
            'daily_pnl': self.daily_pnl,
            'actions': [
                'Trading halted',
                'Emergency parameters active',
                'High-risk positions flagged'
            ]
        }

        logger.critical(f"EMERGENCY NOTIFICATION: {notification}")
        # In production, this would send alerts to all connected systems

    def _calculate_correlation_exposure(self, instrument: str) -> float:
        """Calculate correlation exposure across positions"""

        if not self.open_positions:
            return 0.0

        # Simplified correlation calculation
        # In production, use actual correlation matrix
        correlated_pairs = {
            'EUR_USD': ['GBP_USD', 'EUR_GBP'],
            'GBP_USD': ['EUR_USD', 'EUR_GBP'],
            'USD_JPY': ['EUR_JPY', 'GBP_JPY'],
            'AUD_USD': ['NZD_USD', 'AUD_NZD'],
            'USD_CHF': ['EUR_CHF', 'GBP_CHF']
        }

        correlated_count = 0
        for _, position in self.open_positions.items():
            pos_instrument = position.get('instrument', '')
            if pos_instrument in correlated_pairs.get(instrument, []):
                correlated_count += 1

        correlation_exposure = correlated_count / max(1, len(self.open_positions))
        return correlation_exposure

    def halt_trading(self, reason: str):
        """Halt all trading"""
        self.is_trading_halted = True
        self.halt_reason = reason
        logger.critical(f"TRADING HALTED: {reason}")

    def resume_trading(self, authorization: str):
        """Resume trading after halt"""
        self.is_trading_halted = False
        self.halt_reason = ""
        logger.info(f"Trading resumed: {authorization}")

    def reset_daily_metrics(self):
        """Reset daily metrics (call at start of trading day)"""
        self.daily_pnl = 0.0
        self.tail_risk_controller.extreme_events_24h = 0
        logger.info("Daily risk metrics reset")

    def get_risk_status(self) -> Dict[str, Any]:
        """Get comprehensive risk status"""

        tail_risk_summary = self.tail_risk_controller.get_risk_summary()

        return {
            'timestamp': datetime.utcnow().isoformat(),
            'trading_halted': self.is_trading_halted,
            'halt_reason': self.halt_reason,
            'daily_pnl': self.daily_pnl,
            'open_positions': len(self.open_positions),
            'consecutive_losses': self.tail_risk_controller.consecutive_losses,
            'tail_risk': tail_risk_summary,
            'risk_limits': self.risk_limits,
            'risk_events_24h': len([e for e in self.risk_events
                                    if e['timestamp'] > datetime.utcnow() - timedelta(hours=24)]),
            'emergency_mode': self.tail_risk_controller.emergency_mode
        }

# Example usage
async def test_integrated_risk_manager():
    """Test integrated risk management"""

    print("INTEGRATED RISK MANAGER TEST")
    print("=" * 50)

    config = {
        'max_daily_loss': 2000,
        'max_position_size': 10000,
        'max_concurrent_positions': 5,
        'max_kurtosis': 20.0
    }

    risk_manager = IntegratedRiskManager(config)

    # Test trade request
    trade_request = {
        'instrument': 'EUR_USD',
        'size': 10000,
        'price': 1.1000,
        'direction': 'long',
        'atr': 0.0010
    }

    # Pre-trade risk check
    approved, risk_result = await risk_manager.pre_trade_risk_check(trade_request)

    print(f"\nPRE-TRADE RISK CHECK:")
    print(f"  Approved: {approved}")
    print(f"  Original Size: ${trade_request['size']:,.0f}")
    print(f"  Adjusted Size: ${risk_result['adjusted_size']:,.0f}")

    if risk_result['stop_loss']:
        print(f"  Stop Loss: {risk_result['stop_loss']['price']:.4f}")
        print(f"  Protection: {risk_result['stop_loss']['protection_level']}")

    if risk_result['warnings']:
        print(f"  Warnings:")
        for warning in risk_result['warnings']:
            print(f"    - {warning}")

    # Simulate some trades with tail risk
    test_trades = [
        {'trade_id': '1', 'pnl': 150, 'action': 'close'},
        {'trade_id': '2', 'pnl': -200, 'action': 'close'},
        {'trade_id': '3', 'pnl': -180, 'action': 'close'},
        {'trade_id': '4', 'pnl': -8000, 'action': 'close'},  # Extreme loss
        {'trade_id': '5', 'pnl': 300, 'action': 'close'}
    ]

    print(f"\nSIMULATING TRADES:")
    for trade in test_trades:
        await risk_manager.post_trade_update(trade)
        print(f"  Trade P&L: ${trade['pnl']:+.0f}, Daily Total: ${risk_manager.daily_pnl:+.0f}")

    # Get final risk status
    status = risk_manager.get_risk_status()

    print(f"\nFINAL RISK STATUS:")
    print(f"  Trading Halted: {status['trading_halted']}")
    print(f"  Daily P&L: ${status['daily_pnl']:+.0f}")
    print(f"  Consecutive Losses: {status['consecutive_losses']}")
    print(f"  Tail Risk Level: {status['tail_risk'].get('tail_risk_level', 'N/A')}")
    print(f"  Emergency Mode: {status['emergency_mode']}")

    print("\n" + "=" * 50)
    print("Test complete")

if __name__ == "__main__":
    asyncio.run(test_integrated_risk_manager())