#!/usr/bin/env python3
import os
import asyncio
import httpx
from datetime import datetime

async def get_trade_details():
    api_key = os.getenv('OANDA_API_KEY')
    account_id = os.getenv('OANDA_ACCOUNT_ID')
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    async with httpx.AsyncClient() as client:
        print('=== CURRENT TRADE DETAILS ===')
        
        # Get open trades with full details
        response = await client.get(
            f'https://api-fxpractice.oanda.com/v3/accounts/{account_id}/trades',
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            trades = data.get('trades', [])
            
            if trades:
                for trade in trades:
                    print(f"Trade ID: {trade.get('id')}")
                    print(f"Instrument: {trade.get('instrument')}")
                    print(f"Direction: {'LONG' if float(trade.get('currentUnits', 0)) > 0 else 'SHORT'}")
                    print(f"Current Units: {trade.get('currentUnits')}")
                    print(f"Entry Price: {trade.get('price')}")
                    print(f"Unrealized P&L: ${trade.get('unrealizedPL')}")
                    
                    # Stop Loss details
                    stop_loss = trade.get('stopLossOrder')
                    if stop_loss:
                        print(f"Stop Loss: {stop_loss.get('price')} (Order ID: {stop_loss.get('id')})")
                    else:
                        print('Stop Loss: None set')
                    
                    # Take Profit details  
                    take_profit = trade.get('takeProfitOrder')
                    if take_profit:
                        print(f"Take Profit: {take_profit.get('price')} (Order ID: {take_profit.get('id')})")
                    else:
                        print('Take Profit: None set')
                    
                    # Trade timing
                    open_time = trade.get('openTime')
                    if open_time:
                        print(f"Open Time: {open_time}")
                    
                    print(f"Financing: ${trade.get('financing', '0.0000')}")
                    print(f"Client Extensions: {trade.get('clientExtensions', {})}")
                    print('-' * 50)
            else:
                print('No open trades found')
        
        # Also check for any pending orders
        print('\n=== PENDING ORDERS ===')
        response = await client.get(
            f'https://api-fxpractice.oanda.com/v3/accounts/{account_id}/orders',
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            orders = data.get('orders', [])
            
            if orders:
                for order in orders:
                    print(f"Order ID: {order.get('id')}")
                    print(f"Type: {order.get('type')}")
                    print(f"Instrument: {order.get('instrument')}")
                    print(f"Units: {order.get('units')}")
                    print(f"Price: {order.get('price')}")
                    print(f"State: {order.get('state')}")
                    print('-' * 40)
            else:
                print('No pending orders')

        # Get current market prices for context
        print('\n=== CURRENT MARKET PRICES ===')
        try:
            response = await client.get(
                f'https://api-fxpractice.oanda.com/v3/accounts/{account_id}/pricing',
                headers=headers,
                params={'instruments': 'EUR_USD,GBP_USD,USD_JPY,AUD_USD,USD_CAD,NZD_USD'}
            )
            
            if response.status_code == 200:
                pricing_data = response.json()
                prices = pricing_data.get('prices', [])
                
                for price in prices:
                    instrument = price.get('instrument')
                    bid = price.get('bids', [{}])[0].get('price', 'N/A')
                    ask = price.get('asks', [{}])[0].get('price', 'N/A')
                    print(f"{instrument}: Bid={bid}, Ask={ask}")
        except Exception as e:
            print(f"Could not fetch market prices: {e}")

if __name__ == "__main__":
    asyncio.run(get_trade_details())