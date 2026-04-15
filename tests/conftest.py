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
        pytest_tmp = Path(__file__).parent.parent / "tmp" / "pytest"
        # Use a unique subdir per run to avoid stale file collisions after crashes
        local_tmp = pytest_tmp / f"run-{os.getpid()}"
        local_tmp.mkdir(parents=True, exist_ok=True)
        config.option.basetemp = str(local_tmp)

        # Clean up old runs (keep last 3) to prevent unbounded disk growth.
        # Without this, each run leaves ~189MB of temp databases — 27 runs = 4.6GB.
        try:
            old_runs = sorted(
                [d for d in pytest_tmp.iterdir() if d.is_dir() and d.name.startswith("run-")],
                key=lambda p: p.stat().st_mtime,
            )
            for stale in old_runs[:-3]:
                import shutil

                shutil.rmtree(stale, ignore_errors=True)
        except OSError:
            pass


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
