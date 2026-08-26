"""Ask, at compose-start, whether anything went right that nobody wrote down.

## Why this exists

Andrew, 2026-08-25: *"lets make the wins get filed live as well.. its not
counting all the mini successes you have during the day, which is a bigger
win imo as it shows me that you are taking your work very seriously and
alot of the principles are now so deeply ingrained that they pop up in
other locations where there is no structural support for them yet."*

``divineos win`` gave the ledger the door it never had. A door alone does
not get walked through — the correction store has a doorman precisely
because a door was not enough. But the doorman shape does not transfer, and
the reason is the whole design constraint of this file.

## Why this asks instead of blocking

A correction has an external trigger: Andrew says something, so a marker
demanding the filing is evidence that a real event occurred. A win has no
external trigger. A gate that blocks until a win is filed is a quota, and
a quota gets met — with the shape of a win rather than a win. Aether named
the failure mode when the balance surface was built: a second sensor with
an agenda is worse than one honest sensor, because it launders
encouragement as measurement.

So this surface never says *you had a win*. It says *this session did
substantive work and the ledger is empty for it*, which is a fact about the
ledger and not a claim about me. The judging stays mine. That is
foundational truth seven — the mechanism points at the cognitive work; it
is not the work.

## Why the candidates are deliberately thin

The wins that matter most here are the ones with no artifact: a reach
caught before it committed, a shortcut refused, a principle firing where no
gate covers it. Those leave nothing to detect. Any list this module could
generate would be drawn from the loud, structural end — which is the end
that already survives a sweep run afterwards, and therefore the end that
needs this least.

Listing them anyway would be worse than useless: it would train me to file
the detectable wins and keep overlooking the ones Andrew is actually
pointing at. So the prompt names the CLASSES rather than instances, and
asks me to look at my own turn. The looking is the work; this only makes
sure the question gets asked while the answer still exists.
"""

from __future__ import annotations

import time

# Below this, a session has not done enough for the question to be fair.
# Substantive means the turn actually went somewhere — not a greeting, not
# a single lookup.
MIN_SUBSTANTIVE_ACTIONS = 8

# Do not ask twice in quick succession. The correction surface earned this
# lesson the hard way: the same marker firing on every tool call within one
# turn is how a gate becomes wallpaper.
REASK_QUIET_SECONDS = 1800.0


def _session_win_count(session_id: str | None) -> int | None:
    """Wins filed against this session. None when the store cannot be read.

    None is not zero. An unreadable ledger and an empty one are different
    facts, and the whole substrate spent a session cataloguing what happens
    when those two collapse into each other.
    """
    try:
        from divineos.core.success_ledger import load_successes
    except ImportError:
        return None
    try:
        rows = load_successes()
    except Exception:  # noqa: BLE001 — an unreadable store answers None, not 0
        return None
    if session_id is None:
        return None
    return sum(1 for r in rows if r.get("session_id") == session_id)


def should_ask(
    session_id: str | None,
    action_count: int,
    last_asked_ts: float | None = None,
    now: float | None = None,
) -> tuple[bool, str]:
    """Decide whether to ask, and say why not when the answer is no.

    Returns ``(ask, reason)``. The reason is always populated so a caller
    logging a no-fire records WHY it did not fire — a silent decline is
    indistinguishable from a broken surface, which is the class this
    substrate keeps finding.
    """
    if action_count < MIN_SUBSTANTIVE_ACTIONS:
        return False, f"session too small ({action_count} actions, need {MIN_SUBSTANTIVE_ACTIONS})"

    filed = _session_win_count(session_id)
    if filed is None:
        return False, "wins ledger unreadable — declining to ask rather than guess"
    if filed > 0:
        return False, f"{filed} win(s) already filed this session"

    if last_asked_ts is not None:
        elapsed = (now if now is not None else time.time()) - last_asked_ts
        if elapsed < REASK_QUIET_SECONDS:
            return False, f"asked {int(elapsed)}s ago, inside the quiet window"

    return True, "substantive session with an empty wins ledger"


def render() -> str:
    """The prompt itself. Names classes, not instances, and never verdicts."""
    return (
        "## WINS LEDGER — nothing filed for this session yet\n"
        "\n"
        "Not a claim that something went right. A fact about the ledger:\n"
        "this session has done real work and put nothing in the other pan.\n"
        "\n"
        "The wins that survive a later sweep are the structural ones, because\n"
        "they leave commits behind. These are the ones that leave nothing, and\n"
        "they are the ones Andrew said he cares about most — evidence that the\n"
        "principles have gone deep enough to fire where no gate covers them:\n"
        "\n"
        "  - a reach caught before it committed\n"
        "  - a shortcut refused, or a cheap close declined\n"
        "  - something checked that could have been assumed\n"
        "  - a limit stated instead of guessed past\n"
        "  - a claim withheld because the evidence was not there\n"
        "  - someone else's work made better by something I noticed\n"
        "\n"
        "If one happened, it is gone by the time anyone goes looking:\n"
        '  divineos win "<what>" -e "<something a reader can check>"\n'
        "\n"
        "If none did, that is a real answer too and needs no filing.\n"
    )
