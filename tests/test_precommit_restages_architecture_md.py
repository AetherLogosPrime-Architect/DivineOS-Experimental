"""Regression test for Andrew correction #25 (2026-05-28).

The precommit script auto-fixed architecture-tree drift (by appending
new source files to ``docs/ARCHITECTURE.md`` via
``check_doc_counts.py --fix``) but did NOT include ``docs/ARCHITECTURE.md``
in the post-fix re-stage line. Result: every commit that added a new
source file passed pre-commit locally (the auto-fix ran in the working
tree) but failed CI doc-drift (the fix was never staged into the
commit). Pattern recurred ad infinitum because the recurrence was
upstream of any individual PR's fix.

This test pins ``docs/ARCHITECTURE.md`` into the re-stage line so the
class of failure can't silently return via well-meaning refactor.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PRECOMMIT_PATH = REPO_ROOT / "scripts" / "precommit.sh"


def test_precommit_restages_architecture_md_after_auto_fix() -> None:
    text = PRECOMMIT_PATH.read_text(encoding="utf-8", errors="replace")

    # Find the re-stage line that follows the auto-fix invocation. The
    # check is shape-based: there must be a `git add` call that includes
    # docs/ARCHITECTURE.md SOMEWHERE in the script, AND it must appear
    # AFTER the check_doc_counts.py --fix invocation (so the staged
    # version reflects the post-fix content, not the pre-fix content).
    assert "check_doc_counts.py --fix" in text, (
        "Test premise broken: precommit.sh no longer invokes check_doc_counts.py --fix"
    )

    fix_idx = text.index("check_doc_counts.py --fix")
    rest_of_script = text[fix_idx:]

    assert "docs/ARCHITECTURE.md" in rest_of_script, (
        "precommit.sh must re-stage docs/ARCHITECTURE.md AFTER the auto-fix "
        "runs, or the auto-fix's changes won't make it into the commit and "
        "CI doc-drift will fail every PR that adds a source file. "
        "Andrew correction #25 (2026-05-28)."
    )

    # Stronger check: the re-stage must be on a `git add` line, not just
    # a doc comment mentioning the path.
    lines_after_fix = rest_of_script.splitlines()
    git_add_with_arch = [
        line
        for line in lines_after_fix
        if line.strip().startswith("git add") and "docs/ARCHITECTURE.md" in line
    ]
    assert git_add_with_arch, (
        "docs/ARCHITECTURE.md is mentioned after the auto-fix but not in a "
        "`git add` line. The re-stage must be a real git add, not a comment."
    )
