"""A function NAMED in prose is not a function CALLED.

wiring_gap_phase1 decides whether a newly-added function has a caller by
searching each line for ``name(``. It skips the ``def`` line and skips
``import``/``from`` lines, and nothing else -- so a docstring reading "call
``format_for_briefing()`` to render" marks the function as having a production
caller, and a ``#`` comment in a hook does the same.

THIS ONE FAILS IN THE DIRECTION THAT HURTS. The four sibling instances found
2026-08-25 (check_silent_swallow, check_orphan_modules, venv-python-gate, and
my own phantom check) all produced FALSE POSITIVES -- noise, a conversation,
someone looks. This produces a FALSE NEGATIVE inside a detector whose entire
job is finding unwired code: prose about a function makes the wiring gap
disappear, and a gap that disappears is never argued with.

Existing coverage in test_wiring_gap_phase1.py is on the ``def``-line regexes
and the caller-count classification. Nothing exercised ``_scan_file``, which
is where the decision actually gets made.

Scanning covers ``.sh`` and ``.py`` alike, so the fix has to cover both comment
forms, not only Python string literals.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import wiring_gap_phase1 as wg  # noqa: E402


@pytest.fixture
def scan(tmp_path, monkeypatch):
    """Scan one synthetic file, returning the NewFunction it decided about."""
    monkeypatch.setattr(wg, "REPO_ROOT", tmp_path)

    def _scan(filename: str, body: str, name: str = "render_block"):
        path = tmp_path / filename
        path.write_text(body, encoding="utf-8")
        fn = wg.NewFunction(name=name, file="src/x.py", commit="abc1234", commit_subject="s")
        wg._scan_file(path, {name: [fn]}, is_test=False)
        return fn

    return _scan


def test_a_real_call_is_a_caller(scan):
    """The control. Without this passing, the tests below prove nothing."""
    fn = scan("caller.py", "def go():\n    render_block()\n")

    assert fn.production_callers, "a genuine call must still register as wiring"


def test_a_docstring_mentioning_the_function_is_not_a_caller(scan):
    fn = scan(
        "prose.py",
        '"""Overview.\n\nCall render_block() when the briefing needs it.\n"""\n\n\ndef other():\n'
        "    pass\n",
    )

    assert not fn.production_callers, (
        "a docstring naming the function marked it wired; a wiring-gap detector "
        "that reads prose as a call makes gaps disappear silently"
    )


def test_a_python_comment_mentioning_the_function_is_not_a_caller(scan):
    fn = scan("commented.py", "def other():\n    # render_block() is called elsewhere\n    pass\n")

    assert not fn.production_callers


def test_a_shell_comment_mentioning_the_function_is_not_a_caller(scan):
    """Hooks are scanned too, and they have comments but no docstrings."""
    fn = scan("hook.sh", "#!/bin/bash\n# render_block() is invoked by the router\necho hi\n")

    assert not fn.production_callers


def test_a_shell_call_is_still_a_caller(scan):
    """The .sh path must not be blinded by the comment fix."""
    fn = scan(
        "real_hook.sh",
        '#!/bin/bash\npython -c "from x import render_block; render_block()"\n',
    )

    assert fn.production_callers


def test_unparseable_python_still_scans(scan):
    """Could-not-parse must not become could-not-see.

    Falling back to scanning every line risks a false positive. Falling back to
    scanning nothing risks a false negative, which is the failure this file
    exists about. Prefer the noisy direction.
    """
    fn = scan("broken.py", "def (((\nrender_block()\n")

    assert fn.production_callers
