"""Merged CLI commands for relationships, questions, commitments, and temporal queries."""

import datetime
import time

import click

from divineos.cli._helpers import _resolve_knowledge_id, _safe_echo
from divineos.core.constants import SECONDS_PER_DAY
from divineos.cli._wrappers import _ensure_db
from divineos.core.knowledge.temporal import (
    format_changes_summary,
    get_changes_since,
)
from divineos.core.planning_commitments import (
    add_commitment,
    clear_commitments,
    format_commitment_review,
    fulfill_commitment,
    get_pending_commitments,
    review_commitments,
)


# ---------------------------------------------------------------------------
# Temporal commands
# ---------------------------------------------------------------------------


@click.command()
@click.option(
    "--hours",
    default=24.0,
    help="Show changes from the last N hours (default: 24).",
)
@click.option(
    "--days",
    default=0.0,
    help="Show changes from the last N days (overrides --hours).",
)
def changes(hours: float, days: float) -> None:
    """Show what changed in the knowledge store since a given time.

    Useful for session continuity: "what's different since I was last here?"
    """
    if days > 0:
        since = time.time() - (days * SECONDS_PER_DAY)
        label = f"{days:.0f} day{'s' if days != 1 else ''}"
    else:
        since = time.time() - (hours * 3600)
        label = f"{hours:.0f} hour{'s' if hours != 1 else ''}"

    result = get_changes_since(since)

    total = sum(len(v) for v in result.values())
    if total == 0:
        click.echo(f"No knowledge changes in the last {label}.")
        return

    click.secho(f"=== Knowledge changes (last {label}) ===", fg="cyan", bold=True)
    click.echo(format_changes_summary(result))


# ---------------------------------------------------------------------------
# Commitment commands
# ---------------------------------------------------------------------------


@click.group()
def commit_group() -> None:
    """Track and review agent commitments."""


@commit_group.command("add")
@click.argument("text")
@click.option("--context", "-c", default="", help="Context when commitment was made")
def commit_add(text: str, context: str) -> None:
    """Record a commitment the agent made."""
    commitment = add_commitment(text, context=context)
    click.echo(f"Commitment recorded: {commitment.text}")


@commit_group.command("list")
def commit_list() -> None:
    """Show pending commitments."""
    pending = get_pending_commitments()
    if not pending:
        click.echo("No pending commitments.")
        return

    click.echo(f"\n{len(pending)} pending commitment(s):\n")
    for i, c in enumerate(pending, 1):
        click.echo(f"  {i}. {c.text}")
        if c.context:
            click.echo(f"     Context: {c.context}")


@commit_group.command("done")
@click.argument("text")
def commit_done(text: str) -> None:
    """Mark a commitment as fulfilled."""
    if fulfill_commitment(text):
        click.echo("Commitment marked as fulfilled.")
    else:
        click.echo("No matching pending commitment found.")


@commit_group.command("review")
def commit_review() -> None:
    """Review all commitments at session end."""
    result = review_commitments()
    output = format_commitment_review(result)
    if output:
        click.echo(f"\n{output}")
    else:
        click.echo("No commitments to review.")


@commit_group.command("clear")
def commit_clear() -> None:
    """Clear all commitments (after review)."""
    clear_commitments()
    click.echo("Commitments cleared.")


# ---------------------------------------------------------------------------
# Question commands
# ---------------------------------------------------------------------------


@click.command("wonder")
@click.argument("question")
@click.option("--context", default="", help="Additional context for the question")
def wonder_cmd(question: str, context: str) -> None:
    """Record an open question -- something I'm uncertain about."""
    _ensure_db()
    from divineos.core.questions import add_question, init_questions_table

    init_questions_table()
    qid = add_question(question=question, context=context)
    click.secho(f"[?] Recorded: {question}", fg="yellow")
    click.secho(f"    ID: {qid[:8]}...", fg="bright_black")


@click.command("questions")
@click.option(
    "--status",
    default=None,
    type=click.Choice(["OPEN", "ANSWERED", "ABANDONED"], case_sensitive=False),
)
@click.option("--limit", default=20, type=int)
def questions_cmd(status: str | None, limit: int) -> None:
    """List open questions."""
    _ensure_db()
    from divineos.core.questions import get_questions, init_questions_table

    init_questions_table()
    status_upper = status.upper() if status else None
    questions = get_questions(status=status_upper, limit=limit)

    if not questions:
        click.secho("No questions found.", fg="bright_black")
        return

    label = status_upper or "ALL"
    click.secho(f"\n  {label} QUESTIONS ({len(questions)})\n", fg="yellow", bold=True)

    for q in questions:
        dt = datetime.datetime.fromtimestamp(q["created_at"])
        status_color = {
            "OPEN": "yellow",
            "ANSWERED": "green",
            "ABANDONED": "bright_black",
        }.get(q["status"], "white")

        click.secho(f"  [{q['status']}] ", fg=status_color, nl=False)
        _safe_echo(q["question"])
        click.secho(f"         {dt:%Y-%m-%d} | {q['question_id'][:8]}...", fg="bright_black")

        if q["resolution"]:
            click.secho(f"         -> {q['resolution']}", fg="green")
        click.echo()


@click.command("answer")
@click.argument("question_id")
@click.argument("resolution")
def answer_cmd(question_id: str, resolution: str) -> None:
    """Resolve an open question with an answer."""
    _ensure_db()
    from divineos.core.questions import answer_question, get_questions, init_questions_table

    init_questions_table()

    all_qs = get_questions(limit=200)
    match = None
    for q in all_qs:
        if q["question_id"].startswith(question_id):
            match = q
            break

    if not match:
        click.secho(f"No question found matching '{question_id}'", fg="red")
        return

    if answer_question(match["question_id"], resolution):
        click.secho(f"[+] Answered: {match['question'][:80]}", fg="green")
        click.secho(f"    Resolution: {resolution}", fg="bright_black")
    else:
        click.secho("Failed to update question.", fg="red")


@click.command("abandon-question")
@click.argument("question_id")
@click.option("--reason", default="", help="Why this question is being abandoned")
def abandon_cmd(question_id: str, reason: str) -> None:
    """Abandon an open question that's no longer relevant."""
    _ensure_db()
    from divineos.core.questions import abandon_question, get_questions, init_questions_table

    init_questions_table()

    all_qs = get_questions(limit=200)
    match = None
    for q in all_qs:
        if q["question_id"].startswith(question_id):
            match = q
            break

    if not match:
        click.secho(f"No question found matching '{question_id}'", fg="red")
        return

    if abandon_question(match["question_id"], reason):
        click.secho(f"[--] Abandoned: {match['question'][:80]}", fg="bright_black")
    else:
        click.secho("Failed to update question.", fg="red")


# ---------------------------------------------------------------------------
# Relationship commands
# ---------------------------------------------------------------------------


@click.command("relate")
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


@click.command("related")
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


@click.command("graph")
@click.option("--center", default=None, help="Knowledge ID to center the graph on")
@click.option("--depth", default=2, type=int, help="Traversal depth from center")
@click.option(
    "--format",
    "fmt",
    default="mermaid",
    type=click.Choice(["mermaid", "json"]),
    help="Export format",
)
def graph_cmd(center: str | None, depth: int, fmt: str) -> None:
    """Export the knowledge graph as Mermaid or JSON."""
    from divineos.core.knowledge.edges import graph_export

    center_id = None
    if center:
        try:
            center_id = _resolve_knowledge_id(center)
        except click.ClickException:
            raise

    result = graph_export(center_id=center_id, depth=depth, fmt=fmt)
    if fmt == "mermaid":
        click.echo("```mermaid")
        click.echo(result)
        click.echo("```")
    else:
        click.echo(result)


@click.command("unrelate")
@click.argument("relationship_id")
def unrelate_cmd(relationship_id: str) -> None:
    """Remove a relationship by its ID."""
    from divineos.core.knowledge.relationships import remove_relationship

    if remove_relationship(relationship_id):
        click.secho(f"[+] Removed relationship {relationship_id[:8]}...", fg="green")
    else:
        click.secho(f"[-] Relationship {relationship_id} not found.", fg="yellow")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(cli: click.Group) -> None:
    """Register all entity commands (temporal, commitment, question, relationship)."""
    # Temporal
    cli.add_command(changes)

    # Commitments
    cli.add_command(commit_group, "commitment")

    # Questions
    cli.add_command(wonder_cmd)
    cli.add_command(questions_cmd)
    cli.add_command(answer_cmd)
    cli.add_command(abandon_cmd)

    # Relationships
    cli.add_command(relate_cmd)
    cli.add_command(related_cmd)
    cli.add_command(graph_cmd)
    cli.add_command(unrelate_cmd)
