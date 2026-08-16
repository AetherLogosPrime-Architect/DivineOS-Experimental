"""The receipt must show the payload, not judge it.

2026-08-05: correction #307 arrived at the CLI already damaged — bash had
eaten a backticked clause before Python saw a byte of it. The CLI stored what
it received, faithfully, and printed success.

The seam that matters is between what was INTENDED and what ARRIVED, and no
code stands at that seam. So the receipt does not try to detect corruption.
It makes the payload visible at filing time so the discrepancy becomes
inspectable by the only party who knows the intent.

These tests pin that distinction: the receipt must always report, and must
never claim a verdict it cannot reach.
"""

from __future__ import annotations

from divineos.cli.correction_commands import _SHELL_HAZARDS, _echo_payload_receipt


def test_receipt_reports_size_and_both_ends(capsys):
    """Length plus first and last line is what makes a lost clause visible."""
    text = "first line here\nmiddle that could vanish\nlast line here"
    _echo_payload_receipt(text)
    out = capsys.readouterr().out
    assert f"{len(text)} chars" in out
    assert "3 lines" in out
    assert "first line here" in out
    assert "last line here" in out


def test_receipt_warns_when_shell_metacharacters_survived(capsys):
    """Backticks present means the payload probably went through a shell.

    Their presence is not proof of damage — prose about commands contains
    them legitimately. The warning says "check", not "corrupted", because
    the receipt cannot know what was intended.
    """
    _echo_payload_receipt("root cause: I ran `divineos psf` and it did not exist")
    out = capsys.readouterr().out
    assert "shell metacharacters" in out
    assert "check the text above" in out


def test_receipt_stays_quiet_when_nothing_looks_shell_shaped(capsys):
    """No false alarm on ordinary prose — a receipt that cries wolf is ignored."""
    _echo_payload_receipt("root cause: I read a two-valued answer out of a three-valued world.")
    out = capsys.readouterr().out
    assert "shell metacharacters" not in out
    assert "chars" in out, "the receipt must still report even when it has no warning"


def test_receipt_survives_a_single_line_and_an_empty_payload(capsys):
    """Boundary: splitlines('') is [], and lines[-1] would raise on it."""
    _echo_payload_receipt("one line only")
    assert "one line only" in capsys.readouterr().out
    _echo_payload_receipt("")
    assert "0 chars" in capsys.readouterr().out


def test_hazard_list_is_not_empty_and_holds_the_one_that_bit():
    """Regression pin. The backtick is the character that ate #307."""
    assert "`" in _SHELL_HAZARDS
