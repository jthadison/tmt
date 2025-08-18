import asyncio
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

async def test_complete_trading_workflow():
    """Test complete end-to-end trading workflow"""
    print("Testing complete trading workflow...")
    
    try:
        # Simulate regulatory compliance system
        from agents.regulatory_compliance.tests.test_regulatory_compliance_system import MockRegulatoryComplianceSystem
        
        # Setup test environment
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {'storage_path': tmpdir}
            compliance_system = MockRegulatoryComplianceSystem(config)
            
            # Initialize system
            await compliance_system.initialize()
            print("  ✓ Compliance system initialized")
            
            # Test user registration
            user_data = {
                'user_id': 'e2e_test_user_20250817_214215',
                'account_id': 'e2e_test_account_20250817_214215',
                'email': 'test@example.com',
                'name': 'Test User',
                'country': 'US',
                'initial_equity': 50000,
                'is_margin_account': True,
                'has_options_approval': False
            }
            
            result = await compliance_system.register_user(user_data)
            print(f"  ✓ User registered: {result['compliance_status']}")
            
            # Test trade processing
            trades = [
                {
                    'trade_id': f'trade_{i:03d}',
                    'account_id': 'e2e_test_account_20250817_214215',
                    'user_id': 'e2e_test_user_20250817_214215',
                    'instrument': 'AAPL',
                    'trade_type': 'buy' if i % 2 == 0 else 'sell',
                    'quantity': '100',
                    'price': f'{150 + i}.00',
                    'timestamp': (datetime.now() - timedelta(days=10-i)).isoformat(),
                    'commission': '5.00',
                    'fees': '1.00'
                }
                for i in range(5)
            ]
            
            for trade in trades:
                # Check trade permission
                permission = await compliance_system.check_trade_permission(
                    trade['account_id'], trade
                )
                
                if permission['allowed']:
                    # Process trade
                    await compliance_system.process_trade(trade)
                    print(f"  ✓ Trade processed: {trade['trade_id']}")
                else:
                    print(f"  ⚠ Trade rejected: {trade['trade_id']} - {permission.get('restrictions', [])}")
            
            # Generate compliance reports
            from datetime import date
            
            # Tax summary report
            tax_report = await compliance_system.generate_compliance_report(
                'tax_summary', date(2024, 1, 1), date(2024, 12, 31), 'e2e_test_account_20250817_214215'
            )
            print("  ✓ Tax summary report generated")
            
            # Full compliance report
            full_report = await compliance_system.generate_compliance_report(
                'full_compliance', date(2024, 1, 1), date(2024, 12, 31)
            )
            print("  ✓ Full compliance report generated")
            
            # Get compliance status
            status = await compliance_system.get_compliance_status()
            print(f"  ✓ Compliance status: {status.overall_status}")
            
            # Run compliance checks
            await compliance_system.run_compliance_checks()
            print("  ✓ Compliance checks completed")
            
            print("✓ Complete trading workflow test passed")
            return True
            
    except Exception as e:
        print(f"✗ Trading workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_complete_trading_workflow())
    sys.exit(0 if success else 1)
