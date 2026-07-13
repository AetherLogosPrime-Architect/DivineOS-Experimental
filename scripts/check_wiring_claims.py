#!/usr/bin/env python3
"""Wiring-claim commit-msg gate — friction-fix F2.

When a commit message claims "wire X to Y", "bridge X and Y",
"integrate X with Y", "connect X to Y" — verify the claim is more
than receiver-side. Auditor-Claude caught half-built wiring twice
in 2026-05-05: loadout commit had no tests; EMPIRICA commit had no
producer side. Both passed the closure-claim gate because the
commit messages didn't say "fully closed" — but they said "wire"
which is the same shape of overclaim.

This gate doesn't enforce specific tests; it raises a *visible*
warning when wiring-language appears, prompting the operator to
verify both sides are exercised end-to-end. The cost-restructuring:
make the wrong-cheap path (claim wired without end-to-end) more
expensive than the right path (verify both sides + add a test).

Per the mesa-optimization re-costing principle (knowledge 82049915):
don't argue with the optimizer; raise the cost of the wrong path.

Usage as commit-msg hook:

    python scripts/check_wiring_claims.py <commit-msg-file>

The gate is a soft warning, not a hard block. Visible bypass via
``--no-verify``. Exits 0 always — but prints a loud reminder when
wiring-language is detected.

Standalone smoke test:

    python scripts/check_wiring_claims.py --self-test
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Patterns that indicate wiring/integration claims. Word-boundaries
# and case-insensitive. Conservative — these all clearly imply
# producer-and-consumer integration.
_WIRING_PATTERNS = (
    r"\bwire(?:d|s|ing)?\s+[\w\s]{1,30}?\s+(?:to|→|->|and)\b",
    r"\bbridge(?:d|s|ing)?\s+[\w\s]{1,30}?\s+(?:to|→|->|and|with)\b",
    r"\bintegrate(?:d|s)?\s+[\w\s]{1,30}?\s+(?:to|→|->|with|and)\b",
    r"\bconnect(?:ed|s|ing)?\s+[\w\s]{1,30}?\s+(?:to|→|->|and)\b",
    r"\bproducer\s*[/-]?\s*(?:and|or|to|→|->)?\s*consumer",
    r"\bend[- ]to[- ]end\b",
    r"\bclos(?:e|ed|es|ing)\s+the\s+gap\b",
)
_WIRING_RE = re.compile("|".join(_WIRING_PATTERNS), re.IGNORECASE)


def find_wiring_claims(commit_msg: str) -> list[str]:
    """Return all wiring-claim phrases found in the commit message."""
    return [m.group(0) for m in _WIRING_RE.finditer(commit_msg)]


def check_commit(commit_msg: str) -> tuple[bool, str]:
    """Check a commit message for wiring claims.

    Returns (ok, message). ok is always True (soft gate); message is
    a warning when wiring-language is detected.
    """
    claims = find_wiring_claims(commit_msg)
    if not claims:
        return True, ""

    return True, (
        f"[wiring-claim] {len(claims)} wiring claim(s) found in commit message:\n"
        + "\n".join(f"  * {c!r}" for c in claims[:5])
        + "\n\n"
        "WIRING DISCIPLINE: a 'wire X to Y' claim must verify BOTH sides.\n"
        "Auditor caught two half-built wirings on 2026-05-05 (loadout "
        "without tests; EMPIRICA without producer). Re-cost the wrong\n"
        "path by checking before commit:\n"
        "  1. Did you exercise BOTH the producer and consumer ends\n"
        "     end-to-end (not just the receiver, not just one side)?\n"
        "  2. Is there a test that would catch the absence of either side?\n"
        "  3. If a downstream caller never produces what the upstream\n"
        "     accepts, the wiring is half-built — the NotImplementedError\n"
        "     is gone but the integration is still broken.\n"
        "\n"
        "If both sides verified: proceed (this is a soft warning, not\n"
        "a block). If unsure: open the file at the production-side and\n"
        "trace one real call before committing."
    )


def self_test() -> int:
    """Smoke test the detector."""
    test_cases = [
        ("loadout system + mini briefing: cold-start substrate map", False),
        ("wire Tier IV to VOID via VOID_SURVIVAL corroboration kind", True),
        ("bridge VOID and EMPIRICA at the corroboration layer", True),
        ("integrate the timer with felt-sense calibration", True),
        ("connect the producer to the consumer", True),
        ("Just a regular commit message with no wiring", False),
        ("close the gap between producer and consumer", True),
        ("end-to-end test for loadout refresh", True),
    ]
    failures = 0
    for msg, expected_warning in test_cases:
        claims = find_wiring_claims(msg)
        actual = bool(claims)
        if actual != expected_warning:
            failures += 1
            print(
                f"FAIL: {msg!r} expected_warning={expected_warning} actual={actual} claims={claims}"
            )
    if failures == 0:
        print("self-test OK")
        return 0
    return 1


def main(argv: list[str]) -> int:
    args = argv[1:]
    if "--help" in args or "-h" in args or not args:
        print(__doc__)
        return 0
    if "--self-test" in args:
        return self_test()

    # Commit-msg hook mode: argv[1] is the path to the commit message file
    msg_path = Path(args[0])
    if not msg_path.exists():
        print(f"[!] commit message file not found: {msg_path}", file=sys.stderr)
        return 0  # fail-open
    commit_msg = msg_path.read_text(encoding="utf-8", errors="replace")
    _ok, info = check_commit(commit_msg)
    if info:
        print(info)
    return 0  # always 0 — this is a soft gate


if __name__ == "__main__":
    sys.exit(main(sys.argv))
