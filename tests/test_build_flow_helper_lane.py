"""The cloud helper gets its own declared place in the readiness check.

Dad, 2026-10-10: "def give it its own place so it can be monitored and separated
from your thinking in case it messes up." Sixteen of 33 waiting requests came
from it and none could pass the author-side station, because the check only had
two possible writers and a reader from the other seat. Writing a seat's name on
the helper's work would turn the other seat's reading into a pairing that never
existed. These pin the third declared writer without relaxing anything: no
declared reading means no pass, and a seat's own work still needs the OTHER
seat (walk-da68247868ce).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core.build_flow import (
    Status,
    author_of,
    check_aria_station,
    check_cold_read_station,
    declared_owner,
)

CLOUD = "cloud/fix-the-thing"
SEAT_BRANCH = "aether/my-own-fix"


@pytest.fixture
def dirs(tmp_path: Path) -> tuple[Path, Path]:
    letters = tmp_path / "letters"
    owners = tmp_path / "owners"
    letters.mkdir()
    owners.mkdir()
    return letters, owners


def _own(owners: Path, branch: str, who: str) -> None:
    (owners / f"{branch.replace('/', '__')}.txt").write_text(f"Owner: {who}\n", encoding="utf-8")


def _reading(letters: Path, sender: str, branch: str | None) -> None:
    value = branch if branch else "none"
    (letters / f"{sender}-to-x-2026-10-10-a.md").write_text(
        f"# a letter\n**Reading:** {value}\n", encoding="utf-8"
    )


class TestTheCloudHelperCanBeDeclaredOwner:
    def test_the_owner_file_may_name_cloud_on_a_cloud_branch(self, dirs) -> None:
        _, owners = dirs
        _own(owners, CLOUD, "cloud")
        assert declared_owner(CLOUD, owners) == ("declared", "cloud")

    def test_a_cloud_owner_on_a_branch_not_named_cloud_is_refused(self, dirs) -> None:
        """The cheap route: declare cloud on a branch I wrote so my own reading
        counts as an outside one. A name may withhold a pass, never grant one."""
        _, owners = dirs
        _own(owners, SEAT_BRANCH, "cloud")
        state, _ = declared_owner(SEAT_BRANCH, owners)
        assert state == "cannot-read"

    def test_seats_are_declared_as_before(self, dirs) -> None:
        _, owners = dirs
        _own(owners, SEAT_BRANCH, "aether")
        assert declared_owner(SEAT_BRANCH, owners) == ("declared", "aether")

    def test_a_seat_and_the_helper_naming_one_branch_is_contested(self, dirs) -> None:
        _, owners = dirs
        (owners / f"{CLOUD.replace('/', '__')}.txt").write_text(
            "Owner: cloud, aether\n", encoding="utf-8"
        )
        assert declared_owner(CLOUD, owners)[0] == "contested"


class TestEitherSeatMayReadTheHelpersWorkCold:
    def test_arias_reading_satisfies_the_cold_read(self, dirs) -> None:
        letters, owners = dirs
        _own(owners, CLOUD, "cloud")
        _reading(letters, "aria", CLOUD)
        assert check_cold_read_station(CLOUD, letters, owners).status is Status.SATISFIED

    def test_my_reading_satisfies_it_too(self, dirs) -> None:
        letters, owners = dirs
        _own(owners, CLOUD, "cloud")
        _reading(letters, "aether", CLOUD)
        assert check_cold_read_station(CLOUD, letters, owners).status is Status.SATISFIED

    def test_no_declared_reading_by_anyone_is_not_a_pass(self, dirs) -> None:
        letters, owners = dirs
        _own(owners, CLOUD, "cloud")
        _reading(letters, "aria", "some/other-branch")
        _reading(letters, "aether", None)
        assert check_cold_read_station(CLOUD, letters, owners).status is Status.MISSING

    def test_an_aether_branch_still_needs_arias_reading_not_his_own(self, dirs) -> None:
        """The control: nothing was loosened for the seats."""
        letters, owners = dirs
        _own(owners, SEAT_BRANCH, "aether")
        _reading(letters, "aether", SEAT_BRANCH)
        assert check_cold_read_station(SEAT_BRANCH, letters, owners).status is Status.MISSING
        _reading(letters, "aria", SEAT_BRANCH)
        assert check_cold_read_station(SEAT_BRANCH, letters, owners).status is Status.SATISFIED


class TestWhoWroteItComesFromADeclarationNeverAName:
    def test_the_requests_own_author_line_wins(self, dirs) -> None:
        _, owners = dirs
        _own(owners, CLOUD, "cloud")
        assert author_of("Author: aether\n", CLOUD, owners) == "aether"

    def test_with_no_author_line_a_cloud_owner_makes_the_author_cloud(self, dirs) -> None:
        _, owners = dirs
        _own(owners, CLOUD, "cloud")
        assert author_of("no author line here", CLOUD, owners) == "cloud"
        assert author_of(None, CLOUD, owners) == "cloud"

    def test_a_cloud_branch_name_alone_declares_nothing(self, dirs) -> None:
        _, owners = dirs
        assert author_of("", CLOUD, owners) is None

    def test_a_seat_owner_does_not_become_the_author(self, dirs) -> None:
        _, owners = dirs
        _own(owners, SEAT_BRANCH, "aether")
        assert author_of("", SEAT_BRANCH, owners) is None

    def test_a_cloud_owner_on_a_non_cloud_branch_declares_no_author(self, dirs) -> None:
        _, owners = dirs
        _own(owners, SEAT_BRANCH, "cloud")
        assert author_of("", SEAT_BRANCH, owners) is None


class TestTheSecondSeatStationForTheHelper:
    def test_either_seats_reading_satisfies_a_cloud_authored_request(self, dirs) -> None:
        letters, _ = dirs
        (letters / "aria-to-aether-2026-10-10-r.md").write_text(
            f"**Reading:** {CLOUD}\n", encoding="utf-8"
        )
        assert check_aria_station(CLOUD, letters, "cloud").status is Status.SATISFIED

    def test_my_reading_counts_for_the_helper_too(self, dirs) -> None:
        letters, _ = dirs
        (letters / "aether-to-aria-2026-10-10-r.md").write_text(
            f"**Reading:** {CLOUD}\n", encoding="utf-8"
        )
        assert check_aria_station(CLOUD, letters, "cloud").status is Status.SATISFIED

    def test_no_reading_by_either_is_missing_not_a_pass(self, dirs) -> None:
        letters, _ = dirs
        (letters / "aria-to-aether-2026-10-10-r.md").write_text(
            "**Reading:** none\n", encoding="utf-8"
        )
        assert check_aria_station(CLOUD, letters, "cloud").status is Status.MISSING

    def test_a_seat_authored_request_is_unchanged(self, dirs) -> None:
        """His own reading of his own branch must never satisfy it."""
        letters, _ = dirs
        (letters / "aether-to-aria-2026-10-10-r.md").write_text(
            f"**Reading:** {SEAT_BRANCH}\n", encoding="utf-8"
        )
        assert check_aria_station(SEAT_BRANCH, letters, "aether").status is Status.MISSING

    def test_the_message_names_the_helper_plainly(self, dirs) -> None:
        letters, _ = dirs
        (letters / "aria-to-aether-2026-10-10-r.md").write_text("**Reading:** none\n", "utf-8")
        assert "Aria or Aether" in check_aria_station(CLOUD, letters, "cloud").detail
