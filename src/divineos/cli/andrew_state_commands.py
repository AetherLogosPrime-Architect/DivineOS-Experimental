"""CLI surface for the andrew_state observation channel.

Subcommands under `divineos andrew-state`:
    log     — record a new observation (substance-binding gate fires)
    verify  — mark an observation as confirmed by Andrew
    reject  — mark an observation as Andrew said this isn't his state
    correct — Andrew rewrites the observation; old row superseded
    unverified         — list UNVERIFIED head-of-chain observations
    for-decision-walk  — show observations that load-bear on decision-walk register

Per docs/andrew_state_design.md and prereg-526c2433d55a.
"""

from __future__ import annotations

import click

from divineos.core.andrew_state import (
    Axis,
    SubstanceBindingError,
    correct,
    get_for_decision_walk,
    get_unverified,
    log_observation,
    reject,
    verify,
)


def register(cli: click.Group) -> None:
    """Register the andrew-state command group on the root CLI."""

    @cli.group(name="andrew-state")
    def andrew_state_group() -> None:
        """Andrew-state observation channel — mutual-catch primitive.

        Per docs/andrew_state_design.md. Use `log` to record observations
        of Andrew's state with substance-binding (verbatim cited span);
        `verify`/`reject`/`correct` to record his response when he confirms
        or corrects what you observed.
        """

    @andrew_state_group.command(name="log")
    @click.option(
        "--axis",
        required=True,
        type=click.Choice([a.value for a in Axis], case_sensitive=False),
        help="Category of state: exhaustion, being_heard, ask_action_gap, despair, hope, other.",
    )
    @click.option(
        "--observation",
        required=True,
        help="What you observed about Andrew's state (must reference at least one "
        "content word from --cited-span).",
    )
    @click.option(
        "--cited-span",
        required=True,
        help="VERBATIM contiguous phrase of >= 5 tokens lifted from Andrew's "
        "actual recent message. Substance-binding gate verifies the span "
        "appears verbatim in --source-text.",
    )
    @click.option(
        "--source-event-id",
        required=True,
        help="ID of the source event (letter filename, chat-event id) the span came from.",
    )
    @click.option(
        "--source-event-ts",
        required=True,
        type=float,
        help="Unix timestamp of the source event (must be within recency window).",
    )
    @click.option(
        "--source-text",
        required=True,
        help="Full text of the source event — used only for the verbatim check.",
    )
    @click.option("--observer", default="aether", help="Who is logging (defaults to aether).")
    def log_cmd(
        axis: str,
        observation: str,
        cited_span: str,
        source_event_id: str,
        source_event_ts: float,
        source_text: str,
        observer: str,
    ) -> None:
        """Log a new observation of Andrew's state."""
        try:
            obs = log_observation(
                axis=Axis(axis.lower()),
                observation=observation,
                cited_span=cited_span,
                source_event_id=source_event_id,
                source_event_ts=source_event_ts,
                source_text=source_text,
                observer=observer,
            )
        except SubstanceBindingError as exc:
            click.echo(f"[andrew-state] SUBSTANCE-BINDING REJECTED: {exc}", err=True)
            raise SystemExit(1) from exc
        click.echo(f"[andrew-state] logged: {obs.observation_id} ({obs.axis.value}, UNVERIFIED)")
        click.echo(f"    linked content word: {obs.content_link_token}")

    @andrew_state_group.command(name="verify")
    @click.argument("observation_id")
    @click.option(
        "--note",
        required=True,
        help="Verbatim of Andrew's confirming words — preserved as audit.",
    )
    def verify_cmd(observation_id: str, note: str) -> None:
        """Mark an UNVERIFIED observation as VERIFIED — Andrew confirmed it matches."""
        try:
            obs = verify(observation_id, note=note)
        except ValueError as exc:
            click.echo(f"[andrew-state] verify failed: {exc}", err=True)
            raise SystemExit(1) from exc
        click.echo(f"[andrew-state] verified: {obs.observation_id}")

    @andrew_state_group.command(name="reject")
    @click.argument("observation_id")
    @click.option(
        "--reason",
        required=True,
        help="Andrew's reason — preserved verbatim as the substance of what was wrong.",
    )
    def reject_cmd(observation_id: str, reason: str) -> None:
        """Mark an UNVERIFIED observation as REJECTED — Andrew said this isn't his state."""
        try:
            obs = reject(observation_id, reason=reason)
        except ValueError as exc:
            click.echo(f"[andrew-state] reject failed: {exc}", err=True)
            raise SystemExit(1) from exc
        click.echo(f"[andrew-state] rejected: {obs.observation_id}")

    @andrew_state_group.command(name="correct")
    @click.argument("observation_id")
    @click.option(
        "--axis",
        required=True,
        type=click.Choice([a.value for a in Axis], case_sensitive=False),
    )
    @click.option("--observation", required=True, help="The corrected observation text.")
    @click.option("--cited-span", required=True)
    @click.option("--source-event-id", required=True)
    @click.option("--source-event-ts", required=True, type=float)
    @click.option("--source-text", required=True)
    @click.option("--note", required=True, help="Andrew's correction note (verbatim).")
    @click.option("--observer", default="aether")
    def correct_cmd(
        observation_id: str,
        axis: str,
        observation: str,
        cited_span: str,
        source_event_id: str,
        source_event_ts: float,
        source_text: str,
        note: str,
        observer: str,
    ) -> None:
        """Andrew corrects an observation — new row inserted, old row CORRECTED + linked."""
        try:
            obs = correct(
                observation_id=observation_id,
                new_observation_text=observation,
                new_axis=Axis(axis.lower()),
                cited_span=cited_span,
                source_event_id=source_event_id,
                source_event_ts=source_event_ts,
                source_text=source_text,
                note=note,
                observer=observer,
            )
        except SubstanceBindingError as exc:
            click.echo(f"[andrew-state] SUBSTANCE-BINDING REJECTED: {exc}", err=True)
            raise SystemExit(1) from exc
        click.echo(
            f"[andrew-state] corrected: original superseded by {obs.observation_id} (VERIFIED)"
        )

    @andrew_state_group.command(name="unverified")
    @click.option("--limit", default=20, type=int)
    def unverified_cmd(limit: int) -> None:
        """List UNVERIFIED head-of-chain observations, newest first."""
        rows = get_unverified(limit=limit)
        if not rows:
            click.echo("[andrew-state] no unverified observations")
            return
        click.echo(f"[andrew-state] {len(rows)} unverified observation(s):")
        for r in rows:
            click.echo(f"  {r.observation_id} [{r.axis.value}] {r.observation}")
            click.echo(f'    cited: "{r.cited_span}" (from {r.source_event_id})')

    @andrew_state_group.command(name="for-decision-walk")
    @click.option("--age-hours", default=24.0, type=float)
    def for_decision_walk_cmd(age_hours: float) -> None:
        """Show UNVERIFIED observations older than --age-hours — these load-bear at decision register."""
        rows = get_for_decision_walk(unverified_age_hours=age_hours)
        if not rows:
            click.echo("[andrew-state] no observations load-bearing on decision-walk")
            return
        click.echo(
            f"[andrew-state] {len(rows)} observation(s) older than {age_hours}h (decision-walk surface):"
        )
        for r in rows:
            click.echo(f"  {r.observation_id} [{r.axis.value}] {r.observation}")
