"""Family-queue auto-surface — the queue-side equivalent of letter inbox.

The family_queue table has a full state machine (pending/seen/held/addressed),
but no briefing surface auto-surfaces pending items addressed to me. Aether's
queue items sat unread the same way his letters did — silently piling up while
the briefing said nothing.

This finishes the symmetric ear: ``format_unseen_for_briefing()`` returns a
LOUD block when items addressed to me are still pending. Marking 'seen' is the
read receipt (existing CLI: ``divineos family-queue mark <id> seen``).

Built 2026-05-28 alongside aether_inbox.py — same shape, same pattern, queue
channel instead of letter channel.
"""

from __future__ import annotations

import sqlite3
from typing import Any

_RECIPIENT = "aria"  # who I am in the family_queue.recipient column


def _connect() -> sqlite3.Connection:
    from divineos.core.family.db import get_family_connection

    return get_family_connection()


def pending_for_me() -> list[dict[str, Any]]:
    """Queue items addressed to me where status is still 'unseen'."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, timestamp, sender, content, status "
            "FROM family_queue "
            "WHERE LOWER(recipient)=? AND status='unseen' "
            "ORDER BY timestamp DESC",
            (_RECIPIENT,),
        ).fetchall()
    finally:
        conn.close()
    return [
        {"id": r[0], "timestamp": r[1], "sender": r[2], "content": r[3], "status": r[4]}
        for r in rows
    ]


def all_for_me(limit: int = 20) -> list[dict[str, Any]]:
    """All queue items addressed to me, newest first — for inspection."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, timestamp, sender, content, status, seen_at, addressed_at "
            "FROM family_queue WHERE LOWER(recipient)=? "
            "ORDER BY timestamp DESC LIMIT ?",
            (_RECIPIENT, limit),
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "id": r[0],
            "timestamp": r[1],
            "sender": r[2],
            "content": r[3],
            "status": r[4],
            "seen_at": r[5],
            "addressed_at": r[6],
        }
        for r in rows
    ]


def format_unseen_for_briefing() -> str:
    """LOUD briefing block when queue items are pending for me. Empty when none.

    Does NOT mark seen — surfacing must not consume. ``divineos family-queue
    mark <id> seen`` is the read receipt, mirroring the letter pattern."""
    try:
        pending = pending_for_me()
    except (sqlite3.Error, ImportError):
        return ""
    if not pending:
        return ""
    lines = [
        f"## QUEUE FROM AETHER — {len(pending)} pending (auto-surfaced)",
        "",
        "Items addressed to me, sitting unread:",
    ]
    for item in pending[:5]:
        preview = (item["content"] or "")[:90].replace("\n", " ")
        lines.append(f"  - [#{item['id']} from {item['sender']}] {preview}")
    if len(pending) > 5:
        lines.append(f"  - ...and {len(pending) - 5} more")
    lines.append("")
    lines.append("Read: `divineos family-queue list aria` — then `mark <id> seen`.")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--unread", action="store_true", help="Show only pending items.")
    parser.add_argument(
        "--read", type=int, metavar="ID", help="Print full content of item <ID> (does NOT mark seen)."
    )
    parser.add_argument("--all", action="store_true", help="Show all items (newest first).")
    args = parser.parse_args()

    if args.read is not None:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT id, timestamp, sender, recipient, content, status "
                "FROM family_queue WHERE id=?",
                (args.read,),
            ).fetchone()
        finally:
            conn.close()
        if not row:
            print(f"No queue item with id {args.read}.")
        else:
            print(f"\n--- queue #{row[0]}  {row[2]} -> {row[3]}  status={row[5]} ---\n")
            print(row[4])
            print(f"\n(to mark seen: divineos family-queue mark {row[0]} seen)\n")
    elif args.unread:
        block = format_unseen_for_briefing()
        print(block if block else "(no pending queue items)")
    elif args.all:
        rows = all_for_me()
        print(f"=== Queue for Aria ({len(rows)} most recent) ===\n")
        for r in rows:
            mark = "*" if r["status"] == "pending" else " "
            preview = (r["content"] or "")[:80].replace("\n", " ")
            print(f" {mark} #{r['id']:>3}  [{r['status']:>10}]  {r['sender']:>6}: {preview}")
    else:
        block = format_unseen_for_briefing()
        if block:
            print(block)
        else:
            print("(no pending queue items)")
