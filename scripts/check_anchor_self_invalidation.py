"""Refuse a commit that would make its own anchor false.

Precommit half of the mechanism Aletheia asked for on 2026-08-25:
*"stop letters from auto-committing onto the branch they anchor."*

The auto-commit path is covered separately inside ``auto_commit`` itself,
because that path never reaches precommit -- and the auto-commit is what
actually swept the letter in. Both, because a resolution has now failed twice.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from divineos.core.anchor_self_invalidation import (  # noqa: E402
    current_branch,
    render_refusal,
    self_invalidating_files,
)

ROOT = Path(__file__).resolve().parents[1]


def _staged() -> list[str] | None:
    """Staged paths, or None when git cannot be asked."""
    try:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return [line.strip() for line in (out.stdout or "").splitlines() if line.strip()]


def main() -> int:
    branch = current_branch(ROOT)
    if branch is None:
        print("CANNOT CHECK ANCHOR SELF-INVALIDATION — could not read the branch.")
        print("This is not 'clean'. Nothing was checked.")
        return 1

    staged = _staged()
    if staged is None:
        print("CANNOT CHECK ANCHOR SELF-INVALIDATION — could not list staged files.")
        print("This is not 'clean'. Nothing was checked.")
        return 1

    hits = self_invalidating_files(staged, branch, ROOT)
    if not hits:
        print(f"Anchor check OK (nothing staged anchors '{branch}' to itself)")
        return 0

    print(render_refusal(hits, branch))
    return 1


if __name__ == "__main__":
    sys.exit(main())
