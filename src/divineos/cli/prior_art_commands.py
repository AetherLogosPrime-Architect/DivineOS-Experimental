"""`divineos already-built "<thing>"` — station 0 of the build flow.

Named in plain words on purpose. Andrew is not a coder and the command he
asked for was *"looking through the system to make sure we dont already have
it"*, so the command is called what he called it, not `prior-art-scan`.
"""

from __future__ import annotations

import click

from divineos.core.prior_art import UNSEARCHED_SURFACES, search


def register(cli: click.Group) -> None:
    @cli.command("already-built")
    @click.argument("thing")
    def already_built_cmd(thing: str) -> None:
        """Check whether THING already exists before building it.

        Searches the axis the four prose surfaces do not cover: registered
        commands, files in the working tree, files that exist ONLY on another
        branch, and branch names.

        Example: divineos already-built "build flow"
        """
        r = search(thing)

        click.echo("")
        click.echo(f'=== ALREADY BUILT? — "{thing}" ===')
        click.echo("")

        if not r.git_readable:
            click.echo("  [NOT CHECKED] git is not readable here — the branch axis was skipped.")
            click.echo("  This is NOT a clean result. It is an unread one.")
            click.echo("")

        if r.commands:
            click.echo("  FOUND — registered commands:")
            for c in r.commands:
                click.echo(f"      divineos {c}")
            click.echo("")

        if r.working_tree:
            click.echo("  FOUND — files here:")
            for p in r.working_tree:
                click.echo(f"      {p}")
            click.echo("")

        if r.elsewhere_in_git:
            click.echo("  FOUND ELSEWHERE — exists in git, NOT in this working tree:")
            for path, commit, branch in r.elsewhere_in_git:
                click.echo(f"      {path}")
                click.echo(f"          on {branch}  ({commit})")
                # A branch name of "(remote only)" is prose, not a git ref --
                # interpolating it produced `git checkout (remote only) -- path`,
                # which is not a command. Caught by running this tool on
                # "letter monitor" minutes after writing it: a painted door in
                # the tool built to find painted doors. Fall back to the commit,
                # which is always a valid ref.
                ref = commit if branch == "(remote only)" else branch
                click.echo(f"          recover: git checkout {ref} -- {path}")
            click.echo("")
            click.echo("  Finished work that did not reach here reads as never-written")
            click.echo("  from where you are standing. It is not. Recover, do not rebuild.")
            click.echo("")

        if r.branches:
            click.echo("  FOUND — branches named for it:")
            for b in r.branches:
                click.echo(f"      {b}")
            click.echo("")

        if r.touching:
            # WHO ELSE HAS THIS FILE OPEN -- a different question from the list
            # above, which answers which branch NAMES resemble the term. Both
            # are useful and only one was being asked. On 2026-09-13 Aria and I
            # each wrote the same repair to one file the same evening, on
            # branches named for what we were writing about rather than for the
            # file, so neither name matched and neither of us was warned.
            click.echo("  WHO ELSE HAS THESE FILES OPEN (refs with commits touching them):")
            for path, (refs, capped) in r.touching.items():
                click.echo(f"      {path}")
                for ref in refs:
                    click.echo(f"          {ref}")
                if capped:
                    click.echo("          ... more, not listed (this list is capped)")
            click.echo("")
            click.echo("  A branch of mine here is a version I know about.")
            click.echo("  A branch of somebody else's is a collision, and it is silent:")
            click.echo("  two people fixing one defect produce two things that both work.")
            click.echo("")

        if not r.anything_found and r.git_readable:
            click.echo("  NOT FOUND on this axis — no command, file, or branch resembles it.")
            click.echo("")

        click.echo("  NOT CHECKED HERE — prose lives in other stores. Run these yourself:")
        for cmd, what in UNSEARCHED_SURFACES:
            click.echo(f'      {cmd} "{thing}"'.ljust(46) + f"  {what}")
        click.echo("")
        click.echo("  Silence from this command is not coverage. It searched code,")
        click.echo("  git and the command registry. It did not read a word of prose.")
        click.echo("")
