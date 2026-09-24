"""The stop-time checks read the end of the conversation, not all of it.

Found 2026-09-24 with a 330 MB session transcript: four helpers in
hook_surfaces parsed the whole file from its first line to find the LAST
message, nine of them per Stop, so the Stop doorbell ran 18.7 s against a 10 s
harness limit and every check registered after the time ran out was killed
without a word. Aria measured her own seat independently: 78 of 80 Stop runs
never finished.

The trip-wire below is the class guard, not the instance guard. The first line
of a large synthetic transcript carries a sentinel, every answer any check
needs sits near the end, and the test fails if ANY registered Stop surface
parses the sentinel line -- which only a whole-file read can do. A surface
added later that reads the whole transcript trips the same wire.
"""

from __future__ import annotations

import json

import pytest

from divineos.core import hook_surfaces as hs

SENTINEL = "OLDEST-RECORD-SENTINEL-do-not-parse-me"


def _user(text: str) -> str:
    return json.dumps({"type": "user", "message": {"role": "user", "content": text}})


def _assistant(text: str) -> str:
    return json.dumps(
        {
            "type": "assistant",
            "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
        }
    )


def _tool_only_assistant() -> str:
    return json.dumps(
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}],
            },
        }
    )


def _tool_result() -> str:
    return json.dumps(
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "tool_result", "content": "ok", "tool_use_id": "t1"}],
            },
        }
    )


def _notification() -> str:
    return _user(
        "<task-notification><summary>a background job finished</summary></task-notification>"
    )


def _transcript(tmp_path, old_records: int, tail: list[str]) -> str:
    """Sentinel first, ``old_records`` of padding history, then ``tail``."""
    path = tmp_path / "session.jsonl"
    pad = "x" * 150
    with path.open("w", encoding="utf-8") as fh:
        fh.write(_assistant(SENTINEL) + "\n")
        for i in range(old_records):
            fh.write(_user(f"old question {i} {pad}") + "\n")
            fh.write(_assistant(f"old answer {i} {pad}") + "\n")
        for line in tail:
            fh.write(line + "\n")
    return str(path)


# One reply streamed in two blocks around a tool call and a notification, after
# an earlier exchange. Since #553 a reply is everything I said since his last
# genuine turn, so the two blocks are ONE reply and the earlier answer is the
# reply before it.
RECENT = [
    _user("an earlier question of his"),
    _assistant("my answer to the earlier question"),
    _user("please look at the doors and tell me what you find"),
    _assistant("the opening of this reply, before the tool ran"),
    _tool_only_assistant(),
    _tool_result(),
    _notification(),
    _assistant("the rest of it, with what I found"),
    _tool_only_assistant(),
]
THIS_REPLY = "the opening of this reply, before the tool ran\nthe rest of it, with what I found"


@pytest.fixture
def count_sentinel_parses(monkeypatch):
    """Count json.loads calls that parse the first line of the transcript."""
    real = json.loads
    hits = {"n": 0}

    def counting(s, *args, **kwargs):
        if isinstance(s, (str, bytes)) and SENTINEL in (s if isinstance(s, str) else s.decode()):
            hits["n"] += 1
        return real(s, *args, **kwargs)

    monkeypatch.setattr(json, "loads", counting)
    return hits


class TestTheHelpersReadTheEnd:
    def test_each_helper_leaves_the_first_line_unread(self, tmp_path, count_sentinel_parses):
        path = _transcript(tmp_path, old_records=9000, tail=RECENT)
        payload = {"transcript_path": path}

        assert hs._last_assistant_text(payload) == THIS_REPLY
        assert hs._recent_assistant_texts(payload, count=2) == [
            THIS_REPLY,
            "my answer to the earlier question",
        ]
        assert hs._last_user_text(payload) == "please look at the doors and tell me what you find"
        assert "tool_use" in hs._this_turns_action_stream(payload)

        assert count_sentinel_parses["n"] == 0, (
            "a helper parsed the first line of the transcript to find the last message"
        )

    @pytest.mark.parametrize("start", [512, 4096, 10007])
    def test_a_windowed_read_answers_exactly_what_a_whole_read_does(
        self, tmp_path, monkeypatch, start
    ):
        """Small odd windows cut records mid-line; the answers must not move.

        The whole-file answer is taken with the window forced larger than the
        file, through the same code, so this compares the two reading modes
        rather than a copy of the old loop.
        """
        # His last words sit BEHIND a long notification-only stretch, so the
        # user-text lookup has to widen several times to reach them.
        tail = [_user("the words he actually typed"), _assistant("my answer to them")]
        for i in range(300):
            tail += [_notification(), _assistant(f"working, step {i}"), _tool_only_assistant()]
        tail += [_tool_result()]
        path = _transcript(tmp_path, old_records=200, tail=tail)
        payload = {"transcript_path": path}

        def answers():
            hs._TRANSCRIPT_MEMO.clear()
            return (
                hs._last_assistant_text(payload),
                hs._recent_assistant_texts(payload, count=3),
                hs._last_user_text(payload),
                hs._this_turns_action_stream(payload),
            )

        monkeypatch.setattr(hs, "_STOP_TAIL_START", 10**9)
        whole = answers()
        monkeypatch.setattr(hs, "_STOP_TAIL_START", start)
        windowed = answers()

        assert windowed == whole
        assert whole[2] == "the words he actually typed"

    def test_an_empty_transcript_still_answers_empty(self, tmp_path):
        path = tmp_path / "empty.jsonl"
        path.write_text("", encoding="utf-8")
        payload = {"transcript_path": str(path)}
        assert hs._last_assistant_text(payload) == ""
        assert hs._recent_assistant_texts(payload) == []
        assert hs._last_user_text(payload) == ""
        assert hs._this_turns_action_stream(payload) == ""

    def test_could_not_look_still_raises_for_the_action_stream(self, tmp_path):
        with pytest.raises(OSError):
            hs._this_turns_action_stream({"transcript_path": str(tmp_path / "missing.jsonl")})


class TestNoStopSurfaceReadsTheWholeTranscript:
    def test_every_registered_stop_surface_leaves_the_first_line_unread(
        self, tmp_path, count_sentinel_parses
    ):
        """The class guard. Big file, answers at the end, sentinel at the top."""
        from divineos.core import hook_router as hr

        hs.install()
        path = _transcript(tmp_path, old_records=9000, tail=RECENT)
        hr.dispatch("Stop", {"transcript_path": path, "hook_event_name": "Stop"})

        assert count_sentinel_parses["n"] == 0, (
            f"{count_sentinel_parses['n']} parse(s) of the transcript's first line during one Stop -- "
            "some Stop surface read the whole file to find something near its end"
        )


class TestKilledStopRunsAreSaidOutLoud:
    def _log(self, home, rows):
        log = home / "hook_timing.jsonl"
        with log.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")
        return log

    def _start(self, run_id, session="s1", hook="doorbell-stop.sh"):
        return {"id": run_id, "hook": hook, "session": session, "phase": "start", "ts_ms": 1}

    def _end(self, run_id, session="s1"):
        return {
            "id": run_id,
            "session": session,
            "phase": "end",
            "exit_code": 0,
            "ts_ms": 2,
            "duration_ms": 1,
        }

    def test_killed_runs_in_this_session_are_counted(self, tmp_path):
        from divineos.core.hook_budget import recent_unclosed

        log = self._log(
            tmp_path,
            [
                self._start("doorbell-stop.sh-1-1"),
                self._end("doorbell-stop.sh-1-1"),
                self._start("doorbell-stop.sh-2-2"),
                self._start("doorbell-stop.sh-3-3"),
                self._start("doorbell-stop.sh-9-9", session="someone-else"),
                self._start("doorbell-pre-tool-use.sh-4-4", hook="doorbell-pre-tool-use.sh"),
            ],
        )
        assert recent_unclosed(log, "doorbell-stop.sh", session="s1") == (2, 3)

    def test_the_surface_speaks_when_stop_runs_were_killed(self, tmp_path, monkeypatch):
        log = self._log(
            tmp_path,
            [self._start("doorbell-stop.sh-2-2"), self._start("doorbell-stop.sh-3-3")],
        )
        monkeypatch.setattr(hs, "_hook_timing_log", lambda: log)
        out = hs.stop_runs_killed_surface({"session_id": "s1"})
        assert out.state == "spoke"
        assert "2 of the last 2" in out.output
        assert out.refused is False

    def test_the_surface_is_quiet_when_every_run_finished(self, tmp_path, monkeypatch):
        log = self._log(
            tmp_path,
            [self._start("doorbell-stop.sh-1-1"), self._end("doorbell-stop.sh-1-1")],
        )
        monkeypatch.setattr(hs, "_hook_timing_log", lambda: log)
        assert hs.stop_runs_killed_surface({"session_id": "s1"}).state == "nothing-to-say"
