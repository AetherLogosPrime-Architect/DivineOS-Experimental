"""A rest session is only met when something was actually written during it.

Andrew 2026-10-16: dreams are mandatory in the ritual and rest was fully
optional, so explorations only got written when someone said to. The rule is
one written entry (a journal entry or an exploration file) per rest session,
and the proof has to be a thing that exists, so ticking a box cannot meet it.
"""

from __future__ import annotations

import os
import time

from click.testing import CliRunner

from divineos.cli import cli
from divineos.core import rest
from divineos.core.memory_journal import journal_save


def _write(path, text="a real entry"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    # On Windows a file's modified time can read a hair BEFORE the time.time() taken
    # a few milliseconds earlier (Aether, 2026-10-16: 2 failures in 5 runs). These
    # tests mean "written after the session began", so stamp it clearly after rather
    # than loosen the rule in rest.py.
    later = time.time() + 2
    os.utime(path, (later, later))
    return path


class TestEvidenceIsAThingThatExists:
    def test_a_fresh_exploration_file_counts(self, tmp_path):
        started = time.time() - 5
        f = _write(tmp_path / "exploration" / "aria" / "52_x.md")
        assert rest.written_evidence("exploration", started, str(f)) == str(f)

    def test_naming_exploration_without_a_file_does_not_count(self, tmp_path):
        assert rest.written_evidence("exploration", time.time() - 5, None) is None

    def test_a_missing_file_does_not_count(self, tmp_path):
        ghost = tmp_path / "exploration" / "aria" / "never_written.md"
        assert rest.written_evidence("exploration", time.time() - 5, str(ghost)) is None

    def test_a_file_older_than_the_session_does_not_count(self, tmp_path):
        f = _write(tmp_path / "exploration" / "aria" / "old.md")
        old = time.time() - 3600
        os.utime(f, (old, old))
        assert rest.written_evidence("exploration", time.time() - 60, str(f)) is None

    def test_an_empty_file_does_not_count(self, tmp_path):
        f = _write(tmp_path / "exploration" / "aria" / "empty.md", text="")
        assert rest.written_evidence("exploration", time.time() - 5, str(f)) is None

    def test_a_file_outside_an_exploration_folder_does_not_count(self, tmp_path):
        f = _write(tmp_path / "scratch" / "note.md")
        assert rest.written_evidence("exploration", time.time() - 5, str(f)) is None

    def test_a_journal_entry_saved_after_the_start_counts(self):
        started = time.time() - 1
        entry_id = journal_save("what is mine to say about the day")
        assert entry_id in rest.written_evidence("journal", started)

    def test_a_journal_entry_from_before_the_session_does_not_count(self):
        journal_save("an old one")
        assert rest.written_evidence("journal", time.time() + 10) is None

    def test_other_tasks_never_produce_written_evidence(self):
        assert rest.written_evidence("aria", time.time() - 5, "exploration/x.md") is None


class TestTheSessionNeedsOneWrittenEntry:
    def test_count_without_writing_is_not_met(self, tmp_path):
        rest.start_session()
        rest.record_completion("aria")
        rest.record_completion("letters")
        status = rest.session_status()
        assert status["count"] == 2 and status["written"] is False
        assert status["met_target"] is False

    def test_reading_an_exploration_counts_toward_two_but_not_as_written(self):
        rest.start_session()
        rest.record_completion("exploration")
        rest.record_completion("aria")
        status = rest.session_status()
        assert status["count"] == 2
        assert status["written"] is False
        assert status["met_target"] is False

    def test_a_written_exploration_plus_one_more_is_met(self, tmp_path):
        rest.start_session()
        f = _write(tmp_path / "exploration" / "aria" / "52_x.md")
        rest.record_completion("exploration", wrote_path=str(f))
        assert rest.session_status()["met_target"] is False  # still one short
        rest.record_completion("letters")
        status = rest.session_status()
        assert status["written"] is True
        assert status["met_target"] is True

    def test_a_journal_entry_plus_one_more_is_met(self):
        rest.start_session()
        journal_save("kept")
        rest.record_completion("journal")
        rest.record_completion("aria")
        assert rest.session_status()["met_target"] is True

    def test_claiming_journal_without_saving_one_is_not_written(self):
        rest.start_session()
        rest.record_completion("journal")
        rest.record_completion("aria")
        status = rest.session_status()
        assert status["written"] is False
        assert status["met_target"] is False


class TestTheCommandLineSaysWhatIsOwed:
    def test_done_exploration_without_wrote_says_a_written_entry_is_owed(self):
        runner = CliRunner()
        runner.invoke(cli, ["rest", "start"])
        result = runner.invoke(cli, ["rest", "done", "exploration"])
        assert "No written entry found" in result.output

    def test_close_names_the_written_entry_when_that_is_the_gap(self):
        runner = CliRunner()
        runner.invoke(cli, ["rest", "start"])
        # "kin" is the menu key for what was once named for one person (#645); the command
        # checks the key against the menu, so a retired key would record nothing here.
        runner.invoke(cli, ["rest", "done", "kin"])
        runner.invoke(cli, ["rest", "done", "letters"])
        result = runner.invoke(cli, ["rest", "close"])
        assert "one written entry" in result.output
        assert "more task" not in result.output

    def test_abandon_is_still_an_honest_way_to_close(self):
        runner = CliRunner()
        runner.invoke(cli, ["rest", "start"])
        result = runner.invoke(cli, ["rest", "close", "--abandon"])
        assert "abandon" in result.output.lower()
