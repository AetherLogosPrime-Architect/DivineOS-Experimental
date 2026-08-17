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
import re
import subprocess
from pathlib import Path

import click

# "at tree dd08aa75", "tree-hash:ebad5700...", "tree: <hash>". Anchored on the
# word `tree` deliberately: a bare hex scan also matches the hex tail of a
# round id (round-6d67d2df400d), and a round id mistaken for a tree is a silent
# wrong answer of exactly the kind this guard exists to stop.
_TREE_NEAR = re.compile(r"tree[-\s]*(?:hash)?[:\s]+([0-9a-f]{8,40})", re.IGNORECASE)


def _confirmed_trees(round_id: str) -> set[str]:
    """Trees named by the CONFIRMS findings on this round.

    The tree an audit actually covers lives in its CONFIRMS findings, NOT in
    the round's ``notes``. Learned mid-fix on 2026-08-17: the first version of
    this guard read ``notes``, and the stale round in the live case carried
    ``Source ref: split/ci-merge-review-visibility`` -- a branch name. It named
    no tree, so the guard concluded "this round makes no claim" and waved
    through the exact pairing it had been written to refuse.

    A check that cannot see the data it is checking is worse than no check,
    because it reports safety. That first version passed its own test and
    would have failed the only case that mattered.

    Hashes appear abbreviated ("at tree dd08aa75") and full
    ("tree-hash:ebad5700..."), so callers compare by prefix in both directions.

    KNOWN LIMIT, stated because it runs in the permissive direction. This
    cannot tell a tree the finding CONFIRMS from a tree the finding merely
    MENTIONS. The live round here returns both ebad5700 (what it confirms) and
    dd08aa75 (named in prose as the confirmation it supersedes). So a round
    whose text discusses an old tree could be stamped onto that old tree
    without objection.

    Accepted rather than solved: the strict version needs structured
    per-finding tree fields, and inferring intent from prose would be a worse
    guess than the loose match. What this DOES catch is the case that actually
    occurred -- a round whose findings never mention the head tree at all --
    and it catches it by refusing, which is the direction that matters.
    """
    from divineos.core.watchmen.store import list_findings

    trees: set[str] = set()
    try:
        findings = list_findings(round_id=round_id, limit=200) or []
    except Exception:  # noqa: BLE001 - an unreadable store is not "no trees"
        return trees
    for f in findings:
        text = f"{getattr(f, 'title', '') or ''} {getattr(f, 'description', '') or ''}"
        if "confirms" not in text.lower():
            continue
        trees.update(m.group(1).lower() for m in _TREE_NEAR.finditer(text))
    return trees


def _tree_is_covered(head_tree: str, confirmed: set[str]) -> bool:
    """Does any confirmed tree refer to this head? Prefix match, both ways.

    The empty-head guard is not defensive noise. Prefix matching makes ""
    match EVERYTHING -- every string starts with the empty string -- so an
    unresolvable head tree would have read as covered by any round at all.
    Caught by the test that asserted it, which is the whole argument for
    writing the unglamorous case down.
    """
    h = (head_tree or "").lower()
    if not h:
        return False
    return any(h.startswith(t) or t.startswith(h) for t in confirmed if t)


def _round_by_id(round_id: str):
    """The round record, or None. Lookup by id, never by position."""
    from divineos.core.watchmen.store import list_rounds

    for rnd in list_rounds(limit=500):
        if getattr(rnd, "round_id", "") == round_id:
            return rnd
    return None


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
            # Match the full branch OR its last segment. The narrow version
            # matched only the full ref, and on 2026-08-17 that made a WRONG
            # resolution look like a confident one: PR #412's fresh round had
            # focus "...PR 412 ci-merge-review-visibility at tree ebad5700",
            # which does not contain "split/ci-merge-review-visibility". So the
            # correct round was not a candidate at all, the stale one was the
            # only match, and the multi-candidate guard below -- which exists
            # precisely to refuse this -- never fired because one is not more
            # than one.
            #
            # Widening makes ambiguity VISIBLE rather than resolving it by
            # accident. Two candidates now means the command stops and asks,
            # which is the outcome the guard was written for.
            tail = branch.rsplit("/", 1)[-1] if branch else ""
            candidates = [
                rnd
                for rnd in list_rounds(limit=200)
                if branch
                and (
                    branch in (getattr(rnd, "focus", "") or "")
                    or (tail and tail in (getattr(rnd, "focus", "") or ""))
                )
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

        # THE ROUND MUST ATTEST TO THE TREE IT IS ABOUT TO BE PAIRED WITH.
        #
        # `External-Review: <round> tree-hash:<T>` is a sentence, and it says
        # that round authorized tree T. Until 2026-08-17 nothing checked it:
        # the round came from branch-resolution and the tree came from the PR
        # head, and they were concatenated without ever being compared.
        #
        # Caught on PR #412, where the two halves came from different reviews.
        # Branch-resolution selected a round aged 5.3 days and paired it with a
        # tree written four hours earlier. Every line of the validation output
        # was true -- operator-CONFIRMS present, external-AI-CONFIRMS present,
        # within the 14-day recency window -- and the composed sentence was
        # false. A recency window measured in DAYS cannot see that the tree
        # moved, and tree-movement rather than elapsed time is what ends a
        # confirmation's authority. That is precisely the stale-round stamping
        # that substance-binding was introduced to stop, performed by the tool
        # built to perform substance-binding.
        #
        # Worse in that instance, and the reason this refuses rather than
        # warns: the id belonged to a DIFFERENT PARTY'S round. The external
        # reviewer minted an id in her own store; it collided with an unrelated
        # local round on the same branch. So the failure is not only "old
        # review" -- it can be "someone else's review entirely", and neither is
        # visible in the emitted trailer.
        if tree_hash:
            confirmed = _confirmed_trees(round_id)
            if confirmed and not _tree_is_covered(tree_hash, confirmed):
                named = ", ".join(sorted(t[:12] for t in confirmed))
                click.secho(
                    f"[!] Round {round_id} CONFIRMS tree(s) {named}, but this PR's head\n"
                    f"    tree is {tree_hash[:12]}. Pairing them would assert a review\n"
                    "    that did not happen.\n"
                    "    Get a round against the current tree, or pass --audit-round\n"
                    "    naming the round that actually covers it.",
                    fg="red",
                )
                click.secho(
                    "    PR left in draft. This is the stale-round stamping that\n"
                    "    substance-binding exists to prevent.",
                    fg="bright_black",
                )
                raise click.exceptions.Exit(1)
            if not confirmed:
                # The round's CONFIRMS name no tree at all. That is NOT
                # agreement -- it is a round that never said, and saying
                # nothing must not read as saying yes. Loud, but not fatal:
                # plenty of legitimate older rounds predate the convention of
                # naming the tree, and refusing them outright would break the
                # normal path to fix a rare one.
                click.secho(
                    f"[!] Round {round_id} names no tree in any CONFIRMS finding, so\n"
                    f"    nothing here proves it covers tree {tree_hash[:12]}. The trailer\n"
                    "    will still bind the tree; the ROUND's coverage of it is unverified.",
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
