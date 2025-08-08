"""
TradeLocker integration for Funding Pips compliance monitoring.
Provides real-time trade validation and monitoring through TradeLocker platform.
"""

import asyncio
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
import logging
import aiohttp
import websockets
from urllib.parse import urljoin

from pydantic import BaseModel, Field

from .models import Account, Trade, Position
from .funding_pips import FundingPipsCompliance
from .daily_loss_tracker import DailyLossTracker
from .static_drawdown_monitor import StaticDrawdownMonitor
from .stop_loss_enforcer import MandatoryStopLossEnforcer
from .weekend_closure import WeekendClosureAutomation
from .minimum_hold_time import MinimumHoldTimeEnforcer

logger = logging.getLogger(__name__)


class TradeLockerConfig(BaseModel):
    """TradeLocker API configuration."""
    base_url: str = "https://api.tradelocker.com/v1"
    websocket_url: str = "wss://api.tradelocker.com/v1/ws"
    api_key: str
    account_id: str
    environment: str = "live"  # live, demo, sandbox
    timeout_seconds: int = 30
    retry_attempts: int = 3
    rate_limit_per_second: int = 10


class TradeLockerEvent(BaseModel):
    """TradeLocker event model."""
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime
    account_id: str


class TradeValidationResult(BaseModel):
    """Trade validation result from TradeLocker."""
    approved: bool
    trade_id: Optional[str] = None
    rejection_reason: Optional[str] = None
    compliance_checks: Dict[str, bool]
    risk_assessment: Dict[str, Any]


class TradeLockerIntegration:
    """
    TradeLocker platform integration for Funding Pips compliance.
    
    Features:
    - Real-time trade validation before execution
    - WebSocket monitoring for position updates
    - Automatic stop-loss enforcement
    - Weekend closure coordination
    - Compliance event streaming
    """
    
    def __init__(self, config: TradeLockerConfig):
        """
        Initialize TradeLocker integration.
        
        Args:
            config: TradeLocker configuration
        """
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        
        # Initialize compliance components
        self.funding_pips = FundingPipsCompliance()
        self.daily_loss_tracker = DailyLossTracker()
        self.drawdown_monitor = StaticDrawdownMonitor()
        self.stop_loss_enforcer = MandatoryStopLossEnforcer()
        self.weekend_closure = WeekendClosureAutomation()
        self.hold_time_enforcer = MinimumHoldTimeEnforcer()
        
        # Connection state
        self.connected = False
        self.monitoring_active = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        
        # Event handlers
        self.event_handlers = {
            'trade_opened': self._handle_trade_opened,
            'trade_closed': self._handle_trade_closed,
            'trade_modified': self._handle_trade_modified,
            'balance_update': self._handle_balance_update,
            'margin_call': self._handle_margin_call,
            'connection_status': self._handle_connection_status
        }
        
        # Rate limiting
        self.request_timestamps = []
    
    async def initialize(self) -> None:
        """Initialize TradeLocker connection."""
        try:
            # Create aiohttp session
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'Authorization': f'Bearer {self.config.api_key}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'TMT-Compliance-Agent/1.0'
                }
            )
            
            # Test API connection
            await self._test_api_connection()
            
            # Start WebSocket monitoring
            await self._start_websocket_monitoring()
            
            self.connected = True
            logger.info("TradeLocker integration initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize TradeLocker integration: {e}")
            raise
    
    async def _test_api_connection(self) -> None:
        """Test API connection and authentication."""
        try:
            url = urljoin(self.config.base_url, "/accounts/info")
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Connected to TradeLocker account: {data.get('accountId')}")
                elif response.status == 401:
                    raise ValueError("Invalid API credentials")
                else:
                    raise ValueError(f"API connection failed: {response.status}")
                    
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            raise
    
    async def _start_websocket_monitoring(self) -> None:
        """Start WebSocket connection for real-time monitoring."""
        try:
            # Connect to WebSocket
            headers = {'Authorization': f'Bearer {self.config.api_key}'}
            
            self.websocket = await websockets.connect(
                self.config.websocket_url,
                extra_headers=headers,
                ping_interval=30,
                ping_timeout=10
            )
            
            # Subscribe to account events
            subscribe_message = {
                'action': 'subscribe',
                'topics': [
                    f'account.{self.config.account_id}.trades',
                    f'account.{self.config.account_id}.positions',
                    f'account.{self.config.account_id}.balance',
                    f'account.{self.config.account_id}.margin'
                ]
            }
            
            await self.websocket.send(json.dumps(subscribe_message))
            
            # Start monitoring task
            asyncio.create_task(self._websocket_listener())
            
            self.monitoring_active = True
            logger.info("WebSocket monitoring started")
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            await self._schedule_reconnect()
    
    async def _websocket_listener(self) -> None:
        """Listen for WebSocket events."""
        try:
            while self.monitoring_active and self.websocket:
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(), 
                        timeout=60
                    )
                    
                    # Parse and handle event
                    event_data = json.loads(message)
                    await self._handle_websocket_event(event_data)
                    
                    # Reset reconnect attempts on successful message
                    self.reconnect_attempts = 0
                    
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    await self.websocket.ping()
                    
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket connection closed")
                    await self._schedule_reconnect()
                    break
                    
        except Exception as e:
            logger.error(f"WebSocket listener error: {e}")
            await self._schedule_reconnect()
    
    async def _handle_websocket_event(self, event_data: Dict[str, Any]) -> None:
        """Handle incoming WebSocket event."""
        try:
            event_type = event_data.get('type')
            event_handler = self.event_handlers.get(event_type)
            
            if event_handler:
                await event_handler(event_data)
            else:
                logger.debug(f"Unhandled event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error handling WebSocket event: {e}")
    
    async def _schedule_reconnect(self) -> None:
        """Schedule WebSocket reconnection."""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            self.monitoring_active = False
            return
        
        self.reconnect_attempts += 1
        wait_time = min(300, 5 * (2 ** self.reconnect_attempts))  # Exponential backoff
        
        logger.info(f"Scheduling reconnection in {wait_time}s (attempt {self.reconnect_attempts})")
        await asyncio.sleep(wait_time)
        
        try:
            await self._start_websocket_monitoring()
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            await self._schedule_reconnect()
    
    async def validate_trade_pre_execution(self, account: Account, trade: Trade) -> TradeValidationResult:
        """
        Validate trade against all Funding Pips rules before execution.
        
        Args:
            account: Trading account
            trade: Trade to validate
            
        Returns:
            Validation result with compliance checks
        """
        try:
            compliance_checks = {}
            rejection_reasons = []
            
            # Funding Pips rules validation
            funding_pips_result = self.funding_pips.validate_trade(account, trade)
            compliance_checks['funding_pips_rules'] = funding_pips_result.approved
            
            if not funding_pips_result.approved:
                rejection_reasons.extend([v['message'] for v in funding_pips_result.violations])
            
            # Daily loss limit check
            daily_loss_allowed, daily_loss_reason = self.daily_loss_tracker.validate_trade_risk(account, trade)
            compliance_checks['daily_loss_limit'] = daily_loss_allowed
            
            if not daily_loss_allowed:
                rejection_reasons.append(daily_loss_reason)
            
            # Static drawdown check
            drawdown_allowed, drawdown_reason = self.drawdown_monitor.validate_trade_impact(account, trade)
            compliance_checks['static_drawdown'] = drawdown_allowed
            
            if not drawdown_allowed:
                rejection_reasons.append(drawdown_reason)
            
            # Stop loss validation
            stop_loss_result = self.stop_loss_enforcer.validate_trade_stop_loss(account, trade)
            compliance_checks['mandatory_stop_loss'] = stop_loss_result.valid
            
            if not stop_loss_result.valid:
                rejection_reasons.append(stop_loss_result.violation_reason)
            
            # Weekend closure check
            if self.weekend_closure.get_weekend_closure_status(account.account_id)['manual_override_active']:
                compliance_checks['weekend_trading'] = False
                rejection_reasons.append("Weekend trading not allowed")
            else:
                compliance_checks['weekend_trading'] = True
            
            # Overall approval decision
            approved = all(compliance_checks.values())
            
            # Calculate risk assessment
            risk_assessment = await self._calculate_trade_risk_assessment(account, trade)
            
            result = TradeValidationResult(
                approved=approved,
                rejection_reason='; '.join(rejection_reasons) if rejection_reasons else None,
                compliance_checks=compliance_checks,
                risk_assessment=risk_assessment
            )
            
            # Log validation result
            if approved:
                logger.info(f"Trade validation passed for {trade.symbol}")
            else:
                logger.warning(f"Trade validation failed for {trade.symbol}: {result.rejection_reason}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating trade: {e}")
            return TradeValidationResult(
                approved=False,
                rejection_reason=f"Validation error: {str(e)}",
                compliance_checks={},
                risk_assessment={}
            )
    
    async def submit_trade_with_compliance(self, account: Account, trade: Trade) -> Dict[str, Any]:
        """
        Submit trade to TradeLocker with compliance validation.
        
        Args:
            account: Trading account
            trade: Trade to submit
            
        Returns:
            Trade submission result
        """
        try:
            # Pre-execution validation
            validation_result = await self.validate_trade_pre_execution(account, trade)
            
            if not validation_result.approved:
                return {
                    'success': False,
                    'error': 'Compliance validation failed',
                    'details': validation_result.dict(),
                    'trade_id': None
                }
            
            # Auto-calculate stop loss if missing
            if not trade.stop_loss and self.stop_loss_enforcer.config.auto_calculate:
                calculated_sl = self.stop_loss_enforcer._calculate_optimal_stop_loss(account, trade)
                trade.stop_loss = calculated_sl
                logger.info(f"Auto-calculated stop loss: {calculated_sl}")
            
            # Submit to TradeLocker
            trade_submission = await self._submit_to_tradelocker(trade)
            
            if trade_submission['success']:
                # Start hold time tracking
                if 'position_id' in trade_submission:
                    position = Position(
                        position_id=trade_submission['position_id'],
                        account_id=account.account_id,
                        symbol=trade.symbol,
                        direction=trade.direction,
                        size=trade.position_size,
                        entry_price=trade.entry_price,
                        stop_loss=trade.stop_loss,
                        open_time=datetime.utcnow(),
                        unrealized_pnl=Decimal('0.0')
                    )
                    
                    self.hold_time_enforcer.track_position_open(position)
                
                # Update daily loss tracker
                await self.daily_loss_tracker.update_daily_pnl(account, Decimal('0'))  # No P&L yet
                
                logger.info(f"Trade submitted successfully: {trade_submission['trade_id']}")
            
            return trade_submission
            
        except Exception as e:
            logger.error(f"Error submitting trade: {e}")
            return {
                'success': False,
                'error': f'Submission error: {str(e)}',
                'trade_id': None
            }
    
    async def _submit_to_tradelocker(self, trade: Trade) -> Dict[str, Any]:
        """Submit trade to TradeLocker platform."""
        try:
            await self._rate_limit_check()
            
            url = urljoin(self.config.base_url, "/trades")
            
            payload = {
                'symbol': trade.symbol,
                'side': 'buy' if trade.direction.lower() == 'buy' else 'sell',
                'volume': float(trade.position_size),
                'type': 'market',  # Could be configurable
                'stopLoss': float(trade.stop_loss) if trade.stop_loss else None,
                'takeProfit': float(trade.take_profit) if trade.take_profit else None
            }
            
            async with self.session.post(url, json=payload) as response:
                response_data = await response.json()
                
                if response.status == 200:
                    return {
                        'success': True,
                        'trade_id': response_data.get('tradeId'),
                        'position_id': response_data.get('positionId'),
                        'execution_price': response_data.get('executionPrice'),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        'success': False,
                        'error': response_data.get('message', 'Unknown error'),
                        'status_code': response.status
                    }
                    
        except Exception as e:
            logger.error(f"TradeLocker submission error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def close_position_with_compliance(self, account: Account, position: Position, 
                                           reason: str = "manual") -> Dict[str, Any]:
        """
        Close position with compliance checks.
        
        Args:
            account: Trading account
            position: Position to close
            reason: Reason for closure
            
        Returns:
            Closure result
        """
        try:
            # Check hold time compliance
            allowed, rejection_reason, seconds_remaining = self.hold_time_enforcer.validate_closure_request(
                position, reason
            )
            
            if not allowed:
                return {
                    'success': False,
                    'error': 'Hold time violation',
                    'details': {
                        'reason': rejection_reason,
                        'seconds_remaining': seconds_remaining
                    }
                }
            
            # Submit closure to TradeLocker
            closure_result = await self._close_position_tradelocker(position.position_id)
            
            if closure_result['success']:
                # Clean up tracking
                self.hold_time_enforcer.cleanup_closed_positions([position.position_id])
                
                logger.info(f"Position closed successfully: {position.position_id}")
            
            return closure_result
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _close_position_tradelocker(self, position_id: str) -> Dict[str, Any]:
        """Close position on TradeLocker platform."""
        try:
            await self._rate_limit_check()
            
            url = urljoin(self.config.base_url, f"/positions/{position_id}/close")
            
            async with self.session.post(url) as response:
                response_data = await response.json()
                
                if response.status == 200:
                    return {
                        'success': True,
                        'closure_price': response_data.get('closurePrice'),
                        'pnl': response_data.get('pnl'),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        'success': False,
                        'error': response_data.get('message', 'Unknown error'),
                        'status_code': response.status
                    }
                    
        except Exception as e:
            logger.error(f"TradeLocker closure error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _calculate_trade_risk_assessment(self, account: Account, trade: Trade) -> Dict[str, Any]:
        """Calculate comprehensive risk assessment for trade."""
        try:
            risk_amount = Decimal('0')
            if trade.stop_loss:
                risk_amount = abs(trade.entry_price - trade.stop_loss) * trade.position_size
            
            risk_percentage = float((risk_amount / account.balance) * 100) if account.balance > 0 else 0
            
            # Calculate potential daily loss impact
            current_daily_loss = abs(account.daily_pnl)
            potential_daily_loss = current_daily_loss + risk_amount
            daily_loss_percentage = float((potential_daily_loss / account.initial_balance) * 100)
            
            # Calculate drawdown impact
            current_equity = account.balance + account.unrealized_pnl
            potential_equity_after_loss = current_equity - risk_amount
            potential_drawdown = (account.initial_balance - potential_equity_after_loss) / account.initial_balance
            
            return {
                'risk_amount': float(risk_amount),
                'risk_percentage': risk_percentage,
                'daily_loss_impact': daily_loss_percentage,
                'drawdown_impact': float(potential_drawdown * 100),
                'risk_rating': self._calculate_risk_rating(risk_percentage, daily_loss_impact, potential_drawdown),
                'leverage': self._calculate_effective_leverage(trade, account.balance),
                'position_size_rating': self._rate_position_size(trade.position_size, account.balance)
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk assessment: {e}")
            return {}
    
    def _calculate_risk_rating(self, risk_pct: float, daily_loss_pct: float, drawdown_pct: float) -> str:
        """Calculate overall risk rating."""
        if risk_pct >= 2.0 or daily_loss_pct >= 3.8 or drawdown_pct >= 0.075:
            return "high"
        elif risk_pct >= 1.5 or daily_loss_pct >= 3.2 or drawdown_pct >= 0.06:
            return "medium"
        else:
            return "low"
    
    def _calculate_effective_leverage(self, trade: Trade, balance: Decimal) -> float:
        """Calculate effective leverage for trade."""
        position_value = trade.position_size * trade.entry_price
        return float(position_value / balance) if balance > 0 else 0
    
    def _rate_position_size(self, position_size: Decimal, balance: Decimal) -> str:
        """Rate position size relative to account."""
        size_ratio = position_size * 100000 / balance  # Assuming standard lot size
        
        if size_ratio >= 0.02:  # 2% per lot
            return "large"
        elif size_ratio >= 0.01:  # 1% per lot
            return "medium"
        else:
            return "small"
    
    async def _rate_limit_check(self) -> None:
        """Check and enforce rate limiting."""
        now = datetime.utcnow()
        
        # Remove old timestamps (older than 1 second)
        self.request_timestamps = [
            ts for ts in self.request_timestamps 
            if (now - ts).total_seconds() < 1.0
        ]
        
        # Check if we're at the rate limit
        if len(self.request_timestamps) >= self.config.rate_limit_per_second:
            sleep_time = 1.0 - (now - self.request_timestamps[0]).total_seconds()
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # Add current timestamp
        self.request_timestamps.append(now)
    
    # Event handlers
    
    async def _handle_trade_opened(self, event_data: Dict[str, Any]) -> None:
        """Handle trade opened event."""
        try:
            position_data = event_data.get('data', {})
            position = Position(
                position_id=position_data.get('positionId'),
                account_id=self.config.account_id,
                symbol=position_data.get('symbol'),
                direction=position_data.get('side'),
                size=Decimal(str(position_data.get('volume', 0))),
                entry_price=Decimal(str(position_data.get('openPrice', 0))),
                stop_loss=Decimal(str(position_data.get('stopLoss'))) if position_data.get('stopLoss') else None,
                open_time=datetime.utcnow(),
                unrealized_pnl=Decimal('0.0')
            )
            
            # Start hold time tracking
            self.hold_time_enforcer.track_position_open(position)
            
            logger.info(f"Position opened: {position.position_id}")
            
        except Exception as e:
            logger.error(f"Error handling trade opened event: {e}")
    
    async def _handle_trade_closed(self, event_data: Dict[str, Any]) -> None:
        """Handle trade closed event."""
        try:
            position_data = event_data.get('data', {})
            position_id = position_data.get('positionId')
            pnl = Decimal(str(position_data.get('pnl', 0)))
            
            # Update daily P&L
            account = await self._get_account_from_tradelocker()
            if account:
                await self.daily_loss_tracker.update_daily_pnl(account, pnl)
            
            # Clean up tracking
            self.hold_time_enforcer.cleanup_closed_positions([position_id])
            
            logger.info(f"Position closed: {position_id}, P&L: {pnl}")
            
        except Exception as e:
            logger.error(f"Error handling trade closed event: {e}")
    
    async def _handle_trade_modified(self, event_data: Dict[str, Any]) -> None:
        """Handle trade modified event."""
        try:
            logger.info("Trade modified event received")
        except Exception as e:
            logger.error(f"Error handling trade modified event: {e}")
    
    async def _handle_balance_update(self, event_data: Dict[str, Any]) -> None:
        """Handle balance update event."""
        try:
            balance_data = event_data.get('data', {})
            new_balance = Decimal(str(balance_data.get('balance', 0)))
            
            logger.info(f"Balance updated: {new_balance}")
            
        except Exception as e:
            logger.error(f"Error handling balance update event: {e}")
    
    async def _handle_margin_call(self, event_data: Dict[str, Any]) -> None:
        """Handle margin call event."""
        try:
            logger.critical("MARGIN CALL received from TradeLocker")
            
            # Trigger emergency procedures
            # This would integrate with circuit breaker system
            
        except Exception as e:
            logger.error(f"Error handling margin call event: {e}")
    
    async def _handle_connection_status(self, event_data: Dict[str, Any]) -> None:
        """Handle connection status event."""
        try:
            status = event_data.get('data', {}).get('status')
            logger.info(f"TradeLocker connection status: {status}")
            
        except Exception as e:
            logger.error(f"Error handling connection status event: {e}")
    
    async def _get_account_from_tradelocker(self) -> Optional[Account]:
        """Get current account data from TradeLocker."""
        try:
            await self._rate_limit_check()
            
            url = urljoin(self.config.base_url, "/accounts/info")
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    return Account(
                        account_id=self.config.account_id,
                        prop_firm="Funding Pips",
                        balance=Decimal(str(data.get('balance', 0))),
                        initial_balance=Decimal(str(data.get('initialBalance', 0))),
                        daily_pnl=Decimal(str(data.get('dailyPnL', 0))),
                        unrealized_pnl=Decimal(str(data.get('unrealizedPnL', 0))),
                        daily_trades_count=data.get('dailyTrades', 0)
                    )
                    
        except Exception as e:
            logger.error(f"Error getting account data: {e}")
        
        return None
    
    async def get_integration_status(self) -> Dict[str, Any]:
        """Get TradeLocker integration status."""
        return {
            'connected': self.connected,
            'monitoring_active': self.monitoring_active,
            'websocket_connected': self.websocket is not None and not self.websocket.closed,
            'reconnect_attempts': self.reconnect_attempts,
            'last_heartbeat': datetime.utcnow().isoformat(),
            'config': {
                'environment': self.config.environment,
                'account_id': self.config.account_id,
                'rate_limit': self.config.rate_limit_per_second
            }
        }
    
    async def shutdown(self) -> None:
        """Shutdown TradeLocker integration."""
        try:
            self.monitoring_active = False
            
            if self.websocket:
                await self.websocket.close()
            
            if self.session:
                await self.session.close()
            
            logger.info("TradeLocker integration shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")