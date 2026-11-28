"""The kept-out list must not lose a line when two seats write at once, must say so when its fingerprints may
no longer match, and must record who kept a line out from the seat, never from a typed default.

Aria's cold read of #867 (2026-11-23): a lost keep-out here means a hurt line returns, which is the one thing
this piece exists to prevent. Each test below fails against the door before this change.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from divineos.core import his_words_door as door

PASSAGES = [
    f"a line number {i} said in pain about something unrelated to the others {i * 7}"
    for i in range(12)
]


def _keep(path: Path, text: str, by: str) -> None:
    door.keep_out(text, why="a line read as pain", by=by, on="2026-11-23", path=path)


def test_two_writers_at_once_lose_nothing(tmp_path, monkeypatch):
    path = tmp_path / "kept.json"
    real_read = door._kept_out_entries

    def slow_read(p=path):
        entries = real_read(p)
        time.sleep(0.03)  # a slow disk: the window in which the other writer used to slip in
        return entries

    monkeypatch.setattr(door, "_kept_out_entries", slow_read)
    errors: list[BaseException] = []

    def writer(items: list[str], who: str) -> None:
        try:
            for text in items:
                _keep(path, text, who)
        except BaseException as exc:  # noqa: BLE001 - the test reports it
            errors.append(exc)

    a = threading.Thread(target=writer, args=(PASSAGES[:6], "aether"))
    b = threading.Thread(target=writer, args=(PASSAGES[6:], "aria"))
    a.start()
    b.start()
    a.join()
    b.join()
    assert not errors, errors
    monkeypatch.setattr(door, "_kept_out_entries", real_read)
    kept = {e["fp"] for e in real_read(path)}
    assert kept == {door.fingerprint(t) for t in PASSAGES}


def test_return_to_door_loses_nothing_either(tmp_path):
    path = tmp_path / "kept.json"
    for text in PASSAGES[:3]:
        _keep(path, text, "aether")
    assert door.return_to_door(PASSAGES[0], path=path) is True
    kept = {e["fp"] for e in door._kept_out_entries(path)}
    assert kept == {door.fingerprint(t) for t in PASSAGES[1:3]}


def test_a_leftover_lock_file_nobody_holds_does_not_wedge_the_list(tmp_path):
    path = tmp_path / "kept.json"
    lock = path.with_name(path.name + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text("left behind by a crashed writer", encoding="utf-8")
    old = time.time() - 3600
    import os

    os.utime(lock, (old, old))
    _keep(
        path, PASSAGES[0], "aether"
    )  # the lock is the system's, not the file's: no age is ever judged
    assert door.fingerprint(PASSAGES[0]) in {e["fp"] for e in door._kept_out_entries(path)}


def test_a_lock_really_held_is_said_out_loud_and_nothing_is_dropped(tmp_path, monkeypatch):
    from divineos.core import os_file_lock

    path = tmp_path / "kept.json"
    lock = path.with_name(path.name + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    holder = open(lock, "a+b")  # another writer, holding the system's own lock
    try:
        assert os_file_lock.try_lock(holder) is True
        monkeypatch.setattr(door, "LOCK_WAIT_SECONDS", 0.2)
        with pytest.raises(door.KeptOutBusy):
            _keep(path, PASSAGES[0], "aether")
        assert not path.exists()  # the refused write left no half-list behind
    finally:
        os_file_lock.unlock(holder)
        holder.close()
    _keep(path, PASSAGES[0], "aether")  # the moment the holder lets go, the write goes through
    assert path.exists()


def test_the_shared_lock_says_busy_without_waiting_when_asked_to_try(tmp_path):
    from divineos.core import os_file_lock

    lock = tmp_path / "x.lock"
    first = open(lock, "a+b")
    second = open(lock, "a+b")
    try:
        assert os_file_lock.try_lock(first) is True
        assert os_file_lock.try_lock(second) is False
    finally:
        os_file_lock.unlock(first)
        first.close()
        second.close()


def test_the_list_records_the_cleaner_it_was_made_under(tmp_path):
    path = tmp_path / "kept.json"
    _keep(path, PASSAGES[0], "aether")
    assert json.loads(path.read_text(encoding="utf-8"))["cleaner"] == door.CLEANER


def test_a_list_made_under_another_cleaner_says_so(tmp_path):
    path = tmp_path / "kept.json"
    _keep(path, PASSAGES[0], "aether")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["cleaner"] = "an-older-cleaner"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert "different cleaner" in door.kept_out_cleaner_note(path)


def test_a_list_made_under_this_cleaner_says_nothing(tmp_path):
    path = tmp_path / "kept.json"
    _keep(path, PASSAGES[0], "aether")
    assert door.kept_out_cleaner_note(path) == ""


def test_a_list_from_before_the_stamp_says_nothing_but_is_stamped_on_the_next_save(tmp_path):
    path = tmp_path / "kept.json"
    entry = {
        "fp": door.fingerprint(PASSAGES[0]),
        "why": "older",
        "by": "aether",
        "on": "2026-11-20",
    }
    path.write_text(json.dumps({"entries": [entry]}), encoding="utf-8")
    assert door.kept_out_cleaner_note(path) == ""
    _keep(path, PASSAGES[1], "aria")
    assert json.loads(path.read_text(encoding="utf-8"))["cleaner"] == door.CLEANER
    assert len(door._kept_out_entries(path)) == 2


def test_a_missing_list_has_no_cleaner_note(tmp_path):
    assert door.kept_out_cleaner_note(tmp_path / "none.json") == ""


def test_who_kept_it_out_comes_from_the_seat_not_a_typed_default(monkeypatch):
    import divineos.core.identity as identity

    monkeypatch.setattr(identity, "get_my_identity", lambda *a, **k: "aria")
    assert door.acting_name("") == "aria"
    assert door.acting_name("   ") == "aria"


def test_a_named_author_is_kept_as_named(monkeypatch):
    import divineos.core.identity as identity

    monkeypatch.setattr(identity, "get_my_identity", lambda *a, **k: "aria")
    assert door.acting_name("andrew") == "andrew"


def test_an_unset_seat_with_no_name_is_refused_in_plain_words(monkeypatch):
    import divineos.core.identity as identity

    def unset(*a, **k):
        raise identity.IdentityNotSetError("no identity")

    monkeypatch.setattr(identity, "get_my_identity", unset)
    with pytest.raises(ValueError, match="who you are"):
        door.acting_name("")
