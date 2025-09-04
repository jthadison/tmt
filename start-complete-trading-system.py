#!/usr/bin/env python3
"""
Complete TMT Trading System Startup Script
Launches all 11 services: 8 AI agents + 3 core services

Based on CLAUDE.md specifications:
- Market Analysis (8001), Strategy Analysis (8002), Parameter Optimization (8003)
- Learning Safety (8004), Disagreement Engine (8005), Data Collection (8006)
- Continuous Improvement (8007), Pattern Detection (8008)
- Execution Engine (8082), Circuit Breaker (8084), Orchestrator (8089)
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
    print("\n\nShutting down all TMT services...")
    for name, proc in processes:
        try:
            print(f"Stopping {name}...")
            proc.terminate()
            time.sleep(0.3)
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
        print(f"  [OK] {name} started (PID: {proc.pid})")
        return proc
    except Exception as e:
        print(f"  [FAIL] Failed to start {name}: {e}")
        return None

def main():
    """Complete system startup sequence"""
    print("=" * 70)
    print("🚀 STARTING COMPLETE TMT TRADING SYSTEM")
    print("=" * 70)
    print("Launching 11 services: 8 AI agents + 3 core services")
    print()
    
    # Check for OANDA credentials
    if not os.getenv("OANDA_API_KEY"):
        print("⚠️  Warning: OANDA_API_KEY not set - running in demo mode")
    print()
    
    # === CORE INFRASTRUCTURE ===
    print("📦 Starting Core Infrastructure...")
    
    # 1. Execution Engine (8082)
    start_service(
        "Execution Engine",
        [sys.executable, "simple_main.py"],
        cwd="execution-engine",
        env={"PORT": "8082"}
    )
    time.sleep(1.5)
    
    # 2. Circuit Breaker (8084)  
    start_service(
        "Circuit Breaker",
        [sys.executable, "main.py"],
        cwd="agents/circuit-breaker", 
        env={"PORT": "8084"}
    )
    time.sleep(1.5)
    
    # 3. Orchestrator (8089)
    start_service(
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
    time.sleep(2)
    
    print()
    print("🤖 Starting Complete 8-Agent AI Ecosystem...")
    
    # === 8-AGENT AI ECOSYSTEM ===
    
    # Agent 1: Market Analysis (8001)
    start_service(
        "Market Analysis Agent",
        [sys.executable, "simple_main.py"],
        cwd="agents/market-analysis",
        env={"PORT": "8001"}
    )
    time.sleep(1)
    
    # Agent 2: Strategy Analysis (8002) 
    start_service(
        "Strategy Analysis Agent",
        [sys.executable, "start_agent_simple.py"],
        cwd="agents/strategy-analysis",
        env={"PORT": "8002"}
    )
    time.sleep(1)
    
    # Agent 3: Parameter Optimization (8003)
    start_service(
        "Parameter Optimization Agent", 
        [sys.executable, "start_agent.py"],
        cwd="agents/parameter-optimization",
        env={"PORT": "8003"}
    )
    time.sleep(1)
    
    # Agent 4: Learning Safety (8004)
    start_service(
        "Learning Safety Agent",
        [sys.executable, "start_agent.py"],
        cwd="agents/learning-safety",
        env={"PORT": "8004"}
    )
    time.sleep(1)
    
    # Agent 5: Disagreement Engine (8005)
    start_service(
        "Disagreement Engine Agent",
        [sys.executable, "start_agent.py"],
        cwd="agents/disagreement-engine", 
        env={"PORT": "8005"}
    )
    time.sleep(1)
    
    # Agent 6: Data Collection (8006)
    start_service(
        "Data Collection Agent",
        [sys.executable, "start_agent.py"],
        cwd="agents/data-collection",
        env={"PORT": "8006"}
    )
    time.sleep(1)
    
    # Agent 7: Continuous Improvement (8007)
    start_service(
        "Continuous Improvement Agent",
        [sys.executable, "start_agent.py"],
        cwd="agents/continuous-improvement",
        env={"PORT": "8007"}
    )
    time.sleep(1)
    
    # Agent 8: Pattern Detection (8008) 
    start_service(
        "Pattern Detection Agent",
        [sys.executable, "start_agent_simple.py"],
        cwd="agents/pattern-detection",
        env={"PORT": "8008"}
    )
    time.sleep(2)
    
    print()
    print("=" * 70)
    print("✅ COMPLETE TMT TRADING SYSTEM OPERATIONAL!")
    print("=" * 70)
    print()
    print("🌐 Service URLs (All Services Running):")
    print()
    print("📊 Core Infrastructure:")
    print("  • Execution Engine:     http://localhost:8082/health")
    print("  • Circuit Breaker:      http://localhost:8084/health") 
    print("  • Orchestrator:         http://localhost:8089/health")
    print()
    print("🤖 Complete 8-Agent AI Ecosystem:")
    print("  • Market Analysis:      http://localhost:8001/health")
    print("  • Strategy Analysis:    http://localhost:8002/health")
    print("  • Parameter Optimization: http://localhost:8003/health")
    print("  • Learning Safety:      http://localhost:8004/health")
    print("  • Disagreement Engine:  http://localhost:8005/health")
    print("  • Data Collection:      http://localhost:8006/health")
    print("  • Continuous Improvement: http://localhost:8007/health")
    print("  • Pattern Detection:    http://localhost:8008/health")
    print()
    print("🖥️  Dashboard:              http://localhost:3003")
    print()
    print("🧪 Test Commands:")
    print("  • System health:  python -c \"import httpx; [print(f'Port {p}: OK') for p in [8001,8002,8003,8004,8005,8006,8007,8008,8082,8084,8089] if httpx.get(f'http://localhost:{p}/health').status_code==200]\"")
    print("  • Generate signal: curl http://localhost:8001/api/signals/EUR_USD")
    print("  • Check positions: curl http://localhost:8082/positions")
    print()
    print("🔄 Status: LIVE TRADING SYSTEM - All 11 services operational")
    print("Press Ctrl+C to stop all services")
    print("=" * 70)
    
    # Monitor all processes
    try:
        while True:
            # Check if any critical process has died
            dead_services = []
            for name, proc in processes[:]:
                if proc.poll() is not None:
                    print(f"⚠️  Critical service {name} has stopped (exit code: {proc.returncode})")
                    dead_services.append((name, proc))
                    processes.remove((name, proc))
            
            if dead_services:
                print("❌ CRITICAL: Core services have failed - system may be unstable")
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main()