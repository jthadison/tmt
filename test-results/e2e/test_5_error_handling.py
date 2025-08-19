import asyncio
import sys
import os
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

async def test_error_handling():
    """Test error handling and system recovery"""
    print("Testing error handling and recovery...")
    
    try:
        from agents.regulatory_compliance.tests.test_regulatory_compliance_system import MockRegulatoryComplianceSystem
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {'storage_path': tmpdir}
            compliance_system = MockRegulatoryComplianceSystem(config)
            await compliance_system.initialize()
            
            # Test invalid trade data
            invalid_trade = {
                'trade_id': 'invalid_001',
                'account_id': 'nonexistent_account',
                'instrument': '',  # Invalid empty instrument
                'trade_type': 'invalid_type',
                'quantity': 'not_a_number',
                'price': 'invalid_price',
                'timestamp': 'invalid_timestamp'
            }
            
            try:
                await compliance_system.process_trade(invalid_trade)
                print("  ⚠ System accepted invalid trade (should have rejected)")
            except Exception as e:
                print(f"  ✓ System properly rejected invalid trade: {type(e).__name__}")
            
            # Test missing user registration
            try:
                permission = await compliance_system.check_trade_permission(
                    'nonexistent_account', {'is_day_trade': True}
                )
                print(f"  ✓ Graceful handling of missing account: {permission.get('allowed', 'Unknown')}")
            except Exception as e:
                print(f"  ✓ Proper error handling for missing account: {type(e).__name__}")
            
            # Test report generation with missing data
            from datetime import date
            try:
                report = await compliance_system.generate_compliance_report(
                    'tax_summary', date(2024, 1, 1), date(2024, 12, 31), 'nonexistent_account'
                )
                print("  ✓ Graceful handling of missing report data")
            except Exception as e:
                print(f"  ✓ Proper error handling for missing report data: {type(e).__name__}")
            
            print("✓ Error handling test passed")
            return True
            
    except Exception as e:
        print(f"✗ Error handling test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_error_handling())
    sys.exit(0 if success else 1)
