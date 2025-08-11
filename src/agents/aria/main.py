"""
ARIA - Adaptive Risk Intelligence Agent
======================================

Main entry point for the Adaptive Risk Intelligence Agent that provides
intelligent position sizing and risk management capabilities for autonomous
trading systems.

This agent implements:
- Dynamic position sizing based on multiple risk factors
- Volatility-adjusted position scaling
- Drawdown-based size reduction
- Correlation-aware portfolio management  
- Prop firm compliance enforcement
- Anti-detection variance generation
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
import uvicorn

from .api.main import create_aria_app
from .position_sizing.calculator import PositionSizeCalculator
from .position_sizing.validators import PositionSizeValidator
from .position_sizing.adjusters import (
    VolatilityAdjuster, DrawdownAdjuster, CorrelationAdjuster,
    PropFirmLimitChecker, SizeVarianceEngine
)
from .position_sizing.adjusters.drawdown import DrawdownTracker
from .position_sizing.adjusters.correlation import PositionTracker, CorrelationCalculator
from .position_sizing.adjusters.prop_firm_limits import AccountFirmMapping
from .position_sizing.adjusters.variance import VarianceHistoryTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('aria.log')
    ]
)

logger = logging.getLogger(__name__)


class ARIAAgent:
    """
    Main ARIA Agent class that orchestrates position sizing and risk management.
    """
    
    def __init__(self):
        self.app: Optional[FastAPI] = None
        self.calculator: Optional[PositionSizeCalculator] = None
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all ARIA components."""
        logger.info("Initializing ARIA Agent components...")
        
        # Initialize data trackers
        drawdown_tracker = DrawdownTracker()
        position_tracker = PositionTracker()
        correlation_calculator = CorrelationCalculator()
        account_firm_mapping = AccountFirmMapping()
        variance_history = VarianceHistoryTracker()
        
        # Initialize adjusters
        volatility_adjuster = VolatilityAdjuster()
        drawdown_adjuster = DrawdownAdjuster(drawdown_tracker)
        correlation_adjuster = CorrelationAdjuster(position_tracker, correlation_calculator)
        prop_firm_checker = PropFirmLimitChecker(account_firm_mapping)
        variance_engine = SizeVarianceEngine(variance_history)
        
        # Initialize validator
        validator = PositionSizeValidator()
        
        # Create main calculator
        self.calculator = PositionSizeCalculator(
            volatility_adjuster=volatility_adjuster,
            drawdown_adjuster=drawdown_adjuster,
            correlation_adjuster=correlation_adjuster,
            prop_firm_checker=prop_firm_checker,
            variance_engine=variance_engine,
            validator=validator
        )
        
        logger.info("ARIA Agent components initialized successfully")
    
    def create_app(self) -> FastAPI:
        """Create and return the FastAPI application."""
        if self.app is None:
            self.app = create_aria_app()
            logger.info("ARIA FastAPI application created")
        
        return self.app
    
    async def start_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the ARIA API server."""
        logger.info(f"Starting ARIA Agent server on {host}:{port}")
        
        app = self.create_app()
        
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
        
        server = uvicorn.Server(config)
        await server.serve()
    
    async def health_check(self) -> bool:
        """Perform health check of all components."""
        try:
            logger.info("Performing ARIA Agent health check...")
            
            # Test calculator availability
            if self.calculator is None:
                logger.error("Position size calculator not initialized")
                return False
            
            # Test component health (simplified)
            # In production, this would test database connections, etc.
            
            logger.info("ARIA Agent health check passed")
            return True
            
        except Exception as e:
            logger.error(f"ARIA Agent health check failed: {str(e)}")
            return False
    
    def get_status(self) -> dict:
        """Get current status of the ARIA Agent."""
        return {
            'status': 'running',
            'calculator_initialized': self.calculator is not None,
            'app_created': self.app is not None,
            'components': {
                'volatility_adjuster': True,
                'drawdown_adjuster': True,
                'correlation_adjuster': True,
                'prop_firm_checker': True,
                'variance_engine': True,
                'validator': True
            }
        }


# Global agent instance
_aria_agent: Optional[ARIAAgent] = None


def get_aria_agent() -> ARIAAgent:
    """Get or create the global ARIA agent instance."""
    global _aria_agent
    
    if _aria_agent is None:
        _aria_agent = ARIAAgent()
    
    return _aria_agent


async def main():
    """Main entry point for running ARIA as a standalone service."""
    logger.info("Starting ARIA - Adaptive Risk Intelligence Agent")
    
    try:
        # Create agent
        agent = get_aria_agent()
        
        # Perform health check
        if not await agent.health_check():
            logger.error("Health check failed, exiting")
            sys.exit(1)
        
        # Start server
        await agent.start_server()
        
    except KeyboardInterrupt:
        logger.info("ARIA Agent shutdown requested")
    
    except Exception as e:
        logger.error(f"ARIA Agent failed to start: {str(e)}")
        sys.exit(1)
    
    finally:
        logger.info("ARIA Agent shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())