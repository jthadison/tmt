#!/usr/bin/env python3
"""
Session Parameters Validation
============================
Direct validation of session-targeted parameters and OANDA integration.
"""

import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import asyncio
import requests

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not installed, using system environment variables")

# Add project paths
sys.path.append('agents/market-analysis')
from app.signals.signal_generator import SignalGenerator, TradingSession

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SessionParametersValidator:
    """Validate session-targeted trading parameters and OANDA integration"""

    def __init__(self):
        self.oanda_api_key = os.getenv('OANDA_API_KEY')
        self.base_url = "https://api-fxpractice.oanda.com"

    def test_oanda_connection(self) -> dict:
        """Test direct OANDA API connection"""

        if not self.oanda_api_key:
            return {
                'connected': False,
                'error': 'No OANDA_API_KEY environment variable found',
                'recommendation': 'Set OANDA_API_KEY environment variable'
            }

        headers = {
            'Authorization': f'Bearer {self.oanda_api_key}',
            'Content-Type': 'application/json'
        }

        try:
            # Test account access
            logger.info("Testing OANDA API connection...")
            response = requests.get(f"{self.base_url}/v3/accounts", headers=headers, timeout=10)

            if response.status_code == 200:
                accounts = response.json().get('accounts', [])

                # Test instruments
                if accounts:
                    account_id = accounts[0]['id']
                    instruments_response = requests.get(
                        f"{self.base_url}/v3/accounts/{account_id}/instruments",
                        headers=headers, timeout=10
                    )

                    if instruments_response.status_code == 200:
                        instruments = instruments_response.json().get('instruments', [])
                        forex_pairs = [i['name'] for i in instruments if i['type'] == 'CURRENCY']

                        # Test historical data
                        test_data = self.test_historical_data_fetch()

                        return {
                            'connected': True,
                            'account_id': account_id,
                            'total_accounts': len(accounts),
                            'forex_pairs_available': len(forex_pairs),
                            'sample_pairs': forex_pairs[:5],
                            'historical_data_test': test_data
                        }

            return {
                'connected': False,
                'status_code': response.status_code,
                'error': response.text[:200],
                'recommendation': 'Check API key validity and account permissions'
            }

        except Exception as e:
            return {
                'connected': False,
                'error': f'Connection error: {str(e)}',
                'recommendation': 'Check internet connection and API key'
            }

    def test_historical_data_fetch(self) -> dict:
        """Test fetching historical data from OANDA"""

        if not self.oanda_api_key:
            return {'status': 'skipped', 'reason': 'no_api_key'}

        headers = {
            'Authorization': f'Bearer {self.oanda_api_key}',
            'Content-Type': 'application/json'
        }

        try:
            # Fetch 100 hours of EUR_USD data
            url = f"{self.base_url}/v3/instruments/EUR_USD/candles"
            params = {
                'count': 100,
                'granularity': 'H1',
                'price': 'MBA'
            }

            response = requests.get(url, headers=headers, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                candles = data.get('candles', [])

                if candles:
                    first_candle = candles[0]
                    last_candle = candles[-1]

                    return {
                        'status': 'success',
                        'candles_received': len(candles),
                        'time_range': {
                            'start': first_candle.get('time'),
                            'end': last_candle.get('time')
                        },
                        'sample_data': {
                            'open': float(first_candle['mid']['o']),
                            'close': float(last_candle['mid']['c']),
                            'volume': first_candle.get('volume', 0)
                        }
                    }
                else:
                    return {'status': 'error', 'reason': 'no_candles_returned'}
            else:
                return {
                    'status': 'error',
                    'status_code': response.status_code,
                    'error': response.text[:100]
                }

        except Exception as e:
            return {'status': 'error', 'exception': str(e)}

    def validate_session_parameters(self) -> dict:
        """Validate session-specific parameter mapping"""

        logger.info("Validating session parameter configurations...")

        # Create generator with session targeting enabled
        generator = SignalGenerator(enable_session_targeting=True)

        # Expected session parameters (from our configuration)
        expected_params = {
            'London': {
                'confidence_threshold': 72.0,
                'min_risk_reward': 3.2,
                'atr_multiplier_stop': 0.45,
                'source': 'cycle_5_london_optimized'
            },
            'New_York': {
                'confidence_threshold': 70.0,
                'min_risk_reward': 2.8,
                'atr_multiplier_stop': 0.6,
                'source': 'cycle_4_newyork_optimized'
            },
            'Tokyo': {
                'confidence_threshold': 85.0,
                'min_risk_reward': 4.0,
                'atr_multiplier_stop': 0.3,
                'source': 'cycle_2_tokyo_optimized'
            },
            'Sydney': {
                'confidence_threshold': 78.0,
                'min_risk_reward': 3.5,
                'atr_multiplier_stop': 0.4,
                'source': 'cycle_3_sydney_optimized'
            },
            'London_NY_Overlap': {
                'confidence_threshold': 70.0,
                'min_risk_reward': 2.8,
                'atr_multiplier_stop': 0.6,
                'source': 'cycle_4_overlap_optimized'
            }
        }

        validation_results = {}

        # Test each session
        sessions = [
            TradingSession.LONDON, TradingSession.NEW_YORK, TradingSession.TOKYO,
            TradingSession.SYDNEY, TradingSession.LONDON_NY_OVERLAP
        ]

        for session in sessions:
            # Mock the session detection
            original_method = generator._get_current_session
            generator._get_current_session = lambda: session

            # Get applied parameters
            applied_params = generator._apply_session_parameters()
            expected = expected_params.get(session.value, {})

            # Validate parameters
            param_match = {
                'confidence_threshold': applied_params.get('confidence_threshold') == expected.get('confidence_threshold'),
                'min_risk_reward': applied_params.get('min_risk_reward') == expected.get('min_risk_reward'),
                'atr_multiplier_stop': applied_params.get('atr_multiplier_stop') == expected.get('atr_multiplier_stop'),
                'source': applied_params.get('source') == expected.get('source')
            }

            validation_results[session.value] = {
                'expected': expected,
                'applied': applied_params,
                'validation': param_match,
                'all_match': all(param_match.values())
            }

            # Restore original method
            generator._get_current_session = original_method

        return validation_results

    def test_toggle_functionality(self) -> dict:
        """Test session targeting toggle functionality"""

        logger.info("Testing session targeting toggle functionality...")

        generator = SignalGenerator(enable_session_targeting=False)

        test_results = {
            'initial_state': {},
            'enable_toggle': {},
            'disable_toggle': {},
            'parameter_persistence': {}
        }

        # Test initial state (Universal Cycle 4)
        initial_mode = generator.get_current_trading_mode()
        test_results['initial_state'] = {
            'mode': initial_mode.get('mode'),
            'confidence_threshold': generator.confidence_threshold,
            'min_risk_reward': generator.min_risk_reward,
            'session_targeting_enabled': generator.enable_session_targeting
        }

        # Test enabling session targeting
        enable_result = generator.toggle_session_targeting(True)
        enabled_mode = generator.get_current_trading_mode()

        test_results['enable_toggle'] = {
            'toggle_successful': enable_result.get('session_targeting_changed', False),
            'new_mode': enabled_mode.get('mode'),
            'current_session': enabled_mode.get('current_session'),
            'confidence_threshold': generator.confidence_threshold,
            'min_risk_reward': generator.min_risk_reward,
            'session_targeting_enabled': generator.enable_session_targeting
        }

        # Test disabling (rollback)
        disable_result = generator.toggle_session_targeting(False)
        disabled_mode = generator.get_current_trading_mode()

        test_results['disable_toggle'] = {
            'toggle_successful': disable_result.get('session_targeting_changed', False),
            'back_to_universal': disabled_mode.get('mode') == 'universal_cycle_4',
            'confidence_threshold': generator.confidence_threshold,
            'min_risk_reward': generator.min_risk_reward,
            'session_targeting_enabled': generator.enable_session_targeting
        }

        # Test parameter persistence
        cycle_4_params = {
            'confidence_threshold': 70.0,
            'min_risk_reward': 2.8
        }

        test_results['parameter_persistence'] = {
            'cycle_4_confidence_restored': generator.confidence_threshold == cycle_4_params['confidence_threshold'],
            'cycle_4_risk_reward_restored': generator.min_risk_reward == cycle_4_params['min_risk_reward'],
            'rollback_complete': all([
                generator.confidence_threshold == cycle_4_params['confidence_threshold'],
                generator.min_risk_reward == cycle_4_params['min_risk_reward'],
                not generator.enable_session_targeting
            ])
        }

        return test_results

    def test_session_detection(self) -> dict:
        """Test GMT-based session detection logic"""

        logger.info("Testing session detection logic...")

        generator = SignalGenerator()

        # Test cases: (hour_gmt, expected_session)
        test_cases = [
            (2, 'Sydney'),     # 02:00 GMT
            (7, 'Tokyo'),      # 07:00 GMT
            (10, 'London'),    # 10:00 GMT
            (14, 'London_NY_Overlap'),  # 14:00 GMT
            (18, 'New_York'),  # 18:00 GMT
            (23, 'Sydney'),    # 23:00 GMT
        ]

        detection_results = {}

        for hour, expected_session in test_cases:
            # Create mock datetime
            from unittest.mock import patch
            mock_time = datetime(2024, 9, 22, hour, 0)

            with patch('datetime.datetime') as mock_datetime:
                mock_datetime.now.return_value = mock_time
                mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

                try:
                    detected_session = generator._get_current_session()
                    detection_results[f"{hour:02d}:00_GMT"] = {
                        'expected': expected_session,
                        'detected': detected_session.value,
                        'correct': detected_session.value == expected_session
                    }
                except Exception as e:
                    detection_results[f"{hour:02d}:00_GMT"] = {
                        'expected': expected_session,
                        'detected': 'ERROR',
                        'correct': False,
                        'error': str(e)
                    }

        # Calculate overall accuracy
        correct_detections = sum(1 for result in detection_results.values() if result.get('correct', False))
        total_tests = len(test_cases)
        accuracy = (correct_detections / total_tests) * 100

        return {
            'detection_tests': detection_results,
            'accuracy': accuracy,
            'total_tests': total_tests,
            'correct_detections': correct_detections
        }

def print_validation_results(results: dict):
    """Print comprehensive validation results"""

    print("\n" + "=" * 80)
    print("SESSION-TARGETED TRADING VALIDATION RESULTS")
    print("=" * 80)

    # OANDA Connection Test
    print("\n1. OANDA API CONNECTION TEST:")
    oanda_test = results.get('oanda_connection', {})

    if oanda_test.get('connected', False):
        print("   [+] OANDA API Connection: SUCCESS")
        print(f"   Account ID: {oanda_test.get('account_id', 'N/A')}")
        print(f"   Forex Pairs Available: {oanda_test.get('forex_pairs_available', 0)}")
        print(f"   Sample Pairs: {', '.join(oanda_test.get('sample_pairs', []))}")

        hist_data = oanda_test.get('historical_data_test', {})
        if hist_data.get('status') == 'success':
            print(f"   [+] Historical Data Test: SUCCESS")
            print(f"       Candles Received: {hist_data.get('candles_received', 0)}")
            sample = hist_data.get('sample_data', {})
            print(f"       Sample OHLC: Open {sample.get('open', 0):.5f}, Close {sample.get('close', 0):.5f}")
        else:
            print(f"   [-] Historical Data Test: FAILED")
    else:
        print("   [-] OANDA API Connection: FAILED")
        print(f"   Error: {oanda_test.get('error', 'Unknown error')}")
        print(f"   Recommendation: {oanda_test.get('recommendation', 'Check configuration')}")

    # Session Parameters Validation
    print("\n2. SESSION PARAMETERS VALIDATION:")
    session_params = results.get('session_parameters', {})

    for session, validation in session_params.items():
        status = "[+] PASS" if validation.get('all_match', False) else "[-] FAIL"
        print(f"   {session:<20}: {status}")

        if not validation.get('all_match', False):
            expected = validation.get('expected', {})
            applied = validation.get('applied', {})
            print(f"     Expected: Conf {expected.get('confidence_threshold', 0):.1f}%, RR {expected.get('min_risk_reward', 0):.1f}")
            print(f"     Applied:  Conf {applied.get('confidence_threshold', 0):.1f}%, RR {applied.get('min_risk_reward', 0):.1f}")

    # Toggle Functionality Test
    print("\n3. TOGGLE FUNCTIONALITY TEST:")
    toggle_test = results.get('toggle_functionality', {})

    initial = toggle_test.get('initial_state', {})
    enable = toggle_test.get('enable_toggle', {})
    disable = toggle_test.get('disable_toggle', {})
    persistence = toggle_test.get('parameter_persistence', {})

    print(f"   Initial State: {initial.get('mode', 'unknown')} (Conf: {initial.get('confidence_threshold', 0):.1f}%)")
    print(f"   Enable Toggle: {'[+] SUCCESS' if enable.get('toggle_successful', False) else '[-] FAILED'}")
    print(f"   Session Mode: {enable.get('new_mode', 'unknown')} - {enable.get('current_session', 'unknown')}")
    print(f"   Disable Toggle: {'[+] SUCCESS' if disable.get('toggle_successful', False) else '[-] FAILED'}")
    print(f"   Rollback Complete: {'[+] SUCCESS' if persistence.get('rollback_complete', False) else '[-] FAILED'}")

    # Session Detection Test
    print("\n4. SESSION DETECTION TEST:")
    detection_test = results.get('session_detection', {})

    print(f"   Overall Accuracy: {detection_test.get('accuracy', 0):.1f}% ({detection_test.get('correct_detections', 0)}/{detection_test.get('total_tests', 0)})")

    detection_tests = detection_test.get('detection_tests', {})
    for time_test, result in detection_tests.items():
        status = "[+] PASS" if result.get('correct', False) else "[-] FAIL"
        print(f"   {time_test}: {result.get('expected', 'N/A'):<18} -> {result.get('detected', 'N/A'):<18} {status}")

    # Overall Assessment
    print("\n5. OVERALL ASSESSMENT:")

    all_tests_passed = all([
        oanda_test.get('connected', False),
        all(v.get('all_match', False) for v in session_params.values()),
        toggle_test.get('parameter_persistence', {}).get('rollback_complete', False),
        detection_test.get('accuracy', 0) >= 100.0
    ])

    if all_tests_passed:
        print("   [+] ALL TESTS PASSED - Session-targeted trading ready for deployment")
    else:
        print("   [!] SOME TESTS FAILED - Review issues before deployment")

        if not oanda_test.get('connected', False):
            print("       - OANDA API connection issues")
        if not all(v.get('all_match', False) for v in session_params.values()):
            print("       - Session parameter mapping issues")
        if not toggle_test.get('parameter_persistence', {}).get('rollback_complete', False):
            print("       - Toggle functionality issues")
        if detection_test.get('accuracy', 0) < 100.0:
            print("       - Session detection accuracy issues")

async def main():
    """Main validation execution"""

    print("Session-Targeted Trading Parameters Validation")
    print("=" * 60)
    print("Validating OANDA integration and session parameters")
    print()

    validator = SessionParametersValidator()

    # Run all validation tests
    results = {
        'oanda_connection': validator.test_oanda_connection(),
        'session_parameters': validator.validate_session_parameters(),
        'toggle_functionality': validator.test_toggle_functionality(),
        'session_detection': validator.test_session_detection()
    }

    # Print results
    print_validation_results(results)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"session_validation_results_{timestamp}.json"

    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nDetailed validation results saved: {report_file}")

    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)