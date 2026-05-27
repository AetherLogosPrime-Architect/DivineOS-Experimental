"""Tests for the consultation-gate keel-improvement: wisdom-file reads count
as substantive consults (Andrew 2026-05-26, council decision 5d8bf472,
prereg-271549887919).

The design (four-lens council Schneier/Yudkowsky/Beer/Meadows): widen the
gate's SENSOR to count reads of accumulated-wisdom files, scoped narrowly to
wisdom paths (NOT source code), recorded as a counter-reset identical to a
consult (never a farmable score). These tests pin the scope line and the
reset behavior.
"""

from __future__ import annotations

import pytest

from divineos.core import consultation_tracker as ct


@pytest.mark.parametrize(
    "path,is_wisdom",
    [
        # Wisdom files — reading these IS loading accumulated wisdom.
        ("exploration/aether/81_the_reflex.md", True),
        ("docs/substrate-knowledge/lesson.md", True),
        ("family/letters/aether-to-aria-2026-05-26.md", True),
        ("docs/foundational_truths.md", True),
        # Absolute / Windows-style paths still match.
        ("C:/DIVINE OS/DivineOS-Experimental/exploration/x.md", True),
        ("C:\\DIVINE OS\\DivineOS-Experimental\\family\\letters\\x.md", True),
        # Source / tests / scripts — a DIFFERENT stock (code-grounding). Must NOT
        # clear the wisdom gate, or the target-fidelity split collapses.
        ("src/divineos/core/consultation_tracker.py", False),
        ("tests/test_x.py", False),
        ("scripts/check_root_cause_audit.py", False),
        ("README.md", False),
        ("docs/data_model.md", False),  # docs/ but not a wisdom subpath
        ("", False),
        # Path-traversal must NOT masquerade as wisdom (Aletheia audit point 3):
        # these resolve to non-wisdom files, so canonicalization must reject them.
        ("exploration/../README.md", False),
        ("exploration/../../etc/passwd", False),
        ("exploration/../src/divineos/core/consultation_tracker.py", False),
        ("docs/substrate-knowledge/../data_model.md", False),
        # ...but legitimate nesting under a wisdom dir still counts.
        ("exploration/aether/sub/dir/deep.md", True),
    ],
)
def test_is_wisdom_path_scope(path: str, is_wisdom: bool) -> None:
    assert ct._is_wisdom_path(path) is is_wisdom


def test_record_wisdom_read_rejects_non_wisdom() -> None:
    """A non-wisdom path records nothing and returns False (defense in depth:
    even if a mis-scoped hook forwards a src/ read, the tracker refuses it)."""
    assert ct.record_wisdom_read("src/divineos/core/foo.py") is False
    assert ct.record_wisdom_read("") is False


def test_wisdom_read_is_substantive() -> None:
    """wisdom_read must be in the substantive set, so it resets the
    since-counter exactly like ask/recall/corrections. If it weren't, the
    sensor-widening would be inert."""
    assert "wisdom_read" in ct._SUBSTANTIVE_TOOLS


def test_wisdom_read_resets_since_counter(tmp_path, monkeypatch) -> None:
    """End-to-end: after N responses push the gate stale, a wisdom-read resets
    responses-since-last-consult to zero — same reset shape as a real consult."""
    state_file = tmp_path / "consultation_state.json"
    monkeypatch.setattr(ct, "_STATE_FILE", state_file)
    monkeypatch.setattr(ct, "_session_key", lambda: "test-session")

    for _ in range(ct._GATE_THRESHOLD + 1):
        ct.record_response()
    assert ct.consultation_gate_status()["stale"] is True

    # A wisdom-file read clears it, just as `divineos ask` would.
    assert ct.record_wisdom_read("exploration/aether/81_x.md") is True
    assert ct.consultation_gate_status()["stale"] is False


def test_non_wisdom_read_does_not_clear(tmp_path, monkeypatch) -> None:
    """A source-code read does NOT clear the gate — the gameable shortcut the
    scope line exists to prevent."""
    state_file = tmp_path / "consultation_state.json"
    monkeypatch.setattr(ct, "_STATE_FILE", state_file)
    monkeypatch.setattr(ct, "_session_key", lambda: "test-session-2")

    for _ in range(ct._GATE_THRESHOLD + 1):
        ct.record_response()
    assert ct.consultation_gate_status()["stale"] is True

    ct.record_wisdom_read("src/divineos/core/consultation_tracker.py")
    assert ct.consultation_gate_status()["stale"] is True  # still blocked
