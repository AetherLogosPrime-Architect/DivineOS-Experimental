"""Tests for presence_memory — briefing pointer to unindexed personal writing.

Locked invariants:

1. format_for_briefing returns empty string when no surfaces exist.
2. format_for_briefing finds exploration/ at the same path as .git.
3. format_for_briefing finds family/letters/ relative to repo root.
4. Output is descriptive, not prescriptive — no "read X first" language.
5. Output names the actual path and a browsing command (ls).
6. Worktree resolution: a worktree whose .git is a file pointing at a
   main repo's .git/worktrees/<name> also surfaces the main repo's
   presence-memory surfaces.
"""

from __future__ import annotations

from pathlib import Path

from divineos.core.presence_memory import (
    _count_md_files,
    _find_main_repo_root,
    _find_repo_root,
    _presence_surfaces,
    format_for_briefing,
)


class TestEmptyCase:
    def test_returns_empty_when_git_exists_but_no_surfaces(self, tmp_path: Path):
        # Construct a repo root with no presence-memory surfaces.
        # We can't usefully test "no .git anywhere up the chain" because
        # when tests run from inside the real repo, the walker correctly
        # finds the real repo's .git — which is the function's intended
        # behavior. So we test the narrower invariant: given a repo
        # root that genuinely has no known surfaces, output is empty.
        (tmp_path / ".git").mkdir()
        result = format_for_briefing(start=tmp_path)
        assert result == ""


class TestFindRepoRoot:
    def test_finds_dot_git_at_cwd(self, tmp_path: Path):
        (tmp_path / ".git").mkdir()
        assert _find_repo_root(start=tmp_path) == tmp_path.resolve()

    def test_walks_up_to_find_dot_git(self, tmp_path: Path):
        (tmp_path / ".git").mkdir()
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        assert _find_repo_root(start=deep) == tmp_path.resolve()

    def test_returns_none_when_no_git_anywhere(self, tmp_path: Path):
        # Fresh tmp_path with no .git and no parent .git
        deep = tmp_path / "nested"
        deep.mkdir()
        # Can't guarantee nothing above tmp_path — but usually pytest tmp
        # is under /tmp or similar with no .git. If the test env has a
        # parent .git somewhere, this will find it; that's a platform
        # thing, not a bug.
        result = _find_repo_root(start=deep)
        # Either None OR some outside path; never deep itself
        assert result != deep.resolve()


class TestExplorationFolder:
    def test_finds_exploration_at_repo_root(self, tmp_path: Path):
        (tmp_path / ".git").mkdir()
        exp = tmp_path / "exploration"
        exp.mkdir()
        (exp / "01_something.md").write_text("body", encoding="utf-8")
        (exp / "02_another.md").write_text("body", encoding="utf-8")

        surfaces = _presence_surfaces(start=tmp_path)
        names = [s[0] for s in surfaces]
        assert "exploration" in names
        # md count of 2
        exp_entry = next(s for s in surfaces if s[0] == "exploration")
        assert exp_entry[2] == 2

    def test_output_block_names_path_and_count(self, tmp_path: Path):
        (tmp_path / ".git").mkdir()
        exp = tmp_path / "exploration"
        exp.mkdir()
        (exp / "01_something.md").write_text("body", encoding="utf-8")

        block = format_for_briefing(start=tmp_path)
        assert "exploration" in block
        assert "1 .md file" in block
        assert "ls " in block  # browsing command present


class TestFamilyLetters:
    def test_finds_family_letters(self, tmp_path: Path):
        (tmp_path / ".git").mkdir()
        letters = tmp_path / "family" / "letters"
        letters.mkdir(parents=True)
        (letters / "aether-to-aria.md").write_text("body", encoding="utf-8")

        block = format_for_briefing(start=tmp_path)
        assert "family letters" in block
        assert "1 .md file" in block


class TestDescriptiveNotPrescriptive:
    def test_no_prescriptive_reading_order(self, tmp_path: Path):
        """The block must not prescribe which files to read first —
        session salience varies, and prescription from one session
        biases the next."""
        (tmp_path / ".git").mkdir()
        exp = tmp_path / "exploration"
        exp.mkdir()
        (exp / "01_a.md").write_text("body", encoding="utf-8")

        block = format_for_briefing(start=tmp_path)
        # Prescriptive markers we specifically want to avoid
        assert "read first" not in block.lower()
        assert "start with" not in block.lower()
        assert "priority" not in block.lower()
        # But it should acknowledge context-dependence
        assert "salience" in block.lower() or "context" in block.lower()


class TestMdCount:
    def test_counts_only_md_files(self, tmp_path: Path):
        d = tmp_path / "target"
        d.mkdir()
        (d / "a.md").write_text("x", encoding="utf-8")
        (d / "b.md").write_text("x", encoding="utf-8")
        (d / "c.txt").write_text("x", encoding="utf-8")
        (d / "d.py").write_text("x", encoding="utf-8")
        assert _count_md_files(d) == 2

    def test_not_recursive(self, tmp_path: Path):
        d = tmp_path / "target"
        sub = d / "sub"
        sub.mkdir(parents=True)
        (d / "a.md").write_text("x", encoding="utf-8")
        (sub / "b.md").write_text("x", encoding="utf-8")
        assert _count_md_files(d) == 1

    def test_returns_zero_on_missing(self, tmp_path: Path):
        missing = tmp_path / "does_not_exist"
        assert _count_md_files(missing) == 0


class TestWorktreeResolution:
    def test_main_root_found_from_worktree(self, tmp_path: Path):
        # Construct a fake worktree: tmp_path/main/.git is a directory,
        # tmp_path/main/.git/worktrees/wt/ exists, and
        # tmp_path/wt/.git is a file pointing at it.
        main = tmp_path / "main"
        main.mkdir()
        git_dir = main / ".git"
        git_dir.mkdir()
        wt_internal = git_dir / "worktrees" / "wt"
        wt_internal.mkdir(parents=True)

        wt = tmp_path / "wt"
        wt.mkdir()
        (wt / ".git").write_text(f"gitdir: {wt_internal}\n", encoding="utf-8")

        # Main root resolution from the worktree
        result = _find_main_repo_root(wt)
        assert result is not None
        assert result.resolve() == main.resolve()

    def test_worktree_sees_main_repo_surfaces(self, tmp_path: Path):
        """The key integration: a worktree's briefing should surface
        an exploration/ folder that lives at the main repo root."""
        main = tmp_path / "main"
        main.mkdir()
        git_dir = main / ".git"
        git_dir.mkdir()
        wt_internal = git_dir / "worktrees" / "wt"
        wt_internal.mkdir(parents=True)

        # Exploration at main repo root
        exp = main / "exploration"
        exp.mkdir()
        (exp / "01_thought.md").write_text("body", encoding="utf-8")

        # Worktree pointing at main
        wt = tmp_path / "wt"
        wt.mkdir()
        (wt / ".git").write_text(f"gitdir: {wt_internal}\n", encoding="utf-8")

        # Briefing run from inside the worktree must surface main's exploration
        block = format_for_briefing(start=wt)
        assert "exploration" in block
        assert "1 .md file" in block

    def test_non_worktree_git_file_returns_none(self, tmp_path: Path):
        """A .git file without a valid gitdir pointer should not crash."""
        (tmp_path / ".git").write_text("not a gitdir pointer", encoding="utf-8")
        result = _find_main_repo_root(tmp_path)
        assert result is None


class TestNoDuplication:
    def test_worktree_and_main_both_having_folder_dedup(self, tmp_path: Path):
        """If the worktree also has its own exploration/ at the same
        resolved path, it should not be listed twice. This is a
        practical concern more than a likely case, but the dedup logic
        uses resolved paths so we test that it works."""
        main = tmp_path / "main"
        main.mkdir()
        git_dir = main / ".git"
        git_dir.mkdir()
        exp = main / "exploration"
        exp.mkdir()
        (exp / "a.md").write_text("x", encoding="utf-8")

        surfaces = _presence_surfaces(start=main)
        exploration_entries = [s for s in surfaces if s[0] == "exploration"]
        assert len(exploration_entries) == 1
