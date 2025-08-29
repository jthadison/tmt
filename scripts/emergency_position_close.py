#!/usr/bin/env python3
"""
Emergency position close script - closes all open positions to free up margin
"""

import os
import asyncio
import aiohttp
import sys
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

async def get_open_positions():
    """Get all open positions"""
    url = f"{OANDA_BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/positions"
    headers = {
        "Authorization": f"Bearer {OANDA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("positions", [])
            else:
                print(f"Error getting positions: {response.status}")
                return []

async def close_position(instrument):
    """Close a specific position"""
    url = f"{OANDA_BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/positions/{instrument}/close"
    headers = {
        "Authorization": f"Bearer {OANDA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Close ALL units (both long and short)
    data = {
        "longUnits": "ALL",
        "shortUnits": "ALL"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.put(url, headers=headers, json=data) as response:
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
    print("EMERGENCY POSITION CLOSURE SCRIPT")
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
        print(f"  Open Positions: {account_before.get('openPositionCount', 'N/A')}")
        print()
    
    # Get all open positions
    positions = await get_open_positions()
    
    if not positions:
        print("No open positions found.")
        return
    
    print(f"Found {len(positions)} open positions:")
    print()
    
    # Display positions
    for pos in positions:
        instrument = pos.get("instrument", "")
        long_units = pos.get("long", {}).get("units", "0")
        short_units = pos.get("short", {}).get("units", "0")
        unrealized_pl = pos.get("unrealizedPL", "0")
        
        if long_units != "0":
            print(f"  {instrument}: LONG {long_units} units, Unrealized P&L: {unrealized_pl}")
        if short_units != "0":
            print(f"  {instrument}: SHORT {short_units} units, Unrealized P&L: {unrealized_pl}")
    
    print()
    print("Closing all positions...")
    print()
    
    # Close each position
    closed = 0
    failed = 0
    
    for pos in positions:
        instrument = pos.get("instrument", "")
        long_units = pos.get("long", {}).get("units", "0")
        short_units = pos.get("short", {}).get("units", "0")
        
        # Only close if there are actual units
        if long_units != "0" or short_units != "0":
            print(f"Closing {instrument}...", end="")
            success, result = await close_position(instrument)
            
            if success:
                print(" [CLOSED]")
                closed += 1
                
                # Display closing details
                if isinstance(result, dict):
                    long_fill = result.get("longOrderFillTransaction", {})
                    short_fill = result.get("shortOrderFillTransaction", {})
                    
                    if long_fill:
                        pl = long_fill.get("pl", "0")
                        print(f"    Long closed: P&L = {pl}")
                    
                    if short_fill:
                        pl = short_fill.get("pl", "0")
                        print(f"    Short closed: P&L = {pl}")
            else:
                print(f" [FAILED]: {result}")
                failed += 1
    
    print()
    print("=" * 60)
    print(f"RESULTS: {closed} positions closed, {failed} failed")
    
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
        print(f"  Open Positions: {account_after.get('openPositionCount', 'N/A')}")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())