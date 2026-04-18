"""Connection helper for ``family.db`` (separate from event_ledger.db).

Why a separate file:

1. **Asymmetric coupling.** Family members read Aether's ledger when they
   need to; they never write into it. Aether reads family state when the
   user asks him to; he never writes there. Separate DB enforces this
   structurally — a cross-store write would require a deliberate
   cross-import, which will stand out in any review.

2. **Ablation test mechanics (Phase 4).** Popper's redaction-ablation
   compares T1 (store live) against T2 (store blocked). A separate file
   means the ablation is "point read path at empty file" — one line.
   Table-level blocking inside a shared DB would require surgical SQL
   and would be brittle. The falsifier's mechanical cleanliness matters.

3. **Backup / migration.** Family state is relational but small; isolating
   it makes the sleep-for-family.db phase (affect decay, opinion
   consolidation) easier to reason about without side effects on the
   main ledger's invariants.

Path resolution mirrors ``_ledger_base.py``: PEP 562 dynamic lookup so
``DIVINEOS_FAMILY_DB`` takes effect at runtime, not just at import. This
is essential for tests that set the env var inside a tmp_path fixture —
an import-time-captured path would miss the override and tests would
write to the production file.
"""

import os
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    FAMILY_DB_PATH: Path


def _get_family_db_path() -> Path:
    """Return the family DB path.

    Override order:
    1. ``DIVINEOS_FAMILY_DB`` env var (tests, explicit redirect)
    2. Default ``<repo>/data/family.db``

    The default is computed at call time, not import time, so worktree
    moves don't bake in a stale absolute path.
    """
    env_path = os.environ.get("DIVINEOS_FAMILY_DB")
    if env_path:
        return Path(env_path)
    return Path(__file__).parent.parent.parent.parent.parent / "data" / "family.db"


def __getattr__(name: str) -> object:
    """PEP 562: dynamic ``FAMILY_DB_PATH`` resolution.

    Same pattern as ``_ledger_base.py`` — real attributes (monkeypatch)
    win over this fallback, but in the normal case every reference to
    ``FAMILY_DB_PATH`` reads the env var fresh.
    """
    if name == "FAMILY_DB_PATH":
        return _get_family_db_path()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def get_family_connection() -> sqlite3.Connection:
    """Open a connection to the family DB, creating the parent dir if needed.

    WAL + busy-timeout matches the main ledger — same durability and
    concurrency posture. Foreign keys are ON because family tables use
    real FK relationships (knowledge → member, letter → member,
    response → letter) and we want referential integrity enforced by
    the engine, not by hope.
    """
    db_path = _get_family_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
