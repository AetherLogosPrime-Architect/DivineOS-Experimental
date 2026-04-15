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
        help="Session ID for SESSION_END (optional, uses current if not provided)",
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
        - SESSION_END: (no arguments needed, queries ledger for actual counts)
        """
        import json

        from divineos.event.event_emission import (
            emit_event,
            emit_session_end,
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

            elif event_type == "SESSION_END":
                # Capture session start BEFORE emitting — once the SESSION_END
                # event lands in the ledger, get_session_start_time() would
                # return its timestamp (the end, not the start).
                _pre_emit_start: float | None = None
                try:
                    from divineos.core.session_checkpoint import get_session_start_time

                    _pre_emit_start = get_session_start_time()
                except (ImportError, OSError):
                    pass

                event_id = emit_session_end(session_id=session_id or None)
                click.secho("[+] Event emitted: SESSION_END", fg="green")
                click.secho(f"    Event ID: {event_id}", fg="cyan")

                _run_session_end_pipeline(session_start_override=_pre_emit_start)

            elif event_type == "EXPLANATION":
                if not content:
                    click.secho("[-] EXPLANATION requires --content", fg="red")
                    sys.exit(1)
                event_id = emit_event(
                    "EXPLANATION",
                    {"content": content},
                    actor="assistant",
                    validate=False,
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
                    "    Supported types: USER_INPUT, ASSISTANT_OUTPUT, TOOL_CALL, TOOL_RESULT, SESSION_END, EXPLANATION",
                    fg="yellow",
                )
                sys.exit(1)

        except _EC_ERRORS as e:
            click.secho(f"[-] Error emitting event: {e}", fg="red")
            logger.exception("Event emission failed")
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
            row = conn.execute(
                "SELECT session_id FROM session_validation ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
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
