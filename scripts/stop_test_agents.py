#!/usr/bin/env python3
"""
Test Agent Orchestration - Stop Script
Stops all running test agents started by start_test_agents.py
"""
import os
import signal
import sys
from pathlib import Path


def main():
    """Stop all test agents"""
    print("=" * 60)
    print("TMT Trading System - Stopping Test Agents")
    print("=" * 60)
    print()

    project_root = Path(__file__).parent.parent
    pids_file = project_root / "test_agent_pids.txt"

    if not pids_file.exists():
        print("⚠️  No PID file found. Agents may not be running.")
        print(f"   Expected: {pids_file}")
        sys.exit(0)

    # Read PIDs
    stopped_count = 0
    failed_count = 0

    with open(pids_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                name, pid = line.split(":")
                pid = int(pid)

                print(f"🛑 Stopping {name} (PID: {pid})...")

                try:
                    # Check if process exists
                    os.kill(pid, 0)

                    # Try graceful shutdown first
                    os.kill(pid, signal.SIGTERM)

                    # Wait a bit for graceful shutdown
                    import time
                    time.sleep(2)

                    # Check if still running
                    try:
                        os.kill(pid, 0)
                        # Still running, force kill
                        print(f"   ⚠️  Force killing {name}...")
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        # Process terminated gracefully
                        pass

                    print(f"   ✓ Stopped {name}")
                    stopped_count += 1

                except ProcessLookupError:
                    print(f"   ℹ️  {name} not running (PID {pid} not found)")
                    stopped_count += 1

                except PermissionError:
                    print(f"   ✗ Permission denied to stop {name} (PID {pid})")
                    failed_count += 1

            except ValueError:
                print(f"✗ Invalid PID file entry: {line}")
                failed_count += 1

            except Exception as e:
                print(f"✗ Error stopping process: {e}")
                failed_count += 1

    # Remove PID file
    try:
        pids_file.unlink()
        print(f"\n✓ Removed PID file: {pids_file}")
    except Exception as e:
        print(f"\n⚠️  Could not remove PID file: {e}")

    # Summary
    print("\n" + "=" * 60)
    print(f"✓ Stopped: {stopped_count} agents")
    if failed_count > 0:
        print(f"✗ Failed: {failed_count} agents")
    print("=" * 60)

    sys.exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    main()
