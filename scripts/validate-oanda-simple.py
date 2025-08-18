#!/usr/bin/env python3
"""
Simple OANDA Connection Validator (Windows-compatible)
Tests basic connectivity with OANDA API
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta

def load_environment():
    """Load environment variables"""
    env_file = os.path.join(os.path.dirname(__file__), '..', '.env')
    env_vars = {}
    
    # Load from .env file if exists
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    # Override with actual environment variables
    env_vars.update({
        'OANDA_API_KEY': os.getenv('OANDA_API_KEY', env_vars.get('OANDA_API_KEY', '')),
        'OANDA_ACCOUNT_ID': os.getenv('OANDA_ACCOUNT_ID', env_vars.get('OANDA_ACCOUNT_ID', '')),
        'OANDA_ENVIRONMENT': os.getenv('OANDA_ENVIRONMENT', env_vars.get('OANDA_ENVIRONMENT', 'practice')),
        'OANDA_BASE_URL': os.getenv('OANDA_BASE_URL', env_vars.get('OANDA_BASE_URL', 'https://api-fxpractice.oanda.com'))
    })
    
    return env_vars

def validate_credentials(env_vars):
    """Validate OANDA credentials are present"""
    print("[INFO] Validating OANDA credentials...")
    
    if not env_vars.get('OANDA_API_KEY') or env_vars.get('OANDA_API_KEY') == 'your_api_key_here':
        print("[ERROR] OANDA_API_KEY not configured")
        return False
    
    if not env_vars.get('OANDA_ACCOUNT_ID') or env_vars.get('OANDA_ACCOUNT_ID') == 'your_account_id_here':
        print("[ERROR] OANDA_ACCOUNT_ID not configured")
        return False
    
    print("[OK] Credentials found")
    return True

def test_account_access(env_vars):
    """Test account access and get account details"""
    print("[INFO] Testing account access...")
    
    headers = {
        'Authorization': f"Bearer {env_vars['OANDA_API_KEY']}",
        'Accept-Datetime-Format': 'RFC3339'
    }
    
    url = f"{env_vars['OANDA_BASE_URL']}/v3/accounts/{env_vars['OANDA_ACCOUNT_ID']}"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            account_data = response.json()['account']
            print("[OK] Account access successful")
            print(f"   Account ID: {account_data['id']}")
            print(f"   Currency: {account_data['currency']}")
            print(f"   Balance: {account_data['balance']}")
            print(f"   Unrealized P&L: {account_data.get('unrealizedPL', '0')}")
            print(f"   Open Trades: {account_data.get('openTradeCount', 0)}")
            return True, account_data
        else:
            print(f"[ERROR] Account access failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False, None
            
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Connection error: {str(e)}")
        return False, None

def test_market_data(env_vars):
    """Test market data access"""
    print("[INFO] Testing market data access...")
    
    headers = {
        'Authorization': f"Bearer {env_vars['OANDA_API_KEY']}",
        'Accept-Datetime-Format': 'RFC3339'
    }
    
    # Test EUR/USD
    url = f"{env_vars['OANDA_BASE_URL']}/v3/instruments/EUR_USD/candles"
    params = {
        'count': 5,
        'granularity': 'M1',
        'price': 'MBA'
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            candles = response.json()['candles']
            latest = candles[-1] if candles else None
            
            if latest:
                bid_price = latest['bid']['c']
                ask_price = latest['ask']['c']
                spread = float(ask_price) - float(bid_price)
                
                print(f"[OK] EUR_USD: Bid={bid_price}, Ask={ask_price}, Spread={spread:.5f}")
                return True
        else:
            print(f"[ERROR] Failed to get market data: {response.status_code}")
            return False
                
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Market data error: {str(e)}")
        return False
    
    return False

def main():
    """Run OANDA validation"""
    print("\n=== OANDA Connection Validator v1.0 ===")
    print("=" * 50)
    
    # Load environment
    env_vars = load_environment()
    
    # Validate credentials
    if not validate_credentials(env_vars):
        print("\n[FAILED] Missing credentials")
        print("Please configure OANDA_API_KEY and OANDA_ACCOUNT_ID in .env file")
        return False
    
    # Test account access
    success, account_data = test_account_access(env_vars)
    if not success:
        print("\n[FAILED] Cannot access account")
        return False
    
    # Test market data
    if not test_market_data(env_vars):
        print("\n[FAILED] Market data access failed")
        return False
    
    # Summary
    print("\n=== Validation Summary ===")
    print("[OK] Credentials: PASS")
    print("[OK] Account Access: PASS")
    print("[OK] Market Data: PASS")
    print("\n[SUCCESS] All validation tests passed!")
    print("Your OANDA connection is ready for trading.")
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[INFO] Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {str(e)}")
        sys.exit(1)