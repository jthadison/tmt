"""
Pattern Detection Agent Configuration
"""

import os
from datetime import datetime

# Core trading instruments for pattern monitoring
ACTIVE_MONITORING_INSTRUMENTS = [
    "EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CHF"
]

# Pattern detection parameters
PATTERN_CONFIDENCE_THRESHOLD = 0.75
MIN_PATTERN_STRENGTH = 0.6
MAX_CONCURRENT_PATTERNS = 10

# Wyckoff methodology settings
WYCKOFF_ENABLED = True
VOLUME_ANALYSIS_ENABLED = True
SMART_MONEY_CONCEPTS_ENABLED = True

# API configuration
PORT = int(os.environ.get('PORT', 8008))
HOST = os.environ.get('HOST', '0.0.0.0')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')

# Health check configuration
HEALTH_CHECK_INTERVAL = 30  # seconds
SERVICE_NAME = "pattern-detection"