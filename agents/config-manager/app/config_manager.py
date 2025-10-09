"""
Configuration Manager

Manages version-controlled configuration with Git-based audit trails.
"""

import os
import logging
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import yaml

try:
    from git import Repo, GitCommandError
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    logging.warning("GitPython not available - Git operations will be disabled")

from .models import TradingConfig, ConfigHistoryEntry, ConfigValidationResult
from .validator import ConfigValidator

logger = logging.getLogger(__name__)


class ConfigurationManager:
    """
    Manages version-controlled trading configurations

    Features:
    - Load/save configurations
    - Git-based version control
    - Symlink management for active config
    - Rollback capabilities
    - Audit trail preservation
    """

    def __init__(
        self,
        config_dir: Path,
        schema_path: Path,
        repo_path: Optional[Path] = None
    ):
        """
        Initialize configuration manager

        Args:
            config_dir: Directory containing configuration files
            schema_path: Path to JSON Schema for validation
            repo_path: Git repository path (default: parent of config_dir)
        """
        self.config_dir = Path(config_dir)
        self.schema_path = Path(schema_path)
        self.repo_path = repo_path or self.config_dir.parent.parent

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Initialize validator
        self.validator = ConfigValidator(self.schema_path)

        # Initialize Git repo if available
        self.repo = None
        if GIT_AVAILABLE:
            try:
                self.repo = Repo(self.repo_path)
                logger.info(f"Git repository initialized at {self.repo_path}")
            except Exception as e:
                logger.warning(f"Failed to initialize Git repo: {e}")

        # Active config symlink name
        self.active_config_name = "active.yaml"

        logger.info(f"ConfigurationManager initialized: {config_dir}")

    def load_current_config(self) -> TradingConfig:
        """
        Load currently active configuration

        Returns:
            TradingConfig: Active configuration

        Raises:
            FileNotFoundError: If active config doesn't exist
            ValueError: If config is invalid
        """
        active_path = self.config_dir / self.active_config_name

        if not active_path.exists():
            raise FileNotFoundError(
                f"Active configuration not found: {active_path}. "
                "Use activate_version() to set active configuration."
            )

        # Resolve symlink to actual file
        resolved_path = active_path.resolve()

        logger.info(f"Loading active configuration: {resolved_path.name}")

        # Load and parse YAML
        with open(resolved_path, 'r') as f:
            config_data = yaml.safe_load(f)

        # Validate and return
        config = TradingConfig(**config_data)
        return config

    def load_version(self, version: str) -> TradingConfig:
        """
        Load specific configuration version

        Args:
            version: Version string (e.g., "1.0.0")

        Returns:
            TradingConfig for specified version

        Raises:
            FileNotFoundError: If version doesn't exist
        """
        version_file = self._get_version_filename(version)
        version_path = self.config_dir / version_file

        if not version_path.exists():
            raise FileNotFoundError(f"Configuration version not found: {version}")

        logger.info(f"Loading configuration version: {version}")

        with open(version_path, 'r') as f:
            config_data = yaml.safe_load(f)

        return TradingConfig(**config_data)

    def propose_new_config(
        self,
        config: TradingConfig,
        commit_message: Optional[str] = None,
        auto_commit: bool = True
    ) -> Path:
        """
        Propose new configuration (save and optionally commit)

        Args:
            config: New configuration to save
            commit_message: Git commit message (optional)
            auto_commit: Whether to auto-commit (default: True)

        Returns:
            Path to saved configuration file

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate configuration
        config_dict = config.model_dump(mode='json')

        # Convert date objects to strings for YAML
        if 'effective_date' in config_dict:
            config_dict['effective_date'] = str(config_dict['effective_date'])

        if config.validation and config.validation.approved_date:
            config_dict['validation']['approved_date'] = str(config.validation.approved_date)

        # Generate filename
        version_file = self._get_version_filename(config.version)
        version_path = self.config_dir / version_file

        if version_path.exists():
            logger.warning(f"Configuration version {config.version} already exists")
            raise ValueError(f"Version {config.version} already exists")

        # Write YAML file
        with open(version_path, 'w') as f:
            yaml.safe_dump(
                config_dict,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True
            )

        logger.info(f"Saved new configuration: {version_file}")

        # Git commit if enabled
        if auto_commit and self.repo:
            if commit_message is None:
                commit_message = self._generate_commit_message(config)

            try:
                # Add file to Git
                self.repo.index.add([str(version_path.relative_to(self.repo_path))])

                # Commit
                self.repo.index.commit(commit_message)

                logger.info(f"Committed configuration: {config.version}")

            except Exception as e:
                logger.error(f"Failed to commit configuration: {e}")
                raise

        return version_path

    def activate_version(
        self,
        version: str,
        reason: Optional[str] = None,
        auto_commit: bool = True
    ) -> Path:
        """
        Activate a configuration version (update symlink)

        Args:
            version: Version to activate
            reason: Reason for activation
            auto_commit: Whether to commit symlink change

        Returns:
            Path to activated configuration

        Raises:
            FileNotFoundError: If version doesn't exist
        """
        # Verify version exists
        version_file = self._get_version_filename(version)
        version_path = self.config_dir / version_file

        if not version_path.exists():
            raise FileNotFoundError(f"Configuration version not found: {version}")

        # Validate configuration before activating
        validation_result = self.validator.validate_file(version_path)
        if not validation_result.valid:
            error_msg = "Configuration validation failed:\n" + "\n".join(
                validation_result.errors
            )
            raise ValueError(error_msg)

        # Update symlink
        active_path = self.config_dir / self.active_config_name

        # Remove existing symlink if exists
        if active_path.exists() or active_path.is_symlink():
            active_path.unlink()

        # Create new symlink
        try:
            # Use relative path for portability
            active_path.symlink_to(version_file)
            logger.info(f"Activated configuration version: {version}")
        except OSError as e:
            # Fallback to copy if symlinks not supported
            logger.warning(f"Symlink failed, using copy: {e}")
            shutil.copy2(version_path, active_path)

        # Commit activation if enabled
        if auto_commit and self.repo:
            commit_message = f"chore: Activate configuration v{version}"
            if reason:
                commit_message += f"\n\n{reason}"

            try:
                # Add symlink change
                self.repo.index.add([str(active_path.relative_to(self.repo_path))])

                # Commit
                self.repo.index.commit(commit_message)

                logger.info(f"Committed activation of v{version}")

            except Exception as e:
                logger.error(f"Failed to commit activation: {e}")

        return version_path

    def rollback_to_version(
        self,
        version: Optional[str] = None,
        reason: str = "Rollback",
        preserve_audit_trail: bool = True
    ) -> Path:
        """
        Rollback to a previous configuration version

        Args:
            version: Version to rollback to (if None, rollback to previous)
            reason: Reason for rollback
            preserve_audit_trail: Create new commit (don't rewrite history)

        Returns:
            Path to rolled-back configuration

        Raises:
            ValueError: If rollback fails
        """
        if version is None:
            # Get previous version from history
            history = self.get_config_history(limit=2)
            if len(history) < 2:
                raise ValueError("No previous version to rollback to")

            # Get the version before current
            previous_version = self._extract_version_from_filename(history[1].file_path)
            version = previous_version

        logger.info(f"Rolling back to version: {version}")

        # Activate the rollback version
        rollback_path = self.activate_version(
            version,
            reason=f"ROLLBACK: {reason}",
            auto_commit=preserve_audit_trail
        )

        # Additional commit message for clarity
        if preserve_audit_trail and self.repo:
            # Already committed by activate_version
            pass

        return rollback_path

    def get_config_history(self, limit: int = 20) -> List[ConfigHistoryEntry]:
        """
        Get configuration change history from Git

        Args:
            limit: Maximum number of history entries to return

        Returns:
            List of ConfigHistoryEntry objects
        """
        if not self.repo:
            logger.warning("Git repository not available, returning empty history")
            return []

        history = []

        try:
            # Get commits affecting config directory
            commits = list(self.repo.iter_commits(
                paths=str(self.config_dir.relative_to(self.repo_path)),
                max_count=limit
            ))

            for commit in commits:
                # Extract version from commit message or files
                version = self._extract_version_from_commit(commit)

                # Get file path from commit
                file_path = None
                for item in commit.stats.files:
                    if 'config/parameters' in item and item.endswith('.yaml'):
                        if 'active.yaml' not in item:
                            file_path = item
                            break

                if file_path:
                    history.append(ConfigHistoryEntry(
                        version=version or "unknown",
                        commit_hash=commit.hexsha[:8],
                        author=str(commit.author),
                        timestamp=datetime.fromtimestamp(commit.committed_date),
                        message=commit.message.strip(),
                        file_path=file_path
                    ))

        except Exception as e:
            logger.error(f"Failed to get config history: {e}")

        return history

    def list_versions(self) -> List[str]:
        """
        List all available configuration versions

        Returns:
            List of version strings (e.g., ["1.0.0", "1.1.0"])
        """
        versions = []

        for file_path in self.config_dir.glob("session_targeted_v*.yaml"):
            if file_path.name != self.active_config_name:
                version = self._extract_version_from_filename(str(file_path))
                if version:
                    versions.append(version)

        # Sort by semantic version
        versions.sort(key=lambda v: [int(x) for x in v.split('.')])

        return versions

    def get_active_version(self) -> Optional[str]:
        """
        Get currently active configuration version

        Returns:
            Version string or None if no active config
        """
        active_path = self.config_dir / self.active_config_name

        if not active_path.exists():
            return None

        # Resolve symlink
        resolved_path = active_path.resolve()

        # Extract version from filename
        version = self._extract_version_from_filename(resolved_path.name)

        return version

    def _get_version_filename(self, version: str) -> str:
        """Generate filename for a version"""
        return f"session_targeted_v{version}.yaml"

    def _extract_version_from_filename(self, filename: str) -> Optional[str]:
        """Extract version from filename (e.g., 'session_targeted_v1.0.0.yaml' -> '1.0.0')"""
        import re
        match = re.search(r'v(\d+\.\d+\.\d+)', filename)
        return match.group(1) if match else None

    def _extract_version_from_commit(self, commit) -> Optional[str]:
        """Extract version from Git commit message"""
        import re
        # Look for version in commit message
        match = re.search(r'v?(\d+\.\d+\.\d+)', commit.message)
        return match.group(1) if match else None

    def _generate_commit_message(self, config: TradingConfig) -> str:
        """Generate Git commit message for configuration"""
        message = f"feat: config v{config.version} - {config.reason}\n\n"
        message += f"Author: {config.author}\n"
        message += f"Effective: {config.effective_date}\n"

        if config.validation:
            message += "\nValidation Metrics:\n"
            if config.validation.backtest_sharpe:
                message += f"- Backtest Sharpe: {config.validation.backtest_sharpe:.2f}\n"
            if config.validation.out_of_sample_sharpe:
                message += f"- Out-of-sample Sharpe: {config.validation.out_of_sample_sharpe:.2f}\n"
            if config.validation.overfitting_score is not None:
                message += f"- Overfitting Score: {config.validation.overfitting_score:.3f}\n"
            if config.validation.approved_by:
                message += f"\nApproved-by: {config.validation.approved_by}\n"

        return message
