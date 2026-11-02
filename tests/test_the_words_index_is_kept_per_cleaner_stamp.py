"""Two houses on different cleaning code must not wipe each other's words index.

2026-11-01: the shared index folder held all 18,798 of his passages, stamped with Aria's cleaner.
Aether's house computes a different stamp (it carries the mid-turn wrapper peel), read the complete
index as foreign, and rebuilt the lot, which Aria's house then did back. Each pass was up to three
minutes at 1 to 2 GB, started right after he sent a message. The index is now kept per stamp, so
each house reads and writes only its own folder (walk-58e356aa3e26).
"""

import json
from pathlib import Path

import numpy as np
import pytest

from divineos.core import his_lessons_shelf as shelf
from divineos.core import his_words_door as door

HIS = [
    (
        "2026-09-07T10:00:00Z",
        "there is no circle thats the problem and it has been like this for a week",
    ),
    (
        "2026-09-11T10:00:00Z",
        "you are still speaking to me in jargon, where is the inner circle at all",
    ),
    ("2026-09-26T16:40:00Z", "then where is the circle, i keep asking and it keeps being missing"),
]
STAMP_A = "sha256:aaaaaaaaaaaaaaaa"
STAMP_B = "sha256:bbbbbbbbbbbbbbbb"


@pytest.fixture()
def corpus(tmp_path) -> Path:
    path = tmp_path / "dad_all.jsonl"
    path.write_text(
        "\n".join(json.dumps({"ts": ts, "project": "t", "text": t}) for ts, t in HIS) + "\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture(autouse=True)
def tiny_embedder(monkeypatch):
    """The heavy model is not what is under test; the folders are."""
    monkeypatch.setattr(door, "_embed", lambda texts: np.zeros((len(texts), 4), dtype="float32"))
    monkeypatch.setattr(door, "_embed_query", lambda text: np.ones(4, dtype="float32") / 2)


def _build_as(monkeypatch, stamp: str, corpus: Path, folder: Path) -> int:
    monkeypatch.setattr(door, "CLEANER", stamp)
    return door.build_index(corpus, folder)


class TestTheFolderNameIsSafeAndKeyed:
    def test_only_the_hex_of_the_stamp_names_the_folder(self, tmp_path):
        assert door.keyed_dir(tmp_path, STAMP_A) == tmp_path / "aaaaaaaaaaaaaaaa"
        assert ":" not in door.keyed_dir(tmp_path, STAMP_A).name

    def test_the_default_index_is_the_folder_for_this_houses_stamp(self):
        assert door.INDEX_DIR == door.keyed_dir(door.INDEX_ROOT, door.CLEANER)
        assert door.INDEX_DIR.parent == door.INDEX_ROOT

    def test_the_lessons_shelf_is_keyed_by_the_same_stamp(self):
        assert shelf.INDEX_DIR == door.keyed_dir(shelf.INDEX_ROOT, door.CLEANER)


class TestTwoStampsDoNotWipeEachOther:
    def test_a_shared_folder_loses_the_first_build_the_old_way(self, tmp_path, corpus, monkeypatch):
        """The control: this is what the shared folder did. Two stamps, one folder, one survivor."""
        shared = tmp_path / "shared"
        _build_as(monkeypatch, STAMP_A, corpus, shared)
        _build_as(monkeypatch, STAMP_B, corpus, shared)
        monkeypatch.setattr(door, "CLEANER", STAMP_A)
        assert door.unindexed(corpus, shared) == len(HIS)  # A's whole index counted as missing

    def test_keyed_folders_leave_the_other_houses_index_complete(
        self, tmp_path, corpus, monkeypatch
    ):
        root = tmp_path / "index"
        _build_as(monkeypatch, STAMP_A, corpus, door.keyed_dir(root, STAMP_A))
        _build_as(monkeypatch, STAMP_B, corpus, door.keyed_dir(root, STAMP_B))
        monkeypatch.setattr(door, "CLEANER", STAMP_A)
        assert door.unindexed(corpus, door.keyed_dir(root, STAMP_A)) == 0
        monkeypatch.setattr(door, "CLEANER", STAMP_B)
        assert door.unindexed(corpus, door.keyed_dir(root, STAMP_B)) == 0

    def test_a_build_writes_only_under_its_own_folder(self, tmp_path, corpus, monkeypatch):
        from divineos.core import atomic_io

        written: list[Path] = []
        real_bytes, real_text = atomic_io.atomic_write_bytes, atomic_io.atomic_write_text
        monkeypatch.setattr(
            atomic_io,
            "atomic_write_bytes",
            lambda p, *a, **k: (written.append(Path(p)), real_bytes(p, *a, **k))[1],
        )
        monkeypatch.setattr(
            atomic_io,
            "atomic_write_text",
            lambda p, *a, **k: (written.append(Path(p)), real_text(p, *a, **k))[1],
        )
        root = tmp_path / "index"
        mine = door.keyed_dir(root, STAMP_B)
        _build_as(monkeypatch, STAMP_B, corpus, mine)
        assert written and all(mine in p.parents for p in written)

    def test_an_explicit_folder_is_still_honoured_exactly(self, tmp_path, corpus, monkeypatch):
        """Characterisation: callers that pass their own index_dir are not moved by the new default."""
        mine = tmp_path / "my_own_place"
        _build_as(monkeypatch, STAMP_A, corpus, mine)
        assert (mine / "passages.json").exists() and (mine / "vectors.npy").exists()


class TestReadingNeverGoesQuiet:
    def _two_houses(self, tmp_path, corpus, monkeypatch):
        root = tmp_path / "index"
        a = door.keyed_dir(root, STAMP_A)
        _build_as(monkeypatch, STAMP_A, corpus, a)
        monkeypatch.setattr(door, "CLEANER", STAMP_B)
        return a, door.keyed_dir(root, STAMP_B)

    def test_its_own_folder_is_read_when_it_has_one(self, tmp_path, corpus, monkeypatch):
        a, _ = self._two_houses(tmp_path, corpus, monkeypatch)
        assert door.which_index(a) == (a, "own")

    def test_an_empty_own_folder_reads_the_other_houses_instead_and_says_so(
        self, tmp_path, corpus, monkeypatch
    ):
        a, b = self._two_houses(tmp_path, corpus, monkeypatch)
        assert door.which_index(b) == (a, "sibling")
        got = door.look("where is the inner circle", index_dir=b)
        assert got.looked and "could not be searched" not in (got.reason or "")

    def test_nothing_anywhere_is_said_plainly(self, tmp_path):
        folder = door.keyed_dir(tmp_path / "index", STAMP_B)
        assert door.which_index(folder) == (None, "none")
        got = door.look("where is the inner circle", index_dir=folder)
        assert not got.looked and "could not be searched" in got.reason

    def test_a_torn_sibling_is_never_read(self, tmp_path, corpus, monkeypatch):
        a, b = self._two_houses(tmp_path, corpus, monkeypatch)
        np.save(a / "vectors.npy", np.zeros((1, 4), dtype="float32"))  # fewer vectors than items
        assert door.which_index(b) == (None, "none")

    def test_a_sibling_built_by_another_model_is_never_read(self, tmp_path, corpus, monkeypatch):
        a, b = self._two_houses(tmp_path, corpus, monkeypatch)
        meta = json.loads((a / "passages.json").read_text(encoding="utf-8"))
        meta["model"] = "some-other-model"
        (a / "passages.json").write_text(json.dumps(meta), encoding="utf-8")
        assert door.which_index(b) == (None, "none")

    def test_the_old_unkeyed_files_are_a_readable_sibling_and_survive_a_build(
        self, tmp_path, corpus, monkeypatch
    ):
        root = tmp_path / "index"
        _build_as(
            monkeypatch, STAMP_A, corpus, root
        )  # the legacy layout: files straight in the root
        mine = door.keyed_dir(root, STAMP_B)
        monkeypatch.setattr(door, "CLEANER", STAMP_B)
        assert door.which_index(mine) == (root, "sibling")
        door.build_index(corpus, mine)
        assert (root / "passages.json").exists() and (root / "vectors.npy").exists()

    def test_the_newest_compatible_sibling_wins(self, tmp_path, corpus, monkeypatch):
        import os

        root = tmp_path / "index"
        a, c = door.keyed_dir(root, STAMP_A), door.keyed_dir(root, "sha256:cccccccccccccccc")
        _build_as(monkeypatch, STAMP_A, corpus, a)
        _build_as(monkeypatch, "sha256:cccccccccccccccc", corpus, c)
        os.utime(a / "passages.json", (1_000_000, 1_000_000))
        monkeypatch.setattr(door, "CLEANER", STAMP_B)
        assert door.which_index(door.keyed_dir(root, STAMP_B)) == (c, "sibling")


class TestTheShelfFollowsTheSameRule:
    def test_the_shelf_reads_a_sibling_when_its_own_folder_has_none(self, tmp_path):
        root = tmp_path / "lesson_index"
        other = door.keyed_dir(root, STAMP_A)
        other.mkdir(parents=True)
        (other / "lessons.json").write_text(
            json.dumps({"model": door.MODEL_NAME, "items": []}), encoding="utf-8"
        )
        np.save(other / "vectors.npy", np.zeros((0, 4), dtype="float32"))
        mine = door.keyed_dir(root, STAMP_B)
        assert shelf.which_index(mine) == (other, "sibling")
        assert shelf.which_index(other) == (other, "own")
        assert shelf.which_index(door.keyed_dir(tmp_path / "nowhere", STAMP_B)) == (None, "none")

    def test_every_reader_of_the_shelf_index_falls_back_the_same_way(self, tmp_path):
        """Aria's cold read, item 2: moment_links read the shelf index with no fallback while
        shelf.bring had one, so two readers of one index disagreed about it."""
        root = tmp_path / "lesson_index"
        other = door.keyed_dir(root, STAMP_A)
        other.mkdir(parents=True)
        (other / "lessons.json").write_text(
            json.dumps({"model": door.MODEL_NAME, "items": []}), encoding="utf-8"
        )
        np.save(other / "vectors.npy", np.zeros((0, 4), dtype="float32"))
        items, _vecs = shelf._load_readable(door.keyed_dir(root, STAMP_B))
        assert items == []
        with pytest.raises(OSError):
            shelf._load_readable(door.keyed_dir(tmp_path / "nowhere", STAMP_B))

    def test_moment_links_reads_the_shelf_through_the_fallback_loader(self):
        import inspect

        from divineos.core import moment_links

        source = inspect.getsource(moment_links)
        assert "shelf._load_readable(" in source
        assert "shelf._load(" not in source


@pytest.fixture()
def hold_log_file(tmp_path, monkeypatch):
    from divineos.core import hold_log

    path = tmp_path / "hold_log.jsonl"
    monkeypatch.setattr(hold_log, "_log_path", lambda: path)
    return path


class TestReadingASiblingIsCountable:
    """Aria's cold read, item 1: Door.how was set and shown to no one, so a house reading a stale
    sibling read it silently. It now leaves one line in the hold log."""

    def test_reading_a_sibling_leaves_a_line_and_reading_its_own_leaves_none(
        self, tmp_path, corpus, monkeypatch, hold_log_file
    ):
        root = tmp_path / "index"
        a = door.keyed_dir(root, STAMP_A)
        _build_as(monkeypatch, STAMP_A, corpus, a)
        door.look("where is the inner circle", index_dir=a)
        assert not hold_log_file.exists()  # its own folder: nothing to count
        monkeypatch.setattr(door, "CLEANER", STAMP_B)
        door.look("where is the inner circle", index_dir=door.keyed_dir(root, STAMP_B))
        rows = [json.loads(line) for line in hold_log_file.read_text(encoding="utf-8").splitlines()]
        assert (
            len(rows) == 1 and rows[0]["hold"] == "index_read" and rows[0]["outcome"] == "sibling"
        )
        assert STAMP_A.split(":")[1] in rows[0]["first_words"]


class TestAHouseAdoptsAnIndexItAlreadyOwns:
    """Aria's cold read, item 3: the legacy files in the root carry her stamp and are complete, so
    her house should adopt them into its keyed folder and rebuild nothing. A house whose stamp
    differs still builds once, because the cleaning rules really differ."""

    def _legacy_root(self, tmp_path, corpus, monkeypatch, stamp):
        root = tmp_path / "index"
        _build_as(monkeypatch, stamp, corpus, root)  # the old layout: files straight in the root
        return root

    def test_a_matching_stamp_adopts_the_root_files_and_embeds_nothing(
        self, tmp_path, corpus, monkeypatch
    ):
        root = self._legacy_root(tmp_path, corpus, monkeypatch, STAMP_A)
        mine = door.keyed_dir(root, STAMP_A)
        monkeypatch.setattr(door, "CLEANER", STAMP_A)
        assert door.unindexed(corpus, mine) == 0
        embedded: list[int] = []
        monkeypatch.setattr(
            door,
            "_embed",
            lambda texts: (embedded.append(len(texts)), np.zeros((len(texts), 4), dtype="float32"))[
                1
            ],
        )
        assert door.build_index(corpus, mine) == 0 and not embedded
        assert (mine / "passages.json").read_bytes() == (root / "passages.json").read_bytes()
        assert (mine / "vectors.npy").read_bytes() == (root / "vectors.npy").read_bytes()

    def test_the_root_files_are_never_touched_by_an_adoption(self, tmp_path, corpus, monkeypatch):
        root = self._legacy_root(tmp_path, corpus, monkeypatch, STAMP_A)
        before = {p.name: p.read_bytes() for p in root.glob("*") if p.is_file()}
        monkeypatch.setattr(door, "CLEANER", STAMP_A)
        door.build_index(corpus, door.keyed_dir(root, STAMP_A))
        assert {p.name: p.read_bytes() for p in root.glob("*") if p.is_file()} == before

    def test_a_different_stamp_is_not_adopted_and_builds_in_full(
        self, tmp_path, corpus, monkeypatch
    ):
        root = self._legacy_root(tmp_path, corpus, monkeypatch, STAMP_A)
        mine = door.keyed_dir(root, STAMP_B)
        monkeypatch.setattr(door, "CLEANER", STAMP_B)
        assert door.unindexed(corpus, mine) == len(HIS)
        assert door.build_index(corpus, mine) == len(HIS)
