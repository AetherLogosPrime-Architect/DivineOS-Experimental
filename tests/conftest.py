"""
Pytest configuration and fixtures for DivineOS tests.
"""

import os
import sys
from pathlib import Path
import tempfile
import shutil

import pytest

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path):
    """Give every test its own fresh database so tests never interfere with each other."""
    db_path = tmp_path / "test_ledger.db"
    os.environ["DIVINEOS_DB"] = str(db_path)

    from divineos.core.ledger import init_db

    init_db()
    yield
    os.environ.pop("DIVINEOS_DB", None)


@pytest.fixture
def temp_test_dir():
    """Provide a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)
