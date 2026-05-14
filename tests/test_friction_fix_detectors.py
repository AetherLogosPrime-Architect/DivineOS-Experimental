"""Pytest wrapper around the script-level self-test for the F2
wiring-claim detector.

Per auditor-Claude's PR #260 review (Finding 2): the closure-claim
gate has *both* a script-level self-test AND a pytest-integrated
test file. The wiring-claim detector shipped with a self-test but
not pytest integration. CI couldn't catch self-test regressions.

Originally this file also wrapped the F1 third-person-drift script
(check_third_person_drift.py). That script was deleted 2026-05-14
(commit 0fccd11) as legacy — superseded by the in-process
distancing_detector module in src/divineos/core/operating_loop/,
which has its own pytest coverage (test_distancing_detector.py).
The F1 portion of this file was removed to match.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make scripts/ importable so the detector can be loaded as a module
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

import check_wiring_claims  # noqa: E402


class TestWiringClaimDetector:
    """F2 — wiring-claim detector."""

    def test_self_test_passes(self):
        assert check_wiring_claims.self_test() == 0

    def test_wiring_phrases_match(self):
        for phrase in (
            "wire Tier IV to VOID via VOID_SURVIVAL corroboration kind",
            "bridge VOID and EMPIRICA at the corroboration layer",
            "end-to-end test for loadout refresh",
            "close the gap between producer and consumer",
        ):
            assert check_wiring_claims.find_wiring_claims(phrase), f"expected match on {phrase!r}"

    def test_non_wiring_phrases_do_not_match(self):
        for phrase in (
            "loadout system + mini briefing: cold-start substrate map",
            "Just a regular commit message with no wiring",
        ):
            assert not check_wiring_claims.find_wiring_claims(phrase), (
                f"unexpected match on {phrase!r}"
            )

    def test_check_commit_returns_warning_on_wiring(self):
        """The ok-flag should always be True (soft gate); the message
        should be non-empty when wiring-language is present."""
        ok, msg = check_wiring_claims.check_commit("wire X to Y")
        assert ok is True, "wiring-claim gate is soft; never blocks"
        assert msg, "wiring-claim gate must surface a warning when triggered"
        assert "WIRING DISCIPLINE" in msg

    def test_check_commit_silent_on_non_wiring(self):
        ok, msg = check_wiring_claims.check_commit("Refactor: rename foo to bar")
        assert ok is True
        assert msg == "", "non-wiring commits must produce no warning"
