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
    def ship_claim_cmd(
        claim: str,
        test_paths: tuple[str, ...],
        executes: tuple[str, ...],
        cross_check: str,
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
            click.echo(
                f"[{e.get('git_sha', '?')}] {e.get('claim', '')[:100]}"
            )
            for t in e.get("test_paths", []):
                click.echo(f"    test: {t}")
            for x in e.get("executes", []):
                click.echo(f"    exec: {x}")
