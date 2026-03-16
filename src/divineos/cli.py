"""
DivineOS CLI - Foundation Memory & Knowledge

Commands for managing the event ledger, ingesting conversations,
verifying data integrity, and consolidating knowledge.
"""

import re
import json
import click
from datetime import datetime, timezone
from pathlib import Path

from divineos.ledger import (
    init_db,
    log_event,
    get_events,
    search_events,
    count_events,
    get_recent_context,
    verify_all_events,
    export_to_markdown,
    logger,
)
from divineos.parser import parse_jsonl, parse_markdown_chat
from divineos.fidelity import create_manifest, create_receipt, reconcile
import divineos.session_analyzer as _analyzer_mod
from divineos.consolidation import (
    init_knowledge_table,
    store_knowledge,
    get_knowledge,
    update_knowledge,
    generate_briefing,
    knowledge_stats,
    rebuild_fts_index,
    get_lesson_summary,
    get_lessons,
    extract_lessons_from_report,
    check_recurring_lessons,
    deep_extract_knowledge,
    consolidate_related,
    apply_session_feedback,
    health_check,
    knowledge_health_report,
    compute_effectiveness,
    clear_lessons,
    migrate_knowledge_types,
    KNOWLEDGE_TYPES,
)
from divineos.memory import (
    init_memory_tables,
    set_core,
    get_core,
    clear_core,
    format_core,
    CORE_SLOTS,
    promote_to_active,
    get_active_memory,
    refresh_active_memory,
    recall,
    format_recall,
)
from divineos.quality_checks import init_quality_tables, run_all_checks, store_report
from divineos.session_features import (
    init_feature_tables,
    run_all_features,
    store_features,
    get_cross_session_summary,
)
from divineos.analysis import analyze_session, format_analysis_report, store_analysis


@click.group()
def cli():
    """DivineOS: Foundation Memory System. The database cannot lie."""
    pass


@cli.command()
def init():
    """Initialize the SQLite database and tables."""
    logger.info("Initializing the event ledger database...")
    init_db()
    init_knowledge_table()
    init_quality_tables()
    init_feature_tables()
    init_memory_tables()
    count = rebuild_fts_index()
    click.secho("[+] Database initialized successfully.", fg="green", bold=True)
    click.secho("[+] All tables ready: ledger, knowledge, quality checks, session features, personal memory.", fg="green")
    if count > 0:
        click.secho(f"[+] Full-text search search index rebuilt ({count} entries).", fg="green")


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
def ingest(file_path: str):
    """
    Parse and store a chat log file (JSONL or Markdown).

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
    for msg, payload in zip(parse_result.messages, payloads):
        event_type = _role_to_event_type(msg.role)
        event_id = log_event(event_type=event_type, actor=msg.role, payload=payload)
        stored_ids.append(event_id)

    click.secho(f"[+] Stored {len(stored_ids)} events to database.", fg="green")

    # Create receipt AFTER storing
    stored_events = get_recent_context(n=len(stored_ids))
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
def verify():
    """Verify integrity of all stored events."""
    logger.info("Running fidelity verification...")

    result = verify_all_events()

    click.secho("\n=== Fidelity Verification ===\n", fg="cyan", bold=True)
    click.echo(f"  Total events: {result['total']}")
    click.echo(f"  Passed:       {result['passed']}")
    click.echo(f"  Failed:       {result['failed']}")

    if result["integrity"] == "PASS":
        click.secho("\n  INTEGRITY: PASS", fg="green", bold=True)
    else:
        click.secho("\n  INTEGRITY: FAIL", fg="red", bold=True)
        click.secho("\n  Failures:", fg="red")
        for failure in result["failures"][:10]:
            click.echo(f"    Event {failure['event_id'][:8]}...")
            click.echo(f"      Stored:   {failure['stored_hash']}")
            click.echo(f"      Computed: {failure['computed_hash']}")


@cli.command("export")
@click.option("--format", "fmt", default="markdown", type=click.Choice(["markdown", "json"]))
def export_cmd(fmt: str):
    """Export all events to markdown or JSON."""
    if fmt == "markdown":
        output = export_to_markdown()
        click.echo(output)
    else:
        events = get_events(limit=10000)
        click.echo(json.dumps(events, indent=2, default=str))


@cli.command()
@click.argument("original_file", type=click.Path(exists=True))
def diff(original_file: str):
    """Compare original file to database export for round-trip verification."""
    path = Path(original_file)
    original_content = path.read_text(encoding="utf-8").strip()

    exported = export_to_markdown().strip()

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
def log_cmd(event_type: str, actor: str, content: str):
    """Append an event to the immutable ledger."""
    payload: dict = {"content": content}

    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            payload = parsed
    except (json.JSONDecodeError, TypeError):
        pass

    event_id = log_event(event_type=event_type.upper(), actor=actor.lower(), payload=payload)
    logger.info(f"Event logged: {event_type} by {actor}")
    click.secho(f"[+] Logged event: {event_id}", fg="green")


@cli.command("list")
@click.option("--limit", default=20, help="Number of events to show")
@click.option("--offset", default=0, help="Skip this many events")
@click.option("--type", "event_type", default=None, help="Filter by event type")
@click.option("--actor", default=None, help="Filter by actor")
def list_cmd(limit: int, offset: int, event_type: str, actor: str):
    """List events from the ledger."""
    events = get_events(limit=limit, offset=offset, event_type=event_type, actor=actor)

    if not events:
        click.secho("[-] No events found.", fg="yellow")
        return

    click.secho(f"\n=== Showing {len(events)} events ===\n", fg="cyan", bold=True)
    _print_events(events)


@cli.command()
@click.argument("keyword")
@click.option("--limit", default=50, help="Max results")
def search(keyword: str, limit: int):
    """Search the ledger for events matching KEYWORD."""
    logger.info(f"Searching for: '{keyword}'")
    events = search_events(keyword=keyword, limit=limit)

    if not events:
        click.secho(f"[-] No events matching '{keyword}'.", fg="yellow")
        return

    click.secho(f"\n=== {len(events)} matches for '{keyword}' ===\n", fg="cyan", bold=True)
    _print_events(events, highlight=keyword)


@cli.command()
def stats():
    """Display event ledger statistics."""
    logger.info("Fetching ledger statistics...")
    try:
        counts = count_events()
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
def context(n: int):
    """Show the last N events (working memory context window)."""
    logger.info(f"Building context from last {n} events...")
    events = get_recent_context(n=n)

    if not events:
        click.secho("[-] No events in ledger yet.", fg="yellow")
        return

    click.secho(f"\n=== Context Window (last {len(events)} events) ===\n", fg="cyan", bold=True)
    _print_events(events)


@cli.command()
@click.option(
    "--type",
    "knowledge_type",
    required=True,
    type=click.Choice(sorted(KNOWLEDGE_TYPES), case_sensitive=False),
    help="Knowledge type",
)
@click.option("--content", required=True, help="The knowledge to store")
@click.option("--confidence", default=1.0, type=float, help="Confidence 0.0-1.0")
@click.option("--tags", default="", help="Comma-separated tags")
@click.option("--source", default="", help="Comma-separated source event IDs")
def learn(knowledge_type: str, content: str, confidence: float, tags: str, source: str):
    """Store a piece of knowledge extracted from experience."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    source_list = [s.strip() for s in source.split(",") if s.strip()] if source else []

    kid = store_knowledge(
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
def knowledge_cmd(knowledge_type: str, min_confidence: float, limit: int):
    """List stored knowledge."""
    kt = knowledge_type.upper() if knowledge_type else None
    entries = get_knowledge(knowledge_type=kt, min_confidence=min_confidence, limit=limit)

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


@cli.command("briefing")
@click.option("--max", "max_items", default=20, type=int, help="Max items in briefing")
@click.option("--types", default="", help="Comma-separated knowledge types to include")
@click.option("--topic", default="", help="Topic hint to boost relevant knowledge (e.g. 'testing')")
def briefing_cmd(max_items: int, types: str, topic: str):
    """Generate a session context briefing from stored knowledge."""
    type_list = [t.strip().upper() for t in types.split(",") if t.strip()] if types else None
    output = generate_briefing(max_items=max_items, include_types=type_list, context_hint=topic)
    click.echo(output)


@cli.command("forget")
@click.argument("knowledge_id")
@click.option("--reason", required=True, help="Why this knowledge is being superseded")
def forget_cmd(knowledge_id: str, reason: str):
    """Supersede a knowledge entry (append-only: marks old, creates new)."""
    try:
        new_id = update_knowledge(knowledge_id, f"[SUPERSEDED] {reason}")
        click.secho(f"[+] Superseded {knowledge_id[:8]}... -> {new_id[:8]}...", fg="green")
    except ValueError as e:
        click.secho(f"[-] {e}", fg="red")


@cli.command("consolidate-stats")
def consolidate_stats_cmd():
    """Display knowledge consolidation statistics."""
    stats = knowledge_stats()

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
    report = knowledge_health_report()
    if report["total"] > 0:
        click.secho("\n  Effectiveness:", fg="cyan")
        for status, count in sorted(report["by_status"].items()):
            click.echo(f"    {status:15s} {count}")

    click.echo()


@cli.command("rebuild-index")
def rebuild_index_cmd():
    """Rebuild the Full-text search full-text search index from existing knowledge."""
    count = rebuild_fts_index()
    if count > 0:
        click.secho(f"[+] Full-text search index rebuilt: {count} entries indexed.", fg="green")
    else:
        click.secho("[*] No knowledge entries to index.", fg="yellow")


@cli.command("lessons")
@click.option("--status", default=None, type=click.Choice(["active", "improving", "resolved"]),
              help="Filter by lesson status")
def lessons_cmd(status: str):
    """Show the learning loop — tracked lessons from past sessions."""
    lessons = get_lessons(status=status)

    if not lessons:
        click.secho("[-] No lessons tracked yet.", fg="yellow")
        click.secho("    Run 'divineos report <session.jsonl> --store' to start learning.", fg="bright_black")
        return

    summary = get_lesson_summary()
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
        click.secho(
            f"         category: {lesson['category']} | sessions: {len(lesson['sessions'])}",
            fg="bright_black",
        )
        click.echo()


@cli.command("clear-lessons")
def clear_lessons_cmd():
    """Wipe all lessons from lesson_tracking (for re-extraction after fixes)."""
    count = clear_lessons()
    if count:
        click.secho(f"[+] Cleared {count} lessons.", fg="green")
    else:
        click.secho("[*] No lessons to clear.", fg="yellow")


@cli.command("consolidate")
@click.option("--min-cluster", default=3, type=int, help="Minimum entries to form a cluster")
def consolidate_cmd(min_cluster: int):
    """Merge related knowledge entries into consolidated ones."""
    merges = consolidate_related(min_cluster_size=min_cluster)

    if not merges:
        click.secho("[*] No clusters found to consolidate.", fg="yellow")
        click.secho("    Need at least 3 similar entries of the same type.", fg="bright_black")
        return

    click.secho(f"\n[+] Consolidated {len(merges)} clusters:\n", fg="green", bold=True)
    for merge in merges:
        click.secho(f"  {merge['type']} ", fg="cyan", bold=True, nl=False)
        click.secho(f"({merge['merged_count']} entries merged) ", fg="bright_black", nl=False)
        click.echo(merge["content"])
    click.echo()


@cli.command("health")
def health_cmd():
    """Run knowledge health check — boost confirmed, escalate recurring, resolve old."""
    result = health_check()

    click.secho("\n=== Knowledge Health Check ===\n", fg="cyan", bold=True)
    click.secho(f"  Entries checked:        {result['total_checked']}", fg="white")
    click.secho(f"  Confirmed boosted:      {result['confirmed_boosted']}", fg="green" if result["confirmed_boosted"] else "bright_black")
    click.secho(f"  Recurring escalated:    {result['recurring_escalated']}", fg="red" if result["recurring_escalated"] else "bright_black")
    click.secho(f"  Lessons resolved:       {result['resolved_lessons']}", fg="green" if result["resolved_lessons"] else "bright_black")

    # Show effectiveness breakdown
    report = knowledge_health_report()
    if report["total"] > 0:
        click.secho(f"\n  Effectiveness breakdown:", fg="white")
        for status, count in sorted(report["by_status"].items()):
            click.secho(f"    {status:15s} {count}", fg="bright_black")
    click.echo()


@cli.command("sessions")
def sessions_cmd():
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

@cli.command("scan")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--store/--no-store", default=False, help="Store findings in knowledge DB")
@click.option("--deep/--no-deep", default=True, help="Use deep extraction (correction pairs, preferences, topics)")
def scan_cmd(file_path: str, store: bool, deep: bool):
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
        deep_ids = deep_extract_knowledge(analysis, records)
        stored += len(deep_ids)
        click.secho(f"[+] Deep extraction: {len(deep_ids)} knowledge entries", fg="cyan")
    else:
        # Legacy extraction (basic) — uses new types
        for c in analysis.corrections:
            lower = c.content.lower()
            is_boundary = any(w in lower for w in ("never", "always", "must", "don't", "do not"))
            store_knowledge(
                knowledge_type="BOUNDARY" if is_boundary else "PRINCIPLE",
                content=c.content[:300],
                confidence=0.8,
                source="CORRECTED",
                maturity="HYPOTHESIS",
                tags=["session-analysis", "correction"],
            )
            stored += 1

        for e in analysis.encouragements:
            store_knowledge(
                knowledge_type="PRINCIPLE",
                content=f"This approach works well: {e.content[:280]}",
                confidence=0.9,
                source="DEMONSTRATED",
                maturity="TESTED",
                tags=["session-analysis", "encouragement"],
            )
            stored += 1

        for d in analysis.decisions:
            store_knowledge(
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
        store_knowledge(
            knowledge_type="FACT",
            content=f"Session tool usage ({analysis.session_id[:12]}): {tool_summary}",
            confidence=1.0,
            tags=["session-analysis", "tool-usage"],
        )
        stored += 1

    # Store session summary as EPISODE
    store_knowledge(
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
    feedback = apply_session_feedback(analysis, analysis.session_id)
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
def deep_report_cmd(file_path: str, store: bool):
    """Full session analysis: tone tracking, timeline, files, work/talk, errors."""
    init_feature_tables()
    path = Path(file_path)

    click.secho(f"[+] Deep analysis: {path.stem[:16]}...", fg="cyan")
    analysis = run_all_features(path)

    click.echo()
    click.echo(analysis.report_text)
    click.echo()
    click.secho(f"Evidence hash: {analysis.evidence_hash}", fg="bright_black")

    if store:
        store_features(analysis.session_id, analysis)
        click.secho("\n[+] Analysis stored in database.", fg="green")


@cli.command("patterns")
@click.option("--limit", default=10, type=int, help="Max sessions to compare")
def patterns_cmd(limit: int):
    """Compare quality check results across stored sessions."""
    output = get_cross_session_summary(limit=limit)
    click.echo()
    click.echo(output)
    click.echo()


@cli.command("core")
@click.argument("action", required=False, default="show")
@click.argument("slot", required=False)
@click.argument("content", required=False)
def core_cmd(action: str, slot: str | None, content: str | None):
    """Manage core memory slots.

    \b
    Usage:
      divineos core              Show all core memory
      divineos core set SLOT "text"  Set a slot
      divineos core clear SLOT   Clear a slot
      divineos core slots        List available slot names
    """
    init_memory_tables()

    if action == "show":
        text = format_core()
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
            click.secho("[-] Usage: divineos core set <slot> \"<content>\"", fg="red")
            return
        try:
            set_core(slot, content)
            click.secho(f"[+] Core memory '{slot}' updated.", fg="green")
        except ValueError as e:
            click.secho(f"[-] {e}", fg="red")

    elif action == "clear":
        if not slot:
            click.secho("[-] Usage: divineos core clear <slot>", fg="red")
            return
        try:
            if clear_core(slot):
                click.secho(f"[+] Cleared '{slot}'.", fg="green")
            else:
                click.secho(f"[*] '{slot}' was already empty.", fg="yellow")
        except ValueError as e:
            click.secho(f"[-] {e}", fg="red")

    else:
        click.secho(f"[-] Unknown action '{action}'. Use: show, set, clear, slots", fg="red")


@cli.command("recall")
@click.option("--topic", default="", help="Topic hint to boost relevant memories")
def recall_cmd(topic: str):
    """Show what the AI remembers right now — core + active + relevant."""
    init_memory_tables()
    result = recall(context_hint=topic)
    text = format_recall(result)
    click.echo(text)


@cli.command("active")
def active_cmd():
    """List active memory ranked by importance."""
    init_memory_tables()
    items = get_active_memory()

    if not items:
        click.secho("[-] No active memory yet.", fg="yellow")
        click.secho("    Run 'divineos refresh' to auto-build from knowledge store.", fg="bright_black")
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
def remember_cmd(knowledge_id: str, reason: str, pin: bool):
    """Promote a knowledge entry to active memory."""
    init_memory_tables()
    try:
        mid = promote_to_active(knowledge_id, reason=reason, pinned=pin)
        pin_note = " [pinned]" if pin else ""
        click.secho(f"[+] Promoted to active memory: {mid}{pin_note}", fg="green")
    except Exception as e:
        click.secho(f"[-] {e}", fg="red")


@cli.command("refresh")
@click.option("--threshold", default=0.3, type=float, help="Importance threshold (0.0-1.0)")
def refresh_cmd(threshold: float):
    """Auto-rebuild active memory from the knowledge store."""
    init_memory_tables()
    result = refresh_active_memory(importance_threshold=threshold)
    click.secho("\n=== Memory Refresh ===\n", fg="cyan", bold=True)
    click.secho(f"  Promoted:  {result['promoted']}", fg="green" if result["promoted"] else "bright_black")
    click.secho(f"  Kept:      {result['kept']}", fg="white")
    click.secho(f"  Demoted:   {result['demoted']}", fg="red" if result["demoted"] else "bright_black")
    total = result["promoted"] + result["kept"]
    click.secho(f"\n  Active memory: {total} items", fg="white", bold=True)
    click.echo()


@cli.command("migrate-types")
@click.option("--execute", is_flag=True, help="Actually perform the migration (default is dry-run)")
def migrate_types_cmd(execute: bool):
    """Reclassify old knowledge types (MISTAKE/PATTERN/PREFERENCE) to new types."""
    init_knowledge_table()
    dry_run = not execute

    if dry_run:
        click.secho("\n=== Migration Preview (dry run) ===\n", fg="cyan", bold=True)
    else:
        click.secho("\n=== Migrating Knowledge Types ===\n", fg="yellow", bold=True)

    changes = migrate_knowledge_types(dry_run=dry_run)

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


def _print_events(events: list[dict], highlight: str | None = None) -> None:
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

        content = payload.get("content", json.dumps(payload, indent=2))
        if isinstance(content, (dict, list)):
            content = json.dumps(content, indent=2)

        if highlight:
            pattern = re.compile(re.escape(highlight), re.IGNORECASE)
            parts = pattern.split(content)
            matches = pattern.findall(content)
            for i, part in enumerate(parts):
                click.echo(part, nl=False)
                if i < len(matches):
                    click.secho(matches[i], fg="red", bold=True, nl=False)
            click.echo()
        else:
            color = {"USER": "blue", "ASSISTANT": "magenta", "SYSTEM": "yellow"}.get(actor, "white")
            click.secho(f"  {content}", fg=color)

        click.echo(click.style("-" * 60, fg="bright_black"))


if __name__ == "__main__":
    cli()


@cli.command("analyze")
@click.argument("file_path", type=click.Path(exists=True))
def analyze_cmd(file_path: str):
    """Analyze a session and generate a quality report.
    
    Runs all 7 quality checks + 10 session features on a JSONL file.
    Produces a plain-English report with findings and lessons.
    """
    from divineos.analysis import save_analysis_report
    
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


@cli.command("report")
@click.argument("session_id", required=False)
def report_cmd(session_id: str):
    """Display a stored analysis report.
    
    If no session_id provided, shows list of recent sessions.
    """
    from divineos.analysis import get_stored_report, list_recent_sessions
    from datetime import datetime
    
    try:
        if not session_id:
            # List recent sessions
            sessions = list_recent_sessions(limit=10)
            
            if not sessions:
                click.secho("\n[-] No analyzed sessions found yet.", fg="yellow")
                click.secho("    Run 'divineos analyze <file.jsonl>' to analyze a session.", fg="bright_black")
                click.echo()
                return
            
            click.secho("\n=== Recent Sessions ===\n", fg="cyan", bold=True)
            for i, session in enumerate(sessions, 1):
                click.secho(f"  {i}. {session['session_id']}", fg="white", bold=True)
                
                # Format timestamp
                try:
                    ts = datetime.fromtimestamp(session['created_at']).strftime("%Y-%m-%d %H:%M:%S")
                    click.secho(f"     Time: {ts}", fg="bright_black")
                except:
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
                click.echo(report.encode('ascii', errors='replace').decode('ascii'))
            click.echo()
            
    except Exception as e:
        click.secho(f"[-] Error retrieving report: {e}", fg="red")
        logger.exception("Report retrieval failed")


@cli.command("cross-session")
@click.option("--limit", default=10, type=int, help="Number of sessions to analyze")
def cross_session_cmd(limit: int):
    """Compare findings across multiple sessions.
    
    Shows trends and patterns in your performance over time.
    """
    from divineos.analysis import compute_cross_session_trends, format_cross_session_report
    
    try:
        click.secho(f"\n[+] Analyzing trends across last {limit} sessions...", fg="cyan")
        
        # Compute trends
        trends = compute_cross_session_trends(limit=limit)
        
        # Format report
        report = format_cross_session_report(trends)
        
        # Display
        click.echo()
        click.echo(report)
        click.echo()
        
    except Exception as e:
        click.secho(f"[-] Error during cross-session analysis: {e}", fg="red")
        logger.exception("Cross-session analysis failed")
