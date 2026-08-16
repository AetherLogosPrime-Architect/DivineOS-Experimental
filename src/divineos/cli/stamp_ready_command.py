"""`divineos stamp-ready` — attach the External-Review trailer and leave draft.

Phase 3 of the audit-stamp-attachment fix (claim ae9d70c4,
prereg-d695c9060158). The surrounding pieces were already built and each
covered a different edge:

- ``divineos push-ready`` amends trailers onto the branch commits.
- ``divineos audit prepare-merge`` validates a round and *prints* a body
  for a human to paste into the squash-merge box.
- ``gh-pr-merge-gate.sh`` refuses an untrailered ``gh pr merge``.

Nothing watched the draft->ready transition, and nothing ever *wrote* the
trailer anywhere durable. GitHub builds the squash-merge message from the
PR title and body, so a trailer that lives only on a branch commit does
not survive the squash. That is why a PR could sit green on its branch
and still fail the trailer check once pulled.

This command closes both: it writes the trailer into the PR body, then
clears the draft flag -- and refuses to clear it when the round has not
actually been confirmed.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import click


def register(cli: click.Group) -> None:
    @cli.command("stamp-ready")
    @click.argument("pr_number", type=int)
    @click.option(
        "--audit-round",
        "round_id",
        default=None,
        help="Round authorizing the merge. Resolved from the branch when omitted.",
    )
    @click.option(
        "--dry-run",
        is_flag=True,
        default=False,
        help="Validate and show the body that would be written; change nothing.",
    )
    def stamp_ready_cmd(pr_number: int, round_id: str | None, dry_run: bool) -> None:
        """Stamp a draft PR with its External-Review trailer and mark it ready.

        Order is load-bearing: body first, then ready. A failure between the
        two leaves a draft carrying a valid trailer, which is recoverable. The
        reverse leaves a ready PR with no trailer -- the exact state this
        exists to prevent.
        """
        from divineos.cli.audit_commands import _EXTERNAL_AI_ACTORS
        from divineos.core.watchmen.merge_stamp import (
            compose_merge_body,
            pr_head_tree_hash,
            validate_round,
        )
        from divineos.core.watchmen.store import list_rounds

        try:
            view = subprocess.run(
                [
                    "gh",
                    "pr",
                    "view",
                    str(pr_number),
                    "--json",
                    "headRefName,title,isDraft",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
            pr = json.loads(view.stdout)
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
            json.JSONDecodeError,
        ) as exc:
            click.secho(f"[!] Could not read PR #{pr_number} via gh: {exc}", fg="red")
            raise click.exceptions.Exit(1) from exc

        branch = pr.get("headRefName", "")
        pr_title = pr.get("title", "") or f"PR #{pr_number}"

        # Pull in any approvals waiting in the shared crossing-point BEFORE
        # validating. Andrew 2026-08-12: review was being given and then lost,
        # because it landed in ~/.divineos-shared/audit/ and every check reads
        # the local store. Syncing here means nobody has to remember to.
        from divineos.cli.audit_sync_command import render_sync_report
        from divineos.core.watchmen.shared_sync import sync_from_shared

        render_sync_report(sync_from_shared())

        # Resolve the round from the branch when not named. Station 8's
        # convention is that a round's focus names the branch it covers,
        # which is also what the build-flow station checker matches on.
        if not round_id:
            candidates = [
                rnd
                for rnd in list_rounds(limit=200)
                if branch and branch in (getattr(rnd, "focus", "") or "")
            ]
            if not candidates:
                click.secho(f"[!] No audit round names branch {branch}.", fg="red")
                click.secho(
                    "    File one, or pass --audit-round explicitly.",
                    fg="bright_black",
                )
                raise click.exceptions.Exit(1)
            if len(candidates) > 1:
                click.secho(
                    f"[!] {len(candidates)} rounds name branch {branch}. "
                    "Pass --audit-round to say which one authorizes this merge.",
                    fg="red",
                )
                for rnd in candidates:
                    click.echo(f"      {rnd.round_id}  {getattr(rnd, 'focus', '')}")
                raise click.exceptions.Exit(1)
            round_id = candidates[0].round_id
            click.secho(f"[=] Resolved round from branch: {round_id}", fg="cyan")

        verdict = validate_round(round_id, _EXTERNAL_AI_ACTORS)
        if not verdict.ok:
            click.secho(f"[!] Cannot stamp PR #{pr_number}: {verdict.reason}", fg="red")
            if verdict.remedy:
                click.secho(f"    {verdict.remedy}", fg="bright_black")
            click.secho(
                "    PR left in draft. An unconfirmed round cannot authorize a merge.",
                fg="bright_black",
            )
            raise click.exceptions.Exit(1)

        # The branch half, BEFORE the body half. The server-side gate wants
        # the trailer on every guardrail-touching COMMIT as well as in the
        # PR body, and stamping only the body left eleven PRs red on
        # 2026-08-13 while every success message said "ready for review".
        #
        # Order is not cosmetic: amending rewrites the commits and moves the
        # tree, so the tree-hash MUST be read after. Doing the body first
        # would bind the trailer to a tree that no longer exists -- valid to
        # look at, certifying nothing, which is the failure this module's
        # own header warns about.
        from divineos.core.push_ready import PushReadyError, run_push_ready

        try:
            pr_result = run_push_ready(
                Path.cwd(), branch=branch, dry_run=dry_run, round_id=round_id
            )
        except PushReadyError as exc:
            click.secho(f"[!] Could not stamp the branch commits: {exc}", fg="red")
            click.secho("    PR left as-is; nothing was changed.", fg="bright_black")
            raise click.exceptions.Exit(1) from exc

        if not pr_result.needing_trailer:
            click.secho("[=] Branch commits already carry the trailer.", fg="cyan")
        elif dry_run:
            click.secho(
                f"[=] {len(pr_result.needing_trailer)} commit(s) would be bound to {round_id}.",
                fg="cyan",
            )
        else:
            # Verify the STATE, never the report. On 2026-08-13 this path
            # announced "2 commit(s) bound" and PR #425 went ready while all
            # three of its commits still carried no trailer. The chain: the
            # branch was checked out in another worktree, so filter-branch
            # could not rewrite it; nothing changed; the force-push was a
            # no-op that returned success; and the guard here asked "did the
            # push succeed" instead of "do the commits carry the trailer
            # now". A push with nothing to push succeeds honestly.
            #
            # Re-detect against the real repo. If the trailer is still
            # missing, refuse the body -- a PR marked ready over unstamped
            # commits is the exact state this command exists to prevent.
            from divineos.core.push_ready import (
                _commits_needing_trailer,
                detect_commits,
                load_guardrail_set,
            )

            still = _commits_needing_trailer(
                detect_commits(Path.cwd(), branch, load_guardrail_set(Path.cwd()))
            )
            if still:
                click.secho(
                    f"[!] {len(still)} commit(s) STILL carry no trailer after the "
                    "amend, whatever the amend reported:",
                    fg="red",
                )
                for c in still:
                    click.echo(f"      {c.short_sha} {c.subject[:56]}")
                click.secho(
                    "    Not writing the body, not clearing draft. Common cause: "
                    "the branch is checked out in another worktree, so its "
                    "history cannot be rewritten from here.",
                    fg="bright_black",
                )
                raise click.exceptions.Exit(1)

            if not pr_result.pushed:
                click.secho(
                    "[!] Commits carry the trailer but the push failed: "
                    f"{pr_result.push_stderr.strip()[:160]}\n"
                    "    Not writing the body -- it would bind a tree the remote "
                    "does not have.",
                    fg="red",
                )
                raise click.exceptions.Exit(1)

            click.secho(
                f"[+] {len(pr_result.needing_trailer)} commit(s) now carry the "
                f"trailer for {round_id}, verified after the amend.",
                fg="green",
            )

        tree_hash = pr_head_tree_hash(pr_number)
        if not tree_hash:
            click.secho(
                "[!] Could not resolve the PR head tree hash. The trailer would carry\n"
                "    no substance binding and the server-side gate will flag it as\n"
                "    DEPRECATED. Fetch the branch, then re-run.",
                fg="yellow",
            )

        body = compose_merge_body(round_id, pr_title, verdict.age_days, tree_hash)

        if dry_run:
            click.secho("--- body that would be written (dry run) ---", fg="cyan")
            click.echo(body)
            click.secho(
                f"--- PR #{pr_number} untouched (isDraft={pr.get('isDraft')})",
                fg="cyan",
            )
            return

        try:
            subprocess.run(
                ["gh", "pr", "edit", str(pr_number), "--body", body],
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
            )
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
        ) as exc:
            click.secho(
                f"[!] Failed to write the trailer into PR #{pr_number}: {exc}",
                fg="red",
            )
            click.secho("    PR left in draft; nothing changed.", fg="bright_black")
            raise click.exceptions.Exit(1) from exc

        click.secho(f"[+] Trailer written into PR #{pr_number} body.", fg="green")

        if not pr.get("isDraft"):
            click.secho("[=] PR was already out of draft; trailer refreshed.", fg="cyan")
            return

        try:
            subprocess.run(
                ["gh", "pr", "ready", str(pr_number)],
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
            )
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
        ) as exc:
            click.secho(
                f"[!] Trailer is written but clearing the draft flag failed: {exc}\n"
                f"    Recoverable: run gh pr ready {pr_number} once gh is reachable.",
                fg="yellow",
            )
            raise click.exceptions.Exit(1) from exc

        click.secho(
            f"[+] PR #{pr_number} is ready for review, stamped by {round_id}.",
            fg="green",
            bold=True,
        )
