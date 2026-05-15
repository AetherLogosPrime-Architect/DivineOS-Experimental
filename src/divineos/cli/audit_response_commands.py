"""Python entrypoint for the post-response audit pipeline.

Andrew named the gap 2026-05-14 night during the triage walk: the
operating_loop_audit pipeline was only invoked from a single .sh
hook. If the hook fails to fire (permission error, harness change,
process crash), the audit pipeline goes dark silently. The 'OS
does the work' claim was technically true at the module level —
``run_audit`` is a callable function — but operationally no Python
entrypoint invoked it, so anyone picking up the OS without Claude
Code's Stop hook would lose the audit pipeline entirely.

This CLI is the Python entrypoint. Any caller (the .sh hook, a
cron, a different IDE harness, a test) can invoke
``divineos audit-response <transcript_path>`` and get the same
audit pipeline. Channel-shape: make the right path cheap (one
command), the wrong path obvious (no audit = no findings file
updating).
"""

import json

import click


def register(cli: click.Group) -> None:
    @cli.command("audit-response")
    @click.argument("transcript_path", type=click.Path(exists=False))
    @click.option(
        "--no-write",
        is_flag=True,
        help="Run audit but don't persist findings (preview mode).",
    )
    @click.option(
        "--format",
        "fmt",
        type=click.Choice(["summary", "json"]),
        default="summary",
    )
    def audit_response_cmd(transcript_path: str, no_write: bool, fmt: str) -> None:
        """Run the post-response audit pipeline on a transcript.

        Python entrypoint for the audit pipeline (operating_loop_audit.run_audit).
        Replaces 'this only runs when the .sh hook fires' with 'this can be
        run from anywhere — the OS itself owns the audit invocation.'
        """
        from divineos.core.operating_loop_audit import run_audit

        result = run_audit(transcript_path, write=not no_write)
        if fmt == "json":
            click.echo(json.dumps(result, indent=2))
            return
        total = result.get("total_findings", 0)
        persisted = result.get("persisted", False)
        click.secho(
            f"[audit-response] total_findings={total}  persisted={persisted}",
            fg="cyan" if total else "white",
        )
        findings_log = result.get("findings_log", {})
        for detector, flags in findings_log.items():
            if flags:
                click.echo(f"  {detector}: {len(flags)} flag(s)")
