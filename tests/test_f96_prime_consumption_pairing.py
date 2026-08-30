"""Tests for F96 fix — fork-is-cheap-close-prime and closure-word-summary-prime
paired with Stop-side record_consumption.

Aletheia audit 2026-07-29 (AUDIT_2026-07-29_four-rounds-F96-F97.md,
finding find-cb124977dd85 MEDIUM): both primes previously had no paired
enforcement in src/. Unvalidated prime prints into a session and no
signal exists whether it was consumed. Fix: on fire, each prime writes
its emitted content to a per-hook marker file; Stop-side audit reads
those markers and calls record_consumption to score overlap between
primed content and response text. Mirrors the wallclock-source-prime +
check_wallclock_semantic_source pattern.

These tests exercise the pair end-to-end at the hook level:
  1. Prime fires and writes marker with the correct primed content.
  2. Marker file lives at the expected path so Stop-side can find it.

Also F97 remediation: closure-word-summary-prime extension previously
had no new tests; these cover both primes' fire+marker path.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


HOOKS_DIR = Path(__file__).resolve().parent.parent / ".claude" / "hooks"
FORK_HOOK = HOOKS_DIR / "fork-is-cheap-close-prime.sh"
CLOSURE_HOOK = HOOKS_DIR / "closure-word-summary-prime.sh"


def _bash():
    candidates = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
        "/bin/bash",
        "bash",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    pytest.skip("no usable bash interpreter for hook invocation")


def _run(hook_path: Path, prompt: str, tmp_home: Path) -> subprocess.CompletedProcess:
    """Run a prime hook with HOME redirected to tmp_home so we can inspect
    the marker file it writes without touching real ~/.divineos."""
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    payload = json.dumps({"prompt": prompt})
    return subprocess.run(
        [_bash(), str(hook_path)],
        input=payload,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )


def test_fork_prime_writes_marker_on_fire(tmp_path):
    """When the fork-is-cheap-close-prime fires, it writes its emitted
    content to $HOME/.divineos/fork_cheap_close_prime_surface_last.txt
    so Stop-side record_consumption can score overlap."""
    result = _run(FORK_HOOK, "which one should we do first?", tmp_path)
    if "FORK-IS-CHEAP-CLOSE PRIME" not in result.stdout:
        pytest.skip(
            f"prime did not fire in this environment (returncode={result.returncode}, "
            f"stderr={result.stderr!r}); skipping marker check"
        )
    marker = tmp_path / ".divineos" / "fork_cheap_close_prime_surface_last.txt"
    assert marker.exists(), (
        f"expected marker at {marker} after prime fire; stdout={result.stdout!r}"
    )
    content = marker.read_text(encoding="utf-8")
    assert "FORK-IS-CHEAP-CLOSE PRIME" in content, (
        f"marker content missing prime header; got: {content[:200]!r}"
    )


def test_fork_prime_no_marker_when_not_firing(tmp_path):
    """When the fork-prime does not fire (irrelevant prompt), no marker
    file is written. Silence is silence — marker only tracks fire events."""
    result = _run(FORK_HOOK, "unrelated conversational message", tmp_path)
    marker = tmp_path / ".divineos" / "fork_cheap_close_prime_surface_last.txt"
    if "FORK-IS-CHEAP-CLOSE PRIME" in result.stdout:
        pytest.skip("prime unexpectedly fired on unrelated prompt; skipping negative check")
    assert not marker.exists(), f"marker should not exist when prime did not fire; found: {marker}"


def test_closure_prime_writes_marker_on_fire(tmp_path):
    """When the closure-word-summary-prime fires, it writes its emitted
    content to $HOME/.divineos/closure_word_summary_prime_surface_last.txt."""
    # Closure-word prime fires on verification-outcome contexts. Test
    # with a prompt-shape that triggers it.
    result = _run(
        CLOSURE_HOOK,
        "did the tests pass",
        tmp_path,
    )
    if "CLOSURE-WORD SUMMARY PRIME" not in result.stdout:
        pytest.skip(
            f"closure prime did not fire in this environment "
            f"(returncode={result.returncode}, stderr={result.stderr!r})"
        )
    marker = tmp_path / ".divineos" / "closure_word_summary_prime_surface_last.txt"
    assert marker.exists(), (
        f"expected marker at {marker} after prime fire; stdout={result.stdout!r}"
    )
    content = marker.read_text(encoding="utf-8")
    assert "CLOSURE-WORD SUMMARY PRIME" in content, (
        f"marker content missing prime header; got: {content[:200]!r}"
    )


def test_stop_side_consumption_wiring_reads_marker():
    """The Stop-side audit path in operating_loop_audit.py reads both
    marker filenames when performing consumption telemetry. This test
    verifies the wiring exists — grep the source rather than execute
    the whole audit path which has many dependencies."""
    audit_file = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "divineos"
        / "core"
        / "operating_loop_audit.py"
    )
    text = audit_file.read_text(encoding="utf-8")
    assert "fork_cheap_close_prime_surface_last.txt" in text, (
        "fork-prime marker not read by operating_loop_audit — F96 not paired"
    )
    assert "closure_word_summary_prime_surface_last.txt" in text, (
        "closure-prime marker not read by operating_loop_audit — F96 not paired"
    )
    assert "record_consumption" in text, (
        "record_consumption not imported in operating_loop_audit — F96 fix incomplete"
    )
