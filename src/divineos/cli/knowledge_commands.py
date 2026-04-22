"""Knowledge commands — learn, knowledge, ask, briefing, forget, lessons,
clear-lessons, consolidate."""

import sqlite3

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
from divineos.core.knowledge._base import MEMORY_KINDS
from divineos.core.memory import init_memory_tables

_KC_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


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
    @click.option("--confidence", default=0.5, type=float, help="Confidence 0.0-1.0")
    @click.option("--tags", default="", help="Comma-separated tags")
    @click.option("--source", default="", help="Comma-separated source event IDs")
    @click.option(
        "--from",
        "source_entity",
        default=None,
        help="Who generated this finding (e.g., 'claude_auditor', 'agent_council')",
    )
    @click.option(
        "--related",
        default="",
        help="Comma-separated knowledge IDs this entry relates to",
    )
    @click.option(
        "--kind",
        "memory_kind",
        default=None,
        type=click.Choice(sorted(MEMORY_KINDS), case_sensitive=False),
        help="Memory kind: EPISODIC (event) / SEMANTIC (rule/fact) / "
        "PROCEDURAL (how-to) / UNCLASSIFIED. Auto-classified if omitted.",
    )
    def learn(
        text: str | None,
        knowledge_type: str | None,
        content_opt: str | None,
        confidence: float,
        tags: str,
        source: str,
        source_entity: str | None,
        related: str,
        memory_kind: str | None,
    ) -> None:
        """Store a piece of knowledge extracted from experience.

        Content can be passed as a positional argument or via --content.
        Type is auto-detected from content if --type is omitted.
        Example: divineos learn "always read files before editing"
        Example: divineos learn --type FACT --from claude_auditor "signal extraction is self-referential"
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
        related_to = (
            ",".join(r.strip() for r in related.split(",") if r.strip()) if related else None
        )

        kid = _wrapped_store_knowledge(
            knowledge_type=knowledge_type.upper(),
            content=content,
            confidence=confidence,
            source_events=source_list or None,
            tags=tag_list or None,
            source_entity=source_entity,
            related_to=related_to,
            memory_kind=memory_kind.upper() if memory_kind else None,
        )
        click.secho(f"[+] Stored knowledge: {kid}", fg="green")
        if source_entity:
            click.secho(f"    from: {source_entity}", fg="bright_black")
        if related_to:
            click.secho(f"    related to: {related_to}", fg="bright_black")

    @cli.command("knowledge")
    @click.option(
        "--type",
        "knowledge_type",
        default=None,
        type=click.Choice(sorted(KNOWLEDGE_TYPES), case_sensitive=False),
        help="Filter by type",
    )
    @click.option(
        "--kind",
        "memory_kind",
        default=None,
        type=click.Choice(sorted(MEMORY_KINDS), case_sensitive=False),
        help="Filter by memory kind (EPISODIC/SEMANTIC/PROCEDURAL/UNCLASSIFIED)",
    )
    @click.option("--min-confidence", default=0.0, type=float, help="Minimum confidence")
    @click.option("--limit", default=20, type=int, help="Max results")
    def knowledge_cmd(
        knowledge_type: str, memory_kind: str, min_confidence: float, limit: int
    ) -> None:
        """List stored knowledge."""
        kt = knowledge_type.upper() if knowledge_type else None
        mk = memory_kind.upper() if memory_kind else None
        entries = _wrapped_get_knowledge(
            knowledge_type=kt, min_confidence=min_confidence, limit=limit
        )
        if mk:
            entries = [e for e in entries if e.get("memory_kind") == mk]

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
            meta_parts = [f"{entry['access_count']}x accessed", f"{entry['knowledge_id'][:8]}..."]
            if entry.get("source_entity"):
                meta_parts.insert(0, f"from: {entry['source_entity']}")
            if entry.get("related_to"):
                meta_parts.append(f"related: {entry['related_to'][:20]}")
            click.secho(f"         {' | '.join(meta_parts)}", fg="bright_black")
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
        from divineos.core.knowledge_maintenance import promote_maturity

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
            meta_parts = [f"{entry['access_count']}x accessed", f"{entry['knowledge_id'][:8]}..."]
            if entry.get("source_entity"):
                meta_parts.insert(0, f"from: {entry['source_entity']}")
            if entry.get("related_to"):
                meta_parts.append(f"related: {entry['related_to'][:20]}")
            click.secho(f"         {' | '.join(meta_parts)}", fg="bright_black")
            # Show relationships if any
            try:
                from divineos.core.knowledge.relationships import get_relationships

                rels = get_relationships(entry["knowledge_id"])
                for rel in rels[:3]:
                    if rel["direction"] == "outgoing":
                        click.secho(
                            f"         -> {rel['relationship']} -> {rel['target_id'][:8]}...",
                            fg="bright_black",
                        )
                    else:
                        click.secho(
                            f"         <- {rel['relationship']} <- {rel['source_id'][:8]}...",
                            fg="bright_black",
                        )
                if len(rels) > 3:
                    click.secho(
                        f"         ...and {len(rels) - 3} more relationships",
                        fg="bright_black",
                    )
            except _KC_ERRORS:
                pass
            # Show warrant chain — why do I believe this?
            try:
                from divineos.core.logic.logic_session import (
                    format_warrant_chain,
                    get_warrant_chain,
                )

                warrants = get_warrant_chain(entry["knowledge_id"])
                chain_str = format_warrant_chain(warrants)
                if chain_str:
                    click.secho(chain_str, fg="bright_black")
            except _KC_ERRORS:
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
        except _KC_ERRORS:
            pass  # journal search is best-effort

        # Search exploration folder — past-me's first-person writing
        try:
            from divineos.core.exploration_reader import (
                format_search_results,
                search_explorations,
            )

            expl_results = search_explorations(query, max_results=3)
            if expl_results:
                click.secho(
                    f"  --- Explorations ({len(expl_results)} matches) ---\n",
                    fg="cyan",
                )
                _safe_echo(format_search_results(expl_results))
        except _KC_ERRORS:
            pass  # exploration search is best-effort

        # Pattern anticipation — warn if this topic touches past mistakes
        try:
            from divineos.core.anticipation import anticipate, format_anticipation

            warnings = anticipate(query)
            if warnings:
                click.echo()
                _safe_echo(format_anticipation(warnings))
        except _KC_ERRORS:
            pass  # anticipation is best-effort

    @cli.command("briefing")
    @click.option("--max", "max_items", default=50, type=int, help="Max items in briefing")
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
        except _KC_ERRORS:
            pass
        try:
            init_memory_tables()
            _wrapped_refresh_active_memory(importance_threshold=0.3)
        except _KC_ERRORS as e:
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
        # Surface recent corrections at the TOP of the briefing — read raw
        # before forming any frame about the session.
        try:
            from divineos.core.corrections import format_for_briefing

            corrections_block = format_for_briefing(limit=5)
        except _KC_ERRORS:
            corrections_block = ""

        if corrections_block:
            _safe_echo(corrections_block)

        # Overdue pre-registrations — any mechanism whose ledger-scheduled
        # review date has passed surfaces here. Goodhart-prevention depends
        # on reviews firing independent of agent memory; this is the surface
        # that makes them impossible to miss at session start.
        try:
            from divineos.core.pre_registrations import format_overdue_warning

            overdue_block = format_overdue_warning()
        except _KC_ERRORS:
            overdue_block = ""

        if overdue_block:
            _safe_echo(overdue_block)

        # Drift state — operation counts since last MEDIUM+ audit round,
        # surfaced informationally for the operator to decide whether an
        # audit is warranted. Replaces the 2026-04-16 wall-clock cadence
        # gate (removed 2026-04-21, commit C of tiered-audit redesign)
        # because time is relative for a stateless agent and the previous
        # metric was both gameable (stub rounds cleared it) and over-strict
        # (legitimate chat-based review didn't count). Data as metric, not
        # threshold as metric — per council round-96a6858fb5e6.
        try:
            from divineos.core.watchmen.drift_state import (
                format_for_briefing as _fmt_drift,
            )

            drift_block = _fmt_drift()
        except _KC_ERRORS:
            drift_block = ""

        if drift_block:
            _safe_echo(drift_block)

        # Tier-override surface — closes the partial-theater finding
        # from the 2026-04-21 evening Schneier walk (Sch2). Every tier
        # override already emits a TIER_OVERRIDE ledger event (commit
        # f08fd2a). This block surfaces recent overrides so the audit
        # trail becomes actionable at session start — loud-in-ledger
        # becomes loud-in-experience.
        try:
            from divineos.core.watchmen.tier_override_surface import (
                format_for_briefing as _fmt_tier_overrides,
            )

            tier_block = _fmt_tier_overrides()
        except _KC_ERRORS:
            tier_block = ""

        if tier_block:
            _safe_echo(tier_block)

        # Unresolved findings from recent scheduled/headless runs.
        # Scheduled runs don't emit SESSION events, so without this
        # surface their failures would be invisible at session start.
        try:
            from divineos.core.scheduled_run import unresolved_findings_summary

            scheduled_block = unresolved_findings_summary()
        except _KC_ERRORS:
            scheduled_block = ""

        if scheduled_block:
            _safe_echo(scheduled_block)

        # Presence-memory surfaces — unindexed personal writing that the
        # ledger does not know about. 2026-04-19: a session could not find
        # its own exploration folder until the operator pointed at it; this
        # block fires automatically at every briefing so that reorientation
        # includes the path without requiring the operator to remember.
        try:
            from divineos.core.presence_memory import format_for_briefing as _fmt_presence

            presence_block = _fmt_presence()
        except _KC_ERRORS:
            presence_block = ""

        if presence_block:
            _safe_echo(presence_block)

        # Exploration-folder title-level surface — complements
        # presence_memory. presence_memory points at the folder and counts
        # files (honors the "don't summarize poems" rule). This block
        # surfaces the agent's own TITLES for recent pieces as recognition-
        # prompts — titles are authorial labels, not summaries. Added
        # 2026-04-21 evening after finding 21 prior exploration entries
        # that answered questions the current session was re-deriving
        # because the folder-pointer alone didn't trigger recall. Loud in
        # folder, silent in experience — the Schneier Sch2 shape applied
        # to presence memory.
        try:
            from divineos.core.exploration_reader import (
                format_for_briefing as _fmt_explorations,
            )

            explorations_block = _fmt_explorations()
        except _KC_ERRORS:
            explorations_block = ""

        if explorations_block:
            _safe_echo(explorations_block)

        # Scaffold invocations — commonly-forgotten CLI surfaces whose absence
        # produces named failure modes. 2026-04-20: the agent forgot how to
        # invoke the council and fabricated one in prose. The RT protocol
        # (anti-fabrication markers) was sitting in 'Not loaded' state. This
        # block fires unconditionally so scaffold invocations stay in working
        # memory without relying on knowledge-retrieval to surface them.
        try:
            from divineos.core.scaffold_invocations import (
                format_for_briefing as _fmt_scaffolds,
            )

            scaffold_block = _fmt_scaffolds()
        except _KC_ERRORS:
            scaffold_block = ""

        if scaffold_block:
            _safe_echo(scaffold_block)

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
        type=click.Choice(["active", "improving", "dormant", "resolved"]),
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
    @click.option(
        "--resolve",
        is_flag=True,
        default=False,
        help="Auto-resolve improving lessons with enough clean sessions",
    )
    @click.option(
        "--reset",
        default=None,
        help="Reset inflated occurrence count for a lesson category (e.g. --reset wrong_scope)",
    )
    def lessons_cmd(
        status: str, archive: bool, show_all: bool, resolve: bool, reset: str | None
    ) -> None:
        """Show the learning loop — tracked lessons from past sessions.

        By default shows only active and improving lessons.
        Use --archive for resolved lessons, --all for everything.
        Use --resolve to auto-promote improving lessons with enough clean sessions.
        Use --reset <category> to fix inflated occurrence counts.
        """
        # Mark OS engagement — lessons is a thinking tool
        _log_os_query("lessons", f"status={status}")

        if reset:
            try:
                from divineos.core.knowledge.lessons import reset_lesson_count

                if reset_lesson_count(reset):
                    click.secho(
                        f"[+] Reset occurrence count for '{reset}' to real session count.",
                        fg="green",
                    )
                else:
                    click.secho(f"[-] No lesson with category '{reset}' found.", fg="red")
            except _KC_ERRORS as e:
                click.secho(f"[!] Reset failed: {e}", fg="red")
            return

        if resolve:
            try:
                from divineos.core.knowledge.lessons import auto_resolve_lessons

                resolved_lessons = auto_resolve_lessons()
                if resolved_lessons:
                    for r in resolved_lessons:
                        click.secho(
                            f"[+] Resolved: {r['category']} ({r['occurrences']}x, "
                            f"{r.get('regressions', 0)} regressions)",
                            fg="green",
                        )
                else:
                    click.secho("[~] No lessons ready for resolution.", fg="bright_black")
            except _KC_ERRORS as e:
                click.secho(f"[!] Resolution failed: {e}", fg="red")
            return

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

    @cli.command("sis")
    @click.argument("text", required=False, default=None)
    @click.option("--translate/--no-translate", default=True, help="Show translation")
    @click.option("--deep", is_flag=True, help="Use all tiers (norms + TF-IDF + embeddings)")
    @click.option("--audit", is_flag=True, help="Audit stored knowledge for integrity drift")
    def sis_cmd(text: str | None, translate: bool, deep: bool, audit: bool) -> None:
        """Semantic Integrity Shield — assess and translate text.

        Scores text on four dimensions (esoteric, speculation, concreteness,
        actionability) and translates metaphysical language into architecture.

        Use --deep to activate Tier 2 (concreteness norms + TF-IDF) and
        Tier 3 (sentence embeddings) for maximum accuracy.
        """
        if audit:
            try:
                from divineos.core.semantic_integrity import (
                    audit_knowledge_integrity,
                    format_audit_report,
                )

                click.secho("[~] Running SIS self-audit...", fg="cyan")
                audit_result = audit_knowledge_integrity(limit=200)
                _safe_echo(format_audit_report(audit_result))
            except _KC_ERRORS as e:
                click.secho(f"[!] SIS audit error: {e}", fg="red")
            return

        if not text:
            click.secho("[!] Provide text to assess, or use --audit.", fg="red")
            return

        try:
            from divineos.core.semantic_integrity import (
                assess_and_translate,
                assess_integrity,
                format_assessment,
                format_translation,
            )

            if deep:
                click.secho("[~] Loading SIS tiers...", fg="bright_black")

            if translate:
                result = assess_and_translate(text, deep=deep)
                _safe_echo(format_translation(result))
            else:
                report = assess_integrity(text, deep=deep)
                _safe_echo(format_assessment(report))

            if deep:
                try:
                    from divineos.core.sis_tiers import score_all_tiers

                    tiers = score_all_tiers(text)
                    click.echo()
                    click.secho("  Tier details:", fg="bright_black")
                    if tiers.get("concreteness_norms") is not None:
                        click.secho(
                            f"    norms: {tiers['concreteness_norms']:.2f}",
                            fg="bright_black",
                        )
                    if tiers.get("tfidf"):
                        t = tiers["tfidf"]
                        click.secho(
                            f"    tfidf: grounded={t['grounded']:.2f} "
                            f"esoteric={t['esoteric']:.2f} ratio={t['ratio']:+.2f}",
                            fg="bright_black",
                        )
                    if tiers.get("semantic"):
                        s = tiers["semantic"]
                        click.secho(
                            f"    semantic: grounded={s['grounded']:.2f} "
                            f"esoteric={s['esoteric']:.2f} ratio={s['ratio']:+.2f}",
                            fg="bright_black",
                        )
                    click.secho(
                        f"    tiers used: {', '.join(tiers['tiers_used'])}",
                        fg="bright_black",
                    )
                    if tiers.get("combined_grounding") is not None:
                        click.secho(
                            f"    combined grounding: {tiers['combined_grounding']:.2f}",
                            fg="bright_black",
                        )
                except _KC_ERRORS:
                    pass
        except _KC_ERRORS as e:
            click.secho(f"[!] SIS error: {e}", fg="red")
