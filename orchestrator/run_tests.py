#!/usr/bin/env python3
"""
Test runner for Trading System Orchestrator

Run all tests with coverage reporting
"""

import sys
import subprocess
import os
from pathlib import Path

def run_tests():
    """Run all tests with coverage"""
    
    # Set up paths
    orchestrator_dir = Path(__file__).parent
    os.chdir(orchestrator_dir)
    
    print("="*60)
    print("Trading System Orchestrator - Test Suite")
    print("="*60)
    
    # Check if pytest is installed
    try:
        import pytest
    except ImportError:
        print("Installing pytest and dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pytest", "pytest-asyncio", "pytest-cov", "pytest-mock"])
    
    # Run tests with coverage
    print("\nRunning tests with coverage...\n")
    
    test_commands = [
        # Run all tests with coverage
        [sys.executable, "-m", "pytest", "tests/", "-v", "--cov=app", "--cov-report=term-missing"],
        
        # Generate coverage report
        [sys.executable, "-m", "coverage", "report", "--show-missing"],
        
        # Create HTML coverage report
        [sys.executable, "-m", "coverage", "html", "-d", "htmlcov"]
    ]
    
    for cmd in test_commands:
        try:
            result = subprocess.run(cmd, capture_output=False, text=True)
            if result.returncode != 0:
                print(f"Command failed: {' '.join(cmd)}")
                # Continue anyway to show partial results
        except Exception as e:
            print(f"Error running command: {e}")
    
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    # Run a quick summary
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "--tb=no", "-q"],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
    except Exception as e:
        print(f"Error generating summary: {e}")
    
    print("\nHTML coverage report generated in: htmlcov/index.html")
    print("="*60)

if __name__ == "__main__":
    run_tests()