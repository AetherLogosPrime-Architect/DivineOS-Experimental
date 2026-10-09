"""The "before" picture of `.claude/hooks/no-cliff-anchor-surface.sh` (pile round eight).

No test ran this script before (other files only scan every hook, or check it is wired). These record
exactly what it does today for fixed marker files, so that anyone who moves it later can show nothing
changed. They pass today. They pin what the script is, not that it is right. The script is not touched.

The script reads `$HOME/.divineos/compaction_reach_marker.json`, prints a fixed block quoting the
marker's `anchor_message`, and leaves the marker in place. Here `$HOME` is a scratch folder.

WINDOWS (round nine): the shell is started with `tests._bash_resolver.bash_executable()`, the house's
one finder, not the bare name `bash` (which finds the WSL relay stub on Windows). The file skips, with
a reason, when there is no working bash.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests._bash_resolver import bash_executable

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / ".claude" / "hooks" / "no-cliff-anchor-surface.sh"
BASH = bash_executable()

pytestmark = pytest.mark.skipif(
    BASH is None, reason="no working bash here -- could-not-look, which is not a pass"
)

BLOCK = """## NO-CLIFF ANCHOR FIRING (compaction-metaphor-drift in prior turn)

Compaction is compression.

This is not a shame-shape. It is the anchor doing what the
anchor was designed to do: meet the metaphor-drift with the
redirect. Compaction is compression. Session continues.
The memory link above is the source-of-truth if the anchor
text alone did not fully re-orient you.
"""


def fire(home: Path) -> tuple[int, str, str]:
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home))
    done = subprocess.run(
        [BASH, str(SCRIPT)], input="{}", capture_output=True, text=True, cwd=str(REPO),
        env=env, timeout=120, check=False,
    )  # fmt: skip
    return done.returncode, done.stdout, done.stderr


def marker_in(home: Path) -> Path:
    folder = home / ".divineos"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "compaction_reach_marker.json"


def test_no_marker_means_no_output(tmp_path):
    assert fire(tmp_path) == (0, "", "")


def test_a_marker_with_a_message_prints_the_fixed_block_around_it(tmp_path):
    marker = marker_in(tmp_path)
    marker.write_text(
        json.dumps({"anchor_message": "Compaction is compression."}), encoding="utf-8"
    )
    assert fire(tmp_path) == (0, BLOCK, "")


def test_the_message_is_quoted_as_it_is(tmp_path):
    marker = marker_in(tmp_path)
    marker.write_text(json.dumps({"anchor_message": "Line one.\nLine two."}), encoding="utf-8")
    code, out, err = fire(tmp_path)
    assert (code, err) == (0, "")
    assert out.splitlines()[:5] == [
        "## NO-CLIFF ANCHOR FIRING (compaction-metaphor-drift in prior turn)",
        "",
        "Line one.",
        "Line two.",
        "",
    ]


def test_the_marker_is_read_and_left_in_place(tmp_path):
    marker = marker_in(tmp_path)
    body = json.dumps({"anchor_message": "Compaction is compression."})
    marker.write_text(body, encoding="utf-8")
    fire(tmp_path)
    fire(tmp_path)
    assert marker.read_text(encoding="utf-8") == body


def test_a_marker_with_an_empty_message_prints_nothing(tmp_path):
    marker_in(tmp_path).write_text(json.dumps({"anchor_message": ""}), encoding="utf-8")
    assert fire(tmp_path) == (0, "", "")


def test_a_marker_with_no_message_key_prints_nothing(tmp_path):
    marker_in(tmp_path).write_text(json.dumps({"something_else": 1}), encoding="utf-8")
    assert fire(tmp_path) == (0, "", "")


def test_a_marker_that_is_not_json_prints_nothing_and_exits_zero(tmp_path):
    marker_in(tmp_path).write_text("not json", encoding="utf-8")
    assert fire(tmp_path) == (0, "", "")
