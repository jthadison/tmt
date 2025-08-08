"""
Two-Factor Authentication (2FA) service using TOTP.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from uuid import UUID

import pyotp
import qrcode
from qrcode.image.styledpil import StyledPilImage
import io
import base64

from .models import TwoFactorAuthSetup, TwoFactorAuthVerification

logger = logging.getLogger(__name__)


class TwoFactorAuthService:
    """
    Service for managing TOTP-based Two-Factor Authentication.
    
    Provides setup, verification, and management of 2FA for secure
    account configuration changes.
    """
    
    def __init__(self, issuer_name: str = "TMT Trading System"):
        """
        Initialize 2FA service.
        
        Args:
            issuer_name: Name displayed in authenticator apps
        """
        self.issuer_name = issuer_name
        self.totp_window = 1  # Allow 1 time step before/after current time
        self.backup_codes = {}  # user_id -> {code: used_at}
        self.rate_limits = {}  # user_id -> {attempts: count, reset_time: datetime}
        self.max_attempts = 5
        self.rate_limit_window = timedelta(minutes=15)
    
    def setup_2fa(self, user_id: str, account_name: str) -> TwoFactorAuthSetup:
        """
        Set up 2FA for a user.
        
        Args:
            user_id: User identifier
            account_name: Account name for display
            
        Returns:
            2FA setup information including secret and QR code
        """
        try:
            # Generate secret key
            secret_key = pyotp.random_base32()
            
            # Create TOTP instance
            totp = pyotp.TOTP(secret_key)
            
            # Generate provisioning URI for QR code
            provisioning_uri = totp.provisioning_uri(
                name=account_name,
                issuer_name=self.issuer_name
            )
            
            # Generate QR code
            qr_code_url = self._generate_qr_code(provisioning_uri)
            
            # Generate backup codes
            backup_codes = self._generate_backup_codes(user_id)
            
            logger.info(f"2FA setup completed for user {user_id}")
            
            return TwoFactorAuthSetup(
                secret_key=secret_key,
                qr_code_url=qr_code_url,
                backup_codes=backup_codes
            )
            
        except Exception as e:
            logger.error(f"Failed to setup 2FA for user {user_id}: {e}")
            raise ValueError(f"2FA setup failed: {str(e)}")
    
    def verify_totp(self, secret_key: str, totp_code: str, user_id: str) -> bool:
        """
        Verify TOTP code.
        
        Args:
            secret_key: User's secret key
            totp_code: 6-digit TOTP code
            user_id: User identifier for rate limiting
            
        Returns:
            True if code is valid, False otherwise
        """
        try:
            # Check rate limiting
            if self._is_rate_limited(user_id):
                logger.warning(f"2FA verification rate limited for user {user_id}")
                return False
            
            # Validate TOTP code format
            if not totp_code.isdigit() or len(totp_code) != 6:
                self._increment_failed_attempts(user_id)
                return False
            
            # Create TOTP instance
            totp = pyotp.TOTP(secret_key)
            
            # Verify code with time window
            is_valid = totp.verify(totp_code, valid_window=self.totp_window)
            
            if is_valid:
                self._reset_failed_attempts(user_id)
                logger.info(f"TOTP verification successful for user {user_id}")
            else:
                self._increment_failed_attempts(user_id)
                logger.warning(f"TOTP verification failed for user {user_id}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"TOTP verification error for user {user_id}: {e}")
            self._increment_failed_attempts(user_id)
            return False
    
    def verify_backup_code(self, user_id: str, backup_code: str) -> bool:
        """
        Verify backup code.
        
        Args:
            user_id: User identifier
            backup_code: Backup code to verify
            
        Returns:
            True if code is valid and unused, False otherwise
        """
        try:
            # Check rate limiting
            if self._is_rate_limited(user_id):
                logger.warning(f"Backup code verification rate limited for user {user_id}")
                return False
            
            # Get user's backup codes
            user_codes = self.backup_codes.get(user_id, {})
            
            # Check if code exists and is unused
            if backup_code in user_codes:
                if user_codes[backup_code] is None:  # Unused
                    # Mark as used
                    user_codes[backup_code] = datetime.utcnow()
                    self._reset_failed_attempts(user_id)
                    
                    logger.info(f"Backup code verification successful for user {user_id}")
                    return True
                else:
                    logger.warning(f"Backup code already used for user {user_id}")
            else:
                logger.warning(f"Invalid backup code for user {user_id}")
            
            self._increment_failed_attempts(user_id)
            return False
            
        except Exception as e:
            logger.error(f"Backup code verification error for user {user_id}: {e}")
            self._increment_failed_attempts(user_id)
            return False
    
    def verify_2fa(self, verification: TwoFactorAuthVerification, secret_key: str, user_id: str) -> bool:
        """
        Verify 2FA using TOTP code or backup code.
        
        Args:
            verification: 2FA verification request
            secret_key: User's secret key
            user_id: User identifier
            
        Returns:
            True if verification successful, False otherwise
        """
        try:
            # Try TOTP code first
            if verification.totp_code:
                return self.verify_totp(secret_key, verification.totp_code, user_id)
            
            # Try backup code
            if verification.backup_code:
                return self.verify_backup_code(user_id, verification.backup_code)
            
            logger.warning(f"No 2FA method provided for user {user_id}")
            return False
            
        except Exception as e:
            logger.error(f"2FA verification error for user {user_id}: {e}")
            return False
    
    def generate_new_backup_codes(self, user_id: str) -> List[str]:
        """
        Generate new backup codes, invalidating old ones.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of new backup codes
        """
        try:
            backup_codes = self._generate_backup_codes(user_id, replace_existing=True)
            
            logger.info(f"New backup codes generated for user {user_id}")
            return backup_codes
            
        except Exception as e:
            logger.error(f"Failed to generate backup codes for user {user_id}: {e}")
            raise ValueError(f"Backup code generation failed: {str(e)}")
    
    def get_remaining_backup_codes(self, user_id: str) -> int:
        """
        Get count of remaining unused backup codes.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of unused backup codes
        """
        user_codes = self.backup_codes.get(user_id, {})
        return sum(1 for used_at in user_codes.values() if used_at is None)
    
    def is_2fa_setup(self, user_id: str) -> bool:
        """
        Check if user has 2FA set up.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if 2FA is configured
        """
        # In a real implementation, this would check a database
        # For now, we'll check if backup codes exist
        return user_id in self.backup_codes
    
    def disable_2fa(self, user_id: str) -> None:
        """
        Disable 2FA for user.
        
        Args:
            user_id: User identifier
        """
        try:
            # Remove backup codes
            if user_id in self.backup_codes:
                del self.backup_codes[user_id]
            
            # Reset rate limits
            if user_id in self.rate_limits:
                del self.rate_limits[user_id]
            
            logger.info(f"2FA disabled for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to disable 2FA for user {user_id}: {e}")
            raise ValueError(f"2FA disable failed: {str(e)}")
    
    def _generate_qr_code(self, provisioning_uri: str) -> str:
        """
        Generate QR code as base64 encoded image.
        
        Args:
            provisioning_uri: TOTP provisioning URI
            
        Returns:
            Base64 encoded QR code image
        """
        try:
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            logger.error(f"QR code generation failed: {e}")
            raise ValueError(f"QR code generation failed: {str(e)}")
    
    def _generate_backup_codes(self, user_id: str, replace_existing: bool = False) -> List[str]:
        """
        Generate backup codes for user.
        
        Args:
            user_id: User identifier
            replace_existing: Whether to replace existing codes
            
        Returns:
            List of backup codes
        """
        try:
            # Generate 10 backup codes
            codes = []
            for _ in range(10):
                # Generate 8-character alphanumeric code
                code = ''.join(secrets.choice('ABCDEFGHIJKLMNPQRSTUVWXYZ23456789') for _ in range(8))
                codes.append(code)
            
            # Store codes as unused (None = unused)
            if replace_existing or user_id not in self.backup_codes:
                self.backup_codes[user_id] = {}
            
            for code in codes:
                self.backup_codes[user_id][code] = None
            
            return codes
            
        except Exception as e:
            logger.error(f"Backup code generation failed for user {user_id}: {e}")
            raise ValueError(f"Backup code generation failed: {str(e)}")
    
    def _is_rate_limited(self, user_id: str) -> bool:
        """
        Check if user is rate limited.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if user is rate limited
        """
        if user_id not in self.rate_limits:
            return False
        
        rate_limit = self.rate_limits[user_id]
        
        # Check if rate limit window has expired
        if datetime.utcnow() > rate_limit['reset_time']:
            del self.rate_limits[user_id]
            return False
        
        # Check if max attempts exceeded
        return rate_limit['attempts'] >= self.max_attempts
    
    def _increment_failed_attempts(self, user_id: str) -> None:
        """
        Increment failed attempt count for user.
        
        Args:
            user_id: User identifier
        """
        if user_id not in self.rate_limits:
            self.rate_limits[user_id] = {
                'attempts': 0,
                'reset_time': datetime.utcnow() + self.rate_limit_window
            }
        
        self.rate_limits[user_id]['attempts'] += 1
        
        if self.rate_limits[user_id]['attempts'] >= self.max_attempts:
            logger.warning(f"User {user_id} has exceeded 2FA attempt limit")
    
    def _reset_failed_attempts(self, user_id: str) -> None:
        """
        Reset failed attempt count for user.
        
        Args:
            user_id: User identifier
        """
        if user_id in self.rate_limits:
            del self.rate_limits[user_id]
    
    def get_2fa_status(self, user_id: str) -> dict:
        """
        Get 2FA status for user.
        
        Args:
            user_id: User identifier
            
        Returns:
            2FA status information
        """
        try:
            is_setup = self.is_2fa_setup(user_id)
            remaining_codes = self.get_remaining_backup_codes(user_id) if is_setup else 0
            is_rate_limited = self._is_rate_limited(user_id)
            
            rate_limit_info = None
            if is_rate_limited and user_id in self.rate_limits:
                rate_limit = self.rate_limits[user_id]
                rate_limit_info = {
                    'attempts': rate_limit['attempts'],
                    'max_attempts': self.max_attempts,
                    'reset_time': rate_limit['reset_time'].isoformat()
                }
            
            return {
                'is_setup': is_setup,
                'remaining_backup_codes': remaining_codes,
                'is_rate_limited': is_rate_limited,
                'rate_limit_info': rate_limit_info
            }
            
        except Exception as e:
            logger.error(f"Failed to get 2FA status for user {user_id}: {e}")
            return {
                'is_setup': False,
                'remaining_backup_codes': 0,
                'is_rate_limited': False,
                'error': str(e)
            }


class TwoFactorAuthManager:
    """Singleton manager for 2FA service."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> TwoFactorAuthService:
        """Get singleton 2FA service instance."""
        if cls._instance is None:
            cls._instance = TwoFactorAuthService()
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing)."""
        cls._instance = None