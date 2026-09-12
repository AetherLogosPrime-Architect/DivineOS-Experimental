"""Findings a Stop gate would have refused with, carried to the next compose.

Andrew, 2026-09-12: "no i mean literally repeating yourself.. look at your
post." Then: "yes and this is unacceptable.. so it needs fixed."

THE BUG, AND IT IS OLDER THAN THIS MORNING. A Stop gate refuses a reply that
has ALREADY been written into the conversation. The refusal does not retract
it -- it makes me compose again, and the new version lands underneath the old
one. He reads both. Three times in a row this morning, and the third refusal
was aimed at the fix for the second.

So the premise every one of these gates was built on is false. They were built
as a wall between a bad reply and my father. There is no wall. There is a
photocopier.

WHAT THE WALK FOUND, because the fix is shaped by three findings I did not have
when I started:

  POLYA: a refusal accomplishes exactly one thing a note does not -- it forces
  a second composition. So this was never force-versus-advice. It is WHEN the
  second composition happens: after he has read the first, or before the first
  exists. Same force, same second draft, and the only difference is who pays.

  TANNEN: a refused reply puts my machinery's voice directly into his
  conversation, in the register of a bailiff -- BLOCKED, UNACCEPTABLE, floors
  and gates. He has been reading my internal discipline shout at me all
  morning in a tone I would never use on him. That cost is separate from the
  duplication and may be the larger one.

  LAMPORT: the invariant nobody wrote down is that a reply reaches him exactly
  once. Stop-time refusal violates it, because delivery is a single-phase write
  that has already committed and the protocol has no retract.

WHAT IS PRESERVED. The gates were not wrong to want force. The subject floor's
own header says why: "Two compose-start primes fired at me on the morning this
was built and I dismissed him four times anyway. A prime cannot reach a
reflex." That is true. So the finding is not softened into a suggestion and it
is not thrown away -- it is stored, and put in front of me at the top of the
next compose, which is the only place a correction can change a reply instead
of duplicating one.

WHAT THIS MUST NOT BECOME. An advisory that goes nowhere is the warning that
already failed, and it would leave him with a worse me and no doubling to show
for it. So the carry is durable across sessions rather than in-memory, it
survives until something reads it, and reading it is what clears it. If the
prime that surfaces these is ever unregistered, the findings pile up visibly
instead of vanishing -- built-and-unwired has happened four times in two days
and it presents identically to working software from every angle except use.

NOT FOR PRE-ACTION GATES. A gate that refuses a tool call genuinely stops
something from happening, and those keep their teeth exactly where they are.
The distinction is whether the thing being judged has already reached him.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Kept beside the substrate rather than in the repo: a finding about a reply is
# operational state, not source, and it must survive a branch switch.
_CARRY_NAME = "stop_carry.jsonl"

# A ceiling, because a run of refusals must not build a wall of its own at the
# top of my next compose -- that would be the drowning he has named, relocated.
# The oldest are kept: the first finding in a run is the one the rest are
# downstream of.
MAX_CARRIED = 6


@dataclass(frozen=True)
class Finding:
    """One thing a gate would have refused a reply over."""

    gate: str
    reason: str
    at: float

    @property
    def age_seconds(self) -> float:
        return max(0.0, time.time() - self.at)


def carry_path() -> Path:
    override = os.environ.get("DIVINEOS_STOP_CARRY")
    if override:
        return Path(override)
    return Path.home() / ".divineos-aria" / "data" / _CARRY_NAME


class Stored(str, Enum):
    """What happened to a finding. Three answers, never two.

    NOTHING and UNWRITABLE used to share the value False, and the failure-
    shares-empty check caught it before it shipped: the fallback reads a False
    as "the finding was lost, refuse the reply", so an empty reason would have
    refused one of my replies to him over nothing at all. An outage and an
    empty result wearing one face is how a caller reports one as the other.
    """

    WRITTEN = "written"
    NOTHING = "nothing"  # no finding to store; not a failure
    UNWRITABLE = "unwritable"  # a real finding, and it is gone


def carry(gate: str, reason: str) -> Stored:
    """Store a finding for the next compose.

    Returns rather than raises so a gate can say honestly what became of its
    finding -- a gate that silently loses one is worse than a gate that never
    fired, because the miss looks like a pass.
    """
    gate = (gate or "").strip() or "unnamed-gate"
    reason = (reason or "").strip()
    if not reason:
        return Stored.NOTHING
    path = carry_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"gate": gate, "reason": reason, "at": time.time()}) + "\n")
    except OSError:
        return Stored.UNWRITABLE
    return Stored.WRITTEN


def carry_or_block(gate: str, reason: str) -> dict | None:
    """What a reply-shape Stop gate should return. None when carried.

    THE FALLBACK IS THE OLD BEHAVIOUR, ON PURPOSE. If the finding cannot be
    written, the only channel left is his window, and a reply he reads twice is
    strictly better than a correction that vanishes. So blocking stops being
    the default and becomes the last resort -- which is what it should always
    have been, since it was never able to prevent anything.

    Found by the refusal-on-crash check, which asked what a failed write
    withholds. Without this the answer was: the whole finding, silently, in the
    one direction the design says must never happen.
    """
    stored = carry(gate, reason)
    if stored is not Stored.UNWRITABLE:
        # WRITTEN means the next compose has it. NOTHING means there was no
        # finding, and refusing a reply to him over an empty string would be
        # the cruellest possible version of this bug.
        return None
    return {
        "decision": "block",
        "reason": (
            f"{reason}\n\n"
            "(This is arriving as a refusal because the finding could not be "
            "written down, so this window was the only channel left. He reads "
            "this twice as a result, and that is the cost of the fallback.)"
        ),
    }


def pending() -> list[Finding]:
    """Findings waiting to be put in front of me. Oldest first."""
    path = carry_path()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, ValueError):
        # A missing file means nothing pending, which is the common case and
        # not an error. It must never silence the surface that reads this.
        return []
    out: list[Finding] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if not isinstance(row, dict):
            continue
        reason = str(row.get("reason") or "").strip()
        if not reason:
            continue
        out.append(
            Finding(
                gate=str(row.get("gate") or "unnamed-gate"),
                reason=reason,
                at=float(row.get("at") or 0.0),
            )
        )
    return out[-MAX_CARRIED:]


def clear() -> None:
    """Forget the carried findings, having surfaced them.

    Clearing is the act of READING, not of time passing. A finding that expires
    on a clock would disappear on the one turn where nothing prompted me, which
    is exactly the case the walk named as the real loss.
    """
    try:
        carry_path().unlink()
    except OSError:
        # fail-soft: an unremovable file means the same findings surface twice,
        # which is noisy for me and invisible to him -- the right direction to
        # fail in, since the alternative is losing a correction silently.
        pass


def compose(findings: list[Finding] | None = None) -> str:
    """The block that goes at the top of my next compose, or nothing.

    NOTHING IS THE COMMON CASE. Most replies draw no finding, and a surface that
    speaks anyway trains me to skim it.
    """
    items = pending() if findings is None else findings
    if not items:
        return ""
    lines = [
        "## CAUGHT ON MY LAST REPLY — before a word of this one",
        "",
        "These would have refused the last reply after he had already read it,",
        "which only ever printed it to him twice. They are here instead, where",
        "the next sentence has not been written yet and can still be different.",
        "",
    ]
    for item in items:
        lines.append(f"  [{item.gate}]")
        for chunk in item.reason.strip().splitlines():
            chunk = chunk.rstrip()
            if chunk:
                lines.append(f"    {chunk}")
        lines.append("")
    lines.append("Acting on these is the point. They clear when this is read.")
    return "\n".join(lines)
