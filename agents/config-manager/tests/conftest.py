"""
Pytest configuration and fixtures for config manager tests
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import yaml
import json


@pytest.fixture
def temp_config_dir():
    """Create temporary configuration directory"""
    temp_dir = Path(tempfile.mkdtemp())
    config_dir = temp_dir / "config" / "parameters"
    config_dir.mkdir(parents=True)

    yield config_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def schema_file(temp_config_dir):
    """Create JSON schema file"""
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["version", "effective_date", "author", "reason", "baseline", "session_parameters", "constraints"],
        "properties": {
            "version": {"type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$"},
            "effective_date": {"type": "string", "format": "date"},
            "author": {"type": "string"},
            "reason": {"type": "string", "minLength": 10},
            "baseline": {
                "type": "object",
                "required": ["confidence_threshold", "min_risk_reward"],
                "properties": {
                    "confidence_threshold": {"type": "number", "minimum": 0, "maximum": 100},
                    "min_risk_reward": {"type": "number", "minimum": 0, "exclusiveMinimum": True}
                }
            },
            "session_parameters": {"type": "object"},
            "constraints": {
                "type": "object",
                "required": ["max_confidence_deviation", "max_risk_reward_deviation", "max_overfitting_score"],
                "properties": {
                    "max_confidence_deviation": {"type": "number", "minimum": 0},
                    "max_risk_reward_deviation": {"type": "number", "minimum": 0},
                    "max_overfitting_score": {"type": "number", "minimum": 0, "maximum": 1}
                }
            }
        }
    }

    schema_path = temp_config_dir / "schema.json"
    with open(schema_path, 'w') as f:
        json.dump(schema, f)

    return schema_path


@pytest.fixture
def sample_config_data():
    """Sample configuration data"""
    return {
        "version": "1.0.0",
        "effective_date": "2025-10-09",
        "author": "Test Author",
        "reason": "Test configuration for unit tests",
        "baseline": {
            "confidence_threshold": 55.0,
            "min_risk_reward": 1.8,
            "max_risk_reward": 5.0,
            "source": "universal_cycle_4"
        },
        "session_parameters": {
            "tokyo": {
                "confidence_threshold": 85.0,
                "min_risk_reward": 4.0,
                "max_risk_reward": 6.0,
                "volatility_adjustment": 0.20,
                "justification": "Tokyo session test"
            },
            "london": {
                "confidence_threshold": 72.0,
                "min_risk_reward": 3.2,
                "max_risk_reward": 5.0
            }
        },
        "constraints": {
            "max_confidence_deviation": 35.0,
            "max_risk_reward_deviation": 2.5,
            "max_overfitting_score": 0.3,
            "min_backtest_sharpe": 1.2,
            "min_out_of_sample_ratio": 0.7
        }
    }


@pytest.fixture
def sample_config_file(temp_config_dir, sample_config_data):
    """Create sample configuration YAML file"""
    config_path = temp_config_dir / "session_targeted_v1.0.0.yaml"

    with open(config_path, 'w') as f:
        yaml.safe_dump(sample_config_data, f)

    return config_path


@pytest.fixture
def temp_git_repo(temp_config_dir):
    """Create temporary Git repository"""
    try:
        from git import Repo

        repo_path = temp_config_dir.parent.parent
        repo = Repo.init(repo_path)

        # Configure git
        with repo.config_writer() as git_config:
            git_config.set_value('user', 'name', 'Test User')
            git_config.set_value('user', 'email', 'test@example.com')

        yield repo

    except ImportError:
        pytest.skip("GitPython not available")
