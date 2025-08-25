#!/usr/bin/env python3
"""
Load environment variables from .env file and restart services with proper configuration
"""

import os
import subprocess
import sys
from pathlib import Path

def load_env_vars():
    """Load environment variables from .env file"""
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ .env file not found!")
        return False
    
    env_vars = {}
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    # Set environment variables for current session
    for key, value in env_vars.items():
        os.environ[key] = value
    
    print("✅ Loaded environment variables:")
    print(f"   OANDA_API_KEY: {env_vars.get('OANDA_API_KEY', 'NOT SET')[:20]}...")
    print(f"   OANDA_ACCOUNT_ID: {env_vars.get('OANDA_ACCOUNT_ID', 'NOT SET')}")
    print(f"   OANDA_ENVIRONMENT: {env_vars.get('OANDA_ENVIRONMENT', 'NOT SET')}")
    print(f"   DATABASE_URL: {env_vars.get('DATABASE_URL', 'NOT SET')}")
    
    return True

def restart_with_env():
    """Restart services with environment variables loaded"""
    print("\n🔄 Restarting services with OANDA credentials...")
    
    # First ensure infrastructure is running
    result = subprocess.run([
        "python", "restart-infrastructure.py", "--infrastructure-only"
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Infrastructure restart failed: {result.stderr}")
        return False
    
    print("✅ Infrastructure restarted")
    
    # Now restart trading services with environment
    env = os.environ.copy()
    
    trading_services = [
        {
            "name": "orchestrator",
            "command": ["python", "-m", "uvicorn", "orchestrator.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
            "cwd": "."
        },
        {
            "name": "market_analysis", 
            "command": ["python", "start-market-analysis.py"],
            "cwd": "."
        },
        {
            "name": "execution_engine",
            "command": ["python", "start-execution-engine.py"],
            "cwd": "."
        }
    ]
    
    print("\n🚀 Starting trading services with OANDA credentials...")
    
    for service in trading_services:
        print(f"   Starting {service['name']}...")
        try:
            process = subprocess.Popen(
                service["command"],
                cwd=service["cwd"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"   ✅ {service['name']} started (PID: {process.pid})")
        except Exception as e:
            print(f"   ❌ Failed to start {service['name']}: {e}")
    
    return True

if __name__ == "__main__":
    print("🔧 Loading OANDA Credentials and Restarting Services")
    print("=" * 60)
    
    if load_env_vars():
        restart_with_env()
        print("\n" + "=" * 60)
        print("✅ Services restarted with OANDA credentials!")
        print("\nTo verify connection:")
        print("   curl http://localhost:8000/health")
    else:
        sys.exit(1)