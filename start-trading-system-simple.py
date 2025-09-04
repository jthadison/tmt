#!/usr/bin/env python3
"""
Simplified Trading System Startup Script
Starts the core trading services directly without complex process management
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path

# Store processes globally for cleanup
processes = []

def cleanup(signum=None, frame=None):
    """Clean up all processes on exit"""
    print("\n\nShutting down services...")
    for name, proc in processes:
        try:
            print(f"Stopping {name}...")
            proc.terminate()
            time.sleep(0.5)
            if proc.poll() is None:
                proc.kill()
        except:
            pass
    print("All services stopped.")
    sys.exit(0)

# Register cleanup handlers
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def start_service(name, command, cwd=None, env=None):
    """Start a service and add to process list"""
    print(f"Starting {name}...")
    
    # Merge environment variables
    service_env = os.environ.copy()
    if env:
        service_env.update(env)
    
    # Start the process
    try:
        proc = subprocess.Popen(
            command,
            cwd=cwd or Path.cwd(),
            env=service_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        processes.append((name, proc))
        print(f"[OK] {name} started (PID: {proc.pid})")
        return proc
    except Exception as e:
        print(f"[FAIL] Failed to start {name}: {e}")
        return None

def main():
    """Main startup sequence"""
    print("=" * 60)
    print("Starting TMT Trading System (Simplified)")
    print("=" * 60)
    
    # Check for OANDA credentials
    if not os.getenv("OANDA_API_KEY"):
        print("Warning: OANDA_API_KEY not set - running in demo mode")
    
    # 1. Start Execution Engine
    exec_proc = start_service(
        "Execution Engine",
        [sys.executable, "simple_main.py"],
        cwd="execution-engine",
        env={"PORT": "8082"}
    )
    time.sleep(2)  # Give it time to start
    
    # 2. Start Market Analysis
    market_proc = start_service(
        "Market Analysis",
        [sys.executable, "simple_main.py"],
        cwd="agents/market-analysis",
        env={"PORT": "8001"}
    )
    time.sleep(2)
    
    # 3. Start Orchestrator (if available)
    orchestrator_path = Path("orchestrator/app/main.py")
    if orchestrator_path.exists():
        orch_proc = start_service(
            "Orchestrator",
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8089"],
            cwd="orchestrator",
            env={
                "ENABLE_TRADING": "true",
                "PORT": "8089",
                "OANDA_API_KEY": os.getenv("OANDA_API_KEY", ""),
                "OANDA_ACCOUNT_IDS": os.getenv("OANDA_ACCOUNT_IDS", "101-001-21040028-001")
            }
        )
    else:
        print("Warning: Orchestrator not found - skipping")
    
    print("\n" + "=" * 60)
    print("Trading System Started Successfully!")
    print("=" * 60)
    print("\nService URLs:")
    print("  • Execution Engine: http://localhost:8082/health")
    print("  • Market Analysis:  http://localhost:8001/health")
    print("  • Orchestrator:     http://localhost:8089/health")
    print("\nTest Commands:")
    print("  • Check health: curl http://localhost:8082/health")
    print("  • Get signals:  curl http://localhost:8001/api/signals/EUR_USD")
    print("\nPress Ctrl+C to stop all services\n")
    
    # Keep running and monitor processes
    try:
        while True:
            # Check if any process has died
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"Warning: {name} has stopped (exit code: {proc.returncode})")
                    # Remove from list
                    processes.remove((name, proc))
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main()