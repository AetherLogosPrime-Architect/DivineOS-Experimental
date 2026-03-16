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
import divineos.expert_lenses as _lenses_mod
import divineos.tree_of_life as _tree_mod
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
    KNOWLEDGE_TYPES,
)
from divineos.quality_checks import init_quality_tables, run_all_checks, store_report
from divineos.session_features import (
    init_feature_tables,
    run_all_features,
    store_features,
    get_cross_session_summary,
)


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
    count = rebuild_fts_index()
    click.secho("[+] Database initialized successfully.", fg="green", bold=True)
    click.secho("[+] All tables ready: ledger, knowledge, quality checks, session features.", fg="green")
    if count > 0:
        click.secho(f"[+] FTS5 search index rebuilt ({count} entries).", fg="green")


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
            "FACT": "blue",
            "PATTERN": "magenta",
            "PREFERENCE": "green",
            "MISTAKE": "red",
            "EPISODE": "cyan",
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
    """Rebuild the FTS5 full-text search index from existing knowledge."""
    count = rebuild_fts_index()
    if count > 0:
        click.secho(f"[+] FTS5 index rebuilt: {count} entries indexed.", fg="green")
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
    """Run knowledge health check — decay stale, boost confirmed, resolve old lessons."""
    result = health_check()

    click.secho("\n=== Knowledge Health Check ===\n", fg="cyan", bold=True)
    click.secho(f"  Entries checked:        {result['total_checked']}", fg="white")
    click.secho(f"  Stale entries decayed:  {result['stale_decayed']}", fg="yellow" if result["stale_decayed"] else "bright_black")
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


@cli.command("experts")
def experts_cmd():
    """List all available expert lenses."""
    experts = _lenses_mod.list_experts()
    click.secho(f"\n=== {len(experts)} Expert Lenses ===\n", fg="cyan", bold=True)
    for expert in experts:
        click.secho(f"  {expert.name}", fg="white", bold=True, nl=False)
        click.secho(f" - {expert.domain}", fg="cyan")
        click.secho(f"    {expert.description}", fg="bright_black")
        click.echo()


@cli.command("route")
@click.argument("question")
@click.option("--max", "max_experts", default=3, type=int, help="Max experts to suggest")
def route_cmd(question: str, max_experts: int):
    """Show which expert lenses are most relevant to a question."""
    results = _lenses_mod.route(question, max_experts=max_experts)
    click.secho("\n=== Expert Routing ===\n", fg="cyan", bold=True)
    for expert, score in results:
        bar_len = int(score * 20)
        bar = "#" * bar_len + "." * (20 - bar_len)
        click.secho(f"  [{bar}] ", fg="green", nl=False)
        click.secho(f"{score:.3f} ", fg="bright_black", nl=False)
        click.secho(f"{expert.display_name}", fg="white", bold=True, nl=False)
        click.secho(f" ({expert.domain})", fg="cyan")
    click.echo()


@cli.command("lens")
@click.argument("expert_name")
@click.argument("question")
def lens_cmd(expert_name: str, question: str):
    """Generate a structured thinking framework for an expert applied to a question."""
    try:
        expert = _lenses_mod.get_expert(expert_name)
    except KeyError as e:
        click.secho(f"[-] {e}", fg="red")
        return
    prompt = _lenses_mod.generate_framework_prompt(expert, question)
    click.echo(prompt)


@cli.command("tree")
def tree_cmd():
    """Display the Tree of Life structure."""
    click.echo()
    click.echo(_tree_mod.render_tree())
    click.echo()

    click.secho("=== 11 Sephirot ===\n", fg="cyan", bold=True)
    for seph in _tree_mod.list_sephirot():
        pillar_color = {
            _tree_mod.Pillar.RIGHT: "green",
            _tree_mod.Pillar.LEFT: "red",
            _tree_mod.Pillar.MIDDLE: "yellow",
        }.get(seph.pillar, "white")
        click.secho(
            f"  {seph.position:2d}. {seph.hebrew_name}",
            fg="white",
            bold=True,
            nl=False,
        )
        click.secho(f" ({seph.english_name})", fg="cyan", nl=False)
        click.secho(f"  [{seph.pillar.value}]", fg=pillar_color)
        click.secho(f"      {seph.description}", fg="bright_black")
    click.echo()


@cli.command("flow")
@click.argument("question")
@click.option(
    "--depth",
    default="full",
    type=click.Choice(["full", "quick"]),
    help="full=11 stages, quick=5 stages (Middle Pillar)",
)
def flow_cmd(question: str, depth: str):
    """Generate a Tree of Life reasoning flow for a question."""
    prompt = _tree_mod.generate_flow_prompt(question, depth=depth)
    click.echo(prompt)


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


@cli.command("analyze")
@click.argument("file_path", type=click.Path(exists=True), required=False)
@click.option("--all", "analyze_all", is_flag=True, help="Analyze all found sessions")
def analyze_cmd(file_path: str | None, analyze_all: bool):
    """Analyze a session file for patterns (corrections, encouragements, tool usage)."""
    if analyze_all:
        analyses = _analyzer_mod.analyze_all_sessions()
        if not analyses:
            click.secho("[-] No sessions found to analyze.", fg="yellow")
            return
        for a in analyses:
            click.echo(a.summary())
        # Show aggregate
        agg = _analyzer_mod.aggregate_analyses(analyses)
        click.secho("=== Aggregate Stats ===\n", fg="cyan", bold=True)
        click.echo(f"  Sessions:       {agg['sessions']}")
        click.echo(f"  Total hours:    {agg['total_duration_hours']}")
        click.echo(f"  User messages:  {agg['total_user_messages']}")
        click.echo(f"  Tool calls:     {agg['total_tool_calls']}")
        click.echo(f"  Corrections:    {agg['corrections']}")
        click.echo(f"  Encouragements: {agg['encouragements']}")
        click.echo(f"  Decisions:      {agg['decisions']}")
        click.echo(f"  Frustrations:   {agg['frustrations']}")
        click.echo(f"  Overflows:      {agg['total_context_overflows']}")
        click.echo()
    elif file_path:
        analysis = _analyzer_mod.analyze_session(Path(file_path))
        click.echo(analysis.summary())
    else:
        # Analyze most recent session
        sessions = _analyzer_mod.find_sessions()
        if not sessions:
            click.secho("[-] No sessions found.", fg="yellow")
            return
        analysis = _analyzer_mod.analyze_session(sessions[0])
        click.echo(analysis.summary())


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
        # Legacy extraction (basic)
        for c in analysis.corrections:
            store_knowledge(
                knowledge_type="MISTAKE",
                content=f"User correction: {c.content[:300]}",
                confidence=0.8,
                tags=["session-analysis", "correction"],
            )
            stored += 1

        for e in analysis.encouragements:
            store_knowledge(
                knowledge_type="PATTERN",
                content=f"User praised: {e.content[:300]}",
                confidence=0.9,
                tags=["session-analysis", "encouragement"],
            )
            stored += 1

        for d in analysis.decisions:
            store_knowledge(
                knowledge_type="PREFERENCE",
                content=f"User decided: {d.content[:300]}",
                confidence=0.9,
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


@cli.command("report")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--store/--no-store", default=False, help="Store report in database")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON instead of plain English")
def report_cmd(file_path: str, store: bool, as_json: bool):
    """Run all 7 quality checks on a session and generate a report card."""
    init_quality_tables()
    path = Path(file_path)

    click.secho(f"[+] Analyzing session: {path.stem[:16]}...", fg="cyan")
    report = run_all_checks(path)

    if as_json:
        output = {
            "session_id": report.session_id,
            "created_at": report.created_at,
            "evidence_hash": report.evidence_hash,
            "checks": [
                {
                    "check_name": c.check_name,
                    "passed": c.passed,
                    "score": c.score,
                    "summary": c.summary,
                    "evidence_hash": c.evidence_hash,
                }
                for c in report.checks
            ],
        }
        click.echo(json.dumps(output, indent=2))
    else:
        click.echo()
        click.echo(report.report_text)
        click.echo()
        click.secho(f"Evidence hash: {report.evidence_hash}", fg="bright_black")

    if store:
        store_report(report)
        click.secho("\n[+] Report stored in database.", fg="green")


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
