"""
CI/CD Test Runner for Broker Integration Testing Suite
Story 8.12 - Task 6: Automated test runner for CI/CD integration
"""
import asyncio
import json
import logging
import argparse
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CICDTestRunner:
    """CI/CD test runner with comprehensive reporting"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = datetime.now(timezone.utc)
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.coverage_threshold = 90.0
        self.performance_threshold_ms = 100.0
        
    async def run_test_suite(self, test_types: List[str] = None) -> Dict[str, Any]:
        """Run comprehensive test suite for CI/CD"""
        test_types = test_types or ['unit', 'integration', 'performance', 'compliance', 'e2e']
        
        logger.info("Starting CI/CD test suite execution")
        logger.info(f"Test types: {', '.join(test_types)}")
        
        results = {}
        
        try:
            if 'unit' in test_types:
                results['unit'] = await self._run_unit_tests()
                
            if 'integration' in test_types:
                results['integration'] = await self._run_integration_tests()
                
            if 'performance' in test_types:
                results['performance'] = await self._run_performance_tests()
                
            if 'compliance' in test_types:
                results['compliance'] = await self._run_compliance_tests()
                
            if 'e2e' in test_types:
                results['e2e'] = await self._run_e2e_tests()
                
            # Generate consolidated report
            consolidated_report = self._generate_consolidated_report(results)
            
            return consolidated_report
            
        except Exception as e:
            logger.error(f"Test suite execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
    async def _run_unit_tests(self) -> Dict[str, Any]:
        """Run unit tests with coverage"""
        logger.info("Running unit tests...")
        
        try:
            import subprocess
            
            # Run unit tests with coverage
            cmd = [
                sys.executable, '-m', 'pytest',
                'test_comprehensive_unit_suite.py',
                '--cov=.',
                '--cov-report=json',
                '--cov-report=term-missing',
                '--tb=short',
                '-v'
            ]
            
            start_time = time.perf_counter()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent
            )
            end_time = time.perf_counter()
            
            # Parse test results
            test_passed = result.returncode == 0
            duration = end_time - start_time
            
            # Try to read coverage data
            coverage_data = self._read_coverage_data()
            coverage_percentage = coverage_data.get('totals', {}).get('percent_covered', 0)
            
            # Parse test output for test counts
            output_lines = result.stdout.split('\n')
            test_counts = self._parse_pytest_output(output_lines)
            
            return {
                'type': 'unit',
                'passed': test_passed,
                'duration_seconds': duration,
                'test_counts': test_counts,
                'coverage_percentage': coverage_percentage,
                'coverage_meets_threshold': coverage_percentage >= self.coverage_threshold,
                'stdout': result.stdout,
                'stderr': result.stderr if result.stderr else None
            }
            
        except Exception as e:
            logger.error(f"Unit test execution failed: {e}")
            return {
                'type': 'unit',
                'passed': False,
                'error': str(e)
            }
            
    async def _run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests"""
        logger.info("Running integration tests...")
        
        try:
            import subprocess
            
            cmd = [
                sys.executable, '-m', 'pytest',
                'test_integration_framework.py::TestIntegrationFramework',
                '--tb=short',
                '-v'
            ]
            
            start_time = time.perf_counter()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent
            )
            end_time = time.perf_counter()
            
            test_passed = result.returncode == 0
            duration = end_time - start_time
            
            output_lines = result.stdout.split('\n')
            test_counts = self._parse_pytest_output(output_lines)
            
            return {
                'type': 'integration',
                'passed': test_passed,
                'duration_seconds': duration,
                'test_counts': test_counts,
                'stdout': result.stdout,
                'stderr': result.stderr if result.stderr else None
            }
            
        except Exception as e:
            logger.error(f"Integration test execution failed: {e}")
            return {
                'type': 'integration',
                'passed': False,
                'error': str(e)
            }
            
    async def _run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests"""
        logger.info("Running performance tests...")
        
        try:
            import subprocess
            
            cmd = [
                sys.executable, '-m', 'pytest',
                'test_performance_suite.py::TestOrderLatencyPerformance::test_single_order_latency',
                'test_performance_suite.py::TestConcurrentOrderHandling::test_100_concurrent_orders',
                '--tb=short',
                '-v'
            ]
            
            start_time = time.perf_counter()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent
            )
            end_time = time.perf_counter()
            
            test_passed = result.returncode == 0
            duration = end_time - start_time
            
            output_lines = result.stdout.split('\n')
            test_counts = self._parse_pytest_output(output_lines)
            
            # Check for performance metrics in output
            performance_issues = self._check_performance_issues(output_lines)
            
            return {
                'type': 'performance',
                'passed': test_passed and not performance_issues,
                'duration_seconds': duration,
                'test_counts': test_counts,
                'performance_issues': performance_issues,
                'performance_threshold_ms': self.performance_threshold_ms,
                'stdout': result.stdout,
                'stderr': result.stderr if result.stderr else None
            }
            
        except Exception as e:
            logger.error(f"Performance test execution failed: {e}")
            return {
                'type': 'performance',
                'passed': False,
                'error': str(e)
            }
            
    async def _run_compliance_tests(self) -> Dict[str, Any]:
        """Run compliance tests"""
        logger.info("Running compliance tests...")
        
        try:
            import subprocess
            
            cmd = [
                sys.executable, '-m', 'pytest',
                'test_compliance_scenarios.py::TestFIFOCompliance::test_fifo_order_acceptance',
                'test_compliance_scenarios.py::TestAntiHedgingCompliance::test_anti_hedging_violation',
                'test_compliance_scenarios.py::TestLeverageLimits::test_leverage_limit_enforcement',
                '--tb=short',
                '-v'
            ]
            
            start_time = time.perf_counter()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent
            )
            end_time = time.perf_counter()
            
            test_passed = result.returncode == 0
            duration = end_time - start_time
            
            output_lines = result.stdout.split('\n')
            test_counts = self._parse_pytest_output(output_lines)
            
            return {
                'type': 'compliance',
                'passed': test_passed,
                'duration_seconds': duration,
                'test_counts': test_counts,
                'stdout': result.stdout,
                'stderr': result.stderr if result.stderr else None
            }
            
        except Exception as e:
            logger.error(f"Compliance test execution failed: {e}")
            return {
                'type': 'compliance',
                'passed': False,
                'error': str(e)
            }
            
    async def _run_e2e_tests(self) -> Dict[str, Any]:
        """Run end-to-end tests"""
        logger.info("Running end-to-end tests...")
        
        try:
            import subprocess
            
            cmd = [
                sys.executable, '-m', 'pytest',
                'test_end_to_end_automation.py::TestE2EScenarios::test_complete_trade_lifecycle',
                '--tb=short',
                '-v'
            ]
            
            start_time = time.perf_counter()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent
            )
            end_time = time.perf_counter()
            
            test_passed = result.returncode == 0
            duration = end_time - start_time
            
            output_lines = result.stdout.split('\n')
            test_counts = self._parse_pytest_output(output_lines)
            
            return {
                'type': 'e2e',
                'passed': test_passed,
                'duration_seconds': duration,
                'test_counts': test_counts,
                'stdout': result.stdout,
                'stderr': result.stderr if result.stderr else None
            }
            
        except Exception as e:
            logger.error(f"E2E test execution failed: {e}")
            return {
                'type': 'e2e',
                'passed': False,
                'error': str(e)
            }
            
    def _parse_pytest_output(self, output_lines: List[str]) -> Dict[str, int]:
        """Parse pytest output to extract test counts"""
        test_counts = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': 0
        }
        
        for line in output_lines:
            if 'passed' in line and 'failed' in line:
                # Look for summary line like "5 passed, 2 failed in 1.23s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'passed' and i > 0:
                        test_counts['passed'] = int(parts[i-1])
                    elif part == 'failed' and i > 0:
                        test_counts['failed'] = int(parts[i-1])
                    elif part == 'skipped' and i > 0:
                        test_counts['skipped'] = int(parts[i-1])
                    elif part == 'error' and i > 0:
                        test_counts['errors'] = int(parts[i-1])
                        
        test_counts['total'] = sum([
            test_counts['passed'],
            test_counts['failed'],
            test_counts['skipped'],
            test_counts['errors']
        ])
        
        return test_counts
        
    def _read_coverage_data(self) -> Dict[str, Any]:
        """Read coverage data from coverage.json file"""
        try:
            coverage_file = Path(__file__).parent / 'coverage.json'
            if coverage_file.exists():
                with open(coverage_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not read coverage data: {e}")
            
        return {}
        
    def _check_performance_issues(self, output_lines: List[str]) -> List[str]:
        """Check for performance issues in test output"""
        issues = []
        
        for line in output_lines:
            if 'latency' in line.lower() and 'exceeds' in line.lower():
                issues.append(line.strip())
            elif 'timeout' in line.lower():
                issues.append(line.strip())
            elif 'too slow' in line.lower():
                issues.append(line.strip())
                
        return issues
        
    def _generate_consolidated_report(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Generate consolidated test report"""
        end_time = datetime.now(timezone.utc)
        total_duration = (end_time - self.start_time).total_seconds()
        
        # Calculate overall statistics
        all_passed = all(result.get('passed', False) for result in results.values())
        total_tests = sum(result.get('test_counts', {}).get('total', 0) for result in results.values())
        total_passed = sum(result.get('test_counts', {}).get('passed', 0) for result in results.values())
        total_failed = sum(result.get('test_counts', {}).get('failed', 0) for result in results.values())
        
        # Check quality gates
        quality_gates = self._check_quality_gates(results)
        
        report = {
            'summary': {
                'overall_success': all_passed and quality_gates['all_passed'],
                'start_time': self.start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'total_duration_seconds': total_duration,
                'test_suites_run': list(results.keys()),
                'total_tests': total_tests,
                'total_passed': total_passed,
                'total_failed': total_failed,
                'success_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0
            },
            'quality_gates': quality_gates,
            'test_results': results,
            'ci_cd_status': 'PASS' if all_passed and quality_gates['all_passed'] else 'FAIL',
            'recommendations': self._generate_recommendations(results, quality_gates),
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        return report
        
    def _check_quality_gates(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Check quality gates for CI/CD"""
        gates = {
            'coverage_threshold': True,
            'performance_threshold': True,
            'no_test_failures': True,
            'all_test_suites_passed': True,
            'all_passed': True
        }
        
        # Check coverage threshold
        unit_results = results.get('unit', {})
        coverage_percentage = unit_results.get('coverage_percentage', 0)
        gates['coverage_threshold'] = coverage_percentage >= self.coverage_threshold
        
        # Check performance threshold
        performance_results = results.get('performance', {})
        performance_issues = performance_results.get('performance_issues', [])
        gates['performance_threshold'] = len(performance_issues) == 0
        
        # Check for test failures
        total_failed = sum(result.get('test_counts', {}).get('failed', 0) for result in results.values())
        gates['no_test_failures'] = total_failed == 0
        
        # Check all test suites passed
        gates['all_test_suites_passed'] = all(result.get('passed', False) for result in results.values())
        
        # Overall gate
        gates['all_passed'] = all(gates.values())
        
        return gates
        
    def _generate_recommendations(self, results: Dict[str, Dict[str, Any]], quality_gates: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        if not quality_gates['coverage_threshold']:
            unit_results = results.get('unit', {})
            coverage = unit_results.get('coverage_percentage', 0)
            recommendations.append(f"Increase test coverage from {coverage:.1f}% to meet {self.coverage_threshold}% threshold")
            
        if not quality_gates['performance_threshold']:
            performance_results = results.get('performance', {})
            issues = performance_results.get('performance_issues', [])
            recommendations.append(f"Address {len(issues)} performance issues detected")
            
        if not quality_gates['no_test_failures']:
            total_failed = sum(result.get('test_counts', {}).get('failed', 0) for result in results.values())
            recommendations.append(f"Fix {total_failed} failing tests")
            
        for test_type, result in results.items():
            if not result.get('passed', False):
                recommendations.append(f"Fix issues in {test_type} test suite")
                
        if not recommendations:
            recommendations.append("All quality gates passed - ready for deployment")
            
        return recommendations


async def main():
    """Main function for CI/CD test runner"""
    parser = argparse.ArgumentParser(description='CI/CD Test Runner for Broker Integration')
    parser.add_argument('--test-types', nargs='+', 
                       choices=['unit', 'integration', 'performance', 'compliance', 'e2e'],
                       default=['unit', 'integration', 'performance', 'compliance', 'e2e'],
                       help='Test types to run')
    parser.add_argument('--output-file', type=str, 
                       help='Output file for test results (JSON format)')
    parser.add_argument('--coverage-threshold', type=float, default=90.0,
                       help='Coverage threshold percentage')
    parser.add_argument('--performance-threshold', type=float, default=100.0,
                       help='Performance threshold in milliseconds')
    
    args = parser.parse_args()
    
    # Initialize test runner
    runner = CICDTestRunner()
    runner.coverage_threshold = args.coverage_threshold
    runner.performance_threshold_ms = args.performance_threshold
    
    # Run test suite
    logger.info("Starting CI/CD test execution")
    results = await runner.run_test_suite(args.test_types)
    
    # Output results
    if args.output_file:
        output_path = Path(args.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
            
        logger.info(f"Test results written to {output_path}")
    else:
        print(json.dumps(results, indent=2))
        
    # Log summary
    summary = results.get('summary', {})
    logger.info(f"Test execution completed")
    logger.info(f"Overall success: {summary.get('overall_success', False)}")
    logger.info(f"Total tests: {summary.get('total_tests', 0)}")
    logger.info(f"Success rate: {summary.get('success_rate', 0):.1f}%")
    logger.info(f"CI/CD Status: {results.get('ci_cd_status', 'UNKNOWN')}")
    
    # Exit with appropriate code for CI/CD
    exit_code = 0 if results.get('ci_cd_status') == 'PASS' else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())