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

    # Initialize database before test (with timeout to prevent hanging)
    try:
        init_db()
    except Exception as e:
        print(f"Warning: Failed to initialize database: {e}")

    # Clear any existing session state
    try:
        clear_session()
    except Exception as e:
        print(f"Warning: Failed to clear session: {e}")

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
