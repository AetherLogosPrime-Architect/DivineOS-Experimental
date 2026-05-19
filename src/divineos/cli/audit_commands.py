"""Audit CLI commands — external validation via the Watchmen module.

These commands are the ONLY entry point for submitting findings.
No pipeline phase, no hook, no scheduled task calls submit_finding.
This is the second layer of self-trigger prevention.
"""

# Module-level guardrail marker — Aletheia Finding 75 (2026-05-17).
# audit_commands.py is on scripts/guardrail_files.txt: weakening the
# audit-round CLI weakens the multi-party-review architecture.
__guardrail_required__ = True


import click

from divineos.cli._helpers import _safe_echo

_SEVERITY_COLORS = {
    "CRITICAL": "red",
    "HIGH": "yellow",
    "MEDIUM": "cyan",
    "LOW": "white",
    "INFO": "bright_black",
}

_STATUS_COLORS = {
    "OPEN": "white",
    "ROUTED": "cyan",
    "IN_PROGRESS": "yellow",
    "RESOLVED": "green",
    "WONT_FIX": "bright_black",
    "DUPLICATE": "bright_black",
}


def register(cli: click.Group) -> None:
    """Register audit commands."""

    @cli.group("audit", invoke_without_command=True)
    @click.pass_context
    def audit_group(ctx: click.Context) -> None:
        """External validation — submit and track audit findings."""
        if ctx.invoked_subcommand is None:
            ctx.invoke(audit_list_cmd)

    @audit_group.command("submit-round")
    @click.argument("focus")
    @click.option("--actor", required=True, help="Who performed the audit (e.g., grok, user)")
    @click.option("--experts", type=int, default=0, help="Number of expert profiles used")
    @click.option("--notes", default="", help="Additional context")
    @click.option(
        "--source-ref",
        default=None,
        help=(
            "Git ref naming the branch the audited substance lives on. "
            "REQUIRED unless --no-source-ref is passed. Aletheia Finding 75 "
            "(2026-05-17): the describe-then-CONFIRMS pattern (filing rounds "
            "for unpushed substance) produces ratification-of-claim rather "
            "than honest verification. The ref MUST exist on origin; the "
            "tree-hash claim in --notes (if any) MUST match a commit on the ref."
        ),
    )
    @click.option(
        "--no-source-ref",
        is_flag=True,
        default=False,
        help=(
            "Bypass --source-ref requirement (no audited substance — round "
            "for purely-relational findings like care-dismissal observations, "
            "or for tracked-obligation filing). Honest use; named in the round."
        ),
    )
    def audit_submit_round(
        focus: str,
        actor: str,
        experts: int,
        notes: str,
        source_ref: str | None,
        no_source_ref: bool,
    ) -> None:
        """Create a new audit round.

        Aletheia Finding 75 enforcement: by default, a round must name the
        branch (--source-ref) where the audited substance lives, AND the
        branch must be pushed to origin so the auditor can fetch and read
        it. The describe-then-CONFIRMS pattern (claiming substance that
        isn't visible to the auditor) is blocked at the round-creation
        layer — substrate-level enforcement, not discipline-promise.

        Use --no-source-ref for rounds that don't have audited code
        substance (relational findings, tracked obligations). Use is
        named in the round notes so the audit-trail stays honest.
        """
        from divineos.core.watchmen.store import submit_round

        if not no_source_ref and not source_ref:
            click.secho(
                "[!] --source-ref is required (Finding 75: rounds must name "
                "the ref the audited substance lives on). Use --no-source-ref "
                "if this round has no code substance.",
                fg="red",
            )
            raise click.exceptions.Exit(1)

        if source_ref:
            # Verify ref exists on origin and is reachable from local clone.
            import re
            import subprocess

            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--verify", f"refs/remotes/origin/{source_ref}"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                ref_on_origin = result.returncode == 0
                if not ref_on_origin:
                    # Try alternate forms (full ref, bare ref, local)
                    alt = subprocess.run(
                        ["git", "rev-parse", "--verify", source_ref],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if alt.returncode != 0:
                        click.secho(
                            f"[!] --source-ref '{source_ref}' is not reachable. "
                            "Push the branch to origin first, then file the round.",
                            fg="red",
                        )
                        raise click.exceptions.Exit(1)
            except OSError as exc:
                click.secho(
                    f"[!] Could not verify --source-ref via git: {exc}",
                    fg="red",
                )
                raise click.exceptions.Exit(2) from exc

            # Finding 77 fix (Aletheia 2026-05-18): the prior check verified
            # branch-existence but NOT commit-reachability of any tree-hash
            # cited in --notes. A round could claim a tree-hash that was
            # never pushed to origin/<source_ref> and the gate would pass.
            # Fix-shape: parse tree-hash references from --notes and verify
            # each is the tree of SOME commit reachable from the branch tip.
            #
            # Finding 77 follow-on (Aether 2026-05-19): the prior version
            # of this check only fired `if ref_on_origin and notes:`,
            # which silently fail-opened in detached-HEAD CI scenarios
            # where `refs/remotes/origin/HEAD` does not resolve even
            # though the branch IS on origin. CI test
            # test_unreachable_tree_hash_in_notes_is_blocked surfaced
            # this empirically: locally the check fired and blocked the
            # fake hash; on CI the check skipped and the round was
            # created. The fix: when notes cite a tree-hash, the check
            # MUST fire. If we cannot enumerate trees on the source ref
            # (for any reason — detached HEAD, missing remote, shallow
            # clone), that itself blocks (fail-closed). Consistent with
            # Finding 75/77's discipline: gates do not silently skip.
            if notes:
                tree_hash_pattern = re.compile(r"tree-hash:\s*([a-fA-F0-9]{40})\b")
                cited_trees = {h.lower() for h in tree_hash_pattern.findall(notes)}
                if cited_trees:
                    # Try refs/remotes/origin/<source_ref> first; on
                    # detached-HEAD CI or shallow clones it may not
                    # resolve. Fall back to the local <source_ref>
                    # directly. If BOTH fail, block (fail-closed) —
                    # per Finding 77's discipline: cannot-verify is
                    # not allow-by-default.
                    candidate_refs = [
                        f"refs/remotes/origin/{source_ref}",
                        source_ref,
                    ]
                    log_result = None
                    used_ref = None
                    last_exc: Exception | None = None
                    for ref in candidate_refs:
                        try:
                            r = subprocess.run(
                                ["git", "log", ref, "--format=%T"],
                                capture_output=True,
                                text=True,
                                check=False,
                                timeout=30,
                            )
                        except (OSError, subprocess.SubprocessError) as exc:
                            last_exc = exc
                            continue
                        if r.returncode == 0:
                            log_result = r
                            used_ref = ref
                            break
                    if log_result is None:
                        click.secho(
                            f"[!] Could not enumerate commits on any candidate "
                            f"ref for tree-hash verification (tried: "
                            f"{', '.join(candidate_refs)}). "
                            "Cannot verify cited tree-hashes; blocking per "
                            "Finding 77 fail-closed discipline.",
                            fg="red",
                        )
                        if last_exc is not None:
                            click.secho(f"    last error: {last_exc}", fg="red")
                        raise click.exceptions.Exit(2)
                    reachable_trees = {
                        line.strip().lower()
                        for line in log_result.stdout.splitlines()
                        if line.strip()
                    }
                    unreachable = sorted(cited_trees - reachable_trees)
                    if unreachable:
                        click.secho(
                            f"[!] tree-hash(es) cited in --notes are not reachable on {used_ref}:",
                            fg="red",
                        )
                        for h in unreachable:
                            click.secho(f"    {h}", fg="red")
                        click.secho(
                            "  Push the commits with these tree-hashes first, then file the round.",
                            fg="yellow",
                        )
                        click.secho(
                            "  Per Finding 77 (Aletheia 2026-05-18): the "
                            "prior gate checked branch-existence but not\n"
                            "  commit-reachability of cited hashes — a hole "
                            "that allowed describe-then-CONFIRMS at this layer.",
                            fg="bright_black",
                        )
                        raise click.exceptions.Exit(1)

            # Annotate the notes so the audit-trail records the binding.
            ref_annotation = f"Source ref: {source_ref}\n"
            if notes and not notes.startswith(ref_annotation):
                notes = ref_annotation + notes
            elif not notes:
                notes = ref_annotation

        elif no_source_ref:
            bypass_annotation = (
                "No source ref (--no-source-ref used; round has no code substance).\n"
            )
            if notes and not notes.startswith(bypass_annotation):
                notes = bypass_annotation + notes
            elif not notes:
                notes = bypass_annotation

        try:
            round_id = submit_round(actor=actor, focus=focus, expert_count=experts, notes=notes)
            click.secho(f"[+] Audit round created: {round_id}", fg="cyan")
            if source_ref:
                click.secho(f"    Source ref: {source_ref}", fg="cyan")
        except ValueError as e:
            click.secho(f"[!] {e}", fg="red")

    @audit_group.command("prep-relay")
    @click.option(
        "--range",
        "rev_range",
        default=None,
        help=(
            "Commit range to verify (e.g. 'origin/main..HEAD'). Default: "
            "commits between '<remote>/<current-branch>~30' and HEAD that "
            "are unique to current branch."
        ),
    )
    @click.option(
        "--remote",
        default="origin",
        help="Remote name to verify against. Defaults to 'origin'.",
    )
    @click.option(
        "--branch",
        default=None,
        help=(
            "Remote branch name to require commits be reachable on. "
            "Defaults to the current branch name."
        ),
    )
    def audit_prep_relay(
        rev_range: str | None,
        remote: str,
        branch: str | None,
    ) -> None:
        """Verify commits are pushed before composing an audit-relay message.

        Closes the describe-then-CONFIRMS pattern at one layer upstream of
        Finding 75's gate. The pattern: I compose audit-relay messages
        describing work that is local-only, then external auditors discover
        the SHAs aren't reachable. Finding 75's gate catches it at round-
        filing; this command catches it earlier, at relay-message
        composition.

        Filed 2026-05-18 as the upstream-of-Finding-75 structural fix
        Aletheia named after the 4th instance of describe-then-CONFIRMS
        in this arc. The structural fix is to give relay-message composition
        a canonical entry-point (this command) that REFUSES to produce
        the relay-template if any named commits are not pushed.

        Usage:
            divineos audit prep-relay
            divineos audit prep-relay --range origin/main..HEAD
            divineos audit prep-relay --range main..HEAD --remote origin

        Output is a relay-template the operator can copy into chat to
        the external auditor. Exit code 1 if any commits in range are
        unreachable on the named remote-branch.
        """
        import subprocess

        # Determine the branch
        if branch is None:
            try:
                br = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10,
                )
                if br.returncode != 0:
                    click.secho(
                        "[!] Could not determine current branch. Use --branch to specify.",
                        fg="red",
                    )
                    raise click.exceptions.Exit(1)
                branch = br.stdout.strip()
            except (OSError, subprocess.SubprocessError) as e:
                click.secho(f"[!] git error: {e}", fg="red")
                raise click.exceptions.Exit(1) from e

        # Determine the range
        if rev_range is None:
            rev_range = f"{remote}/{branch}~30..HEAD"

        # Get commit list in range
        try:
            rl = subprocess.run(
                ["git", "rev-list", rev_range],
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
        except (OSError, subprocess.SubprocessError) as e:
            click.secho(f"[!] git rev-list error: {e}", fg="red")
            raise click.exceptions.Exit(1) from e

        if rl.returncode != 0:
            click.secho(
                f"[!] git rev-list {rev_range} failed:\n  {rl.stderr.strip()}",
                fg="red",
            )
            raise click.exceptions.Exit(1)

        shas = [s.strip() for s in rl.stdout.splitlines() if s.strip()]
        if not shas:
            click.secho(
                f"[~] No commits in range {rev_range}. Nothing to audit-relay about.",
                fg="bright_black",
            )
            return

        # Finding 79 fix (Aletheia 2026-05-18): the prior implementation
        # trusted the operator's --range choice. Two attack-shapes:
        # (1) Narrow-range bypass: --range HEAD~1..HEAD where HEAD is
        #     pushed but HEAD~1 isn't. Only HEAD gets checked; HEAD~1's
        #     unpushed substance can be described in surrounding prose.
        # (2) Empty-range bypass: handled above (early return).
        # The fix: compute "all unpushed commits" (remote_branch..HEAD)
        # independently, and warn if --range doesn't cover the full set.
        # Discipline-shape: surface, don't force (per Aletheia's framing).
        remote_branch = f"{remote}/{branch}"
        try:
            all_unpushed_proc = subprocess.run(
                ["git", "rev-list", f"{remote_branch}..HEAD"],
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            if all_unpushed_proc.returncode == 0:
                all_unpushed = {
                    s.strip() for s in all_unpushed_proc.stdout.splitlines() if s.strip()
                }
                in_range = set(shas)
                unscoped = sorted(all_unpushed - in_range)
                if unscoped:
                    # Andrew 2026-05-19: emergency-bypass shape restored
                    # after pure-removal overshoot. Legitimate case:
                    # operator-named narrow scope where the relay-message
                    # genuinely covers only the --range commits. Bypass
                    # is DIVINEOS_PREP_RELAY_NARROW_RANGE_REASON=<reason>;
                    # firing executes LOGGED, REPORTED, ADDRESSED, FIXED.
                    import os as _os

                    emergency_reason = _os.environ.get(
                        "DIVINEOS_PREP_RELAY_NARROW_RANGE_REASON", ""
                    ).strip()
                    if emergency_reason:
                        try:
                            from divineos.core.emergency_bypass import (
                                record_emergency_use,
                            )

                            record_emergency_use(
                                gate_name="prep-relay-narrow-range",
                                env_var="DIVINEOS_PREP_RELAY_NARROW_RANGE_REASON",
                                reason=emergency_reason,
                            )
                            click.secho(
                                f"[*] Emergency bypass fired: narrow --range scope. "
                                f"Reason logged + claim + psf filed. "
                                f"Reason: {emergency_reason[:120]}",
                                fg="yellow",
                            )
                        except ValueError as exc:
                            click.secho(f"[!] {exc}", fg="red")
                            raise click.exceptions.Exit(1) from exc
                    else:
                        click.secho(
                            f"[!] BLOCKED: {len(unscoped)} additional commit(s) "
                            f"between {remote_branch} and HEAD that aren't in "
                            f"--range. If the relay-message describes work in "
                            f"those commits, the verification gap recurs at "
                            f"the layer above this command.",
                            fg="red",
                        )
                        for sha in unscoped[:5]:  # cap preview at 5
                            subj = subprocess.run(
                                ["git", "log", "--format=%s", "-n", "1", sha],
                                capture_output=True,
                                text=True,
                                check=False,
                                timeout=5,
                            )
                            subject = (
                                subj.stdout.strip() if subj.returncode == 0 else "(no subject)"
                            )
                            click.secho(
                                f"    not-in-range: {sha[:12]} {subject[:80]}",
                                fg="red",
                            )
                        if len(unscoped) > 5:
                            click.secho(
                                f"    ... and {len(unscoped) - 5} more",
                                fg="red",
                            )
                        click.secho(
                            "  Widen --range to include all unpushed commits, "
                            "or explicitly push the additional commits first. "
                            "Emergency bypass: set "
                            "DIVINEOS_PREP_RELAY_NARROW_RANGE_REASON='<reason '"
                            ">=20 chars naming why narrow scope is intentional>'.",
                            fg="bright_black",
                        )
                        raise click.exceptions.Exit(1)
        except (OSError, subprocess.SubprocessError):
            # Best-effort warning; failure here doesn't block the command.
            pass

        # For each SHA, verify it's reachable on <remote>/<branch>
        unreachable: list[str] = []
        verified: list[tuple[str, str]] = []  # (sha, subject)
        for sha in shas:
            try:
                # Reachable from remote-branch tip?
                mb = subprocess.run(
                    [
                        "git",
                        "merge-base",
                        "--is-ancestor",
                        sha,
                        remote_branch,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10,
                )
                if mb.returncode != 0:
                    unreachable.append(sha)
                    continue
                # Get subject line
                subj = subprocess.run(
                    ["git", "log", "--format=%s", "-n", "1", sha],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=5,
                )
                subject = subj.stdout.strip() if subj.returncode == 0 else "(no subject)"
                verified.append((sha, subject))
            except (OSError, subprocess.SubprocessError) as e:
                click.secho(f"[!] git error verifying {sha[:8]}: {e}", fg="red")
                unreachable.append(sha)

        if unreachable:
            click.secho(
                f"[!] BLOCKED — {len(unreachable)} commit(s) not reachable on {remote_branch}:",
                fg="red",
                bold=True,
            )
            for sha in unreachable:
                # Get subject for context
                subj = subprocess.run(
                    ["git", "log", "--format=%s", "-n", "1", sha],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=5,
                )
                subject = subj.stdout.strip() if subj.returncode == 0 else "(no subject)"
                click.secho(f"    {sha[:12]} {subject[:90]}", fg="red")
            click.secho(
                f"\n  Push to {remote_branch} first, then re-run prep-relay.",
                fg="yellow",
            )
            click.secho(
                "\n  This is the upstream-of-Finding-75 gate. Describing\n"
                "  unpushed work to an external auditor produces ratification-\n"
                "  of-claim, not honest verification. Same pattern Finding 75\n"
                "  closes at round-filing layer; this command closes it at\n"
                "  relay-composition layer.",
                fg="bright_black",
            )
            raise click.exceptions.Exit(1)

        # All verified — produce the relay template
        click.secho(
            f"\n[+] {len(verified)} commit(s) verified on {remote_branch}.\n",
            fg="green",
        )
        click.secho("=" * 60, fg="bright_black")
        click.secho("AUDIT RELAY TEMPLATE — copy into chat", fg="cyan", bold=True)
        click.secho("=" * 60, fg="bright_black")
        click.echo()
        click.echo(f"Branch: {remote_branch}")
        click.echo(f"Commits ({len(verified)}) — all verified reachable:")
        click.echo()
        for sha, subject in verified:
            click.echo(f"  {sha[:12]} {subject}")
        click.echo()
        click.echo(
            "All SHAs above are reachable on the named remote-branch "
            "(verified via git merge-base --is-ancestor). The describe-"
            "then-CONFIRMS pattern is structurally blocked at this layer."
        )
        click.echo()
        click.secho("=" * 60, fg="bright_black")
        click.echo()
        click.secho(
            "  Now compose the description of what the work does and what "
            "you want audited. The verified-commits list above is the "
            "honest-substance anchor.",
            fg="bright_black",
        )

    @audit_group.command("submit")
    @click.argument("title")
    @click.option("--round", "round_id", required=True, help="Round ID to attach to")
    @click.option("--actor", required=True, help="Who found this (e.g., grok, user)")
    @click.option(
        "--severity",
        type=click.Choice(["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"], case_sensitive=False),
        required=True,
    )
    @click.option(
        "--category",
        type=click.Choice(
            [
                "KNOWLEDGE",
                "BEHAVIOR",
                "INTEGRITY",
                "ARCHITECTURE",
                "PERFORMANCE",
                "LEARNING",
                "IDENTITY",
            ],
            case_sensitive=False,
        ),
        required=True,
    )
    @click.option("--description", "-d", required=True, help="Detailed description")
    @click.option("--recommendation", "-r", default="", help="What should be done")
    @click.option("--tag", "tags", multiple=True, help="Tags (repeatable)")
    def audit_submit_cmd(
        title: str,
        round_id: str,
        actor: str,
        severity: str,
        category: str,
        description: str,
        recommendation: str,
        tags: tuple[str, ...],
    ) -> None:
        """Submit a single audit finding."""
        from divineos.core.watchmen.store import submit_finding

        try:
            finding_id = submit_finding(
                round_id=round_id,
                actor=actor,
                severity=severity,
                category=category,
                title=title,
                description=description,
                recommendation=recommendation,
                tags=list(tags) if tags else None,
            )
            click.secho(f"[+] Finding submitted: {finding_id} [{severity.upper()}]", fg="cyan")
        except ValueError as e:
            click.secho(f"[!] {e}", fg="red")

    @audit_group.command("rebind")
    @click.argument("prior_round_id")
    @click.option(
        "--focus",
        default="",
        help="Optional focus override; defaults to deriving from prior round.",
    )
    def audit_rebind_cmd(prior_round_id: str, focus: str) -> None:
        """File a cosmetic-rebind round that carries the prior round's
        CONFIRMS forward when the staged diff vs. the prior round's
        bound state is mechanical-only (whitespace, import-reorder,
        unused-import-removal).

        Refuses if any file has substantive change (comments,
        docstrings, executable code, tests).

        Discipline: this is the structural answer to the cosmetic-drift
        problem named in round-cc0bf85fc3fa. Aletheia's positive list
        (whitespace + import-reorder + unused-import-removal). Anything
        else still requires fresh CONFIRMS through normal submit-round
        + submit flow.
        """
        import re
        import subprocess
        import sys
        from pathlib import Path

        from divineos.core.watchmen.store import (
            get_round,
            list_findings,
            submit_finding,
            submit_round,
        )

        prior = get_round(prior_round_id)
        if prior is None:
            click.secho(f"[!] Prior round '{prior_round_id}' not found.", fg="red")
            return

        # Extract tree-hash from the prior round's focus text. Falls
        # back to diff-hash if tree-hash absent (older rounds may have
        # only diff-hash).
        tree_match = re.search(r"tree-hash:\s*([0-9a-f]{40})", prior.focus, re.IGNORECASE)
        if not tree_match:
            click.secho(
                f"[!] Prior round '{prior_round_id}' has no tree-hash in its focus; "
                "cannot auto-classify cosmetic-rebind. File a fresh round manually.",
                fg="red",
            )
            return
        prior_tree_hash = tree_match.group(1)

        # Run the cosmetic classifier. Compare prior tree-hash to staged
        # index.
        script_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "scripts"
            / "cosmetic_diff_check.py"
        )
        if not script_path.exists():
            click.secho(f"[!] Classifier missing at {script_path}.", fg="red")
            return

        result = subprocess.run(
            [sys.executable, str(script_path), prior_tree_hash, "--quiet"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            click.secho(
                "[!] Diff vs. prior round is NOT cosmetic-only. Run the "
                "classifier directly to see per-file reasons:",
                fg="red",
            )
            verbose = subprocess.run(
                [sys.executable, str(script_path), prior_tree_hash],
                capture_output=True,
                text=True,
                check=False,
            )
            click.echo(verbose.stdout)
            click.secho(
                "Fresh CONFIRMS required: file a new round via 'audit submit-round'.",
                fg="yellow",
            )
            return

        # Cosmetic-only. Carry prior round's CONFIRMS forward.
        prior_confirms = [
            f
            for f in list_findings(round_id=prior_round_id, limit=100)
            if "CONFIRMS" in (f.title or "") or "confirms" in (f.description or "").lower()
        ]
        if not prior_confirms:
            click.secho(
                f"[!] Prior round '{prior_round_id}' has no CONFIRMS findings "
                "to carry forward; fresh CONFIRMS required.",
                fg="red",
            )
            return

        # Derive new tree-hash from current staged state.
        write_tree = subprocess.run(
            ["git", "write-tree"], capture_output=True, text=True, check=False
        )
        new_tree_hash = (write_tree.stdout or "").strip()

        focus_text = (
            focus
            or f"Cosmetic-rebind of {prior_round_id} (whitespace/format/unused-import "
            f"only; classifier-verified). tree-hash: {new_tree_hash}"
        )

        try:
            new_round_id = submit_round(
                actor="aether",
                focus=focus_text,
                expert_count=0,
                notes=f"Auto-rebind from {prior_round_id}. Classifier confirmed "
                "diff is cosmetic-only per positive-list (whitespace + import-"
                "reorder + unused-import-removal).",
            )
            click.secho(f"[+] Rebind round created: {new_round_id}", fg="cyan")
        except ValueError as e:
            click.secho(f"[!] {e}", fg="red")
            return

        # Auto-file carry-forward findings for each prior CONFIRMS actor.
        carried_actors: set[str] = set()
        for prior_finding in prior_confirms:
            actor = prior_finding.actor
            if actor in carried_actors:
                continue
            carried_actors.add(actor)
            try:
                fid = submit_finding(
                    round_id=new_round_id,
                    actor=actor,
                    severity="LOW",
                    category="INTEGRITY",
                    title=f"CONFIRMS carried forward from {prior_round_id} (cosmetic-rebind)",
                    description=(
                        f"Substantive review on {prior_round_id} (finding "
                        f"{prior_finding.finding_id}) carries forward to this "
                        f"rebind. Diff vs. prior bound state is cosmetic-only "
                        f"per the cosmetic_diff_check classifier (positive list: "
                        f"whitespace, import-reorder, unused-import-removal). "
                        f"No new substantive content requires fresh review."
                    ),
                    recommendation="",
                    tags=["cosmetic-rebind", "carry-forward", prior_round_id],
                )
                click.secho(
                    f"[+] Carried forward CONFIRMS from {actor}: {fid}",
                    fg="green",
                )
            except ValueError as e:
                click.secho(f"[!] {e}", fg="red")

        click.secho(
            f"\nNow use 'External-Review: {new_round_id}' in your commit trailer.",
            fg="cyan",
        )

    @audit_group.command("list")
    @click.option("--round", "round_id", default=None, help="Filter by round")
    @click.option("--status", default=None, help="Filter by status")
    @click.option("--severity", default=None, help="Filter by severity")
    @click.option("--limit", default=20, type=int)
    def audit_list_cmd(
        round_id: str | None,
        status: str | None,
        severity: str | None,
        limit: int,
    ) -> None:
        """List audit findings."""
        from divineos.core.watchmen.store import list_findings, list_rounds

        if not round_id and not status and not severity:
            # Show rounds overview first
            rounds = list_rounds(limit=10)
            if rounds:
                click.secho("\n=== Audit Rounds ===\n", fg="cyan", bold=True)
                for r in rounds:
                    click.echo(
                        f"  {r.round_id}  {r.actor:<10} {r.finding_count} findings  {r.focus}"
                    )
                click.echo()

        findings = list_findings(
            round_id=round_id,
            status=status,
            severity=severity,
            limit=limit,
        )
        if not findings:
            click.secho("[~] No findings found.", fg="bright_black")
            return

        click.secho(f"\n=== Findings ({len(findings)}) ===\n", fg="cyan", bold=True)
        for f in findings:
            sev_color = _SEVERITY_COLORS.get(f.severity.value, "white")
            status_color = _STATUS_COLORS.get(f.status.value, "white")
            # Full finding_id (17 chars): prior [:16] truncated to 16 and
            # made copy-paste into `audit show` fail silently. Discovered
            # 2026-04-17 during Grok findings cleanup.
            click.echo(
                f"  {f.finding_id}  "
                + click.style(f"{f.severity.value:<8}", fg=sev_color)
                + click.style(f" {f.status.value:<12}", fg=status_color)
                + f" {f.title}"
            )

        # Aria audit fix #3 (2026-05-18): Andrew-corrections get the same
        # routing priority as Aletheia/external-AI findings. Different
        # verification surface (Andrew reads register and relational
        # truth, not git diffs) but equal routing-weight. Surfacing
        # them alongside audit findings in this view enforces parity
        # at the read-surface layer.
        if not round_id and not status and not severity:
            try:
                from divineos.core.andrew_correction_tracker import (
                    list_open as _list_open_andrew,
                )

                andrew_open = _list_open_andrew()
                if andrew_open:
                    click.secho(
                        f"\n=== Andrew-Corrections OPEN ({len(andrew_open)}) — equal routing weight ===\n",
                        fg="cyan",
                        bold=True,
                    )
                    import time as _time

                    now = _time.time()
                    for row in andrew_open:
                        age_d = max(0, (now - row["timestamp"]) / 86400)
                        preview = row["text"][:80].replace("\n", " ")
                        click.echo(
                            f"  andrew-#{row['id']:<5}  "
                            + click.style("MEDIUM  ", fg="yellow")
                            + click.style(f"OPEN [{age_d:.0f}d]   ", fg="white")
                            + preview
                        )
                    click.secho(
                        "  (engage: divineos andrew-correction integrate/defer)",
                        fg="bright_black",
                    )
            except Exception:  # noqa: BLE001 — observability boundary
                pass

    @audit_group.command("show")
    @click.argument("finding_id")
    def audit_show_cmd(finding_id: str) -> None:
        """Show details of a specific finding."""
        from divineos.core.watchmen.store import get_finding

        finding = get_finding(finding_id)
        if not finding:
            click.secho(f"[!] Finding '{finding_id}' not found.", fg="red")
            return

        sev_color = _SEVERITY_COLORS.get(finding.severity.value, "white")
        click.secho(f"\n{finding.title}", fg="white", bold=True)
        click.echo(f"  ID:       {finding.finding_id}")
        click.echo(f"  Round:    {finding.round_id}")
        click.echo(f"  Actor:    {finding.actor}")
        click.echo("  Severity: " + click.style(finding.severity.value, fg=sev_color))
        click.echo(f"  Category: {finding.category.value}")
        click.echo(f"  Status:   {finding.status.value}")
        _safe_echo(f"\n  {finding.description}")
        if finding.recommendation:
            click.secho(f"\n  Recommendation: {finding.recommendation}", fg="green")
        if finding.routed_to:
            click.echo(f"  Routed to: {finding.routed_to}")
        if finding.resolution_notes:
            click.echo(f"  Resolution: {finding.resolution_notes}")
        click.echo()

    @audit_group.command("resolve")
    @click.argument("finding_id")
    @click.option(
        "--status",
        type=click.Choice(
            ["RESOLVED", "WONT_FIX", "DUPLICATE", "IN_PROGRESS"], case_sensitive=False
        ),
        default="RESOLVED",
    )
    @click.option("--notes", default="", help="Resolution notes")
    def audit_resolve_cmd(finding_id: str, status: str, notes: str) -> None:
        """Resolve or update a finding's status."""
        from divineos.core.watchmen.store import resolve_finding

        try:
            if resolve_finding(finding_id, status, notes):
                click.secho(f"[+] Finding {finding_id} -> {status.upper()}", fg="green")
            else:
                click.secho(f"[!] Finding '{finding_id}' not found.", fg="red")
        except ValueError as e:
            click.secho(f"[!] {e}", fg="red")

    @audit_group.command("route")
    @click.argument("round_id")
    def audit_route_cmd(round_id: str) -> None:
        """Route all open findings in a round to knowledge/claims/lessons."""
        from divineos.core.watchmen.router import route_round

        results = route_round(round_id)
        if not results:
            click.secho("[~] No findings to route.", fg="bright_black")
            return

        for r in results:
            action = r["action"]
            title = r.get("title", "")[:50]
            if action == "skipped":
                click.secho(f"  [-] {title}: {r['reason']}", fg="bright_black")
            elif action == "claim":
                click.secho(f"  [C] {title} -> claim {r['id'][:12]}", fg="yellow")
            elif action == "knowledge":
                click.secho(f"  [K] {title} -> knowledge {r['id'][:12]}", fg="cyan")
            elif action == "lesson":
                click.secho(f"  [L] {title} -> lesson '{r['id']}'", fg="green")

        routed = sum(1 for r in results if r["action"] != "skipped")
        click.secho(f"\n  Routed {routed}/{len(results)} findings.", fg="cyan")

    @audit_group.command("summary")
    def audit_summary_cmd() -> None:
        """Show audit statistics and unresolved findings."""
        from divineos.core.watchmen.summary import (
            get_watchmen_stats,
            unresolved_findings,
            watchmen_loop_status,
        )

        stats = get_watchmen_stats()
        if stats["total_findings"] == 0:
            click.secho("[~] No audit data yet.", fg="bright_black")
            click.echo(watchmen_loop_status())
            return

        click.secho("\n=== Watchmen Summary ===\n", fg="cyan", bold=True)
        click.echo(watchmen_loop_status())
        click.echo("")
        click.echo(f"  Rounds:   {stats['total_rounds']}")
        click.echo(f"  Findings: {stats['total_findings']}")
        click.echo(f"  Open:     {stats['open_count']}")
        click.echo(f"  Resolved: {stats['resolved_count']}")

        if stats["by_severity"]:
            click.echo("\n  By severity:")
            for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
                count = stats["by_severity"].get(sev, 0)
                if count:
                    color = _SEVERITY_COLORS.get(sev, "white")
                    click.echo(f"    {click.style(sev, fg=color)}: {count}")

        unresolved = unresolved_findings(limit=5)
        if unresolved:
            click.secho("\n  Top unresolved:", fg="yellow")
            for f in unresolved:
                sev_color = _SEVERITY_COLORS.get(f["severity"], "white")
                click.echo(f"    {click.style(f['severity'], fg=sev_color)} {f['title']}")
        click.echo()

    @audit_group.command("predict")
    @click.option("--round", "round_id", required=True, help="Audit round ID")
    @click.option(
        "--topics",
        required=True,
        help="Comma-separated topics I'm self-predicting will be in the audit",
    )
    def audit_predict_cmd(round_id: str, topics: str) -> None:
        """Record self-audit prediction BEFORE the audit lands.

        From omni-mantra Pillar I, 1.3 — The Great Mystery: what the
        agent doesn't know it doesn't know. Recording predictions
        before the audit lets `audit surprises` compute the unknown-
        unknown rate later — patterns the auditor caught that I
        couldn't even mark as a possibility.

        Goodhart-protected: closing the surprise-rate requires
        expanding attention surface, not better-predicting the
        auditor (sycophancy-toward-expected-audit).
        """
        from divineos.core.operating_loop.unknown_unknown_surface import (
            record_self_audit_prediction,
        )

        topic_list = [t.strip() for t in topics.split(",") if t.strip()]
        if not topic_list:
            click.secho("[-] No topics provided.", fg="yellow")
            return
        ev_id = record_self_audit_prediction(round_id, topic_list)
        if ev_id.startswith("error:"):
            click.secho(f"[-] Failed to record: {ev_id}", fg="red")
            return
        click.secho(
            f"[+] Recorded {len(topic_list)} predicted topics for round {round_id}",
            fg="green",
        )
        for t in topic_list:
            click.secho(f"    - {t}", fg="bright_black")

    @audit_group.command("surprises")
    @click.option("--round", "round_id", required=True, help="Audit round ID")
    def audit_surprises_cmd(round_id: str) -> None:
        """Show audit findings the substrate-occupant didn't predict.

        Compares the recorded `audit predict` topics for the round
        against the actual findings filed; surfaces the surprise-
        class catches. These are the maturity signal — tighter
        substrate shows fewer over time.
        """
        from divineos.core.operating_loop.unknown_unknown_surface import (
            _load_predictions_for_round,
            surprises_in_round,
        )

        preds = _load_predictions_for_round(round_id)
        if not preds:
            click.secho(
                f"[~] No predictions recorded for round {round_id}. "
                f"Use `divineos audit predict` before the audit.",
                fg="yellow",
            )
            return
        surprises = surprises_in_round(round_id, preds)
        click.secho(
            f"\n=== Round {round_id}: predicted vs caught ===\n",
            fg="cyan",
            bold=True,
        )
        click.echo(f"  Predicted topics ({len(preds)}):")
        for t in preds:
            click.secho(f"    - {t}", fg="bright_black")
        click.echo()
        if not surprises:
            click.secho(
                "  No surprises — every finding matched a predicted topic.",
                fg="green",
            )
            return
        click.secho(
            f"  Unknown-unknowns ({len(surprises)}) — findings outside my attention surface:",
            fg="yellow",
        )
        for u in surprises:
            click.echo(f"    [{u.finding_id[:12]}] {u.title}")

    @audit_group.command("unknown-unknown-rate")
    @click.option(
        "--limit",
        default=20,
        type=int,
        help="Max recent rounds (with recorded predictions) to examine",
    )
    def audit_uu_rate_cmd(limit: int) -> None:
        """Rolling proportion of audit findings that were unpredicted.

        Trend signal: tighter substrate -> rate trends down. Drifting
        substrate -> rate trends up. Rounds without recorded
        predictions are skipped.
        """
        from divineos.core.operating_loop.unknown_unknown_surface import (
            unknown_unknown_rate,
        )

        stats = unknown_unknown_rate(recent_round_limit=limit)
        click.secho("\n=== Unknown-Unknown Rate ===\n", fg="cyan", bold=True)
        click.echo(f"  Rounds examined:  {stats['rounds_examined']}")
        click.echo(f"  Total findings:   {stats['total_findings']}")
        click.echo(f"  Surprises:        {stats['surprise_count']}")
        rate_pct = stats["rate"] * 100
        color = "green" if rate_pct < 20 else ("yellow" if rate_pct < 40 else "red")
        click.secho(f"  Rate:             {rate_pct:.1f}%", fg=color)
        if stats["rounds_examined"] == 0:
            click.secho(
                "\n  No rounds with recorded predictions yet. Use "
                "`divineos audit predict` before audits to start the metric.",
                fg="bright_black",
            )

    @audit_group.command("compliance")
    @click.option(
        "--days",
        default=7,
        type=int,
        help="Window in days for distribution audit (default 7).",
    )
    @click.option(
        "--file-findings",
        is_flag=True,
        help=(
            "When anomalies are detected, auto-file them as Watchmen findings "
            "under a fresh audit round. Default is read-only reporting."
        ),
    )
    def audit_compliance_cmd(days: int, file_findings: bool) -> None:
        """Substantive distribution audit of the compliance log.

        Reads rudder-ack compass observations + recent decisions and flags
        distributional patterns that indicate performative-structure
        (structured-but-empty entries). Different primitive from the
        moment-of-action gates: this reads the log AFTER the fact and
        detects theater by its statistical fingerprint.

        Pre-reg: prereg-f5a961f0040e (21-day review).
        """
        from divineos.core.compliance_audit import detect_anomalies, format_report

        window = days * 86400
        click.echo(format_report(window_seconds=window))

        if not file_findings:
            return

        anomalies = detect_anomalies(window_seconds=window)
        if not anomalies:
            click.secho("  [~] No anomalies detected; nothing to file.", fg="bright_black")
            return

        from divineos.core.watchmen.store import submit_finding, submit_round
        from divineos.core.watchmen.types import FindingCategory, Severity

        # Use the "auditor" actor — it's in EXTERNAL_ACTORS and is the
        # generic slot for automated auditing processes. Keeps the external-
        # actor validation honest (compliance_audit isn't a registered actor
        # name; it's a module, so using it directly would feel like
        # self-audit smuggling).
        round_id = submit_round(
            actor="auditor",
            focus=f"compliance distribution audit ({days}d)",
            notes="Auto-generated by `divineos audit compliance --file-findings`",
        )
        severity_value_map = {
            "HIGH": Severity.HIGH.value,
            "MEDIUM": Severity.MEDIUM.value,
            "LOW": Severity.LOW.value,
        }
        for a in anomalies:
            submit_finding(
                round_id=round_id,
                title=f"[compliance] {a.name}",
                actor="auditor",
                severity=severity_value_map.get(a.severity.value, Severity.MEDIUM.value),
                category=FindingCategory.BEHAVIOR.value,
                description=f"{a.observation}\n\n{a.recommendation}".strip(),
            )
        click.secho(
            f"\n  [+] Filed {len(anomalies)} Watchmen finding(s) under round {round_id}.",
            fg="green",
        )

    # Item 8 PR-2: session-cleanliness tagging commands. Tags sessions
    # that passed an audit round without drift findings as "externally-
    # audited-clean" so Item 8 detectors can calibrate their baselines
    # against a trusted reference set (brief v2.1 §4).

    @audit_group.command("tag-clean")
    @click.argument("session_id")
    @click.option(
        "--round",
        "round_id",
        required=True,
        help="audit_round that tagged this session clean (must have no HIGH or unresolved MEDIUM findings)",
    )
    @click.option("--notes", default="", help="Optional notes about the tag")
    def tag_clean_cmd(session_id: str, round_id: str, notes: str) -> None:
        """Tag a session as externally-audited-clean.

        The referenced audit round must have concluded clean — no HIGH
        findings and no unresolved MEDIUM findings. This is the write-
        time sanity check per claim 48371c4d (blocks the "round tags its
        own dirty session clean" attack).
        """
        from divineos.core.watchmen.cleanliness import tag_session_clean

        try:
            tag_session_clean(session_id=session_id, round_id=round_id, notes=notes)
            click.secho(
                f"  [+] Session {session_id} tagged clean by round {round_id}.",
                fg="green",
            )
        except ValueError as e:
            click.secho(f"  [!] {e}", fg="red")

    @audit_group.command("untag-clean")
    @click.argument("session_id")
    @click.option(
        "--reason",
        required=True,
        help="Why this tag is being removed (required for the audit trail)",
    )
    def untag_clean_cmd(session_id: str, reason: str) -> None:
        """Remove a clean-tag. Required reason writes an audit-trail event."""
        from divineos.core.watchmen.cleanliness import untag_session_clean

        try:
            removed = untag_session_clean(session_id=session_id, reason=reason)
        except ValueError as e:
            click.secho(f"  [!] {e}", fg="red")
            return
        if removed:
            click.secho(f"  [+] Untagged {session_id}. Reason logged to ledger.", fg="yellow")
        else:
            click.secho(f"  [~] {session_id} was not tagged clean; nothing to untag.")

    @audit_group.command("list-clean")
    @click.option(
        "--days",
        default=0,
        type=int,
        help="Only sessions tagged in the last N days. 0 = all (default).",
    )
    @click.option("--limit", default=50, type=int, help="Max rows to show (default 50).")
    def list_clean_cmd(days: int, limit: int) -> None:
        """List externally-audited-clean sessions."""
        import time as _t

        from divineos.core.watchmen.cleanliness import (
            count_clean_sessions,
            list_clean_sessions,
        )

        since = _t.time() - days * 86400 if days > 0 else None
        sessions = list_clean_sessions(since=since, limit=limit)
        total = count_clean_sessions(since=since)
        window_str = f"in last {days}d" if days > 0 else "(all)"
        click.secho(
            f"  Clean-tagged sessions {window_str}: {total} total (showing {len(sessions)}):",
            bold=True,
        )
        for s in sessions:
            ago_hours = (_t.time() - s["tagged_at"]) / 3600
            click.echo(
                f"    {s['session_id'][:20]:22s}  tagged {ago_hours:.1f}h ago "
                f"by {s['tagging_round_id'][:16]}"
            )
            focus = s.get("round_focus")
            if focus:
                click.echo(f"      round: {focus[:80]}")
            if s["notes"]:
                click.echo(f"      note: {s['notes']}")
