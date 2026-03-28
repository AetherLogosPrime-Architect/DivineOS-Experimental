"""CLI commands for open questions — track and resolve uncertainty."""

import datetime

import click

from divineos.cli._helpers import _safe_echo
from divineos.cli._wrappers import _ensure_db


def register(cli: click.Group) -> None:
    """Register question commands on the CLI group."""

    @cli.command("wonder")
    @click.argument("question")
    @click.option("--context", default="", help="Additional context for the question")
    def wonder_cmd(question: str, context: str) -> None:
        """Record an open question — something I'm uncertain about."""
        _ensure_db()
        from divineos.core.questions import add_question, init_questions_table

        init_questions_table()
        qid = add_question(question=question, context=context)
        click.secho(f"[?] Recorded: {question}", fg="yellow")
        click.secho(f"    ID: {qid[:8]}...", fg="bright_black")

    @cli.command("questions")
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
                click.secho(f"         → {q['resolution']}", fg="green")
            click.echo()

    @cli.command("answer")
    @click.argument("question_id")
    @click.argument("resolution")
    def answer_cmd(question_id: str, resolution: str) -> None:
        """Resolve an open question with an answer."""
        _ensure_db()
        from divineos.core.questions import answer_question, get_questions, init_questions_table

        init_questions_table()

        # Support partial IDs
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
            click.secho(f"[✓] Answered: {match['question'][:80]}", fg="green")
            click.secho(f"    Resolution: {resolution}", fg="bright_black")
        else:
            click.secho("Failed to update question.", fg="red")

    @cli.command("abandon-question")
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
            click.secho(f"[—] Abandoned: {match['question'][:80]}", fg="bright_black")
        else:
            click.secho("Failed to update question.", fg="red")
