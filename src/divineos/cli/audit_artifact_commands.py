"""Audit artifact CLI — pre-commit tree-hash binding for guardrail changes.

The chicken-egg problem this solves: the commit-msg hook requires
External-Review: <round_id> in the trailer for guardrail-touching
changes. The round, in turn, requires the auditor to read the diff —
which means the diff must be reachable on origin. But the diff only
gets to origin via the commit, which requires the trailer, which
requires the round. Loop.

Before this command existed, the only escape was emergency_bypass.
Repeated bypass-use makes the gate ceremonial — exactly the
drift-through-success pattern Dekker names.

The fix uses git's native object model: a guardrail-touching change
gets staged, then this command:
  1. Runs `git write-tree` to compute the tree-hash of the staged state.
  2. Creates an orphan commit via `git commit-tree` (plumbing, does
     NOT invoke the commit-msg hook).
  3. Pushes that commit to `refs/audit/<slug>` on origin.
  4. Prints the tree-hash, ref, and ready-to-run submit-round command.

The auditor (Aletheia / user) fetches the ref, reads the diff, and
files a round naming `--source-ref refs/audit/<slug>` and
`--notes "tree-hash: <hash>"`. The existing reachability check in
audit_commands.submit-round verifies the tree-hash is reachable on
the ref. The orphan commit can never merge to main (no branch points
at it), so this is artifact-only.

At commit-time, the commit-msg hook (already in place) validates that
`External-Review: <round_id>` references a round whose cited tree-hash
matches `git write-tree` at commit-time. Mismatch → block. The fingerprint
binding is reproducible across vantages (Aletheia's empirical finding,
PR-context 2026-05-31): tree-hashes survive cross-vantage verification;
diff-hashes do not.

Council-walked 2026-06-01 (Schneier / Popper / Dekker / Taleb /
Yudkowsky) before build — convergence: precision-increase, not new gate.

Non-guardrail module: this command CREATES audit artifacts, it does
NOT enforce. Enforcement still lives in audit_commands.py (guardrail)
and the commit-msg hook (guardrail). Adding new entry points to the
audit-artifact creation surface does not weaken enforcement.
"""

from __future__ import annotations

import subprocess

import click


def _run(args: list[str], check: bool = True) -> str:
    """Run a git command, return stdout stripped. Raise on nonzero if check."""
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        raise click.ClickException(
            f"git command failed: {' '.join(args)}\nstderr: {result.stderr.strip()}"
        )
    return (result.stdout or "").strip()


def register(cli: click.Group) -> None:
    """Register audit-artifact subcommands into the existing audit group."""
    audit_group = cli.commands.get("audit")
    if audit_group is None or not isinstance(audit_group, click.Group):
        # audit_commands.register hasn't run yet, or audit isn't a group.
        # Fail loud — the registration ORDER in cli/__init__.py matters.
        raise RuntimeError(
            "audit_artifact_commands.register must run AFTER "
            "audit_commands.register (which creates the 'audit' group)."
        )

    @audit_group.command("prepare-artifact")
    @click.option(
        "--message",
        "-m",
        default="audit-artifact: staged change for review",
        help="Annotation on the orphan commit (auditor will read this).",
    )
    @click.option(
        "--slug",
        default=None,
        help=(
            "Slug for refs/audit/<slug>. Defaults to first 12 chars of "
            "the tree-hash, which is content-addressed and deterministic."
        ),
    )
    @click.option(
        "--remote",
        default="origin",
        help="Remote to push the audit ref to. Default: origin.",
    )
    @click.option(
        "--dry-run",
        is_flag=True,
        default=False,
        help="Compute tree-hash and slug; do not create commit or push.",
    )
    def audit_prepare_artifact(message: str, slug: str | None, remote: str, dry_run: bool) -> None:
        """Create an audit artifact from the currently staged change.

        Output: tree-hash, ref name, and the ready-to-run submit-round
        command for the auditor to file the review round against.

        The orphan commit is created via `git commit-tree` (plumbing,
        no hooks) and pushed to refs/audit/<slug>. It can never merge
        to main — there's no branch pointing at it. Pure artifact.
        """
        # 1. Verify there ARE staged changes.
        diff_check = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True,
        )
        if diff_check.returncode == 0:
            raise click.ClickException(
                "No staged changes. Stage the guardrail change first "
                "with `git add <files>`, then re-run prepare-artifact."
            )

        # 2. Compute tree-hash of staged state.
        tree_hash = _run(["git", "write-tree"])
        if not tree_hash:
            raise click.ClickException("git write-tree produced no output")

        # 3. Derive slug if not supplied (content-addressed, deterministic).
        if slug is None:
            slug = tree_hash[:12]

        ref = f"refs/audit/{slug}"

        # Honest dry-run — print plan, no side effects.
        if dry_run:
            click.secho(f"[dry-run] tree-hash: {tree_hash}", fg="cyan")
            click.secho(f"[dry-run] ref: {ref}", fg="cyan")
            click.secho(f"[dry-run] remote: {remote}", fg="cyan")
            click.secho("[dry-run] no commit-tree, no push.", fg="yellow")
            return

        # 4. Get current HEAD to parent the orphan commit (gives auditor
        #    a base for `git show <commit>` to render readable diff).
        head_sha = _run(["git", "rev-parse", "HEAD"])

        # 5. Create the orphan commit via plumbing. Hooks DO NOT run.
        commit_message = f"{message}\n\ntree-hash: {tree_hash}\n"
        commit_sha = _run(["git", "commit-tree", tree_hash, "-p", head_sha, "-m", commit_message])
        if not commit_sha:
            raise click.ClickException("git commit-tree produced no output")

        # 6. Push to refs/audit/<slug>. --force-with-lease in case of
        #    re-prepare of same staged state (slug stable on tree-hash).
        push_spec = f"{commit_sha}:{ref}"
        push_result = subprocess.run(
            ["git", "push", "--force-with-lease", remote, push_spec],
            capture_output=True,
            text=True,
        )
        if push_result.returncode != 0:
            raise click.ClickException(
                f"git push failed:\nstdout: {push_result.stdout}\nstderr: {push_result.stderr}"
            )

        # 7. Print the ready-to-run submit-round command.
        click.secho("", fg="white")
        click.secho("[+] Audit artifact prepared", fg="green")
        click.secho(f"    tree-hash:    {tree_hash}", fg="white")
        click.secho(f"    commit:       {commit_sha}", fg="white")
        click.secho(f"    ref:          {ref}", fg="white")
        click.secho(f"    remote:       {remote}", fg="white")
        click.secho("", fg="white")
        click.secho("Auditor: read the diff with:", fg="cyan")
        click.secho(f"    git fetch {remote} {ref}", fg="white")
        click.secho(f"    git show {commit_sha}", fg="white")
        click.secho("", fg="white")
        click.secho("Then file the round (auditor runs this):", fg="cyan")
        click.secho(
            '    divineos audit submit-round "<focus>" \\',
            fg="white",
        )
        click.secho("        --actor <user|external-auditor> \\", fg="white")
        click.secho(f"        --source-ref {ref} \\", fg="white")
        click.secho(
            f'        --notes "tree-hash: {tree_hash}\\n<verification notes>"',
            fg="white",
        )
        click.secho("", fg="white")
        click.secho(
            "After CONFIRMs land, commit with the External-Review trailer:",
            fg="cyan",
        )
        click.secho(
            '    git commit -m "<msg>\\n\\nExternal-Review: <round_id>"',
            fg="white",
        )
        click.secho("", fg="white")
        click.secho(
            "The commit-msg hook will verify tree-hash at commit-time "
            "matches the round's cited tree-hash. No bypass needed.",
            fg="bright_black",
        )
