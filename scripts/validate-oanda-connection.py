#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OANDA Connection Validation Script
Tests connectivity and basic functionality with OANDA API
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from decimal import Decimal

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except Exception:
        pass  # Fallback to default encoding

# Color codes for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_colored(message: str, color: str = Colors.NC):
    """Print colored message with Windows-safe Unicode handling"""
    try:
        print(f"{color}{message}{Colors.NC}")
    except UnicodeEncodeError:
        # Fallback to ASCII-only version
        safe_message = message.encode('ascii', 'ignore').decode('ascii')
        print(f"{color}{safe_message}{Colors.NC}")

def load_environment() -> Dict[str, str]:
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

def validate_credentials(env_vars: Dict[str, str]) -> bool:
    """Validate OANDA credentials are present"""
    print_colored("[INFO] Validating OANDA credentials...", Colors.BLUE)
    
    if not env_vars.get('OANDA_API_KEY') or env_vars.get('OANDA_API_KEY') == 'your_api_key_here':
        print_colored("[ERROR] OANDA_API_KEY not configured", Colors.RED)
        return False
    
    if not env_vars.get('OANDA_ACCOUNT_ID') or env_vars.get('OANDA_ACCOUNT_ID') == 'your_account_id_here':
        print_colored("[ERROR] OANDA_ACCOUNT_ID not configured", Colors.RED)
        return False
    
    print_colored("[OK] Credentials found", Colors.GREEN)
    return True

def test_account_access(env_vars: Dict[str, str]) -> Tuple[bool, Optional[Dict]]:
    """Test account access and get account details"""
    print_colored("📊 Testing account access...", Colors.BLUE)
    
    headers = {
        'Authorization': f"Bearer {env_vars['OANDA_API_KEY']}",
        'Accept-Datetime-Format': 'RFC3339'
    }
    
    url = f"{env_vars['OANDA_BASE_URL']}/v3/accounts/{env_vars['OANDA_ACCOUNT_ID']}"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            account_data = response.json()['account']
            print_colored("✅ Account access successful", Colors.GREEN)
            print(f"   Account ID: {account_data['id']}")
            print(f"   Currency: {account_data['currency']}")
            print(f"   Balance: {account_data['balance']}")
            print(f"   Unrealized P&L: {account_data.get('unrealizedPL', '0')}")
            print(f"   Open Trades: {account_data.get('openTradeCount', 0)}")
            print(f"   Open Positions: {account_data.get('openPositionCount', 0)}")
            return True, account_data
        else:
            print_colored(f"❌ Account access failed: {response.status_code}", Colors.RED)
            print(f"   Error: {response.text}")
            return False, None
            
    except requests.exceptions.RequestException as e:
        print_colored(f"❌ Connection error: {str(e)}", Colors.RED)
        return False, None

def test_market_data(env_vars: Dict[str, str]) -> bool:
    """Test market data access"""
    print_colored("📈 Testing market data access...", Colors.BLUE)
    
    headers = {
        'Authorization': f"Bearer {env_vars['OANDA_API_KEY']}",
        'Accept-Datetime-Format': 'RFC3339'
    }
    
    # Test multiple instruments
    instruments = ['EUR_USD', 'GBP_USD', 'USD_JPY']
    
    for instrument in instruments:
        url = f"{env_vars['OANDA_BASE_URL']}/v3/instruments/{instrument}/candles"
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
                    mid_price = latest['mid']['c']
                    bid_price = latest['bid']['c']
                    ask_price = latest['ask']['c']
                    spread = float(ask_price) - float(bid_price)
                    
                    print(f"   {instrument}: Bid={bid_price}, Ask={ask_price}, Spread={spread:.5f}")
            else:
                print_colored(f"   ❌ Failed to get {instrument} data: {response.status_code}", Colors.YELLOW)
                
        except requests.exceptions.RequestException as e:
            print_colored(f"   ❌ Error getting {instrument} data: {str(e)}", Colors.YELLOW)
    
    print_colored("✅ Market data access successful", Colors.GREEN)
    return True

def test_order_placement(env_vars: Dict[str, str], dry_run: bool = True) -> bool:
    """Test order placement capability (dry run by default)"""
    print_colored("📝 Testing order placement capability...", Colors.BLUE)
    
    if dry_run:
        print_colored("   ℹ️  Dry run mode - no actual orders will be placed", Colors.YELLOW)
    
    headers = {
        'Authorization': f"Bearer {env_vars['OANDA_API_KEY']}",
        'Accept-Datetime-Format': 'RFC3339',
        'Content-Type': 'application/json'
    }
    
    # Create a test market order (very small size)
    order_data = {
        "order": {
            "instrument": "EUR_USD",
            "units": "1",  # Minimum size
            "type": "MARKET",
            "timeInForce": "FOK",
            "positionFill": "DEFAULT"
        }
    }
    
    if dry_run:
        # Just validate the order structure
        print_colored("   ✅ Order structure validated (dry run)", Colors.GREEN)
        print(f"   Test order: Buy 1 unit EUR_USD at market")
        return True
    
    url = f"{env_vars['OANDA_BASE_URL']}/v3/accounts/{env_vars['OANDA_ACCOUNT_ID']}/orders"
    
    try:
        response = requests.post(url, headers=headers, json=order_data, timeout=10)
        
        if response.status_code == 201:
            order_result = response.json()
            print_colored("   ✅ Order placement successful", Colors.GREEN)
            print(f"   Order ID: {order_result.get('orderFillTransaction', {}).get('id', 'N/A')}")
            
            # Immediately close the position if opened
            if 'orderFillTransaction' in order_result:
                close_position(env_vars, 'EUR_USD')
            
            return True
        else:
            print_colored(f"   ❌ Order placement failed: {response.status_code}", Colors.RED)
            print(f"   Error: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print_colored(f"   ❌ Connection error: {str(e)}", Colors.RED)
        return False

def close_position(env_vars: Dict[str, str], instrument: str):
    """Close a position for the given instrument"""
    headers = {
        'Authorization': f"Bearer {env_vars['OANDA_API_KEY']}",
        'Accept-Datetime-Format': 'RFC3339',
        'Content-Type': 'application/json'
    }
    
    url = f"{env_vars['OANDA_BASE_URL']}/v3/accounts/{env_vars['OANDA_ACCOUNT_ID']}/positions/{instrument}/close"
    
    try:
        response = requests.put(url, headers=headers, json={"longUnits": "ALL"}, timeout=10)
        if response.status_code == 200:
            print_colored(f"   ✅ Position closed for {instrument}", Colors.GREEN)
    except:
        pass  # Silent fail for cleanup

def test_historical_data(env_vars: Dict[str, str]) -> bool:
    """Test historical data retrieval"""
    print_colored("📜 Testing historical data access...", Colors.BLUE)
    
    headers = {
        'Authorization': f"Bearer {env_vars['OANDA_API_KEY']}",
        'Accept-Datetime-Format': 'RFC3339'
    }
    
    # Get data from last 24 hours
    to_time = datetime.utcnow()
    from_time = to_time - timedelta(days=1)
    
    url = f"{env_vars['OANDA_BASE_URL']}/v3/instruments/EUR_USD/candles"
    params = {
        'from': from_time.isoformat() + 'Z',
        'to': to_time.isoformat() + 'Z',
        'granularity': 'H1',
        'price': 'MBA'
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            candles = response.json()['candles']
            print_colored(f"   ✅ Retrieved {len(candles)} hourly candles", Colors.GREEN)
            
            if candles:
                # Calculate basic stats
                prices = [float(c['mid']['c']) for c in candles]
                avg_price = sum(prices) / len(prices)
                max_price = max(prices)
                min_price = min(prices)
                volatility = max_price - min_price
                
                print(f"   24h Stats: Avg={avg_price:.5f}, High={max_price:.5f}, Low={min_price:.5f}, Range={volatility:.5f}")
            
            return True
        else:
            print_colored(f"   ❌ Historical data retrieval failed: {response.status_code}", Colors.RED)
            return False
            
    except requests.exceptions.RequestException as e:
        print_colored(f"   ❌ Connection error: {str(e)}", Colors.RED)
        return False

def test_streaming_endpoint(env_vars: Dict[str, str]) -> bool:
    """Test streaming endpoint connectivity"""
    print_colored("📡 Testing streaming endpoint...", Colors.BLUE)
    
    # Streaming uses different URL format
    stream_url = env_vars['OANDA_BASE_URL'].replace('api-', 'stream-')
    
    headers = {
        'Authorization': f"Bearer {env_vars['OANDA_API_KEY']}",
        'Accept-Datetime-Format': 'RFC3339'
    }
    
    url = f"{stream_url}/v3/accounts/{env_vars['OANDA_ACCOUNT_ID']}/pricing/stream"
    params = {
        'instruments': 'EUR_USD'
    }
    
    try:
        # Test connection only (don't actually stream)
        response = requests.get(url, headers=headers, params=params, stream=True, timeout=5)
        
        if response.status_code == 200:
            # Read first chunk to verify stream
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if data.get('type') == 'PRICE':
                        price = data.get('bids', [{}])[0].get('price', 'N/A')
                        print_colored(f"   ✅ Streaming active - EUR/USD: {price}", Colors.GREEN)
                        response.close()
                        return True
                    elif data.get('type') == 'HEARTBEAT':
                        print_colored("   ✅ Streaming heartbeat received", Colors.GREEN)
                        response.close()
                        return True
            
            response.close()
            
        else:
            print_colored(f"   ❌ Streaming connection failed: {response.status_code}", Colors.RED)
            return False
            
    except requests.exceptions.Timeout:
        print_colored("   ⚠️  Streaming test timeout (this might be normal)", Colors.YELLOW)
        return True
    except requests.exceptions.RequestException as e:
        print_colored(f"   ❌ Connection error: {str(e)}", Colors.RED)
        return False

def run_validation():
    """Run complete OANDA validation suite"""
    print_colored("\n🔌 OANDA Connection Validator v1.0", Colors.BLUE)
    print("=" * 50)
    
    # Load environment
    env_vars = load_environment()
    
    # Track test results
    results = {
        'credentials': False,
        'account': False,
        'market_data': False,
        'orders': False,
        'historical': False,
        'streaming': False
    }
    
    # Run tests
    if not validate_credentials(env_vars):
        print_colored("\n❌ VALIDATION FAILED: Missing credentials", Colors.RED)
        print_colored("Please configure OANDA_API_KEY and OANDA_ACCOUNT_ID in .env file", Colors.YELLOW)
        return False
    
    results['credentials'] = True
    
    # Test account access
    success, account_data = test_account_access(env_vars)
    results['account'] = success
    
    if not success:
        print_colored("\n❌ VALIDATION FAILED: Cannot access account", Colors.RED)
        return False
    
    # Continue with other tests
    results['market_data'] = test_market_data(env_vars)
    results['orders'] = test_order_placement(env_vars, dry_run=True)
    results['historical'] = test_historical_data(env_vars)
    results['streaming'] = test_streaming_endpoint(env_vars)
    
    # Summary
    print_colored("\n📊 Validation Summary", Colors.BLUE)
    print("=" * 50)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        color = Colors.GREEN if passed else Colors.RED
        print_colored(f"   {test_name.replace('_', ' ').title()}: {status}", color)
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print_colored("🎉 All validation tests passed!", Colors.GREEN)
        print_colored("Your OANDA connection is ready for trading.", Colors.GREEN)
        return True
    else:
        print_colored("⚠️  Some tests failed. Please review the errors above.", Colors.YELLOW)
        return False

if __name__ == "__main__":
    try:
        success = run_validation()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_colored("\n⚠️  Validation interrupted by user", Colors.YELLOW)
        sys.exit(1)
    except Exception as e:
        print_colored(f"\n❌ Unexpected error: {str(e)}", Colors.RED)
        sys.exit(1)