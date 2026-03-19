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

    - Clears the ledger database
    - Initializes the ledger database
    - Clears any existing session state
    - Cleans up after test completes
    """
    # Clear database before test to ensure clean state
    # Database is at src/data/event_ledger.db
    db_path = Path(__file__).parent.parent / "src" / "data" / "event_ledger.db"
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass  # Ignore errors if file is locked

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
