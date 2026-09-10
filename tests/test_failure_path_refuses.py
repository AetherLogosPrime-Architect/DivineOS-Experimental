"""The detector Aletheia asked for, and the tests that keep it honest.

I told her I had surveyed the tree by hand and found exactly one instance of a
handler that destroys its subject. She refused to confirm it and said why:

    "Grepping for `discard` across src/ returns dozens of files, almost all of
    them using the word for unrelated things. A count from that is a count of a
    WORD, not of a FORM. So I would be doing exactly what Aria has caught you
    doing twice this week: reporting a sweep from an instrument blind to what it
    is supposed to see."

Then she named the resolution instead of stopping at the refusal:

    "Your negative claim rests on one pass by one party, and my confirming it
    would rest on one pass by another. A DETECTOR MAKES IT A PROPERTY."

The detector found 64 sites where the question arises. I had found one.

These tests exist because a detector nobody has tried to fool is a hypothesis.
They check the two failure directions that matter: does it SEE the form it was
built for, and does it stay QUIET on the shape that merely looks like it.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_failure_path_refuses.py"
BASELINE = ROOT / "scripts" / "failure_path_refuses_baseline.txt"


def _module():
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import check_failure_path_refuses as mod
    finally:
        sys.path.pop(0)
    return mod


def _candidates(source: str, tmp_path: Path) -> list[tuple[int, str, str]]:
    mod = _module()
    path = tmp_path / "subject.py"
    path.write_text(source, encoding="utf-8")
    return mod._candidates_in(path)


def test_checker_exists():
    assert CHECKER.is_file()
    assert BASELINE.is_file(), "the backlog is half the mechanism"


def test_it_sees_the_shape_it_was_built_for(tmp_path):
    """The quality gate, reduced to its skeleton: crash -> refuse."""
    found = _candidates(
        "def run_gate(session):\n"
        "    try:\n"
        "        verdict = assess(session)\n"
        "    except OSError:\n"
        "        return False, ''\n"
        "    return True, verdict\n",
        tmp_path,
    )
    assert found, "the detector missed the exact shape it was written for"
    assert found[0][1] == "run_gate"


def test_it_sees_a_refusal_hidden_in_a_tuple(tmp_path):
    """The real one returned `(False, "")` -- the refusal was not the whole value."""
    found = _candidates(
        "def gate(x):\n"
        "    try:\n"
        "        v = check(x)\n"
        "    except ValueError:\n"
        "        return (False, None, 'unchecked')\n"
        "    return (True, v, 'ok')\n",
        tmp_path,
    )
    assert found, "a refusal in one slot of a tuple is still a refusal"


def test_it_stays_quiet_when_the_handler_permits(tmp_path):
    """The FIXED shape must not be flagged, or the fix looks like the defect.

    This is the quality gate after the repair: the handler still returns, but it
    returns permission-with-a-downgrade rather than refusal.
    """
    found = _candidates(
        "def run_gate(session):\n"
        "    try:\n"
        "        verdict = assess(session)\n"
        "    except OSError:\n"
        "        return True, 'HYPOTHESIS'\n"
        "    return True, verdict\n",
        tmp_path,
    )
    assert not found, (
        "the repaired shape was flagged; a detector that cannot tell the fix "
        "from the defect teaches people to ignore it"
    )


def test_it_stays_quiet_when_there_is_no_asymmetry(tmp_path):
    """A function that never permits has no privilege to withhold."""
    found = _candidates(
        "def lookup(key):\n"
        "    try:\n"
        "        return store[key]\n"
        "    except KeyError:\n"
        "        return None\n",
        tmp_path,
    )
    assert not found, (
        "a lookup returning None on a miss is not refusing anything -- flagging "
        "it would bury the real finding under a hundred correct ones"
    )


def test_an_unreadable_file_is_a_finding_not_a_pass(tmp_path):
    """Could-not-look must never render as nothing-to-see.

    This is the fault the whole session was about, so the detector built to
    catch that family must not commit it itself.
    """
    mod = _module()
    path = tmp_path / "broken.py"
    path.write_text("def oops(:\n", encoding="utf-8")
    found = mod._candidates_in(path)
    assert found, "an unparseable file was silently reported as clean"
    assert "unparseable" in found[0][1]


def test_baseline_separates_decided_from_merely_listed():
    """Sixty-four listed must never read as sixty-four cleared."""
    mod = _module()
    decided, enumerated = mod._load_baseline()
    assert decided, "no site has been read and judged, which cannot be right"
    assert enumerated, "the backlog section vanished"
    assert not (set(decided) & enumerated), "a site cannot be both decided and pending"
    for key, why in decided.items():
        assert len(why) > 40, (
            f"{key} is marked decided with no real reason; a one-word note is a "
            "judgement nobody made wearing the shape of one"
        )


@pytest.mark.timeout(300)
def test_the_tree_has_no_unlisted_sites():
    """Runs the real checker over the real tree. New sites must block."""
    proc = subprocess.run(
        [sys.executable, str(CHECKER)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=300,
    )
    assert proc.returncode == 0, (
        "the tree has refusal-on-crash sites that are neither decided nor "
        f"listed:\n{proc.stdout[-2000:]}"
    )
    assert "NOT yet adjudicated" in proc.stdout, (
        "the run stopped saying how many sites remain unjudged; that number is "
        "the one this whole mechanism exists to keep visible"
    )
