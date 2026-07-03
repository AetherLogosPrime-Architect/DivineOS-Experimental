"""Fable audit round 7 (2026-07-02) — artifact pointer resolution.

Fable's exact reproduction: same claim, three pointer values, only
the None case correctly demoted.

    pointer=None                                    -> tier=outcome
    pointer=test:tests/test_nonexistent_fake.py     -> tier=falsifiable  (FAB fake)
    pointer=commit:deadbeefdeadbeef                  -> tier=falsifiable  (FAB fake)
    pointer=garbage-string-not-a-real-pointer        -> tier=falsifiable  (FAB junk)

This suite pins the fix: unresolvable pointers demote just like None.
Runs BEFORE the first production caller of the empirica gate ships,
per the module's caller-contract external-audit checkpoint.
"""

from __future__ import annotations

import pytest

from divineos.core.empirica.classifier import classify_claim
from divineos.core.empirica.pointer_resolver import resolve_pointer
from divineos.core.empirica.types import Tier


# ---------------------------------------------------------------------------
# resolve_pointer unit tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pointer",
    [
        None,
        "",
        "garbage-string-not-a-real-pointer",  # Fable's literal example
        "no-colon-so-not-a-pointer",
        "unknown_kind:whatever",
        "test:tests/does_not_exist.py::fake",  # Fable's example
        "test:tests/nonexistent_fake_test_file.py",
        "commit:deadbeefdeadbeef",  # Fable's example (fake SHA)
        "commit:not_hex_at_all",
        "commit:",
        "prereg:nonexistent-prereg-id-12345",
        "event:nonexistent-event-id-12345",
        "knowledge:nonexistent-knowledge-id-12345",
        "decide:nonexistent-decision-id-12345",
        "decision:nonexistent-decision-id-12345",
    ],
)
def test_unresolvable_pointers_return_false(pointer):
    """Any pointer that doesn't reference a real artifact → False."""
    assert resolve_pointer(pointer) is False


def test_test_pointer_resolves_when_file_exists():
    """test:<path> resolves True when the path is a real file."""
    # This file itself — guaranteed to exist during the test run.
    assert resolve_pointer("test:tests/test_fable_audit_round7_pointer_resolution.py") is True


def test_test_pointer_with_nodeid_resolves_by_path_only():
    """test:<path>::<name> — only the path is checked (fast)."""
    assert (
        resolve_pointer("test:tests/test_fable_audit_round7_pointer_resolution.py::test_x") is True
    )


# ---------------------------------------------------------------------------
# classify_claim behavior — Fable's exact reproduction table
# ---------------------------------------------------------------------------


def _falsifiable_shaped_claim(pointer):
    """A FACT+measured claim that wants FALSIFIABLE tier."""
    return classify_claim(
        content="Metric X exceeded threshold Y in the last run.",
        knowledge_type="FACT",
        source="measured",
        artifact_pointer=pointer,
    )


def test_none_pointer_demotes_to_outcome():
    """Regression: honest None still demoted (was already correct)."""
    c = _falsifiable_shaped_claim(None)
    assert c.tier == Tier.OUTCOME
    assert "no artifact pointer" in c.reason


def test_fabricated_test_pointer_demotes_to_outcome():
    """Fable's #1 reproduction: fake test path no longer earns FALSIFIABLE."""
    c = _falsifiable_shaped_claim("test:tests/does_not_exist.py::fake")
    assert c.tier == Tier.OUTCOME, (
        "Fabricated test pointer should demote (Fable round 7). "
        f"Got tier={c.tier}, reason={c.reason}"
    )
    assert "does not resolve" in c.reason


def test_fabricated_commit_pointer_demotes_to_outcome():
    """Fable's reproduction: fake commit SHA no longer earns FALSIFIABLE."""
    c = _falsifiable_shaped_claim("commit:deadbeefdeadbeef")
    assert c.tier == Tier.OUTCOME
    assert "does not resolve" in c.reason


def test_garbage_string_pointer_demotes_to_outcome():
    """Fable's reproduction: literal 'garbage-string-not-a-real-pointer'."""
    c = _falsifiable_shaped_claim("garbage-string-not-a-real-pointer")
    assert c.tier == Tier.OUTCOME
    assert "does not resolve" in c.reason


def test_unrecognized_kind_pointer_demotes_to_outcome():
    """A new kind: prefix an attacker invents doesn't bypass resolution."""
    c = _falsifiable_shaped_claim("nonexistent-kind:whatever")
    assert c.tier == Tier.OUTCOME
    assert "does not resolve" in c.reason


def test_real_test_pointer_survives_and_stays_falsifiable():
    """Positive control: a resolvable pointer still earns the tier."""
    c = _falsifiable_shaped_claim("test:tests/test_fable_audit_round7_pointer_resolution.py")
    # The classification is still allowed to stay at FALSIFIABLE (or
    # whatever tier the base rules would give). The key is: no demotion
    # for "does not resolve" this time.
    assert "does not resolve" not in (c.reason or "")


def test_classification_carries_the_original_tier_on_demotion():
    """Regression: initial_tier is preserved so downstream can see it."""
    c = _falsifiable_shaped_claim("test:tests/does_not_exist.py")
    assert c.tier == Tier.OUTCOME
    assert c.initial_tier is not None
    assert c.initial_tier != Tier.OUTCOME
