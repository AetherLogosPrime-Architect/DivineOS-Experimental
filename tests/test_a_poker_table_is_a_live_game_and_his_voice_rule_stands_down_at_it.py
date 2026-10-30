"""A live POKER table counts as a live game, and the rule that ends my turn when he speaks stands down at it.

Dad, 2026-10-29: "the issue is my rule that forces you to wait for my words.. when i speak at the table you
respond here.. when you do, you are no longer at the table but in stasis.. so the wait for dad rule needs
silenced at the table as well."

Two faults, found by reading the code:
1. `a_game_table_is_live` only looked at the Magic table's bridge logs, so at poker it never answered yes
   and every stand-down that rides on it (the room gate) stayed asking.
2. `his-voice-ends-the-turn` never asked it at all, so any word he typed into the window mid-turn at a table
   ended my turn and took me out of the game.

Each test below has a control, so a pass means the check can see both cases.
"""

from __future__ import annotations

import io
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from divineos.core import his_voice_is_at_a_table as at_table
from divineos.hooks import his_voice_hook


def _serve(view: dict):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            body = json.dumps(view).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


@pytest.fixture
def no_magic_table(tmp_path, monkeypatch):
    monkeypatch.setenv("MAGIC_RUN_DIR", str(tmp_path / "no-magic-here"))


def _point_at(monkeypatch, view):
    server = _serve(view)
    monkeypatch.setenv("POKER_TABLE_URL", f"http://127.0.0.1:{server.server_port}")
    return server


def test_a_live_hand_at_the_poker_table_is_a_live_game(no_magic_table, monkeypatch):
    server = _point_at(monkeypatch, {"hand": 3, "live": True, "deal_in": None})
    try:
        assert at_table.a_game_table_is_live() is True
    finally:
        server.shutdown()


def test_a_poker_table_counting_down_to_the_next_deal_is_still_live(no_magic_table, monkeypatch):
    server = _point_at(monkeypatch, {"hand": 3, "live": False, "deal_in": 6.0})
    try:
        assert at_table.a_game_table_is_live() is True
    finally:
        server.shutdown()


@pytest.mark.parametrize(
    "view",
    [
        {"hand": None, "live": False},
        {"hand": 3, "live": False, "deal_in": None},
        {"hand": 3, "live": True, "released": True},
    ],
    ids=["nothing dealt", "finished and no deal coming", "Dad ended it with the button"],
)
def test_control_a_table_that_is_not_a_game_is_not_live(no_magic_table, monkeypatch, view):
    server = _point_at(monkeypatch, view)
    try:
        assert at_table.a_game_table_is_live() is False
    finally:
        server.shutdown()


def test_control_a_table_that_does_not_answer_is_not_live(no_magic_table, monkeypatch):
    monkeypatch.setenv("POKER_TABLE_URL", "http://127.0.0.1:9")  # nothing listens here
    assert at_table.a_game_table_is_live() is False


# ---- the rule that ends my turn when he speaks --------------------------------------------------------


def _he_spoke_mid_turn(tmp_path):
    def rec(**kw):
        return json.dumps(kw)

    lines = [
        rec(
            type="user",
            uuid="t1",
            timestamp="2026-09-25T05:20:00.000Z",
            isSidechain=False,
            origin={"kind": "human"},
            promptId="p-t1",
            message={"role": "user", "content": "you could work on your side now"},
        ),
        rec(
            type="assistant",
            uuid="a1",
            timestamp="2026-09-25T05:49:01.929Z",
            isSidechain=False,
            message={"role": "assistant", "content": [{"type": "tool_use", "name": "Bash"}]},
        ),
        rec(
            type="user",
            uuid="r1",
            timestamp="2026-09-25T05:49:07.499Z",
            isSidechain=False,
            message={"role": "user", "content": [{"type": "tool_result", "content": "ok"}]},
        ),
        rec(
            type="attachment",
            uuid="s1",
            timestamp="2026-09-25T05:49:02.218Z",
            isSidechain=False,
            attachment={
                "type": "queued_command",
                "prompt": "aria can you hear me at the table?",
                "commandMode": "prompt",
                "origin": {"kind": "human"},
            },
        ),
    ]
    path = tmp_path / "transcript.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _run_hook(monkeypatch, tmp_path, capsys):
    payload = json.dumps(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "python seat.py aria say hello"},
            "transcript_path": str(_he_spoke_mid_turn(tmp_path)),
        }
    )
    monkeypatch.setattr(his_voice_hook.sys, "stdin", io.StringIO(payload))
    status = his_voice_hook.main()
    return status, capsys.readouterr()


def test_control_away_from_a_table_his_words_still_end_the_turn(
    no_magic_table, monkeypatch, tmp_path, capsys
):
    monkeypatch.setenv("POKER_TABLE_URL", "http://127.0.0.1:9")
    status, _ = _run_hook(monkeypatch, tmp_path, capsys)
    assert status == his_voice_hook.REFUSE


def test_at_a_live_poker_table_his_words_do_not_end_the_turn(
    no_magic_table, monkeypatch, tmp_path, capsys
):
    server = _point_at(monkeypatch, {"hand": 3, "live": True, "deal_in": None})
    try:
        status, out = _run_hook(monkeypatch, tmp_path, capsys)
    finally:
        server.shutdown()
    assert status == 0
    assert "table" in out.err.lower()  # it says it stood down, never silently
