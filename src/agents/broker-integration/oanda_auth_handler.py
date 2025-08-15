"""
OANDA Authentication Handler
Story 8.1 - Task 2: Build OANDA authentication handler
"""
import asyncio
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from enum import Enum
import aiohttp
from dataclasses import dataclass

try:
    from .credential_manager import OandaCredentialManager, CredentialValidationError
except ImportError:
    from credential_manager import OandaCredentialManager, CredentialValidationError

logger = logging.getLogger(__name__)

class Environment(Enum):
    PRACTICE = "practice"
    LIVE = "live"

class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass

@dataclass
class AccountContext:
    """Represents an authenticated OANDA account context"""
    user_id: str
    account_id: str
    environment: Environment
    api_key: str
    base_url: str
    authenticated_at: datetime
    last_refresh: datetime
    session_valid: bool = True

class OandaAuthHandler:
    """Handles OANDA API authentication and multi-account management"""
    
    def __init__(self, credential_manager: OandaCredentialManager):
        self.credential_manager = credential_manager
        self.active_sessions: Dict[str, AccountContext] = {}
        self.session_timeout = timedelta(hours=2)  # 2-hour session timeout
        
        # OANDA API endpoints
        self.api_endpoints = {
            Environment.PRACTICE: 'https://api-fxpractice.oanda.com',
            Environment.LIVE: 'https://api-fxtrade.oanda.com'
        }
        
        # OAuth2 endpoints (for future expansion)
        self.oauth_endpoints = {
            Environment.PRACTICE: 'https://api-fxpractice.oanda.com/oauth2',
            Environment.LIVE: 'https://api-fxtrade.oanda.com/oauth2'
        }
    
    async def authenticate_user(self, user_id: str, account_id: str, environment: str) -> AccountContext:
        """
        Authenticate user with OANDA account
        
        Args:
            user_id: User identifier
            account_id: OANDA account ID
            environment: 'practice' or 'live'
            
        Returns:
            AccountContext: Authenticated session context
            
        Raises:
            AuthenticationError: If authentication fails
        """
        logger.info(f"Authenticating user {user_id} for account {account_id} in {environment}")
        
        try:
            env = Environment(environment)
        except ValueError:
            raise AuthenticationError(f"Invalid environment: {environment}")
        
        # Retrieve credentials
        credentials = await self.credential_manager.retrieve_credentials(user_id)
        if not credentials:
            raise AuthenticationError(f"No credentials found for user: {user_id}")
        
        # Validate account matches
        if credentials.get('account_id') != account_id:
            raise AuthenticationError("Account ID mismatch")
        
        if credentials.get('environment') != environment:
            raise AuthenticationError("Environment mismatch")
        
        # Test authentication
        api_key = credentials['api_key']
        base_url = self.api_endpoints[env]
        
        if not await self._test_authentication(api_key, account_id, base_url):
            raise AuthenticationError("Authentication test failed")
        
        # Create session context
        session_key = f"{user_id}:{account_id}"
        context = AccountContext(
            user_id=user_id,
            account_id=account_id,
            environment=env,
            api_key=api_key,
            base_url=base_url,
            authenticated_at=datetime.utcnow(),
            last_refresh=datetime.utcnow()
        )
        
        self.active_sessions[session_key] = context
        logger.info(f"Authentication successful for {session_key}")
        
        return context
    
    async def get_session_context(self, user_id: str, account_id: str) -> Optional[AccountContext]:
        """
        Get existing session context if valid
        
        Args:
            user_id: User identifier
            account_id: Account identifier
            
        Returns:
            AccountContext or None if not found/expired
        """
        session_key = f"{user_id}:{account_id}"
        context = self.active_sessions.get(session_key)
        
        if not context:
            return None
        
        # Check if session is expired
        if datetime.utcnow() - context.last_refresh > self.session_timeout:
            logger.warning(f"Session expired for {session_key}")
            context.session_valid = False
            await self._refresh_session(context)
        
        return context
    
    async def switch_account_context(self, user_id: str, from_account: str, to_account: str) -> AccountContext:
        """
        Switch between user's OANDA accounts
        
        Args:
            user_id: User identifier
            from_account: Current account ID
            to_account: Target account ID
            
        Returns:
            AccountContext: New account context
        """
        logger.info(f"Switching account context for {user_id}: {from_account} -> {to_account}")
        
        # Get credentials to determine environment
        credentials = await self.credential_manager.retrieve_credentials(user_id)
        if not credentials:
            raise AuthenticationError(f"No credentials found for user: {user_id}")
        
        # For now, assume same environment. In multi-account scenarios,
        # we'd need to store multiple credential sets per user
        environment = credentials['environment']
        
        return await self.authenticate_user(user_id, to_account, environment)
    
    async def refresh_all_sessions(self) -> Dict[str, bool]:
        """
        Refresh all active sessions
        
        Returns:
            Dict mapping session keys to refresh success status
        """
        logger.info(f"Refreshing {len(self.active_sessions)} active sessions")
        
        refresh_results = {}
        for session_key, context in self.active_sessions.items():
            try:
                success = await self._refresh_session(context)
                refresh_results[session_key] = success
            except Exception as e:
                logger.error(f"Failed to refresh session {session_key}: {e}")
                refresh_results[session_key] = False
        
        return refresh_results
    
    async def get_user_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all accounts for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            List of account information dicts
        """
        credentials = await self.credential_manager.retrieve_credentials(user_id)
        if not credentials:
            return []
        
        api_key = credentials['api_key']
        environment = Environment(credentials['environment'])
        base_url = self.api_endpoints[environment]
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                }
                
                url = f"{base_url}/v3/accounts"
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        accounts = data.get('accounts', [])
                        
                        # Enrich with connection status
                        for account in accounts:
                            session_key = f"{user_id}:{account['id']}"
                            context = self.active_sessions.get(session_key)
                            account['connected'] = context is not None and context.session_valid
                        
                        return accounts
                    else:
                        logger.error(f"Failed to fetch accounts: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error fetching accounts for user {user_id}: {e}")
            return []
    
    async def logout_user(self, user_id: str, account_id: Optional[str] = None):
        """
        Logout user from specific account or all accounts
        
        Args:
            user_id: User identifier
            account_id: Specific account to logout (optional)
        """
        if account_id:
            session_key = f"{user_id}:{account_id}"
            if session_key in self.active_sessions:
                del self.active_sessions[session_key]
                logger.info(f"Logged out session: {session_key}")
        else:
            # Logout all user sessions
            keys_to_remove = [key for key in self.active_sessions.keys() if key.startswith(f"{user_id}:")]
            for key in keys_to_remove:
                del self.active_sessions[key]
            logger.info(f"Logged out all sessions for user: {user_id}")
    
    async def _test_authentication(self, api_key: str, account_id: str, base_url: str) -> bool:
        """Test API authentication"""
        try:
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"{base_url}/v3/accounts/{account_id}"
                async with session.get(url, headers=headers, timeout=10) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"Authentication test failed: {e}")
            return False
    
    async def _refresh_session(self, context: AccountContext) -> bool:
        """
        Refresh session by testing API connectivity
        
        Args:
            context: Account context to refresh
            
        Returns:
            bool: True if refresh successful
        """
        try:
            if await self._test_authentication(context.api_key, context.account_id, context.base_url):
                context.last_refresh = datetime.utcnow()
                context.session_valid = True
                logger.debug(f"Session refreshed for {context.user_id}:{context.account_id}")
                return True
            else:
                context.session_valid = False
                logger.warning(f"Session refresh failed for {context.user_id}:{context.account_id}")
                return False
                
        except Exception as e:
            context.session_valid = False
            logger.error(f"Session refresh error for {context.user_id}:{context.account_id}: {e}")
            return False
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about active sessions"""
        now = datetime.utcnow()
        valid_sessions = sum(1 for ctx in self.active_sessions.values() if ctx.session_valid)
        expired_sessions = sum(
            1 for ctx in self.active_sessions.values()
            if now - ctx.last_refresh > self.session_timeout
        )
        
        return {
            'total_sessions': len(self.active_sessions),
            'valid_sessions': valid_sessions,
            'expired_sessions': expired_sessions,
            'session_timeout_hours': self.session_timeout.total_seconds() / 3600,
            'environments': {
                'practice': sum(1 for ctx in self.active_sessions.values() if ctx.environment == Environment.PRACTICE),
                'live': sum(1 for ctx in self.active_sessions.values() if ctx.environment == Environment.LIVE)
            }
        }