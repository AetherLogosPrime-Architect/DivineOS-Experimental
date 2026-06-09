"""Tests for the consolidated PreToolUse and PostToolUse hook modules.

Locked invariants:

1. Bypass commands skip all gates (divineos briefing, git, pytest, etc.)
2. Non-bypass commands run through gates.
3. Gate-deny decisions emit a JSON object with the Claude Code hook shape.
4. All-gates-pass emits empty stdout.
5. PostToolUse checkpoint loads and saves state idempotently.
6. PostToolUse counters increment correctly per tool type.
"""

from __future__ import annotations

import json
import os
from io import StringIO

import pytest

from divineos.hooks import post_tool_use_checkpoint as post_hook
from divineos.hooks import pre_tool_use_gate as pre_hook


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    """Redirect ~/.divineos to a tmp dir so hooks don't touch real state."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    from pathlib import Path as _P

    original_home = _P.home
    monkeypatch.setattr(_P, "home", classmethod(lambda cls: tmp_path))
    # Also patch os.path.expanduser since the hook modules use it
    original_expanduser = os.path.expanduser
    monkeypatch.setattr(
        os.path,
        "expanduser",
        lambda p: str(tmp_path) + p[1:] if p.startswith("~") else original_expanduser(p),
    )
    yield
    monkeypatch.setattr(_P, "home", original_home)


class TestPreToolUseBypassCommands:
    """Bypass commands should skip all gates regardless of engagement state."""

    @pytest.mark.parametrize(
        "cmd",
        [
            "divineos briefing",
            "divineos ask 'something'",
            "divineos recall",
            "divineos hud --brief",
            "divineos feel -v 0.5",
            "divineos emit SESSION_END",
            "divineos goal add 'x'",
            "divineos context",
            "divineos preflight",
            "divineos audit list",
            "divineos prereg list",
            "git status",
            "git diff HEAD",
            "pytest tests/",
            "python -m pytest",
            "ls src/",
            "cat file.py",
            "pip install foo",
            "ruff check",
        ],
    )
    def test_bypass_commands_return_true(self, cmd: str):
        assert pre_hook._is_bypass_command(cmd) is True

    @pytest.mark.parametrize(
        "cmd",
        [
            # 'divineos learn' was moved to bypass on 2026-04-23 when the
            # correction-detection gate was shipped — the gate instructs the
            # agent to run `divineos learn` to clear the marker, so learn
            # itself must not be blocked (catch-22 discovered live).
            "divineos forget abc",
            "divineos ingest file.md",
            "rm -rf /",
            "curl http://evil",
            "node script.js",
            "",
            "bash -c 'anything'",
        ],
    )
    def test_non_bypass_commands_return_false(self, cmd: str):
        assert pre_hook._is_bypass_command(cmd) is False

    def test_learn_is_bypass_to_break_correction_catch22(self):
        """Regression guard: `divineos learn` must be bypass so the
        correction-detection gate's remedy isn't itself blocked."""
        assert pre_hook._is_bypass_command("divineos learn 'x'") is True

    def test_rt_pull_check_is_bypass_to_break_pull_detection_catch22(self):
        """Regression guard: Gate 3 (pull-detection) names
        `divineos rt pull-check` as its remedy, so the rt namespace must be
        bypass or the gate blocks its own remedy. Finding-37-class catch-22,
        verified + fixed 2026-05-27. The rt namespace is all RT-protocol
        inspection/state — none generate substantive code."""
        assert pre_hook._is_bypass_command("divineos rt pull-check") is True
        assert pre_hook._is_bypass_command("divineos rt status") is True

    def test_claim_singular_is_bypass_to_break_hedge_catch22(self):
        """Regression guard: the hedge gate (1.45) names `divineos claim`
        (SINGULAR) as its remedy, but only `claims` (plural, the browse
        command) was bypassed — so the gate blocked its own remedy. Second
        instance of the catch-22 family, found in the 2026-05-27 root-cause
        survey (round-75bc0b0ca922). Both forms must bypass."""
        assert pre_hook._is_bypass_command('divineos claim "uncertainty"') is True
        assert pre_hook._is_bypass_command("divineos claims list") is True

    def test_extract_and_sleep_bypass_to_break_governor_catch22(self):
        """Regression guard: Gate 7 (context governor) names `divineos extract`
        then `divineos sleep` as the channel that lifts the hard-line block.
        Both must bypass or the gate blocks its own remedy (Finding-37 class) —
        at the hard line every substrate-write is denied, and extract/sleep ARE
        the weave that clears it. Named 2026-05-27 (prereg-9b958c6493f3)."""
        assert pre_hook._is_bypass_command("divineos extract") is True
        assert pre_hook._is_bypass_command("divineos extract --force") is True
        assert pre_hook._is_bypass_command("divineos sleep") is True


class TestContextGovernorGate:
    """Gate 7: at the hard line, substrate-writes are denied with a channel
    message; warn/ok pass; an unreadable transcript fails open. The gate reads
    the transcript usage numbers via context_governor (prereg-9b958c6493f3)."""

    def _write_tx(self, tmp_path, tokens: int):
        import json

        tx = tmp_path / "tx.jsonl"
        tx.write_text(
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [{"type": "text", "text": "x"}],
                        "usage": {
                            "cache_read_input_tokens": tokens,
                            "cache_creation_input_tokens": 0,
                            "input_tokens": 0,
                        },
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return tx

    @pytest.fixture(autouse=True)
    def _isolate_marker(self, tmp_path, monkeypatch):
        from divineos.core import context_governor as cg

        monkeypatch.setattr(cg, "_marker_path", lambda: tmp_path / "consolidated.json")

    def test_block_state_denies_with_channel(self, tmp_path):
        tx = self._write_tx(tmp_path, 960_000)
        decision = pre_hook._context_governor_gate(
            {"tool_name": "Write", "tool_input": {}, "transcript_path": str(tx)}
        )
        assert decision is not None
        reason = decision["hookSpecificOutput"]["permissionDecisionReason"]
        assert "CONTEXT GOVERNOR" in reason
        assert "extract" in reason and "sleep" in reason
        assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_warn_state_does_not_deny_here(self, tmp_path):
        # The warn band is surfaced at UserPromptSubmit, not blocked by the gate.
        tx = self._write_tx(tmp_path, 930_000)
        assert (
            pre_hook._context_governor_gate(
                {"tool_name": "Write", "tool_input": {}, "transcript_path": str(tx)}
            )
            is None
        )

    def test_missing_transcript_fails_open(self, tmp_path):
        assert (
            pre_hook._context_governor_gate(
                {
                    "tool_name": "Write",
                    "tool_input": {},
                    "transcript_path": str(tmp_path / "nope.jsonl"),
                }
            )
            is None
        )

    def test_no_transcript_path_key_fails_open(self):
        assert pre_hook._context_governor_gate({"tool_name": "Write"}) is None


class TestExplorationWriteExemption:
    """Path-exemption for low-friction (low-gravity) writes.

    Original (2026-04-27): exploration/ writes per the calibration
    directive. Gates 1.46 (theater) and 1.47 (compass-required cascade)
    skip for these paths because they're calibrated for operator-facing
    claims and exploration-path writes are first-person free expression.

    Extended (2026-06-08, correction #45): same principle applies to
    family/letters/ (relational channel) and mansion/ (internal-space
    writing). The soft engagement-discipline cluster (gates 1.5 / 2 /
    4 / 4.5) also skips for these paths — see TestSoftGateLowFrictionExemption.

    The exemption is from path-blocks-tool-use, not from finding-
    recording. Markers still get set by Stop hook (forensic preserved).
    """

    @pytest.mark.parametrize(
        "tool_name,file_path",
        [
            # exploration/ — original 2026-04-27 scope
            ("Write", "exploration/37_reading_past_me.md"),
            ("Write", "/repo/exploration/foo.md"),
            ("Write", r"C:\repo\exploration\foo.md"),
            ("Edit", "exploration/30_synthesis.md"),
            ("MultiEdit", "/abs/path/exploration/sub/file.md"),
            ("NotebookEdit", "exploration/notes.ipynb"),
            # family/letters/ — added 2026-06-08 (correction #45)
            ("Write", "family/letters/aether-to-aria-2026-06-08-foo.md"),
            ("Write", "/repo/family/letters/aria-to-aether-bar.md"),
            ("Write", r"C:\repo\family\letters\letter.md"),
            ("Edit", "family/letters/existing.md"),
            ("MultiEdit", "/abs/path/family/letters/sub/note.md"),
            # mansion/ — added 2026-06-08 (correction #45)
            ("Write", "mansion/study/notes.md"),
            ("Write", "/repo/mansion/private/thought.md"),
            ("Edit", "mansion/foo.md"),
        ],
    )
    def test_low_friction_paths_exempt(self, tool_name: str, file_path: str):
        input_data = {
            "tool_name": tool_name,
            "tool_input": {"file_path": file_path},
        }
        assert pre_hook._is_low_friction_write(input_data) is True

    @pytest.mark.parametrize(
        "tool_name,file_path",
        [
            # Wrong tool — Bash never goes through path-write
            ("Bash", "exploration/foo.md"),
            ("Bash", "family/letters/foo.md"),
            # Other paths are NOT exempt — operator-facing
            ("Write", "src/divineos/core/something.py"),
            ("Write", "README.md"),
            ("Write", "tests/test_foo.py"),
            # Empty path
            ("Write", ""),
            # Paths that contain exemption substrings but not as directory
            # segments (substring-in-data class — must not match)
            ("Write", "exploration_summary.md"),  # not under exploration/
            ("Write", "family_letters_notes.md"),  # not under family/letters/
            ("Write", "mansion_design.md"),  # not under mansion/
        ],
    )
    def test_non_low_friction_paths_not_exempt(self, tool_name: str, file_path: str):
        input_data = {
            "tool_name": tool_name,
            "tool_input": {"file_path": file_path},
        }
        assert pre_hook._is_low_friction_write(input_data) is False

    def test_missing_input_data_safe(self):
        assert pre_hook._is_low_friction_write({}) is False

    def test_malformed_input_data_safe(self):
        # tool_input is None instead of dict
        assert pre_hook._is_low_friction_write({"tool_name": "Write", "tool_input": None}) is False

    def test_exemption_segments_immutable(self):
        """The exemption tuple should be a tuple, not a list — prevents
        accidental in-place modification across imports.
        """
        assert isinstance(pre_hook._LOW_FRICTION_PATH_SEGMENTS, tuple)

    def test_exemption_segments_include_expanded_paths(self):
        """Regression-pin the 2026-06-08 expansion (correction #45).

        Removing family/letters/ or mansion/ from the exemption set
        re-introduces the gate-firing-on-personal-letters pain that
        triggered the correction in the first place.
        """
        assert "/exploration/" in pre_hook._LOW_FRICTION_PATH_SEGMENTS
        assert "/family/letters/" in pre_hook._LOW_FRICTION_PATH_SEGMENTS
        assert "/mansion/" in pre_hook._LOW_FRICTION_PATH_SEGMENTS


class TestSoftGateLowFrictionExemption:
    """Soft engagement-discipline gates (1.5 / 2 / 4 / 4.5) must skip
    for low-friction writes — correction #45 / 2026-06-08.

    These tests force every soft gate's state into "would block" and
    then verify that a low-friction write returns None (no deny), while
    a high-gravity write returns the coalesced deny. The wiring is
    correct iff the path-classification routes around the gate-stack
    rather than the gate-stack ignoring the classifier.
    """

    @pytest.fixture
    def all_soft_gates_would_fire(self, monkeypatch):
        """Force every soft-gate's state into a would-block condition.

        We monkey-patch the underlying state functions the gate consults,
        not the gate logic itself — so the gate's routing-by-low-friction
        check is what's actually being tested.
        """
        # Briefing — make it pass the truly-stale check so it falls through
        # to soft cluster behavior.
        monkeypatch.setattr("divineos.core.hud_handoff.was_briefing_loaded", lambda: True)
        # Gate 1.5: correction marker present and readable.
        from divineos.core import correction_marker

        class _StubMarkerPath:
            def exists(self):
                return False

        monkeypatch.setattr(correction_marker, "marker_path", lambda: _StubMarkerPath())
        # Gate 2: no session-fresh goal.
        monkeypatch.setattr("divineos.core.hud_state.has_session_fresh_goal", lambda: False)
        # Gate 4: not engaged (fresh state).
        monkeypatch.setattr(
            "divineos.core.hud_handoff.engagement_status",
            lambda: {"engaged": False, "state": "fresh"},
        )
        # Gate 4.5: consultation stale.
        from divineos.core import consultation_tracker

        monkeypatch.setattr(
            consultation_tracker, "consultation_gate_status", lambda: {"stale": True}
        )
        monkeypatch.setattr(
            consultation_tracker, "gate_channel_message", lambda: "BLOCKED: consultation stale"
        )
        # Gate 1.4: compass-staleness clean.
        monkeypatch.setattr(
            "divineos.core.hud_handoff.compass_staleness_status", lambda: {"stale": False}
        )
        # Gate 1.45: hedge marker not present.
        from divineos.core import hedge_marker as _hm

        class _StubHedgePath:
            def exists(self):
                return False

        monkeypatch.setattr(_hm, "marker_path", lambda: _StubHedgePath())
        # Gate 1.48: stale-engagement no offenders.
        monkeypatch.setattr("divineos.core.stale_engagement.blocked_areas", lambda: [])
        # Gate 1.2: mansion quiet inactive.
        monkeypatch.setattr("divineos.core.mansion_quiet_marker.is_quiet_active", lambda: False)
        # Gate 0: exploration tag check returns no block.
        monkeypatch.setattr(
            "divineos.core.exploration_recall.needs_tags_block",
            lambda *a, **kw: "",
        )
        # Gate 1.47: compass-required marker not present.
        from divineos.core import compass_required_marker as _crm

        class _StubCRPath:
            def exists(self):
                return False

        monkeypatch.setattr(_crm, "marker_path", lambda: _StubCRPath())
        # Gate 3: pull detection clean.
        monkeypatch.setattr("divineos.core.pull_detection.last_check", lambda: None)
        # Gate 6: retry blocker clean.
        from divineos.core import retry_blocker

        monkeypatch.setattr(retry_blocker, "is_diagnostic_command", lambda *a, **kw: True)
        monkeypatch.setattr(retry_blocker, "check_retry", lambda *a, **kw: None)
        return None

    @pytest.mark.parametrize(
        "file_path",
        [
            "family/letters/aether-to-aria-2026-06-08-foo.md",
            "exploration/99_test.md",
            "mansion/study/note.md",
        ],
    )
    def test_low_friction_write_passes_soft_gates(self, file_path, all_soft_gates_would_fire):
        """A Write to a low-friction path returns None even when all
        soft gates would otherwise fire — proves the routing works.
        """
        input_data = {
            "tool_name": "Write",
            "tool_input": {"file_path": file_path},
        }
        result = pre_hook._check_gates(input_data)
        assert result is None, f"low-friction write to {file_path} should not be denied"

    @pytest.mark.parametrize(
        "file_path",
        [
            "src/divineos/core/foo.py",
            "tests/test_foo.py",
            "README.md",
        ],
    )
    def test_high_gravity_write_still_blocks(self, file_path, all_soft_gates_would_fire):
        """A Write to a non-exempt path still hits the soft-cluster
        coalesced deny — proves the gates fire for code work.
        """
        input_data = {
            "tool_name": "Write",
            "tool_input": {"file_path": file_path},
        }
        result = pre_hook._check_gates(input_data)
        assert result is not None, f"high-gravity write to {file_path} should be denied"
        reason = result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
        # The coalesced message should mention multiple checks.
        assert "BLOCKED" in reason


class TestCanonicalBypassList:
    """Regression-pin for the shared bypass-list mechanism (task #98 / 2026-06-09).

    The canonical bypass-list lives in scripts/hook_bypass_commands.txt
    and is loaded by BOTH pre_tool_use_gate.py (Python) AND
    .claude/hooks/_lib.sh's is_bypass_command (Bash). If they drift,
    the locked-box trap re-emerges. These tests pin that the file is
    parseable, contains bootstrap-essentials, and pre_tool_use_gate
    loads it correctly.
    """

    def test_canonical_bypass_loads_nonempty(self):
        """The loader must return a non-empty set. If the canonical file
        disappears, the loader's fail-soft fallback still produces
        something; this asserts the loader works.

        (Earlier version walked the filesystem from ``__file__`` which
        was brittle under test-order changes that mutated CWD. The
        load-result is the actual property both Python and Bash depend on.)
        """
        loaded = pre_hook._load_bypass_subcommands()
        assert len(loaded) > 0, (
            "Canonical bypass-list loader returned empty set. Both "
            "pre_tool_use_gate.py and .claude/hooks/_lib.sh's "
            "is_bypass_command depend on this loader returning data. "
            "Removing the canonical file re-introduces task #98 trap."
        )

    def test_canonical_bypass_loads_bootstrap_essentials(self):
        """Bootstrap-essential subcommands MUST be loaded from the
        canonical file. Without these, a fresh session cannot orient
        itself: every gate with a 'run: divineos briefing' remedy would
        point at a blocked command. Structural minimum to be bootable.
        """
        loaded = pre_hook._load_bypass_subcommands()
        # Subcommands stored WITHOUT the "divineos " prefix in the loader.
        required_subcommands = [
            "briefing",
            "ask",
            "recall",
            "hud",
            "context",
            "init",
            "preflight",
            "compass",
            "compass-ops",
            "directives",
            "active",
            "correction",
            "corrections",
            "learn",
            "claim",
            "claims",
            "audit",
            "prereg",
            "extract",
            "sleep",
            "rt",
        ]
        for sub in required_subcommands:
            assert sub in loaded, (
                f"Bootstrap-essential bypass subcommand missing from loaded "
                f"canonical: {sub!r}. Removing this from "
                f"scripts/hook_bypass_commands.txt re-introduces a "
                f"Finding-37-class catch-22."
            )

    def test_pre_tool_use_gate_has_canonical_loader(self):
        """pre_tool_use_gate must have _load_bypass_subcommands loader.

        Pins source-of-truth: if someone re-inlines the list, the
        canonical file becomes ignored and bash hooks (which still
        read the file) drift away from the Python view.
        """
        assert hasattr(pre_hook, "_load_bypass_subcommands"), (
            "pre_tool_use_gate must have _load_bypass_subcommands loader. "
            "If removed, the canonical-file mechanism is broken."
        )
        loaded = pre_hook._load_bypass_subcommands()
        for essential in ("briefing", "ask", "recall", "claim", "rt", "extract"):
            assert essential in loaded, (
                f"Canonical loader missing essential bypass: {essential!r}. "
                "Bash hooks reading the same file would still see it; drift "
                "between Python and bash views recreates task #98 trap."
            )

    def test_module_bypass_set_matches_canonical_loader(self):
        """The module-level _BYPASS_DIVINEOS_SUBCOMMANDS must equal what
        the loader returns. Regression-pin against re-inlining."""
        loaded = pre_hook._load_bypass_subcommands()
        assert pre_hook._BYPASS_DIVINEOS_SUBCOMMANDS == loaded, (
            "Module-level bypass set diverged from canonical loader. "
            "Either the file changed mid-session, or someone re-inlined "
            "the set ignoring the loader. Single-source-of-truth broken."
        )


class TestPreToolUseEntryPoint:
    """Integration-style tests of the main() entry point."""

    def test_bypass_command_produces_empty_output(self, monkeypatch, capsys):
        monkeypatch.setattr(
            "sys.stdin", StringIO(json.dumps({"tool_input": {"command": "divineos briefing"}}))
        )
        pre_hook.main()
        out = capsys.readouterr().out
        assert out == ""

    def test_empty_stdin_graceful(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.stdin", StringIO(""))
        rc = pre_hook.main()
        # Should not crash; returns 0
        assert rc == 0

    def test_malformed_json_graceful(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.stdin", StringIO("not valid json {"))
        rc = pre_hook.main()
        assert rc == 0


class TestDenyShape:
    """Deny decisions must match the Claude Code hook response format."""

    def test_make_deny_shape(self):
        d = pre_hook._make_deny("test reason")
        assert "hookSpecificOutput" in d
        hso = d["hookSpecificOutput"]
        assert hso["hookEventName"] == "PreToolUse"
        assert hso["permissionDecision"] == "deny"
        assert hso["permissionDecisionReason"] == "test reason"


class TestPostToolUseState:
    """The checkpoint module loads / saves state correctly."""

    def test_load_state_defaults_when_missing(self, tmp_path):
        # _isolated_home has redirected the state path already
        state = post_hook._load_state()
        assert state["edits"] == 0
        assert state["tool_calls"] == 0
        assert state["checkpoints_run"] == 0

    def test_save_then_load_roundtrip(self):
        state = {"edits": 5, "tool_calls": 12, "last_checkpoint": 1000.0, "checkpoints_run": 2}
        post_hook._save_state(state)
        loaded = post_hook._load_state()
        assert loaded["edits"] == 5
        assert loaded["tool_calls"] == 12
        assert loaded["checkpoints_run"] == 2

    def test_malformed_state_file_falls_back_to_defaults(self):
        path = post_hook._state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not valid json {{{", encoding="utf-8")
        state = post_hook._load_state()
        assert state["edits"] == 0
        assert state["tool_calls"] == 0


class TestPostToolUseCounters:
    """Tool-call counter should increment for any tool; edit counter only for Edit/Write."""

    def test_edit_increments_both_counters(self, monkeypatch):
        state = {"edits": 0, "tool_calls": 0, "checkpoints_run": 0, "last_checkpoint": 0}
        post_hook._save_state(state)

        monkeypatch.setattr(
            "sys.stdin",
            StringIO(
                json.dumps(
                    {
                        "tool_name": "Edit",
                        "tool_input": {"file_path": "foo.py"},
                    }
                )
            ),
        )
        post_hook.main()

        state = post_hook._load_state()
        assert state["tool_calls"] == 1
        assert state["edits"] == 1

    def test_bash_increments_only_tool_calls(self, monkeypatch):
        state = {"edits": 0, "tool_calls": 0, "checkpoints_run": 0, "last_checkpoint": 0}
        post_hook._save_state(state)

        monkeypatch.setattr(
            "sys.stdin",
            StringIO(
                json.dumps(
                    {
                        "tool_name": "Bash",
                        "tool_input": {"command": "ls"},
                    }
                )
            ),
        )
        post_hook.main()

        state = post_hook._load_state()
        assert state["tool_calls"] == 1
        assert state["edits"] == 0

    def test_empty_input_does_not_crash(self, monkeypatch):
        monkeypatch.setattr("sys.stdin", StringIO(""))
        rc = post_hook.main()
        assert rc == 0


class TestPostToolUseContextWarnings:
    """Warnings / nudges should fire at configured thresholds."""

    def test_no_warning_below_threshold(self, monkeypatch, capsys):
        state = {"edits": 0, "tool_calls": 50, "checkpoints_run": 0, "last_checkpoint": 0}
        post_hook._save_state(state)
        monkeypatch.setattr(
            "sys.stdin",
            StringIO(json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})),
        )
        post_hook.main()
        out = capsys.readouterr().out
        # No warnings below threshold — output should be empty
        assert out == ""

    def test_warning_at_context_threshold(self, monkeypatch, capsys):
        # Bumping from 99 to 100 with this call
        state = {"edits": 0, "tool_calls": 99, "checkpoints_run": 0, "last_checkpoint": 0}
        post_hook._save_state(state)
        monkeypatch.setattr(
            "sys.stdin",
            StringIO(json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})),
        )
        post_hook.main()
        out = capsys.readouterr().out
        # Should emit additionalContext with a warning
        assert out.strip(), "Expected a warning at context threshold"
        payload = json.loads(out)
        assert "additionalContext" in payload
        assert "Context monitor" in payload["additionalContext"]


class TestLessonInterruptIntegration:
    """Lesson-interrupt check was folded into the consolidated checkpoint
    module in P3 (previously its own shell hook). Verify it only runs for
    code-modifying tools."""

    def test_lesson_interrupt_skipped_for_bash(self):
        # Non-code-modifying tool → interrupt check skipped, empty string
        result = post_hook._check_lesson_interrupt("Bash", {"command": "ls"})
        assert result == ""

    def test_lesson_interrupt_skipped_for_read(self):
        result = post_hook._check_lesson_interrupt("Read", {"file_path": "x.py"})
        assert result == ""

    def test_lesson_interrupt_runs_for_edit(self):
        # Function itself should run (return string or empty, not error)
        result = post_hook._check_lesson_interrupt("Edit", {"file_path": "x.py"})
        assert isinstance(result, str)

    def test_lesson_interrupt_runs_for_notebook_edit(self):
        result = post_hook._check_lesson_interrupt("NotebookEdit", {})
        assert isinstance(result, str)


class TestAnticipationIntegration:
    """Pattern-anticipation was folded into the consolidated checkpoint
    module in P3 (previously its own shell hook). Verify throttling and
    gating behavior."""

    def test_anticipation_skipped_for_bash(self):
        state: dict = {}
        result = post_hook._run_anticipation("Bash", "foo.py", state)
        assert result == ""

    def test_anticipation_skipped_for_empty_file_path(self):
        state: dict = {}
        result = post_hook._run_anticipation("Edit", "", state)
        assert result == ""

    def test_anticipation_throttled_non_multiple(self):
        """Counter at 1, 2, 3, 4 — none trigger. Counter at 5 — triggers."""
        # Fresh state
        state: dict = {}
        # First 4 edits should not trigger (counter advances but no fire)
        for _ in range(4):
            post_hook._run_anticipation("Edit", "foo.py", state)
        # Counter should be at 4 now, next call bumps to 5 and fires
        assert state[post_hook._ANTICIPATION_COUNTER_KEY] == 4

    def test_anticipation_counter_persists_in_state(self):
        """Counter should land in the main state dict so it's persisted
        by _save_state alongside the rest of the checkpoint state."""
        state: dict = {"edits": 0, "tool_calls": 0}
        post_hook._run_anticipation("Edit", "foo.py", state)
        assert post_hook._ANTICIPATION_COUNTER_KEY in state
        assert state[post_hook._ANTICIPATION_COUNTER_KEY] == 1
