"""
Mock OANDA Auth Handler for testing
Provides stub implementation when actual auth handler is not available
"""
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional
from unittest.mock import MagicMock


class Environment(Enum):
    """OANDA environment types"""
    LIVE = "live"
    PRACTICE = "practice"
    SANDBOX = "sandbox"


@dataclass
class AccountContext:
    """Account authentication context"""
    user_id: str
    account_id: str
    environment: Environment
    api_key: str
    base_url: str
    authenticated_at: datetime
    last_refresh: datetime


class OandaAuthHandler:
    """Mock auth handler for testing"""
    
    def __init__(self):
        self.active_sessions: Dict[str, AccountContext] = {}
        self.session_timeout = 3600  # 1 hour
        
    async def authenticate(self, user_id: str, account_id: str, api_key: str, environment: Environment = Environment.PRACTICE) -> AccountContext:
        """Mock authentication"""
        context = AccountContext(
            user_id=user_id,
            account_id=account_id,
            environment=environment,
            api_key=api_key,
            base_url="https://api-fxpractice.oanda.com" if environment == Environment.PRACTICE else "https://api-fxtrade.oanda.com",
            authenticated_at=datetime.now(timezone.utc),
            last_refresh=datetime.now(timezone.utc)
        )
        
        self.active_sessions[account_id] = context
        return context
        
    async def refresh_session(self, account_id: str) -> bool:
        """Mock session refresh"""
        if account_id in self.active_sessions:
            self.active_sessions[account_id].last_refresh = datetime.now(timezone.utc)
            return True
        return False
        
    def get_context(self, account_id: str) -> Optional[AccountContext]:
        """Get account context"""
        return self.active_sessions.get(account_id)