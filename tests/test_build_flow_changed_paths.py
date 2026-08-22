"""The changed-file set station 2 keys off, and the two ways it read empty.

Companion to test_build_flow_lens_counting.py, which covers the COUNTING half
(``_lenses_applied``). This covers the FETCHING half that feeds it. Both were
correct in isolation; the station still reported zero, because the counter was
being handed an empty corpus and had no way to know.

Found 2026-08-17 on PR #412, which changes 443 files. Station 2 reported
``0/2 lenses walked`` while two matching COUNCIL_LENS_APPLIED events sat in the
ledger with the correct fingerprint. Two independent faults, either of which
alone produces the same confident zero:

1. ``gh pr view --json files`` SILENTLY CAPS AT 100 entries. No pagination, no
   warning, a well-formed list that looks complete. #412's truncated set
   stopped inside ``docs/audit_rounds/`` and never reached ``src/``, so the
   module the PR is about was absent from its own changed-file set.

2. ``subprocess.run(text=True)`` decodes with the platform default, cp1252
   here. A gh response carrying any byte outside cp1252 — a patch hunk with an
   em-dash, a curly quote, an accented name — raised UnicodeDecodeError inside
   subprocess's reader THREAD, which does not propagate. stdout came back
   empty, the exit code stayed 0, and ``_gh`` returned "" rather than the None
   its own docstring promises for could-not-reach.

Fault 2 is the wider one: it was never a file-list bug. Every caller of ``_gh``
had the same exposure and the file list is only where it surfaced first.

And the consequence ran past under-crediting walks. Gravity is scored off the
same set, so the LARGEST PRs got empty sets and therefore the LIGHTEST lens
requirements — #412 read gravity 1 before the fix and gravity 3 after. The gate
was under-demanding on exactly the changes that most needed demanding, which is
worse than the miscount that exposed it.

Pure-function tests over captured shapes rather than live ``gh`` calls, so they
run offline and cannot go green merely because the network was quiet.
"""

from __future__ import annotations

import json

from divineos.cli.build_flow_commands import _GH_PR_FILES_CAP, _paginated_filenames


def _page(*names: str) -> str:
    return json.dumps([{"filename": n, "status": "modified"} for n in names])


class TestPaginatedOutputIsNotOneJsonDocument:
    """``gh api --paginate`` concatenates one array per page with nothing
    between them. ``[{...}][{...}]`` is not a valid JSON document, so a plain
    ``json.loads`` raises on every PR past the first page."""

    def test_a_single_page_reads(self) -> None:
        assert _paginated_filenames(_page("a.py", "b.py")) == ("a.py", "b.py")

    def test_concatenated_pages_all_read(self) -> None:
        raw = _page("a.py") + _page("b.py") + _page("c.py")
        assert _paginated_filenames(raw) == ("a.py", "b.py", "c.py")

    def test_whitespace_between_pages_is_tolerated(self) -> None:
        raw = _page("a.py") + "\n" + _page("b.py") + "\n"
        assert _paginated_filenames(raw) == ("a.py", "b.py")

    def test_more_than_one_page_survives(self) -> None:
        """The case that started this: a set larger than a single page."""
        names = [f"f{i}.py" for i in range(250)]
        raw = "".join(_page(*names[i : i + 100]) for i in range(0, 250, 100))
        got = _paginated_filenames(raw)
        assert len(got) == 250
        assert got[0] == "f0.py" and got[-1] == "f249.py"

    def test_empty_output_is_empty_not_an_error(self) -> None:
        assert _paginated_filenames("") == ()

    def test_entries_without_a_filename_yield_an_empty_string(self) -> None:
        """Caller filters these out; the parser does not invent a path."""
        raw = json.dumps([{"filename": "a.py"}, {"status": "removed"}])
        assert _paginated_filenames(raw) == ("a.py", "")


class TestTheCapIsNamedSoTruncationStaysDetectable:
    def test_cap_matches_the_observed_limit(self) -> None:
        """If this constant drifts away from gh's real cap, a truncated set
        stops being distinguishable from a complete one and the confident zero
        comes back."""
        assert _GH_PR_FILES_CAP == 100
