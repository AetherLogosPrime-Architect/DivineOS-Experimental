"""Reproduction: the merge guard refuses the merge command the house itself prints.

Rows: psf-ebb90faf, psf-b467a6cc, psf-5b5e0842 (body read from a file);
      psf-49ddcf70, psf-5a23f257, psf-b73eba54 (switching auto-merge off)
Note (psf-ebb90faf): "the merge gate reads the merge message only from the command line itself, so a stamp passed in from a file looks missing. It should read the file too."
Note (psf-49ddcf70): "the merge guard must ignore `--disable-auto`, and must only ever suggest a round whose description names the box being merged."

When ``divineos stamp-ready`` stamps a pull request and the merge is then
refused, the house prints the way to finish:

    gh pr merge N --squash --body-file "<path>" --delete-branch

(``src/divineos/cli/stamp_ready_command.py``, ``_preserve_body_and_say_how``).
The review stamp is inside that file. ``divineos.core.pr_merge_gate.block_reason``
searches only the command's own text (``_command_has_external_review_trailer``),
so on a pull request that touches a protected file it blocks the command the house
just handed over. Aria's list in ``docs/drafts/one_command_from_confirm_to_main_
draft_2026-10-02.md`` already named this ("``--body-file`` unseen by
``pr_merge_gate``") as a case that should become a test.

The second reproduction is not a command the house prints; it is what the old
notes ask: that switching auto-merge OFF is not mistaken for a merge.

Marked ``xfail(strict=True)``: passes quietly as an expected failure today and
turns into a real failure the day the guard is repaired, which forces the markers
out. Nothing here changes the guard.

What would make the reproduction tests wrong: the pull request's file list and
the audit-round lookup are stubbed, so only the SHAPE of the command decides the
verdict; the test says nothing about how the live lookups behave. A repair that
changes what the stamp prints (for example, inlining the body) instead of what
the guard reads would also make the first test obsolete, and that is the owners'
design choice, not a failure of the test.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from divineos.cli import stamp_ready_command
from divineos.cli.ship_command import button
from divineos.core import pr_merge_gate

ROUND = "round-0123456789ab"
BODY = f"Merged after review.\n\nExternal-Review: {ROUND}\n"


@pytest.fixture(autouse=True)
def _pull_request_touches_a_protected_file(monkeypatch):
    """Only the command's shape may decide the verdict."""
    monkeypatch.setattr(
        pr_merge_gate,
        "audit_pr_for_guardrail_touches",
        lambda pr: (True, ["src/divineos/core/example_guardrail.py"]),
    )
    monkeypatch.setattr(
        pr_merge_gate, "_find_usable_audit_round", lambda pr, recency_days=14: (None, "", "")
    )


@pytest.mark.xfail(
    strict=True,
    reason="reproduces: the merge guard blocks the --body-file merge that stamp-ready prints, because it never reads the file",
)
def test_the_merge_the_stamp_prints_is_not_refused(tmp_path: Path):
    body_file = tmp_path / "pr-7.txt"
    body_file.write_text(BODY, encoding="utf-8")
    command = f'gh pr merge 7 --squash --body-file "{body_file}" --delete-branch'
    reason = pr_merge_gate.block_reason(command)
    assert reason is None, f"the house's own printed merge was refused:\n{reason}"


@pytest.mark.xfail(
    strict=True,
    reason="reproduces: switching auto-merge off is judged as a merge and blocked",
)
def test_switching_auto_merge_off_is_not_judged_as_a_merge():
    reason = pr_merge_gate.block_reason("gh pr merge 7 --disable-auto")
    assert reason is None, f"`--disable-auto` removes a merge but was refused:\n{reason}"


def test_control_the_stamp_really_prints_the_body_file_form():
    """Control: the printed form this test reproduces is read from the real
    source, so it follows the house if what it prints ever changes."""
    source = inspect.getsource(stamp_ready_command._preserve_body_and_say_how)
    assert "--squash --body-file" in source


def test_control_a_merge_with_no_stamp_is_still_blocked():
    """Control: the stub does not simply allow everything."""
    assert pr_merge_gate.block_reason("gh pr merge 7 --squash") is not None


def test_control_a_stamp_written_in_the_command_text_is_allowed():
    """Control: the guard passes a correctly stamped merge, and this is the
    form ``divineos ship`` prints (``button``)."""
    assert pr_merge_gate.block_reason(button(7, ROUND)) is None
