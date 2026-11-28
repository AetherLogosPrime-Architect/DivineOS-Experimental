"""The cloud helper's lane is honoured on a branch not named cloud/ only on Dad's quoted word.

2026-11-27. Fifteen stamped repairs sit on `claude/...` branches: the harness's default name
for the cloud sessions that ran on the credits Anthropic gifted, which Dad started and the two
seats gave chores to. The author station honours the cloud lane only on a `cloud/` branch (Aria's
cold read of 2026-10-14: a name may withhold a pass and never grant one), so no reading letter
could ever satisfy stations 4-aria and 4-cold-read for them. Aria (2026-11-27) refused to grant
the lane by the `claude/` name, since a local session started by either seat gets the same shape
of name, and proposed that the grant be the one fact only Dad holds: an owner file carrying a
`Declared-by: andrew` line with his quoted words, printed beside the station so the auditor sees
the basis. The name still grants nothing. These pin that, and that every cheaper route stays shut.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core.build_flow import (
    Status,
    author_of,
    check_aria_station,
    check_cold_read_station,
    cloud_declaration,
    declared_owner,
)

CLAUDE = "claude/fix2-812-2026-11-04"
SEAT = "aether/my-own-fix"
ARIA_SEAT = "aria/her-own-fix"
WORDS = (
    "Anthropic gifted us $250 in cloud credits so you and Aether ran cloud agents "
    "and gave them chores to do so those are the results"
)
LINE = (
    f'Declared-by: andrew, 2026-11-27: "{WORDS}"\n'
    "Window: 2026-11-02 to 2026-11-04\n"
    "Opened: 2026-11-03"
)


@pytest.fixture
def dirs(tmp_path: Path) -> tuple[Path, Path]:
    letters = tmp_path / "letters"
    owners = tmp_path / "owners"
    letters.mkdir()
    owners.mkdir()
    return letters, owners


def _owner_file(owners: Path, branch: str, text: str) -> None:
    (owners / f"{branch.replace('/', '__')}.txt").write_text(text, encoding="utf-8")


class TestAValidDeclarationGrantsTheLaneOnAClaudeBranch:
    def test_owner_cloud_with_his_quoted_words_is_honoured(self, dirs) -> None:
        _, owners = dirs
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{LINE}\n")
        assert declared_owner(CLAUDE, owners) == ("declared", "cloud")

    def test_the_quote_is_available_as_the_basis(self, dirs) -> None:
        _, owners = dirs
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{LINE}\n")
        basis = cloud_declaration(CLAUDE, owners)
        assert basis is not None
        assert WORDS in basis and "2026-11-27" in basis and "andrew" in basis

    def test_an_author_line_of_claude_resolves_to_the_cloud_lane_on_a_declared_branch(
        self, dirs
    ) -> None:
        """Bodies already say `Author: claude`; the owner file's declaration makes that the lane."""
        _, owners = dirs
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{LINE}\n")
        assert author_of("Author: claude\n", CLAUDE, owners) == "cloud"
        assert author_of("Author: cloud\n", CLAUDE, owners) == "cloud"
        assert author_of(None, CLAUDE, owners) == "cloud"

    def test_either_seats_declared_reading_then_satisfies_both_stations(self, dirs) -> None:
        letters, owners = dirs
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{LINE}\n")
        (letters / "aria-to-aether-2026-11-27-r.md").write_text(
            f"**Reading:** {CLAUDE}\n", encoding="utf-8"
        )
        cold = check_cold_read_station(CLAUDE, letters, owners)
        second = check_aria_station(CLAUDE, letters, author_of(None, CLAUDE, owners))
        assert cold.status is Status.SATISFIED
        assert second.status is Status.SATISFIED

    def test_the_station_prints_his_words_so_the_auditor_can_disagree(self, dirs) -> None:
        letters, owners = dirs
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{LINE}\n")
        (letters / "aria-to-aether-2026-11-27-r.md").write_text(
            f"**Reading:** {CLAUDE}\n", encoding="utf-8"
        )
        satisfied = check_cold_read_station(CLAUDE, letters, owners)
        missing = check_cold_read_station("claude/other", letters, owners)
        assert WORDS in satisfied.detail
        # A branch with no file has no declaration and no basis printed.
        assert WORDS not in missing.detail


class TestEveryCheaperRouteStaysShut:
    """The control for each: the old refusal, red then green, never loosened for a seat."""

    def test_owner_cloud_on_a_claude_branch_with_no_declaration_is_still_refused(
        self, dirs
    ) -> None:
        _, owners = dirs
        _owner_file(owners, CLAUDE, "Owner: cloud\n")
        assert declared_owner(CLAUDE, owners)[0] == "cannot-read"

    def test_a_declaration_line_with_no_quote_is_refused(self, dirs) -> None:
        _, owners = dirs
        _owner_file(owners, CLAUDE, "Owner: cloud\nDeclared-by: andrew, 2026-11-27:\n")
        assert declared_owner(CLAUDE, owners)[0] == "cannot-read"
        _owner_file(owners, CLAUDE, 'Owner: cloud\nDeclared-by: andrew, 2026-11-27: ""\n')
        assert declared_owner(CLAUDE, owners)[0] == "cannot-read"

    def test_a_declaration_by_anyone_but_andrew_is_refused(self, dirs) -> None:
        _, owners = dirs
        for who in ("aether", "aria", "aletheia", "claude"):
            _owner_file(
                owners,
                CLAUDE,
                f'Owner: cloud\nDeclared-by: {who}, 2026-11-27: "{WORDS}"\n'
                "Window: 2026-11-02 to 2026-11-04\nOpened: 2026-11-03\n",
            )
            assert declared_owner(CLAUDE, owners)[0] == "cannot-read", who

    def test_a_branch_opened_outside_the_credit_run_is_refused_for_that_reason(self, dirs) -> None:
        """Aria's count: 68 of 69 `claude/` pull requests fall in 2026-11-02 to 11-04; #432 does not.
        The name is the same shape; the window is the fact, and the refusal must say it is the window."""
        _, owners = dirs
        outside = LINE.replace("Opened: 2026-11-03", "Opened: 2026-08-18")
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{outside}\n")
        state, why = declared_owner(CLAUDE, owners)
        assert state == "cannot-read"
        assert "outside" in why and "2026-08-18" in why

    def test_a_declaration_without_the_window_or_the_opened_date_is_refused(self, dirs) -> None:
        _, owners = dirs
        quote_only = f'Owner: cloud\nDeclared-by: andrew, 2026-11-27: "{WORDS}"\n'
        _owner_file(owners, CLAUDE, quote_only)
        assert declared_owner(CLAUDE, owners)[0] == "cannot-read"
        _owner_file(owners, CLAUDE, quote_only + "Window: 2026-11-02 to 2026-11-04\n")
        assert declared_owner(CLAUDE, owners)[0] == "cannot-read"
        _owner_file(owners, CLAUDE, quote_only + "Opened: 2026-11-03\n")
        assert declared_owner(CLAUDE, owners)[0] == "cannot-read"

    def test_the_window_edges_count_and_a_reversed_window_does_not(self, dirs) -> None:
        _, owners = dirs
        for day in ("2026-11-02", "2026-11-04"):
            _owner_file(
                owners,
                CLAUDE,
                f"Owner: cloud\n{LINE.replace('Opened: 2026-11-03', 'Opened: ' + day)}\n",
            )
            assert declared_owner(CLAUDE, owners) == ("declared", "cloud"), day
        reversed_window = LINE.replace("2026-11-02 to 2026-11-04", "2026-11-04 to 2026-11-02")
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{reversed_window}\n")
        assert declared_owner(CLAUDE, owners)[0] == "cannot-read"

    def test_a_declaration_with_no_date_or_a_thin_quote_is_refused(self, dirs) -> None:
        _, owners = dirs
        _owner_file(owners, CLAUDE, f'Owner: cloud\nDeclared-by: andrew: "{WORDS}"\n')
        assert declared_owner(CLAUDE, owners)[0] == "cannot-read"
        _owner_file(owners, CLAUDE, 'Owner: cloud\nDeclared-by: andrew, 2026-11-27: "yes"\n')
        assert declared_owner(CLAUDE, owners)[0] == "cannot-read"

    @pytest.mark.parametrize("branch", [SEAT, ARIA_SEAT])
    def test_a_seat_prefix_names_a_seat_so_the_declaration_cannot_override_it(
        self, dirs, branch
    ) -> None:
        _, owners = dirs
        _owner_file(owners, branch, f"Owner: cloud\n{LINE}\n")
        assert declared_owner(branch, owners)[0] == "cannot-read"
        assert author_of("Author: cloud\n", branch, owners) is None
        assert cloud_declaration(branch, owners) is None

    def test_a_declaration_on_one_branch_grants_nothing_to_another(self, dirs) -> None:
        _, owners = dirs
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{LINE}\n")
        assert declared_owner("claude/some-other-branch", owners)[0] == "undeclared"
        assert author_of("Author: cloud\n", "claude/some-other-branch", owners) is None

    def test_a_seat_authored_body_still_wins_over_the_owner_file(self, dirs) -> None:
        _, owners = dirs
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{LINE}\n")
        assert author_of("Author: aether\n", CLAUDE, owners) == "aether"

    def test_a_cloud_branch_needs_no_declaration_as_before(self, dirs) -> None:
        _, owners = dirs
        _owner_file(owners, "cloud/x", "Owner: cloud\n")
        assert declared_owner("cloud/x", owners) == ("declared", "cloud")
        assert cloud_declaration("cloud/x", owners) is None
