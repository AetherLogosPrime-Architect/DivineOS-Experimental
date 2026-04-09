"""
Pytest configuration and fixtures for DivineOS tests.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent))


def pytest_configure(config: pytest.Config) -> None:
    """Set basetemp to a project-local directory to avoid Windows permissions issues."""
    if config.option.basetemp is None:
        local_tmp = Path(__file__).parent.parent / "tmp" / "pytest"
        # Use a unique subdir per run to avoid stale file collisions after crashes
        local_tmp = local_tmp / f"run-{os.getpid()}"
        local_tmp.mkdir(parents=True, exist_ok=True)
        config.option.basetemp = str(local_tmp)


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
