"""`divineos psf` — the command three gates have prescribed and none provided.

## The painted door

Three separate gates told the agent to run `divineos psf mark-done <psf-id>`
to clear a pending structural-fix obligation. The command has never existed.
`structural_fix_tracker.mark_done()` works fine and was reachable from no CLI
surface at all. Aria found it by exhaustion — not in `--help`, `todos` is
read-only, `obligations` exposes only check/disabled/is-write/list — and
recorded it as knowledge `a2006429` rather than routing around it. Her
learning checkpoint was unreachable as a direct result, and obligations kept
accumulating with no way to close any of them.

A door with a handle painted on it is worse than a wall. A wall does not cost
you the time to believe in it.

## Why closing requires evidence

Making "mark this done" easy is exactly the cheap escape the obligation
mechanism exists to prevent — file an obligation, wave at it, move on. So the
note must name something that actually exists: a commit, or a file. Both are
checked mechanically, which is the structural half of the repricing rule from
`docs/ai_research/2026-08-02_limits_of_automation.md`.

This does NOT verify that the fix is *good* — that is a semantic property, and
no gate can decide it. It verifies that the claim points at something real,
which raises the cost of a hollow close above the cost of an honest one.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import click

_SHA_RE = re.compile(r"\b([0-9a-f]{7,40})\b")
_PATH_RE = re.compile(r"\b([\w./-]+\.(?:py|sh|md|json|txt|yml|yaml))\b")


def find_evidence(note: str, repo_root: Path | None = None) -> list[str]:
    """Return the pieces of the note that resolve to something real.

    A commit that git can resolve, or a file that exists. Empty list means the
    note names nothing checkable.
    """
    root = repo_root or Path(".")
    found: list[str] = []

    for path in _PATH_RE.findall(note or ""):
        if (root / path).exists():
            found.append(f"file: {path}")

    for sha in _SHA_RE.findall(note or ""):
        try:
            r = subprocess.run(
                ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
                cwd=str(root),
                capture_output=True,
                timeout=10,
            )
            if r.returncode == 0:
                found.append(f"commit: {sha}")
        except (OSError, subprocess.SubprocessError):
            continue

    return found


def register(cli: click.Group) -> None:
    """Register `divineos psf`."""

    @cli.group("psf", invoke_without_command=True)
    @click.pass_context
    def psf_group(ctx: click.Context) -> None:
        """Pending structural fixes — the obligations gates file against you."""
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())

    @psf_group.command("list")
    @click.option("--all", "show_all", is_flag=True, help="Include already-closed entries.")
    def psf_list_cmd(show_all: bool) -> None:
        """Show pending structural-fix obligations."""
        from divineos.core.structural_fix_tracker import list_pending

        items = list_pending(include_done=show_all)
        if not items:
            click.secho("[~] No pending structural fixes.", fg="bright_black")
            return
        click.secho(f"{len(items)} pending structural fix(es):", fg="cyan")
        for e in items:
            click.echo(f"  {e.get('id', '?')}  [{e.get('status', 'open')}]")
            # The stored field is `content_excerpt`. This read `content`, which
            # no record has, so every one of 129 obligations printed as a blank
            # line under its id -- the ids were right, so the list looked like
            # it was working and reported an empty backlog 129 times.
            #
            # Found 2026-08-09 when the briefing named the oldest one (69 days)
            # WITH its text while this command showed nothing: two surfaces
            # over one store disagreeing, and the one I would triage from was
            # the blind one. `content` is kept as a fallback so a record
            # written under the other shape still renders.
            #
            # This is why the backlog never got worked. Not neglect -- you
            # cannot triage a list that will not tell you what is in it.
            content = (e.get("content_excerpt") or e.get("content") or "").replace("\n", " ")
            click.echo(f"      {content[:150] or '(no text recorded)'}")

    @psf_group.command("mark-done")
    @click.argument("psf_id")
    @click.option(
        "--note",
        required=True,
        help="What closed it. Must name a real commit or an existing file.",
    )
    def psf_mark_done_cmd(psf_id: str, note: str) -> None:
        """Close an obligation. The note must point at something that exists.

        This is the command three gates have been prescribing since before it
        existed. It refuses a note that names nothing checkable, because a
        close you can type without doing anything is not a close.
        """
        from divineos.core.structural_fix_tracker import mark_done

        evidence = find_evidence(note)
        if not evidence:
            click.secho(
                "[!] Refused: the note names nothing that resolves.\n"
                "    Closing an obligation requires pointing at a real commit "
                "or an existing file.\n"
                "    This checks only that the thing EXISTS — whether the fix is "
                "good is not\n"
                "    something any gate can decide, and is still yours to judge.",
                fg="red",
            )
            raise click.exceptions.Exit(1)

        if not mark_done(psf_id, note=note):
            click.secho(f"[!] No pending obligation with id {psf_id}.", fg="red")
            raise click.exceptions.Exit(1)

        click.secho(f"[+] {psf_id} closed.", fg="green")
        for e in evidence:
            click.secho(f"    evidence: {e}", fg="bright_black")
