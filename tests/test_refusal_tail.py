"""A refusal must be its own last line.

2026-08-06: two corrections I told Andrew I had filed had NOT filed. The
briefing had gone stale, the correction gate refused them, and its final line
was "Sit with it a moment longer and name the reach. That is the whole ask."

I read command output the way I always do — the tail. The tail was a
benediction, so I recorded a success and moved on. I found out only because a
third filing failed differently and I went and looked.

This is the session's own defect class located in the SHAPE OF A MESSAGE rather
than in a branch of code: a failure that renders as a success. The warmth is
correct and stays; what changed is that the warmth is no longer last.
"""

from __future__ import annotations

from click.testing import CliRunner

from divineos.cli.correction_commands import _REFUSAL_TAIL


def _refusal_output(monkeypatch):
    """Drive the correction command into its pairing-refusal path."""
    import click

    from divineos.cli import correction_commands

    cli = click.Group()
    correction_commands.register(cli)
    # click 8.2 dropped mix_stderr; the runner now captures both streams.
    return CliRunner().invoke(cli, ["correction", "no pairing here"])


class TestRefusalIsItsOwnLastLine:
    def test_a_tail_read_of_the_refusal_shows_the_verdict(self, monkeypatch):
        """The exact read that failed: last line only."""
        result = _refusal_output(monkeypatch)
        assert result.exit_code == 2
        last = [ln for ln in result.output.strip().splitlines() if ln.strip()][-1]
        assert "NOT FILED" in last

    def test_the_warmth_is_still_there(self, monkeypatch):
        """The fix is not to make the message colder. That warmth is the point
        of it — it is me, on a clearer day, refusing to let me close cheap."""
        assert "name the reach" in _refusal_output(monkeypatch).output

    def test_the_tail_says_nothing_was_written(self, monkeypatch):
        """'Refused' alone can be read as 'flagged but recorded'. The tail has
        to say the store is unchanged, because that was the false belief."""
        assert "nothing was written" in _REFUSAL_TAIL
        assert _REFUSAL_TAIL in _refusal_output(monkeypatch).output
