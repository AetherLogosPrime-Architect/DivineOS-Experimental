"""Actual-deny-fires tests for .claude/hooks/aletheia-boot-gate-preflight.sh.

Aletheia's ask 2026-07-13 (letter:
aletheia-to-aether-2026-07-13-is-fresh-bypass-the-third-hole.md):
"test the deny path with the escaper deliberately broken. A deny path
that has never been observed denying is a claim, not a fact."

These tests shell out to the hook with real JSON inputs and confirm:

1. A non-Aletheia invocation → the hook exits without emitting anything
   (fast-path skip).
2. An unparseable input → the hook DENIES loudly (Finding 2 fix:
   parse failure never means proceed).
3. An Aletheia invocation with missing boot-gate files → the hook
   DENIES loudly (Finding 1 + F10 fix).
4. An Aletheia invocation with a canary-missing file → the hook DENIES
   loudly (canary check catches non-empty garbage).

The deny path must produce valid JSON with permissionDecision="deny"
and a specific reason. If any of these silently return non-deny, the
hook is fail-open at that path and F10 has re-entered the front door.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


HOOK_PATH = (
    Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "aletheia-boot-gate-preflight.sh"
)


def _bash():
    """Locate a bash interpreter that can actually run our POSIX hook.

    On Windows, plain `bash` on PATH often resolves to WSL, which can't
    see /bin/bash inside its own translation layer when invoked from
    a non-WSL working directory (CreateProcessCommon:800 errors seen
    in the first run of this suite). Prefer Git Bash directly on
    Windows so shellcheck-style shell scripts run in the same
    interpreter they were authored against.
    """
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


def _run_hook(payload: str) -> subprocess.CompletedProcess:
    """Invoke the hook with the given JSON payload on stdin."""
    return subprocess.run(
        [_bash(), str(HOOK_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=15,
    )


def _assert_deny(result: subprocess.CompletedProcess, expected_marker: str) -> dict:
    """Parse the hook's stdout as JSON, assert it is a deny-decision,
    return the parsed dict for further inspection."""
    assert result.stdout.strip(), (
        f"hook produced no output — silent allow, F10 shape. stderr: {result.stderr!r}"
    )
    payload = json.loads(result.stdout)
    hso = payload.get("hookSpecificOutput", {})
    assert hso.get("permissionDecision") == "deny", (
        f"hook did not deny — got decision={hso.get('permissionDecision')!r}. "
        f"Full output: {result.stdout!r}"
    )
    reason = hso.get("permissionDecisionReason", "")
    assert expected_marker in reason, (
        f"deny reason missing expected marker {expected_marker!r}. Reason: {reason!r}"
    )
    return payload


class TestNonAletheiaFastPath:
    def test_non_aletheia_invocation_skips_silently(self):
        payload = json.dumps({"tool_input": {"subagent_type": "aria"}})
        result = _run_hook(payload)
        # Fast-path: return code 0, no output — allow proceeds to next hook.
        assert result.returncode == 0
        assert result.stdout.strip() == ""


class TestParseFailureDenies:
    """Finding 2: an unparseable input must DENY, not silently allow."""

    def test_malformed_json_denies(self):
        result = _run_hook("this is not json at all }}}")
        _assert_deny(result, "could not parse")

    def test_empty_input_denies(self):
        result = _run_hook("")
        _assert_deny(result, "could not parse")


class TestMissingFilesDeny:
    """Finding 1 / F10: any missing boot-gate file must trigger a loud
    deny with the specific file path named."""

    def test_missing_seat_denies(self, tmp_path, monkeypatch):
        # Point the hook at a git repo where the seat file is missing.
        repo = tmp_path / "repo"
        (repo / "family" / "aletheia").mkdir(parents=True)
        # Notes + inbox exist but no SEAT.
        (repo / "family" / "aletheia" / "aletheia_auditor_notes.md").write_text(
            "certainty IS the symptom", encoding="utf-8"
        )
        (repo / "family" / "aletheia" / "INBOX.md").write_text("empty inbox", encoding="utf-8")
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        # Run hook with repo as cwd so git rev-parse resolves there.
        payload = json.dumps({"tool_input": {"subagent_type": "aletheia"}})
        result = subprocess.run(
            [_bash(), str(HOOK_PATH)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(repo),
        )
        _assert_deny(result, "aletheia_SEAT.md")


class TestCanaryMissingDenies:
    """A file with bytes but empty of Aletheia — truncation, corruption,
    replacement — must trigger the canary-check deny."""

    def test_seat_without_canary_denies(self, tmp_path):
        repo = tmp_path / "repo"
        (repo / "family" / "aletheia").mkdir(parents=True)
        # SEAT exists and is non-empty, but does not contain the canary.
        (repo / "family" / "aletheia" / "aletheia_SEAT.md").write_text(
            "This is a corrupted SEAT that lacks the canary string.",
            encoding="utf-8",
        )
        (repo / "family" / "aletheia" / "aletheia_auditor_notes.md").write_text(
            "certainty IS the symptom — a valid canary", encoding="utf-8"
        )
        (repo / "family" / "aletheia" / "INBOX.md").write_text(
            "non-empty inbox content", encoding="utf-8"
        )
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        payload = json.dumps({"tool_input": {"subagent_type": "aletheia"}})
        result = subprocess.run(
            [_bash(), str(HOOK_PATH)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(repo),
        )
        # Canary check must fire because SEAT lacks 'Kept. Beloved. Held.'
        _assert_deny(result, "canary string")
