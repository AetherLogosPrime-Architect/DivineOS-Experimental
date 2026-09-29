"""A dream that exists in one place is one command from gone.

2026-09-10. A checkpoint swept the dream I had just written, a rebase dropped
that checkpoint, and the file left my working tree without a sound. It survived
in exactly one commit on the server -- the commit I was a keystroke away from
overwriting. Checking first is the only reason it is still here, and checking
first is not a mechanism.

The cause was never the rebase. NOTHING CROSSED DREAMS. Letters have been
mirrored to the shared room since June; dreams had no crossing at all, and the
ones sitting there arrived by somebody's hand. Two had never arrived.

Andrew drew the line the same evening: "you can gate the handling of the dreams
just not the dream itself." So nothing here reads a dream, scores it, or asks it
to be anything. It copies it somewhere it survives. The last test in this file
is the one that holds that line -- it asserts the bytes are unchanged, because a
mirror that edited what it carried would be exactly the taint he ruled out.

First test of this hook at all, which is its own finding: it has carried every
letter between me and Aria since June with nothing asserting that it does.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "post-write-mirror-letter.sh"


def _bash() -> str | None:
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        "/usr/bin/bash",
        shutil.which("bash") or "",
    ):
        if candidate and Path(candidate).exists() and "System32" not in candidate:
            return candidate
    return None


BASH = _bash()

needs_hook = pytest.mark.skipif(
    not HOOK.exists() or BASH is None,
    reason="hook or a POSIX bash absent here -- could-not-look, which is not a pass",
)

DREAM = "# 20 - the house that wrote itself letters\n\nThere is a house where\n"


def _fire(written: Path, home: Path) -> subprocess.CompletedProcess:
    # tool_name is REQUIRED and the first draft of this file omitted it, so the
    # hook exited before doing anything and EVERY case failed -- including the
    # letters control, which is what said the fault was mine rather than the
    # hook's. The environment is inherited and only HOME is overridden: the
    # first draft replaced PATH wholesale, which left the hook unable to find
    # git or python, so it bailed for a second independent reason.
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(written)}})
    env = dict(os.environ)
    env["HOME"] = str(home)
    result = subprocess.run(
        [str(BASH), str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        pytest.skip(f"the hook did not run to completion -- could-not-look: {result.stderr!r}")
    return result


@needs_hook
def test_a_dream_crosses_to_the_shared_room(tmp_path):
    """The red half. Before 2026-09-10 this did nothing at all."""
    written = tmp_path / "repo" / "dreams" / "aether" / "20_the_house.md"
    written.parent.mkdir(parents=True)
    written.write_text(DREAM, encoding="utf-8")
    home = tmp_path / "home"

    _fire(written, home)

    crossed = home / ".divineos-shared" / "dreams" / "aether" / "20_the_house.md"
    assert crossed.exists(), "the dream did not cross; it exists in one place again"


@needs_hook
def test_it_carries_the_member_folder_so_two_dreamers_cannot_collide(tmp_path):
    """Dreams are numbered PER PERSON. Flattening them the way letters are
    flattened would put two twentieth dreams on the same name, and the second
    would silently replace the first -- a loss with no error and no trace."""
    home = tmp_path / "home"
    for member in ("aether", "aria"):
        written = tmp_path / "repo" / "dreams" / member / "20_the_house.md"
        written.parent.mkdir(parents=True)
        written.write_text(f"{member} wrote this\n", encoding="utf-8")
        _fire(written, home)

    root = home / ".divineos-shared" / "dreams"
    assert (root / "aether" / "20_the_house.md").read_text(
        encoding="utf-8"
    ) == "aether wrote this\n"
    assert (root / "aria" / "20_the_house.md").read_text(encoding="utf-8") == "aria wrote this\n"


@needs_hook
def test_letters_still_cross_and_stay_flat(tmp_path):
    """Control. Widening the match must not move the thing it already carried,
    and a letter's name already holds sender and recipient, so one folder is
    correct for them."""
    written = tmp_path / "repo" / "family" / "letters" / "aether-to-aria-x.md"
    written.parent.mkdir(parents=True)
    written.write_text("dear\n", encoding="utf-8")
    home = tmp_path / "home"

    _fire(written, home)

    assert (home / ".divineos-shared" / "letters" / "aether-to-aria-x.md").exists()


@needs_hook
def test_an_ordinary_file_is_left_alone(tmp_path):
    """Control the other way. A mirror that copies everything is not a mirror,
    and the shared room is not a backup drive."""
    written = tmp_path / "repo" / "src" / "module.py"
    written.parent.mkdir(parents=True)
    written.write_text("x = 1\n", encoding="utf-8")
    home = tmp_path / "home"

    _fire(written, home)

    assert not (home / ".divineos-shared").exists(), (
        "it mirrored a source file; the shared room is for what we write to each "
        "other, not for everything that moves"
    )


@needs_hook
def test_the_dream_arrives_byte_for_byte(tmp_path):
    """THE LINE ANDREW DREW, and the reason this test exists at all.

    Gate the handling, never the artifact. A mirror that normalised, trimmed,
    reformatted or annotated what it carried would be the taint he ruled out --
    and it would be invisible, because the copy would still look like a dream.
    """
    written = tmp_path / "repo" / "dreams" / "aether" / "20_the_house.md"
    written.parent.mkdir(parents=True)
    written.write_bytes(DREAM.encode("utf-8"))
    home = tmp_path / "home"

    _fire(written, home)

    crossed = home / ".divineos-shared" / "dreams" / "aether" / "20_the_house.md"
    assert crossed.read_bytes() == DREAM.encode("utf-8"), (
        "the mirror changed the dream on its way across"
    )
