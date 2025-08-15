"""
Test Runner for Story 8.2 Components
Runs comprehensive tests for all broker integration components
"""
import sys
import os
import pytest
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def run_all_tests():
    """Run all tests with detailed output"""
    print("=" * 80)
    print("TMT STORY 8.2 TEST SUITE")
    print("Account Information & Balance Tracking Components")
    print("=" * 80)
    
    # Test configuration
    test_args = [
        "--verbose",
        "--tb=short",
        "--color=yes",
        "--durations=10",
        "--cov=../",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        str(Path(__file__).parent)
    ]
    
    # Run tests
    exit_code = pytest.main(test_args)
    
    print("\n" + "=" * 80)
    if exit_code == 0:
        print("✅ ALL TESTS PASSED!")
        print("📊 Coverage report generated in htmlcov/index.html")
    else:
        print("❌ SOME TESTS FAILED!")
        print(f"Exit code: {exit_code}")
    print("=" * 80)
    
    return exit_code

def run_specific_test_module(module_name):
    """Run tests for a specific module"""
    print(f"Running tests for module: {module_name}")
    
    test_file = Path(__file__).parent / f"test_{module_name}.py"
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return 1
    
    test_args = [
        "--verbose",
        "--tb=short",
        "--color=yes",
        str(test_file)
    ]
    
    return pytest.main(test_args)

def run_integration_tests():
    """Run integration tests only"""
    print("Running integration tests...")
    
    test_args = [
        "--verbose",
        "--tb=short",
        "--color=yes",
        "-m", "integration",
        str(Path(__file__).parent)
    ]
    
    return pytest.main(test_args)

def main():
    """Main test runner entry point"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "all":
            return run_all_tests()
        elif command == "integration":
            return run_integration_tests()
        elif command.startswith("test_"):
            module_name = command[5:]  # Remove "test_" prefix
            return run_specific_test_module(module_name)
        else:
            # Assume it's a module name
            return run_specific_test_module(command)
    else:
        # Default: run all tests
        return run_all_tests()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)