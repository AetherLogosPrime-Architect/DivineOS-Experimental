"""CLI for falsifier-enforced ship-claim filing.

The thin CLI layer over ``divineos.core.ship_claim.ship_claim``. The
verification logic lives in the core module; this command just
collects flags and prints the result. The contract is enforced in
the core module — soften here and the verification still holds.
"""

import click

from divineos.cli._helpers import _safe_echo


def register(cli: click.Group) -> None:
    """Register ship-claim commands."""

    @cli.command("ship-claim")
    @click.argument("claim")
    @click.option(
        "--test",
        "test_paths",
        multiple=True,
        required=True,
        help=(
            "Falsifier test path (pytest-style, e.g. "
            "tests/test_x.py::TestY::test_z). Repeatable. Must pass NOW."
        ),
    )
    @click.option(
        "--executes",
        "executes",
        multiple=True,
        required=True,
        help=(
            "Production execution path (module or module:attribute) "
            "that must be importable. Repeatable."
        ),
    )
    @click.option(
        "--cross-check",
        default="",
        help="Optional shell command that must exit 0 for the claim to file.",
    )
    @click.option(
        "--actor",
        default="aether",
        help=(
            "Who is filing this claim. Required for the audit trail "
            "(Aletheia Finding 50). Defaults to 'aether' for self-"
            "filings. External actors (aletheia, grok, user) pass "
            "their own name."
        ),
    )
    def ship_claim_cmd(
        claim: str,
        test_paths: tuple[str, ...],
        executes: tuple[str, ...],
        cross_check: str,
        actor: str,
    ) -> None:
        """File a 'shipped' claim, enforced by its falsifier.

        The claim is recorded ONLY if (1) every --executes target imports
        cleanly, (2) every --test file passes pytest, (3) --cross-check
        (if given) exits 0. No filing on any failure.

        Replaces the show-fix shape — the appearance-of-fix without
        underlying behavior change — with falsifier-enforced reporting.
        """
        from divineos.core.ship_claim import ship_claim

        result = ship_claim(
            claim=claim,
            test_paths=list(test_paths),
            executes=list(executes),
            actor=actor,
            cross_check=cross_check or None,
        )
        if result.filed:
            click.secho("[+] Claim filed with falsifier-verification.", fg="green")
            if result.entry:
                click.echo(f"    git_sha: {result.entry.get('git_sha', 'unknown')}")
                click.echo(f"    tests:   {', '.join(result.entry.get('test_paths', []))}")
                click.echo(
                    f"    executes: {', '.join(result.entry.get('executes', []))}"
                )
            _safe_echo(
                "  [ship-claim] records a falsifier-verified claim — the "
                "claim is true at filing because the test ran green; the "
                "operator can re-run the test to verify any time."
            )
        else:
            click.secho("[!] Claim REJECTED — falsifier did not pass.", fg="red")
            click.echo(result.reason)
            _safe_echo(
                "  [ship-claim] refused this claim. The structural answer to "
                "'is X shipped?' is whether the falsifier runs green. It "
                "didn't. Fix the underlying gap before claiming shipped."
            )

    @cli.command("ship-claims")
    def ship_claims_list_cmd() -> None:
        """List all falsifier-verified shipped claims."""
        from divineos.core.ship_claim import list_claims

        entries = list_claims()
        if not entries:
            click.echo("No shipped claims filed yet.")
            return
        for e in entries[-50:]:
            actor = e.get("actor", "?")
            click.echo(
                f"[{e.get('git_sha', '?')}] (by {actor}) "
                f"{e.get('claim', '')[:100]}"
            )
            for t in e.get("test_paths", []):
                click.echo(f"    test: {t}")
            for x in e.get("executes", []):
                click.echo(f"    exec: {x}")

    @cli.command("ship-claims-reverify")
    def ship_claims_reverify_cmd() -> None:
        """Re-run the falsifier for every previously-filed claim.

        Closes Aletheia Finding 51: filing-time-only verification meant
        a claim filed today with pytest green stayed 'filed' forever,
        even if the production code later regressed. This command
        surfaces claims whose falsifier no longer passes.
        """
        from divineos.core.ship_claim import re_verify_all

        click.secho(
            "[~] Re-verifying all filed ship-claims... this re-runs "
            "every claim's pytest falsifier and may take a while.",
            fg="cyan",
        )
        result = re_verify_all()
        click.echo()
        click.echo(f"  Total filed:  {result['total']}")
        click.secho(f"  Still passing: {result['passing']}", fg="green")
        if result["failing"]:
            click.secho(
                f"  REGRESSED:    {result['failing']}", fg="red", bold=True
            )
            click.echo()
            click.secho("Claims whose falsifier no longer passes:", fg="red")
            for r in result["regressed"][:10]:
                click.secho(f"  - {r['claim']}", fg="red")
                for t in r.get("test_paths") or []:
                    click.echo(f"      test: {t}")
                tail = (r.get("output_tail") or "")[:200]
                if tail:
                    click.echo(f"      tail: {tail}")
        else:
            click.secho("  All filed claims still verify green.", fg="green")
