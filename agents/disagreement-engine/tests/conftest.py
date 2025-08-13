"""
Test configuration and fixtures for disagreement engine tests.
"""
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Ensure pytest can find the agents module
agents_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(agents_path))