"""
Data models for multi-account configuration management.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator, root_validator


class AccountStatus(str, Enum):
    """Account status enumeration."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    IN_DRAWDOWN = "in_drawdown"
    TERMINATED = "terminated"


class BrokerType(str, Enum):
    """Supported broker types."""
    METATRADER4 = "MetaTrader4"
    METATRADER5 = "MetaTrader5"
    TRADELOCKER = "TradeLocker"
    DXTRADE = "DXtrade"


class PropFirm(str, Enum):
    """Supported prop firms."""
    FTMO = "FTMO"
    FUNDEDNEXT = "FundedNext"
    MYFOREXFUNDS = "MyForexFunds"
    DNA_FUNDED = "DNA_Funded"
    FUNDING_PIPS = "Funding_Pips"
    THE_FUNDED_TRADER = "The_Funded_Trader"


class TradingTimeframe(str, Enum):
    """Allowed trading timeframes."""
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"


class BrokerCredentials(BaseModel):
    """Broker connection credentials (to be encrypted)."""
    broker: BrokerType
    server: str = Field(..., description="Broker server address")
    login: str = Field(..., description="Account login/number")
    password: str = Field(..., description="Trading password")
    investor_password: Optional[str] = Field(None, description="Read-only password")
    
    @validator('server')
    def validate_server(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Server address is required")
        return v.strip()
    
    @validator('login')
    def validate_login(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Login is required")
        return v.strip()


class TradingParameters(BaseModel):
    """Trading parameters and restrictions."""
    allowed_pairs: List[str] = Field(
        default_factory=lambda: ["EURUSD", "GBPUSD", "USDJPY"],
        description="Allowed trading pairs"
    )
    max_positions: int = Field(default=3, ge=1, le=50, description="Maximum concurrent positions")
    max_lot_size: Decimal = Field(default=Decimal("1.0"), gt=0, description="Maximum lot size per trade")
    allowed_timeframes: List[TradingTimeframe] = Field(
        default_factory=lambda: [TradingTimeframe.M5, TradingTimeframe.M15, TradingTimeframe.H1],
        description="Allowed trading timeframes"
    )
    trading_hours: str = Field(default="00:00-23:59", description="Allowed trading hours (UTC)")
    weekend_trading: bool = Field(default=False, description="Allow weekend trading")
    news_trading_allowed: bool = Field(default=True, description="Allow trading during news events")
    
    @validator('allowed_pairs')
    def validate_pairs(cls, v):
        if not v:
            raise ValueError("At least one trading pair must be allowed")
        return [pair.upper() for pair in v]
    
    @validator('trading_hours')
    def validate_trading_hours(cls, v):
        try:
            start, end = v.split('-')
            start_h, start_m = map(int, start.split(':'))
            end_h, end_m = map(int, end.split(':'))
            
            if not (0 <= start_h <= 23 and 0 <= start_m <= 59):
                raise ValueError("Invalid start time")
            if not (0 <= end_h <= 23 and 0 <= end_m <= 59):
                raise ValueError("Invalid end time")
                
            return v
        except (ValueError, AttributeError):
            raise ValueError("Trading hours must be in format HH:MM-HH:MM")


class RiskLimits(BaseModel):
    """Risk management limits."""
    max_daily_loss_percent: Decimal = Field(default=Decimal("5.0"), gt=0, le=100, description="Max daily loss %")
    max_total_loss_percent: Decimal = Field(default=Decimal("10.0"), gt=0, le=100, description="Max total loss %")
    max_position_size_percent: Decimal = Field(default=Decimal("2.0"), gt=0, le=100, description="Max position size %")
    max_correlation: Decimal = Field(default=Decimal("0.7"), ge=0, le=1, description="Max position correlation")
    require_stop_loss: bool = Field(default=True, description="Require stop loss on all trades")
    max_leverage: Optional[Dict[str, int]] = Field(
        default_factory=lambda: {"forex": 30, "indices": 20, "commodities": 10},
        description="Maximum leverage by instrument type"
    )
    
    @validator('max_daily_loss_percent', 'max_total_loss_percent', 'max_position_size_percent')
    def validate_percentages(cls, v):
        if v <= 0 or v > 100:
            raise ValueError("Percentage must be between 0 and 100")
        return v


class NotificationSettings(BaseModel):
    """Account notification settings."""
    email: Optional[str] = Field(None, description="Notification email (encrypted)")
    webhook_url: Optional[str] = Field(None, description="Webhook URL (encrypted)")
    alert_on_violation: bool = Field(default=True, description="Alert on rule violations")
    alert_on_status_change: bool = Field(default=True, description="Alert on status changes")
    daily_summary: bool = Field(default=True, description="Send daily summary")
    
    @validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError("Invalid email format")
        return v


class AccountConfiguration(BaseModel):
    """Complete account configuration."""
    account_id: UUID = Field(default_factory=uuid4, description="Unique account identifier")
    prop_firm: PropFirm = Field(..., description="Associated prop firm")
    account_number: str = Field(..., description="Broker account number")
    legal_entity_id: Optional[UUID] = Field(None, description="Associated legal entity")
    personality_profile_id: Optional[UUID] = Field(None, description="Trading personality profile")
    
    # Status and balances
    status: AccountStatus = Field(default=AccountStatus.ACTIVE, description="Current account status")
    balance: Decimal = Field(default=Decimal("0.0"), description="Current account balance")
    equity: Decimal = Field(default=Decimal("0.0"), description="Current account equity")
    initial_balance: Decimal = Field(default=Decimal("0.0"), description="Initial account balance")
    
    # Configuration components
    broker_credentials: BrokerCredentials = Field(..., description="Broker connection details")
    trading_parameters: TradingParameters = Field(default_factory=TradingParameters, description="Trading parameters")
    risk_limits: RiskLimits = Field(default_factory=RiskLimits, description="Risk management limits")
    notification_settings: NotificationSettings = Field(default_factory=NotificationSettings, description="Notification settings")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    created_by: Optional[str] = Field(None, description="Creator user ID")
    last_activity: Optional[datetime] = Field(None, description="Last trading activity")
    
    # Encrypted credential reference (Vault path)
    encrypted_credentials_path: Optional[str] = Field(None, description="Vault path to encrypted credentials")
    
    @validator('account_number')
    def validate_account_number(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Account number is required")
        return v.strip()
    
    @root_validator
    def validate_balances(cls, values):
        balance = values.get('balance', Decimal('0'))
        equity = values.get('equity', Decimal('0'))
        initial_balance = values.get('initial_balance', Decimal('0'))
        
        if balance < 0:
            raise ValueError("Balance cannot be negative")
        if equity < 0:
            raise ValueError("Equity cannot be negative")
        if initial_balance <= 0:
            values['initial_balance'] = balance  # Default to current balance
            
        return values


class AccountStatusTransition(BaseModel):
    """Account status change record."""
    transition_id: UUID = Field(default_factory=uuid4, description="Unique transition identifier")
    account_id: UUID = Field(..., description="Account being transitioned")
    from_status: AccountStatus = Field(..., description="Previous status")
    to_status: AccountStatus = Field(..., description="New status")
    reason: str = Field(..., description="Reason for status change")
    triggered_by: str = Field(..., description="User or system that triggered change")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Transition timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional transition data")


class AccountCreateRequest(BaseModel):
    """Request model for creating a new account."""
    prop_firm: PropFirm
    account_number: str
    initial_balance: Decimal
    broker_credentials: BrokerCredentials
    trading_parameters: Optional[TradingParameters] = None
    risk_limits: Optional[RiskLimits] = None
    notification_settings: Optional[NotificationSettings] = None
    legal_entity_id: Optional[UUID] = None
    personality_profile_id: Optional[UUID] = None
    totp_code: str = Field(..., description="2FA TOTP code for verification")


class AccountUpdateRequest(BaseModel):
    """Request model for updating an account."""
    prop_firm: Optional[PropFirm] = None
    broker_credentials: Optional[BrokerCredentials] = None
    trading_parameters: Optional[TradingParameters] = None
    risk_limits: Optional[RiskLimits] = None
    notification_settings: Optional[NotificationSettings] = None
    legal_entity_id: Optional[UUID] = None
    personality_profile_id: Optional[UUID] = None
    totp_code: str = Field(..., description="2FA TOTP code for verification")


class AccountStatusChangeRequest(BaseModel):
    """Request model for changing account status."""
    new_status: AccountStatus
    reason: str
    totp_code: str = Field(..., description="2FA TOTP code for verification")


class AccountListResponse(BaseModel):
    """Response model for listing accounts."""
    accounts: List[AccountConfiguration]
    total_count: int
    page: int = 1
    page_size: int = 50
    has_more: bool = False


class AccountExportData(BaseModel):
    """Account data for export/backup."""
    version: str = "1.0"
    export_date: datetime = Field(default_factory=datetime.utcnow)
    accounts: List[AccountConfiguration]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('accounts')
    def validate_accounts_not_empty(cls, v):
        if not v:
            raise ValueError("At least one account must be included in export")
        return v


class AccountImportRequest(BaseModel):
    """Request model for importing account configurations."""
    export_data: AccountExportData
    overwrite_existing: bool = Field(default=False, description="Overwrite existing accounts")
    validate_only: bool = Field(default=False, description="Validate without importing")
    totp_code: str = Field(..., description="2FA TOTP code for verification")


class TwoFactorAuthSetup(BaseModel):
    """2FA setup information."""
    secret_key: str = Field(..., description="TOTP secret key")
    qr_code_url: str = Field(..., description="QR code URL for authenticator apps")
    backup_codes: List[str] = Field(..., description="Single-use backup codes")


class TwoFactorAuthVerification(BaseModel):
    """2FA verification request."""
    totp_code: str = Field(..., description="6-digit TOTP code")
    backup_code: Optional[str] = Field(None, description="Backup code (alternative to TOTP)")


class VaultCredentialReference(BaseModel):
    """Reference to encrypted credentials in HashiCorp Vault."""
    vault_path: str = Field(..., description="Path to credentials in Vault")
    version: int = Field(default=1, description="Credential version")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    last_accessed: Optional[datetime] = Field(None, description="Last access timestamp")


class CredentialRotationRequest(BaseModel):
    """Request for credential rotation."""
    account_id: UUID
    new_credentials: BrokerCredentials
    totp_code: str = Field(..., description="2FA TOTP code for verification")
    reason: str = Field(default="Scheduled rotation", description="Reason for rotation")


class AccountHealthStatus(BaseModel):
    """Account health and status information."""
    account_id: UUID
    status: AccountStatus
    is_healthy: bool = Field(..., description="Overall health status")
    last_heartbeat: Optional[datetime] = Field(None, description="Last successful connection")
    connection_status: str = Field(default="unknown", description="Broker connection status")
    balance_last_updated: Optional[datetime] = Field(None, description="Last balance update")
    violations_count: int = Field(default=0, description="Number of recent violations")
    warnings_count: int = Field(default=0, description="Number of recent warnings")
    days_since_activity: Optional[int] = Field(None, description="Days since last trading activity")
    health_score: int = Field(default=100, ge=0, le=100, description="Health score (0-100)")


class AccountSummaryStats(BaseModel):
    """Summary statistics for account dashboard."""
    total_accounts: int = 0
    active_accounts: int = 0
    suspended_accounts: int = 0
    in_drawdown_accounts: int = 0
    terminated_accounts: int = 0
    total_balance: Decimal = Decimal('0.0')
    total_equity: Decimal = Decimal('0.0')
    total_pnl: Decimal = Decimal('0.0')
    avg_health_score: float = 0.0
    accounts_with_violations: int = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)