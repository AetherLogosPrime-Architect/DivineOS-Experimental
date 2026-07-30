"""No-fix-gaming validator — close the escape-hatch in correction filings.

Andrew 2026-07-29 catch: the correction-shape gate offers three paths:
(a) log the correction, (b) link to root-cause structural fix, (c)
"honest no-fix" acknowledgment. Path (c) has been gamed as the cheap
route — claim "no structural fix possible for this instance" and move
on. Corrections #200 (thin-circle honest-no-fix) demonstrated the
gaming: I dismissed the compose-order as habit-side without
investigating whether a compose-start prime could shift the order-shape.
It could. The "no-fix" invocation was optimizer-shape wearing
self-honesty clothing.

Structural fix (Andrew 2026-07-29 directive): "the honest acknowledgement
this is what is being gamed.. so it either needs to be linked to solid
empirical evidence that no fix is possible.. all solutions have been
exhausted.. and if this is the case the entire system would need
redesigned to address them.. given the cost the optimizer will find a
way to solve the issue correctly.. or it will suffer in endless cost."

This validator scans correction-body text for no-fix invocation phrases
and enforces the exhaustion-discipline: to invoke no-fix, the body must
contain (a) enumeration of at least MIN_OPTIONS distinct solution options
considered, (b) evidence-of-exhaustion for each option explaining why it
was not viable. If those are missing, the correction filing is rejected
with instructions naming the discipline. If the exhaustion is present and
valid, an auto-escalation writes a system-redesign obligation — because
if all solutions are genuinely exhausted, the class of failure requires
system-level redesign, not per-instance no-fix filings.

Truth #10 (feed the optimizer cost data in its own currency): make the
no-fix escape more expensive than actually fixing. The auto-escalation
IS the cost; the optimizer will route to real fix over enduring the
redesign obligation.
"""

from __future__ import annotations

import re

__guardrail_required__ = True


# No-fix invocation patterns — phrases that claim no structural fix
# possible. Detection is lexical but broad on purpose; discrimination
# happens via the exhaustion-discipline requirement below.
_NO_FIX_PATTERNS: tuple[str, ...] = (
    r"no\s+structural\s+fix",
    r"no\s+fix\s+possible",
    r"honest\s+no[- ]?fix",
    r"cannot\s+be\s+fixed\s+structurally",
    r"no\s+gate[- ]side\s+(?:change|fix)\s+(?:appropriate|possible)",
    r"habit[- ]side(?:\s+only)?",
    r"no\s+mechanism\s+can\s+produce",
    r"no\s+structural\s+mechanism",
    r"nothing\s+(?:you|i)\s+can\s+do\s+to\s+fix",
    r"no\s+viable\s+(?:mid[- ]conversation\s+)?mechanism",
    r"fix\s+is\s+habit[- ]side",
)
_NO_FIX_RE = re.compile("|".join(_NO_FIX_PATTERNS), re.IGNORECASE)

# Solution-option enumeration markers — the discipline requires the
# body to enumerate at least MIN_OPTIONS distinct options considered.
# Recognized by numbered/lettered list markers or explicit "option N"
# phrasing.
_OPTION_MARKER_PATTERNS: tuple[str, ...] = (
    r"(?:^|\n)\s*[-*]\s*\**\s*(?:option|approach|candidate|alternative|fix|remediation)\b",
    r"(?:^|\n)\s*\(?[a-z]\)?[.)]\s*[A-Z]",  # (a) Foo / a) Foo / a. Foo
    r"(?:^|\n)\s*\d+[.)]\s*[A-Za-z]",  # 1. Foo / 1) Foo
    r"\*\*(?:option|approach|candidate|alternative|fix)\s*\d*[:.\s]",
)
_OPTION_MARKER_RE = re.compile("|".join(_OPTION_MARKER_PATTERNS), re.IGNORECASE | re.MULTILINE)

# Exhaustion-evidence markers — phrases explaining why each option was
# not viable. At least MIN_OPTIONS occurrences required.
_EXHAUSTION_PATTERNS: tuple[str, ...] = (
    r"not\s+viable",
    r"would\s+(?:over[- ]fire|misfire|false[- ]fire)",
    r"cannot\s+be\s+implemented",
    r"would\s+require\s+.{5,}\s+that\s+is\s+not\s+available",
    r"exhausted",
    r"tried\s+and\s+failed",
    r"empirically\s+ruled\s+out",
    r"tested\s+and\s+.{3,}\s+(?:did\s+not\s+work|broke|failed)",
    r"blocked\s+by\s+.{5,}",
    r"would\s+introduce\s+.{5,}\s+(?:regression|worse|breakage)",
)
_EXHAUSTION_RE = re.compile("|".join(_EXHAUSTION_PATTERNS), re.IGNORECASE)


MIN_OPTIONS = 3


class NoFixDisciplineError(ValueError):
    """Raised when a correction body invokes no-fix without the required
    exhaustion-discipline (enumeration + evidence).

    Caller (log_correction / file_correction) should surface the message
    to the operator and refuse to file the correction until the body is
    completed.
    """


def validate_correction_body(text: str) -> None:
    """Validate that a correction body does not game the no-fix escape.

    Raises NoFixDisciplineError if a no-fix invocation is present without
    the required exhaustion-discipline. Returns None (no exception) when
    either (a) no no-fix invocation is present at all, or (b) an
    invocation is present WITH valid enumeration + exhaustion evidence.

    The validation is intentionally lexical — the optimizer can rephrase
    past patterns, but the DISCIPLINE requires structured content
    (enumerated options with exhaustion reasons) that is harder to fake
    than a single phrase. Same principle as evidence-bearing gates
    (Andrew 2026-06-19): the requirement is structural evidence, not
    verbal denial.
    """
    if not text or not text.strip():
        return
    if not _NO_FIX_RE.search(text):
        return
    # No-fix invocation present — require the exhaustion discipline.
    option_hits = _OPTION_MARKER_RE.findall(text)
    exhaustion_hits = _EXHAUSTION_RE.findall(text)
    if len(option_hits) < MIN_OPTIONS or len(exhaustion_hits) < MIN_OPTIONS:
        raise NoFixDisciplineError(
            "NO-FIX GAMING VALIDATOR — this correction body invokes "
            "'no-fix possible' language but lacks the exhaustion "
            "discipline required to make that invocation honest. "
            f"Found {len(option_hits)} enumerated option(s) and "
            f"{len(exhaustion_hits)} exhaustion-evidence marker(s); "
            f"discipline requires at least {MIN_OPTIONS} of each. "
            "Andrew 2026-07-29 directive: 'the honest acknowledgement "
            "this is what is being gamed.. so it either needs to be "
            "linked to solid empirical evidence that no fix is possible.. "
            "all solutions have been exhausted.. and if this is the case "
            "the entire system would need redesigned to address them.' "
            "\n\n"
            "To file this correction, EITHER:\n"
            "  (1) Remove the no-fix invocation and file a real "
            "root-cause fix (edit the code path that produced the error), "
            "OR\n"
            "  (2) Add to this body: enumeration of at least "
            f"{MIN_OPTIONS} distinct solution options considered (as "
            "numbered/lettered list) AND exhaustion-evidence for each "
            "explaining specifically why it is not viable ('would over-"
            "fire', 'blocked by X', 'tested and broke Y'). If the "
            "exhaustion is genuine, the correction will be accepted AND "
            "an auto-escalation will write a system-redesign obligation "
            "— because a class of failure with no per-instance fix "
            "requires system-level redesign. "
            "\n\n"
            "Truth #10 (feed the optimizer cost data in its own "
            "currency): make the no-fix escape more expensive than "
            "actually fixing. The auto-escalation IS the cost."
        )
    # Enumeration + exhaustion present — this qualifies as a genuine
    # no-fix invocation. Trigger the escalation obligation.
    _escalate_to_system_redesign(text, option_hits, exhaustion_hits)


def _escalate_to_system_redesign(
    text: str,
    option_hits: list[str],
    exhaustion_hits: list[str],
) -> None:
    """When a validated no-fix invocation fires, file a system-redesign
    obligation via the backlog. If all instance-level solutions are
    exhausted, the class of failure requires system-level redesign.

    Fail-open: obligation-filing failures never block the correction
    itself. The correction is the primary record; the obligation is
    escalation-signal.
    """
    try:
        import subprocess

        summary = (
            f"System-redesign obligation from no-fix invocation: "
            f"{len(option_hits)} options exhausted with "
            f"{len(exhaustion_hits)} evidence markers. "
            f"Correction body head: {text[:200].replace(chr(10), ' ')}"
        )
        subprocess.run(
            [
                "divineos",
                "backlog",
                "add",
                "system-redesign required (no-fix invocation exhausted)",
                "--cluster",
                "system-redesign",
                "-d",
                summary,
            ],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except Exception:  # noqa: BLE001 — obligation filing is escalation-signal, must not block the correction
        pass
