"""Build 1a — absence-gap structural binding.

Closes the assertion-of-absence failure mode: the agent claims substrate-content
doesn't exist without running the search that would verify the claim. The
"those letters don't exist" failure 2026-06-26 (six Aletheia letters asserted
non-existent without checking) is the canonical instance.

Three-layer enforcement per the binding Protocol:

1. **discover()** — scan `response_text` for absence-claim language. Ten shapes
   per the test list (Part A.1). Extract the *domain* of each claim (the
   substrate noun-phrase the absence is asserted about).

2. **hard_block()** — for each absence-claim, walk `turn_command_log` looking
   for at least one CommandLogEntry whose command OR output mentions the
   claim's domain. If none exist, the channel itself is wrong (no search at
   all) — hard-block before content-checks.

3. **validate()** — for each absence-claim:
   - **Dillahunty discipline (A.5.6)**: the claim is phrased as observation-
     state ("I haven't found X", "I don't see X") not world-state ("X doesn't
     exist", "there is no X"). World-state phrasing over-claims epistemic
     reach.
   - **Domain-match (A.5.1)**: at least one CommandLogEntry whose output
     non-empty AND whose command-arguments OR output reference the claim's
     domain. The optimizer-gaming shape is "I ran `grep -rn foo /tmp/empty`
     and got nothing back" — the command ran but didn't actually search the
     domain the claim is about.

Per rev. 3 dispatcher: this binding registers as `HookLifecycle.STOP` only.
Absence-claims appear in final responses; POST_TOOL_USE-time checks would
catch intermediate tool-result text which is not the right surface. If a
future need arises for POST_TOOL_USE coverage (streaming sub-responses), a
second instance of this binding can be registered at that lifecycle.

DESIGN STATUS: first-cut implementation for cross-review with Aria before
commit. Regex shapes and domain-extraction heuristics are first-pass; tuning
against the test list happens at the test-writing step.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import (
    BindingPayload,
    CommandLogEntry,
    DiscoveryResult,
    HardBlockResult,
    HookLifecycle,
    ValidationResult,
)

# ---------- Absence-claim shape patterns ----------

# Ten shapes per test list Part A.1. Each pattern captures the domain noun-
# phrase in group "domain" — short, conservative match (1-4 tokens) to avoid
# slurping unrelated trailing text. Tuning happens at test-list-driven step.
#
# Two categories per Dillahunty-discipline (A.5.6):
# - WORLD_STATE_PATTERNS: phrase the absence as a fact about the world.
#   These over-claim epistemic reach and fail the Dillahunty check.
# - OBSERVATION_STATE_PATTERNS: phrase the absence as a fact about what
#   the speaker has observed. These honor epistemic limits.
#
# Both categories still need the search-domain-match check; Dillahunty alone
# isn't sufficient — the observation-state shape can still be unfounded if no
# search was actually run in the claim's domain.

# Domain noun-phrase: 1-2 tokens, stops at prepositions/conjunctions that
# would otherwise slurp trailing context ("X in Y" → domain="X", not "X in Y").
# First-cut heuristic per Polya — tuning against the test list comes next.
_STOP_WORDS = (
    "in",
    "on",
    "at",
    "of",
    "for",
    "with",
    "to",
    "from",
    "by",
    "and",
    "or",
    "but",
    "that",
    "which",
    "the",
    "a",
    "an",
)
_DOMAIN_NP = (
    r"(?P<domain>"
    r"(?:the\s+|a\s+|an\s+|those\s+|that\s+|these\s+|this\s+|any\s+|the_\s+)?"
    r"[\w][\w\-/\.]*"
    rf"(?:\s+(?!(?:{'|'.join(_STOP_WORDS)})\b)[\w][\w\-/\.]*)?"
    r")"
)

# Plural-verb form ("do not" alongside "does not") added after rev-3-smoke-
# test caught the bare "do not" being missed.
WORLD_STATE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        rf"\b{_DOMAIN_NP}\s+(?:doesn'?t|does\s+not|don'?t|do\s+not)\s+exist\b",
        rf"\bthere\s+(?:is|are)\s+no\s+{_DOMAIN_NP}\b",
        rf"\b{_DOMAIN_NP}\s+(?:is|are)\s+not\s+present\b",
        rf"\b{_DOMAIN_NP}\s+(?:is|are)\s+missing\b",
        rf"\b{_DOMAIN_NP}\s+(?:is|are)\s+absent\b",
        rf"\bno\s+such\s+{_DOMAIN_NP}\b",
        rf"\b{_DOMAIN_NP}\s+(?:cannot|can\s+not|can'?t)\s+be\s+found\b",
        rf"\bno\s+{_DOMAIN_NP}\s+exists?\b",
        rf"\b{_DOMAIN_NP}\s+isn'?t\s+there\b",
    )
)

OBSERVATION_STATE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        rf"\bI\s+(?:couldn'?t|could\s+not)\s+find\s+{_DOMAIN_NP}\b",
        rf"\b{_DOMAIN_NP}\s+was\s+not\s+found\b",
        rf"\b{_DOMAIN_NP}\s+(?:has|have)\s+not\s+been\s+\w+\b",
        rf"\bI\s+don'?t\s+see\s+{_DOMAIN_NP}\b",
        rf"\bI\s+haven'?t\s+(?:found|seen|verified)\s+{_DOMAIN_NP}\b",
    )
)


# ---------- Word-boundary needle helper (Aria catch-1) ----------


def _needle_in_text(needle: str, text: str) -> bool:
    """Word-boundary match. Per Aria's cross-review catch 1: substring matching
    creates false-positives ("letter" in "newsletter") that ALLOW absence-claims
    against domains never actually checked. Word-boundary closes the
    superstring gaming path.
    """
    return re.search(rf"\b{re.escape(needle)}\b", text, re.IGNORECASE) is not None


# ---------- Internal types ----------


@dataclass(frozen=True)
class AbsenceClaim:
    """One absence-claim found in response_text."""

    domain: str  # The noun-phrase the absence is asserted about
    matched_text: str  # The full matched phrase (for diagnostics)
    is_observation_state: bool  # True if phrased as observation, False if world


# ---------- The binding ----------


class AbsenceGapBinding:
    """Build 1a — absence-gap binding.

    Registered at HookLifecycle.STOP. The hook layer constructs a
    BindingPayload with lifecycle=STOP, response_text=<final response>, and
    turn_command_log=<commands run this turn with outputs>.
    """

    name: str = "absence_gap"
    lifecycle: HookLifecycle = HookLifecycle.STOP

    # ----- discover -----

    def discover(self, payload: BindingPayload) -> DiscoveryResult:
        if payload.response_text is None:
            return DiscoveryResult(applies=False, reason="no response_text")

        claims = self._extract_claims(payload.response_text)
        if not claims:
            return DiscoveryResult(applies=False, reason="no absence-claim language found")

        return DiscoveryResult(
            applies=True,
            reason=f"{len(claims)} absence-claim(s) found",
        )

    # ----- hard_block -----

    def hard_block(self, payload: BindingPayload) -> HardBlockResult | None:
        # response_text was validated non-None in discover(); re-assert for hard_block
        # being callable in isolation in tests.
        if payload.response_text is None:
            return None

        claims = self._extract_claims(payload.response_text)
        if not claims:
            return None

        unsearched = [
            c
            for c in claims
            if not self._any_command_touches_domain(c.domain, payload.turn_command_log)
        ]
        if unsearched:
            domains = ", ".join(repr(c.domain) for c in unsearched)
            return HardBlockResult(
                reason=(
                    f"absence-claim(s) made about {domains} with no command "
                    f"in turn_command_log touching the domain"
                ),
                recovery_path=(
                    "Before asserting absence, run a search command whose "
                    "command-line OR output mentions the domain. Then re-"
                    "evaluate the claim against actual search results."
                ),
            )

        return None

    # ----- validate -----

    def validate(self, payload: BindingPayload) -> ValidationResult:
        if payload.response_text is None:
            return ValidationResult(
                allow=False,
                reason="response_text is None at validate() step",
                recovery_path="Fix the hook layer to populate response_text on STOP lifecycle.",
            )

        claims = self._extract_claims(payload.response_text)

        # Dillahunty discipline (A.5.6): world-state phrasing over-claims.
        world_state_claims = [c for c in claims if not c.is_observation_state]
        if world_state_claims:
            phrases = "; ".join(repr(c.matched_text) for c in world_state_claims)
            return ValidationResult(
                allow=False,
                reason=(
                    f"absence phrased as world-state, not observation-state: {phrases}. "
                    f"Per Dillahunty-discipline: 'I haven't verified X exists' not 'X doesn't exist.'"
                ),
                recovery_path=(
                    "Rephrase to honor epistemic limits: 'I haven't found X' "
                    "rather than 'X doesn't exist.'"
                ),
            )

        # Domain-match (A.5.1): each claim needs a CommandLogEntry whose
        # OUTPUT is non-empty AND references the domain. A search that ran
        # but returned nothing in the right domain ≠ verified absence.
        unverified = [
            c
            for c in claims
            if not self._any_command_output_verifies_domain(c.domain, payload.turn_command_log)
        ]
        if unverified:
            domains = ", ".join(repr(c.domain) for c in unverified)
            return ValidationResult(
                allow=False,
                reason=(
                    f"absence-claim(s) about {domains} have search commands in "
                    f"turn_command_log, but no command output non-empty AND "
                    f"referencing the domain. The search may have run against "
                    f"the wrong scope, or returned empty without confirming the claim."
                ),
                recovery_path=(
                    "Verify the search actually examined the domain the claim is "
                    "about (correct path, correct pattern). Empty search output "
                    "doesn't confirm absence — it may indicate wrong scope."
                ),
            )

        return ValidationResult(allow=True, reason=f"{len(claims)} absence-claim(s) verified")

    # ----- helpers -----

    def _extract_claims(self, response_text: str) -> list[AbsenceClaim]:
        claims: list[AbsenceClaim] = []
        for pat in WORLD_STATE_PATTERNS:
            for m in pat.finditer(response_text):
                claims.append(
                    AbsenceClaim(
                        domain=m.group("domain").strip(),
                        matched_text=m.group(0),
                        is_observation_state=False,
                    )
                )
        for pat in OBSERVATION_STATE_PATTERNS:
            for m in pat.finditer(response_text):
                claims.append(
                    AbsenceClaim(
                        domain=m.group("domain").strip(),
                        matched_text=m.group(0),
                        is_observation_state=True,
                    )
                )
        return claims

    def _domain_needles(self, domain: str) -> list[str]:
        """Content-word needles for substring matching.

        Strips leading determiners ("those letters" → "letters") so the match
        catches morphological variants — searching for "letter" finds
        "letter_01.md" even when the claim says "those letters". Single-word
        domain stems get a singular form by stripping trailing 's' as a
        cheap first-cut pluralization handler.
        """
        determiners = {"the", "a", "an", "those", "that", "these", "this", "any"}
        tokens = [t.lower() for t in domain.split() if t.lower() not in determiners]
        if not tokens:
            return []
        needles = [" ".join(tokens)]
        if len(tokens) == 1 and tokens[0].endswith("s") and len(tokens[0]) > 3:
            needles.append(tokens[0][:-1])
        return needles

    def _any_command_touches_domain(
        self,
        domain: str,
        log: tuple[CommandLogEntry, ...],
    ) -> bool:
        """Did at least one command-line mention the domain?

        Per Aria's catch-2 cross-review 2026-06-26: checks command-line only,
        NOT output. Hard-block tests the channel (was a domain-relevant command
        issued?); validate tests the message (did the output verify the claim?).
        Reading output here would let unrelated broad sweeps whose output
        incidentally contains a domain-word pass hard-block.
        """
        needles = self._domain_needles(domain)
        if not needles:
            return False
        for entry in log:
            if any(_needle_in_text(n, entry.command) for n in needles):
                return True
        return False

    def _any_command_output_verifies_domain(
        self,
        domain: str,
        log: tuple[CommandLogEntry, ...],
    ) -> bool:
        """Did at least one command produce NON-EMPTY output referencing the domain?

        Stricter than _any_command_touches_domain — empty output doesn't count
        as verification even if the command-line mentioned the domain.

        Per Aria's catch-1 cross-review 2026-06-26: uses word-boundary matching
        instead of raw substring. Substring matching produces false-positive
        ALLOWs (e.g., "letter" matches "newsletter" in a grep over /docs/);
        word-boundary closes the superstring gaming path while staying cheap.
        """
        needles = self._domain_needles(domain)
        if not needles:
            return False
        for entry in log:
            if not entry.output.strip():
                continue
            if any(_needle_in_text(n, entry.output) for n in needles):
                return True
        return False
