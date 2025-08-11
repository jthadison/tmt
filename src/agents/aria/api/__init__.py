"""
ARIA API Module
===============

REST API endpoints for the Adaptive Risk Intelligence Agent (ARIA)
position sizing and risk management functionality.
"""

from .main import app, create_aria_app

__all__ = ["app", "create_aria_app"]