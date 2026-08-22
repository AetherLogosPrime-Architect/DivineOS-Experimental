"""The read-gate must never arm on pytest scratch.

The prior-writing index matches on tag headers, and test fixtures carry real
ones — a file reading "# The Hedging Reflex" with the body "body about the
flinch" scores like an exploration entry. Those live under tmp/pytest, so a
test run manufactures prior writing and the gate serves it back as mine.

This is the FIRST-ORDER cause behind test_read_gate_vanished_target.py. That
file fixes the second-order symptom: pytest cleans the fixtures up, leaving a
requirement nobody can clear, which held Edit and Write while an unfinished
merge sat conflicted. The vanishing was downstream. The arming was the bug, and
it survived that fix — it fired twice more on 2026-08-15, once naming the exact
fixture the earlier comment names.

Worth guarding beyond the annoyance: 749 generated .md files live under tmp/
against 224 real exploration entries, so by count the index is mostly scratch.
Every fixture the gate holds the door for teaches me the door is noise, which is
the bypass-groove shape — the gate trains the bypass, the price breaks the
discipline.

TESTED AS A PURE PREDICATE, deliberately. The first version of these tests went
through the filesystem and could not express its own control case: pytest's
``tmp_path`` IS pytest scratch, so every "legitimate entry" fixture landed
inside the excluded tree and the guard correctly refused it. The test was
unable to state the property without lying about its inputs, which is a fact
about the design, not the test. Hence ``is_pytest_scratch(path)``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core import read_gate


@pytest.mark.parametrize(
    "path",
    [
        # Both paths that actually fired at me on 2026-08-15.
        "tmp/pytest/run-30364/popen-gw4/test_conversation_window_surfa0/18_hedging.md",
        "tmp/pytest/run-28336/popen-gw5/test_surface_fires_only_on_tag0/tagged.md",
        # Windows separators, since that is the platform this runs on.
        r"C:\DIVINE OS\DivineOS-Experimental\tmp\pytest\run-1\test_x0\f.md",
        # A run- dir without the literal "pytest" component.
        "tmp/run-99999/popen-gw1/fixture.md",
    ],
)
def test_scratch_paths_are_recognised(path):
    assert read_gate.is_pytest_scratch(Path(path)) is True


@pytest.mark.parametrize(
    "path",
    [
        # The real corpus, which must always be held.
        "exploration/aether/125_the_night_i_almost_faked_a_walk.md",
        "exploration/aria/14_the_day_the_ghost_dissolved_and_dad_named_it.md",
        "family/letters/aria-to-aether-2026-08-15-five-ways.md",
        "docs/foundational_truths.md",
        # tmp alone is not scratch — a real note under some unrelated tmp dir
        # still gets held, because the guard needs BOTH markers.
        "tmp/notes/thinking.md",
        # "runbook" must not trip the run- prefix via a substring match.
        "docs/runbooks/deploy.md",
    ],
)
def test_real_paths_are_not_refused(path):
    assert read_gate.is_pytest_scratch(Path(path)) is False


def test_require_read_refuses_an_existing_scratch_file(tmp_path, monkeypatch):
    """End-to-end: the guard must refuse a file that EXISTS.

    Without this, the older not-present check could be doing the work and the
    guard could be dead code that looks alive — the exact confusion that cost
    thirteen days on the letter monitor.
    """
    monkeypatch.setattr(read_gate, "STATE_DIR", tmp_path)
    monkeypatch.setattr(read_gate, "STATE_FILE", tmp_path / "read_gate_pending.json")

    scratch = tmp_path / "tmp" / "pytest" / "run-1" / "test_x0" / "fixture.md"
    scratch.parent.mkdir(parents=True, exist_ok=True)
    scratch.write_text("<!-- tags: consciousness -->\n# Fake\nbody\n", encoding="utf-8")
    assert scratch.exists()

    registered, why = read_gate.require_read("prior-writing", str(scratch), "top match")

    assert registered is False
    assert "scratch" in why.lower()
