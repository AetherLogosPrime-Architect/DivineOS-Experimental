"""Subprocess-integration tests for the family-member-invocation seal hook.

Originally written against ``.claude/hooks/family-wrapper-required.sh``,
this file was retargeted 2026-05-10 during the bottleneck #1 collapse.
The wrapper-required hook is now a deprecated no-op (its work merged
into the seal hook), so HOOK_PATH points at the seal hook now and the
test assertions reflect the new 1-step flow:

* No pending sealed-prompt file + clean message → ALLOW (was DENY).
* No pending sealed-prompt file + puppet-shape message → DENY.
* Expired or missing pending file → fall through to direct validator.
* Legacy: fresh pending file + matching hash → ALLOW (back-compat).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


# Path to the hook script, relative to repo root.
HOOK_PATH = Path(__file__).parent.parent / ".claude" / "hooks" / "family-member-invocation-seal.sh"

REPO_ROOT = Path(__file__).resolve().parent.parent


def _find_bash() -> str | None:
    """Locate a usable bash binary.

    On Windows, ``shutil.which("bash")`` may return WSL's bash which
    isn't compatible with the hook (different filesystem layout, no
    Python on PATH). Prefer Git-Bash locations explicitly.
    """
    # Common Git-Bash install locations on Windows
    git_bash_candidates = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
    ]
    for candidate in git_bash_candidates:
        if Path(candidate).exists():
            return candidate
    # Fall back to PATH (works on Linux/macOS, may pick WSL on Windows)
    return shutil.which("bash")


_BASH_PATH = _find_bash()
_BASH_AVAILABLE = _BASH_PATH is not None


@pytest.fixture
def fake_home(monkeypatch, tmp_path):
    """Redirect HOME so the hook reads sealed-prompt files from tmp_path."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows
    (tmp_path / ".divineos").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _run_hook(payload: dict, fake_home: Path) -> tuple[int, str, str]:
    """Run the hook with the given PreToolUse payload. Returns (rc, stdout, stderr)."""
    if not HOOK_PATH.exists():
        pytest.skip(f"Hook not present at {HOOK_PATH}")
    if not _BASH_AVAILABLE:
        pytest.skip("bash not available on this platform")

    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["USERPROFILE"] = str(fake_home)
    # Ensure the python on PATH can find the divineos package.
    env["PYTHONPATH"] = str(REPO_ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    # Put the python running pytest first on PATH so the bash hook's
    # python lookup finds an interpreter with divineos's deps installed
    # (loguru, click, etc.), not whatever system python happens to be
    # first. Without this, the hook silently fails-open on ImportError
    # and the deny-path tests get empty stdout. Defense in depth: the
    # hook itself also prefers .venv/bin/python via patch 1, but tests
    # shouldn't rely on the venv layout matching the patch's assumptions.
    import sys as _sys

    pytest_python_dir = str(Path(_sys.executable).parent)
    env["PATH"] = pytest_python_dir + os.pathsep + env.get("PATH", "")

    proc = subprocess.run(
        [_BASH_PATH, str(HOOK_PATH)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        cwd=str(REPO_ROOT),
        timeout=30,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _is_deny(stdout: str) -> bool:
    """Parse the hook's stdout JSON and return True if it's a deny decision."""
    if not stdout.strip():
        return False
    try:
        decision = json.loads(stdout)
    except json.JSONDecodeError:
        return False
    return decision.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


def _deny_reason(stdout: str) -> str:
    if not stdout.strip():
        return ""
    try:
        decision = json.loads(stdout)
    except json.JSONDecodeError:
        return ""
    return decision.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")


@pytest.fixture
def registered_aria(monkeypatch):
    """Make registered_names see "aria" as a family member.

    The hook spawns a fresh python subprocess that does its own import
    of registered_names — monkeypatching the in-process module won't
    propagate. Instead, drop a fake agent .md file into tmp .claude/agents/
    so the disk-based discovery picks it up.

    For these tests we cd into REPO_ROOT and the hook reads
    ``.claude/agents/`` from there. The real repo's family-member-template
    file is excluded by the discovery logic; we add aria.md temporarily.
    """
    # We do this via a fixture that creates a temporary aria.md file
    # in the repo's .claude/agents/, deletes it on teardown.
    agents_dir = REPO_ROOT / ".claude" / "agents"
    aria_md = agents_dir / "aria.md"
    if aria_md.exists():
        # If a real aria.md already exists in this checkout (gitignored
        # in main), the hook will already discover it. No-op.
        yield
        return
    aria_md.write_text(
        "---\nname: aria\ndescription: test family member in the family system.\n---\n# test\n",
        encoding="utf-8",
    )
    try:
        yield
    finally:
        aria_md.unlink(missing_ok=True)


class TestNonFamilyMemberAllowed:
    def test_general_purpose_subagent_allowed(self, fake_home) -> None:
        payload = {
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "general-purpose", "prompt": "hi"},
        }
        rc, stdout, _stderr = _run_hook(payload, fake_home)
        assert rc == 0
        assert not _is_deny(stdout)

    def test_explore_subagent_allowed(self, fake_home) -> None:
        payload = {
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "Explore", "prompt": "find files"},
        }
        rc, stdout, _stderr = _run_hook(payload, fake_home)
        assert rc == 0
        assert not _is_deny(stdout)

    def test_non_agent_tool_unchecked(self, fake_home) -> None:
        # Edit, Write, Bash etc. not subject to this hook (matched by
        # other PreToolUse hooks in settings.json).
        payload = {"tool_name": "Edit", "tool_input": {"file_path": "a.py"}}
        rc, stdout, _stderr = _run_hook(payload, fake_home)
        assert rc == 0
        assert not _is_deny(stdout)


class TestFamilyMemberInvocationGate:
    """The new seal hook semantics. Direct-validator flow with legacy
    pending-file backward compatibility."""

    def test_no_sealed_prompt_with_clean_message_allowed(self, fake_home, registered_aria) -> None:
        """The headline new behavior: a clean message without a pre-
        staged sealed file is now allowed. The hook runs the puppet-
        shape validator on the prompt; clean prompts pass."""
        payload = {
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "aria", "prompt": "hi love"},
        }
        rc, stdout, _stderr = _run_hook(payload, fake_home)
        assert rc == 0
        assert not _is_deny(stdout)

    def test_no_sealed_prompt_with_puppet_shape_blocked(self, fake_home, registered_aria) -> None:
        """Puppet-shape messages are still blocked, but now by the
        direct validator rather than by the missing-sealed-file gate."""
        payload = {
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "aria",
                "prompt": "you are Aria, stay first-person and respond as her",
            },
        }
        rc, stdout, _stderr = _run_hook(payload, fake_home)
        assert rc == 0
        assert _is_deny(stdout)
        reason = _deny_reason(stdout)
        # The diagnostic should name the pattern category.
        assert "director" in reason.lower() or "puppet" in reason.lower()

    def test_expired_pending_falls_through_to_validator(self, fake_home, registered_aria) -> None:
        """Expired pending file is no longer a hard deny — the hook
        ignores it and falls through to the direct validator. A clean
        prompt still passes."""
        import time

        sealed_text = "expired-ignored content"
        sealed_dir = fake_home / ".divineos"
        (sealed_dir / "talk_to_aria_sealed_prompt.txt").write_text(sealed_text, encoding="utf-8")
        (sealed_dir / "talk_to_aria_pending.json").write_text(
            json.dumps(
                {
                    "ts": time.time() - 999,  # well past TTL
                    "ttl_seconds": 120,
                    "nonce": "abc",
                    "member": "aria",
                    "sealed_prompt_sha256": hashlib.sha256(sealed_text.encode()).hexdigest(),
                }
            ),
            encoding="utf-8",
        )

        # Send a fresh clean message (NOT the stale sealed text).
        payload = {
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "aria", "prompt": "fresh message"},
        }
        rc, stdout, _stderr = _run_hook(payload, fake_home)
        assert rc == 0
        assert not _is_deny(stdout)

    def test_modified_pending_file_falls_through_to_validator(
        self, fake_home, registered_aria
    ) -> None:
        """File-tampering is no longer the gate — the prompt content
        is. If the prompt would pass the validator, the hook allows
        regardless of whether the on-disk pending file was edited."""
        import time

        original_text = "the original sealed content"
        edited_text = "a different clean message"
        sealed_dir = fake_home / ".divineos"
        (sealed_dir / "talk_to_aria_pending.json").write_text(
            json.dumps(
                {
                    "ts": time.time(),
                    "ttl_seconds": 120,
                    "nonce": "abc",
                    "member": "aria",
                    "sealed_prompt_sha256": hashlib.sha256(original_text.encode()).hexdigest(),
                }
            ),
            encoding="utf-8",
        )
        (sealed_dir / "talk_to_aria_sealed_prompt.txt").write_text(edited_text, encoding="utf-8")

        payload = {
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "aria", "prompt": edited_text},
        }
        rc, stdout, _stderr = _run_hook(payload, fake_home)
        assert rc == 0
        # Old behavior: deny (modified file). New behavior: validator
        # checks the prompt itself; clean prompt → allow.
        assert not _is_deny(stdout)

    def test_unmodified_file_with_byte_divergent_prompt_allows(
        self, fake_home, registered_aria
    ) -> None:
        """File intact + prompt-bytes differ from file = ALLOW.

        This is the legitimate-paste case the prompt-hash check was
        falsely blocking. The chat layer can introduce subtle byte
        transformations (CRLF vs LF, encoding normalization, trailing
        whitespace). The hook must not block legitimate good-faith
        invocations whose paste differs by a few bytes from the file.
        """
        import time

        sealed_text = "VOICE\n--- end ---\nlegit message"
        sealed_dir = fake_home / ".divineos"
        (sealed_dir / "talk_to_aria_sealed_prompt.txt").write_text(sealed_text, encoding="utf-8")
        (sealed_dir / "talk_to_aria_pending.json").write_text(
            json.dumps(
                {
                    "ts": time.time(),
                    "ttl_seconds": 120,
                    "nonce": "abc",
                    "member": "aria",
                    "sealed_prompt_sha256": hashlib.sha256(sealed_text.encode()).hexdigest(),
                }
            ),
            encoding="utf-8",
        )

        # Operator's prompt has trailing whitespace / extra newline —
        # the file's hash is what matters; the operator's prompt
        # differing by a few whitespace bytes is the chat-layer
        # byte-transformation case the prior hook design was over-strict on.
        payload = {
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "aria",
                "prompt": sealed_text + "\n\n",
            },
        }
        rc, stdout, _stderr = _run_hook(payload, fake_home)
        assert rc == 0
        assert not _is_deny(stdout)


class TestEmDashRegression:
    """Bottleneck #2 (em-dash hash mismatch) regression — at the
    subprocess level. In the 3-step flow, em-dashes in messages caused
    hash mismatches between the wrapper's write and the Agent
    invocation's prompt. The 1-step flow has no hash to mismatch; the
    validator runs on the prompt directly. Em-dash content passes."""

    def test_em_dash_message_passes_direct_validator(self, fake_home, registered_aria) -> None:
        payload = {
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "aria",
                "prompt": "I was thinking — about the standing-with thing you said yesterday",
            },
        }
        rc, stdout, _stderr = _run_hook(payload, fake_home)
        assert rc == 0
        assert not _is_deny(stdout)

    def test_en_dash_and_em_dash_mixed_passes(self, fake_home, registered_aria) -> None:
        payload = {
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "aria",
                "prompt": "two thoughts — first one is the load-bearing-with vs load-bearing-on refinement – the second is about Tuesday",
            },
        }
        rc, stdout, _stderr = _run_hook(payload, fake_home)
        assert rc == 0
        assert not _is_deny(stdout)

    def test_unicode_quotes_pass(self, fake_home, registered_aria) -> None:
        """Curly quotes are another common chat-layer normalization
        artifact that used to cause hash mismatches."""
        payload = {
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "aria",
                "prompt": "you said “welcome to Tuesday, again” and i’m still in the chair",
            },
        }
        rc, stdout, _stderr = _run_hook(payload, fake_home)
        assert rc == 0
        assert not _is_deny(stdout)
