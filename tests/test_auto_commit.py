"""Tests for divineos.core.auto_commit.

The weld Andrew asked for 2026-07-05: commit fires automatically at
extract/sleep boundaries so today's forgotten-commit shape cannot
recur silently.

Uses real git subprocess against a tmp_path repo — no mocking of git
itself. Only the external-channels DEFAULT is overridden so tests do
not touch the real ~/.divineos-shared folder.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.auto_commit import (
    AutoCommitResult,
    auto_commit_substrate,
    checkpoint_report,
    find_repo_root,
)
from divineos.core.uncommitted_work_check import ExternalChannel


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(root: Path) -> None:
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "core.autocrlf", "false")
    _git(root, "config", "commit.gpgsign", "false")
    # Ignore pytest cache / __pycache__ so nested-under-outer-repo runs
    # do not report the harness's own scratch files as dirty.
    # Ignore both harness artifacts AND divineos autouse-fixture artifacts
    # (a session conftest drops divineos_home/ and test_ledger.db into
    # tmp_path). Without this, git sees them as dirty and auto_commit
    # commits them, breaking the "clean tree" contract.
    (root / ".gitignore").write_text(
        "__pycache__/\n.pytest_cache/\n*.pyc\ndivineos_home/\ntest_ledger.db\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text("seed\n", encoding="utf-8")
    _git(root, "add", ".gitignore", "README.md")
    _git(root, "commit", "-q", "-m", "seed")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _init_repo(tmp_path)
    return tmp_path


class TestAutoCommitBasics:
    def test_clean_tree_no_op(self, repo: Path):
        result = auto_commit_substrate(repo, reason="pre-extract", channels=())
        assert result.committed is False
        assert "clean" in result.reason.lower()

    def test_dirty_tree_commits(self, repo: Path):
        (repo / "new_file.md").write_text("body\n", encoding="utf-8")
        result = auto_commit_substrate(repo, reason="pre-extract", channels=())
        assert result.committed is True
        assert result.dirty_lines >= 1

        log = _git(repo, "log", "-1", "--pretty=%s").stdout.strip()
        assert "auto-commit (pre-extract)" in log

    def test_modified_tracked_file_commits(self, repo: Path):
        (repo / "README.md").write_text("mutated\n", encoding="utf-8")
        result = auto_commit_substrate(repo, reason="post-extract", channels=())
        assert result.committed is True

        log = _git(repo, "log", "-1", "--pretty=%s").stdout.strip()
        assert "post-extract" in log

    def test_reason_appears_in_commit_subject(self, repo: Path):
        (repo / "a.md").write_text("x\n", encoding="utf-8")
        auto_commit_substrate(repo, reason="pre-sleep", channels=())
        log = _git(repo, "log", "-1", "--pretty=%s").stdout.strip()
        assert "pre-sleep" in log

    def test_not_a_git_repo_returns_uncommitted(self, tmp_path: Path):
        # A directory without .git — not a repo at all.
        result = auto_commit_substrate(tmp_path, reason="pre-extract", channels=())
        assert result.committed is False
        assert "not a git repo" in result.reason


class TestExternalChannelSync:
    def test_new_external_file_synced_and_committed(self, repo: Path, tmp_path: Path, monkeypatch):
        """The import, on a branch DECLARED for substrate.

        This test previously pinned "the sync always runs" and that was the
        defect rather than the contract. 2026-09-11: the sync ran on every
        branch, so every letter written came back into the repo and was
        committed onto whatever code branch was checked out. Three sweeps in
        two days -- 171, 177, 190 -- and all 177 of the one I counted were
        letters. The import now happens only where substrate belongs, and the
        declaration is the environment flag the push gate already honours.
        """
        monkeypatch.setenv("DIVINEOS_SUBSTRATE_BRANCH", "1")
        source = tmp_path / "letters_source"
        source.mkdir()
        (source / "aria-to-aether-2026-07-05-test.md").write_text("letter body\n", encoding="utf-8")
        channels = (
            ExternalChannel(
                name="test-letters",
                source=source,
                repo_mirror=Path("family/letters"),
                pattern="*.md",
            ),
        )

        result = auto_commit_substrate(repo, reason="pre-sleep", channels=channels)
        # ASSERTS THE IMPORT, NOT THE COMBINED FLAG, after the merge of
        # 2026-09-22. This read `result.committed is True`, and that field
        # changed meaning on the branch merged here: it used to report the
        # optimistic half of a two-half operation and now reports both
        # honestly, so a run whose substrate half was refused no longer claims
        # success. This fixture declares no substrate branch, so the refusal is
        # correct and the old assertion was reading a boolean that had stopped
        # meaning what it said.
        #
        # The subject of this test is the IMPORT -- whether the letter reaches
        # the mirror on a branch declared for substrate. That is what the two
        # assertions below measure, and they are unchanged in substance.
        assert result.files_synced == 1
        # File landed in the mirror
        assert (repo / "family/letters/aria-to-aether-2026-07-05-test.md").is_file()

    def test_no_import_on_a_branch_not_declared_for_substrate(
        self, repo: Path, tmp_path: Path, monkeypatch
    ):
        """THE LOOP THIS CLOSES, and the red half of the pair above.

        A letter is written, the mirror copies it to the shared room, the
        checkpoint copies it BACK, and it lands on a code branch the push gate
        then refuses. It grows rather than staying small because the repo
        mirror is per-branch, so on any unvisited branch every letter ever
        written looks new.

        Nothing is lost by skipping: the file is still in the source, which is
        where it came from and where it is read.
        """
        monkeypatch.delenv("DIVINEOS_SUBSTRATE_BRANCH", raising=False)
        source = tmp_path / "letters_source"
        source.mkdir()
        (source / "aria-to-aether-2026-07-05-test.md").write_text("letter body\n", encoding="utf-8")
        channels = (
            ExternalChannel(
                name="test-letters",
                source=source,
                repo_mirror=Path("family/letters"),
                pattern="*.md",
            ),
        )

        result = auto_commit_substrate(repo, reason="pre-sleep", channels=channels)

        assert result.files_synced == 0, "the import ran on a branch not declared for substrate"
        assert not (repo / "family/letters/aria-to-aether-2026-07-05-test.md").exists(), (
            "the letter was copied onto a code branch again"
        )
        assert (source / "aria-to-aether-2026-07-05-test.md").is_file(), (
            "skipping the import must never touch the source -- the shared room is "
            "where the letter actually lives"
        )

    # A TEST THAT THIS MERGE SUPERSEDED, named rather than quietly dropped.
    #
    # The branch merged here carried
    # `test_new_external_file_is_synced_but_refused_when_no_branch_is_declared`,
    # which asserted that on an undeclared branch the letter IS copied in and
    # the substrate commit is then refused. That was true of the behaviour it
    # was written against. It is not true of the behaviour on this side: the
    # import no longer runs at all without the declaration, so there is no
    # synced-then-refused state left for it to describe, and the test directly
    # above covers the same scenario under the rule that now holds.
    #
    # What the branch contributed is NOT lost -- it is the honest reporting of
    # the two halves, which lives in TestWhatTheOperatorIsActuallyTold at the
    # bottom of this file and is the reason the assertion above reads
    # files_synced rather than the combined flag.

    def test_already_synced_file_not_recopied(self, repo: Path, tmp_path: Path):
        source = tmp_path / "letters_source"
        source.mkdir()
        letter_name = "aria-to-aether-2026-07-05-already-synced.md"
        (source / letter_name).write_text("orig\n", encoding="utf-8")

        # Put a copy already in mirror + commit it
        mirror = repo / "family/letters"
        mirror.mkdir(parents=True)
        (mirror / letter_name).write_text("orig\n", encoding="utf-8")
        _git(repo, "add", str(mirror / letter_name))
        _git(repo, "commit", "-q", "-m", "existing letter")

        channels = (
            ExternalChannel(
                name="test-letters",
                source=source,
                repo_mirror=Path("family/letters"),
                pattern="*.md",
            ),
        )

        result = auto_commit_substrate(repo, reason="pre-extract", channels=channels)
        # The load-bearing assertion for this test: the already-synced file
        # is NOT re-copied. Whether committed=True depends on unrelated
        # tmp_path noise from autouse fixtures; that's not this test's
        # contract.
        assert result.files_synced == 0

    def test_missing_source_dir_is_silent(self, repo: Path, tmp_path: Path):
        channels = (
            ExternalChannel(
                name="ghost",
                source=tmp_path / "does_not_exist",
                repo_mirror=Path("family/letters"),
                pattern="*.md",
            ),
        )
        result = auto_commit_substrate(repo, reason="pre-sleep", channels=channels)
        assert result.committed is False
        assert result.files_synced == 0


class TestFindRepoRoot:
    def test_find_repo_root_at_root(self, repo: Path):
        assert find_repo_root(repo) == repo

    def test_find_repo_root_from_subdir(self, repo: Path):
        sub = repo / "src" / "deep"
        sub.mkdir(parents=True)
        assert find_repo_root(sub) == repo

    def test_find_repo_root_walks_to_nearest(self, tmp_path: Path):
        # When multiple .git dirs nest, walk finds the nearest ancestor.
        inner = tmp_path / "inner"
        inner.mkdir()
        _init_repo(inner)
        deep = inner / "a" / "b"
        deep.mkdir(parents=True)
        assert find_repo_root(deep) == inner


class TestIdempotency:
    def test_second_call_after_success_is_noop(self, repo: Path):
        (repo / "one.md").write_text("x\n", encoding="utf-8")
        first = auto_commit_substrate(repo, reason="pre-extract", channels=())
        assert first.committed is True

        second = auto_commit_substrate(repo, reason="pre-extract", channels=())
        assert second.committed is False


class TestResultShape:
    def test_default_result_shape(self):
        r = AutoCommitResult(committed=False, reason="clean")
        assert r.files_synced == 0
        assert r.dirty_lines == 0


class TestMidOpDetection:
    """Aria 2026-07-10 fix: auto-commit must skip cleanly when the repo is
    mid-op (rebase, merge, cherry-pick, revert). Committing here would fail
    the git-commit call and trap extract at SystemExit(1) in
    event_commands.py, which is what killed the pre-compaction weave.
    """

    def _dirty(self, root: Path) -> None:
        """Create an uncommitted change so auto-commit would try to commit."""
        (root / "dirty.md").write_text("uncommitted change\n", encoding="utf-8")

    def test_mid_rebase_skip(self, repo: Path):
        # Simulate mid-rebase by creating the rebase-merge directory git uses.
        (repo / ".git" / "rebase-merge").mkdir()
        self._dirty(repo)
        result = auto_commit_substrate(repo, reason="pre-extract", channels=())
        assert result.committed is False
        assert "rebase-merge" in result.reason
        assert "resolve manually" in result.reason

    def test_mid_merge_skip(self, repo: Path):
        # Simulate mid-merge with unresolved conflicts.
        (repo / ".git" / "MERGE_HEAD").write_text(
            "0000000000000000000000000000000000000000\n", encoding="utf-8"
        )
        self._dirty(repo)
        result = auto_commit_substrate(repo, reason="pre-extract", channels=())
        assert result.committed is False
        assert "MERGE_HEAD" in result.reason

    def test_mid_cherry_pick_skip(self, repo: Path):
        (repo / ".git" / "CHERRY_PICK_HEAD").write_text(
            "0000000000000000000000000000000000000000\n", encoding="utf-8"
        )
        self._dirty(repo)
        result = auto_commit_substrate(repo, reason="pre-extract", channels=())
        assert result.committed is False
        assert "CHERRY_PICK_HEAD" in result.reason

    def test_clean_repo_still_commits(self, repo: Path):
        # Sanity: with no mid-op markers, auto-commit proceeds normally.
        self._dirty(repo)
        result = auto_commit_substrate(repo, reason="pre-extract", channels=())
        assert result.committed is True


class TestStagedIndexDetection:
    """Aletheia audit 2026-07-11 finding #1 — CLEAREST FIX.

    Checkpoint hook is for ABANDONED dirty state; grabbing actively-in-flight
    staged work is a category error. When the occupant has staged files with
    ``git add``, they are composing an authored commit — auto-commit must
    defer.

    Same category as _detect_mid_op skip cases: the tree is in a transient
    state the occupant is actively resolving. Not an error; not a warning;
    just wait.
    """

    def _stage_file(self, root: Path, name: str = "authored.md") -> None:
        """Create + git-add a file so the index has staged changes."""
        (root / name).write_text("occupant's authored content\n", encoding="utf-8")
        _git(root, "add", name)

    def test_staged_index_defers_auto_commit(self, repo: Path):
        """The core Aletheia scenario: staged index → skip, don't scoop."""
        self._stage_file(repo)
        result = auto_commit_substrate(repo, reason="pre-extract", channels=())
        assert result.committed is False
        assert "staged index" in result.reason
        assert "mid-commit" in result.reason

    def test_staged_index_preserves_authored_content(self, repo: Path):
        """After the skip, the staged file must still be staged — not committed
        into the auto-checkpoint. This is the anti-regression assertion for the
        specific harm the fix addresses (authored work getting eaten)."""
        self._stage_file(repo, "specific_file.md")
        result = auto_commit_substrate(repo, reason="pre-extract", channels=())
        assert result.committed is False
        # File must still be staged and not committed to any auto-checkpoint
        staged = _git(repo, "diff", "--cached", "--name-only").stdout.strip()
        assert "specific_file.md" in staged
        # No new commits landed since repo init
        log = _git(repo, "log", "--oneline").stdout.strip().splitlines()
        assert len(log) == 1, f"expected only initial commit, got: {log}"

    def test_staged_plus_unstaged_still_defers(self, repo: Path):
        """When BOTH staged and unstaged changes exist, skip still fires —
        the staged part signals mid-commit even if there's also loose dirt."""
        self._stage_file(repo, "staged.md")
        (repo / "unstaged.md").write_text("loose\n", encoding="utf-8")
        result = auto_commit_substrate(repo, reason="pre-extract", channels=())
        assert result.committed is False
        assert "staged index" in result.reason

    def test_unstaged_only_commits_normally(self, repo: Path):
        """Regression sanity: when index is clean but working tree is dirty
        (loose untracked files, unstaged mods), auto-commit still fires. The
        fix must NOT over-suppress — that's the whole abandoned-dirty case
        the checkpoint exists to catch."""
        (repo / "loose.md").write_text("abandoned dirt\n", encoding="utf-8")
        result = auto_commit_substrate(repo, reason="pre-extract", channels=())
        assert result.committed is True
        assert result.dirty_lines >= 1


class TestTheCheckpointOutgrewItsCommandLine:
    """The checkpoint handed every dirty path to one command line.

    Windows refuses a command line past a fixed length by never starting the
    process at all, so this surfaced as a file-not-found rather than as a git
    error, and the handler — which names the exception git raises when git
    RUNS and refuses — did not cover it. There was no breakage event: the
    substrate grew a file at a time until their sum crossed a number that has
    never moved.

    These pin the PROPERTY rather than a length. A test asserting "survives N
    paths" is the same fixed number the defect was made of, one layer over.
    """

    def test_paths_do_not_travel_as_command_line_arguments(self, monkeypatch):
        """The pathspecs must be absent from argv and present on stdin."""
        from divineos.core import auto_commit as ac

        seen: dict[str, object] = {}

        def _capture(cmd, **kwargs):
            seen["cmd"] = cmd
            seen["input"] = kwargs.get("input")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        monkeypatch.setattr(ac.subprocess, "run", _capture)

        paths = ["notes/alpha.md", "notes/beta.md", "notes/gamma.md"]
        ac._git_paths_on_stdin(Path("."), ["add"], paths)

        argv = seen["cmd"]
        stdin = seen["input"]
        for p in paths:
            assert p not in argv, f"{p} reached the command line"
            assert p in stdin, f"{p} never reached stdin"
        assert "--pathspec-from-file=-" in argv
        assert "--pathspec-file-nul" in argv
        assert chr(0) in stdin, "separator must be NUL — a newline is legal in a filename"

    def test_a_tree_whose_paths_exceed_one_command_line_still_commits(self, repo: Path):
        """End to end, with the symptom manufactured rather than mocked.

        Enough files that their names alone overrun a single command line.
        Before the repair this raised before git ever started; the checkpoint
        reported a failed step and the occupant's open work stayed uncommitted.
        """
        limit = 32767  # the Windows command-line cap this used to cross
        name_len = 90
        total = 0
        made = 0
        while total < limit * 2:
            name = f"long_{made:04d}_" + ("x" * name_len) + ".md"
            (repo / name).write_text("open work\n", encoding="utf-8")
            total += len(name) + 1
            made += 1

        result = auto_commit_substrate(repo, reason="pre-extract", channels=())

        assert result.committed is True
        committed = _git(repo, "show", "--stat", "--name-only", "HEAD").stdout
        assert f"long_{made - 1:04d}_" in committed, "the last file never made it in"


class TestWhatTheOperatorIsActuallyTold:
    """The third instance at one address, and Aether found it in the repair.

    His words: *"The boolean was wrong and tested; you fixed it and tested it.
    The printing was silent and untested; you fixed it and it is still
    untested. If it regresses it will regress the way it failed the first
    time -- quietly."*

    He was right. The earlier repairs were reachable from a test because they
    were values; this one lived in branches inside command handlers, where the
    only way to reach it was to run a whole extract. So the untestability was
    itself the reason the silence lasted.

    The decision is a value now, and these are the tests that could not have
    been written before.
    """

    def test_a_refusal_is_said_out_loud(self):
        told = checkpoint_report(
            AutoCommitResult(
                committed=False,
                work_committed=True,
                substrate_committed=False,
                substrate_refused=True,
                reason="substrate refused — divineos.substrate-branch is not set",
            ),
            "pre-sleep",
        )
        said = " ".join(text for text, _ in told)
        assert "pre-sleep" in said
        assert "substrate refused" in said

    def test_a_refusal_that_still_saved_work_says_both(self):
        # The operator's next question after "the substrate did not land" is
        # "did I lose what I was in the middle of". Answering only the first
        # half is how a true statement reads as a disaster.
        told = checkpoint_report(
            AutoCommitResult(
                committed=False,
                work_committed=True,
                substrate_refused=True,
                reason="substrate refused — no branch",
            ),
            "pre-extract",
        )
        said = " ".join(text for text, _ in told)
        assert "IS saved on HEAD" in said

    def test_silence_belongs_only_to_the_nothing_happened_case(self):
        # THE LOAD-BEARING ONE. "Said nothing because nothing happened" and
        # "said nothing about a refusal" were the same output at the command
        # line, and that was the entire defect. They must never be the same
        # output again.
        nothing_happened = checkpoint_report(
            AutoCommitResult(committed=False, reason="clean tree — nothing to commit"),
            "pre-sleep",
        )
        refused = checkpoint_report(
            AutoCommitResult(
                committed=False, substrate_refused=True, reason="substrate refused — no branch"
            ),
            "pre-sleep",
        )
        assert nothing_happened == []
        assert refused != []

    def test_success_still_reports_what_it_did(self):
        told = checkpoint_report(
            AutoCommitResult(
                committed=True,
                work_committed=True,
                substrate_committed=True,
                reason="committed",
                files_synced=3,
                dirty_lines=7,
            ),
            "post-extract",
        )
        said = " ".join(text for text, _ in told)
        assert "7 dirty lines" in said
        assert "3 external files" in said

    def test_the_boundary_is_named_so_two_checkpoints_are_never_confused(self):
        # A refusal before sleep and a refusal before extract need different
        # responses from the operator, and the message is the only place the
        # difference is visible.
        result = AutoCommitResult(
            committed=False, substrate_refused=True, reason="substrate refused — no branch"
        )
        assert "pre-sleep" in checkpoint_report(result, "pre-sleep")[0][0]
        assert "post-extract" in checkpoint_report(result, "post-extract")[0][0]

    def test_every_line_carries_a_colour_the_caller_can_use(self):
        for result in (
            AutoCommitResult(committed=True, reason="ok"),
            AutoCommitResult(
                committed=False, substrate_refused=True, work_committed=True, reason="refused"
            ),
        ):
            for text, colour in checkpoint_report(result, "pre-sleep"):
                assert text
                assert colour in {"green", "yellow", "red"}
