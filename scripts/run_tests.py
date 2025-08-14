#!/usr/bin/env python3
"""
Test runner script for TMT Trading System
Executes different types of tests based on command line arguments
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd, timeout=300):
    """Run command and return success/failure"""
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        print(f"Success: {cmd}")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Failed: {cmd}")
        print(f"Error output: {e.stderr}")
        return False, e.stderr
    except subprocess.TimeoutExpired:
        print(f"Timeout: {cmd}")
        return False, "Command timed out"


def check_dependencies():
    """Check if required dependencies are available"""
    print("Checking dependencies...")
    
    # Check Python packages
    required_packages = [
        "pytest", "pytest-asyncio", "pytest-benchmark", "faker", "numpy"
    ]
    
    for package in required_packages:
        success, _ = run_command(f"python -c \"import {package}\"")
        if not success:
            print(f"Missing package: {package}")
            print(f"Install with: pip install {package}")
            return False
    
    print("All dependencies available")
    return True


def run_unit_tests():
    """Run unit tests"""
    print("\nRunning Unit Tests")
    print("=" * 50)
    
    cmd = "python -m pytest tests/unit/ -v --tb=short --cov=src --cov-report=term-missing"
    success, output = run_command(cmd, timeout=180)
    
    if success:
        print("Unit tests passed")
    else:
        print("Unit tests failed")
        print(output)
    
    return success


def run_integration_tests():
    """Run integration tests"""
    print("\nRunning Integration Tests")
    print("=" * 50)
    
    # Check if services are available
    print("Checking for required services...")
    
    services_ok = True
    
    # Check PostgreSQL
    pg_success, _ = run_command(
        "python -c \"import psycopg2; psycopg2.connect('postgresql://postgres:password@localhost:5432/trading_system')\"",
        timeout=10
    )
    if not pg_success:
        print("PostgreSQL not available - some tests may fail")
        services_ok = False
    
    # Check Redis
    redis_success, _ = run_command(
        "python -c \"import redis; redis.Redis('localhost', 6379).ping()\"",
        timeout=10
    )
    if not redis_success:
        print("Redis not available - some tests may fail")
        services_ok = False
    
    if services_ok:
        print("All services available")
    else:
        print("Some services unavailable - starting Docker services...")
        docker_success, _ = run_command("docker-compose up -d postgres redis", timeout=60)
        if docker_success:
            print("Services started via Docker")
            time.sleep(10)  # Wait for services to initialize
        else:
            print("Failed to start services")
    
    cmd = "python -m pytest tests/integration/ -v --tb=short -m integration"
    success, output = run_command(cmd, timeout=300)
    
    if success:
        print("Integration tests passed")
    else:
        print("Integration tests failed")
        print(output)
    
    return success


def run_performance_tests():
    """Run performance tests"""
    print("\nRunning Performance Tests")
    print("=" * 50)
    
    cmd = "python -m pytest tests/performance/ -v --tb=short -m performance"
    success, output = run_command(cmd, timeout=600)
    
    if success:
        print("Performance tests passed")
    else:
        print("Performance tests failed")
        print(output)
    
    return success


def run_load_tests():
    """Run load tests"""
    print("\nRunning Load Tests")
    print("=" * 50)
    
    cmd = "python -m pytest tests/load/ -v --tb=short -m load"
    success, output = run_command(cmd, timeout=1800)  # 30 minutes
    
    if success:
        print("Load tests passed")
    else:
        print("Load tests failed")
        print(output)
    
    return success


def run_eight_agent_tests():
    """Run 8-agent orchestration tests"""
    print("\nRunning 8-Agent Orchestration Tests")
    print("=" * 50)
    
    cmd = "python -m pytest tests/integration/test_eight_agent_orchestration.py -v --tb=short"
    success, output = run_command(cmd, timeout=600)
    
    if success:
        print("8-agent tests passed")
    else:
        print("8-agent tests failed")
        print(output)
    
    return success


def run_all_tests():
    """Run all test suites"""
    print("\nRunning All Tests")
    print("=" * 50)
    
    results = {}
    
    # Run tests in order of dependency
    test_suites = [
        ("Unit", run_unit_tests),
        ("Integration", run_integration_tests),
        ("8-Agent", run_eight_agent_tests),
        ("Performance", run_performance_tests),
        ("Load", run_load_tests)
    ]
    
    for suite_name, test_func in test_suites:
        print(f"\nStarting {suite_name} Tests...")
        results[suite_name] = test_func()
        
        if not results[suite_name]:
            print(f"{suite_name} tests failed - stopping execution")
            break
    
    # Print summary
    print("\nTest Results Summary")
    print("=" * 50)
    
    for suite_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"{suite_name:12} {status}")
    
    total_passed = sum(results.values())
    total_run = len(results)
    
    print(f"\nOverall: {total_passed}/{total_run} test suites passed")
    
    return total_passed == total_run


def fix_import_issues():
    """Fix common import issues"""
    print("\nFixing Import Issues")
    print("=" * 50)
    
    # Add __init__.py files where missing
    missing_init_paths = [
        "tests",
        "tests/unit",
        "tests/integration", 
        "tests/performance",
        "tests/load",
        "tests/fixtures"
    ]
    
    for path in missing_init_paths:
        init_file = Path(path) / "__init__.py"
        if not init_file.exists():
            init_file.parent.mkdir(parents=True, exist_ok=True)
            init_file.write_text('"""Test module"""')
            print(f"Created {init_file}")
    
    # Fix PYTHONPATH issues in existing test files
    test_files = list(Path("tests").rglob("*.py"))
    
    for test_file in test_files:
        if test_file.name.startswith("test_") or test_file.name.endswith("_test.py"):
            try:
                content = test_file.read_text()
                if "import sys" not in content and "from src." in content:
                    # Add PYTHONPATH fix
                    pythonpath_fix = '''import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

'''
                    new_content = pythonpath_fix + content
                    test_file.write_text(new_content)
                    print(f"Fixed imports in {test_file}")
            except Exception as e:
                print(f"Could not fix {test_file}: {e}")
    
    print("Import fixes completed")


def main():
    parser = argparse.ArgumentParser(description="TMT Trading System Test Runner")
    parser.add_argument(
        "test_type",
        choices=["unit", "integration", "performance", "load", "8agent", "all", "fix-imports"],
        help="Type of tests to run"
    )
    parser.add_argument("--check-deps", action="store_true", help="Check dependencies only")
    
    args = parser.parse_args()
    
    print("TMT Trading System Test Runner")
    print("=" * 50)
    
    if args.check_deps:
        success = check_dependencies()
        sys.exit(0 if success else 1)
    
    if args.test_type == "fix-imports":
        fix_import_issues()
        sys.exit(0)
    
    # Check dependencies first
    if not check_dependencies():
        print("Dependency check failed")
        sys.exit(1)
    
    # Run appropriate test suite
    test_functions = {
        "unit": run_unit_tests,
        "integration": run_integration_tests,
        "performance": run_performance_tests,
        "load": run_load_tests,
        "8agent": run_eight_agent_tests,
        "all": run_all_tests
    }
    
    test_func = test_functions.get(args.test_type)
    if not test_func:
        print(f"Unknown test type: {args.test_type}")
        sys.exit(1)
    
    start_time = time.time()
    success = test_func()
    end_time = time.time()
    
    duration = end_time - start_time
    print(f"\nTotal execution time: {duration:.2f} seconds")
    
    if success:
        print("All tests completed successfully!")
        sys.exit(0)
    else:
        print("Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()