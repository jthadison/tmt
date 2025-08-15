"""
Session Management System
Story 8.1 - Task 6: Implement session management
"""
import asyncio
import logging
from typing import Dict, Optional, List, Any, Set
from datetime import datetime, timedelta
import pickle
import json
import os
from dataclasses import dataclass, asdict
from enum import Enum

from .oanda_auth_handler import OandaAuthHandler, AccountContext

logger = logging.getLogger(__name__)

class SessionState(Enum):
    ACTIVE = "active"
    IDLE = "idle" 
    EXPIRED = "expired"
    TERMINATED = "terminated"

@dataclass
class SessionMetrics:
    """Track session performance metrics"""
    created_at: datetime
    last_activity: datetime
    total_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    refresh_count: int = 0
    timeout_events: int = 0
    
    @property
    def average_response_time(self) -> float:
        return self.total_response_time / max(self.total_requests, 1)
    
    @property
    def error_rate(self) -> float:
        return self.failed_requests / max(self.total_requests, 1)
    
    @property
    def session_duration(self) -> timedelta:
        return self.last_activity - self.created_at

@dataclass
class SessionInfo:
    """Complete session information"""
    session_id: str
    user_id: str
    account_id: str
    environment: str
    state: SessionState
    context: AccountContext
    metrics: SessionMetrics
    auto_refresh_enabled: bool = True
    persist_across_restarts: bool = True

class SessionManager:
    """Manages OANDA session lifecycle with persistence and monitoring"""
    
    def __init__(self, 
                 auth_handler: OandaAuthHandler,
                 session_timeout: timedelta = timedelta(hours=2),
                 idle_timeout: timedelta = timedelta(minutes=30),
                 persistence_file: Optional[str] = None):
        
        self.auth_handler = auth_handler
        self.session_timeout = session_timeout
        self.idle_timeout = idle_timeout
        self.persistence_file = persistence_file or "oanda_sessions.pkl"
        
        # Session storage
        self.sessions: Dict[str, SessionInfo] = {}
        self.user_sessions: Dict[str, Set[str]] = {}  # user_id -> session_ids
        
        # Background tasks
        self.monitoring_task: Optional[asyncio.Task] = None
        self.refresh_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.auto_refresh_interval = 60  # seconds
        self.cleanup_interval = 300  # seconds (5 minutes)
        self.max_sessions_per_user = 10
        
        # Metrics
        self.global_metrics = {
            'sessions_created': 0,
            'sessions_terminated': 0,
            'sessions_expired': 0,
            'sessions_restored': 0,
            'refresh_operations': 0,
            'refresh_failures': 0
        }
        
        self.running = False
    
    async def start(self):
        """Start the session manager"""
        if self.running:
            return
            
        logger.info("Starting session manager")
        self.running = True
        
        # Load persisted sessions
        await self._load_persisted_sessions()
        
        # Start background tasks
        self.monitoring_task = asyncio.create_task(self._session_monitoring_loop())
        self.refresh_task = asyncio.create_task(self._auto_refresh_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("Session manager started")
    
    async def stop(self):
        """Stop the session manager"""
        if not self.running:
            return
            
        logger.info("Stopping session manager")
        self.running = False
        
        # Cancel background tasks
        tasks = [self.monitoring_task, self.refresh_task, self.cleanup_task]
        for task in tasks:
            if task:
                task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*[t for t in tasks if t], return_exceptions=True)
        
        # Persist sessions
        await self._persist_sessions()
        
        logger.info("Session manager stopped")
    
    async def create_session(self, user_id: str, account_id: str, environment: str, 
                           persist: bool = True, auto_refresh: bool = True) -> str:
        """
        Create new session
        
        Args:
            user_id: User identifier
            account_id: OANDA account ID
            environment: Environment (practice/live)
            persist: Whether to persist across restarts
            auto_refresh: Whether to auto-refresh session
            
        Returns:
            str: Session ID
        """
        logger.info(f"Creating session for user {user_id}, account {account_id}")
        
        # Check session limits
        user_session_count = len(self.user_sessions.get(user_id, set()))
        if user_session_count >= self.max_sessions_per_user:
            # Terminate oldest session
            await self._terminate_oldest_session(user_id)
        
        # Authenticate and get context
        context = await self.auth_handler.authenticate_user(user_id, account_id, environment)
        
        # Generate session ID
        session_id = f"{user_id}_{account_id}_{int(datetime.utcnow().timestamp())}"
        
        # Create session metrics
        metrics = SessionMetrics(
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )
        
        # Create session info
        session_info = SessionInfo(
            session_id=session_id,
            user_id=user_id,
            account_id=account_id,
            environment=environment,
            state=SessionState.ACTIVE,
            context=context,
            metrics=metrics,
            auto_refresh_enabled=auto_refresh,
            persist_across_restarts=persist
        )
        
        # Store session
        self.sessions[session_id] = session_info
        
        # Update user sessions mapping
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = set()
        self.user_sessions[user_id].add(session_id)
        
        # Update metrics
        self.global_metrics['sessions_created'] += 1
        
        logger.info(f"Session created: {session_id}")
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session by ID"""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        # Update last activity
        session.metrics.last_activity = datetime.utcnow()
        
        # Check if session is still valid
        if await self._is_session_valid(session):
            return session
        else:
            await self._expire_session(session_id)
            return None
    
    async def refresh_session(self, session_id: str) -> bool:
        """
        Manually refresh a session
        
        Args:
            session_id: Session to refresh
            
        Returns:
            bool: True if refresh successful
        """
        session = self.sessions.get(session_id)
        if not session:
            logger.warning(f"Session not found for refresh: {session_id}")
            return False
        
        logger.debug(f"Refreshing session: {session_id}")
        
        try:
            # Refresh authentication context
            new_context = await self.auth_handler.authenticate_user(
                session.user_id, 
                session.account_id, 
                session.environment
            )
            
            # Update session
            session.context = new_context
            session.metrics.last_activity = datetime.utcnow()
            session.metrics.refresh_count += 1
            session.state = SessionState.ACTIVE
            
            self.global_metrics['refresh_operations'] += 1
            
            logger.debug(f"Session refreshed successfully: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to refresh session {session_id}: {e}")
            session.metrics.failed_requests += 1
            self.global_metrics['refresh_failures'] += 1
            return False
    
    async def terminate_session(self, session_id: str) -> bool:
        """
        Terminate a session
        
        Args:
            session_id: Session to terminate
            
        Returns:
            bool: True if terminated
        """
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        logger.info(f"Terminating session: {session_id}")
        
        # Update state
        session.state = SessionState.TERMINATED
        
        # Remove from auth handler
        await self.auth_handler.logout_user(session.user_id, session.account_id)
        
        # Remove from storage
        del self.sessions[session_id]
        
        # Update user sessions mapping
        if session.user_id in self.user_sessions:
            self.user_sessions[session.user_id].discard(session_id)
            if not self.user_sessions[session.user_id]:
                del self.user_sessions[session.user_id]
        
        self.global_metrics['sessions_terminated'] += 1
        
        logger.info(f"Session terminated: {session_id}")
        return True
    
    async def get_user_sessions(self, user_id: str) -> List[SessionInfo]:
        """Get all sessions for a user"""
        session_ids = self.user_sessions.get(user_id, set())
        return [self.sessions[sid] for sid in session_ids if sid in self.sessions]
    
    async def terminate_user_sessions(self, user_id: str) -> int:
        """
        Terminate all sessions for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            int: Number of sessions terminated
        """
        session_ids = list(self.user_sessions.get(user_id, set()))
        terminated = 0
        
        for session_id in session_ids:
            if await self.terminate_session(session_id):
                terminated += 1
        
        return terminated
    
    def record_request(self, session_id: str, response_time: float, success: bool = True):
        """Record a request for session metrics"""
        session = self.sessions.get(session_id)
        if not session:
            return
        
        session.metrics.total_requests += 1
        session.metrics.total_response_time += response_time
        session.metrics.last_activity = datetime.utcnow()
        
        if not success:
            session.metrics.failed_requests += 1
    
    async def _session_monitoring_loop(self):
        """Monitor session states and handle timeouts"""
        while self.running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                current_time = datetime.utcnow()
                expired_sessions = []
                idle_sessions = []
                
                for session_id, session in self.sessions.items():
                    if session.state in [SessionState.TERMINATED, SessionState.EXPIRED]:
                        continue
                    
                    # Check for expired sessions
                    if current_time - session.metrics.created_at > self.session_timeout:
                        expired_sessions.append(session_id)
                        continue
                    
                    # Check for idle sessions
                    if current_time - session.metrics.last_activity > self.idle_timeout:
                        if session.state != SessionState.IDLE:
                            session.state = SessionState.IDLE
                            idle_sessions.append(session_id)
                
                # Handle expired sessions
                for session_id in expired_sessions:
                    await self._expire_session(session_id)
                
                # Log idle sessions
                if idle_sessions:
                    logger.info(f"Detected {len(idle_sessions)} idle sessions")
                
            except Exception as e:
                logger.error(f"Error in session monitoring loop: {e}")
    
    async def _auto_refresh_loop(self):
        """Automatically refresh sessions that need it"""
        while self.running:
            try:
                await asyncio.sleep(self.auto_refresh_interval)
                
                refresh_candidates = [
                    session_id for session_id, session in self.sessions.items()
                    if (session.auto_refresh_enabled and 
                        session.state == SessionState.ACTIVE and
                        self._should_refresh_session(session))
                ]
                
                for session_id in refresh_candidates:
                    await self.refresh_session(session_id)
                
                if refresh_candidates:
                    logger.debug(f"Auto-refreshed {len(refresh_candidates)} sessions")
                
            except Exception as e:
                logger.error(f"Error in auto-refresh loop: {e}")
    
    async def _cleanup_loop(self):
        """Clean up expired and terminated sessions"""
        while self.running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                cleanup_candidates = [
                    session_id for session_id, session in self.sessions.items()
                    if session.state in [SessionState.EXPIRED, SessionState.TERMINATED]
                ]
                
                for session_id in cleanup_candidates:
                    del self.sessions[session_id]
                
                if cleanup_candidates:
                    logger.debug(f"Cleaned up {len(cleanup_candidates)} sessions")
                
                # Persist sessions periodically
                if self.sessions:
                    await self._persist_sessions()
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _expire_session(self, session_id: str):
        """Mark session as expired"""
        session = self.sessions.get(session_id)
        if session:
            session.state = SessionState.EXPIRED
            session.metrics.timeout_events += 1
            self.global_metrics['sessions_expired'] += 1
            logger.info(f"Session expired: {session_id}")
    
    def _should_refresh_session(self, session: SessionInfo) -> bool:
        """Determine if session should be refreshed"""
        # Refresh if last activity was more than half the session timeout ago
        time_since_activity = datetime.utcnow() - session.metrics.last_activity
        return time_since_activity > (self.session_timeout / 2)
    
    async def _is_session_valid(self, session: SessionInfo) -> bool:
        """Check if session is still valid"""
        if session.state in [SessionState.EXPIRED, SessionState.TERMINATED]:
            return False
        
        # Check timeout
        if datetime.utcnow() - session.metrics.created_at > self.session_timeout:
            return False
        
        # Could add additional validation here
        return True
    
    async def _terminate_oldest_session(self, user_id: str):
        """Terminate the oldest session for a user"""
        user_session_ids = self.user_sessions.get(user_id, set())
        if not user_session_ids:
            return
        
        # Find oldest session
        oldest_session_id = None
        oldest_time = datetime.utcnow()
        
        for session_id in user_session_ids:
            session = self.sessions.get(session_id)
            if session and session.metrics.created_at < oldest_time:
                oldest_time = session.metrics.created_at
                oldest_session_id = session_id
        
        if oldest_session_id:
            await self.terminate_session(oldest_session_id)
            logger.info(f"Terminated oldest session for user {user_id}: {oldest_session_id}")
    
    async def _persist_sessions(self):
        """Persist sessions to disk"""
        if not self.persistence_file:
            return
        
        try:
            # Only persist sessions marked for persistence
            persistable_sessions = {
                sid: session for sid, session in self.sessions.items()
                if session.persist_across_restarts and session.state == SessionState.ACTIVE
            }
            
            # Convert to serializable format
            session_data = {}
            for sid, session in persistable_sessions.items():
                session_data[sid] = {
                    'session_id': session.session_id,
                    'user_id': session.user_id,
                    'account_id': session.account_id,
                    'environment': session.environment,
                    'created_at': session.metrics.created_at.isoformat(),
                    'auto_refresh_enabled': session.auto_refresh_enabled
                }
            
            with open(self.persistence_file, 'wb') as f:
                pickle.dump(session_data, f)
            
            logger.debug(f"Persisted {len(session_data)} sessions")
            
        except Exception as e:
            logger.error(f"Failed to persist sessions: {e}")
    
    async def _load_persisted_sessions(self):
        """Load persisted sessions from disk"""
        if not self.persistence_file or not os.path.exists(self.persistence_file):
            return
        
        try:
            with open(self.persistence_file, 'rb') as f:
                session_data = pickle.load(f)
            
            restored_count = 0
            for sid, data in session_data.items():
                try:
                    # Recreate session
                    new_session_id = await self.create_session(
                        user_id=data['user_id'],
                        account_id=data['account_id'],
                        environment=data['environment'],
                        auto_refresh=data['auto_refresh_enabled']
                    )
                    restored_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to restore session {sid}: {e}")
            
            self.global_metrics['sessions_restored'] = restored_count
            logger.info(f"Restored {restored_count} persisted sessions")
            
            # Clean up persistence file
            os.remove(self.persistence_file)
            
        except Exception as e:
            logger.error(f"Failed to load persisted sessions: {e}")
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get comprehensive session statistics"""
        active_sessions = sum(1 for s in self.sessions.values() if s.state == SessionState.ACTIVE)
        idle_sessions = sum(1 for s in self.sessions.values() if s.state == SessionState.IDLE)
        expired_sessions = sum(1 for s in self.sessions.values() if s.state == SessionState.EXPIRED)
        
        # Calculate average session duration
        active_durations = [
            (datetime.utcnow() - s.metrics.created_at).total_seconds()
            for s in self.sessions.values() if s.state == SessionState.ACTIVE
        ]
        avg_duration = sum(active_durations) / max(len(active_durations), 1)
        
        return {
            'total_sessions': len(self.sessions),
            'session_states': {
                'active': active_sessions,
                'idle': idle_sessions,
                'expired': expired_sessions,
                'terminated': 0  # These are cleaned up
            },
            'average_session_duration_seconds': avg_duration,
            'users_with_sessions': len(self.user_sessions),
            'global_metrics': self.global_metrics.copy(),
            'configuration': {
                'session_timeout_hours': self.session_timeout.total_seconds() / 3600,
                'idle_timeout_minutes': self.idle_timeout.total_seconds() / 60,
                'max_sessions_per_user': self.max_sessions_per_user
            },
            'timestamp': datetime.utcnow().isoformat()
        }