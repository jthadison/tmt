"""
Circuit Breaker Agent Package

This package implements the Circuit Breaker Agent for the Adaptive Trading System.
The agent provides three-tier emergency stop capabilities (agent/account/system level)
with <100ms response time requirements.

Components:
- main.py: FastAPI application entry point
- agent.py: CrewAI circuit breaker agent implementation
- breaker_logic.py: Three-tier breaker system logic
- health_monitor.py: System health monitoring
- emergency_stop.py: Emergency stop procedures
- models.py: Pydantic data models
- config.py: Configuration management
- kafka_events.py: Kafka event handling
"""

__version__ = "0.1.0"
__author__ = "Adaptive Trading System"