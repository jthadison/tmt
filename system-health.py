#!/usr/bin/env python3
"""
TMT Trading System - Health Check Script

Comprehensive health monitoring for the trading system.
Can run in monitoring mode or one-shot check mode.

Usage:
    python system-health.py [--mode native|docker] [--monitor] [--interval 30]
    
Options:
    --mode: Specify deployment mode (auto-detect if not specified)
    --monitor: Run continuous monitoring (default: one-shot check)
    --interval: Monitoring interval in seconds (default: 30)
    --alerts: Enable basic alerting (requires configuration)
"""

import asyncio
import sys
import argparse
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import aiohttp
import psutil
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("system_health")

class TradingSystemHealthMonitor:
    """Comprehensive health monitoring for the trading system"""
    
    def __init__(self, deployment_mode: str = "auto", enable_alerts: bool = False):
        self.deployment_mode = self._detect_deployment_mode() if deployment_mode == "auto" else deployment_mode
        self.enable_alerts = enable_alerts
        self.last_check_time = None
        self.health_history = []
        
        # Health check configurations
        self.services = {
            "orchestrator": {"port": 8082, "endpoint": "/health", "critical": True},
            "market_analysis": {"port": 8002, "endpoint": "/health", "critical": True},
            "execution_engine": {"port": 8004, "endpoint": "/health", "critical": True},
            "dashboard": {"port": 8090, "endpoint": "/api/health", "critical": False},
        }
        
        self.infrastructure = {
            "postgres": {"port": 5432, "critical": True},
            "redis": {"port": 6379, "critical": True},
            "kafka": {"port": 9092, "critical": False},
            "prometheus": {"port": 9090, "endpoint": "/-/healthy", "critical": False},
            "grafana": {"port": 3001, "endpoint": "/api/health", "critical": False},
        }
    
    def _detect_deployment_mode(self) -> str:
        """Auto-detect deployment mode"""
        if Path("docker-compose.yml").exists():
            # Check if Docker services are running
            try:
                result = subprocess.run(
                    ["docker-compose", "ps", "-q"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    return "docker"
            except:
                pass
        return "native"
    
    async def run_health_check(self) -> Dict:
        """Run comprehensive health check"""
        logger.info(f"🔍 Running health check ({self.deployment_mode} mode)...")
        
        start_time = datetime.now()
        health_report = {
            "timestamp": start_time.isoformat(),
            "deployment_mode": self.deployment_mode,
            "overall_status": "healthy",
            "services": {},
            "infrastructure": {},
            "system_metrics": {},
            "issues": [],
            "recommendations": []
        }
        
        # Check core trading services
        logger.info("🎯 Checking core trading services...")
        service_results = await self._check_services()
        health_report["services"] = service_results
        
        # Check infrastructure services
        logger.info("🏗️ Checking infrastructure services...")
        infrastructure_results = await self._check_infrastructure()
        health_report["infrastructure"] = infrastructure_results
        
        # Check system metrics
        logger.info("📊 Collecting system metrics...")
        system_metrics = await self._collect_system_metrics()
        health_report["system_metrics"] = system_metrics
        
        # Analyze overall health
        health_report = self._analyze_overall_health(health_report)
        
        # Store in history
        self.health_history.append(health_report)
        if len(self.health_history) > 100:  # Keep last 100 checks
            self.health_history.pop(0)
        
        self.last_check_time = datetime.now()
        
        return health_report
    
    async def _check_services(self) -> Dict:
        """Check trading system services"""
        results = {}
        
        for service_name, config in self.services.items():
            result = await self._check_http_endpoint(
                service_name, 
                config["port"], 
                config["endpoint"]
            )
            result["critical"] = config["critical"]
            results[service_name] = result
        
        return results
    
    async def _check_infrastructure(self) -> Dict:
        """Check infrastructure services"""
        results = {}
        
        for service_name, config in self.infrastructure.items():
            if "endpoint" in config:
                # HTTP endpoint check
                result = await self._check_http_endpoint(
                    service_name,
                    config["port"],
                    config["endpoint"]
                )
            else:
                # Port connectivity check
                result = await self._check_port_connectivity(
                    service_name,
                    config["port"]
                )
            
            result["critical"] = config["critical"]
            results[service_name] = result
        
        return results
    
    async def _check_http_endpoint(self, service_name: str, port: int, endpoint: str) -> Dict:
        """Check HTTP endpoint health"""
        url = f"http://localhost:{port}{endpoint}"
        
        try:
            start_time = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    response_time = (time.time() - start_time) * 1000  # ms
                    
                    if response.status == 200:
                        try:
                            health_data = await response.json()
                            return {
                                "status": "healthy",
                                "response_time_ms": round(response_time, 2),
                                "details": health_data,
                                "url": url
                            }
                        except:
                            return {
                                "status": "healthy",
                                "response_time_ms": round(response_time, 2),
                                "details": "OK",
                                "url": url
                            }
                    else:
                        return {
                            "status": "unhealthy",
                            "response_time_ms": round(response_time, 2),
                            "error": f"HTTP {response.status}",
                            "url": url
                        }
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "error": "Request timed out",
                "url": url
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "url": url
            }
    
    async def _check_port_connectivity(self, service_name: str, port: int) -> Dict:
        """Check port connectivity"""
        try:
            start_time = time.time()
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection('localhost', port),
                timeout=5
            )
            response_time = (time.time() - start_time) * 1000
            writer.close()
            await writer.wait_closed()
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "details": f"Port {port} accessible"
            }
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "error": f"Port {port} connection timed out"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Port {port} not accessible: {str(e)}"
            }
    
    async def _collect_system_metrics(self) -> Dict:
        """Collect system performance metrics"""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network and process info
            network_io = psutil.net_io_counters()
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "network_bytes_sent": network_io.bytes_sent,
                "network_bytes_recv": network_io.bytes_recv,
                "uptime_hours": round((datetime.now() - boot_time).total_seconds() / 3600, 1),
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }
        except Exception as e:
            logger.warning(f"Failed to collect system metrics: {e}")
            return {"error": str(e)}
    
    def _analyze_overall_health(self, health_report: Dict) -> Dict:
        """Analyze overall system health and generate recommendations"""
        issues = []
        recommendations = []
        critical_issues = 0
        
        # Check service health
        for service_name, service_data in health_report["services"].items():
            if service_data["status"] != "healthy":
                issue = f"{service_name} service is {service_data['status']}"
                issues.append(issue)
                if service_data["critical"]:
                    critical_issues += 1
                    recommendations.append(f"Restart {service_name} service immediately")
        
        # Check infrastructure health
        for infra_name, infra_data in health_report["infrastructure"].items():
            if infra_data["status"] != "healthy":
                issue = f"{infra_name} infrastructure is {infra_data['status']}"
                issues.append(issue)
                if infra_data["critical"]:
                    critical_issues += 1
                    recommendations.append(f"Check {infra_name} service configuration")
        
        # Check system metrics
        metrics = health_report["system_metrics"]
        if "cpu_percent" in metrics and metrics["cpu_percent"] > 80:
            issues.append(f"High CPU usage: {metrics['cpu_percent']}%")
            recommendations.append("Monitor CPU-intensive processes")
        
        if "memory_percent" in metrics and metrics["memory_percent"] > 85:
            issues.append(f"High memory usage: {metrics['memory_percent']}%")
            recommendations.append("Consider increasing system memory or optimizing applications")
        
        if "disk_percent" in metrics and metrics["disk_percent"] > 90:
            issues.append(f"Low disk space: {metrics['disk_percent']}% used")
            recommendations.append("Clean up disk space immediately")
        
        # Determine overall status
        if critical_issues > 0:
            overall_status = "critical"
        elif len(issues) > 0:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        health_report["overall_status"] = overall_status
        health_report["issues"] = issues
        health_report["recommendations"] = recommendations
        health_report["critical_issues_count"] = critical_issues
        
        return health_report
    
    def print_health_report(self, health_report: Dict):
        """Print formatted health report"""
        status_emoji = {
            "healthy": "✅",
            "warning": "⚠️",
            "critical": "❌",
            "timeout": "⏱️",
            "error": "💥"
        }
        
        overall_emoji = status_emoji.get(health_report["overall_status"], "❓")
        
        print(f"\n{overall_emoji} TMT Trading System Health Report")
        print("=" * 60)
        print(f"Timestamp: {health_report['timestamp']}")
        print(f"Mode: {health_report['deployment_mode']}")
        print(f"Overall Status: {health_report['overall_status'].upper()}")
        
        # Services
        print("\n🎯 Core Trading Services:")
        for service_name, data in health_report["services"].items():
            emoji = status_emoji.get(data["status"], "❓")
            critical = " (CRITICAL)" if data["critical"] else ""
            response_time = f" ({data.get('response_time_ms', 0):.1f}ms)" if 'response_time_ms' in data else ""
            print(f"  {emoji} {service_name}{critical}{response_time}")
            if data["status"] != "healthy":
                print(f"      Error: {data.get('error', 'Unknown error')}")
        
        # Infrastructure
        print("\n🏗️ Infrastructure Services:")
        for service_name, data in health_report["infrastructure"].items():
            emoji = status_emoji.get(data["status"], "❓")
            critical = " (CRITICAL)" if data["critical"] else ""
            response_time = f" ({data.get('response_time_ms', 0):.1f}ms)" if 'response_time_ms' in data else ""
            print(f"  {emoji} {service_name}{critical}{response_time}")
            if data["status"] != "healthy":
                print(f"      Error: {data.get('error', 'Unknown error')}")
        
        # System Metrics
        metrics = health_report["system_metrics"]
        if "error" not in metrics:
            print("\n📊 System Metrics:")
            print(f"  CPU: {metrics.get('cpu_percent', 0):.1f}%")
            print(f"  Memory: {metrics.get('memory_percent', 0):.1f}% ({metrics.get('memory_available_gb', 0):.1f}GB available)")
            print(f"  Disk: {metrics.get('disk_percent', 0):.1f}% ({metrics.get('disk_free_gb', 0):.1f}GB free)")
            print(f"  Uptime: {metrics.get('uptime_hours', 0):.1f} hours")
        
        # Issues and Recommendations
        if health_report["issues"]:
            print("\n⚠️ Issues Found:")
            for issue in health_report["issues"]:
                print(f"  • {issue}")
        
        if health_report["recommendations"]:
            print("\n💡 Recommendations:")
            for rec in health_report["recommendations"]:
                print(f"  • {rec}")
        
        print("=" * 60)
    
    async def monitor_continuously(self, interval: int = 30):
        """Run continuous health monitoring"""
        logger.info(f"🔄 Starting continuous health monitoring (every {interval}s)")
        logger.info("Press Ctrl+C to stop monitoring")
        
        try:
            while True:
                health_report = await self.run_health_check()
                self.print_health_report(health_report)
                
                # Simple alerting
                if self.enable_alerts and health_report["overall_status"] == "critical":
                    logger.error("🚨 CRITICAL SYSTEM ISSUES DETECTED!")
                
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="TMT Trading System Health Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python system-health.py                     # One-shot health check
  python system-health.py --monitor           # Continuous monitoring
  python system-health.py --mode docker       # Check Docker deployment
  python system-health.py --monitor --interval 60  # Monitor every 60 seconds
        """
    )
    
    parser.add_argument("--mode", choices=["auto", "native", "docker"], default="auto",
                       help="Deployment mode (default: auto-detect)")
    parser.add_argument("--monitor", action="store_true",
                       help="Run continuous monitoring")
    parser.add_argument("--interval", type=int, default=30,
                       help="Monitoring interval in seconds (default: 30)")
    parser.add_argument("--alerts", action="store_true",
                       help="Enable basic alerting")
    parser.add_argument("--json", action="store_true",
                       help="Output in JSON format")
    
    args = parser.parse_args()
    
    try:
        monitor = TradingSystemHealthMonitor(args.mode, args.alerts)
        
        if args.monitor:
            await monitor.monitor_continuously(args.interval)
        else:
            health_report = await monitor.run_health_check()
            
            if args.json:
                print(json.dumps(health_report, indent=2))
            else:
                monitor.print_health_report(health_report)
                
            # Exit with error code if unhealthy
            if health_report["overall_status"] in ["critical", "warning"]:
                return 1
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Health check interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))