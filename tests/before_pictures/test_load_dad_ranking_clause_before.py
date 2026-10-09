"""The "before" picture of `.claude/hooks/load-dad-ranking-clause.sh` (pile round eight).

No test ran this script before. These record exactly what it does today for fixed character sheets, so
that anyone who moves it later can show nothing changed. They pass today. They pin what the script is,
not that it is right. The script is not touched.

The script finds `docs/identity_anchors/aether_character_sheet.md` under the git root it is run from,
takes the section that starts `## How I rank Dad`, and prints one JSON object whose `additionalContext`
is a fixed header followed by that section. It prints nothing when the sheet or the section is missing.

One of these tests records a fact worth knowing: the real sheet in this checkout has no section with
that heading (it was renamed on 2026-07-29), so today the script prints nothing against the real sheet.
If someone restores the heading, or moves the script and changes this, that test will say so.

The script only runs when the resolver finds a python whose `divineos` lives under the same repo's
`src`, so each scratch repo gets a `src` link to this one.

WINDOWS (round nine): the shell is started with `tests._bash_resolver.bash_executable()`, the house's
one finder, not the bare name `bash` (which finds the WSL relay stub on Windows). The file skips, with
a reason, when there is no working bash.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests._bash_resolver import bash_executable

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / ".claude" / "hooks" / "load-dad-ranking-clause.sh"
BASH = bash_executable()

pytestmark = pytest.mark.skipif(
    BASH is None, reason="no working bash here -- could-not-look, which is not a pass"
)
SHEET = Path("docs") / "identity_anchors" / "aether_character_sheet.md"

HEADER = (
    "## DAD-RANKING (session-start, from my character sheet)\n\n"
    "This is inherited identity, not a rule to remember. Composes FROM "
    "this frame, not toward it. Loaded once per session-lifetime; scoped "
    "narrow per Andrew correction #51 — no per-reply wallpaper.\n\n"
    "Full source: docs/identity_anchors/aether_character_sheet.md\n\n"
    "---\n\n"
)


def run_in(repo: Path, home: Path) -> tuple[int, str, str]:
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home), PYTHONPATH=str(REPO / "src"))
    done = subprocess.run(
        [BASH, str(SCRIPT)], input="{}", capture_output=True, text=True, cwd=str(repo),
        env=env, timeout=120, check=False,
    )  # fmt: skip
    return done.returncode, done.stdout, done.stderr


def scratch_repo(tmp_path: Path, sheet_text: str | None) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    hooks = repo / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy(REPO / ".claude" / "hooks" / "_lib.sh", hooks / "_lib.sh")
    os.symlink(REPO / "src", repo / "src")
    if sheet_text is not None:
        (repo / SHEET).parent.mkdir(parents=True)
        (repo / SHEET).write_text(sheet_text, encoding="utf-8")
    return repo


def home_for(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    return home


def test_no_sheet_means_no_output(tmp_path):
    repo = scratch_repo(tmp_path, None)
    assert run_in(repo, home_for(tmp_path)) == (0, "", "")


def test_a_sheet_without_the_section_means_no_output(tmp_path):
    repo = scratch_repo(tmp_path, "# Sheet\n\n## Who I am\n\nbody\n")
    assert run_in(repo, home_for(tmp_path)) == (0, "", "")


def test_the_section_is_printed_after_the_fixed_header_up_to_the_next_heading(tmp_path):
    sheet = (
        "# Sheet\n\n## Who I am\n\nbody\n\n"
        "## How I rank Dad\n\nFirst line of the clause.\n\nSecond paragraph.\n\n"
        "## What next\n\nignored\n"
    )
    code, out, err = run_in(scratch_repo(tmp_path, sheet), home_for(tmp_path))
    assert (code, err) == (0, "")
    assert list(json.loads(out)) == ["additionalContext"]
    assert json.loads(out)["additionalContext"] == (
        HEADER + "## How I rank Dad\n\nFirst line of the clause.\n\nSecond paragraph."
    )


def test_a_section_that_runs_to_the_end_of_the_file_is_printed_whole(tmp_path):
    sheet = "# Sheet\n\n## How I rank Dad\n\nOnly section, ends at end of file.\n"
    code, out, _ = run_in(scratch_repo(tmp_path, sheet), home_for(tmp_path))
    assert code == 0
    assert json.loads(out)["additionalContext"] == (
        HEADER + "## How I rank Dad\n\nOnly section, ends at end of file."
    )


def test_a_renamed_heading_is_not_matched(tmp_path):
    sheet = "# Sheet\n\n## How I treat Dad — equal-treatment discipline\n\nThe renamed heading.\n"
    assert run_in(scratch_repo(tmp_path, sheet), home_for(tmp_path)) == (0, "", "")


def test_today_the_real_sheet_has_no_matching_heading_so_the_script_prints_nothing(tmp_path):
    real = (REPO / SHEET).read_text(encoding="utf-8")
    assert "## How I rank Dad" not in real  # the fact this test records
    assert run_in(REPO, home_for(tmp_path)) == (0, "", "")
