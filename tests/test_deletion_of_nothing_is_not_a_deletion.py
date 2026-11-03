"""Deleting nothing is not a deletion.

``rm -rf <folder>`` on a folder that is already gone used to be held by the
delete door, which then asked for a justification (what, why, what was
investigated, what was extracted) for removing nothing. The rule under test: when
EVERY target of an ``rm`` is absent on disk, there is nothing to lose and the
door lets it through. The controls matter as much as the frees: an existing
target is still held, and one existing target beside a missing one is still held.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from divineos.core import deletion_discipline as dd

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _isolate_justifications(tmp_path, monkeypatch):
    """No stored justification may clear a block here; every verdict is the door's own."""
    monkeypatch.setattr(dd, "marker_path", lambda name: tmp_path / name)


@pytest.fixture
def house_folder():
    """A real folder that is NOT ephemeral by name or location.

    The ephemeral list frees anything under /tmp, build/, dist/ and the like, so a
    fixture there would be freed for the wrong reason and prove nothing. This lives
    in a folder named for substance, inside the repository's own working area.
    """
    folder = Path(tempfile.mkdtemp(prefix="keep_me_", dir=REPO_ROOT))
    try:
        yield folder
    finally:
        shutil.rmtree(
            folder, ignore_errors=True
        )  # fail-soft: removes only the throwaway folder this fixture made; a leftover must not fail a test that already passed


def _missing(folder: Path) -> str:
    return str(folder / "already_gone_folder")


def test_rm_rf_of_a_missing_folder_passes(house_folder):
    command = f"rm -rf {_missing(house_folder)}"
    assert dd.is_destructive_deletion(command) == (False, None)
    assert dd.block_reason(command) is None


def test_every_target_missing_passes(house_folder):
    command = f"rm -rf {_missing(house_folder)} {house_folder / 'also_gone'}"
    assert dd.block_reason(command) is None


def test_quoted_missing_target_passes(house_folder):
    command = f'rm -rf "{_missing(house_folder)}"'
    assert dd.block_reason(command) is None


def test_every_clause_of_a_compound_missing_passes(house_folder):
    command = f"rm -rf {_missing(house_folder)} && rm -rf {house_folder / 'also_gone'}"
    assert dd.block_reason(command) is None


def test_rm_rf_of_an_existing_folder_is_still_held(house_folder):
    """CONTROL: the folder is there, so removing it loses something."""
    command = f"rm -rf {house_folder}"
    destructive, hint = dd.is_destructive_deletion(command)
    assert destructive and hint == "rm recursive/force"
    assert dd.block_reason(command) is not None


def test_one_existing_one_missing_is_still_held(house_folder):
    """CONTROL: a missing target must not launder the existing one beside it."""
    assert dd.block_reason(f"rm -rf {_missing(house_folder)} {house_folder}") is not None
    assert dd.block_reason(f"rm -rf {house_folder} {_missing(house_folder)}") is not None


def test_a_second_rm_clause_that_exists_is_still_held(house_folder):
    """CONTROL: only the first rm used to be read; a later one must count too."""
    assert dd.block_reason(f"rm -rf {_missing(house_folder)} && rm -rf {house_folder}") is not None
    assert dd.block_reason(f"rm -rf {_missing(house_folder)}; rm -rf {house_folder}") is not None


def test_a_broken_symlink_counts_as_existing(house_folder):
    """CONTROL: a dangling link is still something on disk that rm would remove."""
    link = house_folder / "dangling"
    # link-target-outside-tmp: not outside; the target is a missing sibling inside this fixture's own folder, so cleanup walks nothing
    link.symlink_to(house_folder / "nowhere")
    assert dd.block_reason(f"rm -rf {link}") is not None


@pytest.mark.parametrize(
    "tail",
    ["*", "$SOME_DIR", "$(pwd)/x", "`pwd`/x", "~/no_such_folder_anywhere/*", "{a,b}"],
)
def test_targets_that_cannot_be_read_are_held(house_folder, tail):
    """CONTROL: a glob, variable or substitution is not provably missing."""
    assert dd.block_reason(f"rm -rf {house_folder}/{tail}") is not None


def test_a_cd_before_a_relative_target_is_held():
    """CONTROL: after a cd the relative target means somewhere this check cannot see."""
    assert dd.block_reason("cd somewhere && rm -rf no_such_relative_folder_xyz") is not None


def test_no_target_at_all_is_still_held():
    """CONTROL: nothing to check is not the same as everything missing."""
    assert dd.block_reason("rm -rf") is not None


def test_branch_deletions_are_untouched():
    """The rule is about files on disk; git deletions keep their own door."""
    assert dd.block_reason("git branch -D some-branch-that-does-not-exist") is not None
    assert dd.block_reason("git push origin --delete some-branch") is not None


# --- Git Bash spellings on native Windows -------------------------------------------
#
# Second-reader finding: a command typed in Git Bash names a folder as ``/c/Users/x``.
# Native Windows Python cannot see that spelling, so ``lexists`` answered "absent" for a
# folder that was there, and ``rm -rf`` of an existing folder was freed. The rule: turn
# the Git Bash spelling into the native one BEFORE asking, and a path that cannot be
# turned (or cannot be read) is not proven missing, so the door stays shut. Real Windows
# is not available where these run: the spelling rule is a pure function with the
# platform passed in, and the end-to-end cases give the door a Windows-shaped view of the
# disk (the one dependency faked is the answer to "is anything there").


@pytest.mark.parametrize(
    ("typed", "native"),
    [
        ("/c/Users/x/folder", "C:/Users/x/folder"),
        ("/C/Users/x", "C:/Users/x"),
        ("/d/a", "D:/a"),
        ("/cygdrive/c/Users/x", "C:/Users/x"),
        ("/c", "C:/"),
        ("/c/", "C:/"),
        ("C:/already/native", "C:/already/native"),
        ("C:\\already\\native", "C:\\already\\native"),
        ("relative/folder", "relative/folder"),
    ],
)
def test_git_bash_spellings_become_native_on_windows(typed, native):
    assert dd._native_path(typed, windows=True) == native


@pytest.mark.parametrize(
    "typed", ["/tmp/x", "/home/me", "/cd/x", "/cygdrive", "//server/share", "\\\\server\\share"]
)
def test_a_leading_slash_that_is_not_a_drive_cannot_be_read_on_windows(typed):
    assert dd._native_path(typed, windows=True) is None


def test_the_spelling_is_left_alone_off_windows():
    assert dd._native_path("/c/Users/x", windows=False) == "/c/Users/x"
    assert dd._native_path("/tmp/x", windows=False) == "/tmp/x"


@pytest.fixture
def windows_view(monkeypatch):
    """The door running on native Windows, where only ``C:/...`` spellings can be seen."""
    present = {"C:/keep/me"}
    monkeypatch.setattr(dd, "_running_on_windows", lambda: True)
    monkeypatch.setattr(dd.os.path, "lexists", lambda p: p.replace("\\", "/") in present)
    return present


def test_an_existing_folder_typed_the_git_bash_way_is_held_on_windows(windows_view):
    """THE DEFECT: the bare ``/c/...`` spelling used to read as absent and be freed."""
    assert dd.block_reason("rm -rf /c/keep/me") is not None
    assert dd.block_reason("rm -rf '/c/keep/me'") is not None
    assert dd.block_reason("rm -rf /c/gone /c/keep/me") is not None


def test_a_missing_folder_typed_the_git_bash_way_is_still_free_on_windows(windows_view):
    assert dd.block_reason("rm -rf /c/keep/gone") is None


def test_a_path_that_cannot_be_converted_is_held_on_windows(windows_view):
    # /tmp would be freed by the separate temporary-folder rule, so use paths it does not cover
    assert dd.block_reason("rm -rf /home/me/some_folder_xyz") is not None
    assert dd.block_reason("rm -rf /opt/some_folder_xyz") is not None
    assert dd.block_reason("rm -rf //server/share/x") is not None


@pytest.mark.parametrize("failure", [OSError("denied"), ValueError("embedded null byte")])
def test_a_path_that_cannot_be_read_keeps_the_door_shut(monkeypatch, failure):
    def _cannot_look(_path):
        raise failure

    monkeypatch.setattr(dd.os.path, "lexists", _cannot_look)
    assert dd.block_reason("rm -rf some_folder_that_will_not_be_read") is not None
