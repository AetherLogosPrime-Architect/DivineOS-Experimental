"""The memory drawer: memories set aside during work, filed in the ritual.

Andrew 2026-10-04: a place to store the memories I want filed, which re-opens
during the compaction ritual so they are done all at once.
"""

import pytest

from divineos.core.holding import (
    MAX_SESSIONS_UNREVIEWED,
    age_holding,
    file_memory,
    get_stale_items,
    hold,
    init_holding_table,
    let_go,
    memories_to_file,
)


@pytest.fixture(autouse=True)
def _setup():
    init_holding_table()


def test_a_held_memory_is_in_the_drawer():
    item = hold("his father sold used cars", mode="memory")
    assert [m["item_id"] for m in memories_to_file()] == [item]


def test_memories_never_age_out_of_the_drawer():
    item = hold("keep me", mode="memory")
    other = hold("an ordinary held thing")
    for _ in range(MAX_SESSIONS_UNREVIEWED + 1):
        age_holding()
    assert item in [m["item_id"] for m in memories_to_file()]
    stale = [s["item_id"] for s in get_stale_items()]
    assert other in stale
    assert item not in stale


def test_filing_refuses_without_a_real_file(tmp_path):
    item = hold("keep me", mode="memory")
    assert file_memory(item, tmp_path / "missing.md") is False
    (tmp_path / "blank.md").write_text("  \n", encoding="utf-8")
    assert file_memory(item, tmp_path / "blank.md") is False
    assert item in [m["item_id"] for m in memories_to_file()]


def test_filing_with_the_file_empties_the_drawer(tmp_path):
    item = hold("keep me", mode="memory")
    memory = tmp_path / "keep-me.md"
    memory.write_text("---\nname: keep-me\n---\n\nKept.\n", encoding="utf-8")
    assert file_memory(item, memory) is True
    assert memories_to_file() == []


def test_letting_a_memory_go_moves_it_cold_and_needs_a_reason(tmp_path, monkeypatch):
    from click.testing import CliRunner

    from divineos.cli import cli
    from divineos.core import memory_linkage_retriever as r

    monkeypatch.setattr(r, "_memory_files_dir", lambda: tmp_path)
    item = hold("nothing in memory expires", mode="memory")
    refused = CliRunner().invoke(cli, ["hold", "let-go", item])
    assert refused.exit_code != 0
    assert memories_to_file()
    done = CliRunner().invoke(cli, ["hold", "let-go", item, "--note", "kept cold"])
    assert done.exit_code == 0, done.output
    cold = (tmp_path / "cold" / f"{item}.md").read_text(encoding="utf-8")
    assert "nothing in memory expires" in cold and "kept cold" in cold
    assert memories_to_file() == []


def test_letting_go_also_empties_the_drawer():
    item = hold("not worth keeping after all", mode="memory")
    assert let_go(item, note="duplicate of an existing memory")
    assert memories_to_file() == []
