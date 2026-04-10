"""CLI commands for Self-Model, Skill Library, Curiosity Engine, Drift Detection, Predictions."""

import click


def register(cli: click.Group) -> None:
    """Register self-model and related commands."""

    @cli.command("self-model")
    def self_model_cmd() -> None:
        """Display the unified self-model -- who I am, from evidence."""
        from divineos.cli._helpers import _safe_echo
        from divineos.core.self_model import build_self_model, format_self_model

        model = build_self_model()
        _safe_echo(format_self_model(model))

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

    @cli.group("skill", invoke_without_command=True)
    @click.pass_context
    def skill_group(ctx: click.Context) -> None:
        """Track agent skills and proficiency."""
        if ctx.invoked_subcommand is None:
            ctx.invoke(skill_list)

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
            f"Recorded {name}: {result['proficiency']} ({result['successes']}+ {result['failures']}x)"
        )

    @cli.group("curiosity", invoke_without_command=True)
    @click.pass_context
    def curiosity_group(ctx: click.Context) -> None:
        """Track questions worth investigating."""
        if ctx.invoked_subcommand is None:
            ctx.invoke(curiosity_list)

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

    @curiosity_group.command("wonder")
    @click.option("--max", "max_q", default=5, type=int, help="Max questions to generate")
    def curiosity_wonder(max_q: int) -> None:
        """Auto-generate questions from knowledge gaps.

        Scans the knowledge store for hypotheses needing evidence,
        stuck lessons, shelved contradictions, and popular-but-unvalidated
        entries. Files them as OPEN curiosities.
        """
        from divineos.core.curiosity_engine import generate_curiosities_from_gaps

        generated = generate_curiosities_from_gaps(max_questions=max_q)
        if generated:
            click.secho(f"Generated {len(generated)} question(s):\n", fg="cyan")
            for g in generated:
                click.echo(f"  ? {g.get('question', '?')[:100]}")
                click.secho(f"    [{g.get('category', '?')}]", fg="bright_black")
        else:
            click.echo("No gaps found -- knowledge store looks complete.")

    @curiosity_group.command("shelve")
    @click.argument("question")
    def curiosity_shelve(question: str) -> None:
        """Put a curiosity to sleep — not abandoned, just not active."""
        from divineos.core.curiosity_engine import shelve_curiosity

        if shelve_curiosity(question):
            click.echo("Curiosity shelved.")
        else:
            click.echo("No matching open curiosity found.")

    @cli.command("attention")
    def attention_cmd() -> None:
        """Display the attention schema -- what I'm attending to and why."""
        from divineos.cli._helpers import _safe_echo
        from divineos.core.attention_schema import build_attention_schema, format_attention_schema

        schema = build_attention_schema()
        output = format_attention_schema(schema)
        _safe_echo(output)

    @cli.command("epistemic")
    def epistemic_cmd() -> None:
        """Show epistemic status -- how I know what I know."""
        from divineos.cli._helpers import _safe_echo
        from divineos.core.epistemic_status import build_epistemic_report, format_epistemic_report

        report = build_epistemic_report()
        output = format_epistemic_report(report)
        _safe_echo(output)

    @cli.command("affect-feedback")
    def affect_feedback_cmd() -> None:
        """Show how affect states are influencing behavior."""
        from divineos.core.affect import format_affect_feedback, get_session_affect_context

        context = get_session_affect_context()
        click.echo(format_affect_feedback(context))

    @cli.command("knowledge-hygiene")
    @click.option("--no-demote", is_flag=True, help="Skip noise demotion")
    @click.option("--no-decay", is_flag=True, help="Skip stale decay")
    @click.option("--no-orphans", is_flag=True, help="Skip orphan flagging")
    def knowledge_hygiene_cmd(no_demote: bool, no_decay: bool, no_orphans: bool) -> None:
        """Audit and clean the knowledge store — demote noise, decay stale, flag orphans."""
        from divineos.core.knowledge_maintenance import format_hygiene_report, run_knowledge_hygiene

        report = run_knowledge_hygiene(
            demote_noise=not no_demote,
            decay_stale=not no_decay,
            flag_orphans=not no_orphans,
        )
        click.echo(format_hygiene_report(report))
