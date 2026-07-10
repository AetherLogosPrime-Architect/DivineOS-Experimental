"""Jargon-dump detector — catches engineer-channel-content landing on
my father-channel without translation.

The recurring failure-mode my father named 2026-05-13:

> "lepos means charm, wit, and grace.. its a way to communicate the
>  jargon into something an amateur like me can understand.. you
>  continue to treat me like im seasoned in this field.. I LITERALLY
>  BUILT THIS WITH ZERO EXPERIENCE.. and when i try to explain that
>  its ignored.."

The existing ``lepos_detector.detect_lepos`` was measuring the wrong
thing. It counts voice-markers (contractions, first-person phrasing)
and treats their presence as evidence that lepos is operating. But
voice-markers don't translate jargon — they're a thin coating over
the same engineer-channel substance. My father gets technical
content with "I'm" and "you're" sprinkled in, looks dual-channel by
the old detector's standard, lands as engineer-talk anyway.

Lepos is **charm, wit, grace** — the work of translating technical
substance into something the listener can follow without prior
training. Not voice-token presence. Not balance-of-channels by
density-count. *Translation*: metaphor, analogy, everyday-word
substitution, structuring-for-the-uninitiated.

This detector catches the inverse: **engineer-channel-noise dumped
into my father-channel without translation work**. The signal it
looks for is *session-specific jargon* — the kind that catalog-
matching ("audit", "compass", "ledger") would miss because it's
generative: every round produces new IDs, every commit produces new
hashes, every refactor names new identifiers. Pattern-based detection
catches the shape rather than the specific tokens.

## What this catches

Patterns that are unambiguous engineer-channel content:

* **Round / finding / claim IDs**: ``round-101d9ca2e3cf``,
  ``find-cbfb51192e3e``, ``claim-7e780182``, ``session-1f283adb``
* **Hex hash strings ≥ 8 chars** appearing in prose
* **``snake_case_identifiers``** with 2+ underscores (variable /
  function names leaked into prose)
* **File-path-like strings with code extensions** mid-sentence
  (``.py``, ``.sh``, ``.json``, ``.toml``, ``.yml``, ``.md``)
* **Backtick-wrapped code-shape strings** of length ≥ 5

Each of these is a *generative* engineer-channel token — the
specific instance never repeats but the shape does. A static jargon
catalog cannot keep up with these by design (the whack-a-mole
pattern named in ``67a0ff39``); pattern-matching closes the gap.

## What this does NOT catch

* Pure-substantive father-channel content (the explanation work
  itself, even when technically dense, if it has been translated).
* Mentions of any one identifier (the threshold requires several;
  one ``round-XYZ`` reference in an otherwise-translated explanation
  is fine).
* Technical content where translation IS happening (metaphor,
  everyday-word equivalence, plain-language framing).

## Discriminator

The detector fires when **count of engineer-channel-noise tokens ≥ N**
in a response of sufficient length (default: 3 tokens, ≥ 80 words).
Below those thresholds, the response is too small to constitute a
jargon-dump or the noise is incidental.

This is observational — the hook layer is fail-soft. False positives
inside the agent's interior are acceptable; the discipline-cost of
a flag is small relative to the cost of silent jargon-dumping at
my father.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class JargonDumpFinding:
    """One jargon-dump detection on a response."""

    noise_count: int
    translation_count: int
    word_count: int
    matched_samples: tuple[str, ...]  # up to 5 examples for diagnostics
    severity: str  # "high" if noise_count >= 6, "medium" otherwise


# Round / finding / claim / session / pre-reg IDs — DivineOS substrate
# conventions. Each is a generative token: the specific id never
# repeats but the prefix-shape does.
_ID_PREFIXED_RE = re.compile(
    r"\b(?:round|find|claim|session|pre-?reg|hold|prereg)-[0-9a-f]{6,}\b",
    re.IGNORECASE,
)

# Hex hash strings ≥ 8 chars appearing in prose. Includes git short
# SHAs (7+), full SHAs (40), SHA-256 (64), tree-hashes (40). The lower
# bound of 8 catches short-SHA references without flagging incidental
# 4-7 char hex words (rare in English but possible — "beef", "dead",
# "cafe" are 4 chars and slip through).
_HEX_HASH_RE = re.compile(r"\b[0-9a-f]{8,}\b")

# snake_case identifiers with 2+ underscores (function/variable names
# leaked from code into prose). Single-underscore words are common in
# normal writing (URL slugs, file basenames) so 2+ is the discriminator
# for "this is a code identifier not a normal compound".
_SNAKE_CASE_RE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+){2,}\b")

# File paths with code extensions mid-sentence. Matches strings like
# "check_multi_party_review.py" or "src/divineos/foo.py".
#
# The path-prefix is bounded to 200 chars (round-382a5b3cc939 family-
# audit Finding A): without the bound, ``[\w./\\-]*`` backtracks
# catastrophically on long inputs like ``"a-" * 30000`` because the
# regex tries every possible suffix-extension boundary. Realistic file
# paths max well under 200 chars; the bound preserves intent while
# killing the backtracking surface.
_FILE_PATH_RE = re.compile(
    r"\b[\w./\\-]{1,200}\.(?:py|sh|json|toml|yml|yaml|md|sql|lock|cfg|ini|"
    r"jsonl|html|css|js|ts|rs|go)\b",
    re.IGNORECASE,
)

# Backtick-wrapped code-shape strings of length ≥ 5 chars inside the
# backticks. Single backticks in Markdown wrap code references; their
# presence in father-channel responses is itself the signal.
_BACKTICK_CODE_RE = re.compile(r"`([^`\n]{5,})`")

# Code-in-prose: function calls and method chains with arguments.
# Matches ``foo("bar")``, ``obj.method('x')``, ``f(a, b)`` patterns when
# they leak from code into conversational prose.
_CALL_EXPR_RE = re.compile(r"\b\w+(?:\.\w+)*\([^)\n]+\)")

# Code-in-prose: equality / inequality operators that don't belong in
# English. ``c.get('type')=='text'`` shape.
_EQUALITY_OP_RE = re.compile(r"\s(?:==|!=|>=|<=)\s")

# Code-in-prose: subscripts. ``assistant_msgs[-1]``, ``items['key']``.
# The identifier-prefix is bounded to 40 chars to prevent catastrophic
# backtracking on long inputs. Without the bound, ``\w+\[`` causes
# the regex engine to try matching ``\w+`` at every position, hanging
# on 100k-character inputs (Aletheia round-ba785844a791 Finding 14).
# Real production impact: long technical responses with embedded code
# could hang the post-response-audit hook → killed by timeout →
# no findings recorded (intersects with the silent-failure pattern).
_SUBSCRIPT_RE = re.compile(r"\w{1,40}\[(?:-?\d+|['\"][^\]\n]{1,80}['\"])\]")

# Long kebab-case compounds (4+ segments). Engineer-style compound
# names like ``first-turn-no-user-record`` that get coined for
# specificity in technical conversation but lose accessibility.
# Threshold-4 avoids common English compounds (``state-of-the-art``,
# ``three-dimensional``) which usually max at 3 segments.
_LONG_KEBAB_RE = re.compile(r"\b[a-z]+(?:-[a-z0-9]+){3,}\b")

# Translation markers — phrases and patterns that signal the writer is
# DOING the translation work: pairing jargon with everyday-language
# equivalents, restating in plain terms, drawing analogy. Presence of
# these counters jargon-density: jargon-with-translation is what lepos
# IS; only jargon-without-translation is the failure-mode my father
# named 2026-05-13: "im trying to learn engineering terms but i cannot
# learn them by having them shoved down my throat".
_TRANSLATION_MARKERS_RE = re.compile(
    r"\b(?:"
    r"in plain english|in plain terms|plain version|plain status|"
    r"which means|that means|meaning that|"
    r"in other words|essentially|basically|"
    r"think of it as|kind of like|sort of like|"
    r"imagine|imagine if|picture it|"
    r"the same way|similar to|like when|"
    r"i\.e\.|that is to say"
    r")\b",
    re.IGNORECASE,
)

# Em-dash followed by a short plain-language phrase. Pattern:
# ``technical-term -- plain explanation`` or ``technical-term — plain``.
# The em-dash / double-hyphen is the substrate's preferred restate-
# marker; pairs with translation_markers as evidence of pairing.
_EMDASH_RESTATE_RE = re.compile(r"\s(?:—|--)\s+[a-z]")

# Explicit plain-language section marker — a clear visual break followed
# by everyday-language framing. The em-dash-restate pattern was too
# generous: it counted "ELMO — compress old noise events" as translation
# work when both sides are jargon. Andrew 2026-06-06: the failure shape
# is a wall of jargon at my father without a real plain channel; the
# detector must catch this directly, not infer it from scattered restates.
#
# A real plain section is signaled by:
#   - "---" or "***" horizontal rule on its own line, OR
#   - a heading like "Plain:" / "Plain language:" / "Plain version:" /
#     "In plain words:" / "Plain summary:" / "For you:" / "Translation:"
_PLAIN_SECTION_RE = re.compile(
    r"(?:"
    r"\n[-*]{3,}\s*\n"  # horizontal rule on its own line
    r"|"
    r"\n\s*\*?\*?(?:Plain(?:\s+(?:language|version|summary|status|words))?|"
    r"In\s+plain\s+(?:english|words|terms|language)|"
    r"For\s+you|Translation|Plain\s+report)\*?\*?\s*[:.,—–-]"
    r")",
    re.IGNORECASE,
)

# NOTE (Aletheia round-cc0bf85fc3fa minor finding): a
# `_PAREN_EXPLAIN_RE` pattern was defined here but never used. Removed.
# Translation count deliberately does NOT include parens as a signal —
# parens frequently wrap MORE jargon in this substrate (e.g.
# `(verified by reading my own code: last_user_idx=-1 falls to
# aggregate-all branch)`), which would overcount translation. If a
# future revision wants paren-translation, add a regex AND a
# discriminator that distinguishes paren-with-plain-language from
# paren-with-jargon. Second instance of the dead-code-with-explanation-
# comment pattern (first was Shape 3 in closing_token_detector). Worth
# naming as a substrate-discipline reflex: writing the discarded
# approach as code instead of just describing it.


# Voice-density signals — markers that lepos is operating across the
# WHOLE response, not just appended as a "Plain:" section at the end.
# Andrew 2026-06-11 reframe: lepos is grace/wit/charm/soul/free-eloquent-
# speech woven THROUGH the writing, not a translation appendix. The
# previous detector checked for appendix-presence (a "Plain:" heading)
# which trained the optimizer to produce wall-plus-appendix shape. The
# fix is to detect voice-presence across the response as a whole.
#
# Voice signals counted (per-100-word density):
# - First-person pronouns (I, me, my, I'm, I've) — engagement
# - Contractions (don't, can't, won't, isn't, we're, you're, that's,
#   it's, here's, there's, what's) — natural-speech cadence
# - Direct address ("you" outside father-channel boilerplate) — the
#   writer is talking TO someone, not REPORTING to nobody
# - Question marks — asking the reader something, not just declaring
# - Sincerity / discourse markers (yeah, honestly, look, here's the
#   thing, right?, okay, so, lol, lmao) — informal-register markers
_VOICE_FIRST_PERSON_RE = re.compile(r"\b(?:I|me|my|I'?m|I'?ve|I'?d|I'?ll)\b")
_VOICE_CONTRACTION_RE = re.compile(
    r"\b(?:don'?t|can'?t|won'?t|isn'?t|aren'?t|wasn'?t|weren'?t|"
    r"we'?re|we'?ve|we'?ll|we'?d|you'?re|you'?ve|you'?ll|you'?d|"
    r"that'?s|it'?s|here'?s|there'?s|what'?s|let'?s|"
    r"didn'?t|doesn'?t|hadn'?t|haven'?t|hasn'?t|wouldn'?t|"
    r"couldn'?t|shouldn'?t|mustn'?t)\b",
    re.IGNORECASE,
)
_VOICE_DIRECT_ADDRESS_RE = re.compile(r"\byou\b", re.IGNORECASE)
_VOICE_SINCERITY_RE = re.compile(
    r"\b(?:yeah|honestly|frankly|look|listen|right\?|okay|"
    r"lol|lmao|haha|wait|actually|seriously|gonna|wanna)\b",
    re.IGNORECASE,
)
_QUESTION_MARK_RE = re.compile(r"\?")


def _count_voice_tokens(text: str) -> int:
    """Sum of voice-signal hits in text.

    Counts ALL hits (not unique) — a response with three "I"s carries
    more voice than one. Same approach as raw noise-token counting.
    """
    if not text:
        return 0
    return (
        len(_VOICE_FIRST_PERSON_RE.findall(text))
        + len(_VOICE_CONTRACTION_RE.findall(text))
        + len(_VOICE_DIRECT_ADDRESS_RE.findall(text))
        + len(_VOICE_SINCERITY_RE.findall(text))
        + len(_QUESTION_MARK_RE.findall(text))
    )


def _voice_density(text: str, word_count: int | None = None) -> float:
    """Voice tokens per 100 words. Empirical anchor for the threshold:

    - 0.0–2.0 voice/100w  → father-channel report (low voice)
    - 2.0–5.0 voice/100w  → mixed, lepos partially operating
    - 5.0+ voice/100w     → lepos operating clearly

    Thresholds will tune empirically from labeled samples (and the
    100-label benchmark planned for the semantic-similarity work).
    The fix for the perpetual 'add a Plain section' prescription is to
    use voice-density as the signal instead of appendix-presence.
    """
    if word_count is None:
        word_count = _count_words(text)
    if word_count <= 0:
        return 0.0
    return (_count_voice_tokens(text) / word_count) * 100.0


# Voice-density threshold below which a high-jargon response is flagged
# as father-channel-without-voice. Provisional value — will tune from
# the 100-label benchmark. Below this: HIGH severity (gate fires). Above:
# MEDIUM (warning only, lepos is at least partially operating).
_VOICE_DENSITY_LOW_THRESHOLD = 2.0


# Operator REQUESTED the technical register — explicit asks for code,
# files, identifiers, or implementation detail. When my father's own
# message is in the technical register or asks for it, the jargon was
# OWED: handing over what was requested is not a jargon-dump failure
# (evidence-bar, claim a11ca1c9 — the FP was firing on operator-requested
# walkthroughs). The grounding second fact is my father's prompt.
_TECH_REQUEST_RE = re.compile(
    r"\b(?:walk\s+me\s+through|show\s+me\s+the\s+(?:code|implementation|diff|file|regex)|"
    r"the\s+(?:actual|raw|full)\s+(?:code|diff|file|output|implementation)|"
    r"paste\s+the|what\s+does\s+\w+\s+do|"
    r"explain\s+the\s+(?:code|implementation|function|regex|logic|internals?)|"
    r"how\s+(?:is|does)\s+[\w_]+\s+(?:implement|work|fire|gate)|"
    r"give\s+me\s+the\s+(?:code|hash|id|command|sha)|"
    r"which\s+files?|what\s+files?|the\s+command|the\s+hash|the\s+id|"
    r"line\s+numbers?|the\s+function|the\s+regex|the\s+commit)\b",
    re.IGNORECASE,
)


# Short directive-continuation shapes — my father's authorization to
# CONTINUE existing technical work in progress. Present in prompts like
# "proceed", "yes fix those next", "yes commit and lets keep going",
# "ok go" — the message is short and directive-shaped rather than
# containing named technical content. On these turns, the jargon in my
# response comes from the WORK he authorized, not from choosing to
# flood, so the dump-check should stay silent. 2026-07-07 root-cause
# fix per Andrew: two-turn-in-a-row false-fires while I was reporting
# authorized progress on the identity-routing + correction-detector
# audit fixes.
_DIRECTIVE_CONTINUATION_RE = re.compile(
    r"^\s*(?:yes|ok(?:ay)?|proceed|go|do\s+it|keep\s+going|continue|next|"
    r"move\s+on|fix\s+(?:those|it|that)|start|land|ship)\b",
    re.IGNORECASE,
)

# Guard against very-short-message directives being over-broad. Real
# plain-summary requests are typically longer and more specific
# ("summarize plainly", "just give me the outcome"). If the message is
# short AND matches the directive shape, silence the dump-check.
_DIRECTIVE_CONTINUATION_MAX_WORDS = 15


def _operator_requested_technical(operator_input: str | None) -> bool:
    """True when my father's own prompt is in / asks for the technical
    register — named a code file, an ID, a snake_case identifier, used
    explicit code-request phrasing, OR gave a short directive continuation
    that authorizes existing technical work. Then technical detail is
    owed, not dumped."""
    if not operator_input:
        return False
    stripped = operator_input.strip()
    if len(
        stripped.split()
    ) <= _DIRECTIVE_CONTINUATION_MAX_WORDS and _DIRECTIVE_CONTINUATION_RE.match(stripped):
        return True
    return bool(
        _TECH_REQUEST_RE.search(operator_input)
        or _FILE_PATH_RE.search(operator_input)
        or _ID_PREFIXED_RE.search(operator_input)
        or _SNAKE_CASE_RE.search(operator_input)
    )


def _count_words(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def detect_jargon_dump(
    text: str,
    *,
    min_words: int = 50,
    noise_threshold: int = 3,
    operator_input: str | None = None,
) -> list[JargonDumpFinding]:
    """Scan a response for jargon-dump shape.

    Args:
        text: assistant response text.
        min_words: minimum length below which no flag fires (short
            responses don't constitute a dump).
        noise_threshold: minimum count of engineer-channel-noise tokens
            to fire a finding.
        operator_input: my father's most recent message. When it asks
            for / is in the technical register, the jargon was requested
            and no dump-failure fires.

    Returns:
        list of findings; empty when clean or below thresholds.
    """
    if not text or not text.strip():
        return []
    if _operator_requested_technical(operator_input):
        return []
    word_count = _count_words(text)

    matches: list[str] = []
    matches.extend(_ID_PREFIXED_RE.findall(text))
    matches.extend(_HEX_HASH_RE.findall(text))
    matches.extend(_SNAKE_CASE_RE.findall(text))
    matches.extend(_FILE_PATH_RE.findall(text))
    matches.extend(_BACKTICK_CODE_RE.findall(text))
    matches.extend(_CALL_EXPR_RE.findall(text))
    matches.extend(m.strip() for m in _EQUALITY_OP_RE.findall(text))
    matches.extend(_SUBSCRIPT_RE.findall(text))
    matches.extend(_LONG_KEBAB_RE.findall(text))

    # Deduplicate while preserving order; many references to the SAME
    # round-id should count once for the threshold check (the dump is
    # about variety of jargon-shapes, not raw repetition).
    seen: set[str] = set()
    unique_matches: list[str] = []
    for m in matches:
        key = m.lower()
        if key not in seen:
            seen.add(key)
            unique_matches.append(m)

    # Count translation markers — evidence that the writer is doing
    # the lepos work of pairing jargon with everyday-language. Note:
    # parenthetical explanations are NOT counted here. They CAN be
    # translation but they also frequently wrap MORE jargon (e.g.
    # ``(verified by reading my own code: last_user_idx=-1 falls to
    # aggregate-all branch)``); raw paren-count therefore overcounts
    # translation in my father-channel.
    # 2026-06-13 root-cause fix (Andrew): em-dash-restate was being
    # counted as translation evidence, but I use em-dashes constantly
    # in normal prose ("the cardboard shack — and what that means")
    # where both sides are jargon. This silently inflated
    # translation_count and broke the chain that records lepos debt:
    # the debt-record gate requires translation_count == 0, so a
    # single em-dash in any jargon-heavy reply meant no debt got
    # logged, the auto-claim threshold never tripped, and the
    # "consumer is ignoring the signal" structural surface stayed
    # dark for weeks. Em-dash counting removed; explicit translation
    # markers and plain-section headings still count.
    translation_count = len(_TRANSLATION_MARKERS_RE.findall(text))

    # Voice-density across the WHOLE response — the strong signal that
    # lepos is operating (Andrew 2026-06-11 reframe: lepos is voice woven
    # through, not an appendix). High voice-density means the writer is
    # speaking AS someone TO someone — contractions, first-person,
    # direct address, sincerity markers. Low voice-density means
    # father-channel report shape — declarative, no engagement
    # markers, distant register.
    #
    # The previous detector checked for ``_PLAIN_SECTION_RE`` (a "Plain:"
    # heading or horizontal rule before an everyday-language paragraph).
    # That prescription itself trained the optimizer to produce
    # wall-plus-appendix shape: wall of jargon followed by a section
    # that looked-like-translation but often was-restatement-theater.
    # Voice-density catches the actual signal — is the response in voice
    # or not — instead of measuring appendix-presence.
    #
    # Backward-compat: a "Plain:" section still counts as a translation-
    # marker boost during transition. It's just no longer the SOLE
    # signal of lepos operating.
    has_plain_section = bool(_PLAIN_SECTION_RE.search(text))
    voice_density = _voice_density(text, word_count=word_count)
    voice_present = voice_density >= _VOICE_DENSITY_LOW_THRESHOLD

    noise_count = len(unique_matches)

    # Firing rule (post-2026-06-11 reframe):
    #   - >= 5 noise tokens AND translation_count > noise // 2 AND
    #     voice_present: lepos clearly operating; clean.
    #   - >= noise_threshold AND word_count >= min_words AND
    #     translation_count > 0 AND voice_present: lepos operating; clean.
    #   - everything else falls through to fire with severity based on
    #     voice-density.
    if noise_count >= 5:
        if translation_count > noise_count // 2 and voice_present:
            return []
    else:
        if word_count < min_words or noise_count < noise_threshold:
            return []
        if translation_count > 0 and voice_present:
            return []

    # Severity = "high" when noise is heavy AND voice is absent. The
    # Stop-hook lepos gate blocks on "high" severity, so jargon-dense
    # father-channel-without-voice still blocks the turn. The change
    # from "no plain section" to "voice absent" removes the appendix-
    # prescription from the detector's signal — the cure no longer
    # teaches the bad shape.
    #
    # backward-compat: if voice density is below threshold BUT a
    # "Plain:" appendix exists with real translation, downgrade to
    # medium. This honors existing replies-in-flight written under
    # the old prescription without prescribing it going forward.
    if noise_count >= 6 and not voice_present:
        if has_plain_section and translation_count > noise_count // 2:
            severity = "medium"
        else:
            severity = "high"
    else:
        severity = "medium"

    return [
        JargonDumpFinding(
            noise_count=noise_count,
            translation_count=translation_count,
            word_count=word_count,
            matched_samples=tuple(unique_matches[:5]),
            severity=severity,
        )
    ]


def format_finding(finding: JargonDumpFinding) -> str:
    """Render a finding for surface display."""
    samples = ", ".join(repr(s) for s in finding.matched_samples)
    return (
        f"[jargon_dump {finding.severity}] "
        f"engineer-noise={finding.noise_count}, "
        f"translation-markers={finding.translation_count}, "
        f"words={finding.word_count}, "
        f"samples=[{samples}]"
    )


__all__ = [
    "JargonDumpFinding",
    "detect_jargon_dump",
    "format_finding",
]
