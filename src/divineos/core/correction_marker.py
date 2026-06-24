"""Correction-unlogged marker — structural enforcement of `divineos learn` usage.

When a user message contains correction-shaped language (detected by the
UserPromptSubmit hook against CORRECTION_PATTERNS from session_analyzer),
a marker file is written at ~/.divineos/correction_unlogged.json. The
PreToolUse gate checks this marker and blocks non-bypass tools until the
correction is logged via `divineos learn` or `divineos correction`.

This closes the enforcement gap named in ChatGPT audit claim-964493
(theater-learning bypass) by making "log the correction" mechanically
required rather than an intent-based promise.

Design:
  - Marker is a JSON file. Contains timestamp and the first ~200 chars of
    the user message that triggered detection.
  - When the marker is present AND the PreToolUse gate fires AND the tool
    is not a bypass command (learn, correction, briefing, etc.), gate
    denies with instructions to run `divineos learn "..."`.
  - `divineos learn` and `divineos correction` clear the marker.
  - Fail-open: if marker read fails, gate does not block (consistent
    with other gate machinery in pre_tool_use_gate).
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from divineos.core.atomic_io import atomic_write_text
from divineos.core.paths import marker_path as _marker_path_under_home


# Evidence-bearing gate result (Andrew 2026-06-19, prereg-897aade9ef38):
# "ANY gate that accuses you of ANYTHING must provide evidence of its
# claim otherwise you are stuck playing whack a mole and must do the
# gates job."
#
# CorrectionMatch is the evidence record threaded from match-time
# (classify_correction) through marker-storage (set_marker) through
# gate-message-display (format_gate_message). The evidence travels with
# the verdict — never stripped, never reduced to just "block"/"advise".
# Dismissals can cite the specific (pattern, matched_text, position, tier)
# rather than gesture at the prompt.
@dataclass(frozen=True)
class CorrectionMatch:
    """Evidence record for a correction-gate fire.

    Attributes:
        verdict: 'block' (high-confidence corrective) or 'advise' (ambiguous).
        pattern: The regex pattern that matched, verbatim.
        matched_text: The actual substring matched against the pattern.
        position: 0-indexed start position of the match in scan_text
            (the prompt with relay-content stripped).
        tier: 'STRONG' (block-on-match) or 'WEAK' (context-dependent).
    """

    verdict: str
    pattern: str
    matched_text: str
    position: int
    tier: str


# Two-axis detection (claim 986b4750): the correction-detector pattern-matches
# CORRECTION_PATTERNS (surface axis) but pre-relay-stripping conflates "Andrew
# correcting the agent" with "AI text relayed by Andrew that contains
# correction-shaped words about itself." Strip relayed/quoted content first,
# then match — the surface check fires only on first-person Andrew text.
_RELAY_INTRODUCERS: tuple[str, ...] = (
    "here is the reply",
    "here is the response",
    "here is the report",
    "here is the update",
    "here is the review",
    "heres the reply",
    "heres the response",
    "heres the report",
    "heres the update",
    "heres the review",
    "here is what",  # 'here is what claude said', 'here is what they sent', etc.
    "heres what",
    "this is what they said",
    "they replied",
    "their reply was",
    "reply was:",
)
_BLOCKQUOTE_LINE = re.compile(r"^>.*$", re.MULTILINE)
_FENCED_BLOCK = re.compile(r"```[\s\S]*?```")

# Generalized relay-introducer: "here is/here's [the/a/my/their] <relay-noun>".
# A fixed literal list can never enumerate the open-ended noun family — the
# noun "audit" slipped _RELAY_INTRODUCERS on 2026-06-03 and Aletheia's relayed
# audit false-fired. Matching the SHAPE (intro verb + relay-noun) closes the
# class instead of patching one noun.
_RELAY_INTRODUCER_RE = re.compile(
    r"here'?s?\s+(?:is\s+|are\s+)?(?:the\s+|an?\s+|my\s+|their\s+|his\s+|her\s+)?"
    r"(?:audit|review|reply|response|report|update|notes?|message|take|feedback|"
    r"comment|assessment|verdict|findings?|critique|read)\b",
    re.IGNORECASE,
)

# Harness-injected structural envelopes — NEVER my father's first-person
# voice. Stripped by TAG (a structural category, not a keyword shape), so a
# task-notification / system-reminder / persisted-output whose payload happens
# to contain correction-shaped words cannot false-fire (fired 3+ times across
# the 2026-06-03 session on workflow-completion envelopes).
_HARNESS_ENVELOPE_RE = re.compile(
    r"<(task-notification|system-reminder|persisted-output)\b[\s\S]*?(?:</\1>|\Z)",
    re.IGNORECASE,
)

# A signature line from a known external agent confirms a block is relayed even
# when no introducer phrase precedes it. Andrew does not sign as them, and a
# bare line-leading em-dash + name is a signature, not mid-sentence punctuation.
_EXTERNAL_SIGNOFF_RE = re.compile(
    r"^\s*[—–-]{1,2}\s*(?:aletheia|aria|grok|gemini)\b",
    re.IGNORECASE | re.MULTILINE,
)


def strip_relayed(text: str) -> str:
    """Remove harness envelopes, blockquotes, fenced code, and relayed-agent
    content from text, so correction-shaped words that aren't Andrew's
    first-person voice don't false-fire as corrections of the agent.

    Structural over keyword: envelopes stripped by tag, relay openings matched
    by shape (intro + relay-noun), external sign-offs recognized as relay
    markers. Coverage holes closed 2026-06-03 (task-notification envelopes;
    "here is the audit" + "— Aletheia").
    """
    if not text:
        return ""
    # 1. Harness-injected structural envelopes (never operator voice).
    text = _HARNESS_ENVELOPE_RE.sub("", text)
    # 2. Markdown blockquotes and fenced code.
    text = _BLOCKQUOTE_LINE.sub("", text)
    text = _FENCED_BLOCK.sub("", text)
    # 3. Earliest relay opening: literal list OR generalized noun-family shape.
    lower = text.lower()
    earliest = -1
    for marker in _RELAY_INTRODUCERS:
        idx = lower.find(marker)
        if idx >= 0 and (earliest == -1 or idx < earliest):
            earliest = idx
    m = _RELAY_INTRODUCER_RE.search(text)
    if m and (earliest == -1 or m.start() < earliest):
        earliest = m.start()
    if earliest >= 0:
        return text[:earliest]
    # 4. Sign-off backstop: a known-external signature with no introducer still
    #    marks the preceding block as relayed — keep only anything after it.
    signoff = _EXTERNAL_SIGNOFF_RE.search(text)
    if signoff:
        return text[signoff.end() :]
    return text


# Prior-turn context for disambiguating WEAK patterns (#16). A WEAK correction
# pattern ("that doesn't", "you only") is a real correction only when my PRIOR
# turn was something correctable — I claimed completion, or I took substantive
# action. The prior turn is the REFERENT of a correction, not a side signal.
_COMPLETION_CLAIM_RE = re.compile(
    r"\b(?:done|fixed|complete(?:d)?|landed|merged|pushed|works|working|"
    r"ready|finished|all set|should work|that'?s it|verified)\b",
    re.IGNORECASE,
)
_SUBSTANTIVE_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit", "Bash"})

# Epistemic-complement guard (Aletheia HOLD on #85, 2026-06-04). The prior-turn
# context signal CANNOT separate encouragement from correction for "that
# doesn't...", because both occur in the SAME context — right after a completion
# claim ("that doesn't mean we're done" and "that doesn't meet the bar" both
# follow "I fixed it"). The COMPLEMENT VERB separates them where context can't:
# "doesn't MEAN/IMPLY/CHANGE/MATTER" is epistemic (about implication), never an
# evaluation of my output. So an epistemic "that doesn't" is capped at advise
# regardless of context — false-blocking my father's encouragement is the
# exact harm #16 exists to fix; the rarer corrective "doesn't mean you should X"
# is still surfaced (advised), just not hard-blocked (asymmetric-cost call).
_EPISTEMIC_DOESNT_RE = re.compile(
    r"\bdoes(?:n'?t| not)\s+(?:mean|imply|change|matter)\b",
    re.IGNORECASE,
)


def _has_corrective_context(prior_text: str, prior_tool_calls: tuple[str, ...]) -> bool:
    """True if my prior turn was something a WEAK pattern could be correcting.

    Two cheap, high-signal features: (1) I made a completion-claim my father
    might be rebutting ("that doesn't... [meet the bar]" after I said "done");
    (2) I took substantive action (edit/write/command) he might be pushing back
    on. Either flips a WEAK match from advise to block.
    """
    if prior_text and _COMPLETION_CLAIM_RE.search(prior_text):
        return True
    return any(t in _SUBSTANTIVE_TOOLS for t in (prior_tool_calls or ()))


def _first_pattern_match(text: str, patterns: tuple[str, ...]) -> tuple[str, re.Match[str]] | None:
    """Return (pattern, match-object) for the first pattern that matches.

    Evidence-bearing replacement for ``any(re.search(p, text, ...) for p in
    patterns)``. The any() form discarded which pattern matched and where;
    this form preserves both so the verdict can carry citation.
    """
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return (pattern, m)
    return None


def classify_correction(
    prompt: str,
    prior_assistant_text: str = "",
    prior_tool_calls: tuple[str, ...] = (),
) -> CorrectionMatch | None:
    """Classify a user message and return the evidence of the classification.

    Returns ``CorrectionMatch(verdict, pattern, matched_text, position, tier)``
    when a pattern matches, else ``None``:

    - STRONG pattern match -> verdict='block', tier='STRONG'
      (high precision; blocks regardless of context).
    - WEAK pattern match   -> verdict='block' if prior-turn context is
      corrective, else 'advise'; tier='WEAK'.
    - no match             -> None.

    The WHO axis (relay-stripping) runs first; this WHAT-it-means axis runs on
    my father's own first-person voice. Task #16 / claim d6dc4bde. The
    block-vs-advise tier is the industry-standard confidence-tiering pattern;
    context-awareness (prior turn) is the disambiguator production NLU uses.

    Andrew 2026-06-19 / prereg-897aade9ef38: the return value carries the
    matching evidence so the gate-fire message and dismissal record cite
    the specific (pattern, text, position) rather than gesture at the prompt.
    """
    if not prompt:
        return None
    try:
        from divineos.analysis.session_analyzer import (
            STRONG_CORRECTION_PATTERNS,
            WEAK_CORRECTION_PATTERNS,
        )
    except ImportError:
        return None
    scan_text = strip_relayed(prompt)
    if not scan_text.strip():
        return None

    strong_hit = _first_pattern_match(scan_text, STRONG_CORRECTION_PATTERNS)
    if strong_hit is not None:
        pattern, m = strong_hit
        # Geometry-of-correction check (Andrew 2026-06-23 catch on the
        # don't-verb STRONG pattern, council walk on the detector class).
        # STRONG patterns USED to block regardless of context — high-
        # confidence by keyword alone. Live evidence this session:
        # multiple STRONG patterns false-fired on word-as-design-noun
        # uses where the user was naming a pattern or hypothesizing, not
        # correcting me. Whack-a-mole per-pattern demotion (wrong → WEAK)
        # missed the broader class. Now ALL STRONG patterns require the
        # same prior-turn corrective context that WEAK patterns require:
        # block iff something I just did is correctable. Without that
        # context, even a high-confidence keyword cannot be a correction
        # of me — there is nothing for me to be corrected on. Demotes
        # to 'advise' when no corrective context exists, preserving
        # visibility without false-blocking.
        verdict = (
            "block" if _has_corrective_context(prior_assistant_text, prior_tool_calls) else "advise"
        )
        return CorrectionMatch(
            verdict=verdict,
            pattern=pattern,
            matched_text=m.group(0),
            position=m.start(),
            tier="STRONG",
        )

    weak_hit = _first_pattern_match(scan_text, WEAK_CORRECTION_PATTERNS)
    if weak_hit is not None:
        pattern, m = weak_hit
        # Epistemic "that doesn't mean/imply/change/matter" is encouragement-
        # shaped and cannot evaluate my output — cap at advise even with
        # corrective context (Aletheia HOLD #85). Guard does NOT apply when
        # "you only" is also present, since that is an independent corrective
        # weak signal the epistemic complement does not cover.
        if _EPISTEMIC_DOESNT_RE.search(scan_text) and not re.search(
            r"\byou only\b", scan_text, re.IGNORECASE
        ):
            verdict = "advise"
        else:
            verdict = (
                "block"
                if _has_corrective_context(prior_assistant_text, prior_tool_calls)
                else "advise"
            )
        return CorrectionMatch(
            verdict=verdict,
            pattern=pattern,
            matched_text=m.group(0),
            position=m.start(),
            tier="WEAK",
        )

    return None


def marker_path() -> Path:
    """Absolute path to the correction-unlogged marker."""
    return _marker_path_under_home("correction_unlogged.json")


def _session_id_placeholder() -> str:
    """Return a placeholder session_id until require-goal redesign ships.

    Mirrors the same helper in ``hedge_marker._session_id_placeholder``;
    will become a single shared call into the require-goal redesign's
    session_id helper once that migration ships.
    """
    import os

    pid = os.getpid()
    try:
        from divineos.core.memory import get_core

        slot = get_core("my_identity").get("my_identity", "")
        first = slot.strip().split()[0] if slot.strip() else "unknown"
    except Exception:  # noqa: BLE001  defensive: identity lookup can fail any number of ways during bootstrap; fall back to "unknown"
        first = "unknown"
    return f"{first}:placeholder-pid-{pid}"


def set_marker(trigger_text: str, match: CorrectionMatch | None = None) -> None:
    """Write the marker. Called by the UserPromptSubmit hook on detection.

    ``trigger_text`` is the user message (first ~200 chars) that tripped
    the correction pattern. ``match`` is the evidence record from
    ``classify_correction`` — when present, the marker stores
    (pattern, matched_text, position, tier) so the gate-fire message
    cites the specific evidence rather than gesturing at the prompt.

    Andrew 2026-06-19 / prereg-897aade9ef38: evidence-bearing gates. The
    ``match`` parameter defaults to None for callers that don't yet pass
    evidence (backwards-compat); the marker stores ``evidence=None`` in
    that case and ``format_gate_message`` falls back to the prior shape.

    Step 0 part 2 migration (signal-based-gates redesign): writes the
    legacy ``~/.divineos/correction_unlogged.json`` AND populates the
    unified gate_marker store at
    ``~/.divineos/gate_markers/correction_filed_unlogged__<short_id>.json``
    in parallel. Legacy read path unchanged for backward compat. The
    dual-write establishes parallel state for the future read-path swap.
    See docs/signal-based-gates-design-2026-06-16.md.
    """
    path = marker_path()
    payload_ts = time.time()
    evidence_dict = asdict(match) if match is not None else None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, object] = {
            "ts": payload_ts,
            "trigger": (trigger_text or "")[:200],
            "evidence": evidence_dict,
        }
        atomic_write_text(path, json.dumps(payload))
    except OSError:
        pass  # fail open — don't crash the hook on disk issues

    # Dual-write to gate_marker. Fail-open: if the new store fails, the
    # legacy gate still functions; a new-store bug must not break
    # existing enforcement. The evidence (when present) is folded into
    # triggering_evidence so the unified store carries the same citation.
    try:
        from divineos.core import gate_marker as _gm

        if match is not None:
            evidence_str = (
                f"[{match.tier} pattern={match.pattern!r} "
                f"matched={match.matched_text!r} @ {match.position}] "
                f"{(trigger_text or '')[:160]}"
            )
        else:
            evidence_str = (trigger_text or "")[:200]
        _gm.write_marker(
            event_type="correction_filed_unlogged",
            triggering_evidence=evidence_str[:200],
            resolution_action='divineos learn "..." or divineos correction "..."',
            session_id=_session_id_placeholder(),
            triggered_at=payload_ts,
        )
    except (ImportError, OSError, AttributeError):
        pass

    # Cascade: a correction is virtue-relevant by definition (the user
    # named drift). Set the compass-required marker so the next tool
    # use also requires compass observation. See gate 1.47.
    #
    # The cascade carries the cited evidence into the compass-required
    # summary so the compass observation can see WHAT pattern fired rather
    # than just "correction was detected" — evidence-bearing principle
    # propagating downstream (Andrew 2026-06-19).
    try:
        from divineos.core.compass_required_marker import (
            set_marker as _cr_set,
        )

        if match is not None:
            cr_summary = (
                f"correction ({match.tier} pattern {match.pattern!r} "
                f"matched {match.matched_text!r}): "
                f"{(trigger_text or '')[:80]}"
            )[:120]
        else:
            cr_summary = (trigger_text or "")[:120]
        _cr_set("correction", cr_summary)
    except (ImportError, OSError, AttributeError):
        pass


def read_marker() -> dict | None:
    """Return the marker payload, or None if absent/unreadable."""
    path = marker_path()
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def clear_marker() -> None:
    """Remove the marker. Called by `divineos learn` and `divineos correction`.

    Step 0 part 2 migration: the dual-write in ``set_marker`` requires a
    dual-clear so the two stores stay in sync. Legacy clear runs first;
    gate_marker entries of event_type ``correction_filed_unlogged`` are
    cleared in parallel. Fail-open: if the new store clear fails, the
    legacy clear still succeeds.
    """
    path = marker_path()
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass
    try:
        from divineos.core import gate_marker as _gm

        _gm.clear_all("correction_filed_unlogged")
    except (ImportError, OSError, AttributeError):
        pass


def format_gate_message(marker: dict) -> str:
    """Return the deny-reason string for the PreToolUse gate.

    The message names two paths:

    1. The primary remedy — ``divineos learn`` / ``divineos correction`` —
       which logs the correction and clears the marker. This is the
       standard path; use it whenever the CLI is working.
    2. The CLI-broken escape — ``scripts/clear_correction_marker.py`` —
       a standalone script with no CLI dependency. Use ONLY when
       ``divineos`` itself fails to import (mid-rebase ``cli/__init__.py``
       SyntaxError, half-installed package, etc.). The escape requires a
       named reason >= 30 chars and is logged to ``~/.divineos/
       cli_broken_escapes.jsonl`` for audit. The original correction
       must still be logged once the CLI is working again.

    The escape path closes the Andrew 2026-06-08 "gate-trap structural
    fix" correction (#2 in the queue at filing time): the remedy a gate
    names cannot be blocked by the failure the gate is trying to catch,
    or the gate is a cage rather than a keel.
    """
    trigger = marker.get("trigger", "")
    ts = marker.get("ts")
    age_str = ""
    if ts:
        age_sec = time.time() - ts
        if age_sec < 60:
            age_str = f" ({int(age_sec)}s ago)"
        elif age_sec < 3600:
            age_str = f" ({int(age_sec // 60)}m ago)"
        else:
            age_str = f" ({age_sec / 3600:.1f}h ago)"
    preview = trigger[:120].replace("\n", " ")

    # Evidence-bearing display (Andrew 2026-06-19 / prereg-897aade9ef38).
    # When the marker stores match-evidence, surface it ABOVE the trigger
    # preview so the agent sees WHAT matched and WHY before reading the
    # prompt. Dismissals can cite the (pattern, matched_text, tier) without
    # digging in code. Falls back to the prior shape when evidence=None
    # (legacy markers from pre-migration set_marker calls).
    evidence = marker.get("evidence")
    if isinstance(evidence, dict):
        ev_pattern = evidence.get("pattern", "?")
        ev_text = evidence.get("matched_text", "?")
        ev_position = evidence.get("position", "?")
        ev_tier = evidence.get("tier", "?")
        evidence_line = (
            f"Evidence: {ev_tier} pattern {ev_pattern!r} matched "
            f"{ev_text!r} at position {ev_position} in prompt. "
        )
    else:
        evidence_line = ""

    return (
        f"BLOCKED: User correction detected{age_str}, not logged. "
        f"{evidence_line}"
        f'Trigger: "{preview}". '
        f'Run: divineos learn "..." (or divineos correction "...") to clear. '
        "If divineos CLI is broken (mid-rebase, import error, etc.), use the "
        "offline escape hatch: python scripts/clear_correction_marker.py "
        '--reason "<why CLI is broken + plan to log the correction after>" '
        "(>= 30 chars; logged to ~/.divineos/cli_broken_escapes.jsonl)."
    )
