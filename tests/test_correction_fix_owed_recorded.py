"""A correction filed as "structural fix owed" must leave the debt stored.

The comment on that state promised the debt stays visible, but nothing wrote
it anywhere: the owed reason was printed once and lost. These tests pin that
an owed filing writes one pending structural-fix row, labelled as owed, whose
excerpt carries the owed reason.
"""

from __future__ import annotations

import click
from click.testing import CliRunner

from divineos.cli import correction_commands
from divineos.core.structural_fix_tracker import list_pending

_OWED_REASON = (
    "a gate that refuses edits until the council walk binds to the "
    "fingerprint, which needs the tool this marker is blocking"
)
_TEXT = (
    "root cause: I reached for the cheap close and filed the correction "
    "without naming the reach. "
    "positives: the deadlock was named as its own class. "
    f"structural fix owed: {_OWED_REASON}"
)


def _file(text: str):
    cli = click.Group()
    correction_commands.register(cli)
    return CliRunner().invoke(cli, ["correction", text])


def test_owed_filing_stores_the_debt_with_its_reason():
    result = _file(_TEXT)
    assert result.exit_code == 0, result.output
    owed = [e for e in list_pending() if e.get("trigger") == "structural fix owed"]
    assert len(owed) == 1
    assert owed[0]["source_kind"] == "correction"
    assert _OWED_REASON[:60] in owed[0]["content_excerpt"]


def test_owed_filing_does_not_also_file_a_generic_row():
    _file(_TEXT)
    assert len(list_pending()) == 1
