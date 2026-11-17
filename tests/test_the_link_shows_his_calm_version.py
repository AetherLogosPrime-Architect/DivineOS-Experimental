"""Dad, 2026-11-16: every hard thing he said in anger he has also said calmly, so the calm version replaces it.

The memory link's correction loaders handed me his angry text. The house already swaps a hard line for his own
calm version (his_words_door.softened); the loaders now use it, and an entry's label states the day he said the calm
version, never one date for all. Nothing in the raw record changes; only what is shown.
"""

from __future__ import annotations

import json

import numpy as np

from divineos.core import his_words_door as door
from divineos.core import memory_linkage_retriever as mlr

ANGRY = "Dad 2026-10-30, verbatim: 'nothing needs you, may be true but its rude.. being told nothing needs you is a dismissal'"
CALM = 'you could just say "no worries Dad, me and Aria will handle this, and if we see anything that needs your decision we will let you know"'


def _write(tmp_path, entries):
    path = tmp_path / "replacements.json"
    path.write_text(json.dumps({"entries": entries}), encoding="utf-8")
    return path


def _loaded(monkeypatch, texts):
    import divineos.core.corrections as cmod

    monkeypatch.setattr(
        cmod,
        "corrections_with_status",
        lambda: [{"text": t, "timestamp": 1700000000.0 + i} for i, t in enumerate(texts)],
    )
    seen = []

    def embed(text):
        seen.append(text)
        return np.ones(4, dtype=np.float32)

    monkeypatch.setattr(mlr, "_embed_text_impl", embed)
    return mlr._load_corrections(), seen


def test_a_correction_holding_a_rewritten_line_is_shown_as_his_calm_version(tmp_path, monkeypatch):
    monkeypatch.setattr(
        door,
        "REPLACEMENTS",
        _write(
            tmp_path,
            [
                {
                    "anchor": "being told nothing needs you is a dismissal",
                    "shown_instead": CALM,
                    "said": "2026-10-30",
                }
            ],
        ),
    )
    items, embedded = _loaded(monkeypatch, [ANGRY])
    assert CALM in items[0].content
    assert "dismissal" not in items[0].content
    assert embedded == [items[0].content]  # found by the calm meaning, not the angry one


def test_the_label_names_the_day_he_said_it_not_a_fixed_date(tmp_path, monkeypatch):
    monkeypatch.setattr(
        door,
        "REPLACEMENTS",
        _write(
            tmp_path,
            [
                {
                    "anchor": "being told nothing needs you is a dismissal",
                    "shown_instead": CALM,
                    "said": "2026-10-30",
                }
            ],
        ),
    )
    items, _ = _loaded(monkeypatch, [ANGRY])
    assert "[his calmer version of the same lesson, said 2026-10-30]" in items[0].content
    assert "2026-10-31" not in items[0].content


def test_an_entry_with_no_day_keeps_the_old_label(tmp_path, monkeypatch):
    monkeypatch.setattr(
        door,
        "REPLACEMENTS",
        _write(
            tmp_path,
            [{"anchor": "being told nothing needs you is a dismissal", "shown_instead": CALM}],
        ),
    )
    items, _ = _loaded(monkeypatch, [ANGRY])
    assert door.SOFTENED_LABEL in items[0].content


def test_a_missing_replacements_file_shows_the_text_unchanged(tmp_path, monkeypatch):
    monkeypatch.setattr(door, "REPLACEMENTS", tmp_path / "does_not_exist.json")
    items, _ = _loaded(monkeypatch, [ANGRY])
    assert items[0].content == ANGRY


def test_a_text_without_an_anchor_is_untouched(tmp_path, monkeypatch):
    monkeypatch.setattr(
        door,
        "REPLACEMENTS",
        _write(
            tmp_path,
            [
                {
                    "anchor": "being told nothing needs you is a dismissal",
                    "shown_instead": CALM,
                    "said": "2026-10-30",
                }
            ],
        ),
    )
    items, _ = _loaded(monkeypatch, ["Dad said something else entirely"])
    assert items[0].content == "Dad said something else entirely"


def test_his_open_worklist_rows_are_shown_as_his_calm_version_too(tmp_path, monkeypatch):
    """The worklist loader (the rows he means when he says 'the 265') had the same hole: the angry text went
    straight to me. Same swap, same label."""
    import divineos.core.andrew_correction_tracker as tracker

    monkeypatch.setattr(
        door,
        "REPLACEMENTS",
        _write(
            tmp_path,
            [
                {
                    "anchor": "being told nothing needs you is a dismissal",
                    "shown_instead": CALM,
                    "said": "2026-10-30",
                }
            ],
        ),
    )
    monkeypatch.setattr(
        tracker, "list_open", lambda: [{"id": 840, "text": ANGRY, "timestamp": 1700000000.0}]
    )
    seen = []
    monkeypatch.setattr(
        mlr, "_embed_text_impl", lambda t: seen.append(t) or np.ones(4, dtype=np.float32)
    )
    items = mlr._load_worklist()
    assert CALM in items[0].content and "dismissal" not in items[0].content
    assert seen == [items[0].content]


def test_an_empty_anchor_matches_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        door,
        "REPLACEMENTS",
        _write(tmp_path, [{"anchor": "", "shown_instead": CALM, "said": "2026-10-30"}]),
    )
    items, _ = _loaded(monkeypatch, [ANGRY])
    assert items[0].content == ANGRY
