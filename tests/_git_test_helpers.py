"""Windows-safe git-init helpers for tests.

`git.exe` on Windows ships through an MSYS2 runtime that occasionally
fails to initialize when many git processes spawn in quick succession
(the kernel returns STATUS_DLL_INIT_FAILED, exit code 3221225794).
The race is well-known and unfixed upstream — msys2-runtime#165,
git-for-windows/git#1176, gitlab-runner#34376 all reached the same
conclusion: wrap the call and retry.

This module provides two surfaces:

- `safe_git_init(repo, *args, retries=3)` retries `git init` on the
  specific Windows DLL-init exit codes. Tests that need a one-off
  init in unusual config should use this.

- The session-scoped `git_template_repo` fixture (registered in
  conftest) creates one initialized repo per pytest session and
  hands tests a copied `.git` directory instead of running another
  init. Eliminates ~95% of git spawns from the test run.

The retry call site is the load-bearing fix; the template is the
amortization win.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

# Windows STATUS_DLL_INIT_FAILED. The subprocess exit code surfaces
# either as the unsigned 32-bit value (3221225794) or the signed
# representation (-1073741502) depending on the caller; handle both.
_DLL_INIT_FAILED_CODES = {3221225794, -1073741502}


def safe_git_init(repo: Path, *args: str, retries: int = 3, sleep_s: float = 0.1) -> None:
    """Run `git init <args...>` in `repo`, retrying on Windows DLL-init race.

    Raises subprocess.CalledProcessError on any non-DLL-init failure or
    after `retries` consecutive DLL-init failures. The default 3 retries
    with 100ms backoff covers the race in practice — gitlab-runner shipped
    the same shape and resolved their intermittent-init reports.
    """
    repo = Path(repo)
    repo.mkdir(parents=True, exist_ok=True)
    last_err: subprocess.CalledProcessError | None = None
    for attempt in range(retries + 1):
        try:
            subprocess.run(
                ["git", "init", *args],
                cwd=repo,
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8",
                errors="replace",
            )
            return
        except subprocess.CalledProcessError as exc:
            if exc.returncode not in _DLL_INIT_FAILED_CODES:
                raise
            last_err = exc
            if attempt < retries:
                time.sleep(sleep_s)
    assert last_err is not None
    raise last_err


def _build_template_repo(target: Path, *, bare: bool = False) -> None:
    """Initialize a fresh repo at `target` using safe_git_init."""
    args = ["--initial-branch=main"]
    if bare:
        args.insert(0, "--bare")
    safe_git_init(target, *args)


def materialize_repo_from_template(template_repo: Path, target: Path) -> Path:
    """Copy the template repo's contents to `target`, returning `target`.

    Faster than `git init` and immune to the DLL-init race because no
    new git subprocess is spawned. The template lives in a session-
    scoped fixture so the cost amortizes across the whole test run.
    """
    target = Path(target)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(template_repo, target)
    return target
