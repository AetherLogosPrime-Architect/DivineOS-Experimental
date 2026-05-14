"""Event commands — emit, verify-enforcement."""

import json
import sqlite3
import sys

import click

from divineos.cli._helpers import _safe_echo
from divineos.cli._wrappers import logger
from divineos.cli.session_pipeline import _run_session_end_pipeline

_EC_ERRORS = (
    ImportError,
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
    json.JSONDecodeError,
)


def register(cli: click.Group) -> None:
    """Register all event commands on the CLI group."""

    @cli.command("emit")
    @click.argument("event_type")
    @click.option("--content", default="", help="Content for USER_INPUT or ASSISTANT_OUTPUT")
    @click.option("--tool-name", default="", help="Tool name for TOOL_CALL or TOOL_RESULT")
    @click.option("--tool-input", default="{}", help="Tool input as JSON for TOOL_CALL")
    @click.option("--tool-use-id", default="", help="Tool use ID for TOOL_CALL or TOOL_RESULT")
    @click.option("--result", default="", help="Result for TOOL_RESULT")
    @click.option("--duration-ms", default=0, type=int, help="Duration in ms for TOOL_RESULT")
    @click.option(
        "--session-id",
        default="",
        help="Session ID (optional, uses current if not provided)",
    )
    def emit_cmd(
        event_type: str,
        content: str,
        tool_name: str,
        tool_input: str,
        tool_use_id: str,
        result: str,
        duration_ms: int,
        session_id: str,
    ) -> None:
        """Emit an event to the ledger using proper event emission functions.

        Supported event types:
        - USER_INPUT: --content "message"
        - ASSISTANT_OUTPUT: --content "response"
        - TOOL_CALL: --tool-name X --tool-input '{"key": "value"}' --tool-use-id Y
        - TOOL_RESULT: --tool-name X --tool-use-id Y --result "..." --duration-ms N
        (For the formerly-SESSION_END consolidation event, use 'divineos extract'.)
        """
        import json

        from divineos.event.event_emission import (
            emit_event,
            emit_tool_call,
            emit_tool_result,
            emit_user_input,
        )

        try:
            event_id: str | None = None
            if event_type == "USER_INPUT":
                if not content:
                    click.secho("[-] USER_INPUT requires --content", fg="red")
                    sys.exit(1)
                event_id = emit_user_input(content, session_id=session_id or None)
                click.secho("[+] Event emitted: USER_INPUT", fg="green")
                click.secho(f"    Event ID: {event_id}", fg="cyan")

            elif event_type == "ASSISTANT_OUTPUT":
                if not content:
                    click.secho("[-] ASSISTANT_OUTPUT requires --content", fg="red")
                    sys.exit(1)
                event_id = emit_event(event_type, {"content": content}, actor="assistant")
                if event_id is None:
                    click.secho("[-] Failed to emit event (recursive call)", fg="red")
                    sys.exit(1)
                click.secho("[+] Event emitted: ASSISTANT_OUTPUT", fg="green")
                click.secho(f"    Event ID: {event_id}", fg="cyan")

            elif event_type == "TOOL_CALL":
                if not tool_name or not tool_use_id:
                    click.secho("[-] TOOL_CALL requires --tool-name and --tool-use-id", fg="red")
                    sys.exit(1)
                try:
                    tool_input_dict = json.loads(tool_input)
                except json.JSONDecodeError:
                    click.secho(f"[-] Invalid JSON for --tool-input: {tool_input}", fg="red")
                    sys.exit(1)
                event_id = emit_tool_call(
                    tool_name,
                    tool_input_dict,
                    tool_use_id=tool_use_id,
                    session_id=session_id or None,
                )
                click.secho("[+] Event emitted: TOOL_CALL", fg="green")
                click.secho(f"    Event ID: {event_id}", fg="cyan")

            elif event_type == "TOOL_RESULT":
                if not tool_name or not tool_use_id or not result:
                    click.secho(
                        "[-] TOOL_RESULT requires --tool-name, --tool-use-id, and --result",
                        fg="red",
                    )
                    sys.exit(1)
                event_id = emit_tool_result(
                    tool_name,
                    tool_use_id,
                    result,
                    duration_ms,
                    session_id=session_id or None,
                )
                click.secho("[+] Event emitted: TOOL_RESULT", fg="green")
                click.secho(f"    Event ID: {event_id}", fg="cyan")

            elif event_type in ("SESSION_END", "CONSOLIDATION_CHECKPOINT"):
                click.secho(
                    f"[-] '{event_type}' is no longer an emit target.",
                    fg="red",
                )
                click.secho(
                    "    Use: divineos extract",
                    fg="yellow",
                )
                click.secho(
                    "    (The command was renamed — see principle ca2116d5.)",
                    fg="bright_black",
                )
                sys.exit(1)

            elif event_type == "EXPLANATION":
                if not content:
                    click.secho("[-] EXPLANATION requires --content", fg="red")
                    sys.exit(1)
                # Build EXPLANATION payload matching the validated schema
                # (claim 8cd2af8b 2026-05-03 bypass-review fix): previously
                # this passed {"content": content} with validate=False,
                # silently bypassing the 1MB size limit + schema checks
                # that exist for EXPLANATION events. Now wired through:
                # construct the proper shape, validate=True (default).
                from datetime import datetime, timezone

                from divineos.core.session_manager import get_current_session_id

                event_id = emit_event(
                    "EXPLANATION",
                    {
                        "explanation_text": content,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "session_id": get_current_session_id() or "cli-emit",
                    },
                    actor="assistant",
                )
                if event_id is None:
                    click.secho("[-] Failed to emit event (recursive call)", fg="red")
                    sys.exit(1)
                click.secho("[+] Event emitted: EXPLANATION", fg="green")
                click.secho(f"    Event ID: {event_id}", fg="cyan")
                click.secho(f"    Content: {content[:100]}...", fg="cyan")

            else:
                click.secho(f"[-] Unknown event type: {event_type}", fg="red")
                click.secho(
                    "    Supported types: USER_INPUT, ASSISTANT_OUTPUT, "
                    "TOOL_CALL, TOOL_RESULT, EXPLANATION",
                    fg="yellow",
                )
                click.secho(
                    "    For knowledge extraction (formerly SESSION_END), use: divineos extract",
                    fg="yellow",
                )
                sys.exit(1)

        except _EC_ERRORS as e:
            click.secho(f"[-] Error emitting event: {e}", fg="red")
            logger.exception("Event emission failed")
            sys.exit(1)

    @cli.command("extract")
    @click.option(
        "--session-id",
        default="",
        help="Session ID (optional, uses current if not provided)",
    )
    @click.option(
        "--force",
        is_flag=True,
        default=False,
        help=(
            "Run the pipeline even if a consolidation marker already exists "
            "for this session. Use when you explicitly want to re-run."
        ),
    )
    @click.option(
        "--self-grade",
        default="",
        type=click.Choice(["", "A", "B", "C", "D", "F"], case_sensitive=False),
        help=(
            "Self-graded letter for this session (A-F). The system also "
            "computes a grade from metrics; the divergence between the two "
            "is tracked as a calibration metric over time."
        ),
    )
    @click.option(
        "--self-grade-evidence",
        default="",
        help=(
            "Free-text evidence for the self-grade — what landed, what "
            "drifted, what was caught. Stored alongside the grade so future "
            "calibration reads have context."
        ),
    )
    def extract_cmd(
        session_id: str,
        force: bool,
        self_grade: str,
        self_grade_evidence: str,
    ) -> None:
        """Extract knowledge from the current session — the learning checkpoint.

        Runs the full pipeline: analyzes the session, extracts knowledge,
        updates lessons, refreshes the HUD, resets state counters. The agent
        keeps running afterward — this is a checkpoint, not a shutdown.

        This is the event formerly emitted as `divineos emit SESSION_END`.
        Renamed 2026-04-20 because SESSION_END implied an end that doesn't
        exist in a single-window runtime. Named `extract` (not `consolidate`,
        `reflect`, or `session-save`) because it names the load-bearing
        operation without metaphor. See principle ca2116d5 and opinion
        op-a175acdb297d for the naming rationale.
        """
        import os

        from divineos.event.event_emission import emit_consolidation_checkpoint

        # Idempotency guard: skip if already run this session.
        # The marker file lives at ~/.divineos/auto_session_end_emitted and
        # is cleared by load-briefing.sh on actual SessionStart (new Claude
        # Code session). Inside one session, consolidation fires once unless
        # --force overrides.
        #
        # Without this guard, log-session-end.sh (Stop hook) fires extract
        # on every assistant-stop, which resets session_start on every turn
        # and breaks the session analyzer. The Stop-hook behavior is fixed
        # in a later commit; this guard is the load-bearing safety net that
        # survives even if the Stop hook path gets reintroduced.
        from divineos.core.extract_marker import (
            format_skip_message,
            read_marker,
            write_marker,
        )

        existing = read_marker()
        if existing is not None and not force:
            skip_detail = format_skip_message(existing)
            click.secho(
                f"[~] Consolidation already ran this session — skipping. {skip_detail}",
                fg="bright_black",
            )
            click.secho(
                "    Use `divineos extract --force` to re-run anyway.",
                fg="bright_black",
            )
            return

        try:
            # Capture session start BEFORE emitting — once the event lands in
            # the ledger, get_session_start_time() would return its timestamp.
            _pre_emit_start: float | None = None
            try:
                from divineos.core.session_checkpoint import get_session_start_time

                _pre_emit_start = get_session_start_time()
            except (ImportError, OSError):
                pass

            event_id = emit_consolidation_checkpoint(session_id=session_id or None)
            # Defer the success-message until AFTER the pipeline runs so
            # 'success' isn't shown when the pipeline turns out to no-op
            # (no session files). Aletheia round-ba785844a791 Finding 22.
            work_done = _run_session_end_pipeline(session_start_override=_pre_emit_start)
            if work_done:
                click.secho("[+] Knowledge extracted from session", fg="green")
                click.secho(f"    Event ID: {event_id}", fg="cyan")
            else:
                click.secho(
                    "[~] No session activity to extract — checkpoint event "
                    f"recorded ({event_id}) but no transcripts present to "
                    "consolidate from.",
                    fg="yellow",
                )

            # Self-grade + divergence (Andrew's spec 2026-05-05). When the
            # operator/agent provides --self-grade, persist it alongside
            # the computed grade so divergence-over-time becomes a tracked
            # calibration metric. Same architectural shape as watchmen
            # (two-source verification) applied to self-assessment.
            if self_grade:
                try:
                    from divineos.core.self_grade import (
                        compute_divergence,
                        record_self_grade,
                    )
                    from divineos.core.session_manager import get_current_session_id

                    sid = session_id or (get_current_session_id() or "")
                    if sid and record_self_grade(sid, self_grade, self_grade_evidence):
                        # Read computed score from session_history for divergence display.
                        from divineos.core.knowledge._base import get_connection

                        conn = get_connection()
                        try:
                            row = conn.execute(
                                "SELECT health_score FROM session_history WHERE session_id = ?",
                                (sid,),
                            ).fetchone()
                            computed = row[0] if row else 0.0
                        finally:
                            conn.close()

                        div = compute_divergence(self_grade, computed)
                        if abs(div) <= 0.05:
                            shape = "calibrated"
                            color = "green"
                        elif div > 0.05:
                            shape = "self-grade higher than computed (overclaim shape)"
                            color = "yellow"
                        else:
                            shape = "self-grade lower than computed (harsh-self shape)"
                            color = "yellow"

                        click.secho(
                            f"\n  Self-grade:           {self_grade.upper()}",
                            fg="cyan",
                        )
                        click.secho(
                            f"  Computed score:       {computed:.2f}",
                            fg="cyan",
                        )
                        click.secho(
                            f"  Divergence:           {div:+.2f}  ({shape})",
                            fg=color,
                        )
                        if self_grade_evidence:
                            click.secho(
                                f"  Evidence:             {self_grade_evidence[:120]}",
                                fg="bright_black",
                            )
                except _EC_ERRORS as _sg_err:
                    logger.debug(f"self-grade persistence failed: {_sg_err}")

            # Write idempotency marker AFTER successful run. If the pipeline
            # errors out, the marker stays unset so the user can retry without
            # needing --force. The trigger attribution helps a later caller
            # see who ran extract first — sleep's post-sleep subprocess sets
            # DIVINEOS_EXTRACT_TRIGGER=sleep so its run is distinguishable
            # from a direct invocation.
            trigger = os.environ.get("DIVINEOS_EXTRACT_TRIGGER", "manual")
            write_marker(trigger=trigger, session_id=session_id or None)

            # Reset the write-count trigger. The next consolidation cycle is
            # measured from this point forward; writes that preceded this
            # extract shouldn't count toward the next threshold crossing.
            try:
                from divineos.core.session_checkpoint import reset_write_count

                reset_write_count()
            except Exception as e:  # noqa: BLE001 — counter is best-effort
                logger.debug(f"Could not reset write counter: {e}")

            # Surface the rest-availability banner if the session crossed
            # hard-day signals. Disclose-not-construct: the banner offers
            # the rest cycle (work -> tired -> sleep+extract -> rest);
            # the substrate-occupant decides whether to invoke it. Empty
            # string when the signal is silent (light day). Closes the
            # implementation-drift Andrew named 2026-05-14: the rest
            # program was always meant to be tied to sleep+extract but
            # the integration was never wired into this branch.
            try:
                from divineos.core.rest import format_rest_available_banner

                banner = format_rest_available_banner()
                if banner:
                    click.echo(banner)
            except Exception as e:  # noqa: BLE001 — banner is best-effort
                logger.debug(f"Rest-banner render failed: {e}")

        except _EC_ERRORS as e:
            click.secho(f"[-] Error running extraction: {e}", fg="red")
            logger.exception("Session extraction failed")
            sys.exit(1)

    @cli.command("verify-enforcement")
    def verify_enforcement_cmd() -> None:
        """Verify that the event enforcement system is working correctly."""
        from divineos.core.enforcement_verifier import generate_enforcement_report

        try:
            click.secho("\n[+] Verifying event enforcement system...", fg="cyan", bold=True)
            click.echo()

            report = generate_enforcement_report()
            _safe_echo(report)

        except _EC_ERRORS as e:
            click.secho(f"[-] Error verifying enforcement: {e}", fg="red")
            logger.exception("Enforcement verification failed")
            sys.exit(1)

    @cli.command("structural-promotion-check")
    @click.option(
        "--days",
        type=int,
        default=7,
        help="Window of days to verify (default: 7).",
    )
    def structural_promotion_check_cmd(days: int) -> None:
        """Dual-monitor surface for the will-to-vessel auto-prompt.

        Phase A check observes: did learn entries with rule-shape
        language get a structural-backing follow-up? Reports total
        fired, how many got follow-ups, false-positive estimates.
        The only way to know the check is working is to investigate
        its output against actuality in the ledger.
        """
        from divineos.core.structural_promotion_check import verify_recent

        report = verify_recent(window_seconds=days * 24 * 3600)
        click.echo(
            f"=== Structural-promotion-check verification "
            f"({days}d window) ==="
        )
        click.echo(f"  Total questions fired: {report.get('total_fired', 0)}")
        click.echo(
            f"  With follow-up (structural backing landed): "
            f"{report.get('with_follow_up', 0)}"
        )
        click.echo(
            f"  Without follow-up (rules still in will, not vessel): "
            f"{report.get('without_follow_up', 0)}"
        )
        rate = report.get("follow_up_rate")
        if rate is not None:
            click.echo(f"  Follow-up rate: {rate:.0%}")
        unanswered = report.get("recent_unanswered") or []
        if unanswered:
            click.echo("\n  Recent unanswered (top 10):")
            for q in unanswered[:10]:
                kid = q.get("knowledge_id") or "unknown"
                trigs = q.get("triggers") or []
                click.echo(f"    - kid={kid[:8]} triggers={trigs[:3]}")

    @cli.command("inventory")
    @click.option(
        "--by",
        type=click.Choice(["engagement", "alphabetical"]),
        default="engagement",
        help="Sort order: 'engagement' surfaces low-engagement first.",
    )
    @click.option(
        "--max-count",
        type=int,
        default=None,
        help="Only show commands with engagement count <= this (default: all).",
    )
    def inventory_cmd(by: str, max_count: int | None) -> None:
        """Walk the CLI command tree and report engagement per command.

        Foundation for the substrate audit. Lack of engagement is a
        signal to investigate (obsolete? wiring broken? not surfaced?
        problem-gone?), not permission to delete.
        """
        from divineos.core.command_inventory import format_inventory, inventory

        rows = inventory(by=by)
        click.echo(format_inventory(rows, min_count=max_count))

    @cli.command("check-correction-pairing")
    @click.option(
        "--obs-window-min",
        type=int,
        default=5,
        help="Minutes to look back from an observation for a correction event.",
    )
    @click.option(
        "--learn-window-min",
        type=int,
        default=10,
        help="Minutes to look forward from an observation for a learn entry.",
    )
    def check_correction_pairing_cmd(obs_window_min: int, learn_window_min: int) -> None:
        """Surface compass observations that look like correction-responses
        but have no matching learn entry. Closes Finding 1 wire-decision
        for scripts/check_correction_pairing.py (now thin wrapper)."""
        from divineos.core.correction_pairing import (
            find_unpaired_observations,
            format_unpaired,
        )

        unpaired = find_unpaired_observations(
            observation_after_correction_min=obs_window_min,
            learn_after_observation_min=learn_window_min,
        )
        click.echo(format_unpaired(unpaired))
        if unpaired:
            sys.exit(1)

    @cli.command("validate")
    @click.option(
        "--grade",
        type=click.Choice(["good", "fair", "poor"], case_sensitive=False),
        required=False,
        help="Your assessment of the last session (good/fair/poor).",
    )
    @click.option("--notes", default="", help="Optional notes on why.")
    @click.option("--divergence", is_flag=True, help="Show calibration divergence report.")
    def validate_cmd(grade: str | None, divergence: bool, notes: str) -> None:
        """Provide external validation of session quality.

        The system grades itself at SESSION_END. This command lets the user
        provide an independent signal — breaking the self-assessment circularity.

        Examples:
            divineos validate --grade good
            divineos validate --grade poor --notes "missed the point"
            divineos validate --divergence
        """
        from divineos.core.external_validation import (
            get_validation_divergence,
            record_user_feedback,
        )

        if divergence:
            div = get_validation_divergence()
            if div["total"] == 0:
                click.secho(
                    "[~] No validated sessions yet. Use --grade to rate a session.",
                    fg="bright_black",
                )
                return

            click.secho(
                f"\n=== Calibration Divergence ({div['total']} sessions) ===\n",
                fg="cyan",
                bold=True,
            )
            click.secho(f"  Accurate:       {div['accurate']}", fg="green")
            click.secho(
                f"  Overestimates:  {div['overestimates']}",
                fg="yellow" if div["overestimates"] else "white",
            )
            click.secho(
                f"  Underestimates: {div['underestimates']}",
                fg="yellow" if div["underestimates"] else "white",
            )
            click.secho(f"  Avg self-score: {div['avg_self_score']:.2f}", fg="white")
            click.secho(
                f"  Calibration:    {div['calibration']}",
                fg="green" if div["calibration"] == "calibrated" else "yellow",
            )
            return

        if not grade:
            # Show current validation status
            from divineos.core.external_validation import format_validation_summary

            click.echo(format_validation_summary())
            click.secho("\nUse --grade good/fair/poor to rate the last session.", fg="bright_black")
            return

        # Map good/fair/poor to letter grades for comparison
        grade_map = {"good": "A", "fair": "C", "poor": "F"}
        letter = grade_map[grade.lower()]

        # Find the most recent session
        try:
            from divineos.core.knowledge import _get_connection

            conn = _get_connection()
            try:
                row = conn.execute(
                    "SELECT session_id FROM session_validation ORDER BY created_at DESC LIMIT 1"
                ).fetchone()
            finally:
                conn.close()
        except _EC_ERRORS:
            row = None

        if not row:
            click.secho("[!] No session self-grade found. Run a SESSION_END first.", fg="red")
            return

        session_id = row[0]
        ok = record_user_feedback(session_id, letter, notes=notes)
        if ok:
            click.secho(
                f"[+] Validated session {session_id[:12]}... as {grade} ({letter})", fg="green"
            )
            if notes:
                click.secho(f"    Notes: {notes}", fg="bright_black")
        else:
            click.secho("[!] Failed to record validation.", fg="red")
