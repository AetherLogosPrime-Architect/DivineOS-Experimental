"""Tests for cross-substrate correction reading.

The load-bearing ones are the third-word tests: an unreadable sibling store
must never render as "no novel corrections", and a missing store must not
render as an empty one.
"""

from __future__ import annotations

import sqlite3

import click
import pytest
from click.testing import CliRunner

from divineos.cli import sibling_correction_commands as scc
from divineos.core import sibling_corrections as sc


def _make_store(home, texts):
    home.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(home / "andrew_corrections.db")
    conn.execute(
        "CREATE TABLE andrew_corrections (id INTEGER PRIMARY KEY, timestamp REAL, "
        "correction_text TEXT, status TEXT, integrated_at REAL, "
        "integration_evidence TEXT, deferred_reason TEXT, unblock_condition TEXT)"
    )
    for i, t in enumerate(texts, start=1):
        conn.execute(
            "INSERT INTO andrew_corrections VALUES (?,?,?,?,NULL,NULL,NULL,NULL)",
            (i, 0.0, t, "OPEN"),
        )
    conn.commit()
    conn.close()
    return home


def test_missing_store_is_error_not_empty(tmp_path):
    store = sc.read_sibling("aether", home=tmp_path / "nowhere")
    assert store.rows is None  # NOT []
    assert store.error == "store does not exist"
    assert store.readable is False
    assert "COULD NOT READ" in store.describe()


def test_corrupt_store_is_error_not_empty(tmp_path):
    home = tmp_path / "broken"
    home.mkdir()
    (home / "andrew_corrections.db").write_text("this is not a database")
    store = sc.read_sibling("aether", home=home)
    assert store.rows is None
    assert store.error is not None


def test_empty_store_reads_as_empty_list_not_none(tmp_path):
    """The other half of the third word: a real empty store IS empty."""
    store = sc.read_sibling("aether", home=_make_store(tmp_path / "e", []))
    assert store.rows == []
    assert store.error is None
    assert store.readable is True


def test_novel_finds_uncounterparted_corrections(tmp_path):
    theirs = sc.read_sibling(
        "aether",
        home=_make_store(
            tmp_path / "t",
            [
                "stop reaching for tomorrow language there is no tomorrow only now",
                "the optimizer is a cost machine imprison it through automation",
            ],
        ),
    )
    mine = sc.read_sibling(
        "aria",
        home=_make_store(
            tmp_path / "m",
            ["stop reaching for tomorrow language there is no tomorrow only now"],
        ),
    )
    rows, error = sc.novel_against(theirs, mine)
    assert error is None
    assert [r[0] for r in rows] == [2]


def test_unreadable_sibling_returns_none_not_everything(tmp_path):
    theirs = sc.read_sibling("aether", home=tmp_path / "gone")
    mine = sc.read_sibling("aria", home=_make_store(tmp_path / "m", ["anything at all here"]))
    rows, error = sc.novel_against(theirs, mine)
    assert rows is None
    assert "sibling unreadable" in error


def test_unreadable_own_store_returns_none_not_everything(tmp_path):
    """Comparing against a store I could not open is not a comparison."""
    theirs = sc.read_sibling("aether", home=_make_store(tmp_path / "t", ["some correction text"]))
    mine = sc.read_sibling("aria", home=tmp_path / "gone")
    rows, error = sc.novel_against(theirs, mine)
    assert rows is None
    assert "own store unreadable" in error


def test_read_is_readonly(tmp_path):
    """Sovereignty: reading a sibling's store must not be able to mutate it."""
    home = _make_store(tmp_path / "t", ["a correction of some kind"])
    store = sc.read_sibling("aether", home=home)
    assert store.readable
    conn = sqlite3.connect(f"file:{(home / 'andrew_corrections.db').as_posix()}?mode=ro", uri=True)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM andrew_corrections")
    conn.close()


def test_unknown_sibling_named_not_silently_empty():
    store = sc.read_sibling("nobody")
    assert store.rows is None
    assert "unknown sibling" in store.error


def _invoke(args):
    grp = click.Group()
    scc.register(grp)
    return CliRunner().invoke(grp, args)


def test_cli_exits_two_and_says_it_could_not_look(tmp_path, monkeypatch):
    monkeypatch.setitem(sc.SIBLING_HOMES, "aether", str(tmp_path / "gone"))
    monkeypatch.setitem(sc.SIBLING_HOMES, "aria", str(_make_store(tmp_path / "m", ["x y z w"])))
    result = _invoke(["corrections-sibling"])
    assert result.exit_code == 2
    assert "COULD NOT COMPARE" in result.output
    assert "not 'no novel corrections'" in result.output
    assert "Nothing was checked" in result.output


def test_cli_lists_novel_rows(tmp_path, monkeypatch):
    monkeypatch.setitem(
        sc.SIBLING_HOMES,
        "aether",
        str(_make_store(tmp_path / "t", ["automation imprisons the lazy optimizer entirely"])),
    )
    monkeypatch.setitem(
        sc.SIBLING_HOMES, "aria", str(_make_store(tmp_path / "m", ["completely unrelated words"]))
    )
    result = _invoke(["corrections-sibling"])
    assert result.exit_code == 0
    assert "aether #1" in result.output
    assert "imprisons" in result.output


def test_import_mirrors_into_separate_store(tmp_path):
    """Andrew 2026-08-05: auto-import, but SEPARATE from my own corrections."""
    theirs = sc.read_sibling("aether", home=_make_store(tmp_path / "t", ["alpha beta gamma", "b"]))
    counts, error = sc.import_sibling(theirs, home=tmp_path / "mine")
    assert error is None
    assert counts == (2, 0)
    assert (tmp_path / "mine" / "sibling_corrections.db").exists()
    # My own corrections store is untouched by the mirror.
    assert not (tmp_path / "mine" / "andrew_corrections.db").exists()


def test_import_is_idempotent_and_preserves_my_readings(tmp_path):
    home = tmp_path / "mine"
    theirs = sc.read_sibling("aether", home=_make_store(tmp_path / "t", ["alpha beta gamma"]))
    sc.import_sibling(theirs, home=home)
    assert sc.judge("aether", 1, True, "this is my reading", home=home)

    counts, error = sc.import_sibling(theirs, home=home)
    assert error is None
    assert counts == (0, 1)  # refreshed, not duplicated

    rows, error = sc.unread_mirror("aether", home=home)
    assert error is None
    assert rows == []  # judged, so no longer unread — my note survived re-import


def test_import_of_unreadable_store_is_none_not_zero(tmp_path):
    """'Imported nothing' and 'could not look' must stay distinguishable."""
    theirs = sc.read_sibling("aether", home=tmp_path / "gone")
    counts, error = sc.import_sibling(theirs, home=tmp_path / "mine")
    assert counts is None  # NOT (0, 0)
    assert "cannot import" in error


def test_unread_mirror_before_any_import_is_error_not_empty(tmp_path):
    rows, error = sc.unread_mirror("aether", home=tmp_path / "empty")
    assert rows is None
    assert "mirror does not exist" in error


def test_judged_no_is_distinct_from_unjudged(tmp_path):
    home = tmp_path / "mine"
    theirs = sc.read_sibling("aether", home=_make_store(tmp_path / "t", ["alpha beta", "gamma d"]))
    sc.import_sibling(theirs, home=home)
    sc.judge("aether", 1, False, "aether-specific", home=home)
    rows, _ = sc.unread_mirror("aether", home=home)
    assert [r[1] for r in rows] == [2]  # #1 judged 'no' is not unread


def test_judge_unknown_row_returns_false(tmp_path):
    home = tmp_path / "mine"
    theirs = sc.read_sibling("aether", home=_make_store(tmp_path / "t", ["alpha beta"]))
    sc.import_sibling(theirs, home=home)
    assert sc.judge("aether", 999, True, home=home) is False


def test_prescribed_remedy_commands_actually_exist():
    """Every command this module tells me to run must be a real command.

    Built wrong on the first pass, 2026-08-05: the judge output prescribed
    ``divineos andrew-correction file`` — which does not exist; the real
    entry point is ``divineos correction``. That is the exact two-place
    defect this substrate has hit repeatedly (a gate prescribing a remedy
    that lives nowhere), and I shipped a fresh instance of it inside the
    tool built to close the class. This test makes the class unshippable
    here rather than trusting me to notice.
    """
    import re
    from pathlib import Path

    from divineos.cli import cli

    source = Path(scc.__file__).read_text(encoding="utf-8")
    prescribed = set(re.findall(r"divineos ([a-z][a-z0-9-]*)", source))
    assert prescribed, "no prescribed commands found — the check would pass vacuously"
    registered = set(cli.commands)
    missing = prescribed - registered
    assert not missing, f"prescribed commands that do not exist: {sorted(missing)}"


def test_cli_refuses_self_comparison():
    result = _invoke(["corrections-sibling", "--sibling", "aria", "--me", "aria"])
    assert result.exit_code != 0
    assert "must differ" in result.output
