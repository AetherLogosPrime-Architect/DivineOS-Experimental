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


def pytest_configure(config):
    """Initialize database before pytest runs - called early in pytest startup."""
    try:
        from divineos.core.ledger import init_db

        init_db()
    except Exception as e:
        # Don't fail pytest startup if DB init fails
        print(f"Warning: Database initialization failed: {e}", file=sys.stderr)


@pytest.fixture
def temp_test_dir():
    """Provide a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)
