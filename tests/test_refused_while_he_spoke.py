"""A call the speaking door refuses is saved whole and handed back once he has been answered; nothing is cut or lost."""

from __future__ import annotations

from divineos.core import refused_while_he_spoke as rw


def test_a_refused_write_comes_back_with_its_full_text(tmp_path):
    body = "line one\n" * 3000  # long on purpose: nothing may be cut
    rw.record("Write", {"file_path": "C:/x/letter.md", "content": body}, root=tmp_path)
    out = rw.release(root=tmp_path)
    assert "C:/x/letter.md" in out
    assert body in out


def test_a_refused_edit_comes_back_with_both_halves(tmp_path):
    rw.record(
        "Edit",
        {"file_path": "p.md", "old_string": "OLD TEXT", "new_string": "NEW TEXT"},
        root=tmp_path,
    )
    out = rw.release(root=tmp_path)
    assert "OLD TEXT" in out and "NEW TEXT" in out


def test_a_refused_command_comes_back(tmp_path):
    rw.record("Bash", {"command": "git status"}, root=tmp_path)
    assert "git status" in rw.release(root=tmp_path)


def test_two_held_calls_come_back_oldest_first(tmp_path):
    rw.record("Bash", {"command": "first one"}, root=tmp_path, now=1000.0)
    rw.record("Bash", {"command": "second one"}, root=tmp_path, now=2000.0)
    out = rw.release(root=tmp_path)
    assert out.index("first one") < out.index("second one")
    assert "2 call(s)" in out


def test_the_hand_back_is_said_once(tmp_path):
    rw.record("Bash", {"command": "once only"}, root=tmp_path)
    assert "once only" in rw.release(root=tmp_path)
    assert rw.release(root=tmp_path) == ""


def test_nothing_held_is_the_empty_string(tmp_path):
    assert rw.release(root=tmp_path) == ""


def test_an_unreadable_held_call_is_named_and_left_in_place(tmp_path):
    pending = tmp_path / "pending"
    pending.mkdir()
    (pending / "1.000-bad.json").write_text("{not json", encoding="utf-8")
    out = rw.release(root=tmp_path)
    assert "could not be read" in out
    assert (pending / "1.000-bad.json").exists()
