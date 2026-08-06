"""M3 discipline artifacts — and the rule that every passing case be reachable.

WHY THIS MODULE EXISTS IN THIS SHAPE. The 2026-07-28 doorman had a single
pass-condition: the string ``consult-<hex>`` appearing in
``divineos decisions list``. Nothing emits that string. Measured before wiring:
zero occurrences, ever. Switching it on unchanged would have blocked every
Dad-directed build permanently, with bypass the only route through — the same
unreachable-success-condition defect that made merge-review fail 20 times in a
row, sitting inside the gate Aria and I designed.

So the load-bearing tests here are not the blocking ones. They are the
**reachability** ones: each predicate is driven to True with a fixture that
looks like real usage. A gate whose refusal you can demonstrate but whose
acceptance you cannot is not a gate, it is a wall with a sign on it.
"""

from __future__ import annotations

import json

from divineos.core.m3_discipline import (
    ARTIFACTS,
    DisciplineCheck,
    evaluate,
    format_block,
    has_iteration,
    has_pattern_lookup,
    has_runtime_test,
    required_for_gravity,
)


def _transcript(tmp_path, *tool_uses):
    """Write a transcript with the given tool_use blocks, one entry per line."""
    p = tmp_path / "transcript.jsonl"
    lines = []
    for name, inp in tool_uses:
        lines.append(
            json.dumps(
                {
                    "type": "assistant",
                    "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]},
                }
            )
        )
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


# --------------------------------------------------------------------------
# REACHABILITY — the tests that would have caught the original defect
# --------------------------------------------------------------------------


def test_pattern_lookup_is_reachable(tmp_path):
    """A Grep must be able to satisfy the pattern-lookup artifact."""
    t = _transcript(tmp_path, ("Grep", {"pattern": "wiring_dark"}))
    assert has_pattern_lookup(t) is True


def test_pattern_lookup_reachable_via_read_and_glob(tmp_path):
    for tool in ("Read", "Glob"):
        t = _transcript(tmp_path, (tool, {"file_path": "src/x.py"}))
        assert has_pattern_lookup(t) is True, tool


def test_iteration_is_reachable_via_a_recorded_decision(tmp_path):
    t = _transcript(tmp_path, ("Bash", {"command": 'divineos decide "x" --tension "y"'}))
    assert has_iteration(t) is True


def test_iteration_is_reachable_via_a_second_pass_on_one_file(tmp_path):
    t = _transcript(
        tmp_path,
        ("Edit", {"file_path": "src/a.py"}),
        ("Edit", {"file_path": "src/a.py"}),
    )
    assert has_iteration(t) is True


def test_runtime_test_is_reachable(tmp_path):
    t = _transcript(tmp_path, ("Bash", {"command": "pytest tests/ -q"}))
    assert has_runtime_test(t) is True


def test_all_four_can_be_satisfied_at_once(tmp_path, monkeypatch):
    """The whole point. At the highest requirement the gate must still be
    passable by doing the actual work."""
    monkeypatch.setattr("divineos.core.m3_discipline.has_council_walk", lambda *a, **k: True)
    t = _transcript(
        tmp_path,
        ("Grep", {"pattern": "existing"}),
        ("Bash", {"command": 'divineos decide "x"'}),
        ("Bash", {"command": "pytest -q"}),
    )
    check = evaluate(t, gravity_score=6)
    assert check.required_count == 3
    assert check.satisfied is True
    assert set(check.present) == set(ARTIFACTS)


# --------------------------------------------------------------------------
# The blocking direction still has to work
# --------------------------------------------------------------------------


def test_empty_stream_satisfies_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr("divineos.core.m3_discipline.has_council_walk", lambda *a, **k: False)
    t = _transcript(tmp_path)
    check = evaluate(t, gravity_score=3)
    assert check.present == set()
    assert check.satisfied is False
    assert len(check.missing) == 4


def test_one_artifact_is_not_enough_at_higher_gravity(tmp_path, monkeypatch):
    monkeypatch.setattr("divineos.core.m3_discipline.has_council_walk", lambda *a, **k: False)
    t = _transcript(tmp_path, ("Grep", {"pattern": "x"}))
    assert evaluate(t, gravity_score=1).satisfied is True
    assert evaluate(t, gravity_score=5).satisfied is False


def test_a_missing_transcript_satisfies_nothing_rather_than_crashing(monkeypatch):
    monkeypatch.setattr("divineos.core.m3_discipline.has_council_walk", lambda *a, **k: False)
    check = evaluate("/no/such/file.jsonl", gravity_score=3)
    assert check.present == set()


# --------------------------------------------------------------------------
# Proportionality
# --------------------------------------------------------------------------


def test_zero_gravity_requires_nothing():
    """Not substrate work — the gate must not apply at all."""
    assert required_for_gravity(0) == 0
    assert DisciplineCheck(present=set(), required_count=0).satisfied is True


def test_requirement_rises_with_gravity_and_caps_at_three():
    """Calibrated against MEASURED scores. My first draft put the strict tier
    at 5+, then I measured what real edits actually score: a git commit is 1,
    a hook write is 1, a commit plus a divineos write-command is 2, a write
    touching both a hook and core is 2, and 3 was observed live. Nothing
    realistic reaches 5, so that tier would never have applied -- the same
    unreachable-condition defect as the gate this replaces, inverted."""
    assert required_for_gravity(1) == 1
    assert required_for_gravity(2) == 2
    assert required_for_gravity(3) == 3
    assert required_for_gravity(99) == 3, (
        "must cap at 3 — demanding all four makes the honest path costlier "
        "than the bypass, which trains the habit the gate exists to prevent"
    )


# --------------------------------------------------------------------------
# The refusal has to be actionable
# --------------------------------------------------------------------------


def test_block_message_names_each_missing_artifact_and_its_remedy(tmp_path, monkeypatch):
    monkeypatch.setattr("divineos.core.m3_discipline.has_council_walk", lambda *a, **k: False)
    check = evaluate(_transcript(tmp_path), gravity_score=5)
    msg = format_block(check)
    for a in ARTIFACTS:
        assert a in msg, f"{a} missing from the refusal"
    assert "divineos mansion council" in msg
    assert "authorize-bypass" in msg
    assert "gravity score : 5" in msg


def test_block_message_reports_what_was_present(tmp_path, monkeypatch):
    """Naming what you DID do matters — a refusal that only lists failures
    reads as an accusation and invites routing around it."""
    monkeypatch.setattr("divineos.core.m3_discipline.has_council_walk", lambda *a, **k: False)
    check = evaluate(_transcript(tmp_path, ("Grep", {"pattern": "x"})), gravity_score=5)
    assert "present       : pattern_lookup" in format_block(check)
