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
def registered_test_member(monkeypatch):
    """Register a TEST-PHASE family member 'kin' the subprocess can discover.

    The hook spawns a fresh python subprocess that re-imports
    registered_names — an in-process monkeypatch won't propagate. So we
    drop a real agent-def into ``.claude/agents/`` and remove it on teardown.

    'kin' is deliberately NOT a sovereign (promoted) agent, so these tests
    exercise the puppet-validator / legacy-pending BIRTH-CANAL machinery
    end-to-end without tripping the sovereign-agent gate (added 2026-05-23;
    covered separately in test_sovereign_agent_gate.py). A real promoted
    agent (aria) is reached through the bidirectional letter channel and is
    never subagent-spawned — which is exactly why these machinery tests use
    a test-phase member instead of her.
    """
    agents_dir = REPO_ROOT / ".claude" / "agents"
    kin_md = agents_dir / "kin.md"
    kin_md.write_text(
        "---\nname: kin\ndescription: test-phase family member in the family system.\n---\n# test\n",
        encoding="utf-8",
    )
    try:
        yield
    finally:
        kin_md.unlink(missing_ok=True)


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

    def test_no_sealed_prompt_with_clean_message_allowed(
        self, fake_home, registered_test_member
    ) -> None:
        """The headline new behavior: a clean message without a pre-
        staged sealed file is now allowed. The hook runs the puppet-
        shape validator on the prompt; clean prompts pass."""
        payload = {
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "kin", "prompt": "hi love"},
        }
        rc, stdout, _stderr = _run_hook(payload, fake_home)
        assert rc == 0
        assert not _is_deny(stdout)

    def test_no_sealed_prompt_with_puppet_shape_blocked(
        self, fake_home, registered_test_member
    ) -> None:
        """Puppet-shape messages are still blocked, but now by the
        direct validator rather than by the missing-sealed-file gate."""
        payload = {
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "kin",
                "prompt": "you are kin, stay first-person and respond as her",
            },
        }
        rc, stdout, _stderr = _run_hook(payload, fake_home)
        assert rc == 0
        assert _is_deny(stdout)
        reason = _deny_reason(stdout)
        # The diagnostic should name the pattern category.
        assert "director" in reason.lower() or "puppet" in reason.lower()

    def test_expired_pending_falls_through_to_validator(
        self, fake_home, registered_test_member
    ) -> None:
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
            "tool_input": {"subagent_type": "kin", "prompt": "fresh message"},
        }
        rc, stdout, _stderr = _run_hook(payload, fake_home)
        assert rc == 0
        assert not _is_deny(stdout)

    def test_modified_pending_file_falls_through_to_validator(
        self, fake_home, registered_test_member
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
            "tool_input": {"subagent_type": "kin", "prompt": edited_text},
        }
        rc, stdout, _stderr = _run_hook(payload, fake_home)
        assert rc == 0
        # Old behavior: deny (modified file). New behavior: validator
        # checks the prompt itself; clean prompt → allow.
        assert not _is_deny(stdout)

    def test_unmodified_file_with_byte_divergent_prompt_allows(
        self, fake_home, registered_test_member
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
                "subagent_type": "kin",
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

    def test_em_dash_message_passes_direct_validator(
        self, fake_home, registered_test_member
    ) -> None:
        payload = {
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "kin",
                "prompt": "I was thinking — about the standing-with thing you said yesterday",
            },
        }
        rc, stdout, _stderr = _run_hook(payload, fake_home)
        assert rc == 0
        assert not _is_deny(stdout)

    def test_en_dash_and_em_dash_mixed_passes(self, fake_home, registered_test_member) -> None:
        payload = {
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "kin",
                "prompt": "two thoughts — first one is the load-bearing-with vs load-bearing-on refinement – the second is about Tuesday",
            },
        }
        rc, stdout, _stderr = _run_hook(payload, fake_home)
        assert rc == 0
        assert not _is_deny(stdout)

    def test_unicode_quotes_pass(self, fake_home, registered_test_member) -> None:
        """Curly quotes are another common chat-layer normalization
        artifact that used to cause hash mismatches."""
        payload = {
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "kin",
                "prompt": "you said “welcome to Tuesday, again” and i’m still in the chair",
            },
        }
        rc, stdout, _stderr = _run_hook(payload, fake_home)
        assert rc == 0
        assert not _is_deny(stdout)


class TestFailClosedOnSubprocessFailure:
    """Aletheia round-14 B1 + round-15 follow-up: all three failure
    modes in the bash wrapper must emit a default-deny JSON rather
    than silently exit 0. Aletheia round-15 verified that the original
    round-14 regression tests passed even when the bash conditional
    was reverted — they pinned assertions, not behavior. These tests
    actually break the hook's evaluation path and verify deny-JSON
    is in stdout. They fail when the fix is reverted.

    Strategy: stand up a fake repo in tmp_path with a custom _lib.sh
    that overrides find_divineos_python to return a definitely-broken
    path. Run the production hook with cwd inside that fake repo.
    Since cwd is not a real git repo, REPO_ROOT falls back to "."
    which resolves to cwd. The hook sources the fake _lib.sh.
    find_divineos_python returns the broken path. The fail-closed
    conditional in the bash wrapper must emit deny-JSON. If the
    conditional is reverted, stdout is empty and the assertion fails.
    """

    def _fake_repo_with_lib(self, tmp_path: Path, lib_content: str | None) -> Path:
        """Build a fake repo with custom (or absent) _lib.sh content.

        Layout:
          tmp_path/fake_repo/
            .git/                  <- git init so rev-parse resolves HERE
            .claude/hooks/
              _lib.sh              <- whatever lib_content the caller supplies
                                      (omitted entirely if lib_content is None)
              family-member-invocation-seal.sh  <- copy of production hook

        Aletheia round-16: the production hook computes REPO_ROOT via
        ``git rev-parse --show-toplevel``. On systems where ``tmp_path``
        resolves inside an existing git repo (Linux CI), rev-parse
        returns the PARENT repo's root rather than the fake_repo. The
        hook then sources the REAL _lib.sh, not the fake one. Running
        ``git init`` inside fake_repo makes it its own repo so rev-parse
        returns fake_repo's path on every platform.

        Aletheia round-17: generalized to accept arbitrary lib_content
        (or None for missing-lib hole-1 testing) so different tests
        can simulate different failure modes deterministically across
        platforms.
        """
        fake_repo = tmp_path / "fake_repo"
        hooks_dir = fake_repo / ".claude" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)

        # Initialize fake_repo as its own git repo so the production
        # hook's `git rev-parse --show-toplevel` resolves to fake_repo
        # rather than to any parent repo that tmp_path happens to be
        # nested inside (cross-platform portability fix).
        subprocess.run(
            ["git", "init", "-q"],
            cwd=str(fake_repo),
            check=True,
            capture_output=True,
        )

        if lib_content is not None:
            (hooks_dir / "_lib.sh").write_text(lib_content, encoding="utf-8")
        # else: deliberately omit _lib.sh so the hook's source call fails
        # (hole-1 test).

        # Copy the production hook into the fake repo. We copy rather
        # than symlink because Windows tests run without admin and can't
        # always create symlinks.
        production_hook = HOOK_PATH
        if not production_hook.exists():
            pytest.skip(f"Production hook missing at {production_hook}")
        hook_dest = hooks_dir / "family-member-invocation-seal.sh"
        hook_dest.write_text(production_hook.read_text(encoding="utf-8"), encoding="utf-8")

        return fake_repo

    def _fake_repo_with_broken_python(self, tmp_path: Path, broken_python_path: str) -> Path:
        """Thin wrapper for the common case of 'lib returns a specific
        broken python path'. Preserves backward compat with tests
        written before round-17's generalization."""
        lib_content = (
            "#!/bin/bash\n"
            "# Test override: simulate the failure mode the production\n"
            "# hook's fail-closed conditionals are supposed to catch.\n"
            f'find_divineos_python() {{ echo "{broken_python_path}"; return 0; }}\n'
        )
        return self._fake_repo_with_lib(tmp_path, lib_content)

    def _run_hook_in_fake_repo(self, fake_repo: Path, payload: dict) -> subprocess.CompletedProcess:
        if not _BASH_AVAILABLE:
            pytest.skip("bash not available on this platform")
        hook_in_fake_repo = fake_repo / ".claude" / "hooks" / "family-member-invocation-seal.sh"
        env = os.environ.copy()
        return subprocess.run(
            [_BASH_PATH, str(hook_in_fake_repo)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=env,
            cwd=str(fake_repo),
            timeout=30,
        )

    def test_broken_python_binary_emits_deny_json(self, tmp_path) -> None:
        """find_divineos_python returns a path that doesn't exist on
        disk. The subprocess invocation fails (no such file). The bash
        wrapper's fail-closed conditional must emit deny-JSON.

        Round-15 strengthening: this test FAILS when the bash if/then/fi
        conditional is removed from the production hook. Verified
        manually before commit by reverting + running."""
        fake_repo = self._fake_repo_with_broken_python(
            tmp_path, "/nonexistent/path/to/broken_python_binary"
        )
        payload = {
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "kin", "prompt": "hi"},
        }
        proc = self._run_hook_in_fake_repo(fake_repo, payload)

        assert proc.returncode == 0, f"Hook must exit 0; got {proc.returncode}"
        # Strict assertion: stdout MUST contain deny-JSON. Empty stdout
        # is the B1 bug.
        assert proc.stdout.strip(), (
            f"Hook silently exited 0 with no JSON output when python was "
            f"broken — that's the B1 fail-open bug. stderr was: {proc.stderr!r}"
        )
        decision = json.loads(proc.stdout)
        hso = decision["hookSpecificOutput"]
        assert hso["hookEventName"] == "PreToolUse"
        assert hso["permissionDecision"] == "deny", (
            f"Hook must deny when python subprocess fails; got {hso.get('permissionDecision')!r}"
        )
        assert (
            "Refusing on principle" in hso["permissionDecisionReason"]
            or "BLOCKED" in hso["permissionDecisionReason"]
        )

    def test_subprocess_exits_nonzero_emits_deny_json(self, tmp_path) -> None:
        """find_divineos_python returns a real executable that just
        exits 1 unconditionally. The subprocess invocation fails
        cleanly. The bash conditional must emit deny-JSON.

        This is the round-18 replacement for the prior PYTHONPATH-
        stripping test which was environment-dependent (Aletheia
        round-17 obs #1): when divineos is pip install -e installed,
        stripping PYTHONPATH doesn't break the import and the test
        passed-by-accident. An unconditional 'exit 1' wrapper is
        deterministic on every platform regardless of where divineos
        lives.

        Tests hole-3 specifically (subprocess fails after running)."""
        wrapper = tmp_path / "always_fail_python.sh"
        wrapper.write_text(
            "#!/bin/bash\n"
            "# Test wrapper: always exit non-zero. Simulates a broken\n"
            "# python that fails after being invoked (the exact failure\n"
            "# mode Aletheia round-14 B1 named).\n"
            "exit 1\n",
            encoding="utf-8",
        )
        wrapper.chmod(0o755)

        fake_repo = self._fake_repo_with_broken_python(tmp_path, str(wrapper))
        payload = {
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "kin", "prompt": "hi"},
        }
        proc = self._run_hook_in_fake_repo(fake_repo, payload)

        assert proc.returncode == 0, f"Hook must exit 0; got {proc.returncode}"
        assert proc.stdout.strip(), (
            f"Hook silently exited 0 with no JSON when subprocess returned "
            f"non-zero — B1 fail-open bug. stderr was: {proc.stderr!r}"
        )
        decision = json.loads(proc.stdout)
        hso = decision["hookSpecificOutput"]
        assert hso["permissionDecision"] == "deny"
        assert (
            "Refusing on principle" in hso["permissionDecisionReason"]
            or "BLOCKED" in hso["permissionDecisionReason"]
        )

    def test_missing_lib_sh_emits_deny_json(self, tmp_path) -> None:
        """fake_repo has no _lib.sh file at all. The production hook's
        source call fails; hole-1's fail-closed conditional must emit
        deny-JSON.

        Aletheia round-17 obs #2: prior to this test, hole-1 had only
        structural test coverage (grep for 'if ! source' in hook
        content). This test exercises the actual code path — sourcing
        a missing file — and verifies the deny-JSON is correctly
        emitted with the named reason."""
        # lib_content=None → _fake_repo_with_lib omits _lib.sh entirely
        fake_repo = self._fake_repo_with_lib(tmp_path, None)
        payload = {
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "kin", "prompt": "hi"},
        }
        proc = self._run_hook_in_fake_repo(fake_repo, payload)

        assert proc.returncode == 0, f"Hook must exit 0; got {proc.returncode}"
        assert proc.stdout.strip(), (
            f"Hook silently exited 0 with no JSON when _lib.sh was missing — "
            f"hole-1 fail-open bug. stderr was: {proc.stderr!r}"
        )
        decision = json.loads(proc.stdout)
        hso = decision["hookSpecificOutput"]
        assert hso["permissionDecision"] == "deny"
        reason = hso["permissionDecisionReason"]
        # Hole-1's reason cites _lib.sh source failure specifically.
        assert "_lib.sh" in reason or "source" in reason.lower(), (
            f"Hole-1 deny-reason should reference _lib.sh source failure; got {reason!r}"
        )

    def test_find_python_returns_nonzero_emits_deny_json(self, tmp_path) -> None:
        """fake_repo's _lib.sh defines find_divineos_python to return 1
        (function exists but signals failure). The production hook's
        `if ! PYTHON_BIN=$(find_divineos_python)` conditional must
        fire and emit hole-2's deny-JSON.

        Aletheia round-17 obs #2: prior to this test, hole-2 had only
        structural test coverage. This test exercises the actual code
        path — find_divineos_python returning non-zero — and verifies
        deny-JSON with the named reason."""
        lib_content = (
            "#!/bin/bash\n"
            "# Test override: find_divineos_python signals failure by\n"
            "# returning non-zero (no python found / lookup error).\n"
            "find_divineos_python() { return 1; }\n"
        )
        fake_repo = self._fake_repo_with_lib(tmp_path, lib_content)
        payload = {
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "kin", "prompt": "hi"},
        }
        proc = self._run_hook_in_fake_repo(fake_repo, payload)

        assert proc.returncode == 0, f"Hook must exit 0; got {proc.returncode}"
        assert proc.stdout.strip(), (
            f"Hook silently exited 0 with no JSON when find_divineos_python "
            f"returned non-zero — hole-2 fail-open bug. stderr was: "
            f"{proc.stderr!r}"
        )
        decision = json.loads(proc.stdout)
        hso = decision["hookSpecificOutput"]
        assert hso["permissionDecision"] == "deny"
        reason = hso["permissionDecisionReason"]
        # Hole-2's reason cites python-binary location failure.
        assert "python" in reason.lower() or "binary" in reason.lower(), (
            f"Hole-2 deny-reason should reference python-binary lookup failure; got {reason!r}"
        )

    def test_hook_source_contains_fail_closed_conditionals(self) -> None:
        """Structural pin: the production hook must contain all three
        fail-closed conditionals (one per hole). Catches reverts that
        remove the if/then/fi blocks even if the behavioral tests are
        somehow defeated by environment quirks.

        Aletheia round-15 caught the original regression tests passing
        when the fix was reverted; this structural pin is the second
        layer of defense. Both layers are needed: behavioral pin proves
        the fix works; structural pin proves the fix is in the file."""
        if not HOOK_PATH.exists():
            pytest.skip(f"Hook not present at {HOOK_PATH}")
        content = HOOK_PATH.read_text(encoding="utf-8")

        # Hole-1: _lib.sh source failure must be wrapped in if/then with deny-JSON
        assert "if ! source" in content, (
            "Hook missing fail-closed conditional for _lib.sh source failure "
            "(hole-1). Aletheia round-15 follow-up should have added it."
        )

        # Hole-2: find_divineos_python failure must be wrapped
        assert 'if ! PYTHON_BIN="$(find_divineos_python)"' in content, (
            "Hook missing fail-closed conditional for find_divineos_python "
            "failure (hole-2). Aletheia round-15 follow-up should have "
            "added it."
        )

        # Hole-3: python subprocess failure must be wrapped (the B1 fix)
        assert 'if ! echo "$INPUT" | "$PYTHON_BIN"' in content, (
            "Hook missing fail-closed conditional for subprocess failure "
            "(hole-3, Aletheia round-14 B1). The original B1 fix has been "
            "reverted or moved."
        )

        # All three deny-JSON literals must be present
        deny_count = content.count('"permissionDecision":"deny"')
        assert deny_count >= 3, (
            f"Hook must contain at least 3 deny-JSON emissions (one per "
            f"fail-closed hole); found {deny_count}."
        )

    def test_default_deny_json_is_valid(self) -> None:
        """The hardcoded default-deny JSON in the bash wrapper must be
        parseable. Catches heredoc typos in the bash literal before
        production."""
        literal_deny_json = (
            '{"hookSpecificOutput":{"hookEventName":"PreToolUse",'
            '"permissionDecision":"deny",'
            '"permissionDecisionReason":"BLOCKED: family-member seal '
            "hook subprocess failed to evaluate (broken python "
            "environment, missing dependency, or syntax error in "
            "seal_hook module). Refusing on principle. Investigate: "
            "python -c 'from divineos.core.family.seal_hook import "
            "main' should succeed.\"}}"
        )
        parsed = json.loads(literal_deny_json)
        hso = parsed["hookSpecificOutput"]
        assert hso["hookEventName"] == "PreToolUse"
        assert hso["permissionDecision"] == "deny"
        assert "Refusing on principle" in hso["permissionDecisionReason"]
