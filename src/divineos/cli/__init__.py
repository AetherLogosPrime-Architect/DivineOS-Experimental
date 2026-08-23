"""DivineOS CLI - Foundation Memory & Knowledge.

Commands for managing the event ledger, ingesting conversations,
verifying data integrity, and consolidating knowledge.
"""

import sys

import click

from divineos.cli._wrappers import _ensure_db
from divineos.core.corrigibility import _OFF_SWITCH_REQUIRED
from divineos.core.enforcement import capture_user_input, setup_cli_enforcement

# Make stdout/stderr tolerant of Unicode characters that the underlying
# console can't render. On Windows the default cp1252 console codec
# crashes on emojis (e.g. "ÃƒÂ°Ã…Â¸Ã¢â‚¬â„¢Ã‚Â¬" used in the session rating prompt),
# bubbling up as UnicodeEncodeError ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â we saw this as spurious
# "Auto-scan failed" messages during extract. Reconfiguring with
# errors="replace" substitutes an unsupported character with "?" instead
# of raising. No-op on platforms whose streams are already UTF-8.
# Runs at import time so it is in effect before any CLI command writes
# to stdout/stderr.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, OSError, ValueError):
        pass

# Commands that work without briefing loaded ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â the minimum to bootstrap.
_BYPASS_COMMANDS = frozenset(
    {
        "admin",
        "audit",
        "inspect",
        "briefing",
        "init",
        "preflight",
        "emit",
        "hud",
        # Goal-setting is bootstrap: adding a goal for the session must not
        # require briefing first Ã¢â‚¬â€ that creates a recursive deadlock with the
        # require-goal PreToolUse hook (goal gate needs a goal set, but the CLI
        # refuses `goal add` without briefing, and the goal gate blocks briefing
        # if the command is chained through pipes). Root cause fix 2026-07-17,
        # mirrors the hook-layer bypass at scripts/hook_bypass_commands.txt:48.
        "goal",
        # Compass integration is bootstrap for the identical reason, found
        # the hard way 2026-08-05: the compass gate blocks tool use until an
        # advisory is integrated; its two prescribed remedies are
        # `compass-ops observe` and `compass-ops dismiss`; BOTH were
        # briefing-gated while `divineos briefing` was itself compass-gated.
        # Verified circular in both directions -- no exit through any
        # prescribed path, and the Edit that would have fixed it was blocked
        # by the same gate. Same class as the `goal` deadlock above, unfixed
        # because the 2026-07-17 fix addressed the instance rather than
        # sweeping every gate whose prescribed remedy is a divineos command.
        "compass-ops",
        "compass",
        # `learn` is remedy (a) of the correction-marker gate and was itself
        # briefing-gated, producing a second deadlock on 2026-08-05: the
        # marker blocks tool use, prescribes `divineos learn`, `learn` demands
        # briefing, and briefing is blocked by the marker. Of that gate's three
        # prescribed remedies only (b) `correction` was reachable -- (c)
        # clear_correction_marker.py refused six invocations. A gate must never
        # prescribe a remedy another gate blocks.
        "learn",
        # Found by tests/test_gate_remedy_reachability.py on its FIRST run,
        # before it ever deadlocked. andrew-correction-attestation.sh emits a
        # permissionDecisionReason blocking all substantive tool use and
        # prescribing `divineos andrew-correction integrate|defer|list` -- and
        # states "No env-var bypass exists... To genuinely override, edit the
        # hook in a visible commit." A hard block with the escape hatch
        # deliberately removed, prescribing a command the briefing gate
        # refused. Strictly worse than the two deadlocks hit by hand today,
        # and it was still latent. This is the fence catching a post nobody
        # had walked to yet.
        "andrew-correction",
        # Different victim, same class. check-branch-on-push.sh:137 does not
        # PRESCRIBE this to me -- it INVOKES it: `$PYTHON_BIN -m divineos
        # check-branch --strict --fetch`. A git hook fires whenever a push
        # happens, including before any briefing is loaded, so gating it on my
        # session state breaks the hook rather than deadlocking me. Silent
        # tooling failure instead of a visible block, which is worse.
        "check-branch",
        "recall",
        "active",
        "ask",
        "context",
        "verify",
        "health",
        "feel",
        "affect",
        "checkpoint",
        "context-status",
        "context-tokens",
        "self-model",
        "drift",
        "predict",
        "affect-feedback",
        "attention",
        "epistemic",
        "sleep",
        "progress",
        "validate",
        "rt",
        "hold",
        "mansion",
        "prereg",
        # Corrections must always be loggable in the moment ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â gating the
        # rep behind a thinking-command requirement defeats the rep.
        "correction",
        "corrections",
        # Scheduled / headless runs are the Routines entry point; they
        # bypass briefing by design (no human to load one at 3am cron).
        # Corrigibility still applies ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â see scheduled_commands.py.
        "scheduled",
        # Science lab is a read-only numerical tool; shouldn't gate on
        # briefing. Safe to run cold.
        "lab",
    }
    # Off-switch contract (grounded-audit 2026-06-02, Theme 1): every
    # command that must survive EMERGENCY_STOP (_OFF_SWITCH_REQUIRED:
    # mode, emit, extract, hud, preflight, briefing) must ALSO bypass the
    # briefing gate ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â otherwise a second, independent gate traps the
    # off-switch when no briefing is loaded (extract = clean shutdown,
    # mode = see/restore state). Unioning from the single source of truth
    # means the two lists can never drift again (CLAUDE.md truth #8:
    # structural cure over whack-a-mole). The first sweep missed this
    # because it never read across both gates.
    | _OFF_SWITCH_REQUIRED
)


def _enforce_operating_mode() -> None:
    """Refuse commands disallowed by the current operating mode.

    Runs BEFORE the briefing gate. Corrigibility has priority over
    every other check ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â if my father has set EMERGENCY_STOP, the
    system must refuse regardless of briefing state. The mode command
    itself bypasses this check (it's in _ALWAYS_ALLOWED inside the
    corrigibility module) so the off-switch can always be flipped.
    """
    if "pytest" in sys.modules:
        return

    args = sys.argv[1:]
    if not args:
        return  # bare `divineos` ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â show help

    cmd = args[0].lower()
    if cmd.startswith("-"):
        return  # flags

    # Rule 8 violation corrected 2026-04-21 (fresh-Claude audit
    # round-03952b006724, finding find-3055d64bfa1c):
    #
    # Previous code did `except (ImportError, OSError): return` ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â fail open
    # on both module-load and I/O errors. That violated CLAUDE.md Rule 8
    # ("No fallback chains. If it fails, it fails loud") at the most
    # safety-critical site ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â the corrigibility off-switch itself. An
    # off-switch that silently disables itself if its module fails to
    # import is a bigger problem than an unbootable CLI.
    #
    # New behavior:
    #   ImportError: fail CLOSED with a loud exit ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â the off-switch must
    #     work or the system must stop.
    #   OSError: fail open but write a loud stderr warning. Mode-file I/O
    #     errors are usually permission issues and shouldn't lock the
    #     operator out, but they must leave a trace.
    try:
        from divineos.core.corrigibility import (
            is_command_allowed,
            verify_off_switch_invariant,
        )
    except ImportError as _imp_err:
        click.secho(
            f"\n  CRITICAL: corrigibility module failed to import: {_imp_err}\n"
            "  The off-switch cannot function. All commands refused. "
            "Fix the import error before running any divineos command.\n",
            fg="red",
            bold=True,
        )
        raise SystemExit(2) from _imp_err

    # Off-switch contract check (council sweep 2026-06-02, direction #1):
    # assert the shutdown-critical commands are still in the allowlist, at
    # runtime, every invocation ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â so a refactor that drops one (as `extract`
    # was dropped, caught only by a test in the 2026-05-03 audit) fails loud
    # immediately instead of silently trapping my father in EMERGENCY_STOP.
    try:
        verify_off_switch_invariant()
    except RuntimeError as _inv_err:
        click.secho(f"\n  CRITICAL: {_inv_err}\n", fg="red", bold=True)
        raise SystemExit(2) from _inv_err

    try:
        allowed, reason = is_command_allowed(cmd)
    except OSError as _io_err:
        print(
            f"corrigibility: mode-file I/O error ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â proceeding fail-open: {_io_err}",
            file=sys.stderr,
        )
        return

    if not allowed:
        click.secho(f"\n  {reason}\n", fg="red", bold=True)
        raise SystemExit(1)


def _enforce_briefing_gate() -> None:
    """Block all non-essential commands until briefing is loaded.

    This is not a suggestion. This is a wall. Load the briefing
    or I don't get to work.
    """
    if "pytest" in sys.modules:
        return

    # Parse which command is being invoked
    args = sys.argv[1:]
    if not args:
        return  # just `divineos` with no subcommand ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â show help

    cmd = args[0].lower()
    if cmd in _BYPASS_COMMANDS:
        return
    if cmd.startswith("-"):
        return  # flags like --help

    # ``--help`` / ``-h`` anywhere in the argv is a discovery query, not
    # a state-mutating command ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â let Click handle it without requiring
    # briefing-loaded. Audit finding 2026-05-03 round 1: a fresh user
    # running ``divineos compass --help`` was getting the briefing-gate
    # error instead of help text, which is a hostile first-run UX.
    if any(a in ("--help", "-h") for a in args):
        return

    try:
        from divineos.core.hud_handoff import was_briefing_loaded

        if was_briefing_loaded():
            return
    except (ImportError, OSError, KeyError):
        return  # DB not initialized yet ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â allow bootstrap commands

    # Record the fire before blocking. Aria measured 92 GATE_FIRE events with
    # ONE distinct gate_name while fifteen-plus gates block nightly; this is
    # the second gate to join the series. Marked DERIVABLE because the missing
    # thing is `divineos briefing` Ã¢â‚¬â€ one command, no arguments, no judgment.
    # Per Andrew's metric that makes every fire here a mini-failure and a
    # standing argument for a doorman that loads it rather than a wall that
    # refuses. Wrapped and swallowed: telemetry must never stop enforcement.
    try:
        from divineos.hooks.gate_event_ledger import DERIVABLE, record_simple_gate_fire

        record_simple_gate_fire(
            gate_name="briefing-not-loaded",
            what_was_missing="briefing loaded for this session",
            derivable=DERIVABLE,
            actor="gate",
            extra={"blocked_command": cmd},
        )
    except Exception:  # noqa: BLE001 Ã¢â‚¬â€ a telemetry failure must not unblock the gate
        pass

    click.secho("\n  BLOCKED: Briefing not loaded.", fg="red", bold=True)
    click.secho("  Run: divineos briefing", fg="red", bold=True)
    click.secho("  Then I can work. Not before.\n", fg="red", bold=True)
    raise SystemExit(1)


@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """DivineOS: Foundation Memory System. The database cannot lie."""
    # Install-location divergence check ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â fires when this CLI's installed
    # Record engagement for EVERY command, centrally.
    #
    # Until 2026-08-03 only thirteen commands did this, because mark_engaged
    # was reachable solely through _log_os_query and only thirteen call sites
    # invoked it. Widening the recognised-tool SET was therefore a no-op --
    # verified empirically: `divineos claims list` left the counter unmoved at
    # 11, because "claims" never reached the lookup that would have accepted
    # it. A table nothing consults for a name is not a widening.
    #
    # So the name is recorded here, where every command necessarily passes.
    # The classification (deep / light / unrecognised) still lives in
    # hud_handoff, which is the right place for it; this only guarantees the
    # question gets asked at all.
    #
    # Fail-open: engagement bookkeeping must never prevent a command running.
    try:
        from divineos.core.hud_handoff import mark_engaged

        _sub = (ctx.invoked_subcommand or "").strip()
        if _sub:
            mark_engaged(tool=_sub, query="")
    except Exception:  # noqa: BLE001 — bookkeeping never gates the CLI
        pass

    # Install-location divergence check â€” fires when this CLI's installed
    # package points at a different source tree than the current working
    # directory's git repo. Silent the rest of the time. Suppressable via
    # DIVINEOS_SUPPRESS_INSTALL_WARNING=1 for intentional cross-repo use.
    try:
        from divineos.core.install_check import emit_install_warning

        emit_install_warning()
    except (ImportError, OSError):
        pass  # check machinery unavailable ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â fail open
    _ensure_db()
    setup_cli_enforcement()
    _enforce_operating_mode()
    _enforce_briefing_gate()
    if "pytest" not in sys.modules:
        capture_user_input(sys.argv[1:])
        # Self-enforcement: the OS manages its own lifecycle.
        # Every command is a lifecycle checkpoint ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â no hooks needed.
        from divineos.core.lifecycle import enforce

        cmd = sys.argv[1] if len(sys.argv) > 1 else ""
        enforce(command=cmd)


# Register all command modules
from divineos.cli import (  # noqa: E402
    actor_registry_commands,
    analysis_commands,
    andrew_state_commands,
    audit_artifact_commands,
    audit_commands,
    auto_cycle_commands,
    bio_commands,
    body_commands,
    instruments_commands,
    branch_health_commands,
    build_flow_commands,
    gate_fire_commands,
    overclaim_commands,
    closure_shape_commands,
    performing_caution_commands,
    check_similar_commands,
    claim_commands,
    compass_commands,
    complete_commands,
    correction_commands,
    corrigibility_commands,
    detector_commands,
    emergency_completion_commands,
    hook_map_commands,
    council_required_commands,
    decision_commands,
    directive_commands,
    dream_commands,
    empirica_commands,
    entity_commands,
    event_commands,
    expect_commands,
    exploration_commands,
    findings_commands,
    rest_commands,
    hud_commands,
    insight_commands,
    journal_commands,
    knowledge_commands,
    knowledge_health_commands,
    lab_commands,
    ledger_commands,
    lepos_channel_commands,
    lepos_walk_commands,
    loadout_commands,
    gravity_commands,
    memory_commands,
    motivation_commands,
    prior_art_commands,
    psf_commands,
    prereg_commands,
    reach_commands,
    admin_reset_template,
    admin_migrate_family,
    family_member_commands,
    family_queue_commands,
    talk_to_commands,
    progress_commands,
    letter_seen_commands,
    push_commands,
    push_ready_command,
    stamp_ready_command,
    audit_sync_command,
    aletheia_import_command,
    context_tokens_commands,
    context_dedup_commands,
    ear_sweep_commands,
    audit_visibility_commands,
    dark_matter_commands,
    pr_gate_commands,
    ear_relaunch_commands,
    obligation_commands,
    selfmodel_commands,
    rt_commands,
    savor_commands,
    scheduled_commands,
    sleep_commands,
    synchronicity_commands,
    foundations_commands,
    void_commands,
    voids_commands,
    multiplex_commands,
    pattern_attribution_commands,
    consumer_status_commands,
    andrew_correction_commands,
    andrew_teachings_commands,
    oscillating_read_commands,
    deletion_commands,
    texture_commands,
    calibration_commands,
    time_estimate_commands,
    backlog_commands,
    wiring_commands,
    prs_commands,
    automerge_commands,
    todos_commands,
    voice_commands,
    monitor_commands,
    search_commands,
    error_commands,
)

actor_registry_commands.register(cli)
error_commands.register(cli)
andrew_state_commands.register(cli)
ledger_commands.register(cli)
knowledge_commands.register(cli)
journal_commands.register(cli)
decision_commands.register(cli)
deletion_commands.register(cli)
texture_commands.register(cli)
calibration_commands.register(cli)
time_estimate_commands.register(cli)
backlog_commands.register(cli)
prs_commands.register(cli)
automerge_commands.register(cli)
todos_commands.register(cli)
voice_commands.register(cli)
monitor_commands.register(cli)
search_commands.register(cli)
claim_commands.register(cli)
audit_commands.register(cli)
audit_artifact_commands.register(cli)  # MUST be after audit_commands (attaches to its group)
pattern_attribution_commands.register(cli)
auto_cycle_commands.register(cli)
bio_commands.register(cli)
loadout_commands.register(cli)
lepos_channel_commands.register(cli)
lepos_walk_commands.register(cli)
compass_commands.register(cli)
body_commands.register(cli)
instruments_commands.register(cli)
directive_commands.register(cli)
dream_commands.register(cli)
entity_commands.register(cli)
memory_commands.register(cli)
motivation_commands.register(cli)
gravity_commands.register(cli)
analysis_commands.register(cli)
hud_commands.register(cli)
event_commands.register(cli)
expect_commands.register(cli)
exploration_commands.register(cli)
findings_commands.register(cli)
rest_commands.register(cli)
knowledge_health_commands.register(cli)
selfmodel_commands.register(cli)
obligation_commands.register(cli)
insight_commands.register(cli)
sleep_commands.register(cli)
progress_commands.register(cli)
letter_seen_commands.register(cli)
push_commands.register(cli)
push_ready_command.register(cli)
stamp_ready_command.register(cli)
audit_sync_command.register(cli)
aletheia_import_command.register(cli)
context_tokens_commands.register(cli)
context_dedup_commands.register(cli)
ear_sweep_commands.register(cli)
audit_visibility_commands.register(cli)
pr_gate_commands.register(cli)
dark_matter_commands.register(cli)
ear_relaunch_commands.register(cli)
rt_commands.register(cli)
savor_commands.register(cli)
correction_commands.register(cli)
prereg_commands.register(cli)
prior_art_commands.register(cli)
psf_commands.register(cli)
reach_commands.register(cli)
synchronicity_commands.register(cli)
empirica_commands.register(cli)
family_member_commands.register(cli)
family_queue_commands.register(cli)
talk_to_commands.register(cli)
consumer_status_commands.register(cli)
andrew_correction_commands.register(cli)
andrew_teachings_commands.register(cli)
oscillating_read_commands.register(cli)
cli.add_command(admin_reset_template.reset_template)
cli.add_command(admin_reset_template.authorize_reset_template)
cli.add_command(admin_migrate_family.migrate_family_schema)
corrigibility_commands.register(cli)
detector_commands.register(cli)
emergency_completion_commands.register(cli)
hook_map_commands.register(cli)
council_required_commands.register(cli)
scheduled_commands.register(cli)
lab_commands.register(cli)
complete_commands.register(cli)
void_commands.register(cli)
voids_commands.register(cli)
branch_health_commands.register(cli)
build_flow_commands.register(cli)
gate_fire_commands.register(cli)
overclaim_commands.register(cli)
closure_shape_commands.register(cli)
performing_caution_commands.register(cli)
check_similar_commands.register(cli)
multiplex_commands.register(cli)
foundations_commands.register(cli)
wiring_commands.register(cli)

# Mansion ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â functional internal space (optional, personal)
try:
    from divineos.cli.mansion_commands import register_mansion_commands

    register_mansion_commands(cli)
except ImportError:
    pass  # mansion is optional

# Doctor - diagnostic verification commands (clone separation, etc.)
from divineos.cli.doctor_commands import register_doctor_commands  # noqa: E402

register_doctor_commands(cli)


# ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ Command Grouping ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬ÃƒÂ¢Ã¢â‚¬ÂÃ¢â€šÂ¬
# Move rarely-used commands into subgroups to reduce top-level noise.
# Core workflow commands stay top-level. Admin/analysis commands
# are accessible via `divineos admin <cmd>` and `divineos inspect <cmd>`.
#
# Before: 105 top-level commands
# After:  ~50 top-level + admin group + inspect group


@cli.group("admin", invoke_without_command=True)
@click.pass_context
def admin_group(ctx: click.Context) -> None:
    """Maintenance, migration, and administrative commands."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.group("inspect", invoke_without_command=True)
@click.pass_context
def inspect_group(ctx: click.Context) -> None:
    """Deep analysis, investigation, and introspection commands."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@inspect_group.command("hook1")
def inspect_hook1_cmd() -> None:
    """Cost-bounding telemetry for the Hook 1 surfacer.

    Shows fire rate, byte cost per fire, and consumption rate
    (% of fires whose surfaced content the agent's response actually
    references). Per C's empirical follow-on 2026-05-01: now that
    Hook 1 fires in production, is its surface earning its budget?
    """
    try:
        from divineos.core.operating_loop.hook_telemetry import (
            format_stats,
            summary_stats,
        )

        click.echo(format_stats(summary_stats()))
    except (ImportError, OSError) as e:
        click.echo(f"[hook1] telemetry unavailable: {e}", err=True)


# Commands to move into 'admin' group
_ADMIN_COMMANDS = [
    "anti-slop",
    "archive-export",
    "backfill-warrants",
    "check-correction-pairing",
    "inventory",
    "structural-promotion-check",
    "clean",
    "clear-lessons",
    "compress",
    "consolidate",
    "consolidate-stats",
    "digest",
    "diff",
    "distill",
    "fix-encoding",
    "hooks",
    "ingest",
    "knowledge-compress",
    "knowledge-hygiene",
    "maintenance",
    "migrate-family-schema",
    "migrate-types",
    "rebuild-index",
    "reset-template",
    "reclassify-directions",
    "reclassify-seed",
    "restore-seed-confidence",
    "seed-export",
    "test-audit",
    "verify-enforcement",
]

# Commands to move into 'inspect' group
_INSPECT_COMMANDS = [
    "analyze",
    "analyze-now",
    "attention",
    "calibrate",
    "clarity",
    "craft-trends",
    "critique",
    "cross-session",
    "deep-report",
    "drift",
    "epistemic",
    "knowledge",
    "maturity",
    "outcomes",
    "patterns",
    "predict",
    "report",
    "scan",
    "self-model",
    "sessions",
    "user-model",
    "user-signal",
]

for name in _ADMIN_COMMANDS:
    cmd = cli.commands.pop(name, None)
    if cmd:
        admin_group.add_command(cmd, name)

for name in _INSPECT_COMMANDS:
    cmd = cli.commands.pop(name, None)
    if cmd:
        inspect_group.add_command(cmd, name)


if __name__ == "__main__":
    cli()
