#!/usr/bin/env python3
"""
Cache Trading Data Script

Fetches and caches signal and trade data from OANDA and system services
for use by the optimization script.
"""

import asyncio
import json
import os
import aiohttp
from datetime import datetime, timedelta
from pathlib import Path
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent.parent / '.env')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TradingDataCache:
    def __init__(self):
        # Load OANDA credentials from .env
        self.oanda_api_key = os.getenv('OANDA_API_KEY')
        self.oanda_account_id = os.getenv('OANDA_ACCOUNT_ID', '101-001-21040028-001')
        self.oanda_api_url = os.getenv('OANDA_BASE_URL', 'https://api-fxpractice.oanda.com')

        self.orchestrator_url = 'http://localhost:8089'
        self.market_analysis_url = 'http://localhost:8001'

        self.signal_cache_file = Path('signal_cache.json')
        self.trade_cache_file = Path('trade_cache.json')

    async def cache_signal_data(self):
        """Fetch and cache signal data from market analysis service"""
        signals = []
        signal_stats = {}

        try:
            async with aiohttp.ClientSession() as session:
                logger.info("Fetching signal statistics from market analysis service...")

                # Get signal statistics from status endpoint
                try:
                    async with session.get(
                        f"{self.market_analysis_url}/status",
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            signal_stats = {
                                'signals_generated_today': data.get('signals_generated_today', 0),
                                'last_signal': data.get('last_signal'),
                                'markets_monitored': data.get('markets_monitored', [])
                            }
                            logger.info(f"Market Analysis Status: {signal_stats['signals_generated_today']} signals today")
                except Exception as e:
                    logger.warning(f"Could not fetch signal stats: {e}")

                # Since there's no direct signals endpoint, we'll store the stats
                # In a real implementation, signals would be stored in a database
                logger.info("Note: Direct signal history not available from service")

                # Save stats to cache (since we can't get actual signals)
                if signal_stats:
                    cache_data = {
                        'signal_stats': signal_stats,
                        'signals': [],  # Would be populated from database in production
                        'cached_at': datetime.now().isoformat(),
                        'source': 'market_analysis_service',
                        'note': 'Signal history requires database integration'
                    }

                    with open(self.signal_cache_file, 'w') as f:
                        json.dump(cache_data, f, indent=2, default=str)

                    logger.info(f"Cached signal statistics to {self.signal_cache_file}")
                else:
                    logger.warning("No signal data to cache")

        except Exception as e:
            logger.error(f"Error caching signal data: {e}")

    async def cache_trade_data(self):
        """Fetch and cache trade data from OANDA"""
        trades = []

        if not self.oanda_api_key:
            logger.warning("OANDA_API_KEY not set, skipping trade data cache")
            return

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {self.oanda_api_key}',
                    'Content-Type': 'application/json'
                }

                logger.info("Fetching trades from OANDA...")

                # Get closed trades
                url = f"{self.oanda_api_url}/v3/accounts/{self.oanda_account_id}/trades"
                params = {
                    'state': 'CLOSED',
                    'count': 500
                }

                async with session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        oanda_trades = data.get('trades', [])

                        # Convert to our format
                        for trade in oanda_trades:
                            trades.append({
                                'trade_id': trade.get('id'),
                                'instrument': trade.get('instrument'),
                                'units': trade.get('currentUnits', trade.get('initialUnits')),
                                'price': trade.get('price'),
                                'open_time': trade.get('openTime'),
                                'close_time': trade.get('closeTime'),
                                'realized_pl': trade.get('realizedPL'),
                                'unrealized_pl': trade.get('unrealizedPL'),
                                'financing': trade.get('financing'),
                                'state': trade.get('state')
                            })

                        logger.info(f"Retrieved {len(trades)} trades from OANDA")
                    else:
                        logger.warning(f"OANDA API returned status {response.status}")

                # Save to cache
                if trades:
                    cache_data = {
                        'executions': trades,
                        'cached_at': datetime.now().isoformat(),
                        'source': 'oanda_api',
                        'account_id': self.oanda_account_id
                    }

                    with open(self.trade_cache_file, 'w') as f:
                        json.dump(cache_data, f, indent=2, default=str)

                    logger.info(f"Cached {len(trades)} trades to {self.trade_cache_file}")
                else:
                    logger.warning("No trades to cache")

        except Exception as e:
            logger.error(f"Error caching trade data: {e}")

    async def get_current_metrics(self):
        """Get current performance metrics from the system"""
        metrics = {}

        try:
            async with aiohttp.ClientSession() as session:
                # Get orchestrator status
                logger.info("Fetching current metrics from orchestrator...")

                async with session.get(
                    f"{self.orchestrator_url}/status",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()

                        metrics['orchestrator'] = {
                            'trading_enabled': data.get('trading_enabled', False),
                            'active_signals': data.get('active_signals', 0),
                            'config': data.get('config', {})
                        }

                        logger.info("Retrieved orchestrator metrics")

                # Get OANDA account summary
                if self.oanda_api_key:
                    headers = {
                        'Authorization': f'Bearer {self.oanda_api_key}',
                        'Content-Type': 'application/json'
                    }

                    url = f"{self.oanda_api_url}/v3/accounts/{self.oanda_account_id}/summary"

                    async with session.get(
                        url,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            account = data.get('account', {})

                            metrics['account'] = {
                                'balance': account.get('balance'),
                                'unrealized_pl': account.get('unrealizedPL'),
                                'realized_pl': account.get('pl'),
                                'margin_used': account.get('marginUsed'),
                                'margin_available': account.get('marginAvailable'),
                                'open_position_count': account.get('openPositionCount'),
                                'open_trade_count': account.get('openTradeCount')
                            }

                            logger.info("Retrieved OANDA account metrics")

                return metrics

        except Exception as e:
            logger.error(f"Error fetching current metrics: {e}")
            return metrics


async def main():
    """Main function to cache all trading data"""

    cache = TradingDataCache()

    print("TMT Trading Data Cache")
    print("=" * 60)

    # Cache signal data
    print("\nCaching signal data...")
    await cache.cache_signal_data()

    # Cache trade data
    print("\nCaching trade data...")
    await cache.cache_trade_data()

    # Get current metrics
    print("\nFetching current metrics...")
    metrics = await cache.get_current_metrics()

    if metrics:
        print("\nCurrent System Metrics:")
        print("-" * 40)

        if 'orchestrator' in metrics:
            orch = metrics['orchestrator']
            print(f"Trading Enabled: {orch.get('trading_enabled', False)}")
            print(f"Active Signals: {orch.get('active_signals', 0)}")

        if 'account' in metrics:
            acc = metrics['account']
            print(f"\nAccount Metrics:")
            print(f"Balance: ${float(acc.get('balance', 0)):,.2f}")
            print(f"Unrealized P&L: ${float(acc.get('unrealized_pl', 0)):,.2f}")
            print(f"Margin Used: ${float(acc.get('margin_used', 0)):,.2f}")
            print(f"Open Positions: {acc.get('open_position_count', 0)}")
            print(f"Open Trades: {acc.get('open_trade_count', 0)}")

    print("\nData caching complete!")
    print(f"Signal cache: {cache.signal_cache_file}")
    print(f"Trade cache: {cache.trade_cache_file}")


if __name__ == "__main__":
    asyncio.run(main())