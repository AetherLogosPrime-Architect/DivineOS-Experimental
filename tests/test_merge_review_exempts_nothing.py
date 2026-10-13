"""The merge-review gate owes review for any change, letters included.

Andrew 2026-09-29, ruling the exempt-prose list wrong: "version A gives the
optimizer an incentive to take that route as it costs less than getting an
audit, so everything is checked, even the mundane stuff."

Nothing tested _pr_needs_review before this file, so the exemption it carried
could have been wrong in either direction with every test green.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _gate():
    spec = importlib.util.spec_from_file_location(
        "ci_merge_review_check", ROOT / "scripts" / "ci_merge_review_check.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_letters_only_pr_needs_review(monkeypatch) -> None:
    gate = _gate()
    monkeypatch.setattr(gate, "_gh_json", lambda _args: ["family/letters/a.md"])
    assert gate._pr_needs_review("o/r", 1) is True


def test_a_pr_with_no_files_needs_none(monkeypatch) -> None:
    gate = _gate()
    monkeypatch.setattr(gate, "_gh_json", lambda _args: [])
    assert gate._pr_needs_review("o/r", 1) is False


def test_an_unreadable_file_list_still_needs_review(monkeypatch) -> None:
    gate = _gate()
    monkeypatch.setattr(gate, "_gh_json", lambda _args: None)
    assert gate._pr_needs_review("o/r", 1) is True
