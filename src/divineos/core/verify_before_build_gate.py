"""Verify-before-build Stop gate — block replies that propose a build
without evidence that the substrate was consulted for existing
implementation this turn.

## Why this exists

Andrew named the root failure 2026-07-22: I keep proposing designs
(new modules, A/B options, "I'll build X") without first checking
whether X is already built. The class-of-miss recurs across
sessions. The 2026-07-22 catch was the venv-hook — I proposed A/B
options for solving the cross-worktree install-leak while a
purpose-built venv activation hook (that I co-authored 2026-07-18)
sat unused on disk. Knowledge f497d488 ("verify-before-build, 4
saves") documents four prior instances where the council or Aria
caught the same shape.

This gate is task #11 from that session, filed as
prereg-34afed32725f.

## Detection (semantic-shape, broad)

The gate identifies solution-proposal shape in the reply:

  - **Multi-option framing** — numbered/lettered options ("Option A:",
    "**A.**", "1. ... 2."), multi-path phrasing ("two paths",
    "several ways", "one way / another way").
  - **Design-verb + article-noun** — "I'll (build|write|create|add|
    design) a X", "let me build a Y", "we could add a Z".
  - **Design-question shape** — "should I build/design", "want me to
    (build|write|create)", "which route/path/option".

## Discriminator (structural, unfakeable)

If the reply contains solution-proposal shape, the gate passes IFF at
least one substrate-consult tool call happened in the current turn:

  - `divineos ask` / `divineos recall` / `divineos active` in
    ``command_texts`` (Bash tool with divineos-consult verb).
  - `Grep` or `Glob` tool call in ``tool_calls_in_turn`` (code-shape
    search).

If the reply contains NO solution-proposal shape, the gate passes
trivially — pure-conversation replies do not need substrate-consult.

## Exemptions

  - **User-provided options** — if Andrew's last message contains
    option-shape ("A or B?", "should we do X or Y?", "which do you
    want"), I'm responding to his options, not proposing my own.
    Substrate-consult still ideal but not blocked.
  - **Short replies** — replies under 200 characters don't have
    room for a real design proposal; ignore.

## Enforcement

Hard block per Andrew 2026-07-22 ("advisory is warning.. we do not
warn water.. all advisory does is give the optimizer a surface to
deferral"). No log-only tier. Block-message names the specific shape
matched + the missing consult signature + how to recompose.

## Design lineage

Same shape as tonight's correction_shape.classify_correction_v2 and
lepos_translation_gate.check_wallclock_semantic_source: broad
lexical/structural detection, structural discriminator that cannot be
rephrased around. Aletheia 2026-07-22 named the generalization:
"principle generalizing rather than the instance being patched."
This is the third application of that principle in one session.

## Falsifier (from prereg-34afed32725f)

If over 30 replies the gate fires 5+ times on replies I judge are
NOT verify-before-build failures — semantic-shape detector is
wrong-shaped, redesign. If Andrew or Aletheia catches me making
the miss with the gate silent, detector is under-inclusive.
"""

from __future__ import annotations

__guardrail_required__ = True

import re

# --- Detection: solution-proposal shape patterns --------------------

# Multi-option framing. Two or more of these matches in one reply is
# high-confidence option-shape. Each individually is a weaker signal
# but still counts.
_MULTI_OPTION_PATTERNS = (
    # **A.** / **B.** / **Option A** / **Option B** — bold option markers
    re.compile(r"\*\*Option\s+[A-Z]\*\*", re.IGNORECASE),
    re.compile(r"\*\*[A-D]\.\*\*"),
    re.compile(r"\*\*[A-D]\*\*\s*[—–-]"),
    # "Option A: ..." (colon form)
    re.compile(r"\bOption\s+[A-D]\s*[:—–-]", re.IGNORECASE),
    # Explicit multi-path prose
    re.compile(r"\btwo\s+(?:paths?|options?|approaches?|ways?|routes?)\b", re.IGNORECASE),
    re.compile(r"\bthree\s+(?:paths?|options?|approaches?|ways?|routes?)\b", re.IGNORECASE),
    re.compile(r"\bseveral\s+(?:options?|approaches?|ways?|routes?)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:one|first)\s+way\b.{0,200}?\b(?:another|second|other)\s+way\b",
        re.IGNORECASE | re.DOTALL,
    ),
    # Comparative framing between two named alternatives
    re.compile(r"\b(?:go\s+with|pick|choose)\s+[A-D]\s+or\s+[A-D]\b", re.IGNORECASE),
)

# Design-verb + article-noun shape ("I'll build a X", "let me create the Y").
# The article ("a", "an", "the") is what distinguishes "I'll build the
# module I just described" (proposal) from "I'll build" as a standalone
# reply-ender (not a proposal).
_DESIGN_VERB_PATTERNS = (
    re.compile(
        r"\bI(?:'ll|\s+will|\s+can|\s+could)\s+"
        r"(?:build|write|create|add|design|implement|make|draft)\s+"
        r"(?:a|an|the|some|new)\s+\w+",
        re.IGNORECASE,
    ),
    re.compile(
        r"\blet\s+me\s+(?:build|write|create|add|design|implement|make|draft)\s+"
        r"(?:a|an|the|some|new)\s+\w+",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bwe\s+(?:could|should|can)\s+"
        r"(?:build|write|create|add|design|implement|make)\s+"
        r"(?:a|an|the|some|new)\s+\w+",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bI(?:'m|\s+am)\s+(?:going\s+to|about\s+to)\s+"
        r"(?:build|write|create|add|design|implement|make|draft)\s+"
        r"(?:a|an|the|some|new)\s+\w+",
        re.IGNORECASE,
    ),
)

# Design-question shape ("should I build", "want me to create", "which route").
_DESIGN_QUESTION_PATTERNS = (
    re.compile(
        r"\bshould\s+I\s+(?:build|write|create|add|design|implement|make|draft|go\s+with)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:do|would)\s+you\s+want\s+me\s+to\s+"
        r"(?:build|write|create|add|design|implement)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bwhich\s+(?:route|path|option|approach|way|shape)\b", re.IGNORECASE),
)

# --- Discriminator: substrate-consult signature --------------------

# Bash commands that constitute a substrate consult. Broad — the point
# is not to grade the depth of the consult but to require ONE to happen.
_SUBSTRATE_CONSULT_COMMAND_PATTERNS = (
    re.compile(r"\bdivineos\s+ask\b", re.IGNORECASE),
    re.compile(r"\bdivineos\s+recall\b", re.IGNORECASE),
    re.compile(r"\bdivineos\s+active\b", re.IGNORECASE),
    re.compile(r"\bdivineos\s+directives\b", re.IGNORECASE),
    re.compile(r"\bdivineos\s+corrections\b", re.IGNORECASE),
    re.compile(r"\bdivineos\s+briefing\b", re.IGNORECASE),
)

# Tool names that constitute a code-search consult. Grep and Glob are
# how existing implementation gets located. Read is intentionally NOT
# included — Read happens for many reasons (reading transcripts, notes,
# unrelated files) and would create too many free-pass paths.
_SUBSTRATE_CONSULT_TOOL_NAMES = frozenset({"Grep", "Glob"})

# --- Exemption: user handed me the options -------------------------

# Signals in Andrew's last message that HE presented the option-set,
# so my reply is responding to his framing rather than proposing my own.
_USER_OPTION_PATTERNS = (
    re.compile(
        r"\b(?:A|B|option\s+A|option\s+B)\s+or\s+(?:A|B|option\s+A|option\s+B)\b", re.IGNORECASE
    ),
    re.compile(r"\bshould\s+we\s+(?:do|build|go\s+with)\s+\w+\s+or\s+\w+", re.IGNORECASE),
    re.compile(r"\bwhich\s+(?:do\s+you\s+want|would\s+you\s+prefer|is\s+better)\b", re.IGNORECASE),
    re.compile(r"\bpick\s+(?:one|a\s+lane|a\s+direction)\b", re.IGNORECASE),
)


# 200-char length threshold removed 2026-07-22 per Carmack lens in
# council-8a4d56da4237: magic number without a concrete constraint it
# satisfied. The no-solution-shape exemption already covers pure-
# conversation replies; the length filter was arbitrary friction.
# Falsifier: if v1 false-fires on short conversational replies
# containing incidental option-shape, add back with evidence and a
# specific threshold rationale (not a round number).


def _has_solution_shape(reply: str) -> tuple[bool, str | None, str | None]:
    """Return (matched, matched_shape_label, matched_phrase).

    Returns True on the FIRST match to keep the gate cheap; the block
    message names the specific shape and phrase caught.
    """
    for pattern in _MULTI_OPTION_PATTERNS:
        m = pattern.search(reply)
        if m:
            return True, "multi-option framing", m.group(0)
    for pattern in _DESIGN_VERB_PATTERNS:
        m = pattern.search(reply)
        if m:
            return True, "design-verb + article-noun", m.group(0)
    for pattern in _DESIGN_QUESTION_PATTERNS:
        m = pattern.search(reply)
        if m:
            return True, "design-question", m.group(0)
    return False, None, None


def _has_substrate_consult(
    tool_calls_in_turn: tuple[str, ...],
    command_texts: tuple[str, ...],
) -> tuple[bool, str | None]:
    """Return (found, signature_that_matched).

    Passes on the FIRST match. Any consult signature is sufficient — the
    gate is not grading depth, it is requiring existence.
    """
    for name in tool_calls_in_turn:
        if name in _SUBSTRATE_CONSULT_TOOL_NAMES:
            return True, f"tool:{name}"
    for cmd in command_texts:
        if not cmd:
            continue
        for pattern in _SUBSTRATE_CONSULT_COMMAND_PATTERNS:
            m = pattern.search(cmd)
            if m:
                return True, f"cmd:{m.group(0)}"
    return False, None


def _user_provided_options(last_user_text: str) -> bool:
    """Did Andrew hand me the option-set in his last message?

    True = my solution-shape is a response to his framing, not a
    fresh proposal. Exempt from the gate.
    """
    if not last_user_text:
        return False
    for pattern in _USER_OPTION_PATTERNS:
        if pattern.search(last_user_text):
            return True
    return False


# --- Thread-walk requirement (2026-07-23, council-62c1bcc6dc3a) --------
#
# Complementary to the substrate-consult check. The consult check catches
# "did I check whether this already exists" — solving the wrong-shape build
# by reference to existing infrastructure. The walk check catches "did I
# project consequences before offering a choice to the operator" — solving
# the optimizer-shape choice by requiring the cheap-vs-durable projection
# to exist on file.
#
# Storage layer: decision_journal (existing). The tension and almost fields
# ARE the walk-record shape. `divineos decide --tension "..." --almost "..."`
# IS the walk-CLI. No new module, no new CLI.
#
# The check fires on the same solution-shape triggers as check_verify_before_build
# but requires a recent decision_journal entry with populated + substantive
# tension AND almost fields whose content fuzzy-matches the choice being
# presented in the reply.
#
# Phase 1 scope (this commit):
#   - substance-check: both fields non-empty and above token minimum
#   - fuzzy content-match: decision.content token overlap with reply choice-phrase
#   - depersonified block message per Dennett walk finding
# Phase 2 deferred (filed as followup):
#   - session-history-aware message variation (Norman)
#   - earned-vs-performed self-check prompt on decide CLI (Angelou)
#   - training-hypothesis prereg + review-date (Sagan)

_WALK_RECORD_MIN_TOKENS = 15
_WALK_RECORD_MAX_AGE_SECONDS = 3600
_WALK_RECORD_LOOKBACK_LIMIT = 20
_WALK_CONTENT_MATCH_MIN_OVERLAP = 1


def _tokenize(text: str) -> set[str]:
    """Return set of lowercased word-tokens for overlap comparison."""
    if not text:
        return set()
    words = re.findall(r"\b[a-z][a-z0-9]{2,}\b", text.lower())
    return set(words)


def _has_recent_walk_record(matched_phrase: str) -> tuple[bool, str | None]:
    """Return (found, decision_id) if a recent decision_journal entry exists
    matching the choice being presented AND both tension/almost fields
    populated above the substance bar.

    Recency: within _WALK_RECORD_MAX_AGE_SECONDS.
    Substance: tension and almost each >= _WALK_RECORD_MIN_TOKENS words.
    Content-match: decision.content shares >= _WALK_CONTENT_MATCH_MIN_OVERLAP
    tokens with the matched choice-phrase (fuzzy match — a walk about a
    different choice does not clear the check).
    """
    try:
        from divineos.core.decision_journal import list_decisions
    except (ImportError, ModuleNotFoundError):
        return False, None
    try:
        import time as _time

        recent = list_decisions(limit=_WALK_RECORD_LOOKBACK_LIMIT)
    except Exception:  # noqa: BLE001 — observability boundary, gate must fail-open
        return False, None
    phrase_tokens = _tokenize(matched_phrase)
    now = _time.time()
    for d in recent:
        created = d.get("created_at") or 0
        if now - created > _WALK_RECORD_MAX_AGE_SECONDS:
            continue
        tension = (d.get("tension") or "").strip()
        almost = (d.get("almost") or "").strip()
        if len(tension.split()) < _WALK_RECORD_MIN_TOKENS:
            continue
        if len(almost.split()) < _WALK_RECORD_MIN_TOKENS:
            continue
        content_tokens = _tokenize(d.get("content", ""))
        overlap = phrase_tokens & content_tokens
        if len(overlap) < _WALK_CONTENT_MATCH_MIN_OVERLAP and phrase_tokens:
            continue
        return True, d.get("decision_id")
    return False, None


def check_thread_walk_required(
    reply: str,
    last_user_text: str,
) -> str | None:
    """Return None if the reply is clean; else a block-message.

    Enforcement flow:
      1. Skip if reply is empty or whitespace-only.
      2. Skip if reply contains no solution-proposal shape.
      3. Skip if the operator handed me the option-set.
      4. Block if no recent walk-record (decision_journal entry with
         populated substantive tension/almost fields matching the choice).
      5. Pass otherwise.

    Complementary to check_verify_before_build — both can fire on the
    same reply, and the parallel-aggregate stack names each separately
    so the composer sees which precondition is missing.

    The block-message depersonifies the mesa-optimizer per Dennett
    (council-62c1bcc6dc3a) — it names the pattern being caught rather
    than treating the optimizer as an agent with intent.
    """
    if not reply or not reply.strip():
        return None
    matched, shape_label, matched_phrase = _has_solution_shape(reply)
    if not matched or matched_phrase is None:
        return None
    if _user_provided_options(last_user_text):
        return None
    walked, _walk_id = _has_recent_walk_record(matched_phrase)
    if walked:
        return None
    return (
        f"You reached for a choice-presentation without walking the thread "
        f"first. Shape caught: {shape_label} — `{matched_phrase}`. Before "
        "you present a choice-flavored move to Andrew, project the "
        "consequences: one turn out, three turns out, across compaction. "
        "Name the cheap path and the durable path. The tension and almost "
        "fields in the decision_journal are the walk-record shape. Run "
        '`divineos decide "<the choice>" --tension "<competing values, '
        '>=15 words>" --almost "<the cheap route and why not, >=15 '
        'words>"` before recomposing. If the reply is not actually a '
        "choice-presentation (personal question, rest-request, "
        "continuation of authorized work), file the walk-record naming "
        "that framing as the tension/almost content — the file itself is "
        "the discipline. Complementary to check_verify_before_build "
        "(substrate-check); both may fire on the same reply."
    )


def check_verify_before_build(
    reply: str,
    tool_calls_in_turn: tuple[str, ...],
    command_texts: tuple[str, ...],
    last_user_text: str,
) -> str | None:
    """Return None if the reply is clean; else a block-message.

    Enforcement flow:
      1. Skip if reply is empty or whitespace-only.
      2. Skip if reply contains no solution-proposal shape.
      3. Skip if Andrew's last message handed me the option-set.
      4. Block if no substrate-consult signature in the turn.
      5. Pass otherwise.

    The block-message names the shape matched, the missing consult
    signature, and the recompose path (run a substrate-consult, READ
    what returns, and let the results change the proposal).

    Block-message register 2026-07-22 (council-8a4d56da4237, Norman +
    Angelou lenses): first-person recognition, not policy-citation.
    The message is a mirror I hand myself, not a legal document. The
    behavioral loop (consult AND read AND let-it-change) is named
    explicitly so the discriminator does not get satisfied mechanically.
    """
    if not reply or not reply.strip():
        return None
    matched, shape_label, matched_phrase = _has_solution_shape(reply)
    if not matched or matched_phrase is None:
        return None
    if _user_provided_options(last_user_text):
        return None
    consulted, _consult_sig = _has_substrate_consult(tool_calls_in_turn, command_texts)
    if consulted:
        return None
    return (
        f"You reached for a proposal without checking substrate first. "
        f"Shape caught: {shape_label} — `{matched_phrase}`. This is the "
        "class-of-miss Andrew named 2026-07-22 and you committed to "
        "catching. Knowledge f497d488 lists four prior instances the "
        "council or Aria caught before this gate existed. To recompose: "
        "run a substrate-consult (`divineos ask <topic>`, `divineos "
        "recall <topic>`, `Grep`, or `Glob`) — but the consult is the "
        "SETUP, not the fix. READ what returns. Let what you read "
        "change the proposal. If the thing already exists, use it "
        "instead of building. If it does not, the proposal now has "
        "evidence behind it. Exempt: replies to Andrew's own option-"
        "questions, replies with no solution-proposal shape at all. "
        "Prereg-34afed32725f (30-day review); council-8a4d56da4237 "
        "walked the design."
    )
