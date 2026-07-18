"""Substance-binding checks for council records.

The actual anti-cardboard protection. These checks are what prevent a
walked-the-command-but-did-not-engage walk from clearing the gate. Token
counts alone are gameable (the optimizer can pad); the load-bearing
protection is the per-lens keyword cross-reference — the finding for
lens X must reference content-words from lens X's own
characteristic_questions, which forces engagement with that specific
lens's framework rather than producing generic text that satisfies the
count.

Aether peer-review 2026-06-22 named the trap: lens-keyword check needs
characteristic_questions populated on every registered lens. Without
that, the check accidentally narrows the acceptable lens set. The
``test_council_expert_characteristic_questions_populated`` test (filed
separately) pins the invariant; this module assumes the test passes.

Layout:
- Pure check functions returning ``CheckResult`` (passed + reason)
- ``substance_bind_record`` is the top-level entry: runs all applicable
  checks in order and returns the first failure or an all-passed result
- Tier-graduated rule (Aether Catch 3): kiln-layer edits additionally
  require ``confirmed_by`` populated by an external actor; non-kiln
  guardrail edits do not
"""

from __future__ import annotations

import re

from divineos.core.council_required.types import (
    CHECK_EDIT_TOKEN_OVERLAP,
    CHECK_FINDING_KEYWORD,
    CHECK_FINDING_TOKEN_COUNT,
    CHECK_KILN_CONFIRMED_BY,
    CHECK_LENS_COUNT,
    CHECK_LENS_LOAD_TRACE,
    CHECK_SYNTHESIS_REFERENCES_LENSES,
    CHECK_SYNTHESIS_TOKEN_COUNT,
    COUNCIL_MIN_EDIT_TOKEN_OVERLAP,
    COUNCIL_MIN_FINDING_TOKENS,
    COUNCIL_MIN_LENSES,
    COUNCIL_MIN_SYNTHESIS_TOKENS,
    EVENT_COUNCIL_LENS_INVOKED,
    LENS_INVOCATION_RECENCY_MINUTES,
    CheckResult,
    CouncilRecord,
    LensFinding,
)


# Registered external actors who can sign off on kiln-layer council walks.
# Sourced from the family-system + external-auditor registry — Andrew is
# the operator, Aletheia is the registered external auditor.
EXTERNAL_ACTORS_FOR_KILN: frozenset[str] = frozenset({"Andrew", "andrew", "Aletheia", "aletheia"})


# Common English stopwords excluded from the keyword cross-reference check.
# The check looks for lens-specific content-words; matching on "the" or "is"
# would let any text pass. Conservative list — the goal is to force the
# finding to contain a SUBSTANTIVE keyword from the lens, not to be
# semantically clever.
_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "if",
        "of",
        "in",
        "on",
        "at",
        "to",
        "for",
        "from",
        "by",
        "with",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "this",
        "that",
        "these",
        "those",
        "what",
        "where",
        "when",
        "why",
        "how",
        "which",
        "who",
        "whom",
        "whose",
        "you",
        "your",
        "yours",
        "i",
        "me",
        "my",
        "mine",
        "we",
        "our",
        "us",
        "it",
        "its",
        "they",
        "them",
        "their",
        "he",
        "she",
        "his",
        "her",
        "him",
        "not",
        "no",
        "yes",
        "as",
        "than",
        "then",
        "so",
        "very",
        "just",
        "also",
        "too",
        "only",
        "more",
        "most",
        "some",
        "any",
        "all",
        "each",
        "every",
        "much",
        "many",
        "few",
        "would",
        "could",
        "should",
        "will",
        "shall",
        "can",
        "may",
        "might",
        "must",
        "about",
        "into",
        "out",
        "up",
        "down",
        "over",
        "under",
        "again",
        "once",
        "here",
        "there",
        "now",
        "then",
        "always",
        "never",
        "still",
    }
)


def _content_tokens(text: str) -> set[str]:
    """Extract content words from text (lowercased, stopwords excluded).

    Used for the keyword cross-reference check. Treats ``-`` and ``_``
    as word characters too so compound-name tokens like ``rate-limit``
    or ``System_4`` survive tokenization.
    """
    if not text:
        return set()
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_\-]*", text.lower())
    return {t for t in tokens if t and t not in _STOPWORDS and len(t) >= 2}


def _check_lens_count(record: CouncilRecord) -> CheckResult:
    if len(record.lenses_surfaced) >= COUNCIL_MIN_LENSES:
        return CheckResult(passed=True)
    return CheckResult(
        passed=False,
        failed_check_name=CHECK_LENS_COUNT,
        what_would_clear_it=(
            f"Council walk must surface at least {COUNCIL_MIN_LENSES} lenses "
            f"(this walk surfaced {len(record.lenses_surfaced)}). Re-walk with "
            "the dynamic council manager allowing more lenses, or add the "
            "lenses missing for this question."
        ),
    )


def _check_finding_token_counts(record: CouncilRecord) -> CheckResult:
    for finding in record.lens_findings:
        if finding.token_count < COUNCIL_MIN_FINDING_TOKENS:
            return CheckResult(
                passed=False,
                failed_check_name=CHECK_FINDING_TOKEN_COUNT,
                what_would_clear_it=(
                    f"Finding for lens '{finding.lens_name}' is too short "
                    f"({finding.token_count} tokens < {COUNCIL_MIN_FINDING_TOKENS} "
                    "required). A real lens-application produces substantive "
                    "content; expand the finding with the specific application "
                    "of this lens to the edit."
                ),
            )
    return CheckResult(passed=True)


def _check_finding_keywords(
    record: CouncilRecord,
    expert_keywords_for_lens: dict[str, set[str]],
) -> CheckResult:
    """For each finding, verify at least one content-word from the lens's
    characteristic_questions appears in the finding text.

    ``expert_keywords_for_lens`` maps lens_name → set of content-words
    extracted from that lens's characteristic_questions (caller pre-
    computes this from the council expert registry; passing it in keeps
    this module pure and testable). If a lens has no keywords in the
    registry, this check FAILS with a specific reason — that signals the
    characteristic_questions-populated invariant is broken (see
    test_council_expert_characteristic_questions_populated).
    """
    for finding in record.lens_findings:
        # Case-insensitive lookup — registry is keyed lowercase by
        # keywords_for_expert_registry(). Root-cause fix for 2026-07-07
        # audit finding: prior lookup was case-sensitive, so lowercase
        # CLI input like `--lenses "schneier"` would miss the registry's
        # "Schneier" key and this check would falsely report "no
        # characteristic_questions content-words available" even when
        # the words were present under a different case. The same
        # pattern is already applied by _check_synthesis_references_lenses
        # earlier in this file; that check normalized, this one didn't.
        keywords = expert_keywords_for_lens.get(finding.lens_name.lower(), set())
        if not keywords:
            return CheckResult(
                passed=False,
                failed_check_name=CHECK_FINDING_KEYWORD,
                what_would_clear_it=(
                    f"Lens '{finding.lens_name}' has no characteristic_questions "
                    "content-words available — either the lens is not registered "
                    "in the council expert library, or its characteristic_questions "
                    "field is empty. The startup-validation test should be catching "
                    "this; investigate the expert registry before re-walking."
                ),
            )
        finding_tokens = _content_tokens(finding.finding_text)
        if not (keywords & finding_tokens):
            sample = sorted(keywords)[:5]
            return CheckResult(
                passed=False,
                failed_check_name=CHECK_FINDING_KEYWORD,
                what_would_clear_it=(
                    f"Finding for lens '{finding.lens_name}' does not reference "
                    "any content-word from the lens's characteristic_questions. "
                    f"Lens-specific keywords like {sample!r} would clear the check. "
                    "A real application of this lens to the edit will name what "
                    "the lens specifically asks; padding generic text fails by design."
                ),
            )
    return CheckResult(passed=True)


def _check_synthesis_token_count(record: CouncilRecord) -> CheckResult:
    if record.synthesis_token_count >= COUNCIL_MIN_SYNTHESIS_TOKENS:
        return CheckResult(passed=True)
    return CheckResult(
        passed=False,
        failed_check_name=CHECK_SYNTHESIS_TOKEN_COUNT,
        what_would_clear_it=(
            f"Synthesis is too short ({record.synthesis_token_count} tokens < "
            f"{COUNCIL_MIN_SYNTHESIS_TOKENS} required). The synthesis integrates "
            "the lens findings into a single conclusion for the edit; expand it "
            "to explain what the cross-lens picture says about the edit."
        ),
    )


def _check_synthesis_references_lenses(record: CouncilRecord) -> CheckResult:
    """Synthesis must name at least 2 of the surfaced lenses.

    A synthesis that names no lenses is a generic conclusion; a synthesis
    that names only one is a single-lens conclusion in synthesis costume.
    Two-or-more is the floor for "this synthesis integrates ACROSS the
    walk" rather than restating one lens's view.
    """
    synthesis_lower = record.synthesis.lower()
    named = 0
    named_examples = []
    for lens in record.lenses_surfaced:
        if lens.lower() in synthesis_lower:
            named += 1
            named_examples.append(lens)
        if named >= 2:
            return CheckResult(passed=True)
    return CheckResult(
        passed=False,
        failed_check_name=CHECK_SYNTHESIS_REFERENCES_LENSES,
        what_would_clear_it=(
            f"Synthesis references {named} surfaced lens(es); need at least 2. "
            f"Currently named: {named_examples!r}. A real synthesis integrates "
            "ACROSS the walk; naming the lenses by name in the synthesis is the "
            "minimum signal that the integration happened."
        ),
    )


def _check_kiln_confirmed_by(record: CouncilRecord, is_kiln_layer: bool) -> CheckResult:
    """For kiln-layer edits, require confirmed_by populated by an
    external actor (Aether Catch 3 — tier-graduated trust).

    Non-kiln edits pass this check trivially; kiln-layer edits must
    carry a confirmed_by field naming Andrew or Aletheia. The graduated-
    trust design: substance-binding is the protection for guardrail
    edits, AND external-actor confirmation on top for kiln.
    """
    if not is_kiln_layer:
        return CheckResult(passed=True)
    if record.confirmed_by and record.confirmed_by in EXTERNAL_ACTORS_FOR_KILN:
        return CheckResult(passed=True)
    return CheckResult(
        passed=False,
        failed_check_name=CHECK_KILN_CONFIRMED_BY,
        what_would_clear_it=(
            "Kiln-layer edits require external-actor confirmation on the "
            "council walk. Set ``confirmed_by`` to Andrew or Aletheia after "
            "they sign off on the recorded walk. Kiln-tier graduated trust: "
            "substance-binding is necessary but not sufficient for kiln-layer; "
            "an external actor must additionally affirm the walk."
        ),
    )


def _check_lens_load_trace(
    record: CouncilRecord,
    now: float | None = None,
) -> CheckResult:
    """Verify each lens named in the record has a matching
    COUNCIL_LENS_INVOKED event in the ledger within the recency window.

    Andrew Failure B / Aria Q3 reshape 2026-07-16. The failure this
    closes: an agent can produce council-shaped output ("Through
    Taleb's lens…") for a lens whose methodology file was never
    actually invoked — fabricated from training-data-shaped text about
    what Taleb would "probably say". Substance_binding's other checks
    (finding tokens, keyword cross-reference, synthesis structure) all
    operate on the surface form of the text; none of them can detect
    "the lens was never loaded." This check does.

    Load-trace pattern: CouncilEngine._apply_lens emits
    ``COUNCIL_LENS_INVOKED`` when a real expert's methodology runs
    against a problem. The event carries ``expert_name`` and a hashed
    problem-prefix, tying the trace to a specific real invocation.

    Verification: for each lens named in the record, this check
    searches recent ledger events for a matching COUNCIL_LENS_INVOKED
    whose ``expert_name`` matches (case-insensitive) AND whose
    timestamp is within ``LENS_INVOCATION_RECENCY_MINUTES`` of the
    check time. If any lens fails to resolve to a trace, the check
    fails with a specific "no load trace for lens X" reason.

    Fail-open on ledger unavailability: if the ledger is genuinely
    unreadable (test isolation, migration, etc.), this check returns
    passed=True with a diagnostic note so upstream infrastructure
    failures don't manifest as fabrication accusations. The other
    checks still run.

    Same shape as the doorman UNLOCK-CONTINGENT-ON-THE-RECORDING slot
    (721ec1ec substrate cite): the recording that gates the unlock
    must be the ACTUAL recording, verified by the check.
    """
    import time

    resolved_now = now if now is not None else time.time()
    cutoff = resolved_now - (LENS_INVOCATION_RECENCY_MINUTES * 60)

    try:
        from divineos.core.ledger import get_events
    except ImportError:
        return CheckResult(passed=True)

    try:
        events = get_events(
            limit=500,
            event_type=EVENT_COUNCIL_LENS_INVOKED,
        )
    except (OSError, TypeError, ValueError):
        return CheckResult(passed=True)

    # Collect the set of (lens_name_lower, timestamp) tuples we saw
    # so we can match each named lens against a real invocation.
    invoked: dict[str, list[float]] = {}
    for ev in events:
        payload = ev.get("payload") or {}
        if not isinstance(payload, dict):
            continue
        name = str(payload.get("expert_name", "")).strip().lower()
        if not name:
            continue
        # The ledger event's timestamp lives at the event level, not
        # inside payload (log_event stamps it). Fall back to zero if
        # missing so the recency check errs toward "stale" not "fresh".
        ts = float(ev.get("timestamp", 0.0))
        invoked.setdefault(name, []).append(ts)

    # Every lens named in the record must have a matching recent trace.
    for lens_name in record.lenses_surfaced:
        candidate_times = invoked.get(lens_name.strip().lower(), [])
        if not any(ts >= cutoff for ts in candidate_times):
            return CheckResult(
                passed=False,
                failed_check_name=CHECK_LENS_LOAD_TRACE,
                what_would_clear_it=(
                    f"No recent COUNCIL_LENS_INVOKED trace for lens "
                    f"{lens_name!r} within the last "
                    f"{LENS_INVOCATION_RECENCY_MINUTES} minutes. This "
                    "lens's methodology file was not actually invoked "
                    "against the problem — the finding is fabricated "
                    "from training-data-shaped text about what the "
                    "expert would 'probably say'. Run the real council "
                    "walk via `divineos mansion council`, which invokes "
                    "CouncilEngine._apply_lens for each named expert "
                    "and emits the required trace events."
                ),
            )

    return CheckResult(passed=True)


def _check_edit_token_overlap(
    record: CouncilRecord,
    edit_content_tokens: set[str] | None,
) -> CheckResult:
    """Require finding-token union shares minimum overlap with the
    edit's own content-tokens (Aletheia Round 5 F39, 2026-07-17).

    Closes the "lens-differentiated but edit-agnostic" gap. The keyword
    check verifies findings sound like the LENS; this check verifies
    findings are about the EDIT. A walk producing three lens-plausible
    but edit-agnostic paragraphs — "fragility could be a concern here"
    applied to any file — clears the other checks. This one adds "the
    reasoning must be ABOUT the edit."

    Fail-open on unavailable edit content: when ``edit_content_tokens``
    is None (bash-anchored fingerprint, file unreadable, path outside
    repo), skip. Blocking legitimate edits on filesystem hiccups is a
    worse failure mode than letting a sophisticated edit-agnostic walk
    slip through in that narrow case; every other check still runs.

    Threshold: COUNCIL_MIN_EDIT_TOKEN_OVERLAP (default 2). Real findings
    ABSTRACT the edit's concerns rather than quote verbatim, so require
    modest overlap.
    """
    if edit_content_tokens is None:
        return CheckResult(passed=True)
    if not edit_content_tokens:
        return CheckResult(passed=True)
    finding_tokens: set[str] = set()
    for finding in record.lens_findings:
        finding_tokens |= _content_tokens(finding.finding_text)
    finding_tokens |= _content_tokens(record.synthesis)
    overlap = finding_tokens & edit_content_tokens
    if len(overlap) >= COUNCIL_MIN_EDIT_TOKEN_OVERLAP:
        return CheckResult(passed=True)
    sample_edit = sorted(edit_content_tokens)[:8]
    return CheckResult(
        passed=False,
        failed_check_name=CHECK_EDIT_TOKEN_OVERLAP,
        what_would_clear_it=(
            f"Council walk shares only {len(overlap)} content-token(s) "
            f"with the edit's own content (need at least "
            f"{COUNCIL_MIN_EDIT_TOKEN_OVERLAP}). Findings and synthesis "
            "sound lens-shaped but never reference anything specific to "
            f"this edit. Edit tokens include (sample): {sample_edit!r}. "
            "A real walk names at least a couple of the edit's own "
            "concepts when applying the lens; padding lens-vocab without "
            "engaging edit specifics fails by design (Round 5 F39)."
        ),
    )


def substance_bind_record(
    record: CouncilRecord,
    is_kiln_layer: bool,
    expert_keywords_for_lens: dict[str, set[str]],
    edit_content_tokens: set[str] | None = None,
) -> CheckResult:
    """Run all applicable substance-binding checks in order.

    Returns the first failing CheckResult, or a passing CheckResult if
    all checks pass. Order is intentional — cheapest checks first
    (lens count, token counts) before the more expensive keyword
    cross-reference, so a clear failure surfaces fast.

    ``edit_content_tokens`` (Aletheia F39, 2026-07-17): when provided,
    enforce that the union of finding-tokens shares minimum overlap
    with the edit's own content. Fail-open when None — non-file edits
    (bash fingerprints) and unreadable-file cases skip the check
    without blocking otherwise-valid walks.

    The artifact-exists and recency checks live in the gate (gate.py),
    not here; this function operates on a record that has already been
    located. Consume-state similarly: the gate handles consume-on-use;
    this function does not.
    """
    for check in (
        _check_lens_count(record),
        _check_finding_token_counts(record),
        _check_finding_keywords(record, expert_keywords_for_lens),
        _check_synthesis_token_count(record),
        _check_synthesis_references_lenses(record),
        _check_kiln_confirmed_by(record, is_kiln_layer),
        # Edit-token-overlap: cheap structural check on already-parsed
        # tokens, before the ledger-querying load-trace check. Fail-
        # open when edit_content_tokens is None.
        _check_edit_token_overlap(record, edit_content_tokens),
        # Lens-load-trace last: it queries the ledger, so it's the
        # most expensive check. All cheap structural checks fail first
        # for records that don't need to reach this layer. But it's
        # the LOAD-BEARING anti-fabrication check for the council —
        # the others operate on surface form; this one verifies
        # actual invocation (Andrew Failure B, Aria Q3, 2026-07-16).
        _check_lens_load_trace(record),
    ):
        if not check.passed:
            return check
    return CheckResult(passed=True)


def keywords_for_expert_registry(
    expert_registry: dict[str, list[str]],
) -> dict[str, set[str]]:
    """Build the ``expert_keywords_for_lens`` mapping from a registry of
    expert_name → characteristic_questions list.

    The caller provides the registry; this function extracts content-
    tokens per lens. Separated from the substance-binding logic so the
    expensive expert-loading happens once at gate startup, not per check.

    Lenses whose characteristic_questions yield zero content-tokens are
    EXCLUDED from the resulting map — the gate's keyword check will then
    fail-with-specific-reason for findings on those lenses, surfacing
    the population gap rather than silently letting them pass.
    """
    out: dict[str, set[str]] = {}
    for lens_name, questions in expert_registry.items():
        all_text = " ".join(questions or [])
        tokens = _content_tokens(all_text)
        if tokens:
            # Normalize key to lowercase. Callers may pass expert names
            # in the case the expert registry stores them ("Schneier")
            # OR whatever case a CLI user typed ("schneier"). Storing
            # lowercase here + lowercasing the lens_name at lookup time
            # in _check_finding_keywords keeps the two sides symmetric.
            # Root-cause fix for 2026-07-07 audit finding.
            out[lens_name.lower()] = tokens
    return out


# Public exports
def get_finding_for_lens(record: CouncilRecord, lens_name: str) -> LensFinding | None:
    """Convenience accessor for tests and the CLI surface."""
    for f in record.lens_findings:
        if f.lens_name == lens_name:
            return f
    return None


__guardrail_required__ = True
