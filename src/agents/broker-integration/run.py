#!/usr/bin/env python3
"""
Run Script for OANDA Broker Integration Service
Story 8.1: Broker Authentication & Connection Management
"""
import os
import sys
from pathlib import Path

def setup_environment():
    """Set up environment variables for development"""
    
    # Default development configuration
    env_vars = {
        'VAULT_URL': 'http://localhost:8200',
        'VAULT_TOKEN': 'dev-token',  # For development only
        'LOG_LEVEL': 'INFO',
        'ENVIRONMENT': 'development'
    }
    
    for key, value in env_vars.items():
        if key not in os.environ:
            os.environ[key] = value
            print(f"Set {key}={value}")

def main():
    """Run the OANDA broker integration service"""
    
    print("🚀 Starting OANDA Broker Integration Service")
    print("Story 8.1: Broker Authentication & Connection Management")
    print("-" * 60)
    
    # Setup environment
    setup_environment()
    
    # Create data directory
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    print(f"📁 Data directory: {data_dir.absolute()}")
    
    # Display configuration
    print("\n⚙️  Configuration:")
    print(f"   Vault URL: {os.environ.get('VAULT_URL')}")
    print(f"   Log Level: {os.environ.get('LOG_LEVEL')}")
    print(f"   Environment: {os.environ.get('ENVIRONMENT')}")
    
    print("\n🔗 Available Endpoints:")
    print("   Health Check:    http://localhost:8000/health")
    print("   API Docs:        http://localhost:8000/docs")
    print("   Dashboard WS:    ws://localhost:8000/ws/dashboard")
    
    print("\n📊 Features Implemented:")
    print("   ✅ Secure credential storage with HashiCorp Vault")
    print("   ✅ OANDA authentication & multi-account support")
    print("   ✅ High-performance connection pooling")
    print("   ✅ Automatic reconnection with circuit breakers")
    print("   ✅ Real-time dashboard status via WebSocket")
    print("   ✅ Session management with persistence")
    print("   ✅ Comprehensive monitoring & metrics")
    
    print("\n🧪 Testing:")
    print("   Run tests: python -m pytest tests/ -v")
    
    print("\n" + "-" * 60)
    
    try:
        # Import and run the FastAPI application
        import uvicorn
        from main import app
        
        print("🌐 Starting FastAPI server on http://localhost:8000")
        print("Press Ctrl+C to stop the server")
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level=os.environ.get('LOG_LEVEL', 'INFO').lower(),
            reload=os.environ.get('ENVIRONMENT') == 'development'
        )
        
    except KeyboardInterrupt:
        print("\n\n👋 OANDA Broker Integration Service stopped")
    except ImportError as e:
        print(f"\n❌ Error: {e}")
        print("Please install dependencies: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()