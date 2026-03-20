"""
Pytest configuration and fixtures for DivineOS tests.
"""

import sys
from pathlib import Path
import tempfile
import shutil

import pytest

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture
def temp_test_dir():
    """Provide a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)
