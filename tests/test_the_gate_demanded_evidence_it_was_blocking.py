"""The correction gate demanded a file path it was itself preventing me from creating.

2026-09-15. Andrew pushed back on a claim of mine, the correction-marker gate
fired, and every exit was held shut by a different gate:

  divineos learn   -> refused by the reach-check doorman, which is one of nine
                      PreToolUse gates that can deny WITHOUT consulting the
                      shared list of every gate's prescribed exit. The list
                      already carried ``divineos learn``. It was never asked.

  divineos correction -> refused without a file path proving a structural fix.
                      That rule is RIGHT: a claimed fix with no path is an
                      empty claim. But a structural fix is an EDIT, and the
                      marker gate blocks edits. The marker is set at
                      prompt-submit, BEFORE any work -- so this closed on every
                      correction needing a code fix, not occasionally.

  clear_correction_marker.py -> the fire door, refused by the permission layer.

Andrew: "you have my permission to bypass the gates but you need to fix the
root issue for the deadlock immediately."

THE SHARED ALLOWLIST CANNOT CARRY THE SECOND HALF. It reads the Bash command
out of the hook payload, so it is Bash-only by construction, and its charter
says nothing in it may ever match an editor -- correctly, since everything it
holds is a RECORDING action that cannot edit, commit, push or delete. So the
edit exemption lives in the gate, narrow and separately named, and Bash stays
blocked either way: the fix can be written and NOTHING else done with it until
the correction is actually filed.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from divineos.hooks.pre_tool_use_gate import _is_low_friction_write, _is_remedy_write

REPO = Path(__file__).resolve().parents[1]


def _edit(path: str, tool: str = "Edit") -> dict:
    return {"tool_name": tool, "tool_input": {"file_path": path}}


# --- the edit half: the gate must not block the evidence it demands --------


@pytest.mark.parametrize(
    "path",
    [
        ".claude/hooks/reach-check-doorman.sh",
        "scripts/clear_correction_marker.py",
        "src/divineos/hooks/pre_tool_use_gate.py",
        "C:/DIVINE OS/DivineOS-Experimental/.claude/hooks/verify-claim-prime.sh",
    ],
)
def test_a_fix_to_gate_machinery_is_the_remedy_not_the_next_task(path: str) -> None:
    assert _is_remedy_write(_edit(path)), (
        "the correction CLI refuses to file without a file path proving a "
        "structural fix -- so the write that creates it cannot be blocked by "
        "the same gate, or the gate demands evidence it prevents"
    )


def test_machinery_is_recognised_by_name_wherever_it_sits(tmp_path: Path) -> None:
    """A detector under core/ is gate machinery. Matching on the NAME is what
    lets the fix land without exempting core/ wholesale."""
    assert _is_remedy_write(_edit("src/divineos/core/correction_marker.py"))
    assert _is_remedy_write(_edit("src/divineos/core/closure_shape_detector.py"))


def test_ordinary_code_is_still_blocked(tmp_path: Path) -> None:
    """THE FENCE. This gate exists so Andrew's words do not evaporate while I
    go do the next thing. Ordinary code work IS the next thing."""
    for path in (
        "src/divineos/core/ledger.py",
        "src/divineos/core/memory.py",
        "tests/test_something_unrelated.py",
    ):
        assert not _is_remedy_write(_edit(path)), f"{path} must stay blocked"


def test_bash_never_qualifies() -> None:
    """The whole safety argument: the fix can be WRITTEN and nothing else --
    not run, not tested, not committed -- until the correction is filed."""
    assert not _is_remedy_write({"tool_name": "Bash", "tool_input": {"command": "pytest tests/"}})
    assert not _is_remedy_write({"tool_name": "Read", "tool_input": {"file_path": "scripts/x.py"}})


def test_traversal_cannot_borrow_the_exemption() -> None:
    """Same hole a prior audit found in the sibling predicate: a path that
    starts in an exempt directory and climbs out of it."""
    assert not _is_remedy_write(_edit(".claude/hooks/../../src/divineos/core/ledger.py"))


def test_the_two_predicates_stay_separate() -> None:
    """The remedy exemption is scoped to ONE gate. The low-friction predicate
    is shared by six, and widening it would silently loosen five unrelated
    disciplines -- which is the alternative that was rejected."""
    hook = _edit(".claude/hooks/reach-check-doorman.sh")
    assert _is_remedy_write(hook)
    assert not _is_low_friction_write(hook), (
        "a gate fix must NOT become low-friction: that predicate feeds five "
        "other gates whose subject is tool gravity, not this deadlock"
    )


# --- the command half: no gate may block another gate's prescribed exit ----


def _denying_prehooks_without_the_allowlist() -> list[str]:
    hooks = REPO / ".claude" / "hooks"
    missing = []
    for f in sorted(hooks.glob("*.sh")):
        text = f.read_text(encoding="utf-8", errors="replace")
        denies = '"deny"' in text or "BLOCKED:" in text
        if denies and "remedy_allowlist" not in text:
            missing.append(f.name)
    return missing


def test_the_doorman_that_caused_this_now_consults_the_shared_list() -> None:
    text = (REPO / ".claude" / "hooks" / "reach-check-doorman.sh").read_text(
        encoding="utf-8", errors="replace"
    )
    assert "remedy_allowlist" in text and "remedy_pass_through" in text, (
        "this doorman refused `divineos learn` -- a remedy the shared list "
        "already carried -- because it never asked"
    )


def _usable_bash() -> str | None:
    """A shell that can actually run, not just a name on PATH.

    On this box ``bash`` resolves to a WSL relay with no interpreter behind
    it, which fails with a process-creation error rather than a syntax error.
    Reporting that as a broken hook would be a confident wrong answer about
    the wrong subject -- a missing instrument rendered as a finding.
    """
    for candidate in ("bash", "C:/Program Files/Git/bin/bash.exe"):
        try:
            probe = subprocess.run(
                [candidate, "-c", "exit 0"], capture_output=True, text=True, timeout=20
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0:
            return candidate
    return None


def test_the_doorman_still_parses() -> None:
    shell = _usable_bash()
    if shell is None:
        pytest.skip("no runnable bash on this machine -- absent, not passing")
    r = subprocess.run(
        [shell, "-n", str(REPO / ".claude" / "hooks" / "reach-check-doorman.sh")],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr


def test_the_remaining_unprotected_deniers_are_named_not_silent() -> None:
    """NOT a pass/fail on the count -- a pin so the set cannot grow unnoticed.

    Several of these are Stop hooks, where a command allowlist is meaningless.
    The point is that the list is visible: a new denying hook that forgets the
    shared list shows up here instead of surfacing as a deadlock weeks later.
    """
    missing = _denying_prehooks_without_the_allowlist()
    assert "reach-check-doorman.sh" not in missing, "the one that caused this is fixed"
    assert len(missing) <= 11, (
        f"denying hooks with no knowledge of any other gate's exit grew to "
        f"{len(missing)}: {missing}"
    )


# --- the third head: an honest false-positive label left the block up ----
#
# The Stop gate's block message is re-read as a correction at the next
# prompt, which sets the marker. Labelling the fire never touched it. So a
# label made honestly -- named reason, appended to the training corpus, on
# the record as a disagreement with my own detector -- left me exactly as
# blocked, with the only exits being to file a correction that did not
# happen, or the fire door. Those are the two outcomes the labelling script
# was written to prevent; it fixed them for its own log and stopped one step
# short of the marker.


def _labeller():
    import importlib.util

    # The script bootstraps its own imports via a sibling module, which is
    # only importable with scripts/ on the path -- true when it runs as a
    # script, false when a test loads it by file.
    scripts_dir = str(REPO / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    spec = importlib.util.spec_from_file_location(
        "_labeller", REPO / "scripts" / "label_correction_shape_false_positive.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def sandboxed_marker(tmp_path, monkeypatch):
    """Redirect the marker to a temp file. The live marker is real session
    state; a test that clobbers it would be a gate-disarming test."""
    from divineos.core import correction_marker as cm

    target = tmp_path / "correction_unlogged.json"
    monkeypatch.setattr(cm, "marker_path", lambda: target)
    return cm, target


def test_labelling_lifts_the_marker_this_gate_set(sandboxed_marker) -> None:
    cm, target = sandboxed_marker
    cm.set_marker("[correction-shape-v2 stop-gate] USE clause matched (1 hits)")
    assert target.exists()

    outcome = _labeller()._lift_marker_set_by_this_gate()

    assert not target.exists(), "an honest label must not leave the same total block"
    assert "lifted" in outcome


def test_a_marker_andrew_set_is_left_standing(sandboxed_marker) -> None:
    """THE SAFETY PROPERTY, and the reason this is conditional rather than a
    blanket clear. The marker is shared. Wiping a real correction from him
    because an unrelated detector fire was mislabelled would destroy the
    protection outright."""
    cm, target = sandboxed_marker
    cm.set_marker("you said the ledger cannot verify itself and that is wrong")

    outcome = _labeller()._lift_marker_set_by_this_gate()

    assert target.exists(), "a correction from Andrew still has to be filed"
    assert "LEFT STANDING" in outcome


def test_no_marker_is_reported_not_crashed(sandboxed_marker) -> None:
    _cm, target = sandboxed_marker
    assert not target.exists()
    assert "nothing to lift" in _labeller()._lift_marker_set_by_this_gate()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-q"]))
