#!/usr/bin/env python3
"""
TMT Trading System - Execution Engine Startup Script
Starts the execution engine with graceful dependency handling.
"""

import sys
import os
import subprocess
import time
from pathlib import Path

def main():
    """Start the execution engine"""
    print("Starting TMT Execution Engine...")
    
    # Change to execution engine directory
    execution_engine_dir = Path(__file__).parent / "execution-engine"
    
    if not execution_engine_dir.exists():
        print(f"Error: Execution engine directory not found: {execution_engine_dir}")
        sys.exit(1)
    
    os.chdir(execution_engine_dir)
    
    # Try to start the simplified execution engine
    try:
        print("Starting simplified execution engine...")
        
        # Start the simplified execution engine
        process = subprocess.Popen(
            [sys.executable, "simple_main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a moment for startup
        time.sleep(2)
        
        # Check if process is still running
        if process.poll() is None:
            print("✅ Execution engine started successfully on port 8081")
            print("   Health endpoint: http://localhost:8081/health")
            print("   Status endpoint: http://localhost:8081/status")
            
            # Keep the process running by waiting for it
            try:
                process.wait()
            except KeyboardInterrupt:
                print("\nShutting down execution engine...")
                process.terminate()
                process.wait()
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Execution engine failed to start")
            print(f"Error: {stderr}")
            if stdout:
                print(f"Output: {stdout}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Failed to start execution engine: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()