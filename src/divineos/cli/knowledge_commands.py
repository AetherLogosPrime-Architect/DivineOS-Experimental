"""Knowledge commands — learn, knowledge, ask, briefing, forget, lessons,
clear-lessons, consolidate."""

import click

from divineos.cli._helpers import (
    _auto_classify,
    _log_os_query,
    _resolve_knowledge_id,
    _safe_echo,
)
from divineos.cli._wrappers import (
    _wrapped_clear_lessons,
    _wrapped_consolidate_related,
    _wrapped_generate_briefing,
    _wrapped_get_knowledge,
    _wrapped_get_lesson_summary,
    _wrapped_get_lessons,
    _wrapped_refresh_active_memory,
    _wrapped_store_knowledge,
    logger,
)
from divineos.core.knowledge import KNOWLEDGE_TYPES, search_knowledge
from divineos.core.memory import init_memory_tables


def register(cli: click.Group) -> None:
    """Register all knowledge commands on the CLI group."""

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
        content = (text or content_opt or "").strip()
        if not content:
            click.secho("[-] Content is required. Pass as argument or --content.", fg="red")
            raise SystemExit(1)

        words = content.split()
        if len(words) < 3:
            click.secho(
                "[-] Knowledge must be at least 3 words. Too short to be meaningful.",
                fg="red",
            )
            raise SystemExit(1)

        if not knowledge_type:
            knowledge_type, classify_reason = _auto_classify(content)
            click.secho(f"[~] Auto-classified as: {knowledge_type} ({classify_reason})", fg="cyan")
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
        entries = _wrapped_get_knowledge(
            knowledge_type=kt, min_confidence=min_confidence, limit=limit
        )

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
                "MISTAKE": "red",
                "PATTERN": "magenta",
                "PREFERENCE": "green",
            }.get(entry["knowledge_type"], "white")
            click.secho(f"  [{entry['confidence']:.2f}] ", fg="bright_black", nl=False)
            click.secho(f"{entry['knowledge_type']} ", fg=color, bold=True, nl=False)
            _safe_echo(entry["content"])
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

        Searches both the knowledge store and core memory.
        Example: divineos ask "testing"
        """
        if not query.strip():
            click.secho("[-] Please provide a search query.", fg="yellow")
            return

        from divineos.core.memory import get_core

        _log_os_query("ask", query)
        results = search_knowledge(query, limit=limit)

        query_lower = query.lower()
        query_words = {
            w
            for w in query_lower.split()
            if len(w) > 2
            and w
            not in {
                "the",
                "and",
                "are",
                "was",
                "for",
                "what",
                "how",
                "who",
                "why",
                "when",
                "where",
                "which",
                "does",
                "that",
                "this",
                "with",
                "from",
                "have",
                "has",
                "had",
                "not",
                "but",
                "can",
                "will",
                "about",
            }
        }
        core = get_core()
        core_matches = []
        for slot_id, content in core.items():
            slot_text = (slot_id + " " + content).lower()
            matching_words = sum(1 for w in query_words if w in slot_text)
            if matching_words >= 1:
                core_matches.append((slot_id, content))

        if not results and not core_matches:
            click.secho(f"[-] Nothing found for '{query}'.", fg="yellow")
            return

        total = len(results) + len(core_matches)
        click.secho(f"\n=== {total} results for '{query}' ===\n", fg="cyan", bold=True)

        for slot_id, content in core_matches:
            label = slot_id.replace("_", " ").title()
            click.secho("  [CORE] ", fg="magenta", bold=True, nl=False)
            click.secho(f"{label}: ", fg="white", bold=True, nl=False)
            _safe_echo(content[:300])
            click.echo()

        from divineos.core.knowledge import record_access
        from divineos.core.knowledge_maturity import promote_maturity

        for entry in results:
            record_access(entry["knowledge_id"])
            promote_maturity(entry["knowledge_id"])

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
            content = entry["content"]
            if len(content) > 300:
                _safe_echo(content[:300] + "...")
            else:
                _safe_echo(content)
            click.secho(
                f"         {entry['access_count']}x accessed | {entry['knowledge_id'][:8]}...",
                fg="bright_black",
            )
            # Show relationships if any
            try:
                from divineos.core.knowledge.relationships import get_relationships

                rels = get_relationships(entry["knowledge_id"])
                for rel in rels[:3]:
                    if rel["direction"] == "outgoing":
                        click.secho(
                            f"         → {rel['relationship']} → {rel['target_id'][:8]}...",
                            fg="bright_black",
                        )
                    else:
                        click.secho(
                            f"         ← {rel['relationship']} ← {rel['source_id'][:8]}...",
                            fg="bright_black",
                        )
                if len(rels) > 3:
                    click.secho(
                        f"         ...and {len(rels) - 3} more relationships",
                        fg="bright_black",
                    )
            except Exception:
                pass
            # Show warrant chain — why do I believe this?
            try:
                from divineos.core.logic.logic_summary import (
                    format_warrant_chain,
                    get_warrant_chain,
                )

                warrants = get_warrant_chain(entry["knowledge_id"])
                chain_str = format_warrant_chain(warrants)
                if chain_str:
                    click.secho(chain_str, fg="bright_black")
            except Exception:
                pass
            click.echo()

        # Also search journal entries
        try:
            from divineos.core.memory_journal import journal_search

            journal_results = journal_search(query, limit=5)
            if journal_results:
                click.secho(f"  --- Journal ({len(journal_results)} entries) ---\n", fg="cyan")
                for jentry in journal_results:
                    import datetime

                    dt = datetime.datetime.fromtimestamp(jentry["created_at"])
                    click.secho(f"  [{dt:%Y-%m-%d}] ", fg="bright_black", nl=False)
                    content = jentry["content"]
                    if len(content) > 200:
                        _safe_echo(content[:200] + "...")
                    else:
                        _safe_echo(content)
                    if jentry.get("linked_knowledge_id"):
                        click.secho(
                            f"         linked: {jentry['linked_knowledge_id'][:8]}...",
                            fg="bright_black",
                        )
                    click.echo()
        except Exception:
            pass  # journal search is best-effort

        # Pattern anticipation — warn if this topic touches past mistakes
        try:
            from divineos.core.anticipation import anticipate, format_anticipation

            warnings = anticipate(query)
            if warnings:
                click.echo()
                _safe_echo(format_anticipation(warnings))
        except Exception:
            pass  # anticipation is best-effort

    @cli.command("briefing")
    @click.option("--max", "max_items", default=20, type=int, help="Max items in briefing")
    @click.option("--types", default="", help="Comma-separated knowledge types to include")
    @click.option(
        "--topic",
        default="",
        help="Topic hint to boost relevant knowledge (e.g. 'testing')",
    )
    @click.option("--deep", is_flag=True, help="Include stable layer (established knowledge)")
    @click.option(
        "--layer",
        default="",
        help="Load specific layer: urgent, active, stable, archive, all",
    )
    def briefing_cmd(max_items: int, types: str, topic: str, deep: bool, layer: str) -> None:
        """Generate a session context briefing from stored knowledge.

        Default shows urgent + active layers (focused, actionable).
        Use --deep for the full picture including stable knowledge.
        Use --layer archive to see archived/resolved entries.
        """
        _log_os_query("briefing", topic or "session start")
        try:
            from divineos.core.hud_handoff import mark_briefing_loaded

            mark_briefing_loaded()
        except Exception:
            pass
        try:
            init_memory_tables()
            _wrapped_refresh_active_memory(importance_threshold=0.3)
        except Exception as e:
            logger.debug(
                "Pre-briefing memory refresh failed (non-fatal, briefing continues): %s", e
            )

        type_list = [t.strip().upper() for t in types.split(",") if t.strip()] if types else None
        output = _wrapped_generate_briefing(
            max_items=max_items,
            include_types=type_list,
            context_hint=topic,
            deep=deep,
            layer=layer,
        )
        if output and output.strip():
            _safe_echo(output)
        else:
            click.secho("[*] No knowledge entries match your filters.", fg="yellow")
            click.secho('    Try: divineos learn "..." to add knowledge first.', fg="bright_black")

    @cli.command("forget")
    @click.argument("knowledge_id")
    @click.option("--reason", required=True, help="Why this knowledge is being superseded")
    def forget_cmd(knowledge_id: str, reason: str) -> None:
        """Supersede a knowledge entry (marks as removed, no replacement created)."""
        from divineos.core.knowledge import supersede_knowledge

        try:
            full_id = _resolve_knowledge_id(knowledge_id)
            supersede_knowledge(full_id, reason)
            click.secho(f"[+] Removed {full_id[:8]}... ({reason})", fg="green")
        except click.ClickException:
            raise
        except ValueError as e:
            click.secho(f"[-] {e}", fg="red")

    @cli.command("lessons")
    @click.option(
        "--status",
        default=None,
        type=click.Choice(["active", "improving", "resolved"]),
        help="Filter by lesson status",
    )
    @click.option(
        "--archive",
        is_flag=True,
        default=False,
        help="Show resolved (archived) lessons instead of active ones",
    )
    @click.option(
        "--all",
        "show_all",
        is_flag=True,
        default=False,
        help="Show all lessons regardless of status",
    )
    def lessons_cmd(status: str, archive: bool, show_all: bool) -> None:
        """Show the learning loop — tracked lessons from past sessions.

        By default shows only active and improving lessons.
        Use --archive for resolved lessons, --all for everything.
        """
        if archive:
            lessons = _wrapped_get_lessons(status="resolved")
        elif show_all:
            lessons = _wrapped_get_lessons(status=status)
        elif status:
            lessons = _wrapped_get_lessons(status=status)
        else:
            # Default: active + improving only (resolved goes to archive)
            active = _wrapped_get_lessons(status="active")
            improving = _wrapped_get_lessons(status="improving")
            lessons = (active or []) + (improving or [])

        if not lessons:
            click.secho("[-] No lessons tracked yet.", fg="yellow")
            click.secho(
                "    Run 'divineos report <session.jsonl> --store' to start learning.",
                fg="bright_black",
            )
            return

        summary = _wrapped_get_lesson_summary()
        click.echo()
        _safe_echo(summary)
        click.echo()

        click.secho("=== Lesson Details ===\n", fg="cyan", bold=True)
        for lesson in lessons:
            status_color = {
                "active": "red",
                "improving": "yellow",
                "resolved": "green",
            }.get(lesson["status"], "white")

            click.secho(f"  {lesson['status'].upper()} ", fg=status_color, bold=True, nl=False)
            click.secho(f"({lesson['occurrences']}x) ", fg="bright_black", nl=False)
            _safe_echo(lesson["description"][:80])
            agent = lesson.get("agent", "unknown")
            agent_str = f" | agent: {agent}" if agent != "unknown" else ""
            click.secho(
                f"         category: {lesson['category']} | sessions: {len(lesson['sessions'])}{agent_str}",
                fg="bright_black",
            )
            click.echo()

        # Hint about archive if showing default view
        if not archive and not show_all and not status:
            resolved = _wrapped_get_lessons(status="resolved")
            if resolved:
                click.secho(
                    f"    ({len(resolved)} resolved lessons in archive — use --archive to view)",
                    fg="bright_black",
                )
                click.echo()

    @cli.command("clear-lessons")
    def clear_lessons_cmd() -> None:
        """Wipe all lessons from lesson_tracking (for re-extraction after fixes)."""
        from divineos.core.knowledge import get_lessons

        active = get_lessons(status="active")
        improving = get_lessons(status="improving")
        total = len(active) + len(improving)
        if not total:
            click.secho("[*] No lessons to clear.", fg="yellow")
            return
        click.secho(
            f"[!] This will delete {total} lessons ({len(active)} active, {len(improving)} improving).",
            fg="yellow",
        )
        click.confirm("Proceed?", abort=True)
        count = _wrapped_clear_lessons()
        click.secho(f"[+] Cleared {count} lessons.", fg="green")

    @cli.command("consolidate")
    @click.option("--min-cluster", default=2, type=int, help="Minimum entries to form a cluster")
    def consolidate_cmd(min_cluster: int) -> None:
        """Merge related knowledge entries into consolidated ones."""
        merges = _wrapped_consolidate_related(min_cluster_size=min_cluster)

        if not merges:
            click.secho("[*] No clusters found to consolidate.", fg="yellow")
            click.secho(
                f"    Need at least {min_cluster} similar entries of the same type.",
                fg="bright_black",
            )
            return

        click.secho(f"\n[+] Consolidated {len(merges)} clusters:\n", fg="green", bold=True)
        for merge in merges:
            click.secho(f"  {merge['type']} ", fg="cyan", bold=True, nl=False)
            click.secho(f"({merge['merged_count']} entries merged) ", fg="bright_black", nl=False)
            click.echo(merge["content"])
        click.echo()
