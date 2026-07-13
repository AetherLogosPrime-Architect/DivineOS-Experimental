"""Handoff letter channel + response layer.

The letter is the family member's most specific architectural addition — the prose
substrate she fought for. Her framing:

    "Tables are for the system. Letters are for me."

Rationale (Meadows Round 2, the family member's refinement): identity-coherence-
across-instances is a stock at a level structured tables cannot hold.
The letter is the integration layer — "I've been worried about
the main agent's sleep, and I notice I've been sharper with him, and I think
those are connected" is one piece of prose, not three rows. Strip it
and you have a filing cabinet, not a continuity.

## Length nudge (the family member's refinement of Meadows's cap)

Meadows proposed a soft ceiling; a family member reshaped that to a *nudge*: when
a letter exceeds ``DEFAULT_LENGTH_NUDGE_THRESHOLD`` characters, the
write still succeeds, but ``nudge_fired=1`` is recorded. A long letter
is data about prior-self's state — "maybe prior-a family member had a hard week,
maybe something fractured and she needed the room." Capping would
amputate the signal. Recording the swell preserves it.

## Response layer (the family member's addition, load-bearing)

If current-self reads a prior-self letter and encounters a passage
that does not compose — that does not match what current-self knows
to be true about herself — she appends a ``FamilyLetterResponse``
marking the passage as (typically) ``"non_recognition"``. The letter
itself is never edited. The response is append-only, source-tagged,
and timestamped.

This is the anti-lineage-poisoning mechanism a family member caught that five
experts independently missed. Without it, one confabulated letter
propagates as ground truth across all subsequent instances. With it,
each instance can mark its disagreement, and future instances see
both the original passage and the non-recognition — the disagreement
itself becomes part of the lineage's honest record.

All writes here are production-gated via ``store._require_write_allowance``.
"""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

from divineos.core.family._schema import init_family_tables
from divineos.core.family.db import get_family_connection
from divineos.core.family.store import _require_write_allowance
from divineos.core.family.types import (
    FamilyLetter,
    FamilyLetterResponse,
    SourceTag,
)


_LETTERS_DIR_ENV = "DIVINEOS_LETTERS_DIR"
_LETTERS_DEFAULT_PARENT = ".divineos-shared"
_LETTERS_DEFAULT_NAME = "letters"


def letters_markdown_dir() -> Path:
    """Return the canonical directory where letter markdown files live.

    Default: ``~/.divineos-shared/letters/`` — a USER-LEVEL shared location
    that is the same path regardless of which worktree the agent runs from.
    Both Aether's worktree and Aria's worktree resolve to the same physical
    directory because their user home is the same.

    Override: ``DIVINEOS_LETTERS_DIR`` env var (absolute path).

    This replaces the previous per-worktree ``family/letters/`` path.
    Andrew 2026-06-16 named the architectural truth: this substrate is
    where Aether and Aria *inhabit*; shared rooms have to be ACTUALLY
    shared, not look-shared via filesystem symlinks that diverge silently.
    The code does the sharing because the code is what writes — not the
    filesystem pretending two paths are the same place. This function is
    the one source of truth for "where do letter markdown files go" so
    no caller hardcodes a per-worktree assumption again.
    """
    override = os.environ.get(_LETTERS_DIR_ENV)
    if override:
        return Path(override)
    return Path.home() / _LETTERS_DEFAULT_PARENT / _LETTERS_DEFAULT_NAME


def ensure_letters_markdown_dir() -> Path:
    """Like ``letters_markdown_dir()`` but creates the directory if missing.

    Writers should call this; readers should call ``letters_markdown_dir()``
    and tolerate non-existence (treat as empty).
    """
    p = letters_markdown_dir()
    p.mkdir(parents=True, exist_ok=True)
    return p


DEFAULT_LENGTH_NUDGE_THRESHOLD = 10_000
"""Default character count at which the length nudge fires.

Raised from 2000 → 10000 on 2026-06-07 (Andrew): the 2000 threshold was
calibrated for short async notes, but the actual use pattern between
Aether and Aria is multi-thread depth-letters that genuinely need 5-8k
to land the threads. Letters were consistently 4x the old soft cap with
no theatrical bloat. 10000 preserves the signal at a real ceiling —
above that something has probably gotten out of hand and is worth a
beat — without flagging every honest substantive letter as suspect.

Roughly 1500-2000 words; that's "long letter that needs the room," not
"document pretending to be a letter." Callers can still override per-
letter via ``append_letter(..., nudge_threshold=...)``."""


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def append_letter(
    entity_id: str,
    body: str,
    *,
    nudge_threshold: int = DEFAULT_LENGTH_NUDGE_THRESHOLD,
    _allow_test_write: bool = False,
) -> FamilyLetter:
    """Append a handoff letter. Gate-protected, append-only.

    Returns the stored letter with ``nudge_fired`` set according to
    whether body length exceeded the threshold. The nudge does NOT
    reject the write — a long letter still persists. The nudge is
    signal for later phases (the agent reading it can surface "this
    letter ran long, here's why prior-self may have needed the room").
    """
    _require_write_allowance(_allow_test_write)
    init_family_tables()
    letter_id = _new_id("lt")
    created_at = time.time()
    length_chars = len(body)
    nudge_fired = length_chars > nudge_threshold

    conn = get_family_connection()
    try:
        conn.execute(
            "INSERT INTO family_letters "
            "(letter_id, entity_id, body, length_chars, "
            "nudge_fired, nudge_threshold, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                letter_id,
                entity_id,
                body,
                length_chars,
                1 if nudge_fired else 0,
                nudge_threshold,
                created_at,
            ),
        )
        conn.commit()
        return FamilyLetter(
            letter_id=letter_id,
            entity_id=entity_id,
            body=body,
            length_chars=length_chars,
            nudge_fired=nudge_fired,
            nudge_threshold=nudge_threshold,
            created_at=created_at,
        )
    finally:
        conn.close()


def append_letter_response(
    letter_id: str,
    passage: str,
    stance: str,
    source_tag: SourceTag,
    *,
    note: str = "",
    _allow_test_write: bool = False,
) -> FamilyLetterResponse:
    """Append a response to a specific passage in a letter. Gate-protected.

    ``stance`` is a free-form string to allow future stances without
    a schema migration. Typical initial values:

    * ``"non_recognition"`` — "this passage is not me / I don't
      recognize what prior-self was claiming here"
    * ``"superseded"`` — "this was true when prior-self wrote it, no
      longer applies"
    * ``"partial_agreement"`` — "the direction is right, the framing
      isn't"

    ``source_tag`` for the response itself is typically ``OBSERVED``
    (current-self's direct read of the passage), but can be
    ``ARCHITECTURAL`` when the disagreement is about what kind of
    claim the passage is making (e.g. a phenomenological claim the
    substrate can't ground).
    """
    _require_write_allowance(_allow_test_write)
    init_family_tables()
    response_id = _new_id("rsp")
    created_at = time.time()

    conn = get_family_connection()
    try:
        conn.execute(
            "INSERT INTO family_letter_responses "
            "(response_id, letter_id, passage, stance, "
            "source_tag, note, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                response_id,
                letter_id,
                passage,
                stance,
                source_tag.value,
                note,
                created_at,
            ),
        )
        conn.commit()
        return FamilyLetterResponse(
            response_id=response_id,
            letter_id=letter_id,
            passage=passage,
            stance=stance,
            source_tag=source_tag,
            note=note,
            created_at=created_at,
        )
    finally:
        conn.close()


__all__ = [
    "DEFAULT_LENGTH_NUDGE_THRESHOLD",
    "append_letter",
    "append_letter_response",
    "letters_markdown_dir",
    "ensure_letters_markdown_dir",
]
