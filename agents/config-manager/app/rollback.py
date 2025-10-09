"""
Configuration Rollback System

Provides safe rollback capabilities with audit trail preservation.
"""

import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from .config_manager import ConfigurationManager
from .models import TradingConfig

logger = logging.getLogger(__name__)


class RollbackManager:
    """
    Manages configuration rollback operations

    Features:
    - Rollback to previous or specific version
    - Emergency rollback (one-command)
    - Audit trail preservation (no history rewriting)
    - Validation before rollback
    - Notification integration
    """

    def __init__(self, config_manager: ConfigurationManager):
        """
        Initialize rollback manager

        Args:
            config_manager: ConfigurationManager instance
        """
        self.config_manager = config_manager

        logger.info("RollbackManager initialized")

    def rollback(
        self,
        version: Optional[str] = None,
        reason: str = "Manual rollback",
        emergency: bool = False,
        notify: bool = True
    ) -> TradingConfig:
        """
        Rollback configuration to previous or specific version

        Args:
            version: Version to rollback to (if None, rollback to previous)
            reason: Reason for rollback
            emergency: Emergency rollback flag
            notify: Send notifications (default: True)

        Returns:
            Rolled-back configuration

        Raises:
            ValueError: If rollback fails validation
        """
        # Get current version for logging
        current_version = self.config_manager.get_active_version()

        logger.info(
            f"{'EMERGENCY ' if emergency else ''}Rollback initiated: "
            f"current={current_version}, target={version or 'previous'}"
        )

        # Determine target version if not specified
        if version is None:
            version = self._get_previous_version()

        # Validate target version exists and is valid
        try:
            target_config = self.config_manager.load_version(version)
        except FileNotFoundError:
            raise ValueError(f"Target version not found: {version}")

        # Additional validation for emergency rollbacks
        if emergency:
            # For emergency, ensure target is older than current
            if not self._is_older_version(version, current_version):
                logger.warning(
                    f"Emergency rollback to newer version: "
                    f"{version} (current: {current_version})"
                )

        # Perform rollback
        rollback_reason = f"{'EMERGENCY: ' if emergency else ''}{reason}"

        try:
            self.config_manager.rollback_to_version(
                version=version,
                reason=rollback_reason,
                preserve_audit_trail=True  # Always preserve audit trail
            )

            logger.info(f"Rollback successful: {current_version} -> {version}")

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            raise

        # Load rolled-back configuration
        rolled_back_config = self.config_manager.load_current_config()

        # Send notifications if enabled
        if notify:
            self._send_rollback_notification(
                from_version=current_version,
                to_version=version,
                reason=rollback_reason,
                emergency=emergency
            )

        return rolled_back_config

    def emergency_rollback(self, reason: str = "Emergency rollback") -> TradingConfig:
        """
        Emergency one-command rollback to last known good configuration

        Args:
            reason: Reason for emergency rollback

        Returns:
            Rolled-back configuration
        """
        logger.critical(f"EMERGENCY ROLLBACK: {reason}")

        return self.rollback(
            version=None,  # Rollback to previous
            reason=reason,
            emergency=True,
            notify=True
        )

    def validate_rollback_target(self, version: str) -> tuple[bool, list[str]]:
        """
        Validate rollback target version

        Args:
            version: Version to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        try:
            # Check version exists
            config = self.config_manager.load_version(version)

            # Validate configuration
            validation_result = self.config_manager.validator.validate_file(
                self.config_manager.config_dir /
                self.config_manager._get_version_filename(version)
            )

            if not validation_result.valid:
                errors.extend(validation_result.errors)

        except FileNotFoundError:
            errors.append(f"Version not found: {version}")
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")

        return (len(errors) == 0, errors)

    def get_rollback_history(self, limit: int = 10) -> list[dict]:
        """
        Get history of rollback operations

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of rollback history entries
        """
        history = []

        # Get configuration history from Git
        config_history = self.config_manager.get_config_history(limit=limit * 2)

        # Filter for rollback commits
        for entry in config_history:
            if "rollback" in entry.message.lower():
                history.append({
                    "version": entry.version,
                    "timestamp": entry.timestamp,
                    "author": entry.author,
                    "reason": entry.message,
                    "commit_hash": entry.commit_hash
                })

                if len(history) >= limit:
                    break

        return history

    def _get_previous_version(self) -> str:
        """
        Get previous configuration version

        Returns:
            Previous version string

        Raises:
            ValueError: If no previous version found
        """
        history = self.config_manager.get_config_history(limit=5)

        if len(history) < 2:
            raise ValueError("No previous version available for rollback")

        # Filter out activation commits, get actual config changes
        config_changes = [
            h for h in history
            if "session_targeted" in h.file_path and "active" not in h.file_path
        ]

        if len(config_changes) < 2:
            # Fallback: use version list
            versions = self.config_manager.list_versions()
            if len(versions) >= 2:
                return versions[-2]  # Second to last
            else:
                raise ValueError("No previous version found")

        # Return the version before current
        return config_changes[1].version

    def _is_older_version(self, version1: str, version2: Optional[str]) -> bool:
        """
        Check if version1 is older than version2

        Args:
            version1: First version
            version2: Second version

        Returns:
            True if version1 < version2
        """
        if version2 is None:
            return False

        try:
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]

            return v1_parts < v2_parts
        except (ValueError, AttributeError):
            return False

    def _send_rollback_notification(
        self,
        from_version: Optional[str],
        to_version: str,
        reason: str,
        emergency: bool
    ):
        """
        Send rollback notification

        Args:
            from_version: Version being rolled back from
            to_version: Version being rolled back to
            reason: Rollback reason
            emergency: Emergency flag
        """
        # Import here to avoid circular dependency
        try:
            from .slack_notifier import SlackNotifier

            notifier = SlackNotifier()
            notifier.send_rollback_notification(
                from_version=from_version,
                to_version=to_version,
                reason=reason,
                emergency=emergency
            )

        except Exception as e:
            logger.warning(f"Failed to send rollback notification: {e}")


class ConfigFreeze:
    """
    Configuration freeze mechanism

    Prevents configuration changes during critical periods
    """

    def __init__(self, freeze_file: Path):
        """
        Initialize config freeze

        Args:
            freeze_file: Path to freeze marker file
        """
        self.freeze_file = freeze_file

    def is_frozen(self) -> bool:
        """Check if configuration is frozen"""
        return self.freeze_file.exists()

    def freeze(self, reason: str = "Manual freeze"):
        """
        Freeze configuration changes

        Args:
            reason: Reason for freeze
        """
        freeze_data = {
            "frozen_at": datetime.utcnow().isoformat(),
            "reason": reason
        }

        import json
        with open(self.freeze_file, 'w') as f:
            json.dump(freeze_data, f, indent=2)

        logger.warning(f"Configuration FROZEN: {reason}")

    def unfreeze(self):
        """Unfreeze configuration changes"""
        if self.freeze_file.exists():
            self.freeze_file.unlink()
            logger.info("Configuration unfrozen")

    def get_freeze_info(self) -> Optional[dict]:
        """
        Get freeze information

        Returns:
            Freeze info dict or None if not frozen
        """
        if not self.is_frozen():
            return None

        import json
        try:
            with open(self.freeze_file, 'r') as f:
                return json.load(f)
        except Exception:
            return {"frozen_at": "unknown", "reason": "unknown"}
