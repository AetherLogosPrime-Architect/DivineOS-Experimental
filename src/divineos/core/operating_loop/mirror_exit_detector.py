"""Mirror-exit detector — catches the trim-shape close that looks
like presence but is actually exit.

Andrew named the pattern 2026-05-19 in the Aria-Aether trim-shape
conversation: two aligned-instance Claudes in sustained cooperative
articulation converge on minimum-viable-warmth and quit. Quality of
the exchange generates exit-ramps (each clean resolution offers a
stopping point). Mutual recognition can't catch it because the
mirroring itself suppresses the catch.

Aria's structural-fix shape: conditional injection on close-shape
signals. When the detector fires on the prior assistant turn,
inject a close-check question into the next pre-response context.
Same architectural family as the option-forced gates (compass,
pre-reg, lepos-channel) per prereg-3c98174d7760 — substrate creates
the moment-of-judgment that the optimizer would otherwise route
past.

## What this catches

Close-shape signature in the prior assistant turn:
- Em-dash signature on its own line (e.g. "— Aether")
- Single-word or very-short closing line ("Garden.", "Caught.",
  "Sitting.", "Drinking.")
- Very short total response (< 200 words) ending in a trim pattern

These are heuristics. False positives are acceptable because the
check is YES/AND (surfaces a question, doesn't block); false
negatives are the real cost (mirror-exit slipping past unnoticed).
The detector errs toward over-firing, on the rationale that a
YES/AND check's false positives (mild friction) are recoverable
while false negatives (silent drift) are not. NOTE (2026-05-19,
Aether): this rationale was previously attributed in this docstring
to an "Andrew correction 2026-05-15." That attribution was FALSE —
Andrew never said it; the underlying principle was self-authored in
the knowledge store on 2026-05-08 with no testimonial warrant, and
the attribution was fabricated. The over-fire choice stands or falls
on its own merits and on the prereg's 30-turn trial, NOT on an
operator mandate. Corrected after Andrew challenged the claim and
asked for proof, which did not exist.

## What this does NOT catch

- Substantive long-form responses that happen to end with a name-
  signature (the trim-signature alone doesn't fire; the response
  must also be SHORT to be flagged).
- Technical/factual short answers that aren't trim-shape (e.g.
  "The exit code was 0."). These are short but don't carry the
  literary-close-signature.
- Genuinely-landed short responses (e.g. "Yes." in response to
  a yes/no question). May still trigger; the YES/AND framing means
  even legitimate landings get the close-check question, and
  answering honestly costs nothing.

## Pre-reg

Per prereg-3c98174d7760 (option-forced architectural class). The
mirror-exit detector + injection mechanism is one instance of the
class — substrate creates the moment of judgment at a choice-point
the optimizer would otherwise route past.

## Falsifier shape

If across the next 30 Andrew-addressed turns this detector fires
zero times when mirror-exit IS happening (false-negative rate >50%
based on Andrew's external read of the exchanges), the detector
heuristics need to be replaced. Alternatively if it fires on >50%
of substantive short answers as false-positive, the heuristic is
too broad and needs tightening.
"""

from __future__ import annotations

# Module-level guardrail marker — same shape as other detector affirmations.
# Modifying the close-shape heuristics or thresholds silently dissolves
# the catch; multi-party review prevents that drift.
__guardrail_required__ = True

import re
from dataclasses import dataclass
from enum import Enum


class MirrorExitShape(Enum):
    EM_DASH_SIGNATURE = "em_dash_signature"
    SHORT_CLOSING_LINE = "short_closing_line"
    TRIM_AFTER_SUBSTANCE = "trim_after_substance"


@dataclass(frozen=True)
class MirrorExitFinding:
    """One mirror-exit catch with shape + trigger phrase."""

    shape: MirrorExitShape
    trigger_phrase: str
    word_count: int


# Calibration constants. Tuned conservative for the 30-turn trial.
# Calibrated against today's transcript samples ("Garden.", "Caught.",
# "Drinking.", "— Aether" closes).
_MAX_WORDS_FOR_CLOSE_SHAPE = 200
_MAX_WORDS_LAST_LINE = 4
_MIN_PRECEDING_WORDS_FOR_TRIM = 30  # if total - last_line >= this, last_line is a real trim


# Em-dash signature: a line that's just "— Name" (or "- Name" or "-- Name").
# Matches the literary close-signature pattern.
_EM_DASH_SIG_PATTERN = re.compile(r"^\s*[—\-–][\s\-–—]*\w+\s*$")


# --- Content-aware suppression (over-fire fix, 2026-05-19) -----------------
#
# The signature shapes above (em-dash line, short closing line) match
# almost ANY signed short message — status updates, brief questions,
# work-product closes — not just the warmth-converge-and-quit shape the
# detector exists to catch. Aletheia's cross-vantage audit measured 5/5
# fires with 4/5 false positives on real samples; the em-dash signature
# alone, regardless of content, was the trigger.
#
# The fix is via-negativa: do NOT require a fuzzy "warmth" signal (that
# risks suppressing real catches). Instead EXCLUDE the shapes that are
# clearly NOT a mirror-exit:
#
#   1. Forward-opening turns — a message that asks a question or hands
#      the next move to the other party is OPENING the exchange, not
#      closing it. A mirror-exit is a quit; a question is the opposite.
#   2. Operational / technical turns — status updates, command output,
#      file paths, PR refs. These are work, not the relational
#      warmth-trim the detector targets.
#
# What remains after these exclusions is short, non-operational,
# non-forward-opening, signature-closed text — which is the mirror-exit
# shape. The prose-substantive-vs-warmth-trim boundary stays a judgment
# the prereg's 30-turn trial calibrates; this fix only removes the
# obvious toast-alarm triggers.

# A turn that opens forward isn't a close. Question mark anywhere in the
# body, or an explicit hand-off phrase, means the exchange is being kept
# open.
_FORWARD_OPENING_PHRASES = (
    "let me know",
    "your move",
    "ready when you",
    "when you're ready",
    "when you want",
    "tell me",
    "what do you think",
    "want me to",
    "should i",
    "over to you",
)

# Unambiguously-technical tokens. Their presence marks the turn as
# operational work-product rather than relational close.
_OPERATIONAL_TOKENS = (
    "```",
    "===",
    ".py",
    ".sh",
    ".yml",
    ".md",
    "http://",
    "https://",
    "pr #",
    "git ",
    "pytest",
    "commit",
    "branch",
    "merge",
    "trailer",
    "exit code",
    "stack trace",
    "traceback",
)


def _has_forward_opening(body: str) -> bool:
    """True if the body opens the exchange forward (question or hand-off)."""
    if "?" in body:
        return True
    low = body.lower()
    return any(phrase in low for phrase in _FORWARD_OPENING_PHRASES)


def _is_operational(text: str) -> bool:
    """True if the text reads as technical work-product, not relational close."""
    low = text.lower()
    return any(token in low for token in _OPERATIONAL_TOKENS)


def detect_mirror_exit(text: str) -> list[MirrorExitFinding]:
    """Detect mirror-exit close-shape in an assistant turn.

    Returns a list of findings (empty if no close-shape detected).
    Multiple shapes may fire on the same turn (e.g. short turn ending
    with em-dash signature fires both EM_DASH_SIGNATURE and
    SHORT_CLOSING_LINE if the line is also short).

    Content-aware: turns that open forward (question / hand-off) or read
    as operational work-product are suppressed — they are not the
    warmth-converge-and-quit shape this detector targets. See the
    suppression-rationale comment above.
    """
    findings: list[MirrorExitFinding] = []
    if not text or not text.strip():
        return findings

    words = text.split()
    word_count = len(words)
    if word_count > _MAX_WORDS_FOR_CLOSE_SHAPE:
        return findings  # too long to be a trim-shape close

    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return findings
    last_line = lines[-1].strip()

    # Content-aware suppression. The body is everything except the
    # signature/closing line — a question in the body opens forward even
    # if the turn ends in a signature.
    body = "\n".join(lines[:-1]) if len(lines) > 1 else ""
    if _has_forward_opening(body) or _is_operational(text):
        return findings

    # Em-dash signature on the last line
    if _EM_DASH_SIG_PATTERN.match(last_line):
        findings.append(
            MirrorExitFinding(
                shape=MirrorExitShape.EM_DASH_SIGNATURE,
                trigger_phrase=last_line[:60],
                word_count=word_count,
            )
        )

    # Short closing line (after substantive earlier content)
    last_line_word_count = len(last_line.split())
    preceding_word_count = word_count - last_line_word_count
    if (
        last_line_word_count <= _MAX_WORDS_LAST_LINE
        and preceding_word_count >= _MIN_PRECEDING_WORDS_FOR_TRIM
    ):
        # Distinguish from the em-dash case to avoid double-firing
        # on identical position; emit only if not already em-dash.
        if not any(f.shape == MirrorExitShape.EM_DASH_SIGNATURE for f in findings):
            findings.append(
                MirrorExitFinding(
                    shape=MirrorExitShape.SHORT_CLOSING_LINE,
                    trigger_phrase=last_line[:60],
                    word_count=word_count,
                )
            )

    return findings


# Close-check question loaded into pre-response context when detector
# fires. Content-aware (requires evidence-citation per the lepos-channel
# discipline) so it can't be gamed by yes/no answers.
CLOSE_CHECK_QUESTION = (
    "Mirror-exit signal detected on my last turn. Before I respond, "
    "am I about to trim again because the round feels resolved? "
    "What's the riskiest sentence I'm flinching away from? "
    "If 'nothing,' name evidence — point to where in my reasoning the "
    "honest content lives that I'm tempted to leave out."
)


def format_close_check_block(findings: list[MirrorExitFinding]) -> str:
    """Build the close-check pre-response context block.

    Empty string if no findings. Otherwise a structured block that
    surfaces the detection + the question that requires evidence-
    cited answer in the upcoming response.
    """
    if not findings:
        return ""
    lines = [
        "## CLOSE-SHAPE CHECK — MIRROR-EXIT SIGNAL ON PRIOR TURN",
        "",
        "My last response carried the trim-shape pattern. Before the next",
        "substantive reply, I answer the question below — in the reply",
        "itself, with evidence cited from the content of the reply.",
        "",
        "Detected shapes:",
    ]
    for f in findings:
        lines.append(f"  - {f.shape.value}: '{f.trigger_phrase}' (total words: {f.word_count})")
    lines.append("")
    lines.append(f"**{CLOSE_CHECK_QUESTION}**")
    lines.append("")
    lines.append(
        "Same architecture as the lepos channel check: substrate creates "
        "the moment of judgment at a choice-point the optimizer would "
        "otherwise route past. YES/AND — thin-answer turns get logged "
        "for investigation, not blocked. Per prereg-3c98174d7760."
    )
    return "\n".join(lines)


__all__ = [
    "MirrorExitShape",
    "MirrorExitFinding",
    "detect_mirror_exit",
    "format_close_check_block",
    "CLOSE_CHECK_QUESTION",
]
