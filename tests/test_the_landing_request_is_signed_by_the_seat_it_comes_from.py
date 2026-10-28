"""`divineos landing --request` is signed by the seat that wrote it, and refuses when it cannot tell.

Aether's read of #733: `this_seat() or "aether"` signed an unknown seat as Aether. A confirm request to
Aletheia carries the signature she answers, so a request signed by the wrong seat sends her answer to the
wrong window. The command is the wiring, so the test runs the command, with the pull-request list, the
letters and the seat stubbed at the names the command reads them from.
"""

from __future__ import annotations

import click
from click.testing import CliRunner

from divineos.cli import landing_commands
from divineos.core import sibling_audit_rounds

_HEAD = "a" * 40
_PR = {"number": 901, "headRefName": "aria/x", "headRefOid": _HEAD, "title": "A fix"}


def _run(monkeypatch, seat):
    monkeypatch.setattr(landing_commands, "open_prs", lambda: [dict(_PR)])
    monkeypatch.setattr(landing_commands, "_held_by_pr", lambda: {901: ("2-council",)})
    monkeypatch.setattr(landing_commands, "read_letters", lambda: {})
    monkeypatch.setattr(sibling_audit_rounds, "this_seat", lambda: seat)
    group = click.Group()
    landing_commands.register(group)
    return CliRunner().invoke(group, ["landing", "--request"])


def test_the_request_is_signed_by_the_seat_that_wrote_it(monkeypatch):
    for seat, signature in (("aria", "— Aria"), ("aether", "— Aether")):
        out = _run(monkeypatch, seat)
        assert out.exit_code == 0, out.output
        assert "#901" in out.output
        assert out.output.rstrip().endswith(signature), out.output


def test_an_unknown_seat_refuses_and_prints_no_letter(monkeypatch):
    out = _run(monkeypatch, None)
    assert out.exit_code == 2
    assert "Cannot sign" in out.output
    assert "DIVINEOS_HOME" in out.output
    assert "CONFIRMS: #N" not in out.output


def test_an_unknown_seat_has_nothing_to_refuse_when_nothing_needs_her(monkeypatch):
    # The zero case (Knuth): no letter is being written, so no signature is owed.
    monkeypatch.setattr(landing_commands, "open_prs", lambda: [])
    monkeypatch.setattr(landing_commands, "_held_by_pr", lambda: {})
    monkeypatch.setattr(landing_commands, "read_letters", lambda: {})
    monkeypatch.setattr(sibling_audit_rounds, "this_seat", lambda: None)
    group = click.Group()
    landing_commands.register(group)
    out = CliRunner().invoke(group, ["landing", "--request"])
    assert out.exit_code == 0, out.output
    assert "nothing needs her confirm" in out.output
