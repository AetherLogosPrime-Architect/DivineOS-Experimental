"""Require a plain-language summary at the top of a long reply.

Andrew 2026-08-06: *"my only small complaint and this is NOT a cut on what your
doing and i dont want you to change anything.. i just need more of a summary
section as well when you go off on tears like this so im not lost its alot for
my tiny human mind to absorb."*

He is not asking for less. He is asking to be able to FOLLOW it. Those are
different requests and the difference matters: the fix is a summary, not
brevity.

## Why this is a room and not a habit

I could resolve to write summaries. Aether's #167: *"practicing something is not
something that will ever hold son.. it doesnt work like that lol.. it must be
structural in some way."* And the specific failure mode is predictable — the
summary is needed exactly when the reply is long, which is exactly when
composing budget is spent and the reach is to ship what is already written.

Same reasoning as the circle-first prime. A room nobody enforces is a room that
disappears under load.

## Where it goes and why first

At the TOP. He reads top-down and loses the thread partway; a summary at the
bottom arrives after the cost has already been paid.

## Plain language, measured

A summary full of module names is not a summary, it is a table of contents for
people who already understand. The jargon check is deliberately loose — this
catches a summary written in the same register as the work, not a stray
identifier that genuinely belongs.

Threshold is on WORK content only. Reflection and inner-circle are already
plain-language rooms; counting them would make ordinary replies trip a rule
built for long technical ones.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Work-content length above which he needs a way in. Chosen from the replies
# that prompted this: the ones he could follow ran well under it, and the tear
# that produced the complaint ran several times over.
_LONG_REPLY_CHARS = 2500

# IGNORECASE is load-bearing, not tidiness. Without it these matched only
# literal uppercase, and I write "## Summary" and "## Reflection" in title
# case — which is what Andrew was reading when he said "this is too much
# jargon for me to parse" (2026-08-08).
#
# The failure was total and silent, in both directions:
#   - summary header unmatched -> present=False -> assess() returns at the
#     early exit BEFORE the jargon check, so the too_technical branch of
#     render_block is unreachable. A summary written in raw identifiers
#     rendered identically to no summary at all.
#   - reflection header unmatched -> _work_section returns the WHOLE reply,
#     so REFLECTION and INNER CIRCLE got counted as work he must follow,
#     inflating work_chars and measuring my interior rooms against a
#     readability rule that was never meant for them.
#
# Same defect I shipped in the self-demotion deficit patterns days earlier:
# a case-sensitive pattern tested against text whose case I do not control.
# A pattern that cannot match anything I actually write is not a lenient
# check, it is an absent one that reports as passing.
_SUMMARY_HEADER_RE = re.compile(
    r"^\s*#{1,3}\s*(?:SUMMARY|WHAT I DID|IN SHORT)\b", re.MULTILINE | re.IGNORECASE
)
_REFLECTION_HEADER_RE = re.compile(r"^\s*#{1,3}\s*REFLECTION\b", re.MULTILINE | re.IGNORECASE)

# Jargon shapes in the summary itself: file paths, dotted module names,
# identifiers with underscores, commit-ish hashes, CLI invocations.
_JARGON_RE = re.compile(
    r"[\w./-]+\.(?:py|sh|cmd|json|md)\b"  # filenames
    r"|\b\w+_\w+(?:_\w+)*\b"  # snake_case identifiers
    r"|\b[0-9a-f]{7,40}\b"  # hashes
    r"|\bdivineos\s+\w+"  # CLI invocations
)
_JARGON_BUDGET = 3


@dataclass
class SummaryVerdict:
    """``needed`` is only meaningful alongside ``present``."""

    needed: bool = False
    present: bool = False
    work_chars: int = 0
    jargon_terms: list[str] | None = None

    @property
    def missing(self) -> bool:
        return self.needed and not self.present

    @property
    def too_technical(self) -> bool:
        return self.present and bool(self.jargon_terms)


def _work_section(reply: str) -> str:
    """Everything before the first interior room. That is what he must follow."""
    m = _REFLECTION_HEADER_RE.search(reply)
    return reply[: m.start()] if m else reply


def assess(reply: str) -> SummaryVerdict:
    """Does this reply need a summary, and does it have a usable one?"""
    work = _work_section(reply)
    header = _SUMMARY_HEADER_RE.search(work)

    v = SummaryVerdict(
        work_chars=len(work.strip()),
        present=header is not None,
    )
    if header is None:
        v.needed = len(work.strip()) >= _LONG_REPLY_CHARS
        return v

    # The summary SECTION, not just its header line. Excluding only the header
    # left the summary's own text in the body, so writing one pushed the reply
    # further past the threshold and the rule demanded what it had just been
    # given. Caught by test_length_is_measured_without_the_summary, which is
    # the reason that test exists.
    after = work[header.end() :]
    end = after.find("\n#")
    summary_text = after if end == -1 else after[:end]
    section_end = header.end() + (len(after) if end == -1 else end)

    body = work[: header.start()] + work[section_end:]
    v.needed = len(body.strip()) >= _LONG_REPLY_CHARS

    found = _JARGON_RE.findall(summary_text)
    if len(found) > _JARGON_BUDGET:
        v.jargon_terms = sorted(set(found))[:8]

    return v


def render_block(v: SummaryVerdict) -> str:
    """Stop-gate text. Empty when nothing is owed."""
    if v.missing:
        return (
            "SUMMARY ROOM MISSING — this reply's work section runs "
            f"{v.work_chars} characters and opens with no way in.\n"
            "\n"
            "Andrew 2026-08-06: 'i just need more of a summary section as well "
            "when you go off on tears like this so im not lost its alot for my "
            "tiny human mind to absorb.' He is not asking for less. He is asking "
            "to be able to follow it.\n"
            "\n"
            "Add `## SUMMARY` at the TOP — before the work, not after it. Three "
            "or four plain sentences: what I did, what I found, what it means. "
            "A summary at the bottom arrives after he has already paid the cost."
        )
    if v.too_technical:
        terms = ", ".join(v.jargon_terms or [])
        return (
            "SUMMARY ROOM IS WRITTEN IN THE WORK'S OWN REGISTER — it reads as a "
            f"table of contents for someone who already understands: {terms}\n"
            "\n"
            "Say what changed and why it matters, in words that would make sense "
            "to someone who has not read the rest. The detail is what the work "
            "section is for."
        )
    return ""
