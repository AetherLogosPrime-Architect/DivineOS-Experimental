"""Insight commands — opinion, user-model, calibrate, advice, critique, recommend.

Groups the six self-assessment improvements into CLI commands.
"""

import sqlite3

import click

from divineos.cli._helpers import _safe_echo

_IC_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


def register(cli: click.Group) -> None:
    """Register insight commands on the CLI group."""

    # ─── Opinion Store ───────────────────────────────────────────

    @cli.group(invoke_without_command=True)
    @click.pass_context
    def opinion(ctx: click.Context) -> None:
        """Manage structured opinions (judgments formed from evidence)."""
        if ctx.invoked_subcommand is None:
            ctx.invoke(opinion_list)

    @opinion.command("add")
    @click.argument("topic")
    @click.argument("position")
    @click.option("--confidence", default=0.7, type=float, help="Confidence 0.0-1.0")
    @click.option("--evidence", multiple=True, help="Supporting evidence (repeatable)")
    @click.option("--tags", default="", help="Comma-separated tags")
    def opinion_add(
        topic: str, position: str, confidence: float, evidence: tuple[str, ...], tags: str
    ) -> None:
        """Store a new opinion on a topic."""
        from divineos.core.opinion_store import store_opinion

        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        oid = store_opinion(topic, position, confidence, list(evidence), tag_list)
        _safe_echo(click.style(f"[+] Opinion stored: {oid}", fg="green"))

    @opinion.command("list")
    @click.option("--topic", default=None, help="Filter by topic")
    @click.option("--min-confidence", default=0.0, type=float, help="Minimum confidence")
    def opinion_list(topic: str | None, min_confidence: float) -> None:
        """List active opinions."""
        from divineos.core.opinion_store import format_opinions, get_opinions

        opinions = get_opinions(topic=topic, min_confidence=min_confidence)
        _safe_echo(format_opinions(opinions))

    @opinion.command("history")
    @click.argument("topic")
    def opinion_history(topic: str) -> None:
        """Show how an opinion on a topic evolved over time."""
        from divineos.core.opinion_store import get_opinion_history

        history = get_opinion_history(topic)
        if not history:
            _safe_echo(click.style(f"No opinions found for topic: {topic}", fg="yellow"))
            return
        for i, op in enumerate(history):
            status = "ACTIVE" if op["superseded_by"] is None else "SUPERSEDED"
            _safe_echo(f"  {i + 1}. [{status}] {op['position']}")
            _safe_echo(f"     confidence: {op['confidence']:.0%}")

    @opinion.command("strengthen")
    @click.argument("opinion_id")
    @click.argument("evidence")
    def opinion_strengthen(opinion_id: str, evidence: str) -> None:
        """Add supporting evidence to an opinion."""
        from divineos.core.opinion_store import strengthen_opinion

        new_conf = strengthen_opinion(opinion_id, evidence)
        if new_conf > 0:
            _safe_echo(click.style(f"[+] Strengthened to {new_conf:.0%}", fg="green"))
        else:
            _safe_echo(click.style("[-] Opinion not found.", fg="red"))

    @opinion.command("challenge")
    @click.argument("opinion_id")
    @click.argument("evidence")
    def opinion_challenge(opinion_id: str, evidence: str) -> None:
        """Add contradicting evidence to an opinion."""
        from divineos.core.opinion_store import challenge_opinion

        new_conf = challenge_opinion(opinion_id, evidence)
        if new_conf > 0:
            _safe_echo(click.style(f"[!] Weakened to {new_conf:.0%}", fg="yellow"))
        else:
            _safe_echo(click.style("[-] Opinion not found.", fg="red"))

    # ─── User Model ──────────────────────────────────────────────

    @cli.command("user-model")
    @click.option("--name", default="default", help="User name")
    def user_model_cmd(name: str) -> None:
        """Show the current user model."""
        from divineos.core.user_model import format_user_model

        _safe_echo(format_user_model(name))

    @cli.command("user-signal")
    @click.argument("signal_type")
    @click.argument("content")
    @click.option("--user", default="default", help="User name")
    def user_signal_cmd(signal_type: str, content: str, user: str) -> None:
        """Record a user behavior signal."""
        from divineos.core.user_model import SIGNAL_TYPES, record_signal

        if signal_type not in SIGNAL_TYPES:
            _safe_echo(
                click.style(
                    f"[-] Unknown signal type. Valid: {', '.join(sorted(SIGNAL_TYPES))}",
                    fg="red",
                )
            )
            return
        sid = record_signal(signal_type, content, user_name=user)
        _safe_echo(click.style(f"[+] Signal recorded: {sid}", fg="green"))

    # ─── Communication Calibration ────────────────────────────────

    @cli.command("calibrate")
    @click.option("--user", default="default", help="User name")
    def calibrate_cmd(user: str) -> None:
        """Show communication calibration for a user."""
        from divineos.core.communication_calibration import calibrate, format_calibration

        guidance = calibrate(user)
        _safe_echo(format_calibration(guidance))

    # ─── Advice Tracking ─────────────────────────────────────────

    @cli.group(invoke_without_command=True)
    @click.pass_context
    def advice(ctx: click.Context) -> None:
        """Track advice quality over time."""
        if ctx.invoked_subcommand is None:
            ctx.invoke(advice_pending)

    @advice.command("record")
    @click.argument("content")
    @click.option("--context", default="", help="What situation prompted this advice")
    @click.option(
        "--category", default="general", help="Category: architecture/pattern/process/debugging"
    )
    def advice_record(content: str, context: str, category: str) -> None:
        """Record a piece of advice given."""
        from divineos.core.advice_tracking import record_advice

        aid = record_advice(content, context=context, category=category)
        _safe_echo(click.style(f"[+] Advice recorded: {aid}", fg="green"))

    @advice.command("assess")
    @click.argument("advice_id")
    @click.argument(
        "outcome",
        type=click.Choice(["successful", "partially_successful", "failed", "inconclusive"]),
    )
    @click.option("--evidence", default="", help="What happened")
    def advice_assess(advice_id: str, outcome: str, evidence: str) -> None:
        """Record the outcome of advice given."""
        from divineos.core.advice_tracking import assess_advice

        result = assess_advice(advice_id, outcome, evidence)
        if result:
            _safe_echo(click.style(f"[+] Assessed as: {outcome}", fg="green"))
        else:
            _safe_echo(click.style("[-] Advice not found.", fg="red"))

    @advice.command("stats")
    def advice_stats() -> None:
        """Show advice quality statistics."""
        from divineos.core.advice_tracking import format_advice_stats

        _safe_echo(format_advice_stats())

    @advice.command("pending")
    def advice_pending() -> None:
        """Show advice that needs outcome assessment."""
        from divineos.core.advice_tracking import get_pending_advice

        pending = get_pending_advice()
        if not pending:
            _safe_echo("No pending advice assessments.")
            return
        for adv in pending:
            _safe_echo(f"  {adv['advice_id']}: {adv['content'][:80]}")
            if adv["context"]:
                _safe_echo(f"    context: {adv['context'][:60]}")

    # ─── Self-Critique ────────────────────────────────────────────

    @cli.command("critique")
    @click.option("--session-id", default="", help="Session ID to assess")
    def critique_cmd(session_id: str) -> None:
        """Run craft self-assessment for current session."""
        from divineos.core.self_critique import assess_session_craft, format_craft_assessment

        assessment = assess_session_craft(session_id)
        _safe_echo(format_craft_assessment(assessment))

    @cli.command("craft-trends")
    @click.option("--n", default=5, type=int, help="Number of recent sessions to analyze")
    def craft_trends_cmd(n: int) -> None:
        """Show craft quality trends across sessions."""
        from divineos.core.self_critique import format_craft_trends, get_craft_trends

        trends = get_craft_trends(n)
        _safe_echo(format_craft_trends(trends))

    # ─── Proactive Recommendations ────────────────────────────────

    @cli.command("recommend")
    @click.argument("context")
    def recommend_cmd(context: str) -> None:
        """Get proactive recommendations for a given context."""
        from divineos.core.proactive_patterns import get_full_context_advice

        result = get_full_context_advice(context)
        if result:
            _safe_echo(result)
        else:
            _safe_echo("No specific recommendations for this context.")
