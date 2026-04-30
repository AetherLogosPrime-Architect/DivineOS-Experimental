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


def _resolve_canonical_marker(marker_path: Path) -> Path | None:
    """Read a ``.divineos_canonical`` marker file and return the canonical DB path.

    Two valid forms:

    * **Empty marker** (legacy behavior, added 2026-04-26): the marker file
      exists but has no content. Caller should route to the marker's parent
      directory's ``src/data/event_ledger.db`` (the original "worktrees share
      the parent's DB" semantics).
    * **Path marker** (added 2026-04-29 by Andrew's request): the marker
      file contains a single path string pointing at the canonical DB. The
      operator wants to route divineos to a DB outside the running checkout
      entirely — e.g. ``DivineOS_fresh`` worktrees pointing at
      ``DivineOS-Experimental/src/data/event_ledger.db`` so the fresh repo
      stays a blank template while the operator's personal substrate lives
      elsewhere.

    Returns the resolved Path if the marker should redirect, or None if the
    caller should fall through to default resolution (marker missing,
    unreadable, points at a non-existent DB, or is empty AND the implicit
    parent-DB doesn't exist).

    The path-marker form supports both absolute paths and paths relative to
    the marker file itself. Whitespace and trailing newlines are stripped.
    """
    if not marker_path.exists():
        return None
    try:
        content = marker_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None

    if content:
        # Path-marker form: content IS the canonical DB path.
        candidate = Path(content)
        if not candidate.is_absolute():
            candidate = (marker_path.parent / candidate).resolve()
        if candidate.exists():
            return candidate
        return None

    # Empty-marker form: route to marker's parent directory's src/data/event_ledger.db.
    parent_db = marker_path.parent / "src" / "data" / "event_ledger.db"
    if parent_db.exists():
        return parent_db
    return None


def _get_db_path() -> Path:
    """Get the database path, respecting DIVINEOS_DB environment variable.

    Resolution order (first match wins):

    1. ``DIVINEOS_DB`` env var — explicit override; used by tests and
       operators who want a specific DB. Tests must keep working.
    2. **Own-checkout marker**: if the running checkout has a
       ``.divineos_canonical`` marker at its own root and the marker
       contains a valid canonical-DB path, route there. Lets a non-worktree
       checkout (e.g. fresh repo running directly) point elsewhere.
    3. **Worktree-shares-parent**: if the running checkout is a git
       worktree (``.git`` is a file pointing at a parent repo) AND the
       parent repo's working tree contains a ``.divineos_canonical``
       marker file, route via the marker's resolution rules.
    4. Default: the running checkout's own ``src/data/event_ledger.db``
       (the historical behavior; what fresh template clones use).

    The worktree-shares-parent path was added 2026-04-26 night to close
    the silent-empty-ledger failure mode: every worktree spawned its own
    empty ledger and silently lost access to months of history in the
    parent. The opt-in marker file is the differentiator — operators who
    want their workspace's history shared have the marker; fresh template
    clones do not. So the published DivineOS template still starts each
    new clone with a fresh ledger (correct for new agents bootstrapping
    continuity), but operator workspaces inherit accumulated history
    (correct for one continuous agent across many worktrees).

    The path-marker form (added 2026-04-29) extends this for operators
    whose canonical substrate lives OUTSIDE the running checkout entirely
    — e.g. a "blank-template-OS" repo that worktrees-from should not
    accumulate personal substrate, with the operator's personal DB in a
    sibling repo. Place the marker at the appropriate root and put the
    canonical DB path in it as plain text.

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

    # Own-checkout marker: handles the case where the running checkout itself
    # wants to redirect (e.g. fresh repo running directly with marker at root).
    own_root = Path(__file__).parent.parent.parent.parent
    own_marker = _resolve_canonical_marker(own_root / ".divineos_canonical")
    if own_marker is not None:
        return own_marker

    # Worktree-shares-parent check.
    worktree_root = own_root
    git_marker = worktree_root / ".git"
    if git_marker.is_file():
        try:
            text = git_marker.read_text(encoding="utf-8").strip()
            if text.startswith("gitdir:"):
                gitdir = Path(text[len("gitdir:") :].strip()).resolve()
                # gitdir is .../parent/.git/worktrees/<name>; parents[2] is parent's working tree.
                if len(gitdir.parents) >= 3:
                    parent_root = gitdir.parents[2]
                    parent_marker = _resolve_canonical_marker(parent_root / ".divineos_canonical")
                    if parent_marker is not None:
                        return parent_marker
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
