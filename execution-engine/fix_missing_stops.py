#!/usr/bin/env python3
"""
Emergency script to add missing stop-loss and take-profit orders to unprotected positions
"""

import requests
import json
from datetime import datetime

# OANDA Configuration
API_KEY = "375f337dd8502af3307ce9179f7a373a-48f35175b87682feea1f057950810a09"
ACCOUNT_ID = "101-001-21040028-001"
BASE_URL = "https://api-fxpractice.oanda.com/v3"

# Headers for OANDA API
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def get_open_trades():
    """Get all open trades from OANDA"""
    url = f"{BASE_URL}/accounts/{ACCOUNT_ID}/trades"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()["trades"]
    else:
        print(f"Error fetching trades: {response.text}")
        return []

def calculate_stops(trade):
    """Calculate default stop-loss and take-profit levels"""
    instrument = trade["instrument"]
    entry_price = float(trade["price"])
    units = float(trade["currentUnits"])
    is_long = units > 0
    
    # Default risk parameters (can be adjusted)
    # Using 2% risk for stop-loss and 3% reward for take-profit
    sl_percentage = 0.02  # 2% stop loss
    tp_percentage = 0.03  # 3% take profit
    
    # For forex pairs, use pip-based calculation
    if "_" in instrument:  # Forex pair
        # Determine pip size based on instrument
        if "JPY" in instrument:
            pip_size = 0.01  # For JPY pairs
        else:
            pip_size = 0.0001  # For standard pairs
        
        # Calculate stops based on ATR or fixed pips
        # Using conservative 50 pip stop and 75 pip target as default
        sl_pips = 50 * pip_size
        tp_pips = 75 * pip_size
        
        if is_long:
            stop_loss = round(entry_price - sl_pips, 5)
            take_profit = round(entry_price + tp_pips, 5)
        else:
            stop_loss = round(entry_price + sl_pips, 5)
            take_profit = round(entry_price - tp_pips, 5)
    else:
        # For other instruments, use percentage
        if is_long:
            stop_loss = round(entry_price * (1 - sl_percentage), 5)
            take_profit = round(entry_price * (1 + tp_percentage), 5)
        else:
            stop_loss = round(entry_price * (1 + sl_percentage), 5)
            take_profit = round(entry_price * (1 - tp_percentage), 5)
    
    return stop_loss, take_profit

def add_stop_loss(trade_id, price):
    """Add a stop-loss order to a trade"""
    url = f"{BASE_URL}/accounts/{ACCOUNT_ID}/trades/{trade_id}/orders"
    
    order_data = {
        "stopLoss": {
            "price": str(price),
            "timeInForce": "GTC"
        }
    }
    
    response = requests.put(url, headers=headers, json=order_data)
    return response.status_code == 200, response.text

def add_take_profit(trade_id, price):
    """Add a take-profit order to a trade"""
    url = f"{BASE_URL}/accounts/{ACCOUNT_ID}/trades/{trade_id}/orders"
    
    order_data = {
        "takeProfit": {
            "price": str(price),
            "timeInForce": "GTC"
        }
    }
    
    response = requests.put(url, headers=headers, json=order_data)
    return response.status_code == 200, response.text

def fix_missing_stops():
    """Main function to fix missing stops on all unprotected trades"""
    print("=" * 60)
    print("EMERGENCY STOP-LOSS FIXER")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print(f"Account: {ACCOUNT_ID}")
    print("-" * 60)
    
    # Get all open trades
    trades = get_open_trades()
    print(f"\nFound {len(trades)} open trades")
    
    fixed_count = 0
    error_count = 0
    
    for trade in trades:
        trade_id = trade["id"]
        instrument = trade["instrument"]
        entry_price = float(trade["price"])
        units = float(trade["currentUnits"])
        unrealized_pl = float(trade.get("unrealizedPL", 0))
        
        # Check if trade has stop-loss and take-profit
        has_sl = "stopLossOrder" in trade
        has_tp = "takeProfitOrder" in trade
        
        print(f"\nTrade #{trade_id}: {instrument}")
        print(f"  Entry: {entry_price}, Units: {units}, P&L: ${unrealized_pl:.2f}")
        print(f"  Stop-Loss: {'YES' if has_sl else 'NO'}")
        print(f"  Take-Profit: {'YES' if has_tp else 'NO'}")
        
        # Fix missing stops
        if not has_sl or not has_tp:
            print(f"  ⚠️  MISSING PROTECTION - Adding stops...")
            
            # Calculate stops
            sl_price, tp_price = calculate_stops(trade)
            
            # Add stop-loss if missing
            if not has_sl:
                success, response = add_stop_loss(trade_id, sl_price)
                if success:
                    print(f"  [SUCCESS] Added Stop-Loss at {sl_price}")
                    fixed_count += 1
                else:
                    print(f"  [FAILED] Failed to add Stop-Loss: {response}")
                    error_count += 1
            
            # Add take-profit if missing
            if not has_tp:
                success, response = add_take_profit(trade_id, tp_price)
                if success:
                    print(f"  [SUCCESS] Added Take-Profit at {tp_price}")
                    fixed_count += 1
                else:
                    print(f"  [FAILED] Failed to add Take-Profit: {response}")
                    error_count += 1
        else:
            print(f"  [OK] Already protected")
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total trades checked: {len(trades)}")
    print(f"Stops added: {fixed_count}")
    print(f"Errors: {error_count}")
    
    if fixed_count > 0:
        print("\n[WARNING] IMPORTANT: Review the added stops and adjust if needed!")
        print("These are conservative default values.")
    
    return fixed_count, error_count

if __name__ == "__main__":
    fixed, errors = fix_missing_stops()
    exit(0 if errors == 0 else 1)