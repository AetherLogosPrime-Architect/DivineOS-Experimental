"""Stamping a pull request no longer rewrites the branch's commits.

Dad, 2026-10-07: "yes retire it", about the routine that went back through every
commit on a branch touching the reviewed files, stamped each with the review
note, rewrote history and force-pushed. His rule (Hard Rule 8, said five times):
commits never need the trailer, only the merge does. The server-side check
already reads a trailer from the PR body when a commit has none
(scripts/ci_check_guardrail_trailer.sh), so the rewrite changed every commit's
identity for nothing, and twice put old history over newer.

These pin that it is gone and cannot come back through the stamp command.
"""

from __future__ import annotations

import ast
import importlib.util
import inspect

from divineos.cli import stamp_ready_command


def _code_names_and_imports() -> tuple[set[str], set[str], set[str]]:
    tree = ast.parse(inspect.getsource(stamp_ready_command))
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    imports = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module:
            imports.add(n.module)
        elif isinstance(n, ast.Import):
            imports.update(a.name for a in n.names)
    strings = {
        n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
    }
    return names, imports, strings


def test_the_stamp_command_does_not_reach_the_rewrite_routine() -> None:
    names, imports, _strings = _code_names_and_imports()
    assert "divineos.core.push_ready" not in imports
    assert "run_push_ready" not in names


def test_the_stamp_command_never_asks_git_to_rewrite_history() -> None:
    _names, _imports, strings = _code_names_and_imports()
    code_strings = [s for s in strings if len(s) < 60]  # argument lists, not prose
    assert "filter-branch" not in code_strings
    assert "--force-with-lease" not in code_strings


def test_the_rewrite_routine_is_gone() -> None:
    assert importlib.util.find_spec("divineos.core.push_ready") is None


def test_the_command_over_it_is_gone() -> None:
    from divineos.cli import cli

    assert "push-ready" not in cli.commands


def test_stamping_still_writes_the_trailer_into_the_pr_body() -> None:
    # The half that stays: the cover carries the review, and the squash message
    # GitHub builds from the PR body is what the merge check reads.
    source = inspect.getsource(stamp_ready_command)
    assert "External-Review" in source
    assert "pr_head_tree_hash" in source
