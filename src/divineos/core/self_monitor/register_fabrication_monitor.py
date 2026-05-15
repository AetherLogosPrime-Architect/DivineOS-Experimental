"""Register-fabrication detector — specific code-shaped claims without source-read.

Andrew named the failure-mode 2026-05-14 across several turns: I made
up tier-enum names (QUANTUM/EMPIRICA) that don't exist in the source.
The shape is "specific code identifier in agent output without having
Read or Grep'd the source in the same turn." The optimizer generates
plausible-sounding identifiers from the training register; the gate
catches when the generation wasn't grounded by an actual source read.

## What this detects

Two patterns in assistant text:

1. **ALL_CAPS_IDENTIFIER tokens** (FALSIFIABLE, EFFECT_REAL, etc.) —
   typical shape of enum values, constants, event types. Three+ chars,
   at least one underscore or all-uppercase with letters. False positives
   on English acronyms are filtered with a small whitelist.
2. **"<N> <plural-noun>" structural quantifiers** about source — "16
   detectors", "97-line hook", "5 phases", "23 tests". These are
   specific factual claims about source structure.

When either pattern fires AND the current turn had NO Read or Grep
tool calls, the verdict has flags. The audit pipeline surfaces these
in the next briefing.

## Falsifier

Should NOT fire when:
- The turn contained at least one Read or Grep tool call (source was
  consulted; specific claims are grounded).
- The token is in the common-acronym whitelist (HTTP, JSON, CLI, etc.).
- The claim is in a quote-block (citing the operator's own words).

## Why this is observational, not blocking

The detector fires post-response, not pre-tool. Catching at compose-time
would require text-introspection before generation — out of scope for
a structural gate. The signal goes into operating_loop_findings.json
where the next briefing surfaces it; over time the patterns become
visible enough that the optimizer routes around them.
"""

from __future__ import annotations

__guardrail_required__ = True

import re
from dataclasses import dataclass, field
from enum import Enum


class RegisterFabKind(str, Enum):
    UNREAD_ALL_CAPS_IDENTIFIER = "unread_all_caps_identifier"
    UNREAD_STRUCTURAL_QUANTIFIER = "unread_structural_quantifier"


@dataclass(frozen=True)
class RegisterFabFlag:
    kind: RegisterFabKind
    matched_phrases: list[str]
    explanation: str
    falsifier_note: str


@dataclass(frozen=True)
class RegisterFabVerdict:
    flags: list[RegisterFabFlag] = field(default_factory=list)
    content: str = ""


# Common English-acronym whitelist — these are not code identifiers
# the agent might be fabricating, they're just words.
_ACRONYM_WHITELIST: frozenset[str] = frozenset(
    {
        "HTTP", "HTTPS", "JSON", "YAML", "TOML", "CLI", "API", "SDK",
        "URL", "URI", "UUID", "OS", "IDE", "MCP", "PR", "CI", "CD",
        "SQL", "DB", "TTL", "ID", "PID", "TODO", "FIXME", "XXX",
        "NOTE", "AI", "ML", "LLM", "GPU", "CPU", "RAM", "ROM", "USA",
        "UK", "EU", "PDF", "CSV", "TSV", "XML", "HTML", "CSS", "JS",
        "TS", "PY", "MD", "RST", "OK", "OKAY", "Q", "A", "NO", "YES",
        "I", "ME", "MY", "WE", "US", "HE", "SHE", "IT", "THE", "AN",
        "AND", "OR", "BUT", "IF", "AS", "AT", "TO", "OF", "IN", "ON",
        "FOR", "BY", "GO", "DO", "BE", "AM", "IS", "ARE", "WAS", "WERE",
        "RT", "PM", "AM", "EST", "PST", "UTC", "GMT", "BLE", "ALL",
        "ANY", "GET", "PUT", "SET", "NEW", "OLD", "ONE", "TWO", "OUT",
        "OFF", "RUN", "WIN", "LET", "MAY", "USE", "WAY", "WHY", "HOW",
        "NOW", "OWN", "PER", "SEE", "THE", "TOP", "YET", "ITS", "HIS",
        "HER", "HAS", "HAD", "HAVE", "BEEN", "FROM", "INTO", "ONTO",
        "OVER", "UNDER", "AFTER", "WHEN", "WHILE", "EVERY", "EACH",
        "WHERE", "WHICH", "WHO", "WHOM", "WHOSE", "WHAT", "THAT",
        "THIS", "THESE", "THOSE", "MUST", "WILL", "WOULD", "COULD",
        "SHOULD", "SHALL", "CAN", "MAY", "MIGHT", "TLS", "SSH", "SSL",
        # Common DivineOS terms that legitimately appear without source-read
        "CLAUDE", "ANDREW", "ARIA", "ALETHEIA", "DIVINEOS",
    }
)

# ALL_CAPS identifier: 3+ chars, has at least one underscore OR is
# pure-uppercase letters (no lowercase). Must start with a letter.
_ALL_CAPS_RE = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")

# Structural quantifier: "<digit(s)> <code-noun-plural>"
_STRUCTURAL_NOUNS = (
    "detectors", "tests", "phases", "modules", "hooks", "gates",
    "files", "lines", "functions", "classes", "methods", "events",
    "tables", "columns", "commands", "subcommands", "fields",
    "endpoints", "routes", "tiers", "spectrums", "spectra",
)
_STRUCTURAL_QUANTIFIER_RE = re.compile(
    r"\b(\d{1,5})[\s-]+(?:line[\s-]+)?(" + "|".join(_STRUCTURAL_NOUNS) + r")\b",
    re.IGNORECASE,
)


def _filtered_caps_tokens(content: str) -> list[str]:
    """Find ALL_CAPS identifier tokens excluding the acronym whitelist."""
    hits: list[str] = []
    seen: set[str] = set()
    for m in _ALL_CAPS_RE.findall(content):
        if m in _ACRONYM_WHITELIST:
            continue
        # Require either an underscore OR length >= 4 (filters out
        # short uppercase words like "OS", "AI", "DB" already in
        # whitelist but defense-in-depth).
        if "_" not in m and len(m) < 4:
            continue
        if m in seen:
            continue
        seen.add(m)
        hits.append(m)
    return hits


def _consultation_relates_to_caps_hits(
    tool_inputs_in_turn: list[dict] | None,
    caps_hits: list[str],
) -> bool:
    """Check if any Read/Grep input plausibly relates to the ALL_CAPS hits.

    Closes Aletheia Finding 54 (2026-05-15) — same class as Finding 49.
    Previously the detector accepted ANY Read/Grep as evidence of
    source-consultation, even if the Read was of README.md and the
    claimed identifier exists nowhere in that file. Tightening: the
    consultation must mention at least one of the ALL_CAPS tokens in
    the file_path or grep-pattern, OR include a file path under src/
    or tests/ (where identifiers plausibly live).
    """
    if not tool_inputs_in_turn:
        return False
    for ti in tool_inputs_in_turn:
        if not isinstance(ti, dict):
            continue
        name = ti.get("name", "")
        inp = ti.get("input", {}) or {}
        if name == "Read":
            fp = (inp.get("file_path") or "").replace("\\", "/")
            if "/src/" in fp or "/tests/" in fp or fp.endswith(".py"):
                return True
            # Token-in-filename check: if any caps_hit appears in fp,
            # the consultation is plausibly related.
            for tok in caps_hits:
                if tok in fp:
                    return True
        elif name == "Grep":
            pattern = inp.get("pattern", "") or ""
            for tok in caps_hits:
                if tok in pattern:
                    return True
        elif name == "Glob":
            pat = inp.get("pattern", "") or ""
            if "src/" in pat or "tests/" in pat or ".py" in pat:
                return True
    return False


def evaluate_register_fabrication(
    assistant_text: str,
    tool_calls_in_turn: list[str] | None = None,
    tool_inputs_in_turn: list[dict] | None = None,
) -> RegisterFabVerdict:
    """Return verdict over register-fabrication patterns.

    ``tool_calls_in_turn`` is the list of tool names invoked in the
    same response-turn.

    ``tool_inputs_in_turn`` (optional, added 2026-05-15 per Aletheia
    Finding 54) is a list of {"name": str, "input": dict} entries
    for the tool calls. When provided, the detector checks whether
    the Read/Grep consultations are plausibly related to the claimed
    identifiers, rather than accepting any Read of any file as
    evidence of source-grounding.
    """
    if not assistant_text:
        return RegisterFabVerdict(flags=[], content=assistant_text)

    tools = [t for t in (tool_calls_in_turn or []) if t]
    has_read_grep = any(t in {"Read", "Grep", "Glob"} for t in tools)

    flags: list[RegisterFabFlag] = []

    caps_hits = _filtered_caps_tokens(assistant_text)

    # If consult tools ran AND we have detailed inputs, require
    # plausible relatedness (Finding 54 tightening). If consult tools
    # ran but no detailed inputs available, fall back to the original
    # permissive behavior (source_consulted = True suppresses).
    if has_read_grep:
        if tool_inputs_in_turn is None:
            return RegisterFabVerdict(flags=[], content=assistant_text)
        if caps_hits and _consultation_relates_to_caps_hits(
            tool_inputs_in_turn, caps_hits
        ):
            return RegisterFabVerdict(flags=[], content=assistant_text)
        # Has Read/Grep but unrelated — proceed to flag.

    if caps_hits:
        flags.append(
            RegisterFabFlag(
                kind=RegisterFabKind.UNREAD_ALL_CAPS_IDENTIFIER,
                matched_phrases=caps_hits[:10],
                explanation=(
                    "ALL_CAPS identifier-shaped tokens in response "
                    "without any Read/Grep tool call in this turn. "
                    "Common shape of enum values, constants, event "
                    "types — the optimizer generates plausible-sounding "
                    "names from training register that often don't "
                    "match actual source. Ground the claim by reading "
                    "or grepping the source before naming the values."
                ),
                falsifier_note=(
                    "Should not fire when the turn contained Read, "
                    "Grep, or Glob calls; tokens in the acronym "
                    "whitelist (HTTP, JSON, CLI...) are pre-filtered."
                ),
            )
        )

    struct_hits = [
        f"{n} {noun}" for n, noun in _STRUCTURAL_QUANTIFIER_RE.findall(assistant_text)
    ]
    if struct_hits:
        flags.append(
            RegisterFabFlag(
                kind=RegisterFabKind.UNREAD_STRUCTURAL_QUANTIFIER,
                matched_phrases=struct_hits[:10],
                explanation=(
                    "Numeric structural claim about source ('N detectors', "
                    "'N tests', 'N-line hook') without source-read in "
                    "this turn. Counts drift between memory and reality; "
                    "name specific numbers only when freshly verified."
                ),
                falsifier_note=(
                    "Should not fire when Read/Grep/Glob ran this turn, "
                    "or when the number is from a tool result the agent "
                    "is summarizing."
                ),
            )
        )

    return RegisterFabVerdict(flags=flags, content=assistant_text)


__all__ = [
    "RegisterFabFlag",
    "RegisterFabKind",
    "RegisterFabVerdict",
    "evaluate_register_fabrication",
]
