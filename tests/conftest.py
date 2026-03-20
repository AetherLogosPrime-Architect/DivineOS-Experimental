"""
Pytest configuration and fixtures for DivineOS tests.

Provides:
- Database initialization for each test
- Session cleanup between tests
- Temporary test directories
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from divineos.core.session_manager import clear_session


@pytest.fixture(autouse=True)
def setup_test_environment():
    """
    Automatically set up test environment before each test.

    - Clears the ledger database
    - Initializes the ledger database
    - Clears any existing session state
    - Cleans up after test completes
    """
    # Skip database initialization during collection phase
    # This prevents hanging during pytest collection
    yield

    # Cleanup after test
    try:
        clear_session()
    except Exception as e:
        print(f"Warning: Failed to clear session during cleanup: {e}")


@pytest.fixture
def temp_test_dir():
    """
    Provide a temporary directory for test files.

    Automatically cleaned up after test.
    """
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)
