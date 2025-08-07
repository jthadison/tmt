"""
Emergency Stop Implementation

Handles emergency stop procedures with position closure integration
and sub-100ms response time requirements.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx
import structlog

from .models import (
    EmergencyStopRequest, EmergencyStopResponse, 
    PositionCloseRequest, PositionCloseResponse,
    BreakerLevel, BreakerState
)
from .config import config

logger = structlog.get_logger(__name__)


class EmergencyStopManager:
    """
    Manages emergency stop procedures including position closure
    and system shutdown with strict timing requirements.
    """
    
    def __init__(self, breaker_manager):
        self.breaker_manager = breaker_manager
        self.execution_client = httpx.AsyncClient(
            base_url=config.execution_engine_url,
            timeout=httpx.Timeout(5.0),
            limits=httpx.Limits(max_connections=20)
        )
        self._active_stops: Dict[str, asyncio.Task] = {}
        
        logger.info("Emergency stop manager initialized")
    
    async def execute_emergency_stop(
        self, 
        request: EmergencyStopRequest
    ) -> EmergencyStopResponse:
        """
        Execute emergency stop procedure with <100ms response time requirement.
        
        Args:
            request: Emergency stop request with level and details
            
        Returns:
            EmergencyStopResponse with execution results
        """
        start_time = time.time()
        correlation_id = request.correlation_id
        
        try:
            logger.critical(
                "Emergency stop initiated",
                level=request.level.value,
                reason=request.reason.value,
                correlation_id=correlation_id,
                requested_by=request.requested_by
            )
            
            # Get current breaker state
            previous_state = await self._get_current_breaker_state(request.level)
            
            # Check if already in emergency state
            if previous_state == BreakerState.TRIPPED and not request.force:
                response_time = int((time.time() - start_time) * 1000)
                return EmergencyStopResponse(
                    success=True,
                    level=request.level,
                    previous_state=previous_state,
                    new_state=BreakerState.TRIPPED,
                    positions_closed=0,
                    response_time_ms=response_time,
                    correlation_id=correlation_id,
                    message="Circuit breaker already tripped"
                )
            
            # Trigger the circuit breaker first (highest priority)
            await self.breaker_manager._trigger_breaker(
                request.level,
                self._get_identifier_for_level(request.level),
                request.reason,
                request.details
            )
            
            # Execute position closure in parallel (fire-and-forget for speed)
            positions_task = None
            if request.level == BreakerLevel.SYSTEM:
                positions_task = asyncio.create_task(
                    self._close_all_positions(correlation_id)
                )
            elif request.level == BreakerLevel.ACCOUNT:
                account_id = request.details.get('account_id')
                if account_id:
                    positions_task = asyncio.create_task(
                        self._close_account_positions(account_id, correlation_id)
                    )
            
            # Don't wait for position closure to maintain <100ms response
            response_time = int((time.time() - start_time) * 1000)
            
            # Start position closure tracking task
            if positions_task:
                self._active_stops[correlation_id] = positions_task
                asyncio.create_task(
                    self._track_position_closure(correlation_id, positions_task)
                )
            
            logger.critical(
                "Emergency stop executed",
                level=request.level.value,
                response_time_ms=response_time,
                correlation_id=correlation_id
            )
            
            return EmergencyStopResponse(
                success=True,
                level=request.level,
                previous_state=previous_state,
                new_state=BreakerState.TRIPPED,
                positions_closed=0,  # Will be updated async
                response_time_ms=response_time,
                correlation_id=correlation_id,
                message="Emergency stop executed successfully"
            )
            
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            logger.exception(
                "Emergency stop failed",
                error=str(e),
                correlation_id=correlation_id,
                response_time_ms=response_time
            )
            
            return EmergencyStopResponse(
                success=False,
                level=request.level,
                previous_state=previous_state or BreakerState.NORMAL,
                new_state=previous_state or BreakerState.NORMAL,
                positions_closed=0,
                response_time_ms=response_time,
                correlation_id=correlation_id,
                message=f"Emergency stop failed: {str(e)}",
                errors=[str(e)]
            )
    
    async def _get_current_breaker_state(self, level: BreakerLevel) -> BreakerState:
        """Get current state of the specified breaker level"""
        if level == BreakerLevel.SYSTEM:
            return self.breaker_manager.system_breaker.state
        elif level == BreakerLevel.AGENT:
            # Return the worst state among agent breakers
            agent_states = [b.state for b in self.breaker_manager.agent_breakers.values()]
            if BreakerState.TRIPPED in agent_states:
                return BreakerState.TRIPPED
            elif BreakerState.WARNING in agent_states:
                return BreakerState.WARNING
            return BreakerState.NORMAL
        elif level == BreakerLevel.ACCOUNT:
            # Return the worst state among account breakers
            account_states = [b.state for b in self.breaker_manager.account_breakers.values()]
            if BreakerState.TRIPPED in account_states:
                return BreakerState.TRIPPED
            elif BreakerState.WARNING in account_states:
                return BreakerState.WARNING
            return BreakerState.NORMAL
        
        return BreakerState.NORMAL
    
    def _get_identifier_for_level(self, level: BreakerLevel) -> str:
        """Get appropriate identifier for the breaker level"""
        if level == BreakerLevel.SYSTEM:
            return "system"
        elif level == BreakerLevel.AGENT:
            return "emergency-agent"
        else:  # ACCOUNT
            return "emergency-account"
    
    async def _close_all_positions(self, correlation_id: str) -> PositionCloseResponse:
        """
        Close all positions across all accounts.
        
        Args:
            correlation_id: Request correlation ID
            
        Returns:
            PositionCloseResponse with closure results
        """
        start_time = time.time()
        
        try:
            request = PositionCloseRequest(
                close_all=True,
                emergency=True,
                timeout_seconds=5,
                correlation_id=correlation_id
            )
            
            response = await self.execution_client.post(
                "/api/v1/positions/close",
                json=request.dict(),
                headers={"X-Correlation-ID": correlation_id}
            )
            
            if response.status_code == 200:
                result = PositionCloseResponse(**response.json())
                response_time = int((time.time() - start_time) * 1000)
                result.response_time_ms = response_time
                
                logger.info(
                    "All positions closed",
                    positions_closed=result.positions_closed,
                    positions_failed=result.positions_failed,
                    response_time_ms=response_time,
                    correlation_id=correlation_id
                )
                
                return result
            else:
                raise Exception(f"Position closure failed with status {response.status_code}: {response.text}")
                
        except httpx.TimeoutException:
            response_time = int((time.time() - start_time) * 1000)
            logger.error(
                "Position closure timed out",
                response_time_ms=response_time,
                correlation_id=correlation_id
            )
            return PositionCloseResponse(
                success=False,
                positions_closed=0,
                positions_failed=0,
                response_time_ms=response_time,
                correlation_id=correlation_id,
                errors=["Position closure timed out"]
            )
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            logger.exception(
                "Position closure failed",
                error=str(e),
                response_time_ms=response_time,
                correlation_id=correlation_id
            )
            return PositionCloseResponse(
                success=False,
                positions_closed=0,
                positions_failed=0,
                response_time_ms=response_time,
                correlation_id=correlation_id,
                errors=[str(e)]
            )
    
    async def _close_account_positions(
        self, 
        account_id: str, 
        correlation_id: str
    ) -> PositionCloseResponse:
        """
        Close all positions for a specific account.
        
        Args:
            account_id: Account to close positions for
            correlation_id: Request correlation ID
            
        Returns:
            PositionCloseResponse with closure results
        """
        start_time = time.time()
        
        try:
            request = PositionCloseRequest(
                account_id=account_id,
                emergency=True,
                timeout_seconds=5,
                correlation_id=correlation_id
            )
            
            response = await self.execution_client.post(
                f"/api/v1/accounts/{account_id}/positions/close",
                json=request.dict(),
                headers={"X-Correlation-ID": correlation_id}
            )
            
            if response.status_code == 200:
                result = PositionCloseResponse(**response.json())
                response_time = int((time.time() - start_time) * 1000)
                result.response_time_ms = response_time
                
                logger.info(
                    "Account positions closed",
                    account_id=account_id,
                    positions_closed=result.positions_closed,
                    positions_failed=result.positions_failed,
                    response_time_ms=response_time,
                    correlation_id=correlation_id
                )
                
                return result
            else:
                raise Exception(f"Account position closure failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            logger.exception(
                "Account position closure failed",
                account_id=account_id,
                error=str(e),
                response_time_ms=response_time,
                correlation_id=correlation_id
            )
            return PositionCloseResponse(
                success=False,
                positions_closed=0,
                positions_failed=0,
                response_time_ms=response_time,
                correlation_id=correlation_id,
                errors=[str(e)]
            )
    
    async def _track_position_closure(
        self, 
        correlation_id: str, 
        positions_task: asyncio.Task
    ) -> None:
        """Track position closure task completion"""
        try:
            result = await positions_task
            
            logger.info(
                "Position closure completed",
                correlation_id=correlation_id,
                success=result.success,
                positions_closed=result.positions_closed,
                positions_failed=result.positions_failed
            )
            
        except Exception as e:
            logger.exception(
                "Position closure task failed",
                correlation_id=correlation_id,
                error=str(e)
            )
        finally:
            # Clean up tracking
            if correlation_id in self._active_stops:
                del self._active_stops[correlation_id]
    
    async def get_active_stops(self) -> List[Dict[str, Any]]:
        """Get list of currently active emergency stops"""
        return [
            {
                "correlation_id": correlation_id,
                "status": "running" if not task.done() else "completed",
                "started_at": datetime.now(timezone.utc).isoformat()  # Approximate
            }
            for correlation_id, task in self._active_stops.items()
        ]
    
    async def verify_position_closure(
        self, 
        correlation_id: str,
        timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """
        Verify that position closure completed successfully.
        
        Args:
            correlation_id: Original request correlation ID
            timeout_seconds: Maximum time to wait for verification
            
        Returns:
            Dictionary with verification results
        """
        start_time = time.time()
        
        try:
            # Check if we're tracking this stop
            if correlation_id not in self._active_stops:
                return {
                    "success": False,
                    "error": "No active stop found for correlation ID",
                    "correlation_id": correlation_id
                }
            
            # Wait for completion with timeout
            try:
                result = await asyncio.wait_for(
                    self._active_stops[correlation_id],
                    timeout=timeout_seconds
                )
                
                verification_time = int((time.time() - start_time) * 1000)
                
                return {
                    "success": result.success,
                    "positions_closed": result.positions_closed,
                    "positions_failed": result.positions_failed,
                    "verification_time_ms": verification_time,
                    "correlation_id": correlation_id,
                    "errors": result.errors
                }
                
            except asyncio.TimeoutError:
                return {
                    "success": False,
                    "error": f"Position closure verification timed out after {timeout_seconds}s",
                    "correlation_id": correlation_id
                }
                
        except Exception as e:
            logger.exception(
                "Position closure verification failed",
                correlation_id=correlation_id,
                error=str(e)
            )
            return {
                "success": False,
                "error": str(e),
                "correlation_id": correlation_id
            }
    
    async def cleanup(self) -> None:
        """Cleanup resources and close connections"""
        try:
            # Cancel active tasks
            for task in self._active_stops.values():
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            if self._active_stops:
                await asyncio.gather(*self._active_stops.values(), return_exceptions=True)
            
            # Close HTTP client
            await self.execution_client.aclose()
            
            logger.info("Emergency stop manager cleaned up")
            
        except Exception as e:
            logger.exception("Error during emergency stop manager cleanup", error=str(e))