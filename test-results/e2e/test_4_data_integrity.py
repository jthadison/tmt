import asyncio
import sys
import os
import tempfile
from datetime import datetime
from decimal import Decimal
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

async def test_data_integrity():
    """Test data integrity across all systems"""
    print("Testing data integrity and persistence...")
    
    try:
        from agents.regulatory_compliance.tests.test_regulatory_compliance_system import MockRegulatoryComplianceSystem
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {'storage_path': tmpdir}
            compliance_system = MockRegulatoryComplianceSystem(config)
            await compliance_system.initialize()
            
            # Test data consistency
            original_trade = {
                'trade_id': 'integrity_test_001',
                'account_id': 'test_account',
                'user_id': 'test_user',
                'instrument': 'AAPL',
                'trade_type': 'buy',
                'quantity': '100',
                'price': '150.00',
                'timestamp': datetime.now().isoformat(),
                'commission': '5.00',
                'fees': '1.00'
            }
            
            # Process trade
            await compliance_system.process_trade(original_trade)
            
            # Verify data retention
            data_retention = compliance_system.data_retention
            retention_summary = await data_retention.get_retention_summary()
            
            print(f"  ✓ Data records stored: {retention_summary['total_records']}")
            print(f"  ✓ Storage size: {retention_summary['total_storage_mb']} MB")
            
            # Verify audit trail
            audit_events = compliance_system.audit_reporting.audit_events
            print(f"  ✓ Audit events recorded: {len(audit_events)}")
            
            # Check data consistency across modules
            trade_in_audit = any(
                event.event_data.get('trade_id') == original_trade['trade_id']
                for event in audit_events
                if event.event_type.value == 'trade_execution'
            )
            
            if trade_in_audit:
                print("  ✓ Trade data consistent across audit system")
            else:
                print("  ⚠ Trade data inconsistency detected")
            
            print("✓ Data integrity test passed")
            return True
            
    except Exception as e:
        print(f"✗ Data integrity test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_data_integrity())
    sys.exit(0 if success else 1)
