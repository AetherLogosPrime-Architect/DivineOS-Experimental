"""Tests for scripts/check_failure_shares_empty.py.

The scanner exists because of Aletheia's 2026-08-29 reading of the anchor
bug: the encoding defect had one manifestation and is gone, but the guard
that enumerates error families and misses one has as many manifestations as
there are error types nobody thought of, and every one produces a well-formed
empty answer at the top.

The load-bearing test is `test_it_finds_the_shape_that_produced_it` -- the
pre-fix patch-id function, reproduced structurally. If that goes green while
the scanner is broken, the scanner is decoration.

The negative controls matter more than their count. A scanner that flags
everything finds the bug too, and is worthless; each negative names a shape
that is NOT the defect and asserts silence on it.
"""

import sys
import textwrap
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_failure_shares_empty as scanner  # noqa: E402


def scan(source: str, include_broad: bool = False):
    return scanner.scan_source(textwrap.dedent(source).encode("utf-8"), "probe.py", include_broad)


class TestItFindsTheDefect:
    def test_it_finds_the_shape_that_produced_it(self):
        """Two families named, the third missed.

        A UnicodeDecodeError is a ValueError, absent from the guard's list, so
        it escaped to a broad handler upstream and the function returned None.
        None here also meant "this branch has no diff" -- which is why an
        anchor that could not be computed looked exactly like a branch with
        nothing to compare, on two machines, for two days.
        """
        found = scan(
            """
            def compute_branch_patch_id(base, ref):
                try:
                    diff = run(["git", "diff", base, ref], text=True)
                    if not diff.stdout.strip():
                        return None
                    pid = run(["git", "patch-id"], input=diff.stdout, text=True)
                except (OSError, SubprocessError):
                    return None
                return pid.stdout.split()[0]
            """
        )
        assert len(found) == 1
        assert found[0].function == "compute_branch_patch_id"
        assert found[0].value == "None"

    def test_the_report_names_both_places(self):
        """A hit the reader cannot go and look at is a count, not a finding."""
        (hit,) = scan(
            """
            def f(x):
                try:
                    if not x:
                        return None
                    return compute(x)
                except KeyError:
                    return None
            """
        )
        assert hit.line != hit.handler_line
        assert hit.line > 0 and hit.handler_line > 0

    @pytest.mark.parametrize("empty", ["None", "[]", "{}", "''", "0", "False", "()"])
    def test_every_falsy_kind_counts_not_only_none(self, empty):
        """An empty list reads as "no results" exactly as None reads as "nothing"."""
        found = scan(
            f"""
            def f(x):
                try:
                    if not x:
                        return {empty}
                    return real_work(x)
                except KeyError:
                    return {empty}
            """
        )
        assert len(found) == 1


class TestShapesThatAreNotTheDefect:
    def test_a_procedure_with_no_real_answer_is_not_flagged(self):
        """No value to be confused WITH means no ambiguity to report.

        The early `return None` in a void function is an exit, not an answer.
        Pairing it with a handler's `return None` was the scanner committing
        the wrong-subject fault against itself, and it is what took the corpus
        scan from a finding to a census.
        """
        assert (
            scan(
                """
                def enforce(state):
                    if state.ok:
                        return None
                    try:
                        emit(state)
                    except KeyError:
                        return None
                """
            )
            == []
        )

    def test_a_broad_handler_is_not_flagged_by_default(self):
        """`except Exception` cannot MISS a family; different risk, different fix."""
        assert (
            scan(
                """
                def f(x):
                    try:
                        if not x:
                            return None
                        return real_work(x)
                    except Exception:
                        return None
                """
            )
            == []
        )

    def test_a_broad_name_inside_a_tuple_is_still_broad(self):
        """`except (KeyError, Exception)` catches everything despite the list."""
        assert (
            scan(
                """
                def f(x):
                    try:
                        if not x:
                            return None
                        return real_work(x)
                    except (KeyError, Exception):
                        return None
                """
            )
            == []
        )

    def test_a_bare_except_belongs_to_the_other_scanner(self):
        """check_silent_swallow.py owns that shape. One hit each, no overlap."""
        assert (
            scan(
                """
                def f(x):
                    try:
                        if not x:
                            return None
                        return real_work(x)
                    except:
                        return None
                """
            )
            == []
        )

    def test_a_handler_that_raises_is_not_flagged(self):
        """Re-raising is the honest form and must never be reported as the defect."""
        assert (
            scan(
                """
                def f(x):
                    try:
                        if not x:
                            return None
                        return real_work(x)
                    except KeyError:
                        raise
                """
            )
            == []
        )

    def test_differing_empties_do_not_pair(self):
        """Returning [] on failure and None on empty IS the distinction wanted."""
        assert (
            scan(
                """
                def f(x):
                    try:
                        if not x:
                            return None
                        return real_work(x)
                    except KeyError:
                        return []
                """
            )
            == []
        )

    def test_include_broad_widens_the_scope_when_asked(self):
        """The narrow default must be a choice the caller can see and reverse."""
        source = """
            def f(x):
                try:
                    if not x:
                        return None
                    return real_work(x)
                except Exception:
                    return None
            """
        assert scan(source) == []
        assert len(scan(source, include_broad=True)) == 1


class TestTheScannerObeysItsOwnFinding:
    """Every one of these is the subject of the file, turned on the tool."""

    def test_a_file_it_cannot_parse_is_not_a_file_it_cleared(self):
        """scan_source raises rather than returning [] on unparseable input.

        So a failure to read can never arrive at the caller wearing the same
        clothes as a clean result -- which is the entire finding.
        """
        with pytest.raises(SyntaxError):
            scanner.scan_source(b"def f(:\n    pass\n", "broken.py")

    def test_git_outage_returns_none_rather_than_no_files(self, tmp_path):
        """An empty list would mean "nothing changed". These must differ."""
        assert scanner.changed_python_files(tmp_path, "no/such/ref/exists") is None

    def test_the_exit_code_separates_outage_from_clean(self, capsys):
        """Exit 2 for could-not-look; exit 0 is reserved for looked-and-clean."""
        code = scanner.main(["--changed-since", "no/such/ref/exists"])
        assert code == 2
        assert "COULD NOT LIST" in capsys.readouterr().out

    def test_the_header_always_names_which_scope_produced_the_count(self, tmp_path, capsys):
        """A count whose scope is unstated is the wrong-subject fault waiting."""
        probe = tmp_path / "p.py"
        probe.write_text("def f():\n    return 1\n", encoding="utf-8")

        scanner.main([str(probe)])
        assert "ENUMERATE error families" in capsys.readouterr().out

        scanner.main([str(probe), "--include-broad"])
        assert "all handlers" in capsys.readouterr().out
