#!/usr/bin/env python3
"""
Close all open trades to free up margin
"""

import os
import sys
import asyncio
import aiohttp
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
OANDA_API_KEY = os.getenv("OANDA_API_KEY")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")
OANDA_BASE_URL = os.getenv("OANDA_BASE_URL", "https://api-fxpractice.oanda.com")

# Validate credentials
if not OANDA_API_KEY or not OANDA_ACCOUNT_ID:
    print("Error: OANDA_API_KEY and OANDA_ACCOUNT_ID must be set in environment variables or .env file")
    sys.exit(1)

async def get_open_trades():
    """Get all open trades"""
    url = f"{OANDA_BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/trades"
    headers = {
        "Authorization": f"Bearer {OANDA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("trades", [])
            else:
                print(f"Error getting trades: {response.status}")
                return []

async def close_trade(trade_id):
    """Close a specific trade"""
    url = f"{OANDA_BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/trades/{trade_id}/close"
    headers = {
        "Authorization": f"Bearer {OANDA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.put(url, headers=headers) as response:
            if response.status in [200, 201]:
                result = await response.json()
                return True, result
            else:
                error_text = await response.text()
                return False, error_text

async def get_account_summary():
    """Get account summary"""
    url = f"{OANDA_BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/summary"
    headers = {
        "Authorization": f"Bearer {OANDA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("account", {})
            else:
                return {}

async def main():
    print("=" * 60)
    print("CLOSING ALL OPEN TRADES")
    print("=" * 60)
    print(f"Account: {OANDA_ACCOUNT_ID}")
    print(f"Time: {datetime.now().isoformat()}")
    print()
    
    # Get account summary before
    account_before = await get_account_summary()
    if account_before:
        print("ACCOUNT STATUS BEFORE:")
        print(f"  Balance: {account_before.get('balance', 'N/A')}")
        print(f"  Unrealized P&L: {account_before.get('unrealizedPL', 'N/A')}")
        print(f"  Margin Used: {account_before.get('marginUsed', 'N/A')}")
        print(f"  Margin Available: {account_before.get('marginAvailable', 'N/A')}")
        print(f"  Open Trades: {account_before.get('openTradeCount', 'N/A')}")
        print()
    
    # Get all open trades
    trades = await get_open_trades()
    
    if not trades:
        print("No open trades found.")
        return
    
    print(f"Found {len(trades)} open trades:")
    print()
    
    # Display trades
    for trade in trades:
        trade_id = trade.get("id", "")
        instrument = trade.get("instrument", "")
        units = trade.get("currentUnits", "0")
        price = trade.get("price", "0")
        unrealized_pl = trade.get("unrealizedPL", "0")
        
        direction = "LONG" if float(units) > 0 else "SHORT"
        print(f"  Trade {trade_id}: {instrument} {direction} {units} @ {price}, P&L: {unrealized_pl}")
    
    print()
    print("Closing all trades...")
    print()
    
    # Close each trade
    closed = 0
    failed = 0
    total_pl = 0.0
    
    for trade in trades:
        trade_id = trade.get("id", "")
        instrument = trade.get("instrument", "")
        
        print(f"Closing trade {trade_id} ({instrument})...", end="")
        success, result = await close_trade(trade_id)
        
        if success:
            print(" [CLOSED]")
            closed += 1
            
            # Get P&L from the closing transaction
            if isinstance(result, dict):
                order_fill = result.get("orderFillTransaction", {})
                if order_fill:
                    pl = float(order_fill.get("pl", "0"))
                    total_pl += pl
                    print(f"    P&L: {pl}")
        else:
            print(f" [FAILED]: {result}")
            failed += 1
    
    print()
    print("=" * 60)
    print(f"RESULTS: {closed} trades closed, {failed} failed")
    print(f"Total P&L from closed trades: {total_pl:.2f}")
    
    # Get account summary after
    await asyncio.sleep(2)  # Wait for account to update
    account_after = await get_account_summary()
    
    if account_after:
        print()
        print("ACCOUNT STATUS AFTER:")
        print(f"  Balance: {account_after.get('balance', 'N/A')}")
        print(f"  Unrealized P&L: {account_after.get('unrealizedPL', 'N/A')}")
        print(f"  Margin Used: {account_after.get('marginUsed', 'N/A')}")
        print(f"  Margin Available: {account_after.get('marginAvailable', 'N/A')}")
        print(f"  Open Trades: {account_after.get('openTradeCount', 'N/A')}")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())