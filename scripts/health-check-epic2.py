#!/usr/bin/env python3
"""
Epic 2 E2E Testing - Service Health Check Script
Verifies all required services are running for Epic 2 testing
"""

import sys
import time
from typing import Tuple
import urllib.request
import urllib.error
import json

# ANSI color codes (disabled on Windows to avoid encoding issues)
try:
    # Try to enable ANSI colors on Windows
    import os
    if os.name == 'nt':
        os.system('color')
except:
    pass

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = ''
    RED = ''
    YELLOW = ''
    BLUE = ''
    CYAN = ''
    BOLD = ''
    END = ''

def check_service(name: str, url: str, timeout: int = 5) -> Tuple[bool, str, float]:
    """
    Check if a service is healthy
    Returns: (is_healthy, status_message, response_time)
    """
    start_time = time.time()
    try:
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=timeout) as response:
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            status_code = response.getcode()

            if status_code == 200:
                try:
                    data = json.loads(response.read().decode('utf-8'))
                    status_msg = data.get('status', 'ok')
                    return True, f"{status_code} - {status_msg}", response_time
                except:
                    return True, f"{status_code} - OK", response_time
            else:
                return False, f"{status_code}", response_time

    except urllib.error.HTTPError as e:
        response_time = (time.time() - start_time) * 1000
        return False, f"HTTP {e.code}", response_time
    except urllib.error.URLError as e:
        response_time = (time.time() - start_time) * 1000
        return False, f"Connection refused", response_time
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return False, f"Error: {str(e)[:30]}", response_time

def print_header():
    """Print header"""
    print()
    print("=" * 80)
    print("Epic 2 E2E Testing - Service Health Check")
    print("=" * 80)
    print()

def print_section(title: str):
    """Print section header"""
    print(f"\n{title}")
    print("-" * len(title))

def print_service_status(name: str, port: int, is_healthy: bool, status: str, response_time: float):
    """Print formatted service status"""
    status_icon = "[OK]" if is_healthy else "[FAIL]"

    # Format response time
    time_str = f"{response_time:6.1f}ms"

    print(f"  {status_icon:6s} {name:30s} http://localhost:{port:5d}  {time_str:10s}  {status}")

def main():
    """Main health check routine"""
    print_header()

    # Define all services required for Epic 2
    services = {
        "Core Infrastructure (Required for Stories 2.1, 2.2, 2.3)": [
            ("Execution Engine", 8082, "http://localhost:8082/health"),
            ("Circuit Breaker Agent", 8084, "http://localhost:8084/health"),
            ("Orchestrator", 8089, "http://localhost:8089/health/detailed"),  # Use detailed endpoint (liveness check)
            ("Dashboard", 8090, "http://localhost:8090"),
        ],
        "AI Agent Ecosystem (Supporting Services)": [
            ("Market Analysis", 8001, "http://localhost:8001/health"),
            ("Strategy Analysis", 8002, "http://localhost:8002/health"),
            ("Parameter Optimization", 8003, "http://localhost:8003/health"),
            ("Learning Safety", 8004, "http://localhost:8004/health"),
            ("Disagreement Engine", 8005, "http://localhost:8005/health"),
            ("Data Collection", 8006, "http://localhost:8006/health"),
            ("Continuous Improvement", 8007, "http://localhost:8007/health"),
            ("Pattern Detection", 8008, "http://localhost:8008/health"),
        ]
    }

    # Track overall health
    all_healthy = True
    critical_services_healthy = True
    results = {}

    # Check all services
    for section, service_list in services.items():
        print_section(section)

        for name, port, url in service_list:
            is_healthy, status, response_time = check_service(name, url)
            print_service_status(name, port, is_healthy, status, response_time)

            results[name] = is_healthy

            if not is_healthy:
                all_healthy = False
                # Mark critical services
                if port in [8082, 8084, 8089, 8090]:
                    critical_services_healthy = False

    # Print summary
    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)

    # Count services
    total_services = sum(len(s) for s in services.values())
    healthy_count = sum(1 for v in results.values() if v)
    unhealthy_count = total_services - healthy_count

    print(f"\n  Total Services:   {total_services}")
    print(f"  Healthy:          {healthy_count}")
    print(f"  Unhealthy:        {unhealthy_count}")

    # Epic 2 readiness check
    print()
    print("Epic 2 E2E Testing Readiness:")
    print()

    # Check critical services
    critical_status = {
        "Execution Engine (8082)": results.get("Execution Engine", False),
        "Circuit Breaker (8084)": results.get("Circuit Breaker Agent", False),
        "Orchestrator (8089)": results.get("Orchestrator", False),
        "Dashboard (8090)": results.get("Dashboard", False),
    }

    for service, is_healthy in critical_status.items():
        icon = "[OK]  " if is_healthy else "[FAIL]"
        status_text = "READY" if is_healthy else "NOT READY"
        print(f"  {icon} {service:30s} {status_text}")

    # Story-specific readiness
    print()
    print("Story Readiness:")

    story_21_ready = critical_status["Execution Engine (8082)"] and critical_status["Orchestrator (8089)"] and critical_status["Dashboard (8090)"]
    story_22_ready = story_21_ready and critical_status["Circuit Breaker (8084)"]
    story_23_ready = critical_status["Orchestrator (8089)"] and critical_status["Dashboard (8090)"]

    print(f"  Story 2.1 (Emergency Stop):      {'READY' if story_21_ready else 'NOT READY'}")
    print(f"  Story 2.2 (Emergency Actions):   {'READY' if story_22_ready else 'NOT READY'}")
    print(f"  Story 2.3 (Emergency Rollback):  {'READY' if story_23_ready else 'NOT READY'}")

    # Known blockers
    print()
    print("Known Blockers:")

    blockers = []
    if not critical_status["Circuit Breaker (8084)"]:
        blockers.append("  [!] Blocker 2: Circuit Breaker Agent not running (port 8084)")
        blockers.append("      Fix: Run 'start-trading.bat' or start manually")

    if not critical_status["Orchestrator (8089)"]:
        blockers.append("  [!] Blocker 3: Orchestrator not running or needs restart (port 8089)")
        blockers.append("      Fix: Restart orchestrator to load new API endpoints")

    if not critical_status["Dashboard (8090)"]:
        blockers.append("  [!] Dashboard not running (port 8090)")
        blockers.append("      Fix: cd dashboard && npm run dev")

    if blockers:
        for blocker in blockers:
            print(blocker)
    else:
        print("  [OK] No blockers! All services ready for Epic 2 E2E testing!")

    # Test commands
    print()
    print("Next Steps:")

    if critical_services_healthy:
        print("  [OK] All critical services running!")
        print()
        print("  Run E2E tests:")
        print("    cd dashboard")
        print("    npx playwright test emergency-stop.spec.ts emergency-actions-panel.spec.ts emergency-rollback.spec.ts --reporter=html")
        print("    npx playwright show-report")
    else:
        print("  Start missing services:")
        print("    start-trading.bat  (Windows - starts all services)")
        print("    python start-complete-trading-system.py  (Cross-platform - backend only)")
        print()
        print("  Then run this health check again:")
        print("    python scripts/health-check-epic2.py")

    print()
    print("=" * 80)
    print()

    # Return exit code
    return 0 if critical_services_healthy else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nHealth check interrupted by user")
        sys.exit(130)
