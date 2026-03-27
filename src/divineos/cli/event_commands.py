"""Event commands — emit, verify-enforcement."""

import sys

import click

from divineos.cli._helpers import _safe_echo
from divineos.cli._wrappers import logger
from divineos.cli.session_pipeline import _run_session_end_pipeline


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
                event_id = emit_session_end(session_id=session_id or None)
                click.secho("[+] Event emitted: SESSION_END", fg="green")
                click.secho(f"    Event ID: {event_id}", fg="cyan")

                _run_session_end_pipeline()

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

        except Exception as e:
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

        except Exception as e:
            click.secho(f"[-] Error verifying enforcement: {e}", fg="red")
            logger.exception("Enforcement verification failed")
            sys.exit(1)
