"""
Signal-to-Trade Correlation Tracking

Monitors OANDA trades and correlates them with generated signals
to track actual execution performance and signal-to-trade conversion rates.
"""

import asyncio
import aiohttp
import logging
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from signal_database import get_signal_database

logger = logging.getLogger(__name__)


@dataclass
class TradeCorrelation:
    """Represents a correlation between a signal and an executed trade"""
    signal_id: str
    trade_id: str
    correlation_confidence: float  # 0-100% how confident we are in the match
    time_diff_minutes: int  # Time difference between signal and trade
    price_diff_pips: float  # Price difference in pips
    correlation_factors: List[str]  # Factors that led to correlation


class SignalTradeCorrelator:
    """
    Correlates trading signals with actual OANDA trade executions.

    Features:
    - Automatic monitoring of OANDA trade history
    - Signal-to-trade matching based on symbol, timing, and price
    - Performance tracking and correlation confidence scoring
    - Database persistence of correlations
    """

    def __init__(self):
        """Initialize the correlator with OANDA credentials"""
        self.oanda_api_key = os.getenv('OANDA_API_KEY')
        self.oanda_account_id = os.getenv('OANDA_ACCOUNT_ID', '101-001-21040028-001')
        self.oanda_api_url = os.getenv('OANDA_BASE_URL', 'https://api-fxpractice.oanda.com')

        self.signal_db = None

        # Correlation parameters
        self.max_time_diff_hours = 4  # Max time difference for correlation
        self.max_price_diff_pips = 20  # Max price difference for correlation
        self.min_correlation_confidence = 60.0  # Minimum confidence for valid correlation

        # Tracking
        self.last_check_time = datetime.now(timezone.utc) - timedelta(hours=24)
        self.correlation_stats = {
            'total_signals': 0,
            'total_trades': 0,
            'correlations_found': 0,
            'high_confidence_correlations': 0,
            'last_updated': datetime.now(timezone.utc)
        }

    async def initialize(self):
        """Initialize the correlator"""
        try:
            self.signal_db = await get_signal_database()
            logger.info("Signal-Trade Correlator initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Signal-Trade Correlator: {e}")
            return False

    async def run_correlation_check(self) -> Dict[str, Any]:
        """
        Run a correlation check between recent signals and trades.

        Returns:
            Dictionary with correlation results and statistics
        """
        if not self.signal_db:
            await self.initialize()

        if not self.oanda_api_key:
            logger.warning("OANDA API key not available, skipping correlation check")
            return {"status": "error", "message": "OANDA API key not configured"}

        try:
            logger.info("Starting signal-to-trade correlation check")

            # Get recent signals and trades
            recent_signals = await self._get_recent_uncorrelated_signals()
            recent_trades = await self._get_recent_oanda_trades()

            logger.info(f"Found {len(recent_signals)} uncorrelated signals and {len(recent_trades)} recent trades")

            if not recent_signals or not recent_trades:
                return {
                    "status": "no_data",
                    "message": "No recent signals or trades found for correlation",
                    "stats": self.correlation_stats
                }

            # Perform correlation analysis
            correlations = await self._correlate_signals_to_trades(recent_signals, recent_trades)

            # Store correlations in database
            stored_correlations = 0
            for correlation in correlations:
                if correlation.correlation_confidence >= self.min_correlation_confidence:
                    success = await self._store_correlation(correlation)
                    if success:
                        stored_correlations += 1

            # Update statistics
            self.correlation_stats.update({
                'total_signals': self.correlation_stats['total_signals'] + len(recent_signals),
                'total_trades': self.correlation_stats['total_trades'] + len(recent_trades),
                'correlations_found': self.correlation_stats['correlations_found'] + len(correlations),
                'high_confidence_correlations': self.correlation_stats['high_confidence_correlations'] + stored_correlations,
                'last_updated': datetime.now(timezone.utc)
            })

            self.last_check_time = datetime.now(timezone.utc)

            logger.info(f"Correlation check complete: {len(correlations)} correlations found, {stored_correlations} stored")

            return {
                "status": "success",
                "correlations_found": len(correlations),
                "high_confidence_correlations": stored_correlations,
                "signals_processed": len(recent_signals),
                "trades_processed": len(recent_trades),
                "stats": self.correlation_stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Error during correlation check: {e}")
            return {
                "status": "error",
                "message": str(e),
                "stats": self.correlation_stats
            }

    async def _get_recent_uncorrelated_signals(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent signals that haven't been correlated to trades yet"""
        try:
            # Get recent signals from database
            signals = await self.signal_db.get_recent_signals(hours=hours)

            # Filter out signals that already have executions recorded
            uncorrelated_signals = []
            for signal in signals:
                # Check if signal already has an execution record
                # For now, we'll assume all signals are uncorrelated (simple implementation)
                # In a more sophisticated version, we'd query the executions table
                uncorrelated_signals.append(signal)

            return uncorrelated_signals

        except Exception as e:
            logger.error(f"Error getting uncorrelated signals: {e}")
            return []

    async def _get_recent_oanda_trades(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent trades from OANDA API"""
        try:
            if not self.oanda_api_key:
                return []

            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {self.oanda_api_key}',
                    'Content-Type': 'application/json'
                }

                # Get trades from the last N hours
                since_time = datetime.now(timezone.utc) - timedelta(hours=hours)

                # Get closed trades
                url = f"{self.oanda_api_url}/v3/accounts/{self.oanda_account_id}/trades"
                params = {
                    'state': 'CLOSED',
                    'count': 200,  # Last 200 closed trades
                }

                async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        all_trades = data.get('trades', [])

                        # Filter trades within time window
                        recent_trades = []
                        for trade in all_trades:
                            close_time_str = trade.get('closeTime')
                            if close_time_str:
                                try:
                                    close_time = datetime.fromisoformat(close_time_str.replace('Z', '+00:00'))
                                    if close_time >= since_time:
                                        recent_trades.append(trade)
                                except Exception as e:
                                    logger.warning(f"Failed to parse trade close time {close_time_str}: {e}")
                                    continue

                        logger.info(f"Retrieved {len(recent_trades)} recent trades from OANDA")
                        return recent_trades
                    else:
                        logger.warning(f"OANDA API returned status {response.status}")
                        return []

        except Exception as e:
            logger.error(f"Error getting recent OANDA trades: {e}")
            return []

    async def _correlate_signals_to_trades(self, signals: List[Dict], trades: List[Dict]) -> List[TradeCorrelation]:
        """Correlate signals to trades based on symbol, timing, and price proximity"""
        correlations = []

        for signal in signals:
            best_match = None
            best_confidence = 0.0

            signal_time = self._parse_timestamp(signal.get('generated_at'))
            signal_symbol = signal.get('symbol', '').replace('_', '')  # EUR_USD -> EURUSD
            signal_entry_price = float(signal.get('entry_price', 0))

            if not signal_time or not signal_symbol or signal_entry_price == 0:
                continue

            for trade in trades:
                trade_symbol = trade.get('instrument', '').replace('_', '')  # EUR_USD -> EURUSD
                trade_time = self._parse_timestamp(trade.get('closeTime') or trade.get('openTime'))
                trade_price = float(trade.get('price', 0))

                if not trade_time or trade_symbol != signal_symbol or trade_price == 0:
                    continue

                # Calculate correlation confidence
                confidence = self._calculate_correlation_confidence(
                    signal_time, signal_entry_price,
                    trade_time, trade_price,
                    signal_symbol
                )

                if confidence > best_confidence and confidence >= self.min_correlation_confidence:
                    time_diff_minutes = abs((trade_time - signal_time).total_seconds() / 60)
                    price_diff_pips = self._calculate_pip_difference(signal_entry_price, trade_price, signal_symbol)

                    factors = []
                    if confidence >= 90:
                        factors.append('exact_match')
                    elif confidence >= 80:
                        factors.append('high_confidence')
                    if time_diff_minutes <= 30:
                        factors.append('close_timing')
                    if abs(price_diff_pips) <= 5:
                        factors.append('close_price')

                    best_match = TradeCorrelation(
                        signal_id=signal.get('signal_id'),
                        trade_id=trade.get('id'),
                        correlation_confidence=confidence,
                        time_diff_minutes=int(time_diff_minutes),
                        price_diff_pips=price_diff_pips,
                        correlation_factors=factors
                    )
                    best_confidence = confidence

            if best_match:
                correlations.append(best_match)
                logger.debug(f"Correlated signal {best_match.signal_id} to trade {best_match.trade_id} "
                           f"with {best_match.correlation_confidence:.1f}% confidence")

        return correlations

    def _calculate_correlation_confidence(self, signal_time: datetime, signal_price: float,
                                        trade_time: datetime, trade_price: float,
                                        symbol: str) -> float:
        """Calculate confidence score for signal-to-trade correlation"""
        confidence = 100.0

        # Time proximity (closer is better)
        time_diff_hours = abs((trade_time - signal_time).total_seconds() / 3600)
        if time_diff_hours > self.max_time_diff_hours:
            return 0.0  # Outside time window

        time_penalty = (time_diff_hours / self.max_time_diff_hours) * 30  # Max 30% penalty
        confidence -= time_penalty

        # Price proximity (closer is better)
        price_diff_pips = abs(self._calculate_pip_difference(signal_price, trade_price, symbol))
        if price_diff_pips > self.max_price_diff_pips:
            return 0.0  # Outside price window

        price_penalty = (price_diff_pips / self.max_price_diff_pips) * 40  # Max 40% penalty
        confidence -= price_penalty

        return max(0.0, confidence)

    def _calculate_pip_difference(self, price1: float, price2: float, symbol: str) -> float:
        """Calculate pip difference between two prices"""
        if 'JPY' in symbol:
            pip_size = 0.01
        else:
            pip_size = 0.0001

        return abs(price1 - price2) / pip_size

    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp string to datetime object"""
        if not timestamp_str:
            return None

        try:
            if isinstance(timestamp_str, datetime):
                return timestamp_str

            # Handle various timestamp formats
            if 'T' in timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                return datetime.fromisoformat(timestamp_str)
        except Exception as e:
            logger.warning(f"Failed to parse timestamp {timestamp_str}: {e}")
            return None

    async def _store_correlation(self, correlation: TradeCorrelation) -> bool:
        """Store a signal-to-trade correlation in the database"""
        try:
            # Get trade details for more complete execution record
            trade_details = await self._get_trade_details(correlation.trade_id)

            if trade_details:
                # Store execution record with correlation
                success = await self.signal_db.record_signal_execution(
                    signal_id=correlation.signal_id,
                    trade_id=correlation.trade_id,
                    executed_at=self._parse_timestamp(trade_details.get('closeTime') or trade_details.get('openTime')),
                    execution_price=Decimal(str(trade_details.get('price', 0))),
                    executed_quantity=abs(float(trade_details.get('currentUnits', 0))),
                    broker='OANDA',
                    account_id=self.oanda_account_id
                )

                if success:
                    # Update performance metrics if we have P&L data
                    pnl = float(trade_details.get('realizedPL', 0))
                    if pnl != 0:
                        await self.signal_db.update_signal_performance(
                            signal_id=correlation.signal_id,
                            pnl=pnl
                        )

                    logger.info(f"Stored correlation for signal {correlation.signal_id} -> trade {correlation.trade_id}")
                    return True
                else:
                    logger.warning(f"Failed to store execution record for correlation {correlation.signal_id}")
                    return False
            else:
                logger.warning(f"Could not get trade details for {correlation.trade_id}")
                return False

        except Exception as e:
            logger.error(f"Error storing correlation {correlation.signal_id} -> {correlation.trade_id}: {e}")
            return False

    async def _get_trade_details(self, trade_id: str) -> Optional[Dict]:
        """Get detailed trade information from OANDA"""
        try:
            if not self.oanda_api_key:
                return None

            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {self.oanda_api_key}',
                    'Content-Type': 'application/json'
                }

                url = f"{self.oanda_api_url}/v3/accounts/{self.oanda_account_id}/trades/{trade_id}"

                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('trade')
                    else:
                        logger.warning(f"Failed to get trade details for {trade_id}: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Error getting trade details for {trade_id}: {e}")
            return None

    async def get_correlation_statistics(self) -> Dict[str, Any]:
        """Get correlation statistics and performance metrics"""
        try:
            if not self.signal_db:
                await self.initialize()

            # Get database statistics
            db_stats = await self.signal_db.get_signal_statistics(days=30)

            # Combine with correlation stats
            combined_stats = {
                **self.correlation_stats,
                'database_stats': db_stats,
                'correlation_rate': (
                    self.correlation_stats['correlations_found'] /
                    max(self.correlation_stats['total_signals'], 1) * 100
                ),
                'high_confidence_rate': (
                    self.correlation_stats['high_confidence_correlations'] /
                    max(self.correlation_stats['correlations_found'], 1) * 100
                )
            }

            return combined_stats

        except Exception as e:
            logger.error(f"Error getting correlation statistics: {e}")
            return self.correlation_stats


# Singleton instance
_correlator_instance = None

async def get_signal_correlator() -> SignalTradeCorrelator:
    """Get or create the signal correlator instance"""
    global _correlator_instance

    if _correlator_instance is None:
        _correlator_instance = SignalTradeCorrelator()
        await _correlator_instance.initialize()

    return _correlator_instance


async def run_background_correlation_monitoring():
    """Background task for continuous signal-to-trade correlation"""
    correlator = await get_signal_correlator()

    while True:
        try:
            logger.info("Running background signal-to-trade correlation check")
            result = await correlator.run_correlation_check()

            if result['status'] == 'success':
                logger.info(f"Background correlation: {result['correlations_found']} correlations found")
            elif result['status'] == 'no_data':
                logger.debug("Background correlation: No new data to correlate")
            else:
                logger.warning(f"Background correlation failed: {result.get('message', 'Unknown error')}")

            # Wait 30 minutes before next check
            await asyncio.sleep(30 * 60)

        except Exception as e:
            logger.error(f"Error in background correlation monitoring: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retry