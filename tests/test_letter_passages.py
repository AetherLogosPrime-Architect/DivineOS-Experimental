"""Letters matched by passage (docs/drafts/letters_by_passage_draft_2026-10-06.md).

The splitter's edges, the index's honesty about failure, and the one letter slot.
The index is built here from a fake encoder and a temporary drawer, so no model is
needed, and the failures are real ones: a missing index, a mismatch, a wrong size.
"""

from __future__ import annotations

import sqlite3

import numpy as np
import pytest

from divineos.core import letter_passages as lp
from divineos.core import vector_drawer


def words(n: int, tag: str = "w") -> str:
    return " ".join(f"{tag}{i}" for i in range(n))


# ------------------------------------------------------------------ the splitter


def test_a_block_of_exactly_150_words_stays_whole_and_151_splits():
    assert lp.split_passages(words(150)) == [words(150)]
    assert len(lp.split_passages(words(151))) > 1


def test_a_short_paragraph_joins_the_next_and_none_is_lost():
    text = f"{words(10, 'a')}\n\n{words(10, 'b')}\n\n{words(10, 'c')}"
    got = lp.split_passages(text)
    assert len(got) == 1 and "a0" in got[0] and "c9" in got[0]


def test_a_merge_never_runs_past_the_maximum():
    text = f"{words(59, 'a')}\n\n{words(150, 'b')}"
    assert all(len(p.split()) <= lp.MAX_WORDS for p in lp.split_passages(text))


def test_a_run_with_no_sentence_ends_is_still_cut():
    got = lp.split_passages(words(1000))
    assert len(got) > 1 and all(len(p.split()) <= lp.MAX_WORDS for p in got)


def test_the_footer_and_sign_off_are_never_passages():
    body = words(40, "real")
    text = (
        f"# A title\n\n**Written:** 2026-10-06\n\n---\n\n{body}\n\n—\nAria\n(2026-10-06)\n\n---\n\n"
        "— the thread so far —\n\nThis is letter 1 of the thread from me to you.\n\n1. one.md\n"
    )
    got = lp.split_passages(text)
    assert got and all("real0" in p for p in got)
    assert not any("thread so far" in p or "(2026-10-06)" in p for p in got)


def test_a_letter_that_is_only_boilerplate_never_surfaces_its_footer():
    text = "**Written:** 2026-10-06\n\n---\n\n— the thread so far —\n\nThis is letter 1."
    assert all("thread so far" not in p for p in lp.split_passages(text))


def test_a_short_letter_is_still_findable():
    assert len(lp.split_passages("Yes. Do it now, and thank you for asking me first today.")) == 1


def test_an_empty_letter_gives_nothing():
    assert lp.split_passages("") == []
    assert lp.split_passages("   \n\n  ") == []


# ------------------------------------------------------------------ the file lister


def test_a_letter_in_every_checkout_is_listed_once(tmp_path):
    roots = []
    for name in ("mine", "main", "hers"):
        letters = tmp_path / name / "family" / "letters"
        letters.mkdir(parents=True)
        (letters / "aria-to-aether-2026-09-24-same.md").write_text(
            "the same letter", encoding="utf-8"
        )
        roots.append(letters)
    assert len(lp.letter_files(roots)) == 1


def test_the_same_path_twice_is_listed_once(tmp_path):
    shared = tmp_path / "shared"
    shared.mkdir()
    (shared / "letter.md").write_text("shared letter", encoding="utf-8")
    assert len(lp.letter_files([shared, shared])) == 1


def test_no_roots_lists_nothing():
    assert lp.letter_files([]) == []


# ------------------------------------------------------------------ the index

DIM = 8
AXIS = {"alpha": 0, "beta": 1, "gamma": 2}


def _vec(slot: int) -> np.ndarray:
    v = np.zeros(DIM, dtype=np.float32)
    v[slot % DIM] = 1.0
    return v


def _encode(batch):
    return np.vstack([_vec(AXIS[t.split()[0].rstrip("0123456789")]) for t in batch])


@pytest.fixture
def built(monkeypatch, tmp_path):
    """Two letters on known axes: one.md has an alpha and a beta passage, two.md a gamma one."""
    monkeypatch.setenv("DIVINEOS_VECTOR_DRAWER", str(tmp_path / "data" / "vectors.db"))
    monkeypatch.setattr(vector_drawer, "_READER", None)
    monkeypatch.setattr(vector_drawer, "_bulk_encoder", lambda: _encode)
    lp._reset_cache()
    letters = tmp_path / "family" / "letters"
    letters.mkdir(parents=True)
    (letters / "one.md").write_text(
        f"{words(40, 'alpha')}\n\n{words(40, 'beta')}", encoding="utf-8"
    )
    (letters / "two.md").write_text(words(40, "gamma"), encoding="utf-8")
    out = lp.build(roots=[letters])
    yield out
    lp._reset_cache()


def test_nothing_built_is_a_stated_problem_not_an_empty_answer(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_VECTOR_DRAWER", str(tmp_path / "data" / "vectors.db"))
    lp._reset_cache()
    hits, problem = lp.best_letters(_vec(0), k=1)
    assert hits == [] and problem and "not built" in problem


def test_the_build_counts_what_it_made(built):
    assert (
        built["letters"] == 2 and built["passages"] == 3 and built["passages_without_vector"] == 0
    )


def test_the_passage_that_matches_is_the_one_returned_not_the_letters_opening(built):
    hits, problem = lp.best_letters(_vec(1), k=1)
    assert problem is None and len(hits) == 1
    assert hits[0].name == "one" and hits[0].text.startswith("beta0")


def test_each_letter_appears_once_with_its_best_passage(built):
    hits, _ = lp.best_letters(_vec(0), k=5)
    assert [h.name for h in hits].count("one") == 1


def test_k_is_the_most_letters_returned(built):
    v = _vec(0) + _vec(1) + _vec(2)
    assert len(lp.best_letters(v, k=1)[0]) == 1
    assert len(lp.best_letters(v, k=5)[0]) == 2


def test_below_the_floor_is_searched_and_empty_not_a_problem(built):
    hits, problem = lp.best_letters(_vec(5), k=1, floor=0.5)
    assert hits == [] and problem is None


def test_exactly_the_floor_is_kept(built):
    hits, _ = lp.best_letters(_vec(0), k=1, floor=1.0)
    assert len(hits) == 1


def test_a_zero_query_is_empty_and_not_a_problem(built):
    assert lp.best_letters(np.zeros(DIM, dtype=np.float32), k=1) == ([], None)


def test_a_vector_of_the_wrong_size_is_a_stated_problem(built):
    hits, problem = lp.best_letters(np.ones(DIM + 3, dtype=np.float32), k=1)
    assert hits == [] and problem and "different vector size" in problem


def test_a_matrix_and_database_that_disagree_is_a_stated_problem(built):
    conn = sqlite3.connect(str(lp.db_path()))
    conn.execute("DELETE FROM passages WHERE row = 0")
    conn.commit()
    conn.close()
    hits, problem = lp.best_letters(_vec(0), k=1)
    assert hits == [] and problem and "disagrees with itself" in problem


def test_an_unreadable_database_is_a_stated_problem(built):
    lp.db_path().write_bytes(b"this is not a database")
    hits, problem = lp.best_letters(_vec(0), k=1)
    assert hits == [] and problem and "could not be read" in problem


def test_a_rebuild_replaces_both_files_and_leaves_no_temporary_ones(built, monkeypatch, tmp_path):
    letters = tmp_path / "family" / "letters"
    (letters / "three.md").write_text(words(40, "alpha"), encoding="utf-8")
    out = lp.build(roots=[letters])
    assert out["passages"] == 4
    assert not list(lp.matrix_path().parent.glob("*.new"))
    assert len(lp.best_letters(_vec(0), k=5)[0]) == 3
