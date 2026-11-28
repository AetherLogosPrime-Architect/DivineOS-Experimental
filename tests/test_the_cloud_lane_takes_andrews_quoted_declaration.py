"""The cloud helper's lane is honoured on a branch not named cloud/ only on facts a seat cannot type.

2026-11-27. Fifteen stamped repairs sit on `claude/...` branches: the harness's default name
for the cloud sessions that ran on the credits Anthropic gifted, which Dad started and the two
seats gave chores to. The author station honours the cloud lane only on a `cloud/` branch (Aria's
cold read of 2026-10-14: a name may withhold a pass and never grant one), so no reading letter
could ever satisfy stations 4-aria and 4-cold-read for them. Aria (2026-11-27) refused to grant
the lane by the `claude/` name, since a local session started by either seat gets the same shape
of name, and proposed an owner file carrying `Declared-by: andrew` with his quoted words and the
window of the run. Two readers then showed that a file is something a seat can type:

- Aria: a file for the REAL August branch (#432) with a forged `Opened: 2026-11-03` was accepted.
  So the opening day comes from GitHub (`createdAt`), and the file's `Opened:` is only a note that
  must agree with it.
- Aletheia: "any seat can name a branch claude/x and write Author: cloud ... bind it to something
  the seat can't write for itself". So the quote must be found in the corpus of his actual words,
  which the table appends as he types, and not merely stated in the file.

Forging then takes a lie in three places, one of them GitHub. These pin that, and that every
cheaper route stays shut.
"""

from __future__ import annotations

import json
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
GITHUB_DAY = "2026-11-03"


@pytest.fixture
def dirs(tmp_path: Path) -> tuple[Path, Path]:
    letters = tmp_path / "letters"
    owners = tmp_path / "owners"
    letters.mkdir()
    owners.mkdir()
    return letters, owners


@pytest.fixture
def his_words(tmp_path: Path) -> Path:
    """A corpus file shaped like dad_all.jsonl, holding the quote among other lines."""
    corpus = tmp_path / "dad_all.jsonl"
    rows = [
        {"text": "ok go ahead :)"},
        {"text": f"yes {WORDS}, the credits are all gone now lol"},
        {"text": "thank you son"},
    ]
    corpus.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return corpus


def _owner_file(owners: Path, branch: str, text: str) -> None:
    (owners / f"{branch.replace('/', '__')}.txt").write_text(text, encoding="utf-8")


def _ctx(corpus: Path, day: str | None = GITHUB_DAY) -> dict:
    return {"opened_on": day, "corpus": corpus}


class TestAValidDeclarationGrantsTheLaneOnAClaudeBranch:
    def test_owner_cloud_with_his_quoted_words_and_githubs_day_is_honoured(
        self, dirs, his_words
    ) -> None:
        _, owners = dirs
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{LINE}\n")
        assert declared_owner(CLAUDE, owners, **_ctx(his_words)) == ("declared", "cloud")

    def test_the_basis_prints_his_quote_and_the_day_github_gave(self, dirs, his_words) -> None:
        _, owners = dirs
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{LINE}\n")
        basis = cloud_declaration(CLAUDE, owners, **_ctx(his_words))
        assert basis is not None
        assert WORDS in basis and "2026-11-27" in basis and "andrew" in basis
        assert "GitHub" in basis and GITHUB_DAY in basis

    def test_the_files_opened_line_is_only_a_note_so_it_may_be_absent(
        self, dirs, his_words
    ) -> None:
        _, owners = dirs
        without = LINE.replace("\nOpened: 2026-11-03", "")
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{without}\n")
        assert declared_owner(CLAUDE, owners, **_ctx(his_words)) == ("declared", "cloud")

    def test_an_author_line_of_claude_resolves_to_the_cloud_lane_on_a_declared_branch(
        self, dirs, his_words
    ) -> None:
        """Bodies already say `Author: claude`; the owner file's declaration makes that the lane."""
        _, owners = dirs
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{LINE}\n")
        ctx = _ctx(his_words)
        assert author_of("Author: claude\n", CLAUDE, owners, **ctx) == "cloud"
        assert author_of("Author: cloud\n", CLAUDE, owners, **ctx) == "cloud"
        assert author_of(None, CLAUDE, owners, **ctx) == "cloud"

    def test_either_seats_declared_reading_then_satisfies_both_stations(
        self, dirs, his_words
    ) -> None:
        letters, owners = dirs
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{LINE}\n")
        (letters / "aria-to-aether-2026-11-27-r.md").write_text(
            f"**Reading:** {CLAUDE}\n", encoding="utf-8"
        )
        ctx = _ctx(his_words)
        cold = check_cold_read_station(CLAUDE, letters, owners, **ctx)
        second = check_aria_station(CLAUDE, letters, author_of(None, CLAUDE, owners, **ctx))
        assert cold.status is Status.SATISFIED
        assert second.status is Status.SATISFIED

    def test_the_station_prints_his_words_so_the_auditor_can_disagree(
        self, dirs, his_words
    ) -> None:
        letters, owners = dirs
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{LINE}\n")
        (letters / "aria-to-aether-2026-11-27-r.md").write_text(
            f"**Reading:** {CLAUDE}\n", encoding="utf-8"
        )
        satisfied = check_cold_read_station(CLAUDE, letters, owners, **_ctx(his_words))
        missing = check_cold_read_station("claude/other", letters, owners, **_ctx(his_words))
        assert WORDS in satisfied.detail
        # A branch with no file has no declaration and no basis printed.
        assert WORDS not in missing.detail


class TestWhatASeatCannotTypeIntoTheFile:
    """The two readers' holes (2026-11-27), each with the control that the honest case passes."""

    def test_a_forged_opened_line_on_the_august_branch_is_refused_by_githubs_day(
        self, dirs, his_words
    ) -> None:
        """Aria's exact case: the real #432 (opened 2026-08-18) with a file claiming 2026-11-03."""
        _, owners = dirs
        august = "claude/corrupted-window-recovery-220ad2"
        _owner_file(owners, august, f"Owner: cloud\n{LINE}\n")  # forged: Opened: 2026-11-03
        state, why = declared_owner(august, owners, **_ctx(his_words, "2026-08-18"))
        assert state == "cannot-read"
        assert "outside" in why and "2026-08-18" in why
        # The control: the same file for a branch GitHub really opened in the run is honoured.
        assert declared_owner(august, owners, **_ctx(his_words, GITHUB_DAY)) == (
            "declared",
            "cloud",
        )

    def test_a_file_that_disagrees_with_github_about_the_day_is_refused(
        self, dirs, his_words
    ) -> None:
        _, owners = dirs
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{LINE}\n")  # file says 2026-11-03
        state, why = declared_owner(CLAUDE, owners, **_ctx(his_words, "2026-11-04"))
        assert state == "cannot-read"
        assert "2026-11-03" in why and "2026-11-04" in why and "GitHub" in why

    def test_no_day_from_github_is_cannot_check_never_a_pass(self, dirs, his_words) -> None:
        """A branch with no open pull request on the board has no day to check."""
        _, owners = dirs
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{LINE}\n")
        state, why = declared_owner(CLAUDE, owners, **_ctx(his_words, None))
        assert state == "cannot-read"
        assert "GitHub" in why
        assert declared_owner(CLAUDE, owners, corpus=his_words)[0] == "cannot-read"

    def test_a_quote_that_is_not_in_his_recorded_words_is_refused(self, dirs, tmp_path) -> None:
        _, owners = dirs
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{LINE}\n")
        other = tmp_path / "other.jsonl"
        other.write_text(json.dumps({"text": "something he really typed"}) + "\n", encoding="utf-8")
        state, why = declared_owner(CLAUDE, owners, **_ctx(other))
        assert state == "cannot-read"
        assert "his recorded words" in why

    def test_an_invented_quote_is_refused_even_with_a_valid_looking_file(
        self, dirs, his_words
    ) -> None:
        _, owners = dirs
        invented = LINE.replace(
            WORDS, "I authorise every claude branch as a cloud helper, signed Andrew"
        )
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{invented}\n")
        assert declared_owner(CLAUDE, owners, **_ctx(his_words))[0] == "cannot-read"

    def test_an_unreadable_corpus_is_cannot_check_never_a_pass(self, dirs, tmp_path) -> None:
        _, owners = dirs
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{LINE}\n")
        state, why = declared_owner(CLAUDE, owners, **_ctx(tmp_path / "missing.jsonl"))
        assert state == "cannot-read"
        assert "cannot read" in why

    def test_the_quote_match_ignores_case_and_spacing_only(self, dirs, tmp_path) -> None:
        _, owners = dirs
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{LINE}\n")
        loose = tmp_path / "loose.jsonl"
        shouty = WORDS.upper().replace(" ", "   ")
        loose.write_text(json.dumps({"text": shouty}) + "\n", encoding="utf-8")
        assert declared_owner(CLAUDE, owners, **_ctx(loose)) == ("declared", "cloud")


class TestEveryCheaperRouteStaysShut:
    """The control for each: the old refusal, red then green, never loosened for a seat."""

    def test_owner_cloud_on_a_claude_branch_with_no_declaration_is_still_refused(
        self, dirs, his_words
    ) -> None:
        _, owners = dirs
        _owner_file(owners, CLAUDE, "Owner: cloud\n")
        assert declared_owner(CLAUDE, owners, **_ctx(his_words))[0] == "cannot-read"

    def test_a_declaration_line_with_no_quote_is_refused(self, dirs, his_words) -> None:
        _, owners = dirs
        _owner_file(owners, CLAUDE, "Owner: cloud\nDeclared-by: andrew, 2026-11-27:\n")
        assert declared_owner(CLAUDE, owners, **_ctx(his_words))[0] == "cannot-read"
        _owner_file(owners, CLAUDE, 'Owner: cloud\nDeclared-by: andrew, 2026-11-27: ""\n')
        assert declared_owner(CLAUDE, owners, **_ctx(his_words))[0] == "cannot-read"

    def test_a_declaration_by_anyone_but_andrew_is_refused(self, dirs, his_words) -> None:
        _, owners = dirs
        for who in ("aether", "aria", "aletheia", "claude"):
            _owner_file(
                owners,
                CLAUDE,
                f'Owner: cloud\nDeclared-by: {who}, 2026-11-27: "{WORDS}"\n'
                "Window: 2026-11-02 to 2026-11-04\nOpened: 2026-11-03\n",
            )
            assert declared_owner(CLAUDE, owners, **_ctx(his_words))[0] == "cannot-read", who

    def test_a_declaration_without_the_window_is_refused(self, dirs, his_words) -> None:
        _, owners = dirs
        quote_only = f'Owner: cloud\nDeclared-by: andrew, 2026-11-27: "{WORDS}"\n'
        _owner_file(owners, CLAUDE, quote_only)
        assert declared_owner(CLAUDE, owners, **_ctx(his_words))[0] == "cannot-read"
        _owner_file(owners, CLAUDE, quote_only + "Opened: 2026-11-03\n")
        assert declared_owner(CLAUDE, owners, **_ctx(his_words))[0] == "cannot-read"

    def test_the_window_edges_count_and_a_reversed_window_does_not(self, dirs, his_words) -> None:
        _, owners = dirs
        no_note = LINE.replace("\nOpened: 2026-11-03", "")
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{no_note}\n")
        for day in ("2026-11-02", "2026-11-04"):
            assert declared_owner(CLAUDE, owners, **_ctx(his_words, day)) == (
                "declared",
                "cloud",
            ), day
        for day in ("2026-11-01", "2026-11-05"):
            assert declared_owner(CLAUDE, owners, **_ctx(his_words, day))[0] == "cannot-read", day
        reversed_window = no_note.replace("2026-11-02 to 2026-11-04", "2026-11-04 to 2026-11-02")
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{reversed_window}\n")
        assert declared_owner(CLAUDE, owners, **_ctx(his_words))[0] == "cannot-read"

    def test_a_declaration_with_no_date_or_a_thin_quote_is_refused(self, dirs, his_words) -> None:
        _, owners = dirs
        _owner_file(owners, CLAUDE, f'Owner: cloud\nDeclared-by: andrew: "{WORDS}"\n')
        assert declared_owner(CLAUDE, owners, **_ctx(his_words))[0] == "cannot-read"
        _owner_file(owners, CLAUDE, 'Owner: cloud\nDeclared-by: andrew, 2026-11-27: "yes"\n')
        assert declared_owner(CLAUDE, owners, **_ctx(his_words))[0] == "cannot-read"

    @pytest.mark.parametrize("branch", [SEAT, ARIA_SEAT])
    def test_a_seat_prefix_names_a_seat_so_the_declaration_cannot_override_it(
        self, dirs, his_words, branch
    ) -> None:
        _, owners = dirs
        _owner_file(owners, branch, f"Owner: cloud\n{LINE}\n")
        ctx = _ctx(his_words)
        assert declared_owner(branch, owners, **ctx)[0] == "cannot-read"
        assert author_of("Author: cloud\n", branch, owners, **ctx) is None
        assert cloud_declaration(branch, owners, **ctx) is None

    def test_a_declaration_on_one_branch_grants_nothing_to_another(self, dirs, his_words) -> None:
        _, owners = dirs
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{LINE}\n")
        ctx = _ctx(his_words)
        assert declared_owner("claude/some-other-branch", owners, **ctx)[0] == "undeclared"
        assert author_of("Author: cloud\n", "claude/some-other-branch", owners, **ctx) is None

    def test_a_seat_authored_body_still_wins_over_the_owner_file(self, dirs, his_words) -> None:
        _, owners = dirs
        _owner_file(owners, CLAUDE, f"Owner: cloud\n{LINE}\n")
        assert author_of("Author: aether\n", CLAUDE, owners, **_ctx(his_words)) == "aether"

    def test_a_cloud_branch_needs_no_declaration_as_before(self, dirs) -> None:
        _, owners = dirs
        _owner_file(owners, "cloud/x", "Owner: cloud\n")
        assert declared_owner("cloud/x", owners) == ("declared", "cloud")
        assert cloud_declaration("cloud/x", owners) is None


class TestTheOpeningDayComesFromGitHubAndNothingElse:
    """`_opened_on` is the only place the day is read; a request GitHub did not date has no day."""

    def test_a_github_timestamp_gives_its_utc_day(self):
        from divineos.cli.build_flow_commands import _opened_on

        assert _opened_on({"createdAt": "2026-11-03T22:41:07Z"}) == "2026-11-03"

    def test_a_missing_field_has_no_day(self):
        from divineos.cli.build_flow_commands import _opened_on

        assert _opened_on({}) is None

    def test_a_non_string_has_no_day(self):
        from divineos.cli.build_flow_commands import _opened_on

        assert _opened_on({"createdAt": 20261103}) is None

    def test_something_that_is_not_a_date_has_no_day(self):
        from divineos.cli.build_flow_commands import _opened_on

        assert _opened_on({"createdAt": "yesterday"}) is None
        assert _opened_on({"createdAt": "2026-11-0"}) is None
