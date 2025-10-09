"""
Tests for ConfigurationManager
"""

import pytest
import yaml
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config_manager import ConfigurationManager
from app.models import TradingConfig


class TestConfigurationManager:
    """Test configuration manager"""

    def test_load_current_config(self, temp_config_dir, schema_file, sample_config_file):
        """Test loading current configuration"""
        manager = ConfigurationManager(temp_config_dir, schema_file)

        # Create active symlink
        active_path = temp_config_dir / "active.yaml"
        try:
            active_path.symlink_to(sample_config_file.name)
        except OSError:
            # Fallback to copy on Windows without admin
            import shutil
            shutil.copy2(sample_config_file, active_path)

        # Load config
        config = manager.load_current_config()

        assert config.version == "1.0.0"
        assert config.author == "Test Author"

    def test_load_version(self, temp_config_dir, schema_file, sample_config_file):
        """Test loading specific version"""
        manager = ConfigurationManager(temp_config_dir, schema_file)

        config = manager.load_version("1.0.0")

        assert config.version == "1.0.0"
        assert config.baseline.confidence_threshold == 55.0

    def test_load_nonexistent_version(self, temp_config_dir, schema_file):
        """Test loading nonexistent version raises error"""
        manager = ConfigurationManager(temp_config_dir, schema_file)

        with pytest.raises(FileNotFoundError):
            manager.load_version("99.99.99")

    def test_propose_new_config(self, temp_config_dir, schema_file, sample_config_data):
        """Test proposing new configuration"""
        manager = ConfigurationManager(temp_config_dir, schema_file)

        # Create new version
        sample_config_data['version'] = "1.1.0"
        sample_config_data['reason'] = "Test version 1.1.0 for unit tests"
        config = TradingConfig(**sample_config_data)

        # Propose (without Git commit)
        config_path = manager.propose_new_config(config, auto_commit=False)

        assert config_path.exists()
        assert config_path.name == "session_targeted_v1.1.0.yaml"

        # Verify content
        loaded_config = manager.load_version("1.1.0")
        assert loaded_config.version == "1.1.0"

    def test_propose_duplicate_version(self, temp_config_dir, schema_file, sample_config_file, sample_config_data):
        """Test proposing duplicate version raises error"""
        manager = ConfigurationManager(temp_config_dir, schema_file)

        config = TradingConfig(**sample_config_data)

        with pytest.raises(ValueError, match="already exists"):
            manager.propose_new_config(config, auto_commit=False)

    def test_activate_version(self, temp_config_dir, schema_file, sample_config_file):
        """Test activating a version"""
        manager = ConfigurationManager(temp_config_dir, schema_file)

        # Activate version
        activated_path = manager.activate_version("1.0.0", auto_commit=False)

        assert activated_path.exists()

        # Verify active symlink
        active_path = temp_config_dir / "active.yaml"
        assert active_path.exists()

        # Load and verify
        config = manager.load_current_config()
        assert config.version == "1.0.0"

    def test_activate_invalid_version(self, temp_config_dir, schema_file):
        """Test activating invalid version creates validation error"""
        manager = ConfigurationManager(temp_config_dir, schema_file)

        # Create invalid config
        invalid_data = {
            "version": "99.0.0",
            "effective_date": "2025-10-09",
            "author": "Test",
            "reason": "Invalid test config",
            "baseline": {"confidence_threshold": 150},  # Invalid
            "session_parameters": {},
            "constraints": {
                "max_confidence_deviation": 35,
                "max_risk_reward_deviation": 2.5,
                "max_overfitting_score": 0.3
            }
        }

        config_path = temp_config_dir / "session_targeted_v99.0.0.yaml"
        with open(config_path, 'w') as f:
            yaml.safe_dump(invalid_data, f)

        # Should raise ValueError for invalid config
        with pytest.raises(ValueError):
            manager.activate_version("99.0.0", auto_commit=False)

    def test_list_versions(self, temp_config_dir, schema_file, sample_config_file):
        """Test listing versions"""
        manager = ConfigurationManager(temp_config_dir, schema_file)

        # Create additional version
        config_path_2 = temp_config_dir / "session_targeted_v1.1.0.yaml"
        import shutil
        shutil.copy2(sample_config_file, config_path_2)

        versions = manager.list_versions()

        assert len(versions) >= 2
        assert "1.0.0" in versions
        assert "1.1.0" in versions
        # Should be sorted
        assert versions == sorted(versions, key=lambda v: [int(x) for x in v.split('.')])

    def test_get_active_version(self, temp_config_dir, schema_file, sample_config_file):
        """Test getting active version"""
        manager = ConfigurationManager(temp_config_dir, schema_file)

        # Activate version
        manager.activate_version("1.0.0", auto_commit=False)

        active_version = manager.get_active_version()
        assert active_version == "1.0.0"

    def test_get_active_version_none(self, temp_config_dir, schema_file):
        """Test getting active version when none exists"""
        manager = ConfigurationManager(temp_config_dir, schema_file)

        active_version = manager.get_active_version()
        assert active_version is None


class TestConfigurationManagerWithGit:
    """Test configuration manager with Git integration"""

    def test_propose_config_with_git_commit(
        self, temp_config_dir, schema_file, sample_config_data, temp_git_repo
    ):
        """Test proposing config with Git commit"""
        manager = ConfigurationManager(temp_config_dir, schema_file, repo_path=temp_git_repo.working_dir)

        # Stage initial files
        temp_git_repo.index.add([str(Path(schema_file).relative_to(temp_git_repo.working_dir))])
        temp_git_repo.index.commit("Initial commit")

        # Create new config
        sample_config_data['version'] = "1.1.0"
        sample_config_data['reason'] = "Test version with Git commit"
        config = TradingConfig(**sample_config_data)

        # Propose with commit
        config_path = manager.propose_new_config(config, auto_commit=True)

        # Verify Git commit
        assert len(list(temp_git_repo.iter_commits())) >= 2
        latest_commit = list(temp_git_repo.iter_commits())[0]
        assert "1.1.0" in latest_commit.message

    def test_get_config_history(
        self, temp_config_dir, schema_file, sample_config_data, temp_git_repo
    ):
        """Test getting configuration history"""
        manager = ConfigurationManager(temp_config_dir, schema_file, repo_path=temp_git_repo.working_dir)

        # Create initial commit
        sample_config_file = temp_config_dir / "session_targeted_v1.0.0.yaml"
        with open(sample_config_file, 'w') as f:
            yaml.safe_dump(sample_config_data, f)

        temp_git_repo.index.add([str(sample_config_file.relative_to(temp_git_repo.working_dir))])
        temp_git_repo.index.commit("feat: config v1.0.0")

        # Get history
        history = manager.get_config_history(limit=10)

        assert len(history) > 0
        assert any("1.0.0" in entry.version or "1.0.0" in entry.message for entry in history)
