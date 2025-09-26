#!/usr/bin/env python3
"""
Automated Test Suite Runner for TMT Trading System

Runs all critical tests to ensure system integrity before deployment.
This should be run:
1. Before committing code (via pre-commit hook)
2. In CI/CD pipeline
3. Before production deployment
"""

import asyncio
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# ANSI color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'


class TestSuite:
    """Manages and runs all system tests"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.test_results = {}
        self.start_time = None
        self.end_time = None

    def print_header(self):
        """Print test suite header"""
        print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
        print(f"{BOLD}{BLUE}TMT Trading System - Automated Test Suite{RESET}")
        print(f"{BOLD}{BLUE}{'='*70}{RESET}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")

    def print_test_start(self, test_name: str, description: str):
        """Print test start message"""
        print(f"{BOLD}[RUNNING]{RESET} {test_name}")
        print(f"         {description}")

    def print_test_result(self, test_name: str, success: bool, duration: float, message: str = ""):
        """Print test result"""
        status = f"{GREEN}✅ PASSED{RESET}" if success else f"{RED}❌ FAILED{RESET}"
        print(f"{status} {test_name} ({duration:.2f}s)")
        if message:
            print(f"         {message}")
        print()

    async def run_python_test(self, test_file: str, description: str) -> Tuple[bool, str]:
        """Run a Python test file"""
        test_path = self.project_root / test_file

        if not test_path.exists():
            return False, f"Test file not found: {test_file}"

        try:
            # Run test as subprocess
            result = subprocess.run(
                [sys.executable, str(test_path)],
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )

            success = result.returncode == 0
            output = result.stdout if success else result.stderr
            return success, output

        except subprocess.TimeoutExpired:
            return False, "Test timed out after 60 seconds"
        except Exception as e:
            return False, f"Error running test: {e}"

    async def check_service_health(self) -> Dict[str, bool]:
        """Check if required services are running"""
        import aiohttp

        services = {
            "Orchestrator": "http://localhost:8089/health",
            "Market Analysis": "http://localhost:8001/health",
            "Execution Engine": "http://localhost:8082/health",
            "Pattern Detection": "http://localhost:8008/health",
        }

        health_status = {}

        async with aiohttp.ClientSession() as session:
            for name, url in services.items():
                try:
                    async with session.get(url, timeout=5) as response:
                        health_status[name] = response.status == 200
                except:
                    health_status[name] = False

        return health_status

    async def run_all_tests(self):
        """Run all tests in sequence"""
        self.start_time = time.time()
        all_passed = True

        # 1. Check service health
        print(f"{BOLD}[CHECKING]{RESET} Service Health")
        health_status = await self.check_service_health()

        all_healthy = all(health_status.values())
        if not all_healthy:
            print(f"{YELLOW}⚠️  Warning: Some services are not running:{RESET}")
            for service, is_healthy in health_status.items():
                if not is_healthy:
                    print(f"   - {service}: {RED}Not responding{RESET}")
            print(f"{YELLOW}   Tests may fail due to missing services{RESET}\n")
        else:
            print(f"{GREEN}✅ All services healthy{RESET}\n")

        # Define test suite
        tests = [
            ("test-execution-engine.py", "Execution Engine Order Placement"),
            ("tests/test_execution_engine_comprehensive.py", "Comprehensive Execution Engine Tests"),
            ("test-trading-pipeline.py", "End-to-End Trading Pipeline"),
        ]

        # Run each test
        for test_file, description in tests:
            self.print_test_start(test_file, description)

            start_time = time.time()
            success, output = await self.run_python_test(test_file, description)
            duration = time.time() - start_time

            self.test_results[test_file] = {
                "success": success,
                "duration": duration,
                "output": output
            }

            # Extract key message from output
            message = ""
            if "units_int" in output:
                message = "🐛 BUG DETECTED: units_int variable error found!"
            elif "PASSED" in output:
                message = "All checks passed"
            elif "FAILED" in output:
                message = "Some checks failed - review output"

            self.print_test_result(test_file, success, duration, message)

            if not success:
                all_passed = False
                # Print detailed error for failed tests
                if "units_int" in output:
                    print(f"{RED}CRITICAL: The 'units_int' bug is still present!{RESET}")
                    print(f"This would prevent all trades from executing.\n")

        self.end_time = time.time()
        return all_passed

    def print_summary(self, all_passed: bool):
        """Print test suite summary"""
        total_duration = self.end_time - self.start_time
        passed_count = sum(1 for r in self.test_results.values() if r["success"])
        total_count = len(self.test_results)

        print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
        print(f"{BOLD}Test Suite Summary{RESET}")
        print(f"{'='*70}")

        print(f"Total Tests: {total_count}")
        print(f"Passed: {GREEN}{passed_count}{RESET}")
        print(f"Failed: {RED}{total_count - passed_count}{RESET}")
        print(f"Duration: {total_duration:.2f} seconds")

        if all_passed:
            print(f"\n{BOLD}{GREEN}✅ ALL TESTS PASSED{RESET}")
            print("The system is ready for deployment.")
        else:
            print(f"\n{BOLD}{RED}❌ SOME TESTS FAILED{RESET}")
            print("Please fix the failing tests before deployment.")
            print("\nFailed tests:")
            for test_name, result in self.test_results.items():
                if not result["success"]:
                    print(f"  - {test_name}")

        print(f"\n{BOLD}Recommendations:{RESET}")
        if all_passed:
            print("1. ✅ Safe to commit and deploy")
            print("2. ✅ All critical paths tested")
            print("3. ✅ No known bugs detected")
        else:
            print("1. ❌ Fix failing tests before committing")
            print("2. ❌ Run tests again after fixes")
            print("3. ❌ Do not deploy until all tests pass")

        print(f"\n{'='*70}\n")


async def main():
    """Main entry point"""
    suite = TestSuite()
    suite.print_header()

    try:
        all_passed = await suite.run_all_tests()
        suite.print_summary(all_passed)
        return 0 if all_passed else 1

    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test suite interrupted by user{RESET}")
        return 1

    except Exception as e:
        print(f"\n{RED}Unexpected error: {e}{RESET}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)