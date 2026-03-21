"""DivineOS CLI - Foundation Memory & Knowledge.

Commands for managing the event ledger, ingesting conversations,
verifying data integrity, and consolidating knowledge.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click


import divineos.analysis.session_analyzer as _analyzer_mod
from divineos.analysis.analysis import analyze_session, format_analysis_report, store_analysis
from divineos.analysis.quality_checks import init_quality_tables
from divineos.analysis.session_features import (
    get_cross_session_summary,
    init_feature_tables,
    run_all_features,
    store_features,
)
from divineos.core.consolidation import (
    KNOWLEDGE_TYPES,
    apply_session_feedback,
    clear_lessons,
    consolidate_related,
    deep_extract_knowledge,
    generate_briefing,
    get_knowledge,
    get_lesson_summary,
    get_lessons,
    health_check,
    init_knowledge_table,
    knowledge_health_report,
    knowledge_stats,
    migrate_knowledge_types,
    rebuild_fts_index,
    search_knowledge,
    store_knowledge,
    update_knowledge,
)
from divineos.core.enforcement import capture_user_input, setup_cli_enforcement
from divineos.core.fidelity import create_manifest, create_receipt, reconcile
from divineos.core.ledger import (
    clean_corrupted_events,
    count_events,
    export_to_markdown,
    get_events,
    get_recent_context,
    init_db,
    log_event,
    logger,
    search_events,
    verify_all_events,
)
from divineos.core.memory import (
    CORE_SLOTS,
    clear_core,
    format_core,
    format_recall,
    get_active_memory,
    init_memory_tables,
    promote_to_active,
    recall,
    refresh_active_memory,
    set_core,
)
from divineos.core.parser import parse_jsonl, parse_markdown_chat
from divineos.core.tool_wrapper import wrap_tool_execution


_EMOJI_MEANINGS: dict[str, str] = {
    "\U0001f614": "(upset)",
    "\U0001f622": "(crying)",
    "\U0001f62d": "(sobbing)",
    "\U0001f620": "(angry)",
    "\U0001f621": "(furious)",
    "\U0001f610": "(neutral)",
    "\U0001f642": "(smile)",
    "\U0001f600": "(grinning)",
    "\U0001f601": "(beaming)",
    "\U0001f603": "(happy)",
    "\U0001f604": "(laughing)",
    "\U0001f605": "(laughing nervously)",
    "\U0001f606": "(laughing hard)",
    "\U0001f609": "(wink)",
    "\U0001f60a": "(warm smile)",
    "\U0001f60d": "(heart eyes)",
    "\U0001f60e": "(cool)",
    "\U0001f60f": "(smirk)",
    "\U0001f612": "(unamused)",
    "\U0001f615": "(confused)",
    "\U0001f616": "(frustrated)",
    "\U0001f618": "(kiss)",
    "\U0001f61b": "(tongue out)",
    "\U0001f61c": "(playful wink)",
    "\U0001f61e": "(disappointed)",
    "\U0001f624": "(frustrated)",
    "\U0001f625": "(relieved)",
    "\U0001f629": "(weary)",
    "\U0001f62b": "(tired)",
    "\U0001f62e": "(surprised)",
    "\U0001f631": "(screaming)",
    "\U0001f633": "(flushed)",
    "\U0001f634": "(sleeping)",
    "\U0001f637": "(sick)",
    "\U0001f641": "(frown)",
    "\U0001f643": "(upside-down smile)",
    "\U0001f644": "(eye roll)",
    "\U0001f914": "(thinking)",
    "\U0001f917": "(hug)",
    "\U0001f923": "(rolling on floor laughing)",
    "\U0001f929": "(starstruck)",
    "\U0001f92f": "(mind blown)",
    "\U0001f970": "(adoring)",
    "\U0001f973": "(party)",
    "\U0001f97a": "(pleading)",
    "\U0001f44d": "(thumbs up)",
    "\U0001f44e": "(thumbs down)",
    "\U0001f44f": "(clapping)",
    "\U0001f389": "(celebration)",
    "\U0001f38a": "(confetti)",
    "\U0001f525": "(fire)",
    "\U0001f4af": "(100%)",
    "\u2764\ufe0f": "(love)",
    "\u2764": "(love)",
    "\U0001f499": "(blue heart)",
    "\U0001f49a": "(green heart)",
    "\U0001f49c": "(purple heart)",
    "\U0001f680": "(rocket)",
    "\u2705": "(checkmark)",
    "\u274c": "(X)",
    "\u26a0\ufe0f": "(warning)",
    "\u26a0": "(warning)",
}


def _safe_echo(text: str, **kwargs: Any) -> None:
    """click.echo that won't crash on Windows with Unicode characters.

    Translates emoji to their meanings (e.g. upset, happy) instead of
    replacing them with '?' — because context matters.
    """
    if os.name == "nt":
        for emoji, meaning in _EMOJI_MEANINGS.items():
            text = text.replace(emoji, meaning)
        text = text.encode("cp1252", errors="replace").decode("cp1252")
    click.echo(text, **kwargs)


def _auto_classify(content: str) -> str:
    """Auto-classify knowledge type from content text."""
    lower = content.lower()
    # Hard constraints
    if re.search(r"\b(never|always|must not|do not|don't|cannot|forbidden)\b", lower):
        return "BOUNDARY"
    # How-to / process
    if re.search(r"\b(step \d|how to|first.*then|process|workflow|procedure)\b", lower):
        return "PROCEDURE"
    # Preferences / directions
    if re.search(r"\b(use |prefer |default to |keep |avoid )\b", lower):
        return "DIRECTION"
    # Facts / data
    if re.search(r"\b(is located|version |database |path |file |count |total )\b", lower):
        return "FACT"
    # Observations about behavior
    if re.search(r"\b(noticed|found that|discovered|turns out|apparently)\b", lower):
        return "OBSERVATION"
    # Default to PRINCIPLE
    return "PRINCIPLE"


# Wrap critical tool calls for event capture
_wrapped_log_event = wrap_tool_execution("log_event", log_event)
_wrapped_get_events = wrap_tool_execution("get_events", get_events)
_wrapped_search_events = wrap_tool_execution("search_events", search_events)
_wrapped_count_events = wrap_tool_execution("count_events", count_events)
_wrapped_get_recent_context = wrap_tool_execution("get_recent_context", get_recent_context)
_wrapped_verify_all_events = wrap_tool_execution("verify_all_events", verify_all_events)
_wrapped_clean_corrupted_events = wrap_tool_execution(
    "clean_corrupted_events",
    clean_corrupted_events,
)
_wrapped_export_to_markdown = wrap_tool_execution("export_to_markdown", export_to_markdown)

# Wrap knowledge consolidation tools
_wrapped_store_knowledge = wrap_tool_execution("store_knowledge", store_knowledge)
_wrapped_get_knowledge = wrap_tool_execution("get_knowledge", get_knowledge)
_wrapped_update_knowledge = wrap_tool_execution("update_knowledge", update_knowledge)
_wrapped_generate_briefing = wrap_tool_execution("generate_briefing", generate_briefing)
_wrapped_knowledge_stats = wrap_tool_execution("knowledge_stats", knowledge_stats)
_wrapped_rebuild_fts_index = wrap_tool_execution("rebuild_fts_index", rebuild_fts_index)
_wrapped_get_lesson_summary = wrap_tool_execution("get_lesson_summary", get_lesson_summary)
_wrapped_get_lessons = wrap_tool_execution("get_lessons", get_lessons)
_wrapped_deep_extract_knowledge = wrap_tool_execution(
    "deep_extract_knowledge",
    deep_extract_knowledge,
)
_wrapped_consolidate_related = wrap_tool_execution("consolidate_related", consolidate_related)
_wrapped_apply_session_feedback = wrap_tool_execution(
    "apply_session_feedback",
    apply_session_feedback,
)
_wrapped_health_check = wrap_tool_execution("health_check", health_check)
_wrapped_knowledge_health_report = wrap_tool_execution(
    "knowledge_health_report",
    knowledge_health_report,
)
_wrapped_clear_lessons = wrap_tool_execution("clear_lessons", clear_lessons)
_wrapped_migrate_knowledge_types = wrap_tool_execution(
    "migrate_knowledge_types",
    migrate_knowledge_types,
)

# Wrap memory tools
_wrapped_set_core = wrap_tool_execution("set_core", set_core)
_wrapped_clear_core = wrap_tool_execution("clear_core", clear_core)
_wrapped_format_core = wrap_tool_execution("format_core", format_core)
_wrapped_promote_to_active = wrap_tool_execution("promote_to_active", promote_to_active)
_wrapped_get_active_memory = wrap_tool_execution("get_active_memory", get_active_memory)
_wrapped_refresh_active_memory = wrap_tool_execution("refresh_active_memory", refresh_active_memory)
_wrapped_recall = wrap_tool_execution("recall", recall)
_wrapped_format_recall = wrap_tool_execution("format_recall", format_recall)

# Wrap analysis tools
_wrapped_run_all_features = wrap_tool_execution("run_all_features", run_all_features)
_wrapped_store_features = wrap_tool_execution("store_features", store_features)
_wrapped_get_cross_session_summary = wrap_tool_execution(
    "get_cross_session_summary",
    get_cross_session_summary,
)


@click.group()
def cli() -> None:
    """DivineOS: Foundation Memory System. The database cannot lie."""
    # Setup CLI enforcement at startup
    setup_cli_enforcement()

    # Capture user input (command line arguments) - only in production
    if "pytest" not in sys.modules:
        capture_user_input(sys.argv[1:])


@cli.command()
def init() -> None:
    """Initialize the SQLite database and tables."""
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

    # Parse the file
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

    # Build payloads
    payloads = [msg.to_dict() for msg in parse_result.messages]

    # Create manifest BEFORE storing
    manifest_data = [{"content": p.get("content", "")} for p in payloads]
    manifest = create_manifest(manifest_data)

    click.secho(f"[+] Manifest: {manifest.count} messages, {manifest.bytes_total} bytes", fg="cyan")
    click.secho(f"    Hash: {manifest.content_hash}", fg="bright_black")

    # Store each message
    stored_ids = []
    for msg, payload in zip(parse_result.messages, payloads, strict=False):
        event_type = _role_to_event_type(msg.role)
        event_id = _wrapped_log_event(event_type=event_type, actor=msg.role, payload=payload)
        stored_ids.append(event_id)

    click.secho(f"[+] Stored {len(stored_ids)} events to database.", fg="green")

    # Create receipt AFTER storing
    stored_events = _wrapped_get_recent_context(n=len(stored_ids))
    receipt = create_receipt(stored_events)

    click.secho(f"[+] Receipt: {receipt.count} messages, {receipt.bytes_total} bytes", fg="cyan")
    click.secho(f"    Hash: {receipt.content_hash}", fg="bright_black")

    # Reconcile
    fidelity_result = reconcile(manifest, receipt)

    if fidelity_result.passed:
        click.secho("\n[+] FIDELITY CHECK: PASS", fg="green", bold=True)
        for check, passed in fidelity_result.checks.items():
            status = click.style("[OK]", fg="green") if passed else click.style("[FAIL]", fg="red")
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
    logger.info("Running fidelity verification...")

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
def clean() -> None:
    """Remove corrupted events from the ledger."""
    logger.info("Cleaning corrupted events from ledger...")

    result = _wrapped_clean_corrupted_events()

    click.secho("\n=== Ledger Cleanup ===\n", fg="cyan", bold=True)
    click.echo(f"  Deleted corrupted events: {result['deleted_count']}")

    if result["deleted_count"] > 0:
        click.secho(
            f"\n  Removed {result['deleted_count']} corrupted events",
            fg="green",
            bold=True,
        )
        click.echo("\n  Run 'divineos verify' to confirm ledger integrity")
    else:
        click.secho("\n  No corrupted events found", fg="green", bold=True)


@cli.command("export")
@click.option("--format", "fmt", default="markdown", type=click.Choice(["markdown", "json"]))
def export_cmd(fmt: str) -> None:
    """Export all events to markdown or JSON."""
    if fmt == "markdown":
        output = _wrapped_export_to_markdown()
        click.echo(output)
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
@click.option("--type", "event_type", required=True, help="Event type (e.g. USER_INPUT, TOOL_CALL)")
@click.option("--actor", required=True, help="Who triggered it (e.g. user, assistant, system)")
@click.option("--content", required=True, help="The event content/message")
def log_cmd(event_type: str, actor: str, content: str) -> None:
    """Append an event to the immutable ledger."""
    payload: dict[str, Any] = {"content": content}

    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            payload = parsed
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(
            f"Failed to parse content as JSON, using raw content: {e}",
            exc_info=True,
        )

    event_id = _wrapped_log_event(
        event_type=event_type.upper(),
        actor=actor.lower(),
        payload=payload,
    )
    logger.info(f"Event logged: {event_type} by {actor}")
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
    logger.info(f"Searching for: '{keyword}'")
    events = _wrapped_search_events(keyword=keyword, limit=limit)

    if not events:
        click.secho(f"[-] No events matching '{keyword}'.", fg="yellow")
        return

    click.secho(f"\n=== {len(events)} matches for '{keyword}' ===\n", fg="cyan", bold=True)
    _print_events(events, highlight=keyword)


@cli.command()
def stats() -> None:
    """Display event ledger statistics."""
    logger.info("Fetching ledger statistics...")
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
@click.option("--n", default=20, help="Number of recent events for context")
def context(n: int) -> None:
    """Show the last N events (working memory context window)."""
    logger.info(f"Building context from last {n} events...")
    events = _wrapped_get_recent_context(n=n)

    if not events:
        click.secho("[-] No events in ledger yet.", fg="yellow")
        return

    click.secho(f"\n=== Context Window (last {len(events)} events) ===\n", fg="cyan", bold=True)
    _print_events(events)


@cli.command()
@click.argument("text", required=False, default=None)
@click.option(
    "--type",
    "knowledge_type",
    required=False,
    default=None,
    type=click.Choice(sorted(KNOWLEDGE_TYPES), case_sensitive=False),
    help="Knowledge type (auto-detected if omitted)",
)
@click.option("--content", "content_opt", default=None, help="The knowledge to store")
@click.option("--confidence", default=1.0, type=float, help="Confidence 0.0-1.0")
@click.option("--tags", default="", help="Comma-separated tags")
@click.option("--source", default="", help="Comma-separated source event IDs")
def learn(
    text: str | None,
    knowledge_type: str | None,
    content_opt: str | None,
    confidence: float,
    tags: str,
    source: str,
) -> None:
    """Store a piece of knowledge extracted from experience.

    Content can be passed as a positional argument or via --content.
    Type is auto-detected from content if --type is omitted.
    Example: divineos learn "always read files before editing"
    """
    content = text or content_opt
    if not content:
        click.secho("[-] Content is required. Pass as argument or --content.", fg="red")
        raise SystemExit(1)

    if not knowledge_type:
        knowledge_type = _auto_classify(content)
        click.secho(f"[~] Auto-classified as: {knowledge_type}", fg="cyan")
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    source_list = [s.strip() for s in source.split(",") if s.strip()] if source else []

    kid = _wrapped_store_knowledge(
        knowledge_type=knowledge_type.upper(),
        content=content,
        confidence=confidence,
        source_events=source_list or None,
        tags=tag_list or None,
    )
    click.secho(f"[+] Stored knowledge: {kid}", fg="green")


@cli.command("knowledge")
@click.option(
    "--type",
    "knowledge_type",
    default=None,
    type=click.Choice(sorted(KNOWLEDGE_TYPES), case_sensitive=False),
    help="Filter by type",
)
@click.option("--min-confidence", default=0.0, type=float, help="Minimum confidence")
@click.option("--limit", default=20, type=int, help="Max results")
def knowledge_cmd(knowledge_type: str, min_confidence: float, limit: int) -> None:
    """List stored knowledge."""
    kt = knowledge_type.upper() if knowledge_type else None
    entries = _wrapped_get_knowledge(knowledge_type=kt, min_confidence=min_confidence, limit=limit)

    if not entries:
        click.secho("[-] No knowledge found.", fg="yellow")
        return

    click.secho(f"\n=== {len(entries)} knowledge entries ===\n", fg="cyan", bold=True)
    for entry in entries:
        color = {
            "BOUNDARY": "red",
            "PRINCIPLE": "yellow",
            "DIRECTION": "green",
            "PROCEDURE": "cyan",
            "FACT": "blue",
            "OBSERVATION": "bright_black",
            "EPISODE": "cyan",
            # Legacy
            "MISTAKE": "red",
            "PATTERN": "magenta",
            "PREFERENCE": "green",
        }.get(entry["knowledge_type"], "white")
        click.secho(f"  [{entry['confidence']:.2f}] ", fg="bright_black", nl=False)
        click.secho(f"{entry['knowledge_type']} ", fg=color, bold=True, nl=False)
        click.echo(entry["content"])
        if entry["tags"]:
            click.secho(f"         tags: {', '.join(entry['tags'])}", fg="bright_black")
        click.secho(
            f"         {entry['access_count']}x accessed | {entry['knowledge_id'][:8]}...",
            fg="bright_black",
        )
        click.echo()


@cli.command("ask")
@click.argument("query")
@click.option("--limit", default=10, type=int, help="Max results")
def ask_cmd(query: str, limit: int) -> None:
    """Search what the system knows about a topic.

    Uses full-text search with relevance ranking.
    Example: divineos ask "testing"
    """
    results = search_knowledge(query, limit=limit)

    if not results:
        click.secho(f"[-] Nothing found for '{query}'.", fg="yellow")
        return

    click.secho(f"\n=== {len(results)} results for '{query}' ===\n", fg="cyan", bold=True)
    for entry in results:
        color = {
            "BOUNDARY": "red",
            "PRINCIPLE": "yellow",
            "DIRECTION": "green",
            "PROCEDURE": "cyan",
            "FACT": "blue",
            "OBSERVATION": "bright_black",
            "EPISODE": "cyan",
        }.get(entry["knowledge_type"], "white")
        click.secho(f"  [{entry['confidence']:.2f}] ", fg="bright_black", nl=False)
        click.secho(f"{entry['knowledge_type']} ", fg=color, bold=True, nl=False)
        click.echo(entry["content"])
        click.secho(
            f"         {entry['access_count']}x accessed | {entry['knowledge_id'][:8]}...",
            fg="bright_black",
        )
        click.echo()


@cli.command("briefing")
@click.option("--max", "max_items", default=20, type=int, help="Max items in briefing")
@click.option("--types", default="", help="Comma-separated knowledge types to include")
@click.option("--topic", default="", help="Topic hint to boost relevant knowledge (e.g. 'testing')")
def briefing_cmd(max_items: int, types: str, topic: str) -> None:
    """Generate a session context briefing from stored knowledge."""
    type_list = [t.strip().upper() for t in types.split(",") if t.strip()] if types else None
    output = _wrapped_generate_briefing(
        max_items=max_items,
        include_types=type_list,
        context_hint=topic,
    )
    click.echo(output)


@cli.command("forget")
@click.argument("knowledge_id")
@click.option("--reason", required=True, help="Why this knowledge is being superseded")
def forget_cmd(knowledge_id: str, reason: str) -> None:
    """Supersede a knowledge entry (marks as removed, no replacement created)."""
    from divineos.core.consolidation import supersede_knowledge

    try:
        supersede_knowledge(knowledge_id, reason)
        click.secho(f"[+] Removed {knowledge_id[:8]}... ({reason})", fg="green")
    except ValueError as e:
        click.secho(f"[-] {e}", fg="red")


@cli.command("consolidate-stats")
def consolidate_stats_cmd() -> None:
    """Display knowledge consolidation statistics."""
    stats = _wrapped_knowledge_stats()

    click.secho("\n=== Knowledge Stats ===\n", fg="cyan", bold=True)
    click.secho(f"  Total knowledge: {stats['total']}", fg="white", bold=True)
    click.echo(f"  Avg confidence:  {stats['avg_confidence']}")

    if stats["by_type"]:
        click.secho("\n  By Type:", fg="cyan")
        for t, c in sorted(stats["by_type"].items()):
            click.echo(f"    {t}: {c}")

    if stats["most_accessed"]:
        click.secho("\n  Most Accessed:", fg="cyan")
        for item in stats["most_accessed"][:5]:
            click.echo(f"    [{item['access_count']}x] {item['content'][:60]}")

    # Effectiveness breakdown
    report = _wrapped_knowledge_health_report()
    if report["total"] > 0:
        click.secho("\n  Effectiveness:", fg="cyan")
        for status, count in sorted(report["by_status"].items()):
            click.echo(f"    {status:15s} {count}")

    click.echo()


@cli.command("rebuild-index")
def rebuild_index_cmd() -> None:
    """Rebuild the Full-text search full-text search index from existing knowledge."""
    count = _wrapped_rebuild_fts_index()
    if count > 0:
        click.secho(f"[+] Full-text search index rebuilt: {count} entries indexed.", fg="green")
    else:
        click.secho("[*] No knowledge entries to index.", fg="yellow")


@cli.command("lessons")
@click.option(
    "--status",
    default=None,
    type=click.Choice(["active", "improving", "resolved"]),
    help="Filter by lesson status",
)
def lessons_cmd(status: str) -> None:
    """Show the learning loop — tracked lessons from past sessions."""
    lessons = _wrapped_get_lessons(status=status)

    if not lessons:
        click.secho("[-] No lessons tracked yet.", fg="yellow")
        click.secho(
            "    Run 'divineos report <session.jsonl> --store' to start learning.",
            fg="bright_black",
        )
        return

    summary = _wrapped_get_lesson_summary()
    click.echo()
    click.echo(summary)
    click.echo()

    # Show details
    click.secho("=== Lesson Details ===\n", fg="cyan", bold=True)
    for lesson in lessons:
        status_color = {
            "active": "red",
            "improving": "yellow",
            "resolved": "green",
        }.get(lesson["status"], "white")

        click.secho(f"  {lesson['status'].upper()} ", fg=status_color, bold=True, nl=False)
        click.secho(f"({lesson['occurrences']}x) ", fg="bright_black", nl=False)
        click.echo(lesson["description"][:80])
        agent = lesson.get("agent", "unknown")
        agent_str = f" | agent: {agent}" if agent != "unknown" else ""
        click.secho(
            f"         category: {lesson['category']} | sessions: {len(lesson['sessions'])}{agent_str}",
            fg="bright_black",
        )
        click.echo()


@cli.command("clear-lessons")
def clear_lessons_cmd() -> None:
    """Wipe all lessons from lesson_tracking (for re-extraction after fixes)."""
    count = _wrapped_clear_lessons()
    if count:
        click.secho(f"[+] Cleared {count} lessons.", fg="green")
    else:
        click.secho("[*] No lessons to clear.", fg="yellow")


@cli.command("consolidate")
@click.option("--min-cluster", default=2, type=int, help="Minimum entries to form a cluster")
def consolidate_cmd(min_cluster: int) -> None:
    """Merge related knowledge entries into consolidated ones."""
    merges = _wrapped_consolidate_related(min_cluster_size=min_cluster)

    if not merges:
        click.secho("[*] No clusters found to consolidate.", fg="yellow")
        click.secho(
            f"    Need at least {min_cluster} similar entries of the same type.", fg="bright_black"
        )
        return

    click.secho(f"\n[+] Consolidated {len(merges)} clusters:\n", fg="green", bold=True)
    for merge in merges:
        click.secho(f"  {merge['type']} ", fg="cyan", bold=True, nl=False)
        click.secho(f"({merge['merged_count']} entries merged) ", fg="bright_black", nl=False)
        click.echo(merge["content"])
    click.echo()


@cli.command("health")
def health_cmd() -> None:
    """Run knowledge health check — boost confirmed, escalate recurring, resolve old."""
    result = _wrapped_health_check()

    click.secho("\n=== Knowledge Health Check ===\n", fg="cyan", bold=True)
    click.secho(f"  Entries checked:        {result['total_checked']}", fg="white")
    click.secho(
        f"  Confirmed boosted:      {result['confirmed_boosted']}",
        fg="green" if result["confirmed_boosted"] else "bright_black",
    )
    click.secho(
        f"  Recurring escalated:    {result['recurring_escalated']}",
        fg="red" if result["recurring_escalated"] else "bright_black",
    )
    click.secho(
        f"  Lessons resolved:       {result['resolved_lessons']}",
        fg="green" if result["resolved_lessons"] else "bright_black",
    )

    # Show effectiveness breakdown
    report = _wrapped_knowledge_health_report()
    if report["total"] > 0:
        click.secho("\n  Effectiveness breakdown:", fg="white")
        for status, count in sorted(report["by_status"].items()):
            click.secho(f"    {status:15s} {count}", fg="bright_black")
    click.echo()


@cli.command("sessions")
def sessions_cmd() -> None:
    """Find and list all Claude Code session files."""
    sessions = _analyzer_mod.find_sessions()
    if not sessions:
        click.secho("[-] No session files found.", fg="yellow")
        return

    click.secho(f"\n=== {len(sessions)} Session Files ===\n", fg="cyan", bold=True)
    for s in sessions:
        size_mb = s.stat().st_size / (1024 * 1024)
        click.secho(f"  {size_mb:.1f}MB ", fg="bright_black", nl=False)
        click.secho(f"{s.stem[:12]}...", fg="white", bold=True, nl=False)
        click.secho(f"  {s.parent.name[:40]}", fg="cyan")
    click.echo()
    click.secho("  Tip: use full path with scan/deep-report commands:", fg="bright_black")
    click.secho(f'    divineos scan "{sessions[0]}"', fg="bright_black")


@cli.command("scan")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--store/--no-store", default=False, help="Store findings in knowledge DB")
@click.option(
    "--deep/--no-deep",
    default=True,
    help="Use deep extraction (correction pairs, preferences, topics)",
)
def scan_cmd(file_path: str, store: bool, deep: bool) -> None:
    """Deep-scan a session and extract knowledge into the consolidation store."""
    path = Path(file_path)
    analysis = _analyzer_mod.analyze_session(path)

    click.echo(analysis.summary())

    if not store:
        click.secho("  (Use --store to save findings to knowledge DB)", fg="bright_black")
        return

    stored = 0

    if deep:
        # Deep extraction: correction pairs, preferences, decisions with context, topics
        records = _analyzer_mod._load_records(path)
        deep_ids = _wrapped_deep_extract_knowledge(analysis, records)
        stored += len(deep_ids)
        click.secho(f"[+] Deep extraction: {len(deep_ids)} knowledge entries", fg="cyan")
    else:
        # Legacy extraction (basic) — uses new types
        for c in analysis.corrections:
            lower = c.content.lower()
            is_boundary = any(w in lower for w in ("never", "always", "must", "don't", "do not"))
            _wrapped_store_knowledge(
                knowledge_type="BOUNDARY" if is_boundary else "PRINCIPLE",
                content=c.content[:300],
                confidence=0.8,
                source="CORRECTED",
                maturity="HYPOTHESIS",
                tags=["session-analysis", "correction"],
            )
            stored += 1

        for e in analysis.encouragements:
            _wrapped_store_knowledge(
                knowledge_type="PRINCIPLE",
                content=f"This approach works well: {e.content[:280]}",
                confidence=0.9,
                source="DEMONSTRATED",
                maturity="TESTED",
                tags=["session-analysis", "encouragement"],
            )
            stored += 1

        for d in analysis.decisions:
            _wrapped_store_knowledge(
                knowledge_type="DIRECTION",
                content=d.content[:300],
                confidence=0.9,
                source="STATED",
                maturity="CONFIRMED",
                tags=["session-analysis", "decision"],
            )
            stored += 1

    # Store tool usage pattern as FACT (both modes)
    if analysis.tool_usage:
        top_tools = sorted(analysis.tool_usage.items(), key=lambda x: x[1], reverse=True)[:10]
        tool_summary = ", ".join(f"{n}:{c}" for n, c in top_tools)
        _wrapped_store_knowledge(
            knowledge_type="FACT",
            content=f"Session tool usage ({analysis.session_id[:12]}): {tool_summary}",
            confidence=1.0,
            tags=["session-analysis", "tool-usage"],
        )
        stored += 1

    # Store session summary as EPISODE
    _wrapped_store_knowledge(
        knowledge_type="EPISODE",
        content=(
            f"Session {analysis.session_id[:12]}: "
            f"{analysis.user_messages} user msgs, "
            f"{analysis.tool_calls_total} tool calls, "
            f"{len(analysis.corrections)} corrections, "
            f"{len(analysis.encouragements)} encouragements, "
            f"{len(getattr(analysis, 'preferences', []))} preferences, "
            f"{len(analysis.context_overflows)} overflows"
        ),
        confidence=1.0,
        tags=["session-analysis", "episode"],
    )
    stored += 1

    click.secho(f"\n[+] Stored {stored} knowledge entries from session.", fg="green")

    # Run feedback loop — compare new findings against existing knowledge
    feedback = _wrapped_apply_session_feedback(analysis, analysis.session_id)
    parts = []
    if feedback["recurrences_found"]:
        parts.append(f"{feedback['recurrences_found']} recurrences")
    if feedback["patterns_reinforced"]:
        parts.append(f"{feedback['patterns_reinforced']} patterns reinforced")
    if feedback["lessons_improving"]:
        parts.append(f"{feedback['lessons_improving']} lessons improving")
    if feedback.get("noise_skipped"):
        parts.append(f"{feedback['noise_skipped']} noise skipped")
    if parts:
        click.secho(f"[~] Feedback: {', '.join(parts)}", fg="cyan")


@cli.command("deep-report")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--store/--no-store", default=False, help="Store results in database")
def deep_report_cmd(file_path: str, store: bool) -> None:
    """Full session analysis: tone tracking, timeline, files, work/talk, errors."""
    init_feature_tables()
    path = Path(file_path)

    click.secho(f"[+] Deep analysis: {path.stem[:16]}...", fg="cyan")
    analysis = _wrapped_run_all_features(path)

    click.echo()
    _safe_echo(analysis.report_text)
    click.echo()
    click.secho(f"Evidence hash: {analysis.evidence_hash}", fg="bright_black")

    if store:
        _wrapped_store_features(analysis.session_id, analysis)
        click.secho("\n[+] Analysis stored in database.", fg="green")


@cli.command("patterns")
@click.option("--limit", default=10, type=int, help="Max sessions to compare")
def patterns_cmd(limit: int) -> None:
    """Compare quality check results across stored sessions."""
    output = _wrapped_get_cross_session_summary(limit=limit)
    click.echo()
    click.echo(output)
    click.echo()


@cli.command("core")
@click.argument("action", required=False, default="show")
@click.argument("slot", required=False)
@click.argument("content", required=False)
def core_cmd(action: str, slot: str | None, content: str | None) -> None:
    r"""Manage core memory slots.

    \b
    Usage:
      divineos core              Show all core memory
      divineos core set SLOT "text"  Set a slot
      divineos core clear SLOT   Clear a slot
      divineos core slots        List available slot names
    """
    init_memory_tables()

    if action == "show":
        text = _wrapped_format_core()
        if text:
            click.echo(text)
        else:
            click.secho("[-] No core memory set yet.", fg="yellow")
            click.secho(f"    Available slots: {', '.join(CORE_SLOTS)}", fg="bright_black")

    elif action == "slots":
        click.secho("\n=== Core Memory Slots ===\n", fg="cyan", bold=True)
        for s in CORE_SLOTS:
            click.echo(f"  {s}")
        click.echo()

    elif action == "set":
        if not slot or not content:
            click.secho('[-] Usage: divineos core set <slot> "<content>"', fg="red")
            return
        try:
            _wrapped_set_core(slot, content)
            click.secho(f"[+] Core memory '{slot}' updated.", fg="green")
        except ValueError as e:
            click.secho(f"[-] {e}", fg="red")

    elif action == "clear":
        if not slot:
            click.secho("[-] Usage: divineos core clear <slot>", fg="red")
            return
        try:
            if _wrapped_clear_core(slot):
                click.secho(f"[+] Cleared '{slot}'.", fg="green")
            else:
                click.secho(f"[*] '{slot}' was already empty.", fg="yellow")
        except ValueError as e:
            click.secho(f"[-] {e}", fg="red")

    else:
        click.secho(f"[-] Unknown action '{action}'. Use: show, set, clear, slots", fg="red")


@cli.command("recall")
@click.option("--topic", default="", help="Topic hint to boost relevant memories")
def recall_cmd(topic: str) -> None:
    """Show what the AI remembers right now — core + active + relevant."""
    init_memory_tables()
    result = _wrapped_recall(context_hint=topic)
    text = _wrapped_format_recall(result)
    click.echo(text)


@cli.command("active")
def active_cmd() -> None:
    """List active memory ranked by importance."""
    init_memory_tables()
    items = _wrapped_get_active_memory()

    if not items:
        click.secho("[-] No active memory yet.", fg="yellow")
        click.secho(
            "    Run 'divineos refresh' to auto-build from knowledge store.",
            fg="bright_black",
        )
        return

    click.secho(f"\n=== Active Memory ({len(items)} items) ===\n", fg="cyan", bold=True)
    for item in items:
        pin = click.style(" [pinned]", fg="yellow") if item["pinned"] else ""
        color = {
            "BOUNDARY": "red",
            "PRINCIPLE": "yellow",
            "DIRECTION": "green",
            "PROCEDURE": "cyan",
            "FACT": "blue",
            "OBSERVATION": "bright_black",
            "EPISODE": "cyan",
            "MISTAKE": "red",
            "PATTERN": "magenta",
            "PREFERENCE": "green",
        }.get(item["knowledge_type"], "white")
        click.secho(f"  [{item['importance']:.2f}] ", fg="bright_black", nl=False)
        click.secho(f"{item['knowledge_type']} ", fg=color, bold=True, nl=False)
        click.echo(f"{item['content'][:100]}{pin}")
        click.secho(
            f"         reason: {item['reason']} | surfaced: {item['surface_count']}x",
            fg="bright_black",
        )
        click.echo()


@cli.command("remember")
@click.argument("knowledge_id")
@click.option("--reason", default="manually promoted", help="Why this is important")
@click.option("--pin", is_flag=True, help="Pin this memory (cannot be auto-demoted)")
def remember_cmd(knowledge_id: str, reason: str, pin: bool) -> None:
    """Promote a knowledge entry to active memory."""
    init_memory_tables()
    try:
        mid = _wrapped_promote_to_active(knowledge_id, reason=reason, pinned=pin)
        pin_note = " [pinned]" if pin else ""
        click.secho(f"[+] Promoted to active memory: {mid}{pin_note}", fg="green")
    except Exception as e:
        click.secho(f"[-] {e}", fg="red")


@cli.command("refresh")
@click.option("--threshold", default=0.3, type=float, help="Importance threshold (0.0-1.0)")
def refresh_cmd(threshold: float) -> None:
    """Auto-rebuild active memory from the knowledge store."""
    init_memory_tables()
    result = _wrapped_refresh_active_memory(importance_threshold=threshold)
    click.secho("\n=== Memory Refresh ===\n", fg="cyan", bold=True)
    click.secho(
        f"  Promoted:  {result['promoted']}",
        fg="green" if result["promoted"] else "bright_black",
    )
    click.secho(f"  Kept:      {result['kept']}", fg="white")
    click.secho(
        f"  Demoted:   {result['demoted']}",
        fg="red" if result["demoted"] else "bright_black",
    )
    total = result["promoted"] + result["kept"]
    click.secho(f"\n  Active memory: {total} items", fg="white", bold=True)
    click.echo()


@cli.command("migrate-types")
@click.option("--execute", is_flag=True, help="Actually perform the migration (default is dry-run)")
def migrate_types_cmd(execute: bool) -> None:
    """Reclassify old knowledge types (MISTAKE/PATTERN/PREFERENCE) to new types."""
    init_knowledge_table()
    dry_run = not execute

    if dry_run:
        click.secho("\n=== Migration Preview (dry run) ===\n", fg="cyan", bold=True)
    else:
        click.secho("\n=== Migrating Knowledge Types ===\n", fg="yellow", bold=True)

    changes = _wrapped_migrate_knowledge_types(dry_run=dry_run)

    if not changes:
        click.secho("  No entries to migrate.", fg="bright_black")
        click.echo()
        return

    type_colors = {
        "BOUNDARY": "red",
        "PRINCIPLE": "yellow",
        "DIRECTION": "green",
        "PROCEDURE": "cyan",
        "FACT": "white",
        "OBSERVATION": "bright_black",
        "EPISODE": "bright_black",
    }

    for change in changes:
        old_color = "bright_black"
        new_color = type_colors.get(change["new_type"], "white")
        click.secho(f"  {change['old_type']}", fg=old_color, nl=False)
        click.echo(" -> ", nl=False)
        click.secho(f"{change['new_type']}", fg=new_color, nl=False)
        click.secho(f"  {change['content'][:80]}", fg="bright_black")

    click.echo()
    # Summary
    from collections import Counter

    by_new = Counter(c["new_type"] for c in changes)
    click.secho(f"  Total: {len(changes)} entries", fg="white", bold=True)
    for new_type, count in sorted(by_new.items()):
        color = type_colors.get(new_type, "white")
        click.secho(f"    {new_type}: {count}", fg=color)

    if dry_run:
        click.secho("\n  Run with --execute to apply these changes.", fg="bright_black")
    else:
        click.secho(f"\n  Migrated {len(changes)} entries.", fg="green", bold=True)
    click.echo()


def _role_to_event_type(role: str) -> str:
    """Convert message role to event type."""
    mapping = {
        "user": "USER_INPUT",
        "assistant": "ASSISTANT_OUTPUT",
        "system": "SYSTEM_PROMPT",
        "tool_call": "TOOL_CALL",
        "tool_result": "TOOL_RESULT",
    }
    return mapping.get(role.lower(), "MESSAGE")


def _print_events(events: list[dict[str, Any]], highlight: str | None = None) -> None:
    """Pretty-print a list of events with optional keyword highlighting."""
    for event in events:
        ts = event["timestamp"]
        try:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            time_str = str(ts)

        actor = event["actor"].upper()
        etype = event["event_type"]
        payload = event["payload"]
        content_hash = event.get("content_hash", "")[:8]

        click.secho(f"[{time_str}] ", fg="bright_black", nl=False)
        click.secho(f"{etype} ", fg="white", bold=True, nl=False)
        click.secho(f"({actor}) ", fg="bright_black", nl=False)
        click.secho(f"[{content_hash}]", fg="bright_black")

        content = payload.get("content")
        if content is None:
            content = json.dumps(payload, indent=2)
        if isinstance(content, (dict, list)):
            content = json.dumps(content, indent=2)
        # Truncate long payloads to keep output readable
        max_len = 500
        if len(content) > max_len:
            content = content[:max_len] + f"\n  ... ({len(content) - max_len} chars truncated)"

        if highlight:
            pattern = re.compile(re.escape(highlight), re.IGNORECASE)
            parts = pattern.split(content)
            matches = pattern.findall(content)
            for i, part in enumerate(parts):
                _safe_echo(part, nl=False)
                if i < len(matches):
                    click.secho(matches[i], fg="red", bold=True, nl=False)
            click.echo()
        else:
            color = {"USER": "blue", "ASSISTANT": "magenta", "SYSTEM": "yellow"}.get(actor, "white")
            _safe_echo(click.style(f"  {content}", fg=color))

        click.echo(click.style("-" * 60, fg="bright_black"))


if __name__ == "__main__":
    cli()


@cli.command("analyze")
@click.argument("file_path", type=click.Path(exists=True))
def analyze_cmd(file_path: str) -> None:
    """Analyze a session and generate a quality report.

    Runs all 7 quality checks + 10 session features on a JSONL file.
    Produces a plain-English report with findings and lessons.
    """
    from divineos.analysis.analysis import save_analysis_report

    path = Path(file_path)

    try:
        # Initialize database if needed
        init_db()
        init_knowledge_table()
        init_quality_tables()
        init_feature_tables()

        click.secho(f"\n[+] Analyzing session: {path.name}", fg="cyan", bold=True)

        # Analyze the session
        result = analyze_session(path)

        # Format the report
        report = format_analysis_report(result)

        # Display to user
        click.echo()
        click.echo(report)
        click.echo()

        # Store in database
        click.secho("[+] Storing analysis in database...", fg="cyan")
        try:
            stored = store_analysis(result, report)
            if stored:
                click.secho("[+] Analysis stored successfully.", fg="green")
        except Exception as e:
            click.secho(f"[!] Warning: Analysis storage failed: {e}", fg="yellow")
            logger.warning(f"Storage failed: {e}")

        # Save report to file
        report_file = save_analysis_report(result, report)
        click.secho(f"[+] Report saved to: {report_file}", fg="green")

        click.secho(f"[+] Analysis complete. Session ID: {result.session_id}", fg="green")
        click.echo()

    except FileNotFoundError as e:
        click.secho(f"[-] File not found: {e}", fg="red")
    except ValueError as e:
        click.secho(f"[-] Invalid session: {e}", fg="red")
    except Exception as e:
        click.secho(f"[-] Error during analysis: {e}", fg="red")
        logger.exception("Analysis failed")


@cli.command("analyze-now")
def analyze_now_cmd() -> None:
    """Analyze the current session from the ledger.

    This runs quality checks on the live session without needing a file.
    Useful for enforcement - run this to see what you're doing wrong right now.
    """
    from divineos.analysis.analysis import (
        analyze_session,
        export_current_session_to_jsonl,
        format_analysis_report,
        save_analysis_report,
        store_analysis,
    )

    try:
        # Initialize database
        init_db()
        init_knowledge_table()
        init_quality_tables()
        init_feature_tables()

        click.secho("\n[+] Exporting current session from ledger...", fg="cyan", bold=True)

        # Export current session
        session_file = export_current_session_to_jsonl(limit=200)

        click.secho("[+] Analyzing live session...", fg="cyan")

        # Analyze the session
        result = analyze_session(session_file)

        # Format the report
        report = format_analysis_report(result)

        # Display to user
        click.echo()
        click.echo(report)
        click.echo()

        # Store in database
        click.secho("[+] Storing analysis in database...", fg="cyan")
        try:
            stored = store_analysis(result, report)
            if stored:
                click.secho("[+] Analysis stored successfully.", fg="green")
        except Exception as e:
            click.secho(f"[!] Warning: Analysis storage failed: {e}", fg="yellow")
            logger.warning(f"Storage failed: {e}")

        # Save report to file
        report_file = save_analysis_report(result, report)
        click.secho(f"[+] Report saved to: {report_file}", fg="green")

        click.secho(f"[+] Analysis complete. Session ID: {result.session_id}", fg="green")
        click.echo()

    except ValueError as e:
        click.secho(f"[-] No session data: {e}", fg="red")
    except Exception as e:
        click.secho(f"[-] Error during analysis: {e}", fg="red")
        logger.exception("Analysis failed")


@cli.command("report")
@click.argument("session_id", required=False)
def report_cmd(session_id: str) -> None:
    """Display a stored analysis report.

    If no session_id provided, shows list of recent sessions.
    """
    from datetime import datetime

    from divineos.analysis.analysis import get_stored_report, list_recent_sessions

    try:
        if not session_id:
            # List recent sessions
            sessions = list_recent_sessions(limit=10)

            if not sessions:
                click.secho("\n[-] No analyzed sessions found yet.", fg="yellow")
                click.secho(
                    "    Run 'divineos analyze <file.jsonl>' to analyze a session.",
                    fg="bright_black",
                )
                click.echo()
                return

            click.secho("\n=== Recent Sessions ===\n", fg="cyan", bold=True)
            for i, session in enumerate(sessions, 1):
                click.secho(f"  {i}. {session['session_id']}", fg="white", bold=True)

                # Format timestamp
                try:
                    ts = datetime.fromtimestamp(session["created_at"]).strftime("%Y-%m-%d %H:%M:%S")
                    click.secho(f"     Time: {ts}", fg="bright_black")
                except Exception:
                    click.secho(f"     Time: {session['created_at']}", fg="bright_black")

                click.secho(f"     Files: {session['file_count']}", fg="bright_black")
                click.echo()

            click.secho("Usage: divineos report <session_id>", fg="bright_black")
            click.echo()
        else:
            # Retrieve specific report
            report = get_stored_report(session_id)

            if not report:
                click.secho(f"[-] Session not found: {session_id}", fg="red")
                return

            click.echo()
            # Use click.echo with default_text_stderr=False to handle UTF-8 properly
            try:
                click.echo(report)
            except UnicodeEncodeError:
                # Fallback: encode to ASCII with replacements
                click.echo(report.encode("ascii", errors="replace").decode("ascii"))
            click.echo()

    except Exception as e:
        click.secho(f"[-] Error retrieving report: {e}", fg="red")
        logger.exception("Report retrieval failed")


@cli.command("cross-session")
@click.option("--limit", default=10, type=int, help="Number of sessions to analyze")
def cross_session_cmd(limit: int) -> None:
    """Compare findings across multiple sessions.

    Shows trends and patterns in your performance over time.
    """
    from divineos.analysis.analysis import compute_cross_session_trends, format_cross_session_report

    try:
        click.secho(f"\n[+] Analyzing trends across last {limit} sessions...", fg="cyan")

        # Compute trends
        trends = compute_cross_session_trends(limit=limit)

        # Format report
        report = format_cross_session_report(trends)

        # Display
        click.echo()
        _safe_echo(report)
        click.echo()

    except Exception as e:
        click.secho(f"[-] Error during cross-session analysis: {e}", fg="red")
        logger.exception("Cross-session analysis failed")


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
    import sys

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
            # ASSISTANT_OUTPUT uses the generic emit_event for backward compatibility
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
            # SESSION_END queries ledger for actual counts
            event_id = emit_session_end(session_id=session_id or None)
            click.secho("[+] Event emitted: SESSION_END", fg="green")
            click.secho(f"    Event ID: {event_id}", fg="cyan")

            # Auto-scan the most recent session file and store findings
            session_files = _analyzer_mod.find_sessions()
            if session_files:
                latest = session_files[0]
                click.secho(f"\n[~] Auto-scanning session: {latest.stem[:16]}...", fg="cyan")
                try:
                    analysis = _analyzer_mod.analyze_session(latest)
                    click.echo(analysis.summary())

                    # Deep extract and store
                    records = _analyzer_mod._load_records(latest)
                    deep_ids = _wrapped_deep_extract_knowledge(analysis, records)
                    stored = len(deep_ids)

                    # Store tool usage and episode — skip if already stored
                    # (prevents duplicates from multiple SESSION_END emits)
                    session_tag = f"session-{analysis.session_id[:12]}"
                    existing = _wrapped_get_knowledge(
                        knowledge_type=None, min_confidence=0.0, limit=100
                    )
                    existing_tags = {tag for e in existing for tag in (e.get("tags") or [])}
                    has_session = session_tag in existing_tags

                    if analysis.tool_usage and not has_session:
                        top_tools = sorted(
                            analysis.tool_usage.items(), key=lambda x: x[1], reverse=True
                        )[:10]
                        tool_summary = ", ".join(f"{n}:{c}" for n, c in top_tools)
                        _wrapped_store_knowledge(
                            knowledge_type="FACT",
                            content=f"Session tool usage ({analysis.session_id[:12]}): {tool_summary}",
                            confidence=1.0,
                            tags=["session-analysis", "tool-usage", session_tag],
                        )
                        stored += 1

                    if not has_session:
                        _wrapped_store_knowledge(
                            knowledge_type="EPISODE",
                            content=(
                                f"Session {analysis.session_id[:12]}: "
                                f"{analysis.user_messages} user msgs, "
                                f"{analysis.tool_calls_total} tool calls, "
                                f"{len(analysis.corrections)} corrections, "
                                f"{len(analysis.encouragements)} encouragements, "
                                f"{len(getattr(analysis, 'preferences', []))} preferences, "
                                f"{len(analysis.context_overflows)} overflows"
                            ),
                            confidence=1.0,
                            tags=["session-analysis", "episode", session_tag],
                        )
                        stored += 1
                    elif has_session:
                        click.secho(
                            "[~] Session already scanned, skipping episode/fact.",
                            fg="bright_black",
                        )

                    click.secho(f"[+] Stored {stored} knowledge entries from session.", fg="green")

                    # Run feedback loop
                    feedback = _wrapped_apply_session_feedback(analysis, analysis.session_id)
                    parts = []
                    if feedback["recurrences_found"]:
                        parts.append(f"{feedback['recurrences_found']} recurrences")
                    if feedback["patterns_reinforced"]:
                        parts.append(f"{feedback['patterns_reinforced']} patterns reinforced")
                    if feedback["lessons_improving"]:
                        parts.append(f"{feedback['lessons_improving']} lessons improving")
                    if feedback.get("noise_skipped"):
                        parts.append(f"{feedback['noise_skipped']} noise skipped")
                    if parts:
                        click.secho(f"[~] Feedback: {', '.join(parts)}", fg="cyan")

                except Exception as e:
                    click.secho(f"[!] Auto-scan failed: {e}", fg="yellow")
                    logger.warning(f"Auto-scan failed: {e}")
            else:
                click.secho("[~] No session files found for auto-scan.", fg="bright_black")

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
    """Verify that the event enforcement system is working correctly.

    This command checks:
    - All event types are being captured
    - Event capture rates
    - Missing or orphaned events
    - Event hash integrity

    Use this to ensure the OS enforcement layer is functioning properly.
    """
    from divineos.core.enforcement_verifier import generate_enforcement_report

    try:
        click.secho("\n[+] Verifying event enforcement system...", fg="cyan", bold=True)
        click.echo()

        # Generate and display report
        report = generate_enforcement_report()
        click.echo(report)

    except Exception as e:
        click.secho(f"[-] Error verifying enforcement: {e}", fg="red")
        logger.exception("Enforcement verification failed")
        sys.exit(1)
