#!/usr/bin/env python3
"""Quick test of OANDA connection"""

import os
import asyncio
import aiohttp
from dotenv import load_dotenv

async def test_oanda():
    load_dotenv()
    
    api_key = os.getenv("OANDA_API_KEY")
    account_id = os.getenv("OANDA_ACCOUNT_ID") 
    environment = os.getenv("OANDA_ENVIRONMENT", "practice")
    
    if not api_key or not account_id:
        print("ERROR: OANDA credentials not found")
        return
    
    print(f"Testing OANDA {environment} connection...")
    print(f"Account: {account_id}")
    
    base_url = "https://api-fxpractice.oanda.com" if environment == "practice" else "https://api-fxtrade.oanda.com"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/v3/accounts/{account_id}", headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    account = data.get("account", {})
                    print(f"SUCCESS: Balance = {account.get('balance')} {account.get('currency')}")
                    print(f"Open Trades: {account.get('openTradeCount', 0)}")
                    print(f"Margin Available: {account.get('marginAvailable')}")
                else:
                    print(f"ERROR: HTTP {response.status}")
                    text = await response.text()
                    print(f"Response: {text[:200]}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_oanda())