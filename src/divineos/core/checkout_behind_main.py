# AGENT_RUNTIME — not imported by Python. Run by file path from
# .claude/hooks/session-start-behind-main.sh at session start (it is standard
# library only for exactly that reason).
"""How far behind origin/main is the checkout the hooks run from?

Found 2026-10-12: Aria's live checkout was 23 commits behind main and mine was 11,
and neither of us was told. A stale checkout runs stale rules: hers had no silence
rule (so the question hold could never open for Dad being asleep) and still wired a
hook main had retired, so she was held twice overnight and the cause lived in no
branch. A block that no branch can fix is a block nobody goes looking for.

Standard library only, run by file path from the session-start hook. One line when
current, a louder block when far behind, and an honest "could not measure" when git
cannot answer, because a check that stays silent on failure is indistinguishable
from a check that passed.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

LOUD_AT = 5  # commits behind; below this a line is enough
FETCH_SECONDS = 10


def _git(repo: Path, *args: str, timeout: int = 10) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def measure(repo: Path, fetch: bool = True) -> tuple[int, int, bool] | None:
    """(behind, ahead, fetched_fresh) for HEAD against origin/main, or None.

    None means could-not-measure and must never be read as zero.
    """
    fresh = False
    if fetch:
        try:
            fresh = (
                _git(repo, "fetch", "-q", "origin", "main", timeout=FETCH_SECONDS).returncode == 0
            )
        except (subprocess.TimeoutExpired, OSError):
            fresh = False
    try:
        out = _git(repo, "rev-list", "--left-right", "--count", "origin/main...HEAD")
    except (subprocess.TimeoutExpired, OSError):
        return None
    if out.returncode != 0:
        return None
    parts = out.stdout.split()
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        return None
    return int(parts[0]), int(parts[1]), fresh


def report(repo: Path, fetch: bool = True) -> str:
    got = measure(repo, fetch)
    if got is None:
        return (
            "## CHECKOUT vs MAIN: could not measure how far behind origin/main this "
            "checkout is. That is not the same as current; look before trusting its hooks."
        )
    behind, _ahead, fresh = got
    stale_note = "" if fresh else " (the fetch failed, so this is against the last fetch)"
    if behind == 0:
        return f"## CHECKOUT vs MAIN: current with origin/main{stale_note}."
    if behind < LOUD_AT:
        return (
            f"## CHECKOUT vs MAIN: {behind} commit(s) behind origin/main{stale_note}. "
            "Bring main in when convenient: git merge origin/main"
        )
    return (
        f"## CHECKOUT vs MAIN: {behind} commits BEHIND origin/main{stale_note}.\n"
        "The hooks in this checkout are older than the house's. Rules that landed on main\n"
        "since (and hooks it retired) are not the ones running here. A block that no branch\n"
        "can fix may be this. Bring main in now: git merge origin/main"
    )


def main(argv: list[str]) -> int:
    repo = Path(argv[1]) if len(argv) > 1 else Path.cwd()
    print(report(repo))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
