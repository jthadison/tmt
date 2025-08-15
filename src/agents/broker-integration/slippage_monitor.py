"""
Slippage Monitoring System
Story 8.3 - Task 4: Implement slippage monitoring

Real-time slippage calculation, alerting, and analytics for order execution quality.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass
from collections import defaultdict
import statistics

try:
    from .order_executor import OrderResult, OrderSide, OrderStatus
except ImportError:
    from order_executor import OrderResult, OrderSide, OrderStatus

logger = logging.getLogger(__name__)

@dataclass
class SlippageAlert:
    """Slippage alert data"""
    instrument: str
    timestamp: datetime
    expected_price: Decimal
    actual_price: Decimal
    slippage: Decimal
    slippage_bps: int  # basis points
    threshold_bps: int
    order_id: str
    alert_level: str  # INFO, WARNING, CRITICAL

@dataclass
class SlippageStats:
    """Slippage statistics for an instrument"""
    instrument: str
    period_hours: int
    total_trades: int
    average_slippage_bps: float
    median_slippage_bps: float
    max_slippage_bps: float
    min_slippage_bps: float
    std_dev_slippage_bps: float
    slippage_95_percentile: float
    negative_slippage_count: int  # Better execution than expected
    positive_slippage_count: int  # Worse execution than expected
    quality_score: float  # 0-100, higher is better

class SlippageMonitor:
    """Advanced slippage monitoring and analysis system"""
    
    def __init__(self, price_feed_service=None):
        self.price_feed = price_feed_service
        self.slippage_history: Dict[str, List[Dict]] = defaultdict(list)
        self.alert_callbacks: List[callable] = []
        
        # Alert thresholds in basis points (1 bp = 0.01%)
        self.alert_thresholds = {
            'INFO': 10,      # 1 pip for most pairs
            'WARNING': 20,   # 2 pips 
            'CRITICAL': 50   # 5 pips
        }
        
        # Instrument-specific pip values (for major pairs)
        self.pip_values = {
            'EUR_USD': Decimal('0.0001'),
            'GBP_USD': Decimal('0.0001'),
            'USD_JPY': Decimal('0.01'),
            'USD_CHF': Decimal('0.0001'),
            'AUD_USD': Decimal('0.0001'),
            'USD_CAD': Decimal('0.0001'),
            'NZD_USD': Decimal('0.0001'),
            'EUR_GBP': Decimal('0.0001'),
            'EUR_JPY': Decimal('0.01'),
            'GBP_JPY': Decimal('0.01'),
        }
        
        # Default pip value for unknown instruments
        self.default_pip_value = Decimal('0.0001')
    
    async def record_execution(
        self, 
        order: OrderResult, 
        expected_price: Optional[Decimal] = None,
        market_price_at_signal: Optional[Decimal] = None
    ):
        """
        Record order execution for slippage analysis
        
        Args:
            order: Order execution result
            expected_price: Expected execution price (from signal)
            market_price_at_signal: Market price when signal was generated
        """
        if order.status != OrderStatus.FILLED or not order.fill_price:
            return
        
        # Determine expected price for slippage calculation
        if expected_price:
            reference_price = expected_price
        elif market_price_at_signal:
            reference_price = market_price_at_signal
        else:
            # If no expected price provided, try to get current market price
            reference_price = await self._get_market_price(order.instrument)
            if not reference_price:
                logger.warning(f"Cannot calculate slippage for {order.client_order_id} - no reference price")
                return
        
        # Calculate slippage
        actual_price = order.fill_price
        slippage = self._calculate_slippage(
            reference_price, actual_price, order.side, order.instrument
        )
        
        # Convert to basis points
        slippage_bps = self._to_basis_points(slippage, reference_price)
        
        # Create slippage record
        slippage_record = {
            'timestamp': order.timestamp,
            'order_id': order.client_order_id,
            'instrument': order.instrument,
            'side': order.side,
            'units': order.units,
            'expected_price': reference_price,
            'actual_price': actual_price,
            'slippage': slippage,
            'slippage_bps': slippage_bps,
            'execution_time_ms': order.execution_time_ms
        }
        
        # Store record
        self.slippage_history[order.instrument].append(slippage_record)
        
        # Maintain history size (keep last 10,000 records per instrument)
        if len(self.slippage_history[order.instrument]) > 10000:
            self.slippage_history[order.instrument] = \
                self.slippage_history[order.instrument][-10000:]
        
        # Check for alerts
        await self._check_slippage_alerts(slippage_record)
        
        logger.debug(f"Recorded slippage for {order.client_order_id}: {slippage_bps:.1f} bps")
    
    def _calculate_slippage(
        self, 
        expected_price: Decimal, 
        actual_price: Decimal, 
        side: OrderSide,
        instrument: str
    ) -> Decimal:
        """
        Calculate slippage based on order side
        
        For BUY orders: positive slippage means paying more than expected
        For SELL orders: positive slippage means receiving less than expected
        """
        if side == OrderSide.BUY:
            # Buy: positive slippage = paid more than expected
            slippage = actual_price - expected_price
        else:
            # Sell: positive slippage = received less than expected  
            slippage = expected_price - actual_price
        
        return slippage
    
    def _to_basis_points(self, slippage: Decimal, price: Decimal) -> float:
        """Convert slippage to basis points (1 bp = 0.01%)"""
        if price == 0:
            return 0.0
        return float((slippage / price) * 10000)
    
    def _get_pip_value(self, instrument: str) -> Decimal:
        """Get pip value for instrument"""
        return self.pip_values.get(instrument, self.default_pip_value)
    
    async def _get_market_price(self, instrument: str) -> Optional[Decimal]:
        """Get current market price from price feed"""
        if not self.price_feed:
            return None
        
        try:
            # This would integrate with a real-time price feed
            # For now, return None to indicate price unavailable
            return None
        except Exception as e:
            logger.error(f"Failed to get market price for {instrument}: {e}")
            return None
    
    async def _check_slippage_alerts(self, record: Dict):
        """Check if slippage exceeds alert thresholds"""
        slippage_bps = abs(record['slippage_bps'])
        
        alert_level = None
        threshold_bps = 0
        
        if slippage_bps >= self.alert_thresholds['CRITICAL']:
            alert_level = 'CRITICAL'
            threshold_bps = self.alert_thresholds['CRITICAL']
        elif slippage_bps >= self.alert_thresholds['WARNING']:
            alert_level = 'WARNING' 
            threshold_bps = self.alert_thresholds['WARNING']
        elif slippage_bps >= self.alert_thresholds['INFO']:
            alert_level = 'INFO'
            threshold_bps = self.alert_thresholds['INFO']
        
        if alert_level:
            alert = SlippageAlert(
                instrument=record['instrument'],
                timestamp=record['timestamp'],
                expected_price=record['expected_price'],
                actual_price=record['actual_price'],
                slippage=record['slippage'],
                slippage_bps=int(slippage_bps),
                threshold_bps=threshold_bps,
                order_id=record['order_id'],
                alert_level=alert_level
            )
            
            await self._send_slippage_alert(alert)
    
    async def _send_slippage_alert(self, alert: SlippageAlert):
        """Send slippage alert to registered callbacks"""
        logger.warning(
            f"Slippage alert ({alert.alert_level}): {alert.instrument} "
            f"slippage {alert.slippage_bps} bps (threshold: {alert.threshold_bps} bps) "
            f"for order {alert.order_id}"
        )
        
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"Error sending slippage alert: {e}")
    
    def add_alert_callback(self, callback: callable):
        """Add callback for slippage alerts"""
        self.alert_callbacks.append(callback)
    
    def get_slippage_stats(self, instrument: str, period_hours: int = 24) -> Optional[SlippageStats]:
        """Get comprehensive slippage statistics"""
        if instrument not in self.slippage_history:
            return None
        
        cutoff = datetime.utcnow() - timedelta(hours=period_hours)
        recent_records = [
            record for record in self.slippage_history[instrument]
            if record['timestamp'] >= cutoff
        ]
        
        if not recent_records:
            return None
        
        slippages_bps = [record['slippage_bps'] for record in recent_records]
        
        # Calculate statistics
        avg_slippage = statistics.mean(slippages_bps)
        median_slippage = statistics.median(slippages_bps)
        max_slippage = max(slippages_bps)
        min_slippage = min(slippages_bps)
        
        std_dev = statistics.stdev(slippages_bps) if len(slippages_bps) > 1 else 0.0
        percentile_95 = self._percentile(slippages_bps, 95)
        
        # Count positive/negative slippage
        positive_count = sum(1 for s in slippages_bps if s > 0)
        negative_count = sum(1 for s in slippages_bps if s < 0)
        
        # Calculate quality score (0-100, higher is better)
        quality_score = self._calculate_quality_score(slippages_bps)
        
        return SlippageStats(
            instrument=instrument,
            period_hours=period_hours,
            total_trades=len(recent_records),
            average_slippage_bps=avg_slippage,
            median_slippage_bps=median_slippage,
            max_slippage_bps=max_slippage,
            min_slippage_bps=min_slippage,
            std_dev_slippage_bps=std_dev,
            slippage_95_percentile=percentile_95,
            negative_slippage_count=negative_count,
            positive_slippage_count=positive_count,
            quality_score=quality_score
        )
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * (percentile / 100.0)
        f = int(k)
        c = k - f
        
        if f == len(sorted_data) - 1:
            return sorted_data[f]
        return sorted_data[f] * (1 - c) + sorted_data[f + 1] * c
    
    def _calculate_quality_score(self, slippages_bps: List[float]) -> float:
        """
        Calculate execution quality score (0-100)
        
        Score factors:
        - Lower average slippage = higher score
        - Lower volatility = higher score  
        - More negative slippage (better fills) = higher score
        """
        if not slippages_bps:
            return 0.0
        
        avg_slippage = statistics.mean(slippages_bps)
        std_dev = statistics.stdev(slippages_bps) if len(slippages_bps) > 1 else 0.0
        
        # Base score starts at 50
        score = 50.0
        
        # Adjust for average slippage (lower is better)
        if avg_slippage < -5:  # Very good (negative slippage)
            score += 30
        elif avg_slippage < 0:  # Good (slight negative slippage)
            score += 20
        elif avg_slippage < 10:  # Acceptable (< 1 pip average)
            score += 10
        elif avg_slippage < 20:  # Poor (1-2 pips)
            score -= 10
        else:  # Very poor (> 2 pips)
            score -= 30
        
        # Adjust for consistency (lower std dev is better)
        if std_dev < 5:  # Very consistent
            score += 20
        elif std_dev < 10:  # Consistent
            score += 10
        elif std_dev < 20:  # Somewhat consistent
            score += 0
        else:  # Inconsistent
            score -= 20
        
        return max(0.0, min(100.0, score))
    
    def get_instruments_with_data(self) -> List[str]:
        """Get list of instruments with slippage data"""
        return list(self.slippage_history.keys())
    
    def get_alert_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of recent alerts"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        alert_counts = {'INFO': 0, 'WARNING': 0, 'CRITICAL': 0}
        instruments_with_alerts = set()
        
        for instrument, records in self.slippage_history.items():
            for record in records:
                if record['timestamp'] >= cutoff:
                    slippage_bps = abs(record['slippage_bps'])
                    
                    if slippage_bps >= self.alert_thresholds['CRITICAL']:
                        alert_counts['CRITICAL'] += 1
                        instruments_with_alerts.add(instrument)
                    elif slippage_bps >= self.alert_thresholds['WARNING']:
                        alert_counts['WARNING'] += 1
                        instruments_with_alerts.add(instrument)
                    elif slippage_bps >= self.alert_thresholds['INFO']:
                        alert_counts['INFO'] += 1
                        instruments_with_alerts.add(instrument)
        
        return {
            'period_hours': hours,
            'alert_counts': alert_counts,
            'total_alerts': sum(alert_counts.values()),
            'instruments_with_alerts': list(instruments_with_alerts),
            'alert_thresholds_bps': self.alert_thresholds
        }
    
    def update_alert_thresholds(self, thresholds: Dict[str, int]):
        """Update slippage alert thresholds"""
        self.alert_thresholds.update(thresholds)
        logger.info(f"Updated slippage alert thresholds: {self.alert_thresholds}")
    
    def clear_history(self, instrument: Optional[str] = None):
        """Clear slippage history for instrument or all instruments"""
        if instrument:
            if instrument in self.slippage_history:
                del self.slippage_history[instrument]
                logger.info(f"Cleared slippage history for {instrument}")
        else:
            self.slippage_history.clear()
            logger.info("Cleared all slippage history")