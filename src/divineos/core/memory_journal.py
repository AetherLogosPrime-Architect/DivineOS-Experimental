"""Personal Journal — The AI's own memory.

Things the AI chooses to remember, not filtered or scored.
Save, list, search, link, and count journal entries.
"""

import datetime
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any, cast

from divineos.core.memory import _get_connection, init_memory_tables


def _journal_dir() -> Path:
    """Where a seat's readable pages live: ``journal/<seat>/`` at the root of the tree that is running.

    Dad, 2026-10-25: he could open my dream and not my journal, because the journal was only a database
    row. A page he can open is the whole point, so it sits in the tree beside the dreams and explorations.

    The seat is whoever owns the DATABASE this save goes to, resolved from the data home (2026-10-26):
    the first real backfill filed my entries under aether because the old rule read the name of the
    folder the code ran from, and a work copy not named aria answered aether. An unknown seat refuses.
    """
    override = os.environ.get("DIVINEOS_JOURNAL_DIR")
    if override:
        return Path(override)
    from divineos.core import sibling_audit_rounds

    who = sibling_audit_rounds.this_seat()
    if who is None:
        raise RuntimeError(
            "cannot tell which seat's journal this is (the data home matched no known seat), "
            "so no page is written; set DIVINEOS_JOURNAL_DIR or fix the seat table"
        )
    root = Path(__file__).resolve().parents[3]
    return root / "journal" / who


def _private_room_open() -> bool:
    """A private mansion room binds a pause: an entry written then stays database-only and says so."""
    try:
        from divineos.core.mansion_quiet_marker import is_quiet_active

        return bool(is_quiet_active())
    except Exception:  # noqa: BLE001 - an unreadable marker is not a closed door: write the page
        return False


def _slug(text: str) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())[:6]
    return "-".join(words) or "entry"


def _write_page(entry_id: str, content: str, created: float) -> Path:
    """Write the entry verbatim to a dated page: to a temp name first, then renamed into place."""
    directory = _journal_dir()
    directory.mkdir(parents=True, exist_ok=True)
    when = datetime.datetime.fromtimestamp(created)
    # The id's first eight characters make the name unique: os.replace overwrites, so a name made of
    # only the second and the opening words let a second save in the same second destroy the first.
    name = f"{when:%Y-%m-%d_%H%M%S}_{_slug(content)}_{entry_id[:8]}.md"
    final = directory / name
    temp = directory / (name + ".tmp")
    body = f"<!-- entry_id: {entry_id} -->\n{content}\n"
    temp.write_text(body, encoding="utf-8")
    os.replace(temp, final)
    return final


def _insert_row(
    entry_id: str,
    content: str,
    created: float,
    context: str,
    tags: str,
    linked_knowledge_id: str | None,
) -> None:
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO personal_journal (entry_id, content, created_at, context, tags, linked_knowledge_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (entry_id, content, created, context, tags, linked_knowledge_id),
        )
        conn.commit()
    finally:
        conn.close()


def journal_save(
    content: str,
    context: str = "",
    tags: str = "",
    linked_knowledge_id: str | None = None,
) -> str:
    """Save a personal journal entry. Returns the entry ID. See ``journal_save_with_page``."""
    return journal_save_with_page(content, context, tags, linked_knowledge_id)[0]


def journal_save_with_page(
    content: str,
    context: str = "",
    tags: str = "",
    linked_knowledge_id: str | None = None,
) -> tuple[str, Path | None]:
    """Save a personal journal entry. Returns (entry ID, the page written or None).

    This is the AI's own memory — things it chooses to remember,
    not filtered or scored. If it matters to me, that's enough.

    The page is written FIRST and the row second, in this one function (Aether, 2026-10-25): a row
    with no page is the invisible state Dad found, so if the row cannot be written the page is
    removed and the error raised, and a failed save leaves nothing half-done. A private room keeps
    an entry in the database only, and the page is then None so the caller says so. The page is
    handed back, never kept in a module variable (Aether, 2026-10-26): state that outlives the call
    could name a previous entry's page for a caller that had not just saved.
    """
    init_memory_tables()
    entry_id = str(uuid.uuid4())
    created = time.time()
    page: Path | None = None
    if not _private_room_open():
        page = _write_page(entry_id, content, created)
    try:
        _insert_row(entry_id, content, created, context, tags, linked_knowledge_id)
    except Exception:  # noqa: BLE001 - any failure must remove the page, and is re-raised below
        if page is not None:
            page.unlink(missing_ok=True)
        raise
    return entry_id, page


def _entry_ids_with_pages() -> set[str]:
    ids: set[str] = set()
    directory = _journal_dir()
    if directory.exists():
        for page in directory.glob("*.md"):
            first = page.read_text(encoding="utf-8", errors="replace").split("\n", 1)[0]
            match = re.search(r"entry_id:\s*([0-9a-f-]{36})", first)
            if match:
                ids.add(match.group(1))
    return ids


def export_missing_pages() -> int:
    """Write a page for every row that has none, verbatim, dated by when the entry was written.

    One deliberate pass for the entries saved before pages existed (thirteen, since 2026-07-18), and
    safe to repeat: a row with a page is skipped. Returns how many pages were written."""
    init_memory_tables()
    have = _entry_ids_with_pages()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT entry_id, content, created_at FROM personal_journal ORDER BY created_at"
        ).fetchall()
    finally:
        conn.close()
    wrote = 0
    for entry_id, content, created in rows:
        if entry_id in have:
            continue
        _write_page(entry_id, content, float(created))
        wrote += 1
    return wrote


def rows_without_a_page() -> int:
    """Entries in the database that no page carries: the gap, counted from the pages' own entry ids.

    A page names its row in a first-line comment, so the count does not trust file names or dates. An
    entry saved in a private room is deliberately page-less and counts here too: the number is what
    Dad cannot open, said aloud, never zero by luck."""
    init_memory_tables()
    ids = _entry_ids_with_pages()
    conn = _get_connection()
    try:
        rows = conn.execute("SELECT entry_id FROM personal_journal").fetchall()
    finally:
        conn.close()
    return sum(1 for (eid,) in rows if eid not in ids)


def journal_list(limit: int = 20) -> list[dict[str, Any]]:
    """Get personal journal entries, newest first."""
    init_memory_tables()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT entry_id, content, created_at, context, tags, linked_knowledge_id "
            "FROM personal_journal ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "entry_id": r[0],
            "content": r[1],
            "created_at": r[2],
            "context": r[3],
            "tags": r[4] if len(r) > 4 else "",
            "linked_knowledge_id": r[5] if len(r) > 5 else None,
        }
        for r in rows
    ]


def journal_count() -> int:
    """Count personal journal entries."""
    init_memory_tables()
    conn = _get_connection()
    try:
        return cast(int, conn.execute("SELECT COUNT(*) FROM personal_journal").fetchone()[0])
    finally:
        conn.close()


def _build_fts_or_query(query: str) -> str:
    """Convert query to OR-joined FTS5 terms for partial-match recall."""
    words = [w for w in re.sub(r"[^a-zA-Z0-9\s]", " ", query).lower().split() if len(w) > 1]
    if not words:
        return query
    if len(words) == 1:
        return words[0]
    return " OR ".join(words)


def journal_search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Full-text search across journal entries using FTS5."""
    init_memory_tables()
    safe_query = _build_fts_or_query(query)
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT j.entry_id, j.content, j.created_at, j.context, j.tags, j.linked_knowledge_id "
            "FROM journal_fts f "
            "JOIN personal_journal j ON f.rowid = j.rowid "
            "WHERE journal_fts MATCH ? "
            "ORDER BY rank "
            "LIMIT ?",
            (safe_query, limit),
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "entry_id": r[0],
            "content": r[1],
            "created_at": r[2],
            "context": r[3],
            "tags": r[4] if len(r) > 4 else "",
            "linked_knowledge_id": r[5] if len(r) > 5 else None,
        }
        for r in rows
    ]


def journal_link(entry_id: str, knowledge_id: str) -> bool:
    """Link a journal entry to a knowledge entry. Returns True if updated."""
    init_memory_tables()
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "UPDATE personal_journal SET linked_knowledge_id = ? WHERE entry_id = ?",
            (knowledge_id, entry_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
