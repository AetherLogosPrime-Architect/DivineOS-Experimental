"""The lighter branch rule must find the folder a shell line acts in.

Found 2026-10-12: a line starting ``cd /c/w-behind && git add ...`` fell back to the strict
gate every time, because ``/c/w-behind`` is not a folder to Python on Windows; and a quoted
folder with a space in its name (``cd "C:/DIVINE OS/..."``) was split in half by a plain
``split()``. Either way target_dir returned None, which the caller treats as "stay strict".
"""

from __future__ import annotations

import shlex

import sys
from pathlib import Path

import pytest

from divineos.core.council_required.push_choke import target_dir


def test_a_quoted_folder_with_a_space_is_one_folder(tmp_path):
    spaced = tmp_path / "a folder with spaces"
    spaced.mkdir()
    got = target_dir((), f'cd "{spaced.as_posix()}" && git add x', Path("."))
    assert got == spaced


def test_git_dash_c_with_a_quoted_folder_is_read_too(tmp_path):
    spaced = tmp_path / "another spaced one"
    spaced.mkdir()
    got = target_dir((), f'git -C "{spaced.as_posix()}" add x', Path("."))
    assert got == spaced


@pytest.mark.skipif(sys.platform != "win32", reason="git-bash drive paths only exist on Windows")
def test_a_git_bash_style_drive_path_is_the_folder_windows_knows(tmp_path):
    drive, rest = tmp_path.as_posix().split(":", 1)  # C:/Users/... -> C, /Users/...
    shell_style = f"/{drive.lower()}{rest}"
    assert target_dir((), f"cd {shlex.quote(shell_style)} && git add x", Path(".")) == tmp_path


def test_control_a_folder_that_does_not_exist_is_could_not_tell(tmp_path):
    # The instrument must be able to say "cannot tell", or the passes above prove nothing.
    assert target_dir((), f'cd "{(tmp_path / "nope").as_posix()}" && git add x', Path(".")) is None
