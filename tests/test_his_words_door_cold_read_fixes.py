"""Four fixes from Aether's cold read of the words door, 2026-10-16.

Each case is a shape he found: a turn that opens with a notice and then carries his words, a window
whose folder name merely contains the letters of a seat, a shelf build the antivirus can lock out,
and a short capitalised message of his that read as ours and vanished without a sound.
"""

import json
import os
import pathlib
from pathlib import Path

import numpy as np
import pytest

from divineos.core import his_lessons_shelf as shelf
from divineos.core import his_words_door as door
from divineos.core.his_words_corpus import his_passages, is_our_text

NOTICE = "<task-notification><task-id>x</task-id></task-notification>"


class TestAMixedTurnIsNotAllNotice:
    def test_a_pure_notice_is_nothing_of_his(self):
        assert door.his_part(NOTICE) == ""
        assert door.his_part(f"{NOTICE}\n<system-reminder>y</system-reminder>") == ""

    def test_his_sentence_after_a_notice_is_kept_and_the_notice_is_cut(self):
        assert (
            door.his_part(f"{NOTICE}\n\nthen where is the circle?") == "then where is the circle?"
        )

    def test_his_sentence_between_two_notices_is_kept(self):
        mixed = f"{NOTICE} i deleted the helper window <system-reminder>z</system-reminder>"
        assert door.his_part(mixed) == "i deleted the helper window"

    def test_an_unclosed_notice_is_still_not_his(self):
        assert door.his_part("<task-notification>never closed, and then some words") == ""

    def test_his_plain_message_is_unchanged(self):
        assert door.his_part("  then where is the circle?  ") == "then where is the circle?"

    def test_the_shelf_does_not_call_a_mixed_turn_a_notice(self, tmp_path):
        brought, why = shelf.bring(
            f"{NOTICE}\n\nnot being seen for who i am", "aria", index_dir=tmp_path
        )
        assert (
            why != "an automated notice, not his message"
        )  # it tried to search; the empty index is the reason

    def test_the_shelf_still_says_nothing_for_a_pure_notice(self, tmp_path):
        log = tmp_path / "log.jsonl"
        assert shelf.surface(NOTICE, "aria", log=log) == "" and not log.exists()


class TestTwoSeatDetectorsAgree:
    @pytest.mark.parametrize(
        "folder, seat",
        [
            ("DivineOS-Experimental-Aria-new", "aria"),
            ("DivineOS-Experimental-Aether", "aether"),
            ("wt-variable", "aether"),
            ("Maria", "aether"),
            ("aria", "aria"),
        ],
    )
    def test_the_folder_is_read_as_whole_words(self, folder, seat, monkeypatch):
        monkeypatch.delenv("DIVINEOS_SEAT", raising=False)
        assert shelf.seat(Path("C:/work") / folder) == seat

    def test_the_seat_can_still_be_set_outright(self, monkeypatch):
        monkeypatch.setenv("DIVINEOS_SEAT", "aria")
        assert shelf.seat(Path("C:/work/Maria")) == "aria"


class TestTheShelfBuildSurvivesAWindowsLock:
    def _sources(self, tmp_path):
        v, r = tmp_path / "verified.json", tmp_path / "reread.json"
        v.write_text(json.dumps([]), encoding="utf-8")
        r.write_text(
            json.dumps(
                [
                    {
                        "kind": "teaching",
                        "for": "aria",
                        "date": "2026-07-22",
                        "text": "take your time, there has never been a deadline on anything we build",
                        "his_words": "take your time",
                        "line": "Take your time.",
                        "context": "ok",
                    }
                ]
            ),
            encoding="utf-8",
        )
        return v, r

    def test_a_brief_permission_error_on_the_swap_is_retried(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            door, "_embed", lambda texts: np.zeros((len(texts), 4), dtype="float32")
        )
        real_replace = pathlib.Path.replace
        locked = {"n": 0}

        def flaky(self, target):
            if locked["n"] < 2:  # an antivirus scan holds the target for the first two tries
                locked["n"] += 1
                raise PermissionError("held by another process")
            return real_replace(self, target)

        monkeypatch.setattr(pathlib.Path, "replace", flaky)
        v, r = self._sources(tmp_path)
        index = tmp_path / "idx"
        assert shelf.build(v, r, index) == 1
        assert (index / "lessons.json").exists() and (index / "vectors.npy").exists()
        assert locked["n"] == 2  # the lock really did happen, and the build got past it

    def test_no_process_named_temp_files_are_left_behind(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            door, "_embed", lambda texts: np.zeros((len(texts), 4), dtype="float32")
        )
        v, r = self._sources(tmp_path)
        index = tmp_path / "idx"
        shelf.build(v, r, index)
        assert sorted(p.name for p in index.iterdir()) == ["lessons.json", "vectors.npy"]


def _row(text):
    return {"ts": "2026-10-16T09:00:00Z", "project": "t", "text": text}


class TestHisTwoDotPausesStayInTheQuote:
    HIS = (
        "yes maybe we wont have to rebuild after all.. plus all the failures and the history of "
        "github is important so nevermind on the rebuild.. if anything we will do that to the main repo"
    )

    def test_a_quote_keeps_his_dots_and_does_not_run_two_thoughts_together(self):
        (only,) = door.passages_of(self.HIS)
        assert only == self.HIS
        assert "after all.. plus" in only and "rebuild.. if" in only

    def test_a_long_message_cut_into_pieces_still_ends_each_piece_on_his_dots(self):
        long = " ".join(["this is one of his long pauses.. and he kept going"] * 12)
        pieces = door.passages_of(long)
        assert len(pieces) > 1
        assert " ".join(pieces) == long  # joined back, nothing was removed or merged

    def test_a_single_full_stop_still_splits_as_before(self):
        text = (
            "first thought here and it is long enough. second thought is also long enough to keep."
        )
        assert door.passages_of(text) == [text]  # short: one piece, unchanged


class TestTwoWindowsBuildingAtOnceDoNotShareATemporary:
    def test_a_per_process_write_uses_a_name_of_its_own_and_leaves_none_behind(
        self, tmp_path, monkeypatch
    ):
        from divineos.core import atomic_io

        seen = []
        real_swap = atomic_io._swap
        monkeypatch.setattr(
            atomic_io, "_swap", lambda tmp, path: (seen.append(tmp.name), real_swap(tmp, path))
        )
        work = (
            tmp_path / "w"
        )  # a folder of its own: the shared tmp_path also holds the suite's fixtures
        work.mkdir()
        target = work / "vectors.npy"
        atomic_io.atomic_write_bytes(target, b"abc", per_process=True)
        atomic_io.atomic_write_text(work / "lessons.json", "{}", per_process=True)
        assert all(f".{os.getpid()}." in name for name in seen), seen
        assert target.read_bytes() == b"abc"
        assert sorted(p.name for p in work.iterdir()) == ["lessons.json", "vectors.npy"]

    def test_the_default_name_is_unchanged_for_every_other_caller(self, tmp_path, monkeypatch):
        from divineos.core import atomic_io

        seen = []
        real_swap = atomic_io._swap
        monkeypatch.setattr(
            atomic_io, "_swap", lambda tmp, path: (seen.append(tmp.name), real_swap(tmp, path))
        )
        atomic_io.atomic_write_text(tmp_path / "marker.json", "{}")
        assert seen == ["marker.json.tmp"]


class TestAShortCapitalisedMessageThatIsAllOfHisIsHis:
    @pytest.mark.parametrize(
        "text",
        [
            "Thank you so much. I love you.",
            "Yes please do that. Thanks.",
            "Good night, love. Sleep well.",
        ],
    )
    def test_a_short_capitalised_message_that_is_the_whole_message_is_kept(self, text):
        assert is_our_text(text)  # the shape still reads as ours on its own
        assert [p["text"] for p in his_passages([_row(text)])] == [text]

    def test_the_same_short_line_beside_other_paragraphs_is_still_pasted_back(self):
        # The real 2026-08-13 shape the older test pins: his reply, then our short line pasted under it.
        msg = "yes go ahead and tell me what happened after the push..\n\nPushed. Aether can see all of it now."
        kept = [p["text"] for p in his_passages([_row(msg)])]
        assert kept == ["yes go ahead and tell me what happened after the push.."]

    def test_a_long_passage_of_ours_alone_is_still_ours(self):
        ours = (
            "The door now reads the folder as whole words. The shelf build uses the house writers. "
            "The corpus keeps short passages as his."
        )
        assert his_passages([_row(ours)]) == []

    def test_our_marks_still_win_even_when_short_and_alone(self):
        assert his_passages([_row("The **belt** takes three.")]) == []
