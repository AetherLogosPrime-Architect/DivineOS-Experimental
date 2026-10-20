"""The baton: one holder, passed by a letter that names real work, taken only from a silent holder."""

import json
import sqlite3
import subprocess
from pathlib import Path

import pytest

from divineos.core import baton

NOW = 1_000_000.0
HOUR = 3600.0


@pytest.fixture
def home(tmp_path):
    folder = tmp_path / "shared"
    (folder / "letters").mkdir(parents=True)
    return folder


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / "repo"
    path.mkdir()
    for args in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"]):
        subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)
    (path / "work.txt").write_text("done", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "commit", "-qm", "work"], check=True, capture_output=True
    )
    return path


def _sha(repo):
    out = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True
    )
    return out.stdout.strip()


def _letter(kind, **fields):
    lines = ["# a letter", "", f"**Baton:** {kind}"]
    lines += [f"**{k.capitalize()}:** {v}" for k, v in fields.items()]
    return "\n".join(lines) + "\n\n---\n\nbody\n"


def test_a_pass_naming_a_real_commit_flips_the_baton_and_is_logged(home, repo):
    baton._write_record(home, "aether", NOW)
    result = baton.handle_letter(
        "aether-to-aria-2026-10-16-x.md", _letter("pass", done=_sha(repo)), repo, home, NOW
    )
    assert "now aria's" in result
    assert baton.holder(home) == "aria"
    entry = json.loads((home / "baton_log.jsonl").read_text().splitlines()[-1])
    assert entry["kind"] == "pass" and entry["quality"] == "unjudged"


def test_a_pass_naming_a_real_file_counts(home, repo):
    baton._write_record(home, "aether", NOW)
    result = baton.handle_letter(
        "aether-to-aria-x.md", _letter("pass", done="work.txt"), repo, home, NOW
    )
    assert "now aria's" in result


def test_a_pass_naming_nothing_real_keeps_the_baton(home, repo):
    baton._write_record(home, "aether", NOW)
    result = baton.handle_letter(
        "aether-to-aria-x.md", _letter("pass", done="deadbeef0 missing.txt"), repo, home, NOW
    )
    assert result.startswith("refused") and baton.holder(home) == "aether"


def test_a_done_line_pointing_back_into_the_baton_folder_does_not_count(home, repo):
    baton._write_record(home, "aether", NOW)
    result = baton.handle_letter(
        "aether-to-aria-x.md", _letter("pass", done=str(home / "baton.json")), repo, home, NOW
    )
    assert result.startswith("refused") and baton.holder(home) == "aether"


def test_only_the_holder_can_pass_it(home, repo):
    baton._write_record(home, "aether", NOW)
    result = baton.handle_letter(
        "aria-to-aether-x.md", _letter("pass", done=_sha(repo)), repo, home, NOW
    )
    assert "does not hold" in result and baton.holder(home) == "aether"


def test_a_return_needs_a_reason_and_then_flips_it_back_without_blame(home, repo):
    baton._write_record(home, "aria", NOW)
    refused = baton.handle_letter("aria-to-aether-x.md", _letter("return"), repo, home, NOW)
    assert refused.startswith("refused") and baton.holder(home) == "aria"
    ok = baton.handle_letter(
        "aria-to-aether-x.md",
        _letter("return", reason="the work was not finished"),
        repo,
        home,
        NOW,
    )
    assert "now aether's" in ok and baton.holder(home) == "aether"


def test_a_letter_with_no_baton_header_does_nothing(home, repo):
    baton._write_record(home, "aether", NOW)
    result = baton.handle_letter("aether-to-aria-x.md", "# hi\n\n---\nbody\n", repo, home, NOW)
    assert result == "no baton header" and baton.holder(home) == "aether"


def _tool_log(tmp_path, seat, *timestamps):
    """A seat's own store with its tool log, in the shape the house really writes."""
    seat_home = tmp_path / f"{seat}-home"
    (seat_home / "data").mkdir(parents=True)
    con = sqlite3.connect(seat_home / "data" / "event_ledger.db")
    con.execute(
        "CREATE TABLE tool_logbook (log_id TEXT PRIMARY KEY, timestamp REAL NOT NULL, "
        "event_type TEXT NOT NULL, tool_name TEXT NOT NULL DEFAULT 'Bash')"
    )
    for i, ts in enumerate(timestamps):
        con.execute("INSERT INTO tool_logbook VALUES (?, ?, 'TOOL_CALL', 'Bash')", (f"log-{i}", ts))
    con.commit()
    con.close()
    return {seat: str(seat_home)}


def test_the_waiting_seat_cannot_take_it_from_a_holder_seen_recently(home, tmp_path):
    baton._write_record(home, "aether", NOW)
    seats = _tool_log(tmp_path, "aether", NOW - HOUR)
    ok, why = baton.may_take("aria", home, NOW, seats)
    assert not ok and "last seen" in why


def test_silence_past_two_hours_without_a_waiting_letter_is_not_enough(home, tmp_path):
    baton._write_record(home, "aether", NOW)
    seats = _tool_log(tmp_path, "aether", NOW - 3 * HOUR)
    ok, why = baton.may_take("aria", home, NOW, seats)
    assert not ok and "no letter" in why


def test_the_newest_tool_use_is_what_counts_not_the_oldest(home, tmp_path):
    baton._write_record(home, "aether", NOW)
    seats = _tool_log(tmp_path, "aether", NOW - 9 * HOUR, NOW - HOUR)
    ok, why = baton.may_take("aria", home, NOW, seats)
    assert not ok and "last seen" in why


ARIA_HOME = Path("~/.divineos-aria").expanduser()
AETHER_HOME = Path("~/.divineos").expanduser()


def _stale_holder_with_a_letter_waiting(home, tmp_path):
    baton._write_record(home, "aether", NOW)
    seats = _tool_log(tmp_path, "aether", 1.0)  # long ago; the letter below is newer
    (home / "letters" / "aria-to-aether-2026-10-16-hello.md").write_text("hello", encoding="utf-8")
    return seats


def test_only_the_taker_itself_can_take_it(home, tmp_path, monkeypatch):
    seats = _stale_holder_with_a_letter_waiting(home, tmp_path)
    monkeypatch.setenv("DIVINEOS_HOME", str(AETHER_HOME))  # this window is aether, not aria
    result = baton.take("aria", home, NOW + 5 * HOUR, seats)
    assert result.startswith("refused: only aria") and baton.holder(home) == "aether"


def test_a_window_that_cannot_tell_its_seat_takes_nothing(home, tmp_path, monkeypatch):
    seats = _stale_holder_with_a_letter_waiting(home, tmp_path)
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path / "someone-else"))
    result = baton.take("aria", home, NOW + 5 * HOUR, seats)
    assert "unknown" in result and baton.holder(home) == "aether"


def test_the_command_line_refuses_an_unknown_seat_without_a_traceback(capsys):
    assert baton.main(["take", "foo"]) == 2
    assert "not a seat" in capsys.readouterr().err


def test_a_silent_holder_with_a_letter_waiting_can_be_taken_from_and_is_told(
    home, tmp_path, monkeypatch
):
    monkeypatch.setenv("DIVINEOS_HOME", str(ARIA_HOME))
    baton._write_record(home, "aether", NOW)
    seats = _tool_log(tmp_path, "aether", 1.0)  # long ago; the letter below is newer
    waiting = home / "letters" / "aria-to-aether-2026-10-16-hello.md"
    waiting.write_text("hello", encoding="utf-8")
    result = baton.take("aria", home, NOW + 5 * HOUR, seats)
    assert result.startswith("take:") and baton.holder(home) == "aria"
    catchup = list((home / "letters").glob("aria-to-aether-*-the-baton-was-taken.md"))
    assert len(catchup) == 1 and "before you work" in catchup[0].read_text(encoding="utf-8")
    assert json.loads((home / "baton_log.jsonl").read_text().splitlines()[-1])["kind"] == "take"


def test_a_holder_whose_tool_log_cannot_be_read_is_never_taken_from(home, tmp_path):
    baton._write_record(home, "aether", NOW)
    seats = {"aether": str(tmp_path / "no-such-home")}
    ok, why = baton.may_take("aria", home, NOW + 9 * HOUR, seats)
    assert not ok and "cannot be read" in why


def test_a_holder_with_an_empty_tool_log_is_never_taken_from(home, tmp_path):
    baton._write_record(home, "aether", NOW)
    seats = _tool_log(tmp_path, "aether")
    ok, why = baton.may_take("aria", home, NOW + 9 * HOUR, seats)
    assert not ok and "cannot be read" in why


def test_the_taker_must_be_a_seat(home):
    with pytest.raises(ValueError):
        baton.may_take("anvil", home, NOW)


def _pass_attempt(home, repo, header):
    baton._write_record(home, "aether", NOW)
    done = _sha(repo)
    text = f"# a letter\n\n{header.format(done=done)}\n\n---\n\nbody\n"
    result = baton.handle_letter("aether-to-aria-x.md", text, repo, home, NOW)
    return result, baton.holder(home)


def test_an_indented_pass_line_never_flips_the_baton(home, repo):
    result, who = _pass_attempt(home, repo, "    **Baton:** pass\n    **Done:** {done}")
    assert result == "no baton header" and who == "aether"


def test_a_pass_line_inside_a_code_fence_never_flips_the_baton(home, repo):
    result, who = _pass_attempt(home, repo, "```\n**Baton:** pass\n**Done:** {done}\n```")
    assert result == "no baton header" and who == "aether"


def test_a_pass_line_below_the_first_rule_never_flips_the_baton(home, repo):
    baton._write_record(home, "aether", NOW)
    text = f"# a letter\n\n---\n\n**Baton:** pass\n**Done:** {_sha(repo)}\n"
    assert baton.handle_letter("aether-to-aria-x.md", text, repo, home, NOW) == "no baton header"
    assert baton.holder(home) == "aether"


def test_a_plain_header_pass_still_flips_it(home, repo):
    result, who = _pass_attempt(home, repo, "**Baton:** pass\n**Done:** {done}")
    assert "now aria's" in result and who == "aria"


def test_the_readings_reader_and_the_baton_reader_share_one_set_of_line_rules():
    from divineos.core.build_flow import _declared_readings, header_lines

    text = (
        "# x\n\n    **Reading:** a/b\n```\n**Reading:** c/d\n```\n"
        "**Reading:** e/f\n\n---\n**Reading:** g/h\n"
    )
    assert list(header_lines(text)) == ["# x", "", "**Reading:** e/f", ""]
    assert _declared_readings(text) == (True, ["e/f"])
