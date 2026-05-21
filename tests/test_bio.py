"""Tests for the bio sheet — the agent's own page."""

from __future__ import annotations

import threading

import pytest

from divineos.core.bio import (
    bio_briefing_surface,
    bio_current,
    bio_history,
    bio_write,
    init_bio_table,
)


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    """Point the bio storage at a fresh temp DB for each test."""
    db_file = tmp_path / "bio_test.db"
    monkeypatch.setenv("DIVINEOS_DB_PATH", str(db_file))
    init_bio_table()


def test_bio_starts_empty():
    assert bio_current(author="aether") is None
    assert bio_history(author="aether") == []


def test_bio_write_creates_v1():
    bio_id = bio_write("# First version\n\nHello.", author="aether")
    assert bio_id

    current = bio_current(author="aether")
    assert current is not None
    assert current["version"] == 1
    assert current["supersedes"] is None
    assert "Hello" in current["content"]
    assert current["author"] == "aether"


def test_bio_supersession_chain():
    id1 = bio_write("# v1\nfirst", author="aether")
    id2 = bio_write("# v2\nsecond", author="aether")
    id3 = bio_write("# v3\nthird", author="aether")

    current = bio_current(author="aether")
    assert current["version"] == 3
    assert current["supersedes"] == id2
    assert "third" in current["content"]

    history = bio_history(author="aether")
    assert len(history) == 3
    assert history[0]["bio_id"] == id3
    assert history[0]["supersedes"] == id2
    assert history[1]["supersedes"] == id1
    assert history[2]["supersedes"] is None  # v1 is the root


def test_bio_empty_content_rejected():
    with pytest.raises(ValueError):
        bio_write("", author="aether")
    with pytest.raises(ValueError):
        bio_write("   \n\t  ", author="aether")


def test_bio_per_author_isolation():
    bio_write("# Aether's bio", author="aether")
    bio_write("# Aria's bio", author="aria")

    aether = bio_current(author="aether")
    aria = bio_current(author="aria")
    assert "Aether" in aether["content"]
    assert "Aria" in aria["content"]
    assert aether["version"] == 1
    assert aria["version"] == 1


def test_briefing_surface_when_empty():
    block = bio_briefing_surface(author="nobody")
    assert "No bio yet" in block
    assert "divineos bio edit" in block


def test_briefing_surface_with_bio():
    bio_write("# Aether\n\nThis is who I am right now.", author="aether")
    block = bio_briefing_surface(author="aether")
    assert "v1" in block
    assert "This is who I am" in block
    assert "divineos bio show" in block


def test_briefing_surface_truncates_long_content():
    long_content = "# Bio\n\n" + ("paragraph of words " * 100)
    bio_write(long_content, author="aether")
    block = bio_briefing_surface(author="aether")
    # The excerpt should be capped — block size is limited.
    assert "..." in block
    assert len(block) < 800  # bounded


def test_concurrent_bio_write_distinct_versions():
    """Finding AAA (Aletheia audit 2026-05-20): concurrent bio_write must not
    both read max-version N and both insert N+1. BEGIN IMMEDIATE serializes
    the read-max -> insert so versions are a contiguous unique sequence.
    """
    n = 8
    barrier = threading.Barrier(n)

    def worker(i: int) -> None:
        barrier.wait()
        bio_write(f"# Version body {i}\n\ncontent", author="aether")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    history = bio_history(author="aether", limit=100)
    versions = sorted(h["version"] for h in history)
    assert len(history) == n
    # Contiguous 1..n with no duplicates — no version collision.
    assert versions == list(range(1, n + 1)), versions
