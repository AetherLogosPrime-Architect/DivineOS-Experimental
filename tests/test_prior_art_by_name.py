"""Prior work, found by name, across every branch.

Per prereg-ad19dea9b03d. Built 2026-08-27 from a duplicate: a letter-state
store built on one branch, forgotten, and built again a week later on
another. The existing verify-before-build gate did not catch it because
its predicate is "has this session read something recently", and because
the earlier work was not on the branch being stood on.

The load-bearing tests are the two that pin its HONESTY rather than its
recall: a run that could not search must not look like a clean result,
and a truncated list must say it was truncated.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.prior_art_by_name import ScanResult, scan, tokens_of


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """A repo whose prior art is on a branch that is NOT checked out."""
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-b", "main")
    _git(r, "config", "user.email", "t@example.com")
    _git(r, "config", "user.name", "T")
    (r / "README.md").write_text("seed\n", encoding="utf-8")
    _git(r, "add", "README.md")
    _git(r, "commit", "-m", "seed")

    _git(r, "checkout", "-q", "-b", "old-work")
    (r / "letter_state_store.py").write_text("# the first one\n", encoding="utf-8")
    _git(r, "add", "letter_state_store.py")
    _git(r, "commit", "-m", "the first build")

    # Back to main, where the earlier build is invisible to the working tree.
    _git(r, "checkout", "-q", "main")
    return r


class TestTheDuplicateItWasBuiltFrom:
    def test_finds_work_on_a_branch_not_checked_out(self, repo):
        # The whole point. A search of the working tree returns nothing
        # and CONFIRMS the belief that no prior version exists.
        assert not (repo / "letter_state_store.py").exists()

        result = scan("src/core/letter_state_channel.py", repo)
        assert [h.path for h in result.hits] == ["letter_state_store.py"]
        assert "old-work" in result.hits[0].refs

    def test_one_shared_word_is_not_enough(self, repo):
        # "letter" alone would return the entire correspondence corpus.
        # Two distinctive words is the floor for being ABOUT the same
        # thing rather than merely nearby.
        result = scan("src/core/letter_reader.py", repo)
        assert result.hits == ()


class TestItCannotLookLikeItRan:
    """The first pre-registered falsifier, as an assertion.

    'If it reports nothing found in a way that is indistinguishable from
    not having run, it has failed.'
    """

    def test_a_name_with_no_distinctive_words_says_it_did_not_run(self, repo):
        result = scan("src/core/util.py", repo)
        assert result.query_tokens == ()
        assert "DID NOT RUN" in result.render()
        assert not result.ran

    def test_no_refs_says_it_did_not_run(self, tmp_path):
        # Not a git repo at all: nothing searchable, and that must not
        # render as an all-clear.
        result = scan("anything_at_all_here.py", tmp_path)
        assert not result.ran
        assert "DID NOT RUN" in result.render()

    def test_a_genuine_empty_result_says_what_it_searched(self, repo):
        result = scan("src/core/quantum_teapot_manifold.py", repo)
        assert result.ran
        rendered = result.render()
        assert "nothing similar" in rendered
        assert "NAMES only" in rendered, (
            "an empty result must state its own blindness, or silence "
            "reads as proof no prior art exists"
        )


class TestNoSilentCaps:
    def test_a_truncated_list_says_it_was_truncated(self):
        hits = tuple(
            ScanResult(("x",), 1).hits for _ in range(0)
        )  # placeholder to keep the import honest
        from divineos.core.prior_art_by_name import PriorArt

        many = tuple(
            PriorArt(path=f"f{i}_letter_state.py", refs=("b",), shared_tokens=("letter", "state"))
            for i in range(20)
        )
        rendered = ScanResult(("letter", "state"), 3, many).render()
        assert "and 12 more" in rendered
        assert "display cap" in rendered
        assert hits == ()


class TestTokens:
    def test_plural_and_singular_match(self):
        # The first real run failed its own success criterion on one
        # letter: "letters" and "letter" shared nothing.
        assert "letter" in tokens_of("letters_seen.json")
        assert "letter" in tokens_of("letter_channel_state.py")

    def test_double_s_words_are_not_mangled(self):
        assert "class" in tokens_of("class_registry.py")

    def test_structural_words_are_dropped(self):
        # Matching on these returns most of the repository, which looks
        # thorough and is the same as returning nothing.
        assert tokens_of("src/divineos/core/tests/util.py") == ()


class TestKindMustMatch:
    def test_prose_is_not_prior_art_for_code(self, repo):
        _git(repo, "checkout", "-q", "old-work")
        (repo / "a-letter-about-letter-state-work.md").write_text("x\n", encoding="utf-8")
        _git(repo, "add", "a-letter-about-letter-state-work.md")
        _git(repo, "commit", "-m", "a letter")
        _git(repo, "checkout", "-q", "main")

        paths = [h.path for h in scan("src/core/letter_state_channel.py", repo).hits]
        assert "letter_state_store.py" in paths
        assert "a-letter-about-letter-state-work.md" not in paths, (
            "correspondence about a subject is not an earlier build of it, "
            "and letting it compete drowns the real hit"
        )
