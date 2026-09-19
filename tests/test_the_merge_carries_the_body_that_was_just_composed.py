"""The merge carries the text the stamp tool just composed, or says what is left.

FOUND IN ANGER 2026-09-19, on the second of two branches merged that evening.
The first merge passed the composed body explicitly and its commit on the main
line carries the review line. The second was merged without it, on the
assumption that the host would source the text from the request body where the
stamp tool had already written it. It does not -- it uses the accumulated
branch commit messages -- and that branch landed with no review line at all.

The gap was between two processes: one composed the text, the other performed
the merge, and the value had to cross by memory. The failure gives no feedback
where the action happens, because a merge without the line succeeds and looks
exactly like a merge with it.

These tests hold the three properties that make closing the gap safe:
opt-in so no existing caller is surprised by an irreversible action, the text
actually reaching the merge, and a refusal leaving a recoverable state that
names its own way forward rather than sending anyone back to memory.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.cli import stamp_ready_command as mod


class _Result:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestMergingIsOptInAndSilentWhenNotAsked:
    def test_not_asking_runs_nothing_at_all(self, monkeypatch) -> None:
        def explode(*_a, **_k):  # pragma: no cover - must never be reached
            raise AssertionError("a merge was attempted without being asked for")

        monkeypatch.setattr(subprocess, "run", explode)
        mod._merge_with_the_body_just_composed(1, "body", merge=False)


class TestTheComposedTextReachesTheMerge:
    def test_the_body_is_passed_to_the_merge_verbatim(self, monkeypatch) -> None:
        seen: dict[str, list[str]] = {}

        def capture(cmd, **_k):
            seen["cmd"] = list(cmd)
            return _Result(0)

        monkeypatch.setattr(subprocess, "run", capture)
        body = "Reviewed via audit round round-abc.\n\nExternal-Review: round-abc"
        mod._merge_with_the_body_just_composed(7, body, merge=True)

        cmd = seen["cmd"]
        assert "--squash" in cmd
        assert "--body" in cmd
        # The exact text, not a reconstruction of it.
        assert cmd[cmd.index("--body") + 1] == body

    def test_the_merge_is_not_retried_when_the_host_refuses(self, monkeypatch) -> None:
        calls = {"n": 0}

        def refuse(cmd, **_k):
            calls["n"] += 1
            return _Result(1, stderr="the base branch policy prohibits the merge")

        monkeypatch.setattr(subprocess, "run", refuse)
        mod._merge_with_the_body_just_composed(7, "body", merge=True)

        # One attempt. A tool that argues with a refusal eventually merges
        # something a policy meant to hold.
        assert calls["n"] == 1


class TestARefusalLeavesARecoverableStateThatNamesItsOwnWayForward:
    def test_the_composed_body_is_preserved_where_it_can_be_found(
        self, monkeypatch, capsys
    ) -> None:
        monkeypatch.setattr(
            subprocess, "run", lambda *_a, **_k: _Result(1, stderr="checks pending")
        )
        body = "External-Review: round-xyz"
        mod._merge_with_the_body_just_composed(4242, body, merge=True)

        printed = capsys.readouterr().out
        assert "checks pending" in printed
        # Says the stamping stands, so nobody reads this as a whole-act failure.
        assert "safe to re-run" in printed

        repo_root = Path(mod.__file__).resolve().parents[3]
        kept = repo_root / "data" / "merge_bodies" / "pr-4242.txt"
        try:
            assert kept.read_text(encoding="utf-8") == body
            # The finishing command names the file rather than the text, so the
            # caller recognises a path instead of reconstructing a paragraph.
            assert "--body-file" in printed
            assert "pr-4242.txt" in printed
        finally:
            kept.unlink(missing_ok=True)

    def test_an_unwritable_location_refuses_loudly_rather_than_silently(
        self, monkeypatch, capsys
    ) -> None:
        monkeypatch.setattr(
            subprocess, "run", lambda *_a, **_k: _Result(1, stderr="checks pending")
        )

        def cannot_write(*_a, **_k):
            raise OSError("read-only")

        monkeypatch.setattr(Path, "write_text", cannot_write)
        mod._merge_with_the_body_just_composed(99, "External-Review: r", merge=True)

        printed = capsys.readouterr().out
        # Cannot-preserve must not read as preserved.
        assert "Could not preserve" in printed
        assert "do not retype it from memory" in printed


class TestTheHostBeingUnreachableIsNotSilence:
    @pytest.mark.parametrize(
        "boom",
        [
            FileNotFoundError("gh is not installed"),
            subprocess.TimeoutExpired(cmd="gh", timeout=180),
        ],
    )
    def test_a_missing_or_hung_host_reports_rather_than_passing(
        self, monkeypatch, capsys, boom
    ) -> None:
        def raise_it(*_a, **_k):
            raise boom

        monkeypatch.setattr(subprocess, "run", raise_it)
        mod._merge_with_the_body_just_composed(5, "External-Review: r", merge=True)

        printed = capsys.readouterr().out
        assert "the merge was refused" in printed

        repo_root = Path(mod.__file__).resolve().parents[3]
        (repo_root / "data" / "merge_bodies" / "pr-5.txt").unlink(missing_ok=True)
