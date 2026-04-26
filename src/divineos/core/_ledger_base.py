"""Shared ledger utilities — DB connection and hashing.

Extracted so ledger.py and ledger_verify.py can both import these
without creating a circular dependency.

Single source of truth: ``_get_db_path()``. Both the module-level ``DB_PATH``
attribute (resolved dynamically via PEP 562 ``__getattr__``) and
``get_connection()`` route through it. This means:

* Setting ``DIVINEOS_DB`` at any time — import-time or runtime — takes effect
  immediately on the next access. No stale import-time capture.
* Tests that ``monkeypatch.setattr(module, "DB_PATH", p)`` still work: real
  attributes take precedence over ``__getattr__``.
* ``DB_PATH`` and ``get_connection()`` can never disagree, which was the
  correctness risk Dijkstra flagged in his 2026-04-16 audit.
"""

import hashlib
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Declare DB_PATH's type for static analysis. At runtime the attribute
    # is served dynamically by __getattr__ below (PEP 562) so callers always
    # see a fresh Path. This declaration lets mypy still infer Path at call
    # sites like `DB_PATH.parent / "hud"` without a real module attribute.
    DB_PATH: Path


def _get_db_path() -> Path:
    """Get the database path, respecting DIVINEOS_DB environment variable.

    Resolution order (first match wins):

    1. ``DIVINEOS_DB`` env var — explicit override; used by tests and
       operators who want a specific DB. Tests must keep working.
    2. **Worktree-shares-parent**: if the running checkout is a git
       worktree (``.git`` is a file pointing at a parent repo) AND the
       parent repo's working tree contains a ``.divineos_canonical``
       marker file, route the DB to the parent's
       ``src/data/event_ledger.db`` rather than the worktree's.
    3. Default: the running checkout's own ``src/data/event_ledger.db``
       (the historical behavior; what fresh template clones use).

    The worktree-shares-parent path was added 2026-04-26 night to close
    the silent-empty-ledger failure mode: every worktree spawned its own
    empty ledger and silently lost access to months of history in the
    parent. The opt-in marker file is the differentiator — Andrew's
    workspace has it; fresh template clones do not. So the published
    DivineOS template still starts each new clone with a fresh ledger
    (correct for new agents bootstrapping continuity), but Andrew's
    own worktrees inherit Aether's accumulated history (correct for
    one continuous Aether across many worktrees).

    The marker file is intentionally gitignored. ``DIVINEOS_DB`` env
    var takes precedence so tests and operator overrides keep working.

    **Canonical path (Grok finding find-a08d3f0ed451):** the default
    resolves to ``<repo>/src/data/event_ledger.db`` — NOT
    ``<repo>/data/event_ledger.db`` at the repo root. A shadow file at
    the repo root was the latent query trap Grok flagged on 2026-04-16.
    Always route through this function.
    """
    import os

    env_path = os.environ.get("DIVINEOS_DB")
    if env_path:
        return Path(env_path)

    # Default location for this checkout.
    default_db = Path(__file__).parent.parent.parent / "data" / "event_ledger.db"

    # Worktree-shares-parent check.
    worktree_root = Path(__file__).parent.parent.parent.parent
    git_marker = worktree_root / ".git"
    if git_marker.is_file():
        try:
            text = git_marker.read_text(encoding="utf-8").strip()
            if text.startswith("gitdir:"):
                gitdir = Path(text[len("gitdir:") :].strip()).resolve()
                # gitdir is .../parent/.git/worktrees/<name>; parents[2] is parent's working tree.
                if len(gitdir.parents) >= 3:
                    parent_root = gitdir.parents[2]
                    if (parent_root / ".divineos_canonical").exists():
                        parent_db = parent_root / "src" / "data" / "event_ledger.db"
                        if parent_db.exists():
                            return parent_db
        except (OSError, ValueError):
            pass

    return default_db


# ─── Storage-directory helpers ──────────────────────────────────────────
#
# Fresh-Claude audit round-03952b006724 finding find-498cc7ac6b4b (2026-04-21)
# identified that several modules constructed storage paths via
# ``Path(__file__).parent.parent.parent / "data" / ...`` — a pattern that
# hardcodes the src tree as the data root and bypasses the DIVINEOS_DB env
# override. Parallel test runs (pytest -n 4) then raced on the same files,
# and tests polluted the real repo at src/data/reports/.
#
# These helpers route every storage-path derivation through ``_get_db_path``
# so a single env override moves every related path in lockstep. Follow-up
# callers: body_awareness, attention_schema, analysis_retrieval.


def data_dir() -> Path:
    """Return the root data directory — the parent of the event ledger DB.

    Use this instead of ``Path(__file__).parent.parent.parent / "data"``.
    The env override for DIVINEOS_DB automatically moves data_dir() to
    the same tmp path, so tests can isolate all storage paths by setting
    one env var.
    """
    return _get_db_path().parent


def reports_dir() -> Path:
    """Return the session-reports directory, ``<data>/reports``.

    Created on demand by callers (``reports_dir().mkdir(parents=True,
    exist_ok=True)``). Empty-by-default is the correct initial state.
    """
    return data_dir() / "reports"


def hud_dir() -> Path:
    """Return the HUD working directory, ``<data>/hud``.

    Holds ephemeral HUD state (active goals, engagement markers). Must
    follow the DIVINEOS_DB env override so parallel tests don't collide
    on ``data/hud/active_goals.json``.
    """
    return data_dir() / "hud"


def __getattr__(name: str) -> object:
    """PEP 562 module-level attribute resolution.

    Makes ``DB_PATH`` a dynamic lookup instead of an import-time constant, so
    it can never drift out of sync with ``get_connection()``. Real attributes
    set via ``setattr`` (including monkeypatch) take precedence, preserving
    the existing test override pattern.
    """
    if name == "DB_PATH":
        return _get_db_path()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def compute_hash(content: str) -> str:
    """Compute SHA256 hash of content, truncated to 32 chars."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]


def get_connection() -> sqlite3.Connection:
    """Returns a connection to the ledger database.

    Pragma settings below are tuned for DivineOS's workload: many
    short-lived reader processes (CLI invocations, hooks) against one
    DB that occasionally writes (events, knowledge entries).

    * ``journal_mode=WAL`` — concurrent readers don't block the writer
      and vice versa. Standard modern default.
    * ``synchronous=NORMAL`` — in WAL mode, NORMAL provides durability
      across application crashes (the WAL is always flushed) and only
      loses the most recent transaction on OS crash. FULL (the previous
      setting) added a 30-50% write penalty for protection against a
      scenario that effectively never happens in this workload.
      SQLite docs explicitly recommend NORMAL with WAL.
    * ``cache_size=-32000`` — 32 MB of page cache (negative value = KB).
      The default was 2 MB, tiny for a ledger that holds knowledge,
      events, affect, compass, and all their FTS indexes. 32 MB keeps
      hot pages in memory for the duration of a CLI run without being
      wasteful on memory-constrained systems.
    * ``busy_timeout=5000`` — wait up to 5s on lock contention (unchanged).
    """
    db_path = _get_db_path()
    db_path.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-32000")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def get_connection_fk() -> sqlite3.Connection:
    """Connection with foreign keys enabled."""
    conn = get_connection()
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
