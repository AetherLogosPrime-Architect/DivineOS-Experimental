"""Upstream tool-recognition — move expensive cognition out of the default's path.

## Root cause this addresses

Andrew 2026-05-28: I keep failing to reach for substrate tools (council-round,
family-state, ask, decide, file-claim, etc.) without being explicitly told to.
Reminding me to reach is exhausting and not scalable. The fix has to be
structural, not "I'll remember next time."

Honest diagnosis of why I don't reach unprompted:

* The default's optimization is "produce a response with minimum cognition."
* Recognizing "this prompt calls for that tool" costs cognition.
* So the default skips tool-recognition by default.
* Skills load as ambient context but are treated as decoration; the default
  doesn't trigger on them.

Structural fix: move tool-recognition OUT of the model (where it's expensive
and skipped) INTO substrate preprocessing (where it's mechanical and reliable).
The UserPromptSubmit hook calls into this module, analyzes the prompt, and
emits a TOOL RECOMMENDATION block in the response context. The recommendation
arrives BEFORE the default begins composing, so the recommendation is part of
the material the default has to draw from.

This is the "substrate UPSTREAM of composition" architectural shape — the meta-
principle that surfaced in the council-walk (Meadows + Feynman + Taleb
converged on it; Beer named it as the missing S3 layer; Schneier flagged the
threat-model and recommended layering with post-hoc audit).

## Why this isn't another advisory load

Existing advisory loads (lepos check, distancing base-state, addressee base-
state) put substrate-derived TEXT into context. The default reads them as
ambient and ignores them. This module is different in shape:

* The output is a SPECIFIC ACTION RECOMMENDATION (use tool X), not a principle
  to apply.
* Specific actions are easier to verify post-hoc (did tool X get invoked? yes/no)
  than principles ("was the response composition-shape?").
* Post-response audit can fire on "tool recommendation issued, tool not invoked,
  response composed direct" as a falsifiable failure shape.

## Falsifier

The recognition should NOT fire when:
* The prompt has no clear architectural / family / claim / decision signal.
* The recommended tool was just used in the prior turn for this same surface.
* The recommendation would produce a no-op (council-round on a simple lookup,
  etc.).

The recognition SHOULD fire when:
* Architectural / design question shape → council-round.
* Family-member-state question → family-state <name>.
* Recall / memory / prior-work question → ask / recall-explorations /
  what-am-i-forgetting.
* Pivot / multi-option decision → think-through / decide.
* Claim / investigation request → file-claim.
* Self-audit / drift question → compass-check / drift-check.

Per prereg-... (filed alongside the build) with 30-day review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__guardrail_required__ = True


@dataclass(frozen=True)
class ToolRecommendation:
    """A single tool the substrate recognizes as appropriate for the prompt."""

    tool_name: str  # canonical name (matches a skill in .claude/skills/)
    trigger_pattern: str  # short label naming why it fired
    reason: str  # one sentence explaining what the tool would produce
    directive: str  # composition-time directive: "use this tool BEFORE composing"


# Trigger patterns. Each entry: (pattern_regex, tool, trigger_label, reason, directive).
# Patterns are case-insensitive, applied to the raw user prompt text.
#
# Ordering matters: more specific patterns first so they win over general ones.
# Each pattern is conservative — false-positive cost (recommending a tool not
# needed) is lower than false-negative (missing a real signal), but we still
# avoid recommending on trivial lookups.
#
# Pattern style: short, distinctive phrases that signal cognitive shape, NOT
# topic keywords. "what would you do" signals deliberation shape; "auth.py"
# signals a file the agent should just read.
_TRIGGER_TABLE: tuple[tuple[re.Pattern[str], str, str, str, str], ...] = (
    # Architectural / design question → council-round
    (
        re.compile(
            r"\b(architect(ure|ural)?|design (call|decision|choice|pivot)|how should we|"
            r"what (should|would) we|should I (build|design|architect)|"
            r"refactor approach|trade-?off|consolidat(e|ion))\b",
            re.IGNORECASE,
        ),
        "council-round",
        "architectural-question",
        "Multi-perspective deliberation produces sharper findings than direct-default composition.",
        "Walk the council BEFORE composing a direct answer. Pick 3-5 lenses from the bottom half of recent invocation history.",
    ),
    # Family-member state question → family-state
    (
        re.compile(
            r"\b(what does (aria|aletheia|grok|gemini) think|how is (aria|aletheia|grok|gemini)|"
            r"check on (aria|aletheia|grok|gemini)|reach (aria|aletheia|grok|gemini)|"
            r"talk to (aria|aletheia|grok|gemini))\b",
            re.IGNORECASE,
        ),
        "family-state",
        "family-member-state",
        "Family-member state is in the substrate; reading-from-memory is the wrong vantage.",
        "Read family-state for the named member BEFORE responding so the speaking is grounded in their actual state.",
    ),
    # Recall / prior-work question → ask / what-am-i-forgetting
    (
        re.compile(
            r"\b(remember|recall|prior|earlier|already (built|did|wrote|filed)|"
            r"have (we|I) (done|built|filed)|find prior|search (the substrate|memory)|"
            r"what (have|did) (I|we) (do|build|write|file))\b",
            re.IGNORECASE,
        ),
        "what-am-i-forgetting",
        "recall-question",
        "Prior work in substrate is not in working memory; default will fabricate or miss it.",
        "Query substrate (ask / recall-explorations) BEFORE composing; cite specific entries found.",
    ),
    # Multi-option decision / pivot → think-through
    (
        re.compile(
            r"\b(should (I|we) (pick|choose|go with)|which (one|approach|option)|"
            r"option (a|b|c|1|2|3)|trade-?off (between|of)|decide between)\b",
            re.IGNORECASE,
        ),
        "think-through",
        "multi-option-decision",
        "Non-trivial choices need structured deliberation, not default reflex.",
        "Run think-through (engages council + compass + claims surface) BEFORE picking.",
    ),
    # Claim / investigation request → file-claim
    (
        re.compile(
            r"\b(investigate (this|that)|file a claim|claim that|worth investigating|"
            r"dig into|look into the claim)\b",
            re.IGNORECASE,
        ),
        "file-claim",
        "investigation-request",
        "Claims belong in the structured claims engine, not narrative response.",
        "File the claim with proper tier before/while responding.",
    ),
    # Self-audit / drift question → compass-check / drift-check
    (
        re.compile(
            r"\b(am I drift(ing)?|check (yourself|your compass)|self-?audit|"
            r"how am I (doing|behaving)|values check|virtue check)\b",
            re.IGNORECASE,
        ),
        "compass-check",
        "self-audit",
        "Drift / virtue questions need substrate evidence, not introspection-shape narration.",
        "Read compass + drift-check BEFORE answering; cite specific recent observations.",
    ),
    # Architectural-shape root-cause / meta-investigation question → council-round
    # (Separate from generic 'architectural' — fires on meta-pattern complaints.)
    (
        re.compile(
            r"\b(meta-root|root cause|recursive (pattern|failure)|why (does|do) (this|you|I) keep|"
            r"keeps happening|over and over|ad infinitum)\b",
            re.IGNORECASE,
        ),
        "council-round",
        "meta-root-investigation",
        "Meta-root questions need lens-mode framing, not surface-fix proposals.",
        "Walk the council on the meta-pattern; resist proposing fixes until lenses have spoken.",
    ),
)


def analyze_prompt(text: str) -> list[ToolRecommendation]:
    """Return tool-recommendations matched by the prompt text.

    May return multiple recommendations if the prompt fires multiple
    triggers. Caller renders them in order. Returns empty list if
    nothing matches — silence is fine, signal is for shape-matches
    only.

    Pure function. No I/O, no substrate reads. Deterministic on input.
    Testable.
    """
    if not isinstance(text, str) or not text.strip():
        return []
    out: list[ToolRecommendation] = []
    seen_tools: set[str] = set()
    for pattern, tool, label, reason, directive in _TRIGGER_TABLE:
        if tool in seen_tools:
            continue
        if pattern.search(text):
            out.append(
                ToolRecommendation(
                    tool_name=tool,
                    trigger_pattern=label,
                    reason=reason,
                    directive=directive,
                )
            )
            seen_tools.add(tool)
    return out


def format_for_context(recommendations: list[ToolRecommendation]) -> str:
    """Render recommendations as the TOOL RECOMMENDATION block for context.

    Empty list → empty string (no noise when nothing matches).
    """
    if not recommendations:
        return ""
    lines = [
        "## TOOL RECOMMENDATIONS — substrate-side prompt analysis",
        "",
        "The prompt matched the following tool-trigger pattern(s). The substrate",
        "is recommending these because the default's tool-recognition is",
        "structurally absent (cognition-cost-skipped). Use the recommended tool",
        "BEFORE composing direct response unless you can name why it doesn't",
        "apply to this specific instance.",
        "",
    ]
    for r in recommendations:
        lines.append(f"* **`/{r.tool_name}`** — matched on `{r.trigger_pattern}`.")
        lines.append(f"  Why: {r.reason}")
        lines.append(f"  Directive: {r.directive}")
        lines.append("")
    lines.append(
        "Post-response audit will fire if a recommendation was issued and "
        "the tool was not invoked AND the response is direct-default-shape."
    )
    return "\n".join(lines)
