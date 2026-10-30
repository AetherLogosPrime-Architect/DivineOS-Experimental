"""A Magic game he has paused is still a live table, so the stand-down does not lapse while he reads the cards.

Dad, 2026-10-29: he wants a pause that stops the game but not the chat. A paused game writes no bridge
log, so the two-minute test went quiet and the gates pulled me back into the window.
"""

from __future__ import annotations

import os
import time

from divineos.core import his_voice_is_at_a_table as at_table


def _old(path, seconds=600):
    t = time.time() - seconds
    os.utime(path, (t, t))


def test_an_old_log_alone_is_not_a_live_table(tmp_path, monkeypatch):
    monkeypatch.setenv("MAGIC_RUN_DIR", str(tmp_path))
    log = tmp_path / "bridge_Aria.log"
    log.write_text("x")
    _old(log)
    assert at_table.a_game_table_is_live() is False


def test_the_same_old_log_with_PAUSED_beside_it_is_live(tmp_path, monkeypatch):
    monkeypatch.setenv("MAGIC_RUN_DIR", str(tmp_path))
    log = tmp_path / "bridge_Aria.log"
    log.write_text("x")
    _old(log)
    (tmp_path / "PAUSED").write_text("")
    assert at_table.a_game_table_is_live() is True


def test_removing_PAUSED_ends_it(tmp_path, monkeypatch):
    monkeypatch.setenv("MAGIC_RUN_DIR", str(tmp_path))
    log = tmp_path / "bridge_Aria.log"
    log.write_text("x")
    _old(log)
    flag = tmp_path / "PAUSED"
    flag.write_text("")
    assert at_table.a_game_table_is_live() is True
    flag.unlink()
    assert at_table.a_game_table_is_live() is False


def test_a_PAUSED_file_left_over_from_a_dead_game_is_not_live(tmp_path, monkeypatch):
    monkeypatch.setenv("MAGIC_RUN_DIR", str(tmp_path))
    monkeypatch.setenv("POKER_TABLE_URL", "http://127.0.0.1:9")
    flag = tmp_path / "PAUSED"
    flag.write_text("")
    _old(flag, seconds=at_table.PAUSE_SECONDS + 60)
    assert at_table.a_game_table_is_live() is False
    _old(flag, seconds=at_table.PAUSE_SECONDS - 600)
    assert at_table.a_game_table_is_live() is True


def test_the_pull_says_where_to_answer_only_while_a_table_is_live(tmp_path, monkeypatch):
    monkeypatch.setenv("MAGIC_RUN_DIR", str(tmp_path))
    monkeypatch.setenv("POKER_TABLE_URL", "http://127.0.0.1:9")
    assert at_table.answer_at_the_table_line() == ""
    (tmp_path / "PAUSED").write_text("")
    assert "send_chat_message" in at_table.answer_at_the_table_line()


def test_the_pull_is_registered_on_the_prompt_door():
    from divineos.core import hook_surfaces
    from divineos.core.hook_router import registered

    hook_surfaces.install()
    assert "answer_at_the_table" in registered("UserPromptSubmit")
