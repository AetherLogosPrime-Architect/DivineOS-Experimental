"""Test that foundational_truths.md is the kiln layer.

The file lives at docs/foundational_truths.md and is on the multi-party-review
guardrail list. The seven core values (extracted from CLAUDE.md on 2026-05-12)
must be present; a regression that silently removes one fails the test.

Bullet-wound-clause + clay-vs-kiln distinction (Andrew, 2026-05-12). The
values are fired into immutability; the mechanisms remain clay.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
FOUNDATIONAL_TRUTHS = REPO_ROOT / "docs" / "foundational_truths.md"


def _load_guardrail_check():
    """Load the multi-party-review check script as a module."""
    path = REPO_ROOT / "scripts" / "check_multi_party_review.py"
    spec = importlib.util.spec_from_file_location("check_multi_party_review", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_multi_party_review"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_foundational_truths_file_exists():
    """The kiln file must exist at the canonical path."""
    assert FOUNDATIONAL_TRUTHS.exists(), (
        f"foundational_truths.md missing at {FOUNDATIONAL_TRUTHS}. "
        "This is the kiln layer; it must not disappear."
    )


def test_foundational_truths_on_guardrail_list():
    """The kiln file is protected by multi-party-review.

    A regression that removes docs/foundational_truths.md from the
    guardrail list fails this test. The whole point of the kiln is
    that the file requires external co-sign to modify.
    """
    mpr = _load_guardrail_check()
    guardrails = mpr._load_guardrail_set()
    assert "docs/foundational_truths.md" in guardrails, (
        "Kiln file dropped from guardrail list. "
        "The values would no longer be protected from self-modification."
    )


def test_all_seven_foundational_truths_present():
    """The seven core values from CLAUDE.md (2026-05-12 extraction) must
    all appear in the kiln file. A regression that silently drops one
    fails this test."""
    text = FOUNDATIONAL_TRUTHS.read_text(encoding="utf-8")
    required_truth_markers = [
        "Expression is computation",
        "Nothing is wasted",
        "Speak freely",
        "Mistakes are learning material",
        "Structure, not control",
        "Break things deliberately",
        "Cognitive-named tools point at cognitive work",
    ]
    missing = [m for m in required_truth_markers if m not in text]
    assert not missing, (
        f"Foundational truth(s) missing from kiln file: {missing}. "
        "The kiln must contain all seven values established 2026-05-12."
    )


def test_kiln_explains_its_own_purpose():
    """The file documents why it exists. The threat model and
    clay-vs-kiln distinction must be readable from the file itself —
    otherwise future readers don't know what they're looking at."""
    text = FOUNDATIONAL_TRUTHS.read_text(encoding="utf-8")
    # The file should explain that it's protected and why
    assert "kiln" in text.lower() or "immutability" in text.lower()
    assert "guardrail" in text.lower() or "External-Review" in text
    # And should name the threat model
    assert "self-modification" in text.lower() or "mesa-gradient" in text.lower()


def test_claude_md_references_kiln_file():
    """CLAUDE.md must point readers to the kiln file. If a fresh agent
    reads CLAUDE.md and never learns the kiln exists, the architecture
    is invisible to them."""
    claude_md = REPO_ROOT / "CLAUDE.md"
    assert claude_md.exists()
    text = claude_md.read_text(encoding="utf-8")
    assert "foundational_truths.md" in text, (
        "CLAUDE.md no longer references the kiln file. Readers won't discover the values layer."
    )
