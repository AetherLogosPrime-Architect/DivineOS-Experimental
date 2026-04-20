"""Knowledge health commands — consolidate-stats, rebuild-index, digest,
health, distill, migrate-types, hooks."""

import sqlite3

# time previously used for manual updated_at stamping of mutated rows.
# Removed 2026-04-20 when knowledge repair moved to supersession (which
# sets its own timestamps internally via update_knowledge).
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

_KHC_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


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

    @cli.command("anti-slop")
    def anti_slop_cmd() -> None:
        """Runtime verification that enforcers actually enforce.

        Complements unit tests. Unit tests check pre-merge; this
        checks the actually-loaded system at runtime. Catches
        regressions where tests pass but shipped code has silently
        stopped working (config drift, env overrides, shadowed
        imports, decorators that swallow errors).

        Each check runs the enforcer against a known-bad input
        (must fire) and a known-good input (must not fire). If
        either is wrong, it's slop.
        """
        from divineos.core.anti_slop import run_all_checks, summarize

        results = run_all_checks()
        total, passed, failed = summarize(results)

        click.secho("\n=== Anti-slop runtime verification ===\n", fg="cyan", bold=True)
        for r in results:
            marker = "[+]" if r.passed else "[-]"
            color = "green" if r.passed else "red"
            click.secho(f"  {marker} {r.name}", fg=color, bold=True)
            click.echo(f"      {r.detail}")

        click.echo("")
        if failed == 0:
            click.secho(
                f"[+] All {total} enforcer(s) verified. No slop detected.",
                fg="green",
                bold=True,
            )
        else:
            click.secho(
                f"[-] {failed}/{total} enforcer(s) failed verification. "
                f"Investigate before trusting downstream behavior.",
                fg="red",
                bold=True,
            )

    @cli.command("maturity")
    def maturity_cmd() -> None:
        """Break down knowledge by maturity, splitting RAW into
        transient (session-scoped, will auto-archive) vs. pending
        (could mature via corroboration but hasn't yet).

        The existing health report counts RAW as a single bucket,
        which conflates two very different populations. This command
        makes the distinction visible.
        """
        from divineos.core.knowledge.maturity_diagnostic import classify_maturity

        b = classify_maturity()

        click.secho("\n=== Knowledge Maturity ===\n", fg="cyan", bold=True)
        click.echo(f"  Total (non-superseded):  {b.total}")
        for mat in ("RAW", "HYPOTHESIS", "TESTED", "CONFIRMED"):
            count = b.by_maturity.get(mat, 0)
            pct = (100 * count / b.total) if b.total else 0
            click.echo(f"  {mat:12s} {count:3d}  ({pct:5.1f}%)")

        click.secho("\n=== RAW Breakdown ===\n", fg="cyan", bold=True)
        click.echo(f"  Transient (session-scoped, will auto-archive): {len(b.raw_transient)}")
        for e in b.raw_transient[:10]:
            snippet = e["content"][:70]
            click.echo(f"    [{e['knowledge_type']}] {ascii(snippet)}")

        click.echo(f"\n  Pending (could mature via corroboration): {len(b.raw_pending)}")
        for e in b.raw_pending[:10]:
            snippet = e["content"][:70]
            click.echo(
                f"    [{e['knowledge_type']}] corr={e['corroboration_count']} "
                f"conf={e['confidence']:.2f} {ascii(snippet)}"
            )

        if b.raw_transient and not b.raw_pending:
            click.secho(
                "\n[*] RAW population is entirely transient. Pipeline is healthy.",
                fg="green",
            )
        elif b.raw_pending:
            click.secho(
                f"\n[*] {len(b.raw_pending)} RAW entries could mature with corroboration. "
                "Watch whether they accumulate evidence over time.",
                fg="yellow",
            )

    @cli.command("rebuild-index")
    def rebuild_index_cmd() -> None:
        """Rebuild the full-text search index from existing knowledge."""
        count = _wrapped_rebuild_fts_index()
        if count > 0:
            click.secho(f"[+] Full-text search index rebuilt: {count} entries indexed.", fg="green")
        else:
            click.secho("[*] No knowledge entries to index.", fg="yellow")

    @cli.command("fix-encoding")
    @click.option(
        "--apply",
        is_flag=True,
        help="Actually update rows. Without this flag the command is dry-run.",
    )
    def fix_encoding_cmd(apply: bool) -> None:
        """Repair mojibake in knowledge content via ftfy.

        Runs ``ftfy.fix_text`` over every row's ``content`` field and
        reports what would change. With ``--apply``, writes the
        cleaned text back in place AND rebuilds the FTS index so
        searches match the corrected text.

        Safe to run repeatedly — ftfy is idempotent on already-clean
        text. Dry-run by default so the operator can inspect the
        diff before committing.
        """
        try:
            import ftfy
        except ImportError:
            click.secho(
                "[-] ftfy not installed. Run: pip install ftfy",
                fg="red",
            )
            return

        from divineos.core.knowledge._base import get_connection

        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT knowledge_id, content FROM knowledge WHERE superseded_by IS NULL"
            ).fetchall()

            to_fix: list[tuple[str, str, str]] = []
            for kid, content in rows:
                if content is None:
                    continue
                cleaned = ftfy.fix_text(content)
                if cleaned != content:
                    to_fix.append((kid, content, cleaned))

            if not to_fix:
                click.secho("[*] No mojibake found. Store is clean.", fg="green")
                return

            click.secho(
                f"[!] {len(to_fix)} row(s) contain fixable encoding issues:",
                fg="yellow",
                bold=True,
            )
            for kid, before, after in to_fix[:10]:
                click.echo(f"  {kid}:")
                # Use ascii() not repr() so output is terminal-safe on
                # Windows cp1252 consoles (repr preserves U+FFFD literally).
                click.echo(f"    before: {ascii(before[:100])}")
                click.echo(f"    after:  {ascii(after[:100])}")
            if len(to_fix) > 10:
                click.echo(f"  ... and {len(to_fix) - 10} more")

            if not apply:
                click.echo("")
                click.secho(
                    "[*] Dry-run. Re-run with --apply to write the cleaned text.",
                    fg="cyan",
                )
                return

            # Close read conn before supersessions — each update_knowledge call
            # opens its own write. Same append-only pattern as the SIS and
            # distill fixes in pipeline_phases.py.
        finally:
            conn.close()

        from divineos.core.knowledge.crud import update_knowledge

        repaired = 0
        for kid, _before, after in to_fix:
            try:
                update_knowledge(
                    kid,
                    new_content=after,
                    additional_tags=["encoding-repaired"],
                )
                repaired += 1
            except ValueError:
                # Entry was deleted/superseded between scan and repair — skip
                pass
        click.secho(
            f"[+] Repaired {repaired} row(s).",
            fg="green",
            bold=True,
        )

        # Rebuild FTS so search matches the cleaned text.
        count = _wrapped_rebuild_fts_index()
        if count > 0:
            click.secho(f"[+] FTS index rebuilt: {count} entries.", fg="green")

    @cli.command("digest")
    @click.argument("file_path", type=click.Path(exists=True))
    @click.option("--chunk-size", default=100, help="Lines per chunk (default 100)")
    def digest_cmd(file_path: str, chunk_size: int) -> None:
        """Read a file in chunks and store a structured digest as knowledge."""
        path = Path(file_path)
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except _KHC_ERRORS as e:
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
        except _KHC_ERRORS as e:
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
        temporal = result.get("temporal_decayed", 0)
        contradiction = result.get("contradiction_flagged", 0)
        needs_review = result.get("needs_review_count", 0)
        decay_total = temporal + contradiction
        if decay_total:
            click.secho(f"  Decayed:                {decay_total}", fg="yellow")
            if temporal:
                click.secho(f"    temporal markers:      {temporal}", fg="bright_black")
            if contradiction:
                click.secho(f"    contradicted (3x+):    {contradiction}", fg="bright_black")
        if needs_review:
            click.secho(f"  Needs review:           {needs_review}", fg="yellow")
            click.secho("    (unseen 30d+ — flagged, not decayed)", fg="bright_black")

        report = _wrapped_knowledge_health_report()
        if report["total"] > 0:
            click.secho("\n  Effectiveness breakdown:", fg="white")
            for status, count in sorted(report["by_status"].items()):
                click.secho(f"    {status:15s} {count}", fg="bright_black")

        # SIS self-audit — check own docstrings for ungrounded esoteric language
        try:
            from divineos.core.sis_self_audit import audit_summary

            sis = audit_summary()
            click.secho(
                f"\n  SIS self-audit:         {sis['modules_scanned']} modules scanned",
                fg="white",
            )
            if sis["clean"]:
                click.secho("    All docstrings grounded", fg="green")
            else:
                click.secho(
                    f"    {sis['flagged_count']} flagged (ungrounded esoteric language)",
                    fg="yellow",
                )
                for mod in sis["flagged_modules"][:5]:
                    click.secho(f"      - {mod}", fg="bright_black")
        except (ImportError, OSError) as e:
            click.secho(f"\n  SIS self-audit: unavailable ({e})", fg="bright_black")

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
        from divineos.core.logic.logic_reasoning import backfill_inherited_warrants

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

    @cli.command("reclassify-directions")
    def reclassify_directions_cmd() -> None:
        """Reclassify DIRECTION entries into PREFERENCE/INSTRUCTION/DIRECTION.

        Uses content analysis to split the overloaded DIRECTION type:
        - PREFERENCE: style/approach choices ("use X", "prefer Y")
        - INSTRUCTION: operational rules ("always X", "never Y")
        - DIRECTION: general guidance (everything else)
        """
        init_knowledge_table()
        from divineos.core.knowledge.migration import reclassify_directions

        counts = reclassify_directions()
        total = counts["preference"] + counts["instruction"]
        if total == 0:
            click.secho("[~] No DIRECTION entries needed reclassification.", fg="bright_black")
        else:
            click.secho(f"[+] Reclassified {total} entries:", fg="green")
            if counts["preference"]:
                click.secho(f"    {counts['preference']} -> PREFERENCE", fg="cyan")
            if counts["instruction"]:
                click.secho(f"    {counts['instruction']} -> INSTRUCTION", fg="yellow")
            click.secho(f"    {counts['unchanged']} unchanged (still DIRECTION)", fg="bright_black")

    @cli.command("reclassify-seed")
    def reclassify_seed_cmd() -> None:
        """Fix legacy seed entries mis-tagged as source='STATED'.

        Seed entries that were loaded before the source-fix landed got
        defaulted to STATED ('told by user'), when they should be INHERITED
        ('born knowing, no session evidence'). This walks the canonical
        seed.json contents and reclassifies any matching STATED entries
        to INHERITED. Safe to run repeatedly.
        """
        import json
        from pathlib import Path

        from divineos.core.seed_manager import reclassify_seed_as_inherited

        init_knowledge_table()

        seed_path = Path(__file__).resolve().parents[1] / "seed.json"
        if not seed_path.exists():
            click.secho(f"[-] Seed file not found: {seed_path}", fg="red")
            return

        seed_data = json.loads(seed_path.read_text(encoding="utf-8"))
        counts = reclassify_seed_as_inherited(seed_data)
        if counts["reclassified"] == 0:
            click.secho(
                f"[~] No seed entries needed reclassification "
                f"({counts['already_correct']} already INHERITED).",
                fg="bright_black",
            )
        else:
            click.secho(
                f"[+] Reclassified {counts['reclassified']} seed entries to INHERITED.",
                fg="green",
            )
            click.secho(
                f"    {counts['already_correct']} already correct, "
                f"{counts['not_seed']} non-seed untouched.",
                fg="bright_black",
            )

    @cli.command("restore-seed-confidence")
    def restore_seed_confidence_cmd() -> None:
        """Restore INHERITED entries spuriously demoted by the orphan-flagger bug.

        Before the orphan-flagger fix, fresh seed entries got demoted to
        confidence 0.5 the same day they loaded because the age gate was
        unenforced and there was no INHERITED exemption. This walks the
        seed and restores any INHERITED entry sitting at exactly the bug's
        sentinel value (0.5) whose content still matches the seed. Safe
        to run repeatedly — only touches entries at the sentinel value.
        """
        import json
        from pathlib import Path

        from divineos.core.seed_manager import restore_inherited_confidence

        init_knowledge_table()

        seed_path = Path(__file__).resolve().parents[1] / "seed.json"
        if not seed_path.exists():
            click.secho(f"[-] Seed file not found: {seed_path}", fg="red")
            return

        seed_data = json.loads(seed_path.read_text(encoding="utf-8"))
        counts = restore_inherited_confidence(seed_data)
        if counts["restored"] == 0:
            click.secho(
                f"[~] No seed entries needed restoration "
                f"({counts['already_ok']} at correct confidence).",
                fg="bright_black",
            )
        else:
            click.secho(
                f"[+] Restored {counts['restored']} INHERITED entries to seed confidence.",
                fg="green",
            )
            click.secho(
                f"    {counts['already_ok']} already ok, "
                f"{counts['not_victim']} non-seed untouched.",
                fg="bright_black",
            )

    @cli.command("seed-export")
    @click.option("--output", "-o", default=None, help="Output file path (default: stdout)")
    def seed_export_cmd(output: str | None) -> None:
        """Export current knowledge and core memory as a seed file."""
        import json

        from divineos.core.knowledge import get_connection
        from divineos.core.memory import get_core

        conn = get_connection()
        try:
            # Core memory
            core = get_core()

            # Active knowledge (not superseded, not archived)
            rows = conn.execute(
                "SELECT knowledge_type, content, confidence, maturity, tags "
                "FROM knowledge WHERE superseded_by IS NULL "
                "ORDER BY knowledge_type, confidence DESC"
            ).fetchall()

            knowledge = []
            for ktype, content, conf, mat, tags_json in rows:
                tags = json.loads(tags_json) if tags_json else []
                # Strip session-specific tags
                clean_tags = [
                    t for t in tags if not t.startswith("session-") and not t.startswith("topic-")
                ]
                knowledge.append(
                    {
                        "content": content,
                        "confidence": round(conf, 2),
                        "maturity": mat,
                        "tags": clean_tags,
                        "type": ktype,
                    }
                )

            # Lessons
            lessons = []
            try:
                lesson_rows = conn.execute(
                    "SELECT category, description, occurrences, status "
                    "FROM lesson_tracking WHERE status IN ('active', 'improving') "
                    "ORDER BY occurrences DESC"
                ).fetchall()
                for cat, desc, occ, status in lesson_rows:
                    lessons.append(
                        {
                            "category": cat,
                            "description": desc,
                            "occurrences": occ,
                            "status": status,
                        }
                    )
            except sqlite3.OperationalError:
                pass

            # Build seed
            from divineos.core.seed_manager import get_applied_seed_version

            current_version = get_applied_seed_version() or "1.0.0"
            # Bump patch version
            parts = current_version.split(".")
            parts[-1] = str(int(parts[-1]) + 1)
            new_version = ".".join(parts)

            seed = {
                "version": new_version,
                "created": __import__("datetime").datetime.now().isoformat() + "Z",
                "description": "Exported from live database",
                "core_memory": core,
                "knowledge": knowledge,
                "lessons": lessons,
            }

            seed_json = json.dumps(seed, indent=2, ensure_ascii=False)

            if output:
                Path(output).write_text(seed_json, encoding="utf-8")
                click.secho(f"[+] Seed exported to {output}", fg="green")
            else:
                _safe_echo(seed_json)

            click.secho(
                f"  {len(knowledge)} knowledge entries, {len(lessons)} lessons, "
                f"version {new_version}",
                fg="bright_black",
                err=True,
            )
        finally:
            conn.close()

    @cli.command("hooks")
    @click.option(
        "--dir",
        "hooks_dir",
        default=".divineos/hooks",
        help="Directory containing hook files",
    )
    def hooks_cmd(hooks_dir: str) -> None:
        """Diagnose hook configuration — validate all .divineos.hook files."""
        from divineos.hooks.hook_diagnostics import HookDiagnostics

        diag = HookDiagnostics(hooks_dir=hooks_dir)
        report = diag.diagnose_all_hooks()

        click.secho("\n=== Hook Diagnostics ===\n", fg="cyan", bold=True)
        click.secho(f"  Directory: {hooks_dir}", fg="bright_black")
        click.secho(f"  Valid:     {report['valid_hooks']}", fg="green")
        click.secho(
            f"  Invalid:   {report['invalid_hooks']}",
            fg="red" if report["invalid_hooks"] else "green",
        )

        if report["global_issues"]:
            click.echo()
            for issue in report["global_issues"]:
                click.secho(f"  [!] {issue}", fg="red")

        if report["hooks"]:
            click.echo()
            for hook in report["hooks"]:
                status = (
                    click.style("OK", fg="green")
                    if hook["valid"]
                    else click.style("FAIL", fg="red")
                )
                click.echo(
                    f"  [{status}] {hook['name']}  ({hook['event_type']} -> {hook['action_type']})"
                )

        if not report["hooks"] and not report["global_issues"]:
            click.secho(f"\n  No hook files found in {hooks_dir}.", fg="yellow")
            click.secho("  Create .divineos.hook JSON files to add hooks.", fg="bright_black")

    @cli.command("compress")
    @click.option("--days", default=7, help="Keep events newer than N days (default: 7)")
    @click.option("--dry-run", is_flag=True, help="Show what would be compressed without deleting")
    @click.option("--vacuum/--no-vacuum", default=True, help="VACUUM DB after compression")
    def compress_cmd(days: int, dry_run: bool, vacuum: bool) -> None:
        """ELMO — compress the event ledger by archiving old noise events."""
        from divineos.core.ledger_compressor import (
            analyze_ledger,
            compress_ledger,
            vacuum_ledger,
        )

        click.secho("\n=== ELMO: Event Ledger Memory Optimizer ===\n", fg="cyan", bold=True)

        # Analyze first
        stats = analyze_ledger()
        click.echo(f"  Total events:      {stats['total_events']}")
        click.echo(f"  Compressible:      {stats['compressible_count']}")
        click.echo(f"  Meaningful (kept): {stats['meaningful_kept']}")
        click.echo(f"  Est. savings:      {stats['estimated_savings_mb']} MB")
        click.echo()

        if stats["compressible_count"] == 0:
            click.secho("  Nothing to compress. Ledger is clean.", fg="green")
            return

        # Compress
        result = compress_ledger(retention_days=days, dry_run=dry_run)
        if dry_run:
            click.secho(f"  [DRY RUN] Would compress {result['compressed']} events:", fg="yellow")
            for etype, count in result["by_type"].items():
                click.echo(f"    {etype}: {count}")
            return

        click.secho(f"  Compressed {result['compressed']} events.", fg="green")
        for etype, count in result["by_type"].items():
            click.echo(f"    {etype}: {count}")

        # Vacuum
        if vacuum:
            click.echo()
            vresult = vacuum_ledger()
            click.echo(
                f"  DB size: {vresult['size_before_mb']} MB -> {vresult['size_after_mb']} MB"
            )
            click.secho(f"  Saved:   {vresult['saved_mb']} MB", fg="green")

    @cli.command("test-audit")
    def test_audit_cmd() -> None:
        """Audit test quality — classify tests by what they actually verify.

        Scans all test files and classifies each test by:
        - Data source: real DB vs synthetic/mock vs no data
        - Assertion type: behavior vs structure vs mixed
        - Coverage: failure mode vs edge case vs happy path
        Also detects inline CREATE TABLE statements (schema divergence risk).
        """
        from divineos.analysis.audit_classifier import (
            audit_test_directory,
            format_audit_report,
        )

        test_dir = Path(__file__).parent.parent.parent.parent / "tests"
        if not test_dir.is_dir():
            click.secho(f"Test directory not found: {test_dir}", fg="red")
            return

        click.secho("\n=== Test Quality Audit ===\n", fg="cyan", bold=True)
        summary = audit_test_directory(test_dir)
        _safe_echo(format_audit_report(summary))
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
