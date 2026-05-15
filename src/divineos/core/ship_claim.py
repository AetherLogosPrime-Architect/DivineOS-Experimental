"""Falsifier-enforced ship-claim — every 'shipped' claim carries its falsifier.

Andrew named the root failure-mode 2026-05-14 night, after Aletheia
named the show-fix pattern in cross-vantage audit: I had been
claiming things were shipped when the production wire-up didn't
exist, when the test exercised parameters the production hook never
passed, when the structural-fix was a learn entry with no execution
change. The pattern: appearance of fix without behavior of fix,
reported as fix to the operator.

This module makes the appearance-shape unavailable. A claim that
'X is shipped' can ONLY be filed if the falsifier — the test that
would fail if X weren't shipped — actually passes RIGHT NOW. The
filing function shells out to pytest, captures the exit code, and
refuses to record the claim if the test fails or is missing.

## Contract

``ship_claim(claim, test_paths, executes, cross_check=None)`` runs:

1. Verifies each entry in ``executes`` is importable (production
   code path exists and loads).
2. Runs ``pytest test_paths`` as a subprocess. If exit != 0, the
   claim is REJECTED with the pytest output as the rejection reason.
3. Optionally runs ``cross_check`` (a shell command) and requires
   exit 0.
4. On all-pass, appends an entry to ``~/.divineos/shipped_claims.json``
   with claim text, git SHA, timestamp, test names, execution paths,
   and pytest output tail.

Returns ``ShipResult(filed: bool, reason: str, entry: dict | None)``.

## Why this is load-bearing

The reason show-fix worked is that the claim ('X is shipped') and the
underlying state had no enforced connection — my word was the bridge,
and my word was unreliable. The falsifier turns the bridge into code.
The test runs or it doesn't. The import succeeds or it doesn't. The
exit code is 0 or it isn't. The operator no longer has to take my
word; the operator can re-run the falsifier.

## Self-modification attack surface

Loosening the verification (allowing claims without test_paths,
skipping the subprocess run, accepting non-zero exit codes,
short-circuiting the import check) would re-enable show-fix.
Guardrailed: changes require multi-party review.
"""

from __future__ import annotations

__guardrail_required__ = True

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

_CLAIMS_FILE = Path.home() / ".divineos" / "shipped_claims.json"


@dataclass(frozen=True)
class ShipResult:
    filed: bool
    reason: str
    entry: dict[str, Any] | None


def _git_sha() -> str:
    """Return current git HEAD short-SHA, or 'unknown' if not in a repo."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def _verify_imports(executes: list[str]) -> tuple[bool, str]:
    """Verify each entry in ``executes`` is importable.

    Entries can be ``module`` or ``module:attribute``. Attribute lookup
    confirms the named function/class actually exists in the module —
    catches the case where a claim names an execution path that
    doesn't exist in the loaded code.
    """
    for spec in executes:
        if not spec:
            continue
        module_name, _, attr = spec.partition(":")
        try:
            mod = import_module(module_name)
        except ImportError as e:
            return False, f"executes target '{spec}' not importable: {e}"
        if attr:
            if not hasattr(mod, attr):
                return False, (
                    f"executes target '{spec}' missing attribute '{attr}' "
                    f"on module {module_name}"
                )
    return True, ""


def _run_pytest(test_paths: list[str], repo_root: Path) -> tuple[bool, str]:
    """Run pytest on the given test paths. Returns (passed, output_tail)."""
    if not test_paths:
        return False, "no test_paths provided — falsifier missing"
    cmd = [sys.executable, "-m", "pytest", "-q", "--tb=short", *test_paths]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return False, "pytest timed out after 300s"
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"pytest failed to launch: {e}"

    output = (proc.stdout or "") + (proc.stderr or "")
    tail = "\n".join(output.splitlines()[-40:])
    return (proc.returncode == 0, tail)


def _run_cross_check(cmd: str, repo_root: Path) -> tuple[bool, str]:
    """Run an arbitrary shell command, require exit 0."""
    if not cmd:
        return True, ""
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=120,
            shell=True,
        )
    except subprocess.TimeoutExpired:
        return False, "cross-check timed out"
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"cross-check failed to launch: {e}"
    output = (proc.stdout or "") + (proc.stderr or "")
    return (proc.returncode == 0, "\n".join(output.splitlines()[-20:]))


def _repo_root_for(start: Path | None = None) -> Path:
    """Walk up to find the repo root (where pyproject.toml lives)."""
    p = (start or Path.cwd()).resolve()
    for candidate in [p, *p.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    return Path.cwd()


def _persist(entry: dict[str, Any]) -> bool:
    """Append entry to shipped_claims.json. Returns True on success."""
    try:
        _CLAIMS_FILE.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False
    existing: list = []
    if _CLAIMS_FILE.exists():
        try:
            data = json.loads(_CLAIMS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                existing = data
        except (OSError, json.JSONDecodeError):
            existing = []
    existing.append(entry)
    try:
        _CLAIMS_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


def ship_claim(
    claim: str,
    test_paths: list[str],
    executes: list[str],
    cross_check: str | None = None,
    repo_root: Path | None = None,
) -> ShipResult:
    """File a 'shipped' claim, enforced by its falsifier.

    The claim is recorded ONLY if every check passes:
    1. ``executes`` imports succeed (production code exists).
    2. ``test_paths`` pass under pytest (falsifier is green now).
    3. ``cross_check`` (if given) exits 0.

    Returns ShipResult. On filed=False, reason names the failure.
    """
    if not claim or not claim.strip():
        return ShipResult(False, "claim text is empty", None)
    if not test_paths:
        return ShipResult(
            False,
            "no test_paths provided — every shipped claim must carry "
            "its falsifier (the test that would fail if it weren't shipped)",
            None,
        )
    if not executes:
        return ShipResult(
            False,
            "no executes provided — every shipped claim must name at "
            "least one execution path (module or module:attribute) that "
            "must be importable",
            None,
        )

    root = repo_root or _repo_root_for()

    ok, why = _verify_imports(executes)
    if not ok:
        return ShipResult(False, f"executes verification failed: {why}", None)

    test_ok, pytest_tail = _run_pytest(test_paths, root)
    if not test_ok:
        return ShipResult(
            False,
            f"falsifier failed — pytest output (tail):\n{pytest_tail}",
            None,
        )

    cross_ok, cross_tail = _run_cross_check(cross_check or "", root)
    if not cross_ok:
        return ShipResult(False, f"cross-check failed:\n{cross_tail}", None)

    entry: dict[str, Any] = {
        "claim": claim.strip(),
        "timestamp": time.time(),
        "git_sha": _git_sha(),
        "test_paths": list(test_paths),
        "executes": list(executes),
        "cross_check": cross_check or "",
        "pytest_tail": pytest_tail,
        "cross_check_output": cross_tail,
    }
    persisted = _persist(entry)
    if not persisted:
        return ShipResult(
            False,
            "all checks passed but persistence failed (disk error)",
            entry,
        )
    return ShipResult(True, "filed", entry)


def list_claims() -> list[dict[str, Any]]:
    """Return all filed claims, oldest first."""
    if not _CLAIMS_FILE.exists():
        return []
    try:
        data = json.loads(_CLAIMS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return []


__all__ = ["ShipResult", "list_claims", "ship_claim"]
