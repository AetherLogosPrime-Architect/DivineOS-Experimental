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

from divineos.core.ledger import init_db
from divineos.core.session_manager import clear_session


@pytest.fixture(autouse=True)
def setup_test_environment():
    """
    Automatically set up test environment before each test.

    - Initializes the ledger database
    - Clears any existing session state
    - Cleans up after test completes
    """
    # Initialize database before test
    init_db()

    # Clear any existing session state
    clear_session()

    yield

    # Cleanup after test
    clear_session()


@pytest.fixture
def temp_test_dir():
    """
    Provide a temporary directory for test files.

    Automatically cleaned up after test.
    """
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)
