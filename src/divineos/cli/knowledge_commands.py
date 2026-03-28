"""Knowledge commands — learn, journal, knowledge, ask, briefing, forget, consolidate-stats,
rebuild-index, directive, directives, directive-edit, digest, distill, lessons, clear-lessons,
consolidate, health, migrate-types."""

from pathlib import Path
from typing import Any

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
    _wrapped_health_check,
    _wrapped_knowledge_health_report,
    _wrapped_knowledge_stats,
    _wrapped_migrate_knowledge_types,
    _wrapped_rebuild_fts_index,
    _wrapped_refresh_active_memory,
    _wrapped_store_knowledge,
    init_knowledge_table,
    logger,
)
from divineos.core.consolidation import KNOWLEDGE_TYPES, get_knowledge, search_knowledge
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

    @cli.group("journal")
    def journal_group() -> None:
        """My personal journal — things I choose to remember."""
        pass

    @journal_group.command("save")
    @click.argument("text", required=False)
    @click.option("--context", default="", help="What prompted this thought")
    def journal_save_cmd(text: str | None, context: str) -> None:
        """Save something to my personal journal."""
        from divineos.core.memory import journal_save

        if not text:
            click.secho("[-] What do you want to remember?", fg="yellow")
            return

        entry_id = journal_save(text, context=context)
        click.secho(f"[+] Saved to journal: {entry_id[:8]}...", fg="green")

    @journal_group.command("list")
    @click.option("--limit", default=20, type=int, help="Max entries to show")
    def journal_list_cmd(limit: int) -> None:
        """Read my personal journal."""
        import datetime

        from divineos.core.memory import journal_list

        entries = journal_list(limit=limit)
        if not entries:
            click.secho("[~] Journal is empty. Nothing saved yet.", fg="bright_black")
            return

        click.secho(f"\n=== My Journal ({len(entries)} entries) ===\n", fg="cyan", bold=True)
        for entry in entries:
            dt = datetime.datetime.fromtimestamp(entry["created_at"], tz=datetime.timezone.utc)
            date_str = dt.strftime("%Y-%m-%d %H:%M")
            click.secho(f"  [{date_str}] ", fg="bright_black", nl=False)
            _safe_echo(entry["content"])
            if entry["context"]:
                click.secho(f"    context: {entry['context']}", fg="bright_black")
            if entry.get("linked_knowledge_id"):
                click.secho(
                    f"    linked: {entry['linked_knowledge_id'][:8]}...",
                    fg="bright_black",
                )
            click.echo()

    @journal_group.command("search")
    @click.argument("query")
    @click.option("--limit", default=10, type=int, help="Max results")
    def journal_search_cmd(query: str, limit: int) -> None:
        """Search journal entries by content."""
        import datetime

        from divineos.core.memory import journal_search

        results = journal_search(query, limit=limit)
        if not results:
            click.secho(f"[-] No journal entries match '{query}'.", fg="yellow")
            return

        click.secho(
            f"\n=== {len(results)} journal results for '{query}' ===\n",
            fg="cyan",
            bold=True,
        )
        for entry in results:
            dt = datetime.datetime.fromtimestamp(entry["created_at"], tz=datetime.timezone.utc)
            date_str = dt.strftime("%Y-%m-%d %H:%M")
            click.secho(f"  [{date_str}] ", fg="bright_black", nl=False)
            _safe_echo(entry["content"])
            if entry.get("linked_knowledge_id"):
                click.secho(
                    f"    linked: {entry['linked_knowledge_id'][:8]}...",
                    fg="bright_black",
                )
            click.echo()

    @journal_group.command("link")
    @click.argument("entry_id")
    @click.argument("knowledge_id")
    def journal_link_cmd(entry_id: str, knowledge_id: str) -> None:
        """Link a journal entry to a knowledge entry."""
        from divineos.core.memory import journal_link

        full_kid = _resolve_knowledge_id(knowledge_id)
        if journal_link(entry_id, full_kid):
            click.secho(f"[+] Linked journal {entry_id[:8]}... → {full_kid[:8]}...", fg="green")
        else:
            click.secho(f"[-] Journal entry {entry_id} not found.", fg="red")

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

        from divineos.core.consolidation import record_access
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
            click.echo()

        # Also search journal entries
        try:
            from divineos.core.memory import journal_search

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
    def briefing_cmd(max_items: int, types: str, topic: str) -> None:
        """Generate a session context briefing from stored knowledge."""
        _log_os_query("briefing", topic or "session start")
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
        from divineos.core.consolidation import supersede_knowledge

        try:
            full_id = _resolve_knowledge_id(knowledge_id)
            supersede_knowledge(full_id, reason)
            click.secho(f"[+] Removed {full_id[:8]}... ({reason})", fg="green")
        except click.ClickException:
            raise
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
                _safe_echo(f"    [{item['access_count']}x] {item['content'][:60]}")

        report = _wrapped_knowledge_health_report()
        if report["total"] > 0:
            click.secho("\n  Effectiveness:", fg="cyan")
            for status, count in sorted(report["by_status"].items()):
                click.echo(f"    {status:15s} {count}")

        click.echo()

    @cli.command("rebuild-index")
    def rebuild_index_cmd() -> None:
        """Rebuild the full-text search index from existing knowledge."""
        count = _wrapped_rebuild_fts_index()
        if count > 0:
            click.secho(f"[+] Full-text search index rebuilt: {count} entries indexed.", fg="green")
        else:
            click.secho("[*] No knowledge entries to index.", fg="yellow")

    @cli.command("directive")
    @click.argument("name")
    @click.argument("links", nargs=-1, required=True)
    @click.option("--tags", default="", help="Comma-separated tags")
    def directive_cmd(name: str, links: tuple[str, ...], tags: str) -> None:
        """Create a sutra-style directive — a chain of precise statements.

        Each argument after the name is one link in the chain.
        Links constrain each other to lock meaning against drift.

        Example:
            divineos directive "ledger-integrity" \\
                "Events enter." \\
                "Events persist." \\
                "No event is altered." \\
                "No event is removed." \\
                "The hash binds content to identity."
        """
        chain_lines = [f"[{name}]"]
        for i, link in enumerate(links, 1):
            chain_lines.append(f"  {i}. {link}")
        chain_text = "\n".join(chain_lines)

        tag_list = ["directive", f"directive:{name}"]
        if tags:
            tag_list.extend(t.strip() for t in tags.split(",") if t.strip())

        existing = search_knowledge(name, limit=10)
        for entry in existing:
            if entry.get("knowledge_type") == "DIRECTIVE" and f"directive:{name}" in entry.get(
                "tags", ""
            ):
                from divineos.core.consolidation import supersede_knowledge

                supersede_knowledge(entry["knowledge_id"], f"Updated directive: {name}")
                click.secho(f"[~] Superseding previous version of '{name}'", fg="yellow")

        entry_id = _wrapped_store_knowledge(
            knowledge_type="DIRECTIVE",
            content=chain_text,
            confidence=1.0,
            source_events=[],
            tags=tag_list,
        )

        click.secho(f"\n[+] Directive '{name}' stored: {entry_id[:12]}...", fg="green")
        click.echo()
        _safe_echo(chain_text)
        click.echo()
        click.secho(
            f"    {len(links)} links in chain. Surfaces first in all briefings.",
            fg="bright_black",
        )

    @cli.command("directives")
    def directives_cmd() -> None:
        """List all active directives."""
        _log_os_query("directives", "list directives")
        entries = get_knowledge(knowledge_type="DIRECTIVE", limit=100)

        if not entries:
            click.secho("[*] No directives yet.", fg="yellow")
            click.secho(
                '    Create one: divineos directive "name" "link1" "link2" ...',
                fg="bright_black",
            )
            return

        click.secho(f"\n=== Directives ({len(entries)}) ===\n", fg="cyan", bold=True)
        for entry in entries:
            _safe_echo(entry["content"])
            click.secho(
                f"    id: {entry['knowledge_id'][:12]}  |  {entry['access_count']}x accessed",
                fg="bright_black",
            )
            click.echo()

    @cli.command("directive-edit")
    @click.argument("name")
    @click.argument("link_number", type=int)
    @click.argument("new_text")
    def directive_edit_cmd(name: str, link_number: int, new_text: str) -> None:
        """Edit a single link in a directive chain.

        Example:
            divineos directive-edit "ledger-integrity" 3 "No event is modified after storage."
        """
        entries = get_knowledge(knowledge_type="DIRECTIVE", limit=100)
        target = None
        for entry in entries:
            if f"directive:{name}" in entry.get("tags", []):
                target = entry
                break

        if not target:
            click.secho(f"[-] No directive named '{name}'", fg="red")
            return

        content_lines = target.get("content", "").splitlines()
        if not content_lines:
            click.secho(f"[-] Directive '{name}' has empty content — cannot edit.", fg="red")
            return
        header = content_lines[0]
        links = [line.strip() for line in content_lines[1:] if line.strip()]

        if not links or link_number < 1 or link_number > len(links):
            click.secho(f"[-] Link {link_number} out of range (1-{len(links)})", fg="red")
            return

        old_link = links[link_number - 1]
        old_text_display = old_link.split(". ", 1)[1] if ". " in old_link else old_link
        click.secho(f"  Old: {old_text_display}", fg="red")
        click.secho(f"  New: {new_text}", fg="green")

        links[link_number - 1] = f"{link_number}. {new_text}"
        new_content = header + "\n" + "\n".join(f"  {link}" for link in links)

        from divineos.core.consolidation import supersede_knowledge

        supersede_knowledge(target["knowledge_id"], f"Edited link {link_number}: {new_text[:50]}")

        tag_list = ["directive", f"directive:{name}"]
        entry_id = _wrapped_store_knowledge(
            knowledge_type="DIRECTIVE",
            content=new_content,
            confidence=1.0,
            source_events=[target["knowledge_id"]],
            tags=tag_list,
        )

        click.secho(f"\n[+] Directive '{name}' updated: {entry_id[:12]}...", fg="green")
        click.echo()
        _safe_echo(new_content)
        click.echo()

    @cli.command("digest")
    @click.argument("file_path", type=click.Path(exists=True))
    @click.option("--chunk-size", default=100, help="Lines per chunk (default 100)")
    def digest_cmd(file_path: str, chunk_size: int) -> None:
        """Read a file in chunks and store a structured digest as knowledge."""
        path = Path(file_path)
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            click.secho(f"[-] Cannot read file: {e}", fg="red")
            return

        lines = content.splitlines()
        total_lines = len(lines)
        file_tag = path.name

        click.secho(f"\n[+] Digesting: {path.name} ({total_lines} lines)", fg="cyan", bold=True)

        sections: list[dict[str, Any]] = []
        if path.suffix == ".py":
            sections = _extract_python_sections(lines)
        else:
            for start in range(0, total_lines, chunk_size):
                end = min(start + chunk_size, total_lines)
                sections.append(
                    {
                        "name": f"lines {start + 1}-{end}",
                        "start": start,
                        "end": end,
                        "kind": "chunk",
                    }
                )

        if not sections:
            click.secho("[*] No sections found to digest.", fg="yellow")
            return

        digest_lines = [f"File: {path.name} ({total_lines} lines)"]
        if path.suffix == ".py":
            docstring = _extract_module_docstring(lines)
            if docstring:
                digest_lines.append(f"Purpose: {docstring}")
        digest_lines.append("")

        for sec in sections:
            if sec["kind"] == "class":
                digest_lines.append(f"  class {sec['name']} (line {sec['start'] + 1})")
            elif sec["kind"] == "function":
                digest_lines.append(f"  def {sec['name']} (line {sec['start'] + 1})")
            elif sec["kind"] == "chunk":
                digest_lines.append(f"  {sec['name']}")

            body_start = sec["start"] + 1
            if body_start < len(lines):
                for k in range(body_start, min(body_start + 5, sec["end"])):
                    stripped = lines[k].strip()
                    if stripped.startswith('"""') or stripped.startswith("'''"):
                        doc = stripped.strip("\"'").strip()
                        if doc:
                            digest_lines.append(f"    {doc}")
                        break

        digest_text = "\n".join(digest_lines)

        click.echo()
        _safe_echo(digest_text)
        click.echo()

        click.secho("[+] Storing digest in knowledge store...", fg="cyan")
        try:
            existing = search_knowledge(file_tag, limit=5)
            superseded = 0
            for entry in existing:
                if entry.get("knowledge_type") == "FACT" and f"digest:{file_tag}" in entry.get(
                    "tags", []
                ):
                    from divineos.core.consolidation import supersede_knowledge

                    supersede_knowledge(entry["knowledge_id"], f"Updated digest of {file_tag}")
                    superseded += 1

            entry_id = _wrapped_store_knowledge(
                knowledge_type="FACT",
                content=digest_text,
                confidence=1.0,
                source_events=[],
                tags=["digest", f"digest:{file_tag}"],
            )
            click.secho(f"[+] Digest stored: {entry_id[:12]}...", fg="green")
            if superseded:
                click.secho(f"    (superseded {superseded} previous digest(s))", fg="bright_black")
            click.secho(
                f"[+] {len(sections)} sections indexed. "
                f'Future sessions can run: divineos ask "{file_tag}"',
                fg="green",
            )
        except Exception as e:
            click.secho(f"[-] Failed to store digest: {e}", fg="red")
            logger.exception("Digest storage failed")

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

    @cli.command("clear-lessons")
    def clear_lessons_cmd() -> None:
        """Wipe all lessons from lesson_tracking (for re-extraction after fixes)."""
        from divineos.core.consolidation import get_lessons

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
        noise_count = result.get("noise_penalized", 0)
        if noise_count:
            click.secho(f"  Noise penalized:        {noise_count}", fg="yellow")
        stale = result.get("stale_decayed", 0)
        temporal = result.get("temporal_decayed", 0)
        abandoned = result.get("abandoned_decayed", 0)
        contradiction = result.get("contradiction_flagged", 0)
        decay_total = stale + temporal + abandoned + contradiction
        if decay_total:
            click.secho(f"  Decayed:                {decay_total}", fg="yellow")
            if stale:
                click.secho(f"    stale (unused 30d+):   {stale}", fg="bright_black")
            if temporal:
                click.secho(f"    temporal markers:      {temporal}", fg="bright_black")
            if abandoned:
                click.secho(f"    abandoned (14d+):      {abandoned}", fg="bright_black")
            if contradiction:
                click.secho(f"    contradicted (3x+):    {contradiction}", fg="bright_black")

        report = _wrapped_knowledge_health_report()
        if report["total"] > 0:
            click.secho("\n  Effectiveness breakdown:", fg="white")
            for status, count in sorted(report["by_status"].items()):
                click.secho(f"    {status:15s} {count}", fg="bright_black")
        click.echo()

    @cli.command("distill")
    @click.option("--id", "knowledge_id", default=None, help="ID of entry to distill")
    @click.option(
        "--to", "new_content", default=None, help="Distilled content to replace raw entry"
    )
    @click.option("--limit", default=10, help="Max candidates to show")
    @click.option("--type", "knowledge_type", default=None, help="Filter by knowledge type")
    def distill_cmd(
        knowledge_id: str | None,
        new_content: str | None,
        limit: int,
        knowledge_type: str | None,
    ) -> None:
        """Distill raw knowledge into clean, actionable entries."""
        from divineos.core.consolidation import get_knowledge, update_knowledge

        if knowledge_id and new_content:
            try:
                new_id = update_knowledge(knowledge_id, new_content)
                click.secho(f"[+] Distilled: {knowledge_id[:12]} -> {new_id[:12]}", fg="green")
                click.secho(f"    New content: {new_content[:100]}", fg="white")
            except ValueError as e:
                click.secho(f"[!] {e}", fg="red")
            return

        if knowledge_id and not new_content:
            click.secho("[!] --id requires --to with the distilled content.", fg="red")
            return

        raw_prefixes = ("I was corrected: ", "I decided: ", "I should: ")
        types_to_check = (
            [knowledge_type] if knowledge_type else ["PRINCIPLE", "DIRECTION", "BOUNDARY"]
        )

        candidates = []
        for ktype in types_to_check:
            entries = get_knowledge(knowledge_type=ktype, limit=200)
            for entry in entries:
                content = entry["content"]
                if not any(content.startswith(p) for p in raw_prefixes):
                    continue
                if entry["confidence"] < 0.3:
                    continue
                candidates.append(entry)

        if not candidates:
            click.secho("[~] No raw entries need distillation.", fg="green")
            return

        candidates.sort(key=lambda e: e["confidence"], reverse=True)
        candidates = candidates[:limit]

        click.secho(
            f"\n=== {len(candidates)} Entries Need Distillation ===\n",
            fg="cyan",
            bold=True,
        )
        for entry in candidates:
            kid = entry["knowledge_id"]
            click.secho(f"  ID: {kid}", fg="yellow")
            click.secho(
                f"  Type: {entry['knowledge_type']}  Confidence: {entry['confidence']:.2f}",
                fg="bright_black",
            )
            raw_text = entry["content"].encode("ascii", errors="replace").decode("ascii")
            click.secho(f"  Raw: {raw_text}", fg="white")
            click.echo()

        click.secho(
            'To distill, run: divineos distill --id <ID> --to "clean first-person version"',
            fg="bright_black",
        )
        click.echo()

    @cli.command("migrate-types")
    @click.option(
        "--execute",
        is_flag=True,
        help="Actually perform the migration (default is dry-run)",
    )
    def migrate_types_cmd(execute: bool) -> None:
        """Reclassify old knowledge types (MISTAKE/PATTERN/PREFERENCE) to new types."""
        init_knowledge_table()
        dry_run = not execute

        if dry_run:
            click.secho("\n=== Migration Preview (dry run) ===\n", fg="cyan", bold=True)
        else:
            preview = _wrapped_migrate_knowledge_types(dry_run=True)
            if not preview:
                click.secho("\n  No entries to migrate.", fg="bright_black")
                click.echo()
                return
            click.secho(
                f"\n[!] This will reclassify {len(preview)} knowledge entries.",
                fg="yellow",
            )
            click.confirm("Proceed?", abort=True)
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

    @cli.command("relate")
    @click.argument("source_id")
    @click.argument("relationship")
    @click.argument("target_id")
    @click.option("--notes", default="", help="Optional notes about this relationship")
    def relate_cmd(source_id: str, relationship: str, target_id: str, notes: str) -> None:
        """Create a typed relationship between two knowledge entries.

        Example: divineos relate abc123 SUPPORTS def456
        """
        from divineos.core.knowledge.relationships import RELATIONSHIP_TYPES, add_relationship

        relationship = relationship.upper()
        if relationship not in RELATIONSHIP_TYPES:
            click.secho(
                f"[-] Unknown relationship '{relationship}'. "
                f"Valid: {', '.join(sorted(RELATIONSHIP_TYPES))}",
                fg="red",
            )
            return

        try:
            full_source = _resolve_knowledge_id(source_id)
            full_target = _resolve_knowledge_id(target_id)
            add_relationship(full_source, full_target, relationship, notes=notes)
            click.secho(
                f"[+] {full_source[:8]}... {relationship} {full_target[:8]}...",
                fg="green",
            )
        except click.ClickException:
            raise
        except ValueError as e:
            click.secho(f"[-] {e}", fg="red")

    @cli.command("related")
    @click.argument("knowledge_id")
    @click.option("--depth", default=2, type=int, help="How many hops to traverse")
    def related_cmd(knowledge_id: str, depth: int) -> None:
        """Show relationships for a knowledge entry."""
        from divineos.core.knowledge.relationships import (
            find_related_cluster,
            get_relationships,
        )

        try:
            full_id = _resolve_knowledge_id(knowledge_id)
        except click.ClickException:
            raise

        rels = get_relationships(full_id)
        if not rels:
            click.secho(f"[-] No relationships for {full_id[:8]}...", fg="yellow")
            return

        click.secho(f"\n=== Relationships for {full_id[:8]}... ===\n", fg="cyan", bold=True)
        for rel in rels:
            if rel["direction"] == "outgoing":
                click.secho(
                    f"  → {rel['relationship']} → {rel['target_id'][:8]}...",
                    fg="white",
                )
            else:
                click.secho(
                    f"  ← {rel['relationship']} ← {rel['source_id'][:8]}...",
                    fg="white",
                )
            if rel["notes"]:
                click.secho(f"    ({rel['notes']})", fg="bright_black")

        if depth > 1:
            cluster = find_related_cluster(full_id, max_depth=depth)
            if len(cluster) > len(rels):
                click.secho(
                    f"\n  Cluster ({len(cluster)} entries within {depth} hops):",
                    fg="cyan",
                )
                for item in cluster:
                    click.secho(
                        f"    [{item['depth']}] {item['knowledge_id'][:8]}... "
                        f"via {item['relationship']}",
                        fg="bright_black",
                    )
        click.echo()

    @cli.command("unrelate")
    @click.argument("relationship_id")
    def unrelate_cmd(relationship_id: str) -> None:
        """Remove a relationship by its ID."""
        from divineos.core.knowledge.relationships import remove_relationship

        if remove_relationship(relationship_id):
            click.secho(f"[+] Removed relationship {relationship_id[:8]}...", fg="green")
        else:
            click.secho(f"[-] Relationship {relationship_id} not found.", fg="yellow")


def _extract_python_sections(lines: list[str]) -> list[dict[str, Any]]:
    """Extract top-level classes and functions from Python source lines."""
    sections: list[dict[str, Any]] = []
    for i, line in enumerate(lines):
        if line.startswith("class "):
            name = line.split("(")[0].split(":")[0].replace("class ", "").strip()
            if name:
                sections.append({"name": name, "start": i, "end": i, "kind": "class"})
        elif line.startswith("def ") and "(" in line:
            name = line.split("(")[0].replace("def ", "").strip()
            sections.append({"name": name, "start": i, "end": i, "kind": "function"})

    for j in range(len(sections) - 1):
        sections[j]["end"] = sections[j + 1]["start"]
    if sections:
        sections[-1]["end"] = len(lines)

    return sections


def _extract_module_docstring(lines: list[str]) -> str:
    """Extract the first line of a module docstring."""
    for line in lines[:10]:
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            doc = stripped.strip("\"'").strip()
            if doc:
                return doc
    return ""
