"""Proof-test (pile round nine): the ranking-clause hook looks for a heading the real character sheet no longer has.

`.claude/hooks/load-dad-ranking-clause.sh` loads one section of `docs/identity_anchors/aether_character_sheet.md`
at session start: the one whose heading is `## How I rank Dad`. The sheet has no such heading now. The
nearest section is `## How I treat Dad -- equal-treatment discipline (added 2026-07-28, axis-corrected
2026-07-29)`, and a note under it says an earlier version of that section was reframed. It looks like the
heading was replaced when the section was rewritten, but this clone is shallow, so I could not read the old
sheet text to confirm it. Either way the hook finds nothing and prints nothing, every session, with no error.

This test does not touch the hook or the sheet. It reads the heading the hook looks for out of the hook's own
source, so it follows the hook if the hook changes, and asks two things of the real sheet: does it hold that
heading, and does the hook print anything when run over a copy of it? Controls show the probe is alive: the
heading is found in the hook, the real sheet has other headings, and the same copy WITH the heading appended
makes the hook print.

Both questions fail today for the one reason. Either repair (restore the heading, or point the hook at the
current one) turns them to passes, and `strict=True` then rings.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from tests._bash_resolver import bash_executable

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / ".claude" / "hooks" / "load-dad-ranking-clause.sh"
SHEET = REPO / "docs" / "identity_anchors" / "aether_character_sheet.md"
BASH = bash_executable()

needs_bash = pytest.mark.skipif(
    BASH is None, reason="no working bash here -- could-not-look, which is not a pass"
)


def heading_the_hook_looks_for() -> str:
    found = re.search(r"re\.search\(r'(## [^.]+?)\.\*\?", HOOK.read_text(encoding="utf-8"))
    assert found, "the hook no longer has a re.search for a '## ' heading; update this test"
    return found.group(1)


def sheet_headings() -> list[str]:
    return [
        line for line in SHEET.read_text(encoding="utf-8").splitlines() if line.startswith("## ")
    ]


def run_hook_over(sheet_text: str, tmp_path: Path) -> str:
    """Run the hook in a scratch repo holding `sheet_text` as the character sheet; return what it prints."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    hooks = repo / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy(REPO / ".claude" / "hooks" / "_lib.sh", hooks / "_lib.sh")
    # the house's python resolver accepts only a python whose divineos lives under THIS repo's src
    os.symlink(REPO / "src", repo / "src")
    target = repo / "docs" / "identity_anchors" / "aether_character_sheet.md"
    target.parent.mkdir(parents=True)
    target.write_text(sheet_text, encoding="utf-8")
    home = tmp_path / "home"
    home.mkdir()
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home), PYTHONPATH=str(REPO / "src"))
    done = subprocess.run(
        [BASH, str(HOOK)], input="{}", capture_output=True, text=True, cwd=str(repo),
        env=env, timeout=120, check=False,
    )  # fmt: skip
    assert done.returncode == 0, done.stderr
    return done.stdout


def test_control_the_heading_is_read_out_of_the_hook():
    assert heading_the_hook_looks_for().startswith("## ")


def test_control_the_real_sheet_is_readable_and_has_other_headings():
    assert "## Andrew is my father" in sheet_headings()


@needs_bash
def test_control_the_hook_prints_when_the_heading_is_present(tmp_path):
    heading = heading_the_hook_looks_for()
    text = SHEET.read_text(encoding="utf-8") + f"\n{heading}\n\nA clause for the control.\n"
    out = run_hook_over(text, tmp_path)
    assert "A clause for the control." in out


@pytest.mark.xfail(
    strict=True,
    reason="reproduces: the heading the hook looks for is not in the real sheet",
)
def test_the_real_sheet_has_the_heading_the_hook_looks_for():
    heading = heading_the_hook_looks_for()
    assert heading in sheet_headings(), (
        f"the hook looks for {heading!r}; the real sheet's headings are:\n  "
        + "\n  ".join(sheet_headings())
    )


@needs_bash
@pytest.mark.xfail(
    strict=True,
    reason="reproduces: run over a copy of the real sheet, the hook prints nothing (session start gets no clause)",
)
def test_the_hook_prints_the_clause_over_a_copy_of_the_real_sheet(tmp_path):
    out = run_hook_over(SHEET.read_text(encoding="utf-8"), tmp_path)
    assert out.strip(), "the hook printed nothing over a copy of the real character sheet"
