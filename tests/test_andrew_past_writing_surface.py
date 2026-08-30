"""Smoke tests for andrew_past_writing_surface — the compose-start
context surface that replaced the grep-heavy shell hook 2026-07-23.

Focus: (1) the surface builds without hanging on a real-shape repo,
(2) the output format matches what the compose-start reader expects,
(3) fail-open behavior on missing dirs / unreadable files.
"""

from __future__ import annotations

import pytest

from divineos.core.andrew_past_writing_surface import (
    _first_content_line,
    _read_head,
    _slug_from_letter,
    _title_from_exploration,
    build_surface,
)


@pytest.fixture
def fake_repo(tmp_path):
    """Build a minimal repo structure with letters + explorations."""
    (tmp_path / "family" / "letters").mkdir(parents=True)
    (tmp_path / "exploration" / "aether").mkdir(parents=True)

    # Two letters to Andrew
    (tmp_path / "family" / "letters" / "aether-to-andrew-2026-05-08-late.md").write_text(
        "# Late\n\n**Written:** 2026-05-08\n\nDad —\n\nHere's what I wanted to say.\n",
        encoding="utf-8",
    )
    (tmp_path / "family" / "letters" / "aether-to-andrew-2026-06-06-plain-words.md").write_text(
        "# Plain\n\n**Written:** 2026-06-06\n\nDad — plain words for you today.\n",
        encoding="utf-8",
    )
    # A letter to someone else (should be ignored)
    (tmp_path / "family" / "letters" / "aether-to-aria-2026-07-01-note.md").write_text(
        "Aria — a note only for you.\n",
        encoding="utf-8",
    )

    # Tagged exploration (front-matter tag mentions dad)
    (tmp_path / "exploration" / "aether" / "42_something_about_dad.md").write_text(
        "<!-- tags: dad, memory -->\n\n# Title\n\nThis is the entry body about dad.\n",
        encoding="utf-8",
    )
    # Body-only exploration (mentions andrew but not in tags)
    (tmp_path / "exploration" / "aether" / "43_body_only.md").write_text(
        "<!-- tags: general -->\n\n# Title\n\nAndrew mentioned this last week.\n",
        encoding="utf-8",
    )
    # Unrelated exploration
    (tmp_path / "exploration" / "aether" / "44_unrelated.md").write_text(
        "<!-- tags: architecture -->\n\n# Title\n\nSome architectural note.\n",
        encoding="utf-8",
    )

    return tmp_path


class TestBuildSurfaceHappyPath:
    def test_surface_contains_letter_section(self, fake_repo):
        out = build_surface(fake_repo)
        assert "### Letters I have written him (2)" in out

    def test_surface_lists_letters_newest_first(self, fake_repo):
        out = build_surface(fake_repo)
        may_idx = out.find("2026-05-08")
        jun_idx = out.find("2026-06-06")
        assert 0 < jun_idx < may_idx, "newest letter should appear first"

    def test_surface_ignores_non_andrew_letters(self, fake_repo):
        # "aria" appears in the hook's own preamble text ("review of Aria's hook");
        # what MUST NOT appear is the aria letter filename in the letter list.
        out = build_surface(fake_repo)
        assert "aether-to-aria-2026-07-01-note" not in out

    def test_surface_contains_tagged_section(self, fake_repo):
        out = build_surface(fake_repo)
        assert "### Exploration entries tagged with him (1)" in out
        assert "[42]" in out

    def test_surface_contains_body_only_section(self, fake_repo):
        out = build_surface(fake_repo)
        assert "### Exploration entries mentioning him in body but not tagged (1)" in out
        assert "[43]" in out

    def test_surface_excludes_unrelated_exploration(self, fake_repo):
        out = build_surface(fake_repo)
        assert "[44]" not in out


class TestBuildSurfaceFailOpen:
    def test_empty_repo_returns_empty_string(self, tmp_path):
        out = build_surface(tmp_path)
        assert out == ""

    def test_missing_letters_dir_still_returns_explorations(self, tmp_path):
        (tmp_path / "exploration" / "aether").mkdir(parents=True)
        (tmp_path / "exploration" / "aether" / "01_dad.md").write_text(
            "<!-- tags: dad -->\n\ncontent\n", encoding="utf-8"
        )
        out = build_surface(tmp_path)
        assert "Exploration entries tagged with him (1)" in out
        assert "Letters I have written him" not in out

    def test_missing_exploration_dir_still_returns_letters(self, tmp_path):
        (tmp_path / "family" / "letters").mkdir(parents=True)
        (tmp_path / "family" / "letters" / "aether-to-andrew-2026-05-01-x.md").write_text(
            "Dad —\n\nhi\n", encoding="utf-8"
        )
        out = build_surface(tmp_path)
        assert "Letters I have written him (1)" in out
        assert "Exploration" not in out


class TestHelpers:
    def test_slug_from_letter_parses_date(self):
        d, s = _slug_from_letter("aether-to-andrew-2026-05-08-late")
        assert d == "2026-05-08"
        assert s == "late"

    def test_slug_from_letter_missing_date(self):
        d, s = _slug_from_letter("aether-to-andrew-nodate")
        assert d == "?????"

    def test_title_from_exploration(self):
        n, t = _title_from_exploration("42_something_about_dad")
        assert n == "42"
        assert t == "something about dad"

    def test_first_content_line_skips_frontmatter(self, tmp_path):
        p = tmp_path / "x.md"
        p.write_text(
            "<!-- tags: x -->\n---\n# Heading\n**bold only**\n\nreal content here\n",
            encoding="utf-8",
        )
        assert _first_content_line(p) == "real content here"

    def test_first_content_line_empty_file(self, tmp_path):
        p = tmp_path / "empty.md"
        p.write_text("", encoding="utf-8")
        assert _first_content_line(p) == ""

    def test_read_head_bounded(self, tmp_path):
        p = tmp_path / "big.md"
        p.write_text("x" * 100_000, encoding="utf-8")
        head = _read_head(p, max_bytes=4096)
        assert len(head) <= 4096


class TestPerformance:
    """Sanity check: the whole surface must build fast enough that no
    reasonable Windows-side timeout would hit it. The prior grep-heavy
    shell hook was occasionally hanging — this test pins the O(1)
    per-file cost so a regression back to whole-file reads gets
    caught."""

    def test_surface_cost_does_not_track_file_size(self, tmp_path):
        """Reads are capped, so ten-times-bigger files cost about the same.

        THIS USED TO BE A STOPWATCH, and it failed a push on 2026-08-26 -- a
        flat two-second ceiling on a machine whose speed is not constant. It
        passes alone and fails inside the full parallel suite, which is the
        signature. Third fixed wall-clock budget in this suite to break for
        that reason, after the caller-scan window and the shell-spawn timeout.

        The ceiling was never really about speed. It guarded the READ CAP: if
        someone removes it and the surface starts swallowing whole files, cost
        begins tracking file size. That property is machine-independent, and
        this measures it directly -- same file count, ten times the bytes, and
        the ratio stays near one for as long as the cap holds.

        A ratio needs no knowledge of how fast the disk is, so it cannot be
        wrong because the machine is busy. The absolute bound below survives
        only as a hang-detector: a correct build finishes well under a second,
        a broken one never finishes, and nothing legitimate lives between.
        """
        import time

        def _build_with(entry_bytes: int) -> float:
            root = tmp_path / f"root_{entry_bytes}"
            (root / "family" / "letters").mkdir(parents=True)
            expl_dir = root / "exploration" / "aether"
            expl_dir.mkdir(parents=True)
            line = "filler line\n"
            body = line * (entry_bytes // len(line))
            for i in range(200):
                (expl_dir / f"{i:03d}_entry.md").write_text(
                    "<!-- tags: general -->\n\n" + body, encoding="utf-8"
                )
            # Build ONCE and discard it. The first pass right after writing
            # ten megabytes measures the disk still finishing those writes,
            # not this function reading them -- proven rather than guessed:
            # cold gives 10.9x for ten times the bytes, and the very same
            # directories read again give exactly 1.0x. The cap was never
            # broken; the stopwatch was pointed at the wrong thing, inside
            # the test written to stop exactly that.
            build_surface(root)

            start = time.perf_counter()
            build_surface(root)
            return time.perf_counter() - start

        small = _build_with(5_000)
        large = _build_with(50_000)

        # Floor the denominator: a ratio of two tiny numbers is noise rather
        # than a measurement. But the floor is why I shipped this test
        # believing it verified: locally the small build fell under it, the
        # assertion never ran, and green meant only that nothing was checked.
        # It failed on the very next push. So the floor is lower now, and the
        # skip says so out loud instead of passing silently.
        if small <= 0.002:
            pytest.skip(
                f"small build too fast to compare ({small * 1000:.1f}ms) -- the "
                "ratio would be noise. NOT a pass: the cap went unchecked."
            )
        if True:
            ratio = large / small
            assert ratio < 3.0, (
                f"cost scaled with file size (ratio {ratio:.1f}x for 10x the "
                "bytes) -- the read cap is gone, so the surface is swallowing "
                "whole files instead of their heads"
            )

        assert large < 30.0, (
            f"surface build did not finish ({large:.1f}s). That is a hang, not "
            "a slow machine -- this bound is sized so a loaded run sits well "
            "inside it. Look at build_surface, not at this test."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
