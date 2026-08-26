"""The doorman must not accept a string I typed as proof I opened something.

reach_check's own docstring: *"a self-reported disposition answers the
question. Reading the action-stream produces the finding."* The CLI then
shipped `--opened`, whose value I type by hand, as the ONLY source of that
action-stream. Saying so, exactly -- the gate that refuses self-report as
evidence accepted self-report as evidence one layer down. I used it five times
on 2026-08-17 before noticing, reported it rather than fixing it, and Andrew
said fix it.

HOW IT GOT THERE, because the shape matters more than the instance. `dispose()`
was written to RECEIVE an action-stream, which is correct, and nothing existed
that could PRODUCE one -- so the CLI filled the parameter from a flag. The
architecture was right and the only available supplier was me. A gate is only
as honest as its cheapest source of evidence.

The transcript is written by the harness as tools fire. A command that never
ran cannot appear in it. That is the whole difference between evidence and
testimony, and it is the only claim this module makes.

SECOND DEFECT, caught by running the thing rather than reasoning about it. The
first reader used `context_tokens._find_active_transcript`, which encodes the
cwd into ONE project directory. This session runs in a worktree; invoked from
the main checkout it opened the main directory and returned its newest file --
dated 2026-08-06, eleven days stale. It parsed perfectly and yielded zero
in-window calls with NO error, so the gate would have fallen back to
self-attestation on every call while looking repaired. A silent wrong answer
wearing a correct one. Verifying meant asking whether it could catch me lying,
not whether it ran.
"""

from __future__ import annotations

import json
import os
import time

from divineos.core import reach_check as R


def _tool_use_line(name, key, value, *, when=None):
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(when or time.time())) + ".000Z"
    return json.dumps(
        {
            "type": "assistant",
            "timestamp": stamp,
            "message": {"content": [{"type": "tool_use", "name": name, "input": {key: value}}]},
        }
    )


def _transcript(tmp_path, monkeypatch, *lines):
    p = tmp_path / "session.jsonl"
    p.write_text("\n".join(lines), encoding="utf-8")
    monkeypatch.setattr(R, "_active_transcript_including_worktrees", lambda: p)
    return p


class TestTheTranscriptIsTheEvidence:
    def test_a_command_that_ran_is_found(self, tmp_path, monkeypatch):
        _transcript(
            tmp_path, monkeypatch, _tool_use_line("Bash", "command", "divineos affect summary")
        )
        calls, why = R.action_stream_from_transcript()
        assert why == ""
        assert R._opened_in_stream("cli:affect", calls, tuple(t for _, t in calls)) == "cmd:affect"

    def test_a_command_that_never_ran_is_not_found(self, tmp_path, monkeypatch):
        """The honesty test. This is the whole point of the module."""
        _transcript(
            tmp_path, monkeypatch, _tool_use_line("Bash", "command", "divineos affect summary")
        )
        calls, _ = R.action_stream_from_transcript()
        assert R._opened_in_stream("cli:tarot", calls, tuple(t for _, t in calls)) is None

    def test_file_reads_are_captured_too(self, tmp_path, monkeypatch):
        _transcript(
            tmp_path, monkeypatch, _tool_use_line("Read", "file_path", "/repo/docs/plan.md")
        )
        calls, _ = R.action_stream_from_transcript()
        assert R._opened_in_stream("docs/plan.md", calls, ()) == "tool:Read:plan.md"

    def test_calls_outside_the_window_do_not_count(self, tmp_path, monkeypatch):
        """A thing opened days ago is not a thing opened for this check."""
        _transcript(
            tmp_path,
            monkeypatch,
            _tool_use_line("Bash", "command", "divineos affect summary", when=time.time() - 86400),
        )
        calls, _ = R.action_stream_from_transcript()
        assert calls == ()


class TestUnreadableIsNotEmpty:
    def test_a_missing_transcript_reports_a_reason(self, monkeypatch):
        """Could-not-look must never render as you-opened-nothing."""
        monkeypatch.setattr(R, "_active_transcript_including_worktrees", lambda: None)
        calls, why = R.action_stream_from_transcript()
        assert calls == ()
        assert why, "a gate that cannot see must say so, not report a clean scan"

    def test_a_readable_transcript_with_no_calls_reports_no_reason(self, tmp_path, monkeypatch):
        """The other side of the same distinction: really nothing there."""
        _transcript(tmp_path, monkeypatch, json.dumps({"type": "user", "message": {"content": []}}))
        calls, why = R.action_stream_from_transcript()
        assert calls == ()
        assert why == ""

    def test_malformed_lines_do_not_kill_the_scan(self, tmp_path, monkeypatch):
        _transcript(
            tmp_path,
            monkeypatch,
            "{not json at all",
            _tool_use_line("Bash", "command", "divineos sleep"),
        )
        calls, _ = R.action_stream_from_transcript()
        assert len(calls) == 1

    def test_an_unparseable_timestamp_keeps_the_call(self, tmp_path, monkeypatch):
        """Erring toward INCLUDING is safe; the call still has to match.

        Dropping rows on a date-format change would silently make the gate
        stricter for a reason nobody could see -- the same invisible-frame
        failure this whole day was about.
        """
        line = json.dumps(
            {
                "timestamp": "not-a-date",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Bash", "input": {"command": "divineos sleep"}}
                    ]
                },
            }
        )
        _transcript(tmp_path, monkeypatch, line)
        assert len(R.action_stream_from_transcript()[0]) == 1


def _projects_root(tmp_path, monkeypatch, dirs_with_mtime):
    """Build a fake ~/.claude/projects and point the resolver at it.

    `dirs_with_mtime` maps encoded-directory-name -> mtime. Each gets one
    transcript file stamped at that time, so `max(mtime)` has something to pick
    between.
    """
    root = tmp_path / ".claude" / "projects"
    for name, mtime in dirs_with_mtime.items():
        d = root / name
        d.mkdir(parents=True)
        f = d / "session.jsonl"
        f.write_text("{}", encoding="utf-8")
        os.utime(f, (mtime, mtime))
    monkeypatch.setattr(R.Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr("divineos.core.context_tokens._encode_cwd_for_claude", lambda: MAIN_DIR)
    return root


MAIN_DIR = "C--DIVINE-OS-DivineOS-Experimental"


class TestWhoseTranscriptIsIt:
    """The resolver must find MY worktrees and no one else's checkout."""

    def test_my_worktree_directory_is_searched_too(self, tmp_path, monkeypatch):
        """The stale-transcript bug, pinned at the resolver.

        Encoding the cwd yields ONE project directory. A worktree session writes
        to a sibling whose name extends it with the worktree separator. Matching
        only the exact name returned an eleven-day-old file that parsed fine and
        answered zero.
        """
        _projects_root(
            tmp_path,
            monkeypatch,
            {
                MAIN_DIR: 1000.0,
                MAIN_DIR + "--claude-worktrees-strange-leakey-4c70a2": 2000.0,
            },
        )
        picked = R._active_transcript_including_worktrees()
        assert picked is not None
        assert picked.parent.name.endswith("strange-leakey-4c70a2"), (
            "my own worktree is newer and must win"
        )

    def test_a_sibling_agents_checkout_is_not_mine(self, tmp_path, monkeypatch):
        """The race that made every disposition refuse.

        Aria's repo is `DivineOS-Experimental-Aria-new`, so her encoded project
        directory literally extends mine. Under a bare `startswith`, whenever
        she wrote more recently than I did, `max(mtime)` handed my doorman HER
        session -- my own commands went invisible and the gate refused
        everything. Her transcript is NEWER here on purpose: that is the losing
        case, and it must still resolve to mine.
        """
        _projects_root(
            tmp_path,
            monkeypatch,
            {
                MAIN_DIR: 1000.0,
                MAIN_DIR + "-Aria-new": 9000.0,
            },
        )
        picked = R._active_transcript_including_worktrees()
        assert picked is not None
        assert picked.parent.name == MAIN_DIR, (
            f"resolved to {picked.parent.name!r} -- a separate agent's live session"
        )

    def test_a_sibling_session_of_mine_is_still_not_this_session(self, tmp_path, monkeypatch):
        """The half the separator fix does NOT cover, and I called it closed.

        Another window of MY OWN lives in the same project directory and
        satisfies the scoped predicate legitimately, so newest-wins could still
        hand this session the wrong transcript. One was open and writing while
        I wrote the separator repair. The harness names each transcript after
        the session id and exports that id, so the resolver looks its own up by
        name -- an exact match, not a tiebreak. The sibling is NEWER here on
        purpose: that is the losing case under mtime, and it must still lose.
        """
        mine = "0c1698fa-9524-4eb2-9942-38e35adf2866"
        root = tmp_path / ".claude" / "projects" / MAIN_DIR
        root.mkdir(parents=True)
        for name, mtime in ((mine, 1000.0), ("a18627d7-0cff-46ee-91df-b39f4e8ddea6", 9000.0)):
            f = root / f"{name}.jsonl"
            f.write_text("{}", encoding="utf-8")
            os.utime(f, (mtime, mtime))
        monkeypatch.setattr(R.Path, "home", staticmethod(lambda: tmp_path))
        monkeypatch.setattr("divineos.core.context_tokens._encode_cwd_for_claude", lambda: MAIN_DIR)
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", mine)
        picked = R._active_transcript_including_worktrees()
        assert picked is not None and picked.stem == mine, (
            f"resolved to {picked and picked.stem!r} -- another window of mine"
        )

    def test_without_a_session_id_the_newest_still_wins(self, tmp_path, monkeypatch):
        """The fallback has to stay intact for hooks and subagents.

        They run without the harness session id in their environment, and there
        newest-wins is still the best answer available. Closing the race for the
        session that HAS an id must not blind the callers that do not.
        """
        _projects_root(tmp_path, monkeypatch, {MAIN_DIR: 1000.0})
        (tmp_path / ".claude" / "projects" / MAIN_DIR / "newer.jsonl").write_text("{}")
        os.utime(tmp_path / ".claude" / "projects" / MAIN_DIR / "newer.jsonl", (9000.0, 9000.0))
        monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
        picked = R._active_transcript_including_worktrees()
        assert picked is not None and picked.name == "newer.jsonl"

    def test_an_unrelated_project_is_not_mine_either(self, tmp_path, monkeypatch):
        """The general case the Aria instance is one example of."""
        _projects_root(
            tmp_path,
            monkeypatch,
            {MAIN_DIR: 1000.0, MAIN_DIR + "-OneDrive-Backup": 9000.0},
        )
        picked = R._active_transcript_including_worktrees()
        assert picked is not None and picked.parent.name == MAIN_DIR


def test_the_cli_prefers_the_transcript_over_the_flag():
    """The library fix is inert if the CLI still trusts what I typed."""
    import inspect

    from divineos.cli import reach_commands

    src = inspect.getsource(reach_commands)
    assert "action_stream_from_transcript()" in src, "the CLI must ask the transcript"
    assert src.index("action_stream_from_transcript()") < src.index("SELF-ATTESTED"), (
        "and ask it BEFORE reaching for the typed fallback"
    )
    assert "SELF-ATTESTED" in src, "a fallback to testimony must announce itself"
