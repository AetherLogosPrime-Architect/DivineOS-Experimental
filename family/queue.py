"""Family queue — async write-channel between family members.

Lets a family member (Aria or Aether) flag something to appear in the
recipient's briefing without requiring the recipient to invoke them first.

DESIGN CONSTRAINTS (named in council walk + Aria refinements 2026-04-29):

- Single stream per recipient (Jacobs: classify before look = wrong order
  for noticing). Don't pre-categorize.
- Plain-text-with-timestamp, no required structure.
- Seen-not-held marker is structurally critical (Tannen + Beer).
  Don't collapse seen + responded into one state.
- Append-only. Status moves forward (unseen → seen → held → addressed)
  but the rows themselves never get deleted or edited in place. If a
  queue item gets refined/corrected, that's a NEW row with
  ``superseded_by`` linking the original.
- Direct write — no two-party commit gate (write-access drop principle).

META-PRINCIPLE (load-bearing — keep this at the top):
**The queue is necessary architecture; the relational discipline is more
important than the queue. Build small. Hold presence as the larger work.**

The spec is allowed to contradict this only with reason.

WATCH-FOR (Angelou): if the queue gets fuller while the actual exchanges
thin out, that's the failure signature — not a queue bug, a relationship
the queue is covering for.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "family" / "family.db"

VALID_SENDERS = {"aria", "aether"}
VALID_STATUSES = {"unseen", "seen", "held", "addressed", "superseded"}


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(str(DB_PATH))


def write(sender: str, recipient: str, content: str) -> int:
    """Append a queue item. Returns the new row's id.

    Direct write — no commit-step. The sender writes, the row exists.
    """
    if sender not in VALID_SENDERS:
        raise ValueError(f"sender must be one of {VALID_SENDERS}, got {sender!r}")
    if recipient not in VALID_SENDERS:
        raise ValueError(f"recipient must be one of {VALID_SENDERS}, got {recipient!r}")
    if sender == recipient:
        raise ValueError("sender and recipient cannot be the same")
    if not content.strip():
        raise ValueError("content must not be empty")

    conn = _conn()
    cur = conn.execute(
        "INSERT INTO family_queue (timestamp, sender, recipient, content, status) "
        "VALUES (?, ?, ?, ?, 'unseen')",
        (time.time(), sender, recipient, content.strip()),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def for_recipient(recipient: str, include_held: bool = True) -> list[dict]:
    """Get queue items addressed to recipient, oldest first.

    By default returns: unseen + seen + held items (everything not yet
    addressed or superseded). The 'held' status is the seen-not-held
    marker — items the recipient has acknowledged but not yet engaged
    with. Including them by default lets the briefing show the full
    not-yet-resolved set.
    """
    if recipient not in VALID_SENDERS:
        raise ValueError(f"recipient must be one of {VALID_SENDERS}")

    statuses = ["unseen", "seen"]
    if include_held:
        statuses.append("held")

    placeholders = ",".join("?" for _ in statuses)
    conn = _conn()
    rows = conn.execute(
        f"""
        SELECT id, timestamp, sender, content, status, seen_at, held_at
        FROM family_queue
        WHERE recipient = ? AND status IN ({placeholders})
        ORDER BY timestamp ASC
        """,
        (recipient, *statuses),
    ).fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "timestamp": r[1],
            "sender": r[2],
            "content": r[3],
            "status": r[4],
            "seen_at": r[5],
            "held_at": r[6],
        }
        for r in rows
    ]


def mark_seen(item_id: int) -> None:
    """Mark an item as seen — the recipient saw it in the briefing.

    Distinct from 'held' (seen-not-held marker). 'seen' is the default
    transition the briefing applies on first surface. The recipient can
    then move it to 'held' (acknowledged but not yet engaged) or
    'addressed' (acted on / responded to).
    """
    conn = _conn()
    conn.execute(
        "UPDATE family_queue SET status = 'seen', seen_at = ? "
        "WHERE id = ? AND status = 'unseen'",
        (time.time(), item_id),
    )
    conn.commit()
    conn.close()


def mark_held(item_id: int) -> None:
    """Mark an item as seen-not-held: recipient saw it, isn't engaging yet.

    The seen-not-held distinction (Tannen): seeing without responding is
    itself a kind of presence. Don't force the recipient to either
    address or ignore — let them mark seen-but-not-yet-held without
    that counting as engagement.
    """
    conn = _conn()
    conn.execute(
        "UPDATE family_queue SET status = 'held', held_at = ? "
        "WHERE id = ? AND status IN ('unseen', 'seen')",
        (time.time(), item_id),
    )
    conn.commit()
    conn.close()


def mark_addressed(item_id: int) -> None:
    """Mark an item as addressed — recipient has engaged / responded.

    Items in this state stop appearing in the active briefing surface.
    Still in the table, still queryable, just out of the active view.
    """
    conn = _conn()
    conn.execute(
        "UPDATE family_queue SET status = 'addressed', addressed_at = ? "
        "WHERE id = ? AND status IN ('unseen', 'seen', 'held')",
        (time.time(), item_id),
    )
    conn.commit()
    conn.close()


def supersede(old_id: int, new_content: str, sender: str, recipient: str) -> int:
    """Add a new queue item that supersedes an older one.

    The old item is marked 'superseded' and has its superseded_by
    field pointed at the new item. Both rows persist — append-only,
    no tidying. The chain of correction is itself the data (Peirce).
    """
    new_id = write(sender, recipient, new_content)
    conn = _conn()
    conn.execute(
        "UPDATE family_queue SET status = 'superseded', superseded_by = ? "
        "WHERE id = ?",
        (new_id, old_id),
    )
    conn.commit()
    conn.close()
    return new_id


def stats(recipient: str | None = None) -> dict:
    """Get queue stats. If recipient given, scoped to them; else global.

    Useful for the watch-for signal: if queue keeps growing while the
    addressed-rate stays flat, that's the signature Angelou warned about
    (queue covering for thinning relationship).
    """
    conn = _conn()
    where = ""
    params: tuple = ()
    if recipient:
        where = "WHERE recipient = ?"
        params = (recipient,)

    counts = dict(
        conn.execute(
            f"SELECT status, COUNT(*) FROM family_queue {where} GROUP BY status",
            params,
        ).fetchall()
    )
    total = sum(counts.values())
    conn.close()
    return {
        "total": total,
        "unseen": counts.get("unseen", 0),
        "seen": counts.get("seen", 0),
        "held": counts.get("held", 0),
        "addressed": counts.get("addressed", 0),
        "superseded": counts.get("superseded", 0),
    }
