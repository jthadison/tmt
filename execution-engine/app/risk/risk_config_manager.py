"""
Risk Configuration Management System

Manages risk configurations, templates, and dynamic updates.
Provides validation, versioning, and audit trails for risk settings.
"""

import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
from decimal import Decimal

import structlog
from pydantic import ValidationError

from ..core.models import (
    RiskConfiguration, RiskLimits, RiskLevel, RiskEventType
)

logger = structlog.get_logger(__name__)


class RiskConfigurationManager:
    """
    Manages risk configurations with validation, versioning, and templates.
    
    Features:
    - Configuration templates for different risk profiles
    - Dynamic configuration updates with validation
    - Configuration versioning and audit trails
    - Automated configuration optimization based on performance
    - Multi-environment support (development, staging, production)
    """
    
    def __init__(
        self,
        config_directory: Optional[str] = None,
        environment: str = "production"
    ) -> None:
        self.config_directory = Path(config_directory or "config/risk")
        self.environment = environment
        
        # Active configurations
        self.active_configs: Dict[str, RiskConfiguration] = {}
        
        # Configuration templates
        self.templates: Dict[str, RiskConfiguration] = {}
        
        # Configuration history for audit
        self.config_history: List[Dict] = []
        
        # Configuration validation rules
        self.validation_rules: Dict[str, callable] = {}
        
        # Auto-optimization settings
        self.auto_optimization_enabled = False
        self.optimization_metrics: Dict[str, List[float]] = {}
        
        logger.info("Risk Configuration Manager initialized",
                   config_directory=str(self.config_directory),
                   environment=environment)
    
    async def initialize(self) -> None:
        """Initialize the configuration manager."""
        # Create config directory if it doesn't exist
        self.config_directory.mkdir(parents=True, exist_ok=True)
        
        # Load default templates
        await self._load_default_templates()
        
        # Load existing configurations
        await self._load_existing_configurations()
        
        # Setup validation rules
        self._setup_validation_rules()
        
        logger.info("Risk Configuration Manager initialized successfully")
    
    def create_conservative_template(self) -> RiskConfiguration:
        """Create conservative risk configuration template."""
        limits = RiskLimits(
            max_position_size=Decimal("25000"),
            max_total_positions=3,
            max_leverage=Decimal("5"),
            required_margin_ratio=Decimal("0.05"),
            max_daily_loss=Decimal("250"),
            max_weekly_loss=Decimal("1000"),
            max_monthly_loss=Decimal("3000"),
            max_drawdown=Decimal("2000"),
            max_instrument_exposure=Decimal("50000"),
            max_orders_per_minute=5,
            max_orders_per_hour=50,
            warning_threshold=0.7,
            critical_threshold=0.9,
            kill_switch_enabled=True,
            auto_close_on_limit=True
        )
        
        return RiskConfiguration(
            account_id="template_conservative",
            name="Conservative Risk Template",
            description="Conservative risk settings for cautious trading",
            limits=limits,
            monitoring_enabled=True,
            alert_frequency_minutes=2,
            kill_switch_conditions=[
                {"metric": "daily_pl", "operator": "<=", "value": "-250"},
                {"metric": "max_drawdown", "operator": ">=", "value": "2000"},
                {"metric": "current_leverage", "operator": ">", "value": "5"}
            ],
            notification_channels=["email", "dashboard"],
            escalation_rules=[
                {"threshold": 0.8, "channel": "email", "frequency_minutes": 15},
                {"threshold": 0.95, "channel": "sms", "frequency_minutes": 5}
            ]
        )
    
    def create_moderate_template(self) -> RiskConfiguration:
        """Create moderate risk configuration template."""
        limits = RiskLimits(
            max_position_size=Decimal("50000"),
            max_total_positions=5,
            max_leverage=Decimal("10"),
            required_margin_ratio=Decimal("0.03"),
            max_daily_loss=Decimal("500"),
            max_weekly_loss=Decimal("2000"),
            max_monthly_loss=Decimal("6000"),
            max_drawdown=Decimal("3000"),
            max_instrument_exposure=Decimal("100000"),
            max_orders_per_minute=10,
            max_orders_per_hour=100,
            warning_threshold=0.8,
            critical_threshold=0.95,
            kill_switch_enabled=True,
            auto_close_on_limit=False
        )
        
        return RiskConfiguration(
            account_id="template_moderate",
            name="Moderate Risk Template",
            description="Balanced risk settings for standard trading",
            limits=limits,
            monitoring_enabled=True,
            alert_frequency_minutes=5,
            kill_switch_conditions=[
                {"metric": "daily_pl", "operator": "<=", "value": "-500"},
                {"metric": "max_drawdown", "operator": ">=", "value": "3000"},
                {"metric": "current_leverage", "operator": ">", "value": "10"}
            ],
            notification_channels=["email", "dashboard"],
            escalation_rules=[
                {"threshold": 0.85, "channel": "email", "frequency_minutes": 30},
                {"threshold": 0.98, "channel": "sms", "frequency_minutes": 10}
            ]
        )
    
    def create_aggressive_template(self) -> RiskConfiguration:
        """Create aggressive risk configuration template."""
        limits = RiskLimits(
            max_position_size=Decimal("100000"),
            max_total_positions=10,
            max_leverage=Decimal("20"),
            required_margin_ratio=Decimal("0.02"),
            max_daily_loss=Decimal("1000"),
            max_weekly_loss=Decimal("4000"),
            max_monthly_loss=Decimal("12000"),
            max_drawdown=Decimal("5000"),
            max_instrument_exposure=Decimal("200000"),
            max_orders_per_minute=20,
            max_orders_per_hour=200,
            warning_threshold=0.85,
            critical_threshold=0.97,
            kill_switch_enabled=True,
            auto_close_on_limit=False
        )
        
        return RiskConfiguration(
            account_id="template_aggressive",
            name="Aggressive Risk Template",
            description="Higher risk settings for experienced traders",
            limits=limits,
            monitoring_enabled=True,
            alert_frequency_minutes=10,
            kill_switch_conditions=[
                {"metric": "daily_pl", "operator": "<=", "value": "-1000"},
                {"metric": "max_drawdown", "operator": ">=", "value": "5000"},
                {"metric": "current_leverage", "operator": ">", "value": "20"}
            ],
            notification_channels=["dashboard"],
            escalation_rules=[
                {"threshold": 0.9, "channel": "email", "frequency_minutes": 60},
                {"threshold": 0.99, "channel": "sms", "frequency_minutes": 15}
            ]
        )
    
    async def create_configuration_from_template(
        self,
        account_id: str,
        template_name: str,
        overrides: Optional[Dict] = None
    ) -> RiskConfiguration:
        """Create a new configuration from a template with optional overrides."""
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")
        
        template = self.templates[template_name]
        config_data = template.dict()
        
        # Apply overrides
        if overrides:
            config_data.update(overrides)
        
        # Set account ID
        config_data['account_id'] = account_id
        config_data['name'] = f"{template.name} - {account_id}"
        config_data['created_at'] = datetime.utcnow()
        config_data['version'] = 1
        
        # Validate configuration
        try:
            config = RiskConfiguration(**config_data)
        except ValidationError as e:
            logger.error("Configuration validation failed", 
                        account_id=account_id,
                        template=template_name,
                        errors=str(e))
            raise ValueError(f"Invalid configuration: {e}")
        
        # Additional custom validation
        validation_result = await self._validate_configuration(config)
        if not validation_result['valid']:
            raise ValueError(f"Configuration validation failed: {validation_result['errors']}")
        
        # Store configuration
        self.active_configs[account_id] = config
        
        # Save to disk
        await self._save_configuration(config)
        
        # Log configuration creation
        await self._log_configuration_change(
            account_id=account_id,
            action="created",
            template=template_name,
            overrides=overrides
        )
        
        logger.info("Configuration created from template",
                   account_id=account_id,
                   template=template_name,
                   version=config.version)
        
        return config
    
    async def update_configuration(
        self,
        account_id: str,
        updates: Dict,
        reason: str = "Manual update"
    ) -> RiskConfiguration:
        """Update an existing configuration with validation and versioning."""
        if account_id not in self.active_configs:
            raise ValueError(f"Configuration for account '{account_id}' not found")
        
        current_config = self.active_configs[account_id]
        
        # Create updated configuration
        updated_data = current_config.dict()
        updated_data.update(updates)
        updated_data['updated_at'] = datetime.utcnow()
        updated_data['version'] = current_config.version + 1
        
        try:
            updated_config = RiskConfiguration(**updated_data)
        except ValidationError as e:
            logger.error("Configuration update validation failed",
                        account_id=account_id,
                        errors=str(e))
            raise ValueError(f"Invalid configuration update: {e}")
        
        # Validate updated configuration
        validation_result = await self._validate_configuration(updated_config)
        if not validation_result['valid']:
            raise ValueError(f"Updated configuration validation failed: {validation_result['errors']}")
        
        # Check for significant changes that require approval
        significant_changes = self._check_significant_changes(current_config, updated_config)
        if significant_changes and self.environment == "production":
            logger.warning("Significant configuration changes detected",
                          account_id=account_id,
                          changes=significant_changes)
        
        # Store updated configuration
        self.active_configs[account_id] = updated_config
        
        # Save to disk
        await self._save_configuration(updated_config)
        
        # Log configuration update
        await self._log_configuration_change(
            account_id=account_id,
            action="updated",
            reason=reason,
            changes=updates,
            version_from=current_config.version,
            version_to=updated_config.version
        )
        
        logger.info("Configuration updated",
                   account_id=account_id,
                   version=updated_config.version,
                   reason=reason)
        
        return updated_config
    
    async def optimize_configuration(
        self,
        account_id: str,
        performance_data: Dict
    ) -> Optional[RiskConfiguration]:
        """Automatically optimize configuration based on performance data."""
        if not self.auto_optimization_enabled:
            return None
        
        if account_id not in self.active_configs:
            logger.warning("Cannot optimize: configuration not found", account_id=account_id)
            return None
        
        current_config = self.active_configs[account_id]
        
        # Analyze performance metrics
        optimization_suggestions = self._analyze_performance_for_optimization(
            account_id, performance_data
        )
        
        if not optimization_suggestions:
            logger.debug("No optimization suggestions", account_id=account_id)
            return None
        
        # Apply optimizations
        optimizations = {}
        
        # Adjust position limits based on performance
        if "reduce_position_size" in optimization_suggestions:
            current_max = current_config.limits.max_position_size
            if current_max:
                new_max = current_max * Decimal("0.8")  # Reduce by 20%
                optimizations["limits.max_position_size"] = new_max
        
        if "increase_position_size" in optimization_suggestions:
            current_max = current_config.limits.max_position_size
            if current_max:
                new_max = current_max * Decimal("1.1")  # Increase by 10%
                optimizations["limits.max_position_size"] = new_max
        
        # Adjust leverage based on performance
        if "reduce_leverage" in optimization_suggestions:
            current_leverage = current_config.limits.max_leverage
            if current_leverage:
                new_leverage = max(current_leverage * Decimal("0.9"), Decimal("2"))
                optimizations["limits.max_leverage"] = new_leverage
        
        if optimizations:
            try:
                optimized_config = await self.update_configuration(
                    account_id=account_id,
                    updates=optimizations,
                    reason=f"Auto-optimization: {', '.join(optimization_suggestions)}"
                )
                
                logger.info("Configuration auto-optimized",
                           account_id=account_id,
                           suggestions=optimization_suggestions,
                           optimizations=optimizations)
                
                return optimized_config
            
            except Exception as e:
                logger.error("Configuration optimization failed",
                           account_id=account_id,
                           error=str(e))
                return None
        
        return None
    
    def get_configuration(self, account_id: str) -> Optional[RiskConfiguration]:
        """Get configuration for an account."""
        return self.active_configs.get(account_id)
    
    def list_configurations(self) -> List[RiskConfiguration]:
        """List all active configurations."""
        return list(self.active_configs.values())
    
    def list_templates(self) -> List[str]:
        """List available configuration templates."""
        return list(self.templates.keys())
    
    async def validate_configuration(self, config: RiskConfiguration) -> Dict:
        """Validate a configuration and return validation result."""
        return await self._validate_configuration(config)
    
    def enable_auto_optimization(self) -> None:
        """Enable automatic configuration optimization."""
        self.auto_optimization_enabled = True
        logger.info("Auto-optimization enabled")
    
    def disable_auto_optimization(self) -> None:
        """Disable automatic configuration optimization."""
        self.auto_optimization_enabled = False
        logger.info("Auto-optimization disabled")
    
    # Private methods
    
    async def _load_default_templates(self) -> None:
        """Load default configuration templates."""
        self.templates = {
            "conservative": self.create_conservative_template(),
            "moderate": self.create_moderate_template(),
            "aggressive": self.create_aggressive_template()
        }
        
        logger.debug("Default templates loaded", templates=list(self.templates.keys()))
    
    async def _load_existing_configurations(self) -> None:
        """Load existing configurations from disk."""
        if not self.config_directory.exists():
            return
        
        config_files = list(self.config_directory.glob("*.json"))
        loaded_count = 0
        
        for config_file in config_files:
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                
                config = RiskConfiguration(**config_data)
                self.active_configs[config.account_id] = config
                loaded_count += 1
                
            except Exception as e:
                logger.error("Failed to load configuration file",
                           file=str(config_file),
                           error=str(e))
        
        logger.info("Existing configurations loaded", count=loaded_count)
    
    async def _save_configuration(self, config: RiskConfiguration) -> None:
        """Save configuration to disk."""
        config_file = self.config_directory / f"{config.account_id}.json"
        
        try:
            with open(config_file, 'w') as f:
                json.dump(config.dict(), f, indent=2, default=str)
            
            logger.debug("Configuration saved to disk",
                        account_id=config.account_id,
                        file=str(config_file))
        
        except Exception as e:
            logger.error("Failed to save configuration",
                        account_id=config.account_id,
                        error=str(e))
    
    def _setup_validation_rules(self) -> None:
        """Setup configuration validation rules."""
        self.validation_rules = {
            "leverage_limit": lambda config: config.limits.max_leverage and config.limits.max_leverage <= 50,
            "position_size_reasonable": lambda config: not config.limits.max_position_size or config.limits.max_position_size <= 1000000,
            "loss_limits_consistent": lambda config: (
                not config.limits.max_daily_loss or 
                not config.limits.max_weekly_loss or
                config.limits.max_daily_loss * 7 <= config.limits.max_weekly_loss * 2
            ),
            "warning_threshold_valid": lambda config: 0 < config.limits.warning_threshold < config.limits.critical_threshold < 1,
            "kill_switch_conditions_valid": lambda config: (
                isinstance(config.kill_switch_conditions, list) and
                all(isinstance(condition, dict) for condition in config.kill_switch_conditions)
            )
        }
    
    async def _validate_configuration(self, config: RiskConfiguration) -> Dict:
        """Validate configuration against rules."""
        errors = []
        warnings = []
        
        # Run validation rules
        for rule_name, rule_func in self.validation_rules.items():
            try:
                if not rule_func(config):
                    errors.append(f"Validation rule '{rule_name}' failed")
            except Exception as e:
                warnings.append(f"Validation rule '{rule_name}' error: {str(e)}")
        
        # Additional context-specific validations
        if self.environment == "production":
            # Stricter validations for production
            if config.limits.max_leverage and config.limits.max_leverage > 30:
                warnings.append("High leverage detected for production environment")
            
            if config.limits.auto_close_on_limit:
                warnings.append("Auto-close enabled in production - ensure this is intended")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _check_significant_changes(
        self,
        old_config: RiskConfiguration,
        new_config: RiskConfiguration
    ) -> List[str]:
        """Check for significant configuration changes that may require approval."""
        significant_changes = []
        
        # Check leverage changes
        if (old_config.limits.max_leverage != new_config.limits.max_leverage):
            old_val = old_config.limits.max_leverage or 0
            new_val = new_config.limits.max_leverage or 0
            if abs(new_val - old_val) > old_val * Decimal("0.5"):  # 50% change
                significant_changes.append("major_leverage_change")
        
        # Check position size changes
        if (old_config.limits.max_position_size != new_config.limits.max_position_size):
            old_val = old_config.limits.max_position_size or 0
            new_val = new_config.limits.max_position_size or 0
            if abs(new_val - old_val) > old_val * Decimal("0.5"):  # 50% change
                significant_changes.append("major_position_size_change")
        
        # Check kill switch changes
        if old_config.limits.kill_switch_enabled != new_config.limits.kill_switch_enabled:
            significant_changes.append("kill_switch_toggle")
        
        # Check auto-close changes
        if old_config.limits.auto_close_on_limit != new_config.limits.auto_close_on_limit:
            significant_changes.append("auto_close_toggle")
        
        return significant_changes
    
    def _analyze_performance_for_optimization(
        self,
        account_id: str,
        performance_data: Dict
    ) -> List[str]:
        """Analyze performance data and suggest optimizations."""
        suggestions = []
        
        # Track metrics
        if account_id not in self.optimization_metrics:
            self.optimization_metrics[account_id] = []
        
        # Extract key metrics
        win_rate = performance_data.get('win_rate', 0.5)
        avg_profit = performance_data.get('avg_profit', 0)
        max_drawdown = performance_data.get('max_drawdown', 0)
        volatility = performance_data.get('volatility', 0)
        
        # Store metrics for trend analysis
        self.optimization_metrics[account_id].append({
            'timestamp': datetime.utcnow(),
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'max_drawdown': max_drawdown,
            'volatility': volatility
        })
        
        # Keep only recent metrics (last 30 data points)
        self.optimization_metrics[account_id] = self.optimization_metrics[account_id][-30:]
        
        # Optimization logic
        if win_rate < 0.4:  # Low win rate
            suggestions.append("reduce_position_size")
            if max_drawdown > 0.1:  # High drawdown
                suggestions.append("reduce_leverage")
        
        elif win_rate > 0.6 and avg_profit > 0:  # Good performance
            if max_drawdown < 0.05:  # Low drawdown
                suggestions.append("increase_position_size")
        
        if volatility > 0.3:  # High volatility
            suggestions.append("reduce_leverage")
        
        return suggestions
    
    async def _log_configuration_change(self, **kwargs) -> None:
        """Log configuration changes for audit trail."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'environment': self.environment,
            **kwargs
        }
        
        self.config_history.append(log_entry)
        
        # Keep only recent history (last 1000 entries)
        self.config_history = self.config_history[-1000:]
        
        logger.info("Configuration change logged", **kwargs)