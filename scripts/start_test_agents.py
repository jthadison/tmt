#!/usr/bin/env python3
"""
Test Agent Orchestration - Start Script
Starts all 8 AI agents in test mode for CI/CD integration testing
"""
import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import httpx

# Agent configuration
AGENTS = [
    {"name": "market-analysis", "port": 8001, "path": "agents/market-analysis", "script": "simple_main.py"},
    {"name": "strategy-analysis", "port": 8002, "path": "agents/strategy-analysis", "script": "start_agent_simple.py"},
    {"name": "parameter-optimization", "port": 8003, "path": "agents/parameter-optimization", "script": "start_agent.py"},
    {"name": "learning-safety", "port": 8004, "path": "agents/learning-safety", "script": "start_agent.py"},
    {"name": "disagreement-engine", "port": 8005, "path": "agents/disagreement-engine", "script": "start_agent.py"},
    {"name": "data-collection", "port": 8006, "path": "agents/data-collection", "script": "start_agent.py"},
    {"name": "continuous-improvement", "port": 8007, "path": "agents/continuous-improvement", "script": "start_agent.py"},
    {"name": "pattern-detection", "port": 8008, "path": "agents/pattern-detection", "script": "start_agent_simple.py"},
]

# Core services
CORE_SERVICES = [
    {"name": "execution-engine", "port": 8082, "path": "execution-engine", "script": "simple_main.py"},
    {"name": "orchestrator", "port": 8089, "path": "orchestrator", "script": "app.main"},
    {"name": "circuit-breaker", "port": 8084, "path": "agents/circuit-breaker", "script": "main.py"},
]


class AgentOrchestrator:
    """Manages starting and monitoring test agents"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.processes: Dict[str, subprocess.Popen] = {}
        self.pids_file = project_root / "test_agent_pids.txt"

    def start_agent(self, agent: Dict) -> Optional[subprocess.Popen]:
        """Start a single agent process"""
        agent_path = self.project_root / agent["path"]

        if not agent_path.exists():
            print(f"⚠️  Warning: Agent path not found: {agent_path}")
            return None

        print(f"🚀 Starting {agent['name']} on port {agent['port']}...")

        # Set environment variables
        env = os.environ.copy()
        env["PORT"] = str(agent["port"])
        env["TESTING"] = "true"
        env["LOG_LEVEL"] = "INFO"
        env["PYTHONUNBUFFERED"] = "1"

        # Set database and Redis URLs if needed
        if "DATABASE_URL" in os.environ:
            env["DATABASE_URL"] = os.environ["DATABASE_URL"]
        if "REDIS_URL" in os.environ:
            env["REDIS_URL"] = os.environ["REDIS_URL"]

        try:
            # Determine how to run the script
            script_path = agent_path / agent["script"]

            if agent["script"].endswith(".py"):
                # Direct Python script
                cmd = [sys.executable, agent["script"]]
            else:
                # Python module (like app.main)
                cmd = [sys.executable, "-m", agent["script"]]

            # Start process
            process = subprocess.Popen(
                cmd,
                cwd=agent_path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            print(f"✓ Started {agent['name']} (PID: {process.pid})")
            return process

        except Exception as e:
            print(f"✗ Failed to start {agent['name']}: {e}")
            return None

    async def wait_for_health(
        self, agent: Dict, timeout: int = 30, interval: float = 1.0
    ) -> bool:
        """Wait for agent health endpoint to respond"""
        url = f"http://localhost:{agent['port']}/health"
        start_time = time.time()

        async with httpx.AsyncClient(timeout=5.0) as client:
            while time.time() - start_time < timeout:
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        print(f"✓ {agent['name']} is healthy")
                        return True
                except (httpx.ConnectError, httpx.TimeoutException):
                    pass

                await asyncio.sleep(interval)

        print(f"✗ {agent['name']} health check timeout after {timeout}s")
        return False

    def save_pids(self) -> None:
        """Save all process PIDs to file for cleanup"""
        with open(self.pids_file, "w") as f:
            for name, process in self.processes.items():
                if process and process.poll() is None:
                    f.write(f"{name}:{process.pid}\n")

        print(f"\n✓ Saved {len(self.processes)} PIDs to {self.pids_file}")

    async def start_all(self, include_core: bool = True) -> bool:
        """Start all agents and optionally core services"""
        print("=" * 60)
        print("TMT Trading System - Test Agent Orchestration")
        print("=" * 60)
        print()

        all_services = AGENTS.copy()
        if include_core:
            all_services.extend(CORE_SERVICES)

        # Start all processes
        for agent in all_services:
            process = self.start_agent(agent)
            if process:
                self.processes[agent["name"]] = process

        # Save PIDs immediately
        self.save_pids()

        # Give agents time to initialize
        print("\n⏳ Waiting for agents to initialize...")
        await asyncio.sleep(10)

        # Check health endpoints
        print("\n🏥 Checking agent health...")
        healthy_count = 0
        failed_agents = []

        for agent in all_services:
            if agent["name"] in self.processes:
                is_healthy = await self.wait_for_health(agent, timeout=20)
                if is_healthy:
                    healthy_count += 1
                else:
                    failed_agents.append(agent["name"])

        # Summary
        print("\n" + "=" * 60)
        print(f"✓ {healthy_count}/{len(all_services)} agents healthy")

        if failed_agents:
            print(f"✗ Failed agents: {', '.join(failed_agents)}")

        print("=" * 60)

        return healthy_count == len(all_services)

    def stop_all(self) -> None:
        """Stop all running agents"""
        print("\n🛑 Stopping all agents...")

        for name, process in self.processes.items():
            if process and process.poll() is None:
                print(f"  Stopping {name} (PID: {process.pid})...")
                try:
                    process.terminate()
                    process.wait(timeout=5)
                    print(f"  ✓ Stopped {name}")
                except subprocess.TimeoutExpired:
                    print(f"  ⚠️  Force killing {name}...")
                    process.kill()
                    process.wait()
                except Exception as e:
                    print(f"  ✗ Error stopping {name}: {e}")

        # Clean up PID file
        if self.pids_file.exists():
            self.pids_file.unlink()

        print("\n✓ All agents stopped")


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Start TMT test agents")
    parser.add_argument(
        "--no-core",
        action="store_true",
        help="Don't start core services (orchestrator, execution-engine)",
    )
    parser.add_argument(
        "--keep-running",
        action="store_true",
        help="Keep agents running (don't exit after startup)",
    )

    args = parser.parse_args()

    # Get project root
    project_root = Path(__file__).parent.parent

    # Create orchestrator
    orchestrator = AgentOrchestrator(project_root)

    # Handle cleanup on exit
    def signal_handler(sig, frame):
        print("\n\n🛑 Received interrupt signal...")
        orchestrator.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start all agents
    success = await orchestrator.start_all(include_core=not args.no_core)

    if not success:
        print("\n❌ Some agents failed to start properly")
        if not args.keep_running:
            orchestrator.stop_all()
        sys.exit(1)

    print("\n✅ All agents started successfully!")

    if args.keep_running:
        print("\n📌 Agents are running. Press Ctrl+C to stop.")
        try:
            # Keep running until interrupted
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            orchestrator.stop_all()
    else:
        print("✓ Agent startup complete (use stop_test_agents.py to stop)")

    sys.exit(0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
        sys.exit(130)
