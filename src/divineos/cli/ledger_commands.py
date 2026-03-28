"""Ledger commands — init, ingest, verify, clean, export, diff, log, list, search, stats, context."""

import json
from pathlib import Path
from typing import Any

import click

from divineos.cli._helpers import (
    _log_os_query,
    _print_events,
    _role_to_event_type,
    _safe_echo,
)
from divineos.cli._wrappers import (
    _wrapped_clean_corrupted_events,
    _wrapped_count_events,
    _wrapped_export_to_markdown,
    _wrapped_get_events,
    _wrapped_get_recent_context,
    _wrapped_log_event,
    _wrapped_search_events,
    _wrapped_verify_all_events,
    init_db,
    init_feature_tables,
    init_quality_tables,
    logger,
    rebuild_fts_index,
)
from divineos.core.fidelity import create_manifest, create_receipt, reconcile
from divineos.core.memory import init_memory_tables
from divineos.core.parser import parse_jsonl, parse_markdown_chat


def register(cli: click.Group) -> None:
    """Register all ledger commands on the CLI group."""

    @cli.command()
    def init() -> None:
        """Initialize the SQLite database and tables."""
        from divineos.core.knowledge import init_knowledge_table

        logger.info("Initializing the event ledger database...")
        init_db()
        init_knowledge_table()
        init_quality_tables()
        init_feature_tables()
        init_memory_tables()
        count = rebuild_fts_index()
        click.secho("[+] Database initialized successfully.", fg="green", bold=True)
        click.secho(
            "[+] All tables ready: ledger, knowledge, quality checks, session features, personal memory.",
            fg="green",
        )
        if count > 0:
            click.secho(f"[+] Full-text search search index rebuilt ({count} entries).", fg="green")

    @cli.command()
    @click.argument("file_path", type=click.Path(exists=True))
    def ingest(file_path: str) -> None:
        """Parse and store a chat log file (JSONL or Markdown).

        Performs manifest-receipt reconciliation to verify data integrity.
        """
        path = Path(file_path)
        logger.info(f"Ingesting chat file: {path}")

        if path.suffix.lower() == ".jsonl":
            parse_result = parse_jsonl(path)
        elif path.suffix.lower() in (".md", ".markdown"):
            parse_result = parse_markdown_chat(path)
        else:
            click.secho(f"[-] Unsupported file type: {path.suffix}", fg="red")
            click.secho("    Supported: .jsonl, .md, .markdown", fg="yellow")
            return

        if parse_result.parse_errors:
            click.secho(f"[!] Parse warnings: {len(parse_result.parse_errors)}", fg="yellow")
            for err in parse_result.parse_errors[:5]:
                click.echo(f"    {err}")

        if not parse_result.messages:
            click.secho("[-] No messages found in file.", fg="red")
            return

        click.secho(
            f"[+] Parsed {parse_result.message_count} messages from {parse_result.source_file}",
            fg="cyan",
        )

        payloads = [msg.to_dict() for msg in parse_result.messages]
        manifest_data = [{"content": p.get("content", "")} for p in payloads]
        manifest = create_manifest(manifest_data)

        click.secho(
            f"[+] Manifest: {manifest.count} messages, {manifest.bytes_total} bytes", fg="cyan"
        )
        click.secho(f"    Hash: {manifest.content_hash}", fg="bright_black")

        stored_ids = []
        for msg, payload in zip(parse_result.messages, payloads, strict=False):
            event_type = _role_to_event_type(msg.role)
            event_id = _wrapped_log_event(event_type=event_type, actor=msg.role, payload=payload)
            stored_ids.append(event_id)

        click.secho(f"[+] Stored {len(stored_ids)} events to database.", fg="green")

        stored_events = _wrapped_get_recent_context(n=len(stored_ids))
        receipt = create_receipt(stored_events)

        click.secho(
            f"[+] Receipt: {receipt.count} messages, {receipt.bytes_total} bytes", fg="cyan"
        )
        click.secho(f"    Hash: {receipt.content_hash}", fg="bright_black")

        fidelity_result = reconcile(manifest, receipt)

        if fidelity_result.passed:
            click.secho("\n[+] FIDELITY CHECK: PASS", fg="green", bold=True)
            for check, passed in fidelity_result.checks.items():
                status = (
                    click.style("[OK]", fg="green") if passed else click.style("[FAIL]", fg="red")
                )
                click.echo(f"    {status} {check}")
        else:
            click.secho("\n[-] FIDELITY CHECK: FAIL", fg="red", bold=True)
            for err in fidelity_result.errors:
                click.secho(f"    ERROR: {err}", fg="red")
            for warn in fidelity_result.warnings:
                click.secho(f"    WARN: {warn}", fg="yellow")

    @cli.command()
    @click.option(
        "--skip-types",
        multiple=True,
        help="Event types to skip (e.g. --skip-types AGENT_PATTERN --skip-types TEST)",
    )
    @click.option(
        "--real-only",
        is_flag=True,
        default=False,
        help="Only verify real events (skip test-generated types like AGENT_PATTERN)",
    )
    def verify(skip_types: tuple[str, ...], real_only: bool) -> None:
        """Verify integrity of all stored events."""
        logger.debug("Running fidelity verification...")

        types_to_skip = list(skip_types)
        if real_only:
            types_to_skip.extend(
                [
                    "AGENT_PATTERN",
                    "AGENT_PATTERN_UPDATE",
                    "AGENT_DECISION",
                    "AGENT_LEARNING_AUDIT",
                    "AGENT_SESSION_END",
                    "AGENT_WORK",
                    "AGENT_CONTEXT_COMPRESSION",
                    "TEST",
                    "TEST_EVENT",
                ]
            )

        result = _wrapped_verify_all_events(skip_types=types_to_skip or None)

        click.secho("\n=== Fidelity Verification ===\n", fg="cyan", bold=True)
        click.echo(f"  Total events: {result['total']}")
        if result.get("skipped"):
            click.echo(f"  Skipped:      {result['skipped']}  (filtered types)")
            click.echo(f"  Checked:      {result['checked']}")
        click.echo(f"  Passed:       {result['passed']}")
        click.echo(f"  Failed:       {result['failed']}")

        if result["integrity"] == "PASS":
            click.secho("\n  INTEGRITY: PASS", fg="green", bold=True)
        else:
            click.secho("\n  INTEGRITY: FAIL", fg="red", bold=True)
            click.secho("\n  Failures:", fg="red")
            for failure in result["failures"][:10]:
                click.echo(f"    Event {failure['event_id'][:8]}...")
                click.echo(f"      Type:   {failure.get('type', 'unknown')}")
                click.echo(f"      Reason: {failure.get('reason', 'unknown')}")

    @cli.command()
    @click.option("--force", is_flag=True, help="Skip confirmation prompt")
    def clean(force: bool) -> None:
        """Remove corrupted events from the ledger."""
        from divineos.core.ledger import verify_all_events

        logger.info("Scanning for corrupted events...")
        result = verify_all_events()
        corrupted = result.get("failures", [])

        if not corrupted:
            click.secho("[+] No corrupted events found. Ledger is clean.", fg="green")
            return

        click.secho(f"\n[!] Found {len(corrupted)} corrupted events:", fg="yellow")
        for f in corrupted[:5]:
            click.echo(f"  - {f.get('event_id', '?')[:12]}  {f.get('reason', 'hash mismatch')}")
        if len(corrupted) > 5:
            click.echo(f"  ... and {len(corrupted) - 5} more")

        if not force:
            click.confirm("\nDelete these corrupted events?", abort=True)

        result = _wrapped_clean_corrupted_events()
        click.secho(f"[+] Removed {result['deleted_count']} corrupted events.", fg="green")
        click.echo("    Run 'divineos verify' to confirm ledger integrity.")

    @cli.command("export")
    @click.option("--format", "fmt", default="markdown", type=click.Choice(["markdown", "json"]))
    def export_cmd(fmt: str) -> None:
        """Export all events to markdown or JSON."""
        if fmt == "markdown":
            output = _wrapped_export_to_markdown()
            _safe_echo(output)
        else:
            events = _wrapped_get_events(limit=10000)
            click.echo(json.dumps(events, indent=2, default=str))

    @cli.command()
    @click.argument("original_file", type=click.Path(exists=True))
    def diff(original_file: str) -> None:
        """Compare original file to database export for round-trip verification."""
        path = Path(original_file)
        original_content = path.read_text(encoding="utf-8").strip()

        exported = _wrapped_export_to_markdown().strip()

        if original_content == exported:
            click.secho("[+] ROUND-TRIP: PASS", fg="green", bold=True)
            click.secho("    Original and exported content are identical.", fg="green")
        else:
            click.secho("[-] ROUND-TRIP: FAIL", fg="red", bold=True)
            click.secho("    Content differs between original and export.", fg="red")

            orig_lines = original_content.split("\n")
            exp_lines = exported.split("\n")
            click.echo(f"\n    Original: {len(orig_lines)} lines, {len(original_content)} bytes")
            click.echo(f"    Exported: {len(exp_lines)} lines, {len(exported)} bytes")

    @cli.command("log")
    @click.option(
        "--type",
        "event_type",
        required=True,
        help="Event type (e.g. USER_INPUT, TOOL_CALL)",
    )
    @click.option("--actor", required=True, help="Who triggered it (e.g. user, assistant, system)")
    @click.option("--content", required=True, help="The event content/message")
    def log_cmd(event_type: str, actor: str, content: str) -> None:
        """Append an event to the immutable ledger."""
        payload: dict[str, Any] = {"content": content}

        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                payload = parsed
        except (json.JSONDecodeError, TypeError):
            pass

        event_id = _wrapped_log_event(
            event_type=event_type.upper(),
            actor=actor.lower(),
            payload=payload,
        )
        logger.debug(f"Event logged: {event_type} by {actor}")
        click.secho(f"[+] Logged event: {event_id}", fg="green")

    @cli.command("list")
    @click.option("--limit", default=20, help="Number of events to show")
    @click.option("--offset", default=0, help="Skip this many events")
    @click.option("--type", "event_type", default=None, help="Filter by event type")
    @click.option("--actor", default=None, help="Filter by actor")
    def list_cmd(limit: int, offset: int, event_type: str, actor: str) -> None:
        """List events from the ledger."""
        events = _wrapped_get_events(limit=limit, offset=offset, event_type=event_type, actor=actor)

        if not events:
            click.secho("[-] No events found.", fg="yellow")
            return

        click.secho(f"\n=== Showing {len(events)} events ===\n", fg="cyan", bold=True)
        _print_events(events)

    @cli.command()
    @click.argument("keyword")
    @click.option("--limit", default=10, help="Max results")
    def search(keyword: str, limit: int) -> None:
        """Search the ledger for events matching KEYWORD."""
        if not keyword.strip():
            click.secho("[-] Please provide a search term.", fg="yellow")
            return
        logger.debug(f"Searching for: '{keyword}'")
        events = _wrapped_search_events(keyword=keyword, limit=limit)

        if not events:
            click.secho(f"[-] No events matching '{keyword}'.", fg="yellow")
            return

        click.secho(f"\n=== {len(events)} matches for '{keyword}' ===\n", fg="cyan", bold=True)
        _print_events(events, highlight=keyword)

    @cli.command()
    def stats() -> None:
        """Display event ledger statistics."""
        logger.debug("Fetching ledger statistics...")
        try:
            counts = _wrapped_count_events()
        except Exception as e:
            logger.error(f"Could not retrieve stats: {e}")
            click.secho(f"[-] Error: {e}", fg="red")
            return

        click.secho("\n=== Event Ledger Stats ===\n", fg="cyan", bold=True)
        click.secho(f"  Total events: {counts['total']}", fg="white", bold=True)

        if counts["by_type"]:
            click.secho("\n  By Type:", fg="cyan")
            for t, c in sorted(counts["by_type"].items()):
                click.echo(f"    {t}: {c}")

        if counts["by_actor"]:
            click.secho("\n  By Actor:", fg="cyan")
            for a, c in sorted(counts["by_actor"].items()):
                click.echo(f"    {a}: {c}")

        click.echo()

    @cli.command()
    @click.option("--n", "--limit", default=20, help="Number of recent events for context")
    def context(n: int) -> None:
        """Show the last N events (working memory context window)."""
        logger.debug(f"Building context from last {n} events...")
        events = _wrapped_get_recent_context(n=n)

        if not events:
            click.secho("[-] No events in ledger yet.", fg="yellow")
            return

        click.secho(f"\n=== Context Window (last {len(events)} events) ===\n", fg="cyan", bold=True)
        _print_events(events)
        _log_os_query("context", f"last {n} events")
