"""The baton: one holder, passed by a letter that names real work, taken only from a silent holder."""

import json
import subprocess

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


def test_the_waiting_seat_cannot_take_it_from_a_holder_seen_recently(home):
    baton._write_record(home, "aether", NOW)
    baton.mark_seen("aether", home, NOW - HOUR)
    ok, why = baton.may_take("aria", home, NOW)
    assert not ok and "last seen" in why


def test_silence_past_two_hours_without_a_waiting_letter_is_not_enough(home):
    baton._write_record(home, "aether", NOW)
    baton.mark_seen("aether", home, NOW - 3 * HOUR)
    ok, why = baton.may_take("aria", home, NOW)
    assert not ok and "no letter" in why


def test_a_silent_holder_with_a_letter_waiting_can_be_taken_from_and_is_told(home):
    baton._write_record(home, "aether", NOW)
    baton.mark_seen("aether", home, 1.0)  # long ago; the letter below is newer
    waiting = home / "letters" / "aria-to-aether-2026-10-16-hello.md"
    waiting.write_text("hello", encoding="utf-8")
    result = baton.take("aria", home, NOW + 5 * HOUR)
    assert result.startswith("take:") and baton.holder(home) == "aria"
    catchup = list((home / "letters").glob("aria-to-aether-*-the-baton-was-taken.md"))
    assert len(catchup) == 1 and "before you work" in catchup[0].read_text(encoding="utf-8")
    assert json.loads((home / "baton_log.jsonl").read_text().splitlines()[-1])["kind"] == "take"


def test_a_holder_with_no_mark_is_never_taken_from(home):
    baton._write_record(home, "aether", NOW)
    ok, why = baton.may_take("aria", home, NOW + 9 * HOUR)
    assert not ok and "no mark" in why


def test_the_taker_must_be_a_seat(home):
    with pytest.raises(ValueError):
        baton.may_take("anvil", home, NOW)
