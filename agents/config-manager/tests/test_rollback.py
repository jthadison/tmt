"""
Tests for Rollback Manager
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config_manager import ConfigurationManager
from app.rollback import RollbackManager, ConfigFreeze
from app.models import TradingConfig


class TestRollbackManager:
    """Test rollback manager"""

    def test_rollback_to_previous(self, temp_config_dir, schema_file, sample_config_data):
        """Test rollback to previous version"""
        manager = ConfigurationManager(temp_config_dir, schema_file)
        rollback_mgr = RollbackManager(manager)

        # Create two versions
        v1_config = TradingConfig(**sample_config_data)
        manager.propose_new_config(v1_config, auto_commit=False)
        manager.activate_version("1.0.0", auto_commit=False)

        # Create v1.1.0
        sample_config_data['version'] = "1.1.0"
        sample_config_data['reason'] = "Updated configuration"
        v2_config = TradingConfig(**sample_config_data)
        manager.propose_new_config(v2_config, auto_commit=False)
        manager.activate_version("1.1.0", auto_commit=False)

        # Rollback to previous (should be 1.0.0)
        rolled_back = rollback_mgr.rollback(
            version="1.0.0",
            reason="Test rollback",
            emergency=False,
            notify=False
        )

        assert rolled_back.version == "1.0.0"

        # Verify active version
        current = manager.load_current_config()
        assert current.version == "1.0.0"

    def test_rollback_to_specific_version(self, temp_config_dir, schema_file, sample_config_data):
        """Test rollback to specific version"""
        manager = ConfigurationManager(temp_config_dir, schema_file)
        rollback_mgr = RollbackManager(manager)

        # Create version 1.0.0
        v1_config = TradingConfig(**sample_config_data)
        manager.propose_new_config(v1_config, auto_commit=False)

        # Create version 1.1.0
        sample_config_data['version'] = "1.1.0"
        sample_config_data['reason'] = "Version 1.1.0"
        v2_config = TradingConfig(**sample_config_data)
        manager.propose_new_config(v2_config, auto_commit=False)
        manager.activate_version("1.1.0", auto_commit=False)

        # Rollback to specific version 1.0.0
        rolled_back = rollback_mgr.rollback(
            version="1.0.0",
            reason="Rollback to 1.0.0",
            notify=False
        )

        assert rolled_back.version == "1.0.0"

    def test_emergency_rollback(self, temp_config_dir, schema_file, sample_config_data):
        """Test emergency rollback"""
        manager = ConfigurationManager(temp_config_dir, schema_file)
        rollback_mgr = RollbackManager(manager)

        # Create two versions
        v1_config = TradingConfig(**sample_config_data)
        manager.propose_new_config(v1_config, auto_commit=False)
        manager.activate_version("1.0.0", auto_commit=False)

        sample_config_data['version'] = "1.1.0"
        sample_config_data['reason'] = "Faulty configuration"
        v2_config = TradingConfig(**sample_config_data)
        manager.propose_new_config(v2_config, auto_commit=False)
        manager.activate_version("1.1.0", auto_commit=False)

        # Emergency rollback
        rolled_back = rollback_mgr.emergency_rollback(reason="Critical issue detected")

        assert rolled_back.version == "1.0.0"

    def test_validate_rollback_target(self, temp_config_dir, schema_file, sample_config_file):
        """Test validating rollback target"""
        manager = ConfigurationManager(temp_config_dir, schema_file)
        rollback_mgr = RollbackManager(manager)

        # Validate existing version
        is_valid, errors = rollback_mgr.validate_rollback_target("1.0.0")

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_nonexistent_rollback_target(self, temp_config_dir, schema_file):
        """Test validating nonexistent rollback target"""
        manager = ConfigurationManager(temp_config_dir, schema_file)
        rollback_mgr = RollbackManager(manager)

        # Validate nonexistent version
        is_valid, errors = rollback_mgr.validate_rollback_target("99.99.99")

        assert is_valid is False
        assert len(errors) > 0


class TestConfigFreeze:
    """Test configuration freeze"""

    def test_freeze_config(self, temp_config_dir):
        """Test freezing configuration"""
        freeze_file = temp_config_dir / ".freeze"
        freeze = ConfigFreeze(freeze_file)

        assert not freeze.is_frozen()

        # Freeze
        freeze.freeze(reason="Testing freeze")

        assert freeze.is_frozen()
        assert freeze_file.exists()

    def test_unfreeze_config(self, temp_config_dir):
        """Test unfreezing configuration"""
        freeze_file = temp_config_dir / ".freeze"
        freeze = ConfigFreeze(freeze_file)

        # Freeze
        freeze.freeze(reason="Testing freeze")
        assert freeze.is_frozen()

        # Unfreeze
        freeze.unfreeze()
        assert not freeze.is_frozen()

    def test_get_freeze_info(self, temp_config_dir):
        """Test getting freeze information"""
        freeze_file = temp_config_dir / ".freeze"
        freeze = ConfigFreeze(freeze_file)

        # Not frozen
        assert freeze.get_freeze_info() is None

        # Freeze
        freeze.freeze(reason="Test reason")

        # Get info
        info = freeze.get_freeze_info()
        assert info is not None
        assert info['reason'] == "Test reason"
        assert 'frozen_at' in info
