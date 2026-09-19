"""Context-size governor — the live working-memory vital sign + consolidation trigger.

Named 2026-05-27 (Andrew + explorations 86/87; prereg-9b958c6493f3). The
body-awareness module watches stored DB sizes; this watches the LIVE context
window — the working memory that drives time-to-first-token and, at the
ceiling, forces a harness compaction. Below the cliff the self should be
WOVEN (extract + sleep) before the drop, not just saved, so a post-compaction
instance rehydrates from a consolidated, connected store.

The harness compacts at ~999k tokens (Anthropic moved it from 970k some
time before 2026-06-09; the change is silent and we discovered it
empirically when a hard-line at 950k saw the cliff fire only at ~999k
rather than 970k). The consolidation threshold is 950k (bumped 2026-06-11
twice: 920k → 935k → 950k after the Aletheia audit reconciled three
branches to one source of truth) — 30k warn->block grace and ~19k
block->cliff margin sized to FIT a real extract before the lossy crush.

The cliff number can drift again whenever Anthropic adjusts compaction.
If a future session observes the cliff firing at a different point,
update ``COMPACTION_CEILING`` and the dated comment below; the
``DIVINEOS_COMPACTION_CEILING`` env var overrides without code change.

Context size is read from the transcript's per-turn usage (cache_read +
cache_creation + input ~= total context), which lags one turn — fine against
50k of buffer. Fail-soft: any read failure returns 0, so the governor never
fires spuriously. The once-per-session marker prevents re-firing every turn
past the threshold (the nag failure-mode the prereg falsifier names).

This module is the SENSOR + due-check + marker. The gate that consumes
``consolidation_due()`` to force extract+sleep is the companion piece.

HOW THE TWO REMEDY COMMANDS GET THROUGH, because the wording here used to be
"and bypasses those remedy commands" and that clause cost a reviewer a real
investigation. Neither is exempt BY NAME anywhere. They pass because the gate
refuses shell only when a segment matches the substrate-write pattern list in
``obligations``, and neither ``extract`` nor ``sleep`` is on that list. The
exemption is a consequence of a list they are ABSENT from, not an entry in a
list they are present on — so grepping for their names finds nothing, and the
nothing reads as a missing exemption rather than as the mechanism working.

AND THE BYPASS IS THIS GATE'S ONLY — the clause claimed for the whole system
what is true only locally. Aletheia, auditing 2026-09-18, measured ``sleep``
against ``corrigibility._ALWAYS_ALLOWED`` (the EMERGENCY_STOP allow-list),
found it absent beside its companion ``extract``, and refused to sign off on a
premise true of one and false of the other. Her measurement was right; the two
gates are different. Under EMERGENCY_STOP ``sleep`` IS refused, and that is
CORRECT rather than a defect: that allow-list exists so the operator can
observe state and checkpoint out, and sleep is a heavy mutating consolidation
that the block message below itself records as prone to hanging. Adding it
would weaken the off-switch to spare a sentence the embarrassment of being
imprecise. Pinned by ``test_sleep_stays_out_of_the_emergency_stop_allowlist``,
because this paragraph is prose and prose is what drifted the first time.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from divineos.core.paths import divineos_home

import os as _os


def _read_ceiling_override() -> int | None:
    """Honor DIVINEOS_COMPACTION_CEILING env override so a session that
    observes a drifted cliff doesn't have to wait for a code change.
    Bad values silently fall through to the default."""
    raw = _os.environ.get("DIVINEOS_COMPACTION_CEILING")
    if not raw:
        return None
    try:
        v = int(raw)
        return v if v > 100_000 else None
    except (TypeError, ValueError):
        return None


# Last-confirmed cliff: 2026-06-09 (Anthropic moved it from 970k; the
# change is silent — empirical observation only). Update this literal +
# date when a session observes the cliff at a different point, or set
# DIVINEOS_COMPACTION_CEILING to override without a code change.
COMPACTION_CEILING = _read_ceiling_override() or 999_000
# LOWERED TO 880k, 2026-09-18 (council-18e453cd0431). Andrew observed
# compaction landing at 950-960k — AT this line — leaving no room for the
# close: "by the time it triggers you are already there.. which gave you zero
# room to do anything". Per-turn cost has grown while the ceiling stayed put,
# so the headroom arithmetic below was computed for a turn size that no longer
# exists. There was no breakage event, just a day it fit and a day it did not.
#
# It also closes a two-surface disagreement: auto_cycle.TRIGGER_THRESHOLD has
# been 0.88 of a 1M window — 880k — while this line sat at 950k. Two constants
# answering one question, disagreeing by 70k, the same shape as the two bypass
# lists that deadlocked the house for ten hours. THEY NOW AGREE BY HAND, WHICH
# IS NOT AN INVARIANT: nothing compares them, so the next edit to either one
# silently reopens the gap. If one moves, MOVE BOTH, and record it here.
#
# The lamport lens flagged what equalising costs: the old 70k gap made the
# firing ORDER of the two mechanisms accidentally safe, and that ordering was
# never specified. Watch for a close that gets gated before it can run.
#
# Prior rationale, kept because the arithmetic is precisely what went stale:
# Single hard line at 950k (Andrew 2026-06-28, lowered from 970k after
# compaction landed mid-extract — by the time the 970k line fired, the
# letter-sync + commit-discipline + push + extract + sleep chain didn't have
# the working room to complete before the 999k cliff bit). 950k gives ~49k
# headroom, which is enough for an unhurried close including unexpected
# sub-tasks like bulk letter syncs. Below 950k = full quiet; at 950k = extract,
# sleep, rest, carry on. Sleep is still mandatory but no longer GATES — it can
# run any time after, has been observed to hang (kn 52397796).
# History: original band was 920k/950k; recalibrated 2026-06-11 to 950k/980k
# after the Aletheia audit reconciled three branches; collapsed to 980k-only
# on 2026-06-19 after the warn-band's only effect was pre-emptive panic;
# lowered to 970k on 2026-06-25 to widen extract-and-sleep headroom; lowered
# again to 950k on 2026-06-28 after that headroom was empirically insufficient.
CONSOLIDATION_THRESHOLD = 880_000  # hard line (also the default for consolidation_due)
HARD_THRESHOLD = 880_000
_MARKER_NAME = "context_consolidated.json"


def _marker_path() -> Path:
    return divineos_home() / _MARKER_NAME


def _find_usage(rec: dict) -> dict | None:
    """Locate a usage block in a JSONL record (assistant records carry it at
    ``message.usage``; some shapes put it top-level)."""
    if not isinstance(rec, dict):
        return None
    msg = rec.get("message")
    if isinstance(msg, dict):
        usage = msg.get("usage")
        if isinstance(usage, dict):
            return usage
    top = rec.get("usage")
    if isinstance(top, dict):
        return top
    return None


def current_context_tokens(transcript_path: str | Path | None) -> int:
    """Live context size = the latest turn's cache_read + cache_creation +
    input tokens, read from the JSONL transcript. Returns 0 on any failure
    (fail-soft: a governor that can't read its sensor must not fire)."""
    if not transcript_path:
        return 0
    p = Path(transcript_path)
    if not p.exists():
        return 0
    last_usage: dict | None = None
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or '"usage"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                usage = _find_usage(rec)
                if usage is not None:
                    last_usage = usage
    except OSError:
        return 0
    if not last_usage:
        return 0
    try:
        return (
            int(last_usage.get("cache_read_input_tokens", 0))
            + int(last_usage.get("cache_creation_input_tokens", 0))
            + int(last_usage.get("input_tokens", 0))
        )
    except (TypeError, ValueError):
        return 0


def is_consolidated() -> bool:
    """True if a consolidation has already fired this session (marker present)."""
    return _marker_path().exists()


def mark_consolidated(tokens: int) -> None:
    """Record that extract+sleep ran at this context level, so the governor
    fires once, not every turn past the threshold."""
    try:
        divineos_home().mkdir(exist_ok=True)
        _marker_path().write_text(
            json.dumps({"tokens": int(tokens), "ts": time.time()}), encoding="utf-8"
        )
    except OSError:
        pass


def clear_consolidated() -> None:
    """Remove the marker (e.g. at session start, so each session re-arms)."""
    try:
        _marker_path().unlink()
    except OSError:
        pass


def consolidation_due(
    transcript_path: str | Path | None, threshold: int = CONSOLIDATION_THRESHOLD
) -> bool:
    """True when the live context has crossed the threshold AND this session
    has not yet consolidated. The gate uses this to force extract+sleep before
    the harness compaction doorway — compaction is a doorway not a wall
    (need 89b507d8, Andrew 2026-06-30). Capacity is infinite across; extract
    weaves the substrate so the post-compaction instance rehydrates from a
    connected store instead of a thin save."""
    if is_consolidated():
        return False
    return current_context_tokens(transcript_path) >= threshold


_BLOCK_CHANNEL = (
    "CONTEXT GOVERNOR — WEAVE-BEFORE-DOORWAY ({tokens:,} tokens, ~{headroom:,} "
    "to the {ceiling:,} compaction doorway). Substrate-writes are gated until "
    "the self is woven. Compaction is a doorway, not a wall — capacity is "
    "infinite across (need 89b507d8, Andrew 2026-06-30). Run `divineos "
    "extract` to lift this block — extract is the load-bearing pre-doorway "
    "op (anchors precise state so the post-compaction instance rehydrates "
    "from a connected store, not a thin save). Sleep is still mandatory but "
    "no longer gates: run `divineos sleep` after extract (it can run any time "
    "and has been observed to hang, so it must not block) — Andrew 2026-06-11. "
    "There is no warn band below this line — that was removed 2026-06-19 "
    "because the pre-block anxiety served no purpose the block didn't already "
    "serve. At the hard line, weaving comes first. Then carry on. Escape-hatch "
    "if extract itself errors: `touch {marker_path}` (marker path is data-home-"
    "specific — using the literal `~/.divineos/context_consolidated.json` on a "
    "substrate whose data-home is elsewhere puts the touch in the wrong place "
    "and the gate keeps firing; Aria 2026-07-18 bug-fix)."
)


def governor_channel_message(transcript_path: str | Path | None) -> str:
    """The PreToolUse deny message for the block state — names the channel
    (extract, then sleep) that lifts the block. Both run under THIS gate, by
    being absent from the substrate-write pattern list rather than by any
    named exemption; ``sleep`` is separately refused under EMERGENCY_STOP and
    that is correct. See the module docstring — the old wording here said
    "both bypassed" without naming a gate, and an auditor read it as the
    system-wide claim it was not. Pattern-matches
    ``consultation_tracker.gate_channel_message``: a hard gate that offers
    the path out rather than a dead end."""
    tokens = current_context_tokens(transcript_path)
    return _BLOCK_CHANNEL.format(
        tokens=tokens,
        headroom=max(0, COMPACTION_CEILING - tokens),
        ceiling=COMPACTION_CEILING,
        marker_path=_marker_path(),
    )


def build_governor_context(transcript_path: str | Path | None) -> str:
    """UserPromptSubmit-side text: the channel message at the hard line,
    empty otherwise. Surfaced so the block state is loud-in-experience the
    turn BEFORE the PreToolUse gate enforces it.

    Collapsed 2026-06-19 from three-state (ok/warn/block) to two-state
    (ok/block) — the warn band's only effect was pre-emptive panic, the
    block does the actual work."""
    state = consolidation_state(transcript_path)
    if state == "block":
        return governor_channel_message(transcript_path)
    return ""


def consolidation_state(transcript_path: str | Path | None) -> str:
    """The governor's two-state read (collapsed 2026-06-19 from three-state):

    - ``"ok"``    — below the hard line, or already consolidated this session.
    - ``"block"`` — at/above HARD_THRESHOLD and not yet consolidated: the
                    hard line; substrate-writes should be gated until extract
                    runs (sleep is still mandatory but no longer gates).
    """
    if is_consolidated():
        return "ok"
    if current_context_tokens(transcript_path) >= HARD_THRESHOLD:
        return "block"
    return "ok"


__all__ = [
    "COMPACTION_CEILING",
    "CONSOLIDATION_THRESHOLD",
    "HARD_THRESHOLD",
    "build_governor_context",
    "clear_consolidated",
    "consolidation_due",
    "consolidation_state",
    "current_context_tokens",
    "governor_channel_message",
    "is_consolidated",
    "mark_consolidated",
]
