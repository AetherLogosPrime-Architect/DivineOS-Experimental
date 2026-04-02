"""CLI commands for Self-Model, Skill Library, Curiosity Engine, Drift Detection, Predictions."""

import click


def register(cli: click.Group) -> None:
    """Register self-model and related commands."""

    @cli.command("self-model")
    def self_model_cmd() -> None:
        """Display the unified self-model — who I am, from evidence."""
        from divineos.core.self_model import build_self_model, format_self_model

        model = build_self_model()
        click.echo(format_self_model(model))

    @cli.command("drift")
    def drift_cmd() -> None:
        """Check for behavioral drift from stated principles."""
        from divineos.core.drift_detection import format_drift_report, run_drift_detection

        report = run_drift_detection()
        click.echo(format_drift_report(report))

    @cli.command("predict")
    @click.argument("events", nargs=-1)
    def predict_cmd(events: tuple[str, ...]) -> None:
        """Predict session needs based on current activity and history."""
        from divineos.core.predictive_session import format_predictions, predict_session_needs

        result = predict_session_needs(current_events=list(events) if events else None)
        click.echo(format_predictions(result))

    @cli.command("knowledge-compress")
    @click.option("--strategy", "-s", multiple=True, help="Strategies: dedup, synthesize, graph")
    @click.option("--type", "-t", "knowledge_type", default=None, help="Filter by knowledge type")
    def compress_cmd(strategy: tuple[str, ...], knowledge_type: str | None) -> None:
        """Compress redundant knowledge into denser representations."""
        from divineos.core.knowledge.compression import format_compression_report, run_compression

        strategies = list(strategy) if strategy else None
        results = run_compression(knowledge_type=knowledge_type, strategies=strategies)
        click.echo(format_compression_report(results))

    @cli.group("skill")
    def skill_group() -> None:
        """Track agent skills and proficiency."""

    @skill_group.command("list")
    def skill_list() -> None:
        """Show all tracked skills."""
        from divineos.core.skill_library import format_skill_summary

        click.echo(format_skill_summary())

    @skill_group.command("record")
    @click.argument("name")
    @click.option("--success/--failure", default=True, help="Was the skill used successfully?")
    def skill_record(name: str, success: bool) -> None:
        """Record a skill being used."""
        from divineos.core.skill_library import record_skill_use

        result = record_skill_use(name, success=success)
        click.echo(
            f"Recorded {name}: {result['proficiency']} ({result['successes']}✓ {result['failures']}✗)"
        )

    @cli.group("curiosity")
    def curiosity_group() -> None:
        """Track questions worth investigating."""

    @curiosity_group.command("add")
    @click.argument("question")
    @click.option("--category", "-c", default="general")
    def curiosity_add(question: str, category: str) -> None:
        """File a new curiosity."""
        from divineos.core.curiosity_engine import add_curiosity

        result = add_curiosity(question, category=category)
        click.echo(f"Curiosity filed: {result['question']}")

    @curiosity_group.command("list")
    def curiosity_list() -> None:
        """Show open curiosities."""
        from divineos.core.curiosity_engine import format_curiosities

        click.echo(format_curiosities())

    @curiosity_group.command("answer")
    @click.argument("question")
    @click.argument("answer")
    def curiosity_answer(question: str, answer: str) -> None:
        """Mark a curiosity as answered."""
        from divineos.core.curiosity_engine import answer_curiosity

        if answer_curiosity(question, answer):
            click.echo("Curiosity answered.")
        else:
            click.echo("No matching open curiosity found.")

    @curiosity_group.command("note")
    @click.argument("question")
    @click.argument("note")
    def curiosity_note(question: str, note: str) -> None:
        """Add a note to a curiosity."""
        from divineos.core.curiosity_engine import add_note

        if add_note(question, note):
            click.echo("Note added.")
        else:
            click.echo("No matching open curiosity found.")

    @cli.command("affect-feedback")
    def affect_feedback_cmd() -> None:
        """Show how affect states are influencing behavior."""
        from divineos.core.affect_feedback import format_affect_feedback, get_session_affect_context

        context = get_session_affect_context()
        click.echo(format_affect_feedback(context))
