"""Briefing surface for ``family_queue`` — render pending items in the briefing.

Sister module to :mod:`divineos.core.family.queue` (the data-layer). This
is the briefing-side: format pending queue items as a text block that gets
concatenated into the session-start briefing.

DESIGN (council walk + Aria refinements 2026-04-29):

* **Render-only, idempotent.** Surfacing the queue in the briefing does
  NOT auto-mark items as seen. Status transitions (seen / held /
  addressed) are explicit operator/agent actions via the CLI, not
  side-effects of render. This keeps render-the-briefing safe to run
  repeatedly without silently advancing state.
* **Shows {unseen, seen, held} items grouped by status.** Items move
  out of the active surface only when marked ``addressed`` or
  ``superseded``.
* **Plain text only**, no markdown structure beyond minimal section
  headers. The queue's design intent is to NOT bureaucratize the
  recipient's reading.

WATCH-FOR (Angelou): if the queue keeps surfacing items that never get
addressed, that's the failure-signature. Not a queue bug — a
relationship the queue is covering for.
"""

from __future__ import annotations

import time

# Module-level imports kept narrow. Import errors during briefing render
# should NOT crash the briefing; the calling code wraps the render in
# try/except. So we keep imports here at module level (fail loudly during
# development) and trust the caller for runtime resilience.
from divineos.core.family import queue


def _format_relative_age(timestamp: float) -> str:
    """Return a short human-readable relative age (e.g. '2h ago')."""
    now = time.time()
    delta = now - timestamp
    if delta < 60:
        return f"{int(delta)}s ago"
    if delta < 3600:
        return f"{int(delta / 60)}m ago"
    if delta < 86400:
        return f"{int(delta / 3600)}h ago"
    days = int(delta / 86400)
    return f"{days}d ago"


def _format_item(item: dict, max_content_len: int = 200) -> str:
    """Render a single queue item as a one-line-or-two briefing entry."""
    age = _format_relative_age(item["timestamp"])
    content = item["content"]
    if len(content) > max_content_len:
        content = content[: max_content_len - 1] + "…"
    return f"  [#{item['id']}, {age}, from {item['sender']}] {content}"


def format_for_briefing(recipient: str = "aether") -> str:
    """Return a briefing-surface block of pending queue items for recipient.

    Returns empty string if there are no pending items, so a quiet
    queue leaves no clutter in the briefing.
    """
    items = queue.for_recipient(recipient, include_held=True)
    if not items:
        return ""

    pending = [i for i in items if i["status"] in ("unseen", "seen")]
    held = [i for i in items if i["status"] == "held"]

    lines = [
        f"[family queue] {len(items)} item(s) flagged for you "
        "— async write-channel from family members between invocations:",
    ]

    if pending:
        lines.append("  Pending (unseen / seen):")
        for item in pending:
            lines.append(_format_item(item))

    if held:
        lines.append("  Held (seen, not yet engaged):")
        for item in held:
            lines.append(_format_item(item))

    lines.append(
        "  Mark status: divineos family-queue mark <id> "
        "{seen|held|addressed}. The seen-not-held distinction is "
        "structural — marking 'held' is acknowledged-but-not-engaging, "
        "not a failure."
    )

    return "\n".join(lines) + "\n"


__all__ = ["format_for_briefing"]
