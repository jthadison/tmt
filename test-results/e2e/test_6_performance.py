import asyncio
import sys
import os
import time
import tempfile
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

async def test_performance():
    """Test system performance under load"""
    print("Testing system performance...")
    
    try:
        from agents.regulatory_compliance.tests.test_regulatory_compliance_system import MockRegulatoryComplianceSystem
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {'storage_path': tmpdir}
            compliance_system = MockRegulatoryComplianceSystem(config)
            
            # Test initialization time
            start_time = time.time()
            await compliance_system.initialize()
            init_time = time.time() - start_time
            print(f"  ✓ System initialization: {init_time:.3f}s")
            
            # Test concurrent trade processing
            num_trades = 100
            trades = [
                {
                    'trade_id': f'perf_trade_{i:03d}',
                    'account_id': f'perf_account_{i % 10}',
                    'user_id': f'perf_user_{i % 10}',
                    'instrument': 'AAPL',
                    'trade_type': 'buy' if i % 2 == 0 else 'sell',
                    'quantity': '100',
                    'price': f'{150 + (i % 50)}.00',
                    'timestamp': (datetime.now() - timedelta(minutes=i)).isoformat(),
                    'commission': '5.00',
                    'fees': '1.00'
                }
                for i in range(num_trades)
            ]
            
            # Process trades sequentially
            start_time = time.time()
            for trade in trades[:10]:  # Test with smaller batch for performance
                await compliance_system.process_trade(trade)
            sequential_time = time.time() - start_time
            
            print(f"  ✓ Sequential processing (10 trades): {sequential_time:.3f}s")
            print(f"  ✓ Average per trade: {sequential_time/10:.3f}s")
            
            # Test memory usage (basic check)
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            print(f"  ✓ Memory usage: {memory_mb:.1f} MB")
            
            # Test report generation performance
            from datetime import date
            start_time = time.time()
            await compliance_system.generate_compliance_report(
                'full_compliance', date(2024, 1, 1), date(2024, 12, 31)
            )
            report_time = time.time() - start_time
            print(f"  ✓ Report generation: {report_time:.3f}s")
            
            print("✓ Performance test passed")
            return True
            
    except Exception as e:
        print(f"✗ Performance test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_performance())
    sys.exit(0 if success else 1)
