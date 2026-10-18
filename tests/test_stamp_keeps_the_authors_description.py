"""Stamping keeps what the author wrote, and asks GitHub for it.

FOUND 2026-10-16 stamping #679: the PR's description, a paragraph and an Author line, came back as
one title and a review line. The code that keeps the author's text existed and read `pr.get("body")`,
but the stamp had asked GitHub only for `headRefName,title,isDraft`. The field was never there, so
the answer was always empty and the keeping step never ran. Nothing failed; the description was
gone from the squash-merge message at the moment the change was approved to enter the record.
"""

from __future__ import annotations

from divineos.cli import stamp_ready_command as mod

STAMP = (
    "Some title line\n\n"
    "Reviewed via audit round round-abc (operator-CONFIRMS + external-AI-CONFIRMS).\n\n"
    "External-Review: round-abc tree-hash:deadbeef"
)


def _run_stamp_with_reply(monkeypatch, reply: dict):
    import json
    import subprocess

    import click
    from click.testing import CliRunner

    calls: list[list[str]] = []

    def fake_run(cmd, *a, **k):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(reply), stderr="")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    group = click.Group()
    mod.register(group)
    result = CliRunner().invoke(group, ["stamp-ready", "5", "--audit-round", "round-x"])
    return result, calls


def test_a_reply_with_no_body_field_refuses_before_changing_anything(monkeypatch):
    """Aletheia's hardening of #687: no `body` key at all is could-not-look, never an empty
    description."""
    result, calls = _run_stamp_with_reply(
        monkeypatch, {"headRefName": "x/y", "title": "t", "isDraft": True}
    )
    assert result.exit_code == 1
    assert "no body field" in result.output
    assert not any(c[:3] == ["gh", "pr", "edit"] for c in calls), "nothing may be edited"


def test_control_a_reply_with_an_empty_body_is_not_refused_for_missing_it(monkeypatch):
    """The control for the test above: an empty string is a real answer ("there is no
    description") and must not trip the missing-field refusal."""
    result, _ = _run_stamp_with_reply(
        monkeypatch, {"headRefName": "x/y", "title": "t", "isDraft": True, "body": ""}
    )
    assert "no body field" not in result.output


def test_the_stamp_asks_github_for_the_body():
    assert "body" in mod.PR_FIELDS.split(",")


def test_the_authors_prose_and_author_line_survive_and_the_review_lines_come_last():
    prior = "What this does and why.\n\nAuthor: aria\n"
    out = mod.keep_the_authors_text(prior, STAMP)
    assert out.startswith("What this does and why.")
    assert "Author: aria" in out
    assert out.rstrip().splitlines()[-1].startswith("External-Review:")
    assert "Some title line" not in out


def test_an_earlier_stamp_is_replaced_not_stacked():
    prior = "Prose.\n\nReviewed via audit round round-old (x).\n\nExternal-Review: round-old tree-hash:aaaa"
    out = mod.keep_the_authors_text(prior, STAMP)
    assert "round-old" not in out
    assert out.count("External-Review:") == 1
    assert out.count("Reviewed via audit round") == 1


def test_no_prior_text_leaves_the_block_alone():
    assert mod.keep_the_authors_text(None, STAMP) == STAMP
    assert mod.keep_the_authors_text("   \n", STAMP) == STAMP
