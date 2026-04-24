"""CLI commands for EMPIRICA — corroboration provenance and kappa.

Exposes two operator-facing entry points:

* ``divineos corroborate`` — record a corroboration event on a
  knowledge row, with explicit actor + kind + optional evidence
  pointer. Replaces the invisible access-count auto-bump with a
  traceable event.

* ``divineos kappa`` — run the classifier against its gold
  fixture and print inter-rater agreement. A diagnostic, not a
  grade: the number shows how well the classifier matches the
  handwritten labels. Low kappa = fixture and classifier disagree;
  inspect the confusion matrix to find which cases.
"""

from __future__ import annotations

import click

from divineos.core.empirica.kappa import measure_classifier_agreement
from divineos.core.empirica.provenance import (
    CorroborationKind,
    count_by_kind,
    count_distinct_corroborators,
    record_corroboration,
)


def register(cli: click.Group) -> None:
    """Attach EMPIRICA commands to the top-level CLI group."""

    @cli.command("corroborate")
    @click.argument("knowledge_id")
    @click.option(
        "--actor",
        required=True,
        help='Who/what is corroborating (e.g. "user:<operator>", "council:popper", "audit:grok")',
    )
    @click.option(
        "--kind",
        type=click.Choice([k.value for k in CorroborationKind]),
        default=CorroborationKind.USER.value,
        help="Kind of corroboration. ACCESS and LEGACY are excluded from distinct-actor counts.",
    )
    @click.option(
        "--pointer", default=None, help="Optional pointer to the evidence (commit, URL, event_id)."
    )
    @click.option("--notes", default=None, help="Free-form notes for the record.")
    def corroborate(
        knowledge_id: str,
        actor: str,
        kind: str,
        pointer: str | None,
        notes: str | None,
    ) -> None:
        """Record a corroboration event on a knowledge row.

        The knowledge_id is the target. The actor is yourself or
        another rater. Kind should reflect what actually happened
        (not what sounds most impressive).
        """
        ev = record_corroboration(
            knowledge_id=knowledge_id,
            actor=actor,
            kind=CorroborationKind(kind),
            evidence_pointer=pointer,
            notes=notes,
        )
        click.echo(f"[+] Recorded: {ev.event_id}")
        click.echo(f"    actor={actor}  kind={kind}")
        if pointer:
            click.echo(f"    pointer={pointer}")

        distinct = count_distinct_corroborators(knowledge_id)
        by_kind = count_by_kind(knowledge_id)
        click.echo(f"    distinct evidential actors: {distinct}")
        click.echo("    by kind:")
        for k, n in sorted(by_kind.items(), key=lambda x: x[0].value):
            click.echo(f"      {k.value:24s} {n}")

    @cli.command("kappa")
    @click.option(
        "--verbose",
        "-v",
        is_flag=True,
        help="Show the full confusion matrix and per-label marginals.",
    )
    def kappa(verbose: bool) -> None:
        """Measure classifier agreement against the gold fixture.

        Cohen's kappa corrects for chance agreement. A high kappa
        means the classifier's labels match the gold fixture beyond
        what you'd get randomly; a low kappa means they don't.
        Neither is a pass/fail — it's a diagnostic.
        """
        result = measure_classifier_agreement()

        # Landis & Koch reference
        if result.kappa < 0:
            band = "worse than chance"
        elif result.kappa <= 0.20:
            band = "slight"
        elif result.kappa <= 0.40:
            band = "fair"
        elif result.kappa <= 0.60:
            band = "moderate"
        elif result.kappa <= 0.80:
            band = "substantial"
        else:
            band = "near-perfect"

        click.echo(f"Cohen's kappa: {result.kappa:.3f}  ({band})")
        click.echo(f"  observed agreement:  {result.observed_agreement:.3f}")
        click.echo(f"  expected by chance:  {result.expected_agreement:.3f}")
        click.echo(f"  n items:             {result.n}")

        if verbose:
            click.echo("")
            click.echo("Confusion matrix (gold -> classifier):")
            for a_label in sorted(result.confusion.keys()):
                for b_label in sorted(result.confusion[a_label].keys()):
                    count = result.confusion[a_label][b_label]
                    if count == 0:
                        continue
                    marker = "=" if a_label == b_label else "X"
                    click.echo(
                        f"  {marker}  gold={a_label:14s} -> classifier={b_label:14s}  {count}"
                    )
            click.echo("")
            click.echo("Per-label marginals:")
            for label in sorted(set(result.per_label_counts_a) | set(result.per_label_counts_b)):
                a = result.per_label_counts_a.get(label, 0)
                b = result.per_label_counts_b.get(label, 0)
                click.echo(f"  {label:14s}  gold={a}  classifier={b}")
