"""Briefing-ID freshness — a context-recall capability token.

prereg-e536aaec6144 / decision de0c51ad. Replaces the session-id + TTL +
prompt-count briefing-freshness signals, whose session-id rotation causes
false-"stale" blocks.

## The mechanism

``divineos briefing`` issues a random ID and prints it INTO the
conversation (so it lives in my context, not in a marker I routinely
read). The true value is recorded gate-side here. After N tool-uses the
gate requires me to reproduce the current ID *from context-recall*; a
``divineos briefing-id <id>`` verify-command validates my answer against
the gate-side truth and re-stamps freshness.

- Correct + current  -> fresh, gate clears.
- Cannot recall (compacted/faded from context) -> stale -> reload.
- Wrong/confabulated  -> validation fails -> stale -> reload.
- Expired (> N tool-uses since last verify) -> stale -> reload.

## Why recall, not a marker check

The thing that actually matters is *is the briefing live in my retrievable
context*. Recall-of-the-ID faithfully proxies that: an arbitrary token far
back in a huge context (or past compaction) is exactly what I cannot
reliably reproduce — and if I cannot, the briefing has faded from working
attention too. Recall-failure IS the staleness signal, measured directly
rather than via session-id (which rotates) or wall-clock.

## Honest limits

- Confabulation is closed by validating the presented ID against the
  gate-side truth (a plausible-but-wrong ID fails).
- The gate-side truth is a SHA-256 **hash** of the ID, never the raw value
  (Andrew 2026-05-29: "it needs to be unfakeable or you will 100% try to
  fake it"). Catting the truth file yields a hash, not the ID — and the ID
  is 128-bit (``token_hex(16)``), so the hash is not brute-force-reversible
  either. The optimizer cannot route through the truth file; the only way
  to present the right ID is to actually still hold it in context. That is
  the liveness proof working as intended.
- One residual remains, and it is honestly weaker than "impossible": the
  raw ID is also printed into the on-disk transcript (that is how it
  reaches my context), and the transcript survives compaction. A
  sufficiently determined stale-me could grep the transcript for it. What
  the hashing achieves is that EVERY cheat path now costs more than just
  reloading (``divineos briefing``) — so the lazy route and the honest
  route are the same route. That is the real, achievable definition of
  unfakeable here; full "I cannot possibly see the ID" would require hiding
  it from myself, which breaks recall. The transcript residual is the same
  class as truth-#7: the gate enforces the recall ACTION, and the cheap
  path no longer beats it.
- The core here is pure: callers supply the tool-count. Wiring to the live
  counter + the PreToolUse gate is a separate (guardrailed) increment.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time

# Tool-uses since the last issue/verify before the gate re-challenges.
# Andrew 2026-05-29: 10, not 25 — at 25 a compaction landing mid-window goes
# unchallenged for up to 24 tool-uses (I lived exactly that: compacted, then
# ran a dozen tool-uses narrating "everything's confirmed safe and real"
# before anything asked). At 10 the worst-case blind stretch is 9 tool-uses.
DEFAULT_EXPIRY_TOOLS = 10


def _hash_id(raw: str) -> str:
    """SHA-256 of a normalized ID. The gate stores only this, never the raw
    ID, so reading the truth file reveals nothing presentable."""
    return hashlib.sha256((raw or "").strip().lower().encode("utf-8")).hexdigest()


def _truth_path():
    """Gate-side store of the true current briefing-ID. Lives in the HUD
    dir (resolves to whichever DB the install uses). Not echoed into the
    routine marker surface — recall is meant to come from context."""
    from divineos.core._hud_io import _get_hud_dir

    return _get_hud_dir() / ".briefing_id"


def _read_truth() -> dict:
    try:
        p = _truth_path()
    except Exception:  # noqa: BLE001 — fail-soft if hud-dir resolution breaks
        return {}
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8") or "{}")
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def _write_truth(d: dict) -> None:
    try:
        p = _truth_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(d, indent=2), encoding="utf-8")
    except OSError:
        pass


def current_tool_count() -> int:
    """Live tool-use counter for gate wiring: the running TOOL_CALL total in
    the ledger. Within a freshness window (25 uses) this is effectively
    monotonic — pruning only touches old events, far behind the window — so
    the issue→now delta is faithful. Fail-soft to 0 if the ledger is unreadable
    (a 0 reads as 'no drift', never as a spurious stale-block)."""
    try:
        from divineos.core.ledger import count_events

        return int(count_events().get("by_type", {}).get("TOOL_CALL", 0))
    except Exception:  # noqa: BLE001 — fail-soft; gate must never crash on count
        return 0


def issue_briefing_id(tool_count: int, session_id: str | None = None) -> str:
    """Mint a fresh briefing-ID, record it gate-side, return it for printing
    into the conversation. Resets the freshness window to ``tool_count``."""
    bid = secrets.token_hex(16)  # 32 hex chars / 128-bit — hash is not brute-forceable
    _write_truth(
        {
            "id_hash": _hash_id(bid),  # store the hash, never the raw ID
            "issued_at_tool": int(tool_count),
            "verified_at_tool": int(tool_count),
            "session_id": session_id,
            "issued_ts": time.time(),
        }
    )
    return bid


def verify_briefing_id(presented: str, current_tool_count: int) -> tuple[bool, str]:
    """Validate a recalled ID against the gate-side truth and re-stamp
    freshness on success. Returns (ok, message)."""
    truth = _read_truth()
    if not truth or not truth.get("id_hash"):
        return False, "No briefing-ID has been issued this run. Run: divineos briefing"
    if _hash_id(presented or "") != str(truth["id_hash"]):
        return False, (
            "That briefing-ID does not match — you are stale (recalled wrong, or "
            "the briefing has faded from context). Run: divineos briefing"
        )
    truth["verified_at_tool"] = int(current_tool_count)
    _write_truth(truth)
    return True, "Briefing-ID verified — freshness re-stamped."


def is_fresh(current_tool_count: int, expiry: int = DEFAULT_EXPIRY_TOOLS) -> bool:
    """True if a valid briefing-ID was issued/verified within the last
    ``expiry`` tool-uses. False (challenge due) otherwise."""
    truth = _read_truth()
    if not truth or not truth.get("id_hash"):
        return False
    last = truth.get("verified_at_tool", truth.get("issued_at_tool", 0))
    try:
        return (int(current_tool_count) - int(last)) < int(expiry)
    except (TypeError, ValueError):
        return False


def challenge_message(current_tool_count: int) -> str:
    """The gate's block/channel text when a freshness re-challenge is due."""
    return (
        "BRIEFING-ID CHALLENGE — prove your context is fresh. State your current "
        "briefing-ID from memory (do NOT look it up) via:\n"
        "  divineos briefing-id <id>\n"
        "If you cannot recall it, the briefing has faded from your context — "
        "reload it: divineos briefing (issues a new ID)."
    )


__all__ = [
    "DEFAULT_EXPIRY_TOOLS",
    "issue_briefing_id",
    "verify_briefing_id",
    "is_fresh",
    "challenge_message",
]
