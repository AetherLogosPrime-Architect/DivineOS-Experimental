"""CLI for the deletion-discipline gate — record a deletion justification.

The gate (core.deletion_discipline) blocks destructive deletions until a
fresh justification exists. This command files it: what, why, what was
investigated, what was extracted. Per [code-does-not-think], the judgment
is the operator's/agent's; this only records it so the gate can verify it
was made before the irreversible act. Prereg: prereg-251b15df9461.
"""

from __future__ import annotations

import click


def register(cli: click.Group) -> None:
    @cli.command("delete-justify")
    @click.argument("target")
    @click.option("--why", required=True, help="Why this deletion is correct")
    @click.option(
        "--investigated",
        required=True,
        help="What you read/checked to confirm nothing needed is lost",
    )
    @click.option(
        "--extracted",
        required=True,
        help="What you pulled out first (or 'nothing — superseded/empty', stated explicitly)",
    )
    def delete_justify_cmd(target: str, why: str, investigated: str, extracted: str) -> None:
        """Record a justification so the deletion-discipline gate will allow
        deleting TARGET (a branch name, path, or substring of the delete cmd).

        Fresh for 10 minutes. All fields must be substantive — hollow
        justifications are rejected (anti-Goodhart)."""
        from divineos.core.deletion_discipline import record_justification

        try:
            entry = record_justification(
                target=target, why=why, investigated=investigated, extracted=extracted
            )
        except ValueError as e:
            click.secho(f"[-] {e}", fg="red")
            raise SystemExit(1) from None

        click.secho(
            f"[+] Deletion justified: '{entry['target']}' (fresh 10 min). "
            "The gate will now allow a matching destructive deletion.",
            fg="green",
        )
        click.echo(
            "    [delete-justify] records the judgment you already made — "
            "it does not make the deletion safe; you did that by investigating."
        )
