"""
Pytest runner with proper path setup
"""

import sys
import subprocess
import os

# Add current directory to Python path
sys.path.insert(0, '.')

# Set PYTHONPATH environment variable
os.environ['PYTHONPATH'] = '.'

# Run pytest with the current environment
if __name__ == "__main__":
    cmd = [
        sys.executable, 
        "-m", 
        "pytest", 
        "tests/test_position_manager.py::TestPositionManager::test_get_open_positions_success",
        "-v",
        "--tb=short"
    ]
    
    print("Running specific position manager test...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    print("\nSTDERR:")
    print(result.stderr)
    print(f"\nReturn code: {result.returncode}")