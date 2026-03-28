"""Knowledge health commands — consolidate-stats, rebuild-index, digest,
health, distill, migrate-types."""

from pathlib import Path
from typing import Any

import click

from divineos.cli._helpers import _safe_echo
from divineos.cli._wrappers import (
    _wrapped_health_check,
    _wrapped_knowledge_health_report,
    _wrapped_knowledge_stats,
    _wrapped_migrate_knowledge_types,
    _wrapped_rebuild_fts_index,
    _wrapped_store_knowledge,
    init_knowledge_table,
    logger,
)
from divineos.core.knowledge import search_knowledge


def register(cli: click.Group) -> None:
    """Register knowledge health commands on the CLI group."""

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
                    from divineos.core.knowledge import supersede_knowledge

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
        from divineos.core.knowledge import get_knowledge, update_knowledge

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

    @cli.command("backfill-warrants")
    @click.option(
        "--execute",
        is_flag=True,
        help="Actually create warrants (default is dry-run)",
    )
    def backfill_warrants_cmd(execute: bool) -> None:
        """Give pre-existing knowledge entries INHERITED warrants.

        Entries created before the warrant system have no justification chain.
        This creates an INHERITED warrant for each unwarranted entry.
        """
        from divineos.core.logic.warrant_backfill import backfill_inherited_warrants

        dry_run = not execute
        if dry_run:
            click.secho("\n=== Warrant Backfill Preview (dry run) ===\n", fg="cyan", bold=True)

        counts = backfill_inherited_warrants(dry_run=dry_run)
        click.secho(f"  Checked:          {counts['checked']}", fg="white")
        click.secho(f"  Already warranted: {counts['already_warranted']}", fg="bright_black")

        if dry_run:
            click.secho(f"  Would backfill:   {counts['backfilled']}", fg="yellow")
            click.secho("\n  Run with --execute to apply.", fg="bright_black")
        else:
            click.secho(f"  Backfilled:       {counts['backfilled']}", fg="green")
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
