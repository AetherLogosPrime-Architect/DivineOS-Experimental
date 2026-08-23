"""Tests for scripts/sibling_sweep.py — "where else is this true?"

The tool answers a question nothing in the loop asked: a fix landed here,
does the thing it repudiated survive elsewhere? Its failure modes are
asymmetric, so the tests are too:

  A MISSED SURVIVOR is the failure the tool exists to prevent -- silent, and
  indistinguishable from a clean sweep.
  A FALSE HIT is noise, and noise is not harmless either: a tool whose noise
  looks like its signal trains the reader to skip it. That happened on the
  second real run (11 findings, mostly a refactor describing itself).
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from collections import Counter

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "sibling_sweep", pathlib.Path(__file__).resolve().parents[1] / "scripts" / "sibling_sweep.py"
)
sweep = importlib.util.module_from_spec(_SPEC)
sys.modules["sibling_sweep"] = sweep
assert _SPEC.loader is not None
_SPEC.loader.exec_module(sweep)


def df_from(files: dict[str, str]) -> Counter:
    c: Counter = Counter()
    for text in files.values():
        for ident in set(sweep.IDENT.findall(text)):
            c[ident] += 1
    return c


class TestToQuery:
    """A removed line becomes a regex: local names generalised, shape kept."""

    def test_rare_identifier_is_wildcarded_common_one_is_kept(self):
        # _MY_LOCAL_RE appears once (local); search/command appear widely.
        df = Counter({"_MY_LOCAL_RE": 1, "bool": 40, "search": 30, "command": 50})
        q = sweep.to_query("return bool(_MY_LOCAL_RE.search(command))", df, 100, 2)
        assert q is not None
        assert "_MY_LOCAL_RE" not in q, "a file-local name must be generalised"
        assert "search" in q and "command" in q, "the shared shape must be matched"

    def test_the_query_matches_a_sibling_with_a_different_local_name(self):
        df = Counter({"_A_RE": 1, "_B_RE": 1, "bool": 40, "search": 30, "command": 50})
        q = sweep.to_query("return bool(_A_RE.search(command))", df, 100, 2)
        import re as _re

        assert _re.compile(q).search("return bool(_B_RE.search(command))")

    def test_a_line_of_only_ubiquitous_words_yields_no_query(self):
        """The band rule catches lines whose every word is everywhere.

        NOTE WHAT THIS DOES *NOT* CLAIM. An earlier version of this test
        asserted that `return "".join(out)` yields no query, and it passed --
        on a fixture where all three words were 70-80% ubiquitous. On the
        REAL corpus `out` is 33% and `join` is 41%, both distinctive, so that
        line DOES yield a query and produces 4 hits. The band rule is a cheap
        pre-filter; hit-count is what actually catches genericness. The test
        passed for the wrong reason until the fixture was made honest.
        """
        df = Counter({"return": 80, "join": 75, "out": 78})
        assert sweep.to_query('return "".join(out)', df, 100, 2) is None

    def test_a_distinctive_line_yields_a_query_even_if_generic_looking(self):
        """The real-corpus frequencies for that same line, which DO qualify."""
        df = Counter({"return": 704, "join": 362, "out": 298})
        assert sweep.to_query('return "".join(out)', df, 882, 2) is not None, (
            "this is the honest behaviour: the band rule lets it through, "
            "and the idiom filter is what suppresses it"
        )

    def test_a_line_of_only_local_names_yields_no_query(self):
        df = Counter({"_x": 1, "_y": 1, "_z": 1})
        assert sweep.to_query("_x = _y(_z)", df, 100, 2) is None


class TestMovedIsNotRemoved:
    """A refactor deletes here and adds there. That is not a finding."""

    DIFF = (
        "+++ b/src/a.py\n"
        "-    value = helper(command)\n"
        "-    moved_line = shared(command)\n"
        "+++ b/src/b.py\n"
        "+    moved_line = shared(command)\n"
    )

    def test_a_relocated_line_is_suppressed(self, monkeypatch):
        monkeypatch.setattr(
            sweep.subprocess,
            "run",
            lambda *a, **k: type("R", (), {"stdout": self.DIFF})(),
        )
        removed, moved = sweep.removed_lines("HEAD", staged=False)
        bodies = [b for _, b in removed]
        assert "moved_line = shared(command)" not in bodies
        assert moved == 1, "the suppression must be counted, not silent"

    def test_a_genuinely_deleted_line_survives_the_filter(self, monkeypatch):
        monkeypatch.setattr(
            sweep.subprocess,
            "run",
            lambda *a, **k: type("R", (), {"stdout": self.DIFF})(),
        )
        removed, _ = sweep.removed_lines("HEAD", staged=False)
        assert "value = helper(command)" in [b for _, b in removed]

    def test_comments_and_imports_are_not_queries(self, monkeypatch):
        diff = (
            "+++ b/src/a.py\n"
            "-# this is a comment with (parens)\n"
            "-import os\n"
            "-from x import y\n"
            "-    real = call(command)\n"
        )
        monkeypatch.setattr(
            sweep.subprocess, "run", lambda *a, **k: type("R", (), {"stdout": diff})()
        )
        removed, _ = sweep.removed_lines("HEAD", staged=False)
        assert [b for _, b in removed] == ["real = call(command)"]


class TestRegressionTheCaseThatFoundARealBug:
    """The motivating instance, pinned.

    `is_gh_pr_create` was fixed and `has_draft_flag` was not, in the SAME
    file -- an escape predicate left scanning raw text, so a mentioned
    `--draft` made the gate stand down and guardrail PRs opened ready.
    The removed line had to generalise into a query that finds it.
    """

    def test_the_removed_shape_generalises_to_the_missed_sibling(self):
        """The fixture mirrors the real corpus's frequency SHAPE, on purpose.

        The first version of this test put the same four words in all 40
        files, making every identifier 95%-ubiquitous, and it failed -- not
        because the code was wrong but because no real corpus looks like
        that. Measured here: `search` appears in about 30 of 882 files,
        `command` in about 50. Distinctive, not universal. A fixture that
        gets the frequency shape wrong tests a codebase that does not exist.
        """
        files = {f"filler{i}.py": "return unrelated stuff here" for i in range(80)}
        # distinctive band: shared vocabulary, present in a minority of files
        for i in range(20):
            files[f"gate{i}.py"] = "search command bool"
        # local band: each name appears in exactly one file
        files["local_a.py"] = "_GH_PR_CREATE_RE = 1"
        files["local_b.py"] = "_DRAFT_FLAG_RE = 1"
        df = df_from(files)
        q = sweep.to_query("return bool(_GH_PR_CREATE_RE.search(command))", df, len(files), 2)
        assert q is not None, "a real-shaped corpus must yield a query"
        import re as _re

        assert _re.compile(q).search("return bool(_DRAFT_FLAG_RE.search(command))"), (
            "the query must reach the escape predicate that was left unfixed"
        )


@pytest.mark.parametrize("bad", ["", "   ", "# comment"])
def test_empty_and_comment_lines_are_never_queries(bad):
    assert sweep.to_query(bad, Counter(), 10, 2) is None
