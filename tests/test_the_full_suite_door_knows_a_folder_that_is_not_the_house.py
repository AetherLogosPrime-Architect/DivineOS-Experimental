"""A pytest run in a folder that is not the house is not the house's whole suite.

The door refuses a hand-run of the full suite (Dad, 2026-09-09: it takes 15 to 20 minutes and the
push runs it anyway). After a `cd` it treated wherever the shell stood as "the repository", which is
right for `cd src` inside the house and wrong for an unrelated folder: `cd C:/monopoly-play && python
-m pytest tests -q` ran 150 tests of a different project in under a second and was refused as the
house's whole suite, five times in one night (2026-11-28), each costing a rewrite of a harmless line.

A place the shell has `cd`ed to counts as the house only if it is inside the house or is itself a
house checkout (a clone or worktree, which has src/divineos). The conservative defaults stay: a cd the
door cannot follow still counts as everything.
"""

from pathlib import Path

from divineos.core.full_suite_by_hand import decide


def _house(tmp_path: Path) -> Path:
    house = tmp_path / "house"
    (house / "src" / "divineos").mkdir(parents=True)
    (house / "tests").mkdir()
    return house


def _folder(tmp_path: Path, name: str, house_like: bool = False) -> Path:
    folder = tmp_path / name
    (folder / "tests").mkdir(parents=True)
    if house_like:
        (folder / "src" / "divineos").mkdir(parents=True)
    return folder


def test_a_pytest_run_in_an_unrelated_folder_is_not_the_houses_whole_suite(tmp_path):
    house = _house(tmp_path)
    other = _folder(tmp_path, "monopoly")
    assert decide(f"cd {other.as_posix()} && python -m pytest tests -q", repo=house) is None


def test_a_bare_pytest_in_an_unrelated_folder_is_allowed_too(tmp_path):
    house = _house(tmp_path)
    other = _folder(tmp_path, "monopoly")
    assert decide(f"cd {other.as_posix()} && python -m pytest -q", repo=house) is None


def test_a_pytest_run_in_a_clone_of_the_house_is_still_refused(tmp_path):
    house = _house(tmp_path)
    clone = _folder(tmp_path, "w-copy", house_like=True)
    assert decide(f"cd {clone.as_posix()} && python -m pytest tests -q", repo=house) is not None


def test_a_pytest_run_after_a_cd_to_the_house_itself_is_still_refused(tmp_path):
    house = _house(tmp_path)
    assert decide(f"cd {house.as_posix()} && python -m pytest tests -q", repo=house) is not None


def test_the_run_from_a_subfolder_of_the_house_stays_refused(tmp_path):
    # Aria, 2026-10-04: `cd src && pytest ../tests` ran everything
    house = _house(tmp_path)
    assert decide("cd src && pytest ../tests", repo=house) is not None


def test_a_cd_the_door_cannot_follow_still_counts_as_everything(tmp_path):
    house = _house(tmp_path)
    assert decide("cd $SOMEWHERE && pytest tests -q", repo=house) is not None


def test_a_cd_to_a_folder_that_does_not_exist_cannot_be_placed_so_it_counts_as_everything(tmp_path):
    # the door's own principle: a place it cannot place is the one a route around it would use
    house = _house(tmp_path)
    missing = tmp_path / "wcopy-that-is-not-there"
    assert decide(f"cd {missing.as_posix()} && python -m pytest tests -q", repo=house) is not None


def test_naming_one_test_file_in_an_unrelated_folder_is_allowed(tmp_path):
    house = _house(tmp_path)
    other = _folder(tmp_path, "monopoly")
    (other / "tests" / "test_x.py").write_text("")
    assert decide(f"cd {other.as_posix()} && pytest tests/test_x.py -q", repo=house) is None


def test_the_plain_run_in_the_house_with_no_cd_is_still_refused(tmp_path):
    house = _house(tmp_path)
    assert decide("pytest tests -q", repo=house) is not None
