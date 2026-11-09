"""A command that closes one of Dad's rows shows the store and the row first, and refuses a mismatch.

Draft: docs/drafts/a_correction_command_shows_the_row_and_store_before_it_closes_it_draft_2026-11-09.md
Walk: walk-0ac923c59307.

The incident, 2026-11-09: I read the oldest open asks from one store, then ran
`integrate` and `misfiled` for the same row numbers against a different store,
where those numbers are other corrections, and closed four of his real words
with evidence about something else. Nothing on the screen could have told me.

The main test replays that: two temporary stores holding DIFFERENT rows under
the same ids, and the command run against the wrong one.
"""

import subprocess
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from divineos.cli.andrew_correction_commands import register
from divineos.core import andrew_correction_tracker as act

REPO = Path(__file__).resolve().parents[1]

ROW_A = "you are literally flooding me in information my brain CANNOT process all at once"
ROW_B = "i have never punished either of you for failure my anger is due to a precise few things"
OTHER_STORE_ROW = "yes also the hard block at 920K should not interrupt you mid flow"


@pytest.fixture
def cli():
    group = click.Group()
    register(group)
    return group


def _use_store(monkeypatch, path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(act, "divineos_home", lambda: path)


def _run(cli, *args):
    return CliRunner().invoke(cli, ["andrew-correction", *args])


def _status(correction_id: int) -> str:
    conn = act._conn()
    try:
        return conn.execute(
            "SELECT status FROM andrew_corrections WHERE id = ?", (correction_id,)
        ).fetchone()[0]
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def _in_the_repo(monkeypatch, tmp_path):
    monkeypatch.chdir(REPO)
    _use_store(monkeypatch, tmp_path / "mine")


def test_the_real_incident_is_refused_and_the_row_stays_open(cli, monkeypatch, tmp_path):
    """Two stores, one id, different rows: the command run against the wrong one."""
    _use_store(monkeypatch, tmp_path / "other seat")
    other_id = act.file_correction(OTHER_STORE_ROW)
    _use_store(monkeypatch, tmp_path / "mine")
    mine_id = act.file_correction(ROW_A)
    assert mine_id == other_id, "the probe needs the same id in both stores"

    result = _run(
        cli,
        "integrate",
        str(mine_id),
        "--evidence",
        "Done: see src/divineos/core/andrew_correction_tracker.py for the buffer",
        "--expect-text",
        OTHER_STORE_ROW[:30],
    )
    assert result.exit_code != 0
    assert _status(mine_id) == "OPEN"
    assert ROW_A[:40] in result.output, "the refusal must show the row's true start"


def test_a_matching_expectation_closes_the_row_and_the_output_names_store_and_words(cli, tmp_path):
    cid = act.file_correction(ROW_A)
    result = _run(
        cli,
        "integrate",
        str(cid),
        "--evidence",
        "Landed in src/divineos/core/andrew_correction_tracker.py as one verdict",
        "--expect-text",
        ROW_A[:30],
    )
    assert result.exit_code == 0, result.output
    assert _status(cid) == "INTEGRATED"
    assert str(tmp_path / "mine") in result.output.replace("\\", "/") or "mine" in result.output
    assert ROW_A[:40] in result.output


def test_the_expectation_is_required_not_optional(cli):
    cid = act.file_correction(ROW_A)
    result = _run(cli, "integrate", str(cid), "--evidence", "Landed in tests/test_cli.py ok")
    assert result.exit_code != 0
    assert "expect-text" in result.output.lower()
    assert _status(cid) == "OPEN"


@pytest.mark.parametrize(
    "too_short", ["", "abc", "short one", "12345678901", "you are literally floo"]
)
def test_an_expectation_under_twenty_letters_or_digits_is_refused(cli, too_short):
    cid = act.file_correction(ROW_A)
    result = _run(
        cli,
        "integrate",
        str(cid),
        "--evidence",
        "Landed in tests/test_cli.py to prove it",
        "--expect-text",
        too_short,
    )
    assert result.exit_code != 0
    assert "20" in result.output
    assert _status(cid) == "OPEN"


# Aether's cold read, 2026-11-09: counting the first twelve letters and digits of all
# 857 rows in his store, 430 rows share their opening with at least one other row
# (54 shared openings; the biggest is 96 rows of templated gate text, then 41 rows
# beginning "Andrew 2026-08"). So what a person pastes proved the date and the
# speaker, not the row. The speaker, date and marker are now set aside first, the
# floor applies to what is left, and the words must point at ONE row in the store.
TWIN_A = "Andrew 2026-08-09: you are literally flooding me in information at once"
TWIN_B = "Andrew 2026-08-09: i have never punished either of you for failure at all"


def test_a_speaker_and_date_alone_prove_nothing(cli):
    cid = act.file_correction(TWIN_A)
    act.file_correction(TWIN_B)
    result = _run(
        cli,
        "integrate",
        str(cid),
        "--evidence",
        "Landed in tests/test_cli.py to prove it",
        "--expect-text",
        "Andrew 2026-08-09: and a little more",
    )
    assert result.exit_code != 0
    assert _status(cid) == "OPEN"


def test_the_speaker_and_date_are_set_aside_before_the_floor_is_counted(cli):
    cid = act.file_correction(TWIN_A)
    act.file_correction(TWIN_B)
    result = _run(
        cli,
        "integrate",
        str(cid),
        "--evidence",
        "Landed in tests/test_cli.py to prove it",
        "--expect-text",
        "Andrew 2026-08-09: you are literally flooding me",
    )
    assert result.exit_code == 0, result.output


def test_words_that_also_begin_another_row_are_refused_with_the_count(cli):
    first = act.file_correction("the gate said stop and this one was about the buffer limit")
    act.file_correction("the gate said stop and this one was about the doorman instead")
    result = _run(
        cli,
        "integrate",
        str(first),
        "--evidence",
        "Landed in tests/test_cli.py to prove it",
        "--expect-text",
        "the gate said stop and this one",
    )
    assert result.exit_code != 0
    assert "1 other" in result.output
    assert _status(first) == "OPEN"


def test_more_of_the_row_tells_it_apart_from_its_twin(cli):
    first = act.file_correction("the gate said stop and this one was about the buffer limit")
    act.file_correction("the gate said stop and this one was about the doorman instead")
    result = _run(
        cli,
        "integrate",
        str(first),
        "--evidence",
        "Landed in tests/test_cli.py to prove it",
        "--expect-text",
        "the gate said stop and this one was about the buffer",
    )
    assert result.exit_code == 0, result.output


SHORT_ROW = "Andrew 2026-09-08: ok yes"


def test_a_row_with_no_more_words_than_its_lead_in_is_closed_by_the_whole_row(cli):
    """Aether's third read: nothing more to paste, so do not say 'paste more'."""
    cid = act.file_correction(SHORT_ROW)
    result = _run(
        cli,
        "integrate",
        str(cid),
        "--evidence",
        "Landed in tests/test_cli.py to prove it",
        "--expect-text",
        SHORT_ROW,
    )
    assert result.exit_code == 0, result.output


def test_a_wrong_expectation_for_a_short_row_says_the_row_has_no_more_words(cli):
    cid = act.file_correction(SHORT_ROW)
    result = _run(
        cli,
        "integrate",
        str(cid),
        "--evidence",
        "Landed in tests/test_cli.py to prove it",
        "--expect-text",
        "Andrew 2026-09-08: no",
    )
    assert result.exit_code != 0
    assert "no more words" in result.output
    assert "paste more" not in result.output.lower()
    assert _status(cid) == "OPEN"


def test_two_rows_with_identical_words_may_be_closed_by_their_opening(cli):
    """Aether's store has 93 rows with an identical twin; making each paste its whole
    text (the longest is over a thousand letters) would punish a harmless case."""
    words = "the same words filed twice by two gates, nothing different at all"
    first = act.file_correction(words)
    act.file_correction(words)
    result = _run(
        cli,
        "integrate",
        str(first),
        "--evidence",
        "Landed in tests/test_cli.py to prove it",
        "--expect-text",
        "the same words filed twice by two gates",
    )
    assert result.exit_code == 0, result.output


def test_two_rows_with_identical_words_may_be_closed_by_the_whole_text(cli):
    words = "the same words filed twice by two gates, nothing different at all"
    first = act.file_correction(words)
    act.file_correction(words)
    result = _run(
        cli,
        "integrate",
        str(first),
        "--evidence",
        "Landed in tests/test_cli.py to prove it",
        "--expect-text",
        words,
    )
    assert result.exit_code == 0, result.output


def test_case_spacing_and_punctuation_do_not_fail_a_true_match(cli):
    cid = act.file_correction("Dad: 'yes   also the hard block at 920K should not interrupt'")
    result = _run(
        cli,
        "integrate",
        str(cid),
        "--evidence",
        "Landed in src/divineos/core/context_governor.py thresholds",
        "--expect-text",
        "DAD yes also the HARD block",
    )
    assert result.exit_code == 0, result.output


def test_garbled_characters_in_a_row_do_not_fail_a_true_match(cli):
    garbled = "ok thanks ðŸ™‚ and yes the block should hold the work"
    cid = act.file_correction(garbled)
    result = _run(
        cli,
        "integrate",
        str(cid),
        "--evidence",
        "Landed in src/divineos/core/context_governor.py thresholds",
        "--expect-text",
        "ok thanks and yes the block",
    )
    assert result.exit_code == 0, result.output


def test_a_missing_id_is_refused_before_any_text_is_compared(cli):
    result = _run(
        cli,
        "integrate",
        "99999",
        "--evidence",
        "Landed in tests/test_cli.py to prove it",
        "--expect-text",
        "anything long enough here",
    )
    assert result.exit_code != 0
    assert "99999" in result.output
    assert "not found" in result.output.lower()


COMMANDS = {
    "integrate": ["--evidence", "Landed in tests/test_cli.py to prove it"],
    "misfiled": ["--belongs", "Belongs in the kindness he has shown, not a task"],
    "defer": ["--reason", "Waits on a decision that is his to make, named here"],
    "propose-hold": ["--why", "This reads as grief about the ones he lost, not a task"],
    "confirm-hold": [],
    "unhold": [],
}


@pytest.mark.parametrize("command", sorted(COMMANDS))
def test_every_row_changing_command_refuses_a_wrong_expectation_and_shows_the_row(cli, command):
    """A rule over the whole list, not three copies of one test."""
    cid = act.file_correction(ROW_B)
    before = _status(cid)
    result = _run(
        cli,
        command,
        str(cid),
        *COMMANDS[command],
        "--expect-text",
        "this is a different row altogether",
    )
    assert result.exit_code != 0, f"{command} accepted a wrong expectation"
    assert _status(cid) == before, f"{command} changed the row despite the mismatch"
    assert ROW_B[:40] in result.output, f"{command} did not show the row's true start"


@pytest.mark.parametrize("command", ["integrate", "misfiled", "defer", "propose-hold"])
def test_every_row_changing_command_prints_the_row_before_it_changes_it(cli, command):
    cid = act.file_correction(ROW_B)
    result = _run(
        cli,
        command,
        str(cid),
        *COMMANDS[command],
        "--expect-text",
        ROW_B[:30],
    )
    assert result.exit_code == 0, f"{command}: {result.output}"
    assert ROW_B[:40] in result.output
    assert "mine" in result.output.replace("\\", "/")


def _real_commit() -> str:
    done = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        pytest.skip("git could not name a commit")
    return done.stdout.strip()


def test_the_commit_route_prints_the_row_words_it_closed(cli):
    """auto-integrate cannot take row words from a commit message, so it shows them."""
    cid = act.file_correction(ROW_A)
    commit = _real_commit()
    result = _run(
        cli,
        "auto-integrate",
        "--message",
        f"Fix the buffer. Closes correction #{cid}. See src/divineos/core/context_governor.py",
        "--commit-hash",
        commit,
    )
    assert result.exit_code == 0, result.output
    assert ROW_A[:40] in result.output, "the commit route must show the words it closed"
    assert "mine" in result.output.replace("\\", "/")
