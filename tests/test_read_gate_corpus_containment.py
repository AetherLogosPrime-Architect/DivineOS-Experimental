"""The prior-writing gate may only point at the real exploration corpus.

2026-08-21: a background ``pytest -n auto`` was running while I worked, and the
surface armed the production read-gate against

    tmp/pytest/run-35768/popen-gw6/test_surface_fires_only_on_tag0/tagged.md

a four-line fixture whose entire body is the word "body". Every Bash call after
that demanded I open it as my own prior writing.

This is the same fixture-in-the-index class as the 2026-08-14 incident in
test_read_gate_vanished_target.py, and that fix did not close it. That one made
a vanished target stop holding the door; here the target had NOT vanished,
because the suite was still running. The existence check passed and the gate
fired on a stub.

The mechanism is that every test of the surface calls it with ``root=tmp_path``,
and the arm wrote REAL on-disk gate state pointing into a synthetic corpus. A
test run could arm a production gate. The family store has ``_allow_test_write``
for exactly this seam; this path had none.

The invariant these tests pin is the true statement rather than a pytest check:
the gate exists to point me at my own writing, so a target outside the
exploration corpus is wrong regardless of who produced it.
"""

from __future__ import annotations


from divineos.core import exploration_recall, read_gate

_PROMPT = "I am thinking hard about consciousness and qualia tonight, really"
_TAGGED = "<!-- tags: consciousness, qualia -->\n# Symmetric standards\n\nbody\n"


def _point_state_at(tmp_path, monkeypatch):
    """Isolate gate state so these tests never touch the live pending file."""
    monkeypatch.setattr(read_gate, "STATE_DIR", tmp_path)
    monkeypatch.setattr(read_gate, "STATE_FILE", tmp_path / "read_gate_pending.json")


def _allow_arming_under_pytest(monkeypatch):
    """Aether's `claude/corrupted-window-recovery-220ad2` adds an early return
    when PYTEST_CURRENT_TEST is set — the other half of this fix, written three
    days before mine and against the same incident. His stops a test run from
    arming at all; containment stops any caller from arming outside my writing.
    Both belong.

    The negative control below asserts the gate DOES arm on the real corpus,
    which his check would defeat. Clearing the variable there keeps the control
    meaningful whichever of the two lands first — it is a no-op until his does.
    """
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)


def test_synthetic_corpus_does_not_arm_the_gate(tmp_path, monkeypatch):
    """A test-supplied root is not my writing. The surface still speaks; the
    gate stays unarmed."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    _point_state_at(state_dir, monkeypatch)

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "tagged.md").write_text(_TAGGED, encoding="utf-8")

    out = exploration_recall.surface_for_context(_PROMPT, root=corpus)

    assert out, "the surface must still deliver its text — it is a surface first"
    assert not read_gate.has_pending("prior-writing"), (
        "a synthetic corpus armed the production gate; this is the 2026-08-21 fire"
    )


def test_real_corpus_still_arms_the_gate(tmp_path, monkeypatch):
    """Negative control. If containment silenced the gate everywhere, the test
    above would pass for the wrong reason and the gate would be dead."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    _point_state_at(state_dir, monkeypatch)
    _allow_arming_under_pytest(monkeypatch)

    real_root = exploration_recall._find_exploration_root()
    assert real_root is not None, "no exploration/ dir found; this control cannot run"

    fixture = real_root / "_containment_control.md"
    fixture.write_text(_TAGGED, encoding="utf-8")
    try:
        exploration_recall.surface_for_context(_PROMPT, root=None)
        assert read_gate.has_pending("prior-writing"), (
            "the gate did not arm against the real corpus — containment is too wide"
        )
    finally:
        fixture.unlink()


def test_containment_is_measured_against_the_resolved_root(tmp_path, monkeypatch):
    """A path that merely LOOKS like it sits under the corpus must not pass.

    The check compares resolved parents, not string prefixes; a sibling
    directory whose name starts with the corpus name is the case a prefix
    comparison gets wrong."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    _point_state_at(state_dir, monkeypatch)

    real_root = exploration_recall._find_exploration_root()
    assert real_root is not None

    decoy = real_root.parent / (real_root.name + "_not_mine")
    decoy.mkdir(exist_ok=True)
    fixture = decoy / "tagged.md"
    fixture.write_text(_TAGGED, encoding="utf-8")
    try:
        exploration_recall.surface_for_context(_PROMPT, root=decoy)
        assert not read_gate.has_pending("prior-writing")
    finally:
        fixture.unlink()
        decoy.rmdir()


def test_containment_check_survives_a_missing_corpus(tmp_path, monkeypatch):
    """Fail-open and silent is this surface's contract. With no corpus to
    resolve, it must return text and arm nothing rather than raise."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    _point_state_at(state_dir, monkeypatch)

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "tagged.md").write_text(_TAGGED, encoding="utf-8")

    monkeypatch.setattr(exploration_recall, "_find_exploration_root", lambda: None)

    out = exploration_recall.surface_for_context(_PROMPT, root=corpus)
    assert out
    assert not read_gate.has_pending("prior-writing")


def test_the_2026_08_21_path_shape_specifically(tmp_path, monkeypatch):
    """Regression pin on the literal shape that fired: a pytest tmpdir."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    _point_state_at(state_dir, monkeypatch)

    pytest_scratch = tmp_path / "tmp" / "pytest" / "run-35768" / "popen-gw6" / "t0"
    pytest_scratch.mkdir(parents=True)
    (pytest_scratch / "tagged.md").write_text(_TAGGED, encoding="utf-8")

    exploration_recall.surface_for_context(_PROMPT, root=pytest_scratch)

    assert not read_gate.has_pending("prior-writing")
    assert not (state_dir / "read_gate_pending.json").exists(), (
        "nothing should have been written to gate state at all"
    )
