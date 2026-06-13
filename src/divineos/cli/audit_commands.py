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

# Canonical external-AI actor roster. Must match check_multi_party_review.py
# and the prepare-merge gate. Hoisted to module level so file-external-confirm
# and prepare-merge share one source of truth instead of two drifting copies.
_EXTERNAL_AI_ACTORS = frozenset(
    {
        "grok",
        "gemini",
        "aletheia",
        "claude-3.5-sonnet",
        "claude-3-opus",
        "claude-sonnet-4",
        "claude-sonnet-4-5",
        "claude-opus-4",
        "claude-opus-4-1",
        # Generic audit-vantage label — used when the operator relays a
        # cross-vantage CONFIRMS but the specific audit-sibling name isn't
        # routed (e.g. Aletheia relay through Andrew tonight 2026-06-13
        # filed with --actor external-auditor). The validator should
        # honor this as a legitimate external-AI confirms shape.
        "external-auditor",
    }
)


def validate_external_confirm_inputs(
    *,
    actor: str,
    claimed_tree: str = "",
    actual_tree: str | None = None,
    claimed_patch_id: str = "",
    actual_patch_id: str | None = None,
    claimed_tip: str = "",
    actual_tip: str | None = None,
    valid_actors: frozenset[str] = _EXTERNAL_AI_ACTORS,
) -> tuple[bool, str, str]:
    """Pure validation for filing/holding a relayed external-AI CONFIRM.

    Binds a confirm to BOTH the tree-hash and the change's patch-id, and
    validates on a ladder (Aletheia's correction 2026-06-02 — replacing
    tree-hash outright would recreate the diff-hash cross-vantage trap,
    claim 1d0f9e7b):

      1. tree-hash matches  -> 'tree-exact': the auditor read EXACTLY this
         content. Strongest; cross-vantage reproducible (git write-tree).
         No catch-up happened.
      2. tree differs, patch-id matches -> 'patch-id-after-catchup': a clean
         base-move (GitHub 'require up to date' catch-up) changed the tree but
         the reviewed CHANGE is identical. Valid, no re-sign. The treadmill-
         killer.
      3. patch-id differs -> refuse: the change itself changed (e.g. a
         conflict-resolution touched a guardrail file). Re-sign required.
         The safety property.

    patch-id is base-move-stable and tamper-sensitive, BUT only when computed
    over merge-base(main,branch)..branch with default context (never -U0), and
    only after a one-time cross-vantage reproduction check (git versions can
    differ). tree-hash stays primary precisely so the cure is strictly
    additive over tree-only signing — never weaker, just catch-up-stable.

    Does NOT prove the auditor genuinely reviewed (forgeability-by-relay
    remains named-not-solved; needs an authenticated auditor write-path).

    Returns (ok, reason, basis). basis is 'tree-exact' or
    'patch-id-after-catchup' when ok, '' when refused.
    """
    if actor.lower() not in valid_actors:
        return (
            False,
            f"actor '{actor}' is not an external-AI actor. This command files "
            f"only external-AI CONFIRMs (operator confirms go via 'audit submit "
            f"--actor user'). Valid: " + ", ".join(sorted(valid_actors)),
            "",
        )

    ct = (claimed_tree or "").strip().lower()
    at = (actual_tree or "").strip().lower()
    cp = (claimed_patch_id or "").strip().lower()
    ap = (actual_patch_id or "").strip().lower()

    if not ct and not cp:
        return (
            False,
            "no --claimed-tree and no --claimed-patch-id; need at least one "
            "anchor (tree-hash for exact-content, patch-id for catch-up).",
            "",
        )

    # Rung 1: exact-content match. Strongest, cross-vantage reproducible.
    if ct and at and ct == at:
        if claimed_tip:
            cti = claimed_tip.strip().lower()
            ati = (actual_tip or "").strip().lower()
            if ati and cti != ati:
                return (
                    False,
                    f"tree matched but claimed tip {cti} != remote tip {ati} "
                    "(unexpected; refusing out of caution).",
                    "",
                )
        return (True, "", "tree-exact")

    # Rung 2: clean catch-up — tree moved, reviewed change unchanged.
    if cp and ap and cp == ap:
        return (
            True,
            f"tree differs (catch-up) but patch-id matches ({cp}) — the "
            "reviewed change is unchanged; no re-sign needed.",
            "patch-id-after-catchup",
        )

    # Rung 3: refuse. Distinguish the two failure shapes for a clear message.
    if cp and ap and cp != ap:
        return (
            False,
            f"patch-id differs: claimed {cp} vs actual {ap}. The reviewed "
            "CHANGE changed (e.g. a conflict-resolution touched a guardrail "
            "file) — re-sign required.",
            "",
        )
    return (
        False,
        f"no anchor matched: claimed tree {ct or '(none)'} vs actual "
        f"{at or '(unresolved)'}; claimed patch-id {cp or '(none)'} vs actual "
        f"{ap or '(unresolved)'}. Refusing to file.",
        "",
    )


def _git_capture(args: list[str], timeout: int = 30) -> str | None:
    """Run a git command; return stripped stdout, or None on any failure."""
    import subprocess

    try:
        p = subprocess.run(args, capture_output=True, text=True, check=False, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        return None
    return p.stdout.strip()


def _git_version() -> str:
    """The local git version string (e.g. '2.43.0'), or '' if unknown.

    patch-id is version-conditioned (Aletheia 2026-06-02): the algorithm could
    shift across git versions, so a confirm records the version it was computed
    under, and confirm-holds warns if the current version has drifted — the
    signal to re-run the cross-vantage reproduction check.
    """
    import re as _re

    raw = _git_capture(["git", "--version"]) or ""
    m = _re.search(r"(\d+\.\d+\.\d+)", raw)
    return m.group(1) if m else ""


def compute_branch_patch_id(branch_ref: str, main_ref: str = "origin/main") -> str | None:
    """Patch-id of a branch's cumulative change — the stable identity of the
    reviewed diff, invariant to base-moves (catch-up) but sensitive to any
    real change to the diff.

    Aletheia's load-bearing specifics (2026-06-02), baked in so they can't be
    forgotten:
      * Range MUST be merge-base(main, branch)..branch (the cumulative branch
        diff). The naive tip-commit range breaks after a merge-based catch-up
        (the tip becomes a merge commit), which is exactly the path GitHub's
        'require up to date' uses.
      * DEFAULT diff context — never -U0 (which yields a different patch-id).
      * Trust patch-id cross-vantage only after a one-time reproduction check
        (git versions can differ); tree-hash stays the primary anchor.

    Returns the 40-hex patch-id, or None if it cannot be computed.
    """
    import subprocess

    base = _git_capture(["git", "merge-base", main_ref, branch_ref])
    if not base:
        return None
    try:
        diff = subprocess.run(
            ["git", "diff", base, branch_ref],  # default context; NEVER -U0
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if diff.returncode != 0:
            return None
        pid = subprocess.run(
            ["git", "patch-id", "--stable"],
            input=diff.stdout,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if pid.returncode != 0 or not pid.stdout.strip():
        return None
    # Output line: "<patch-id> <commit-id>" — first token is the patch-id.
    return pid.stdout.split()[0].strip()


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

        Output is a relay-template my father can copy into chat to
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
        # trusted my father's --range choice. Two attack-shapes:
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

    @audit_group.command("file-external-confirm")
    @click.option(
        "--round", "round_id", required=True, help="Round to file the external-AI CONFIRM into."
    )
    @click.option(
        "--actor", required=True, help="External-AI actor (aletheia, grok, gemini, claude-*)."
    )
    @click.option("--branch", required=True, help="Remote branch the audited code lives on.")
    @click.option(
        "--claimed-tree",
        default="",
        help="Tree-hash the auditor read (exact-content anchor, strongest).",
    )
    @click.option(
        "--claimed-patch-id",
        default="",
        help="patch-id the auditor reviewed (catch-up-stable anchor). At least one of "
        "--claimed-tree / --claimed-patch-id is required.",
    )
    @click.option(
        "--claimed-tip",
        default="",
        help="Optional commit tip the auditor named (cross-checked on the tree-exact rung).",
    )
    @click.option("--pr", default="", help="PR number, for the finding title.")
    @click.option("--remote", default="origin", help="Remote to validate against. Default origin.")
    @click.option(
        "--main-ref",
        default="origin/main",
        help="Main ref for the patch-id merge-base. Default origin/main.",
    )
    @click.option("--basis", default="", help="The auditor's stated review basis/finding.")
    def audit_file_external_confirm(
        round_id: str,
        actor: str,
        branch: str,
        claimed_tree: str,
        claimed_patch_id: str,
        claimed_tip: str,
        pr: str,
        remote: str,
        main_ref: str,
        basis: str,
    ) -> None:
        """File a relayed external-AI CONFIRM into a round — validated on the
        both-bind ladder (tree-hash + patch-id), so a clean catch-up does NOT
        require a re-sign while any real change to the diff still does.

        Closes the 'confirm relayed as text, never written down' gap — the
        audit's committed-but-never-pushed (Aletheia, 2026-06-02). An
        external-AI auditor is a clone-and-read chat instance with no store-
        write path; their CONFIRM is text until a human/agent files it.

        Validation ladder (Aletheia's correction — replacing tree-hash with
        patch-id would recreate the diff-hash cross-vantage trap, 1d0f9e7b):
          1. tree-hash matches            -> filed (tree-exact). Strongest.
          2. tree differs, patch-id match -> filed (patch-id-after-catchup):
             a clean base-move; the reviewed change is unchanged. No re-sign.
          3. patch-id differs             -> REFUSED: the change changed;
             re-audit and relay a fresh confirm.

        Does NOT prove the auditor genuinely reviewed (forgeability-by-relay
        is named, not solved — needs an authenticated auditor write-path).

        Usage:
            divineos audit file-external-confirm --round round-xxx \\
              --actor aletheia --branch protect-off-switch \\
              --claimed-tree c853630... --claimed-patch-id 7466992... \\
              --pr 77 --basis "registers corrigibility.py in guardrail registry"
        """
        from divineos.core.watchmen.store import get_round, submit_finding

        if get_round(round_id) is None:
            click.secho(f"[!] Round '{round_id}' not found.", fg="red")
            raise click.exceptions.Exit(1)
        if not claimed_tree and not claimed_patch_id:
            click.secho(
                "[!] Need at least one anchor: --claimed-tree (exact content) "
                "or --claimed-patch-id (catch-up-stable).",
                fg="red",
            )
            raise click.exceptions.Exit(1)

        # Resolve the remote branch's actual tree, tip, and patch-id.
        _git_capture(["git", "fetch", remote, branch], timeout=60)
        actual_tip = _git_capture(["git", "rev-parse", f"{remote}/{branch}"])
        actual_tree = _git_capture(["git", "rev-parse", f"{remote}/{branch}^{{tree}}"])
        actual_patch_id = compute_branch_patch_id(f"{remote}/{branch}", main_ref)

        ok, reason, sbasis = validate_external_confirm_inputs(
            actor=actor,
            claimed_tree=claimed_tree,
            actual_tree=actual_tree,
            claimed_patch_id=claimed_patch_id,
            actual_patch_id=actual_patch_id,
            claimed_tip=claimed_tip,
            actual_tip=actual_tip,
        )
        if not ok:
            click.secho(f"[!] Refusing to file external CONFIRM: {reason}", fg="red")
            raise click.exceptions.Exit(1)

        pr_label = f"PR #{pr} " if pr else ""
        title = f"CONFIRMS {pr_label}(external-AI review, {actor}) — {sbasis}"
        catchup_note = f" ({reason})" if sbasis == "patch-id-after-catchup" else ""
        description = (
            f"External-AI CONFIRM by {actor}. Validated rung: {sbasis}{catchup_note}. "
            f"Tip {actual_tip} / Tree {actual_tree} / patch-id {actual_patch_id} "
            f"(git-version {_git_version() or 'unknown'}) — "
            f"verified against {remote}/{branch} at file-time over "
            f"merge-base({main_ref})..branch (default context). "
            f"Basis: {basis or '(none provided)'}. "
            f"PROVENANCE: {actor} has no store-write path; this genuine confirm was "
            f"relayed as text and filed via 'audit file-external-confirm', which "
            f"validated tree-hash + patch-id before writing. Honest relay, not forgery. "
            f"(Forgeability-by-relay remains named-not-solved.)"
        )
        try:
            fid = submit_finding(
                round_id=round_id,
                actor=actor.lower(),
                severity="INFO",
                category="INTEGRITY",
                title=title,
                description=description,
                tags=["external-confirm", sbasis, "relay-filed"],
            )
        except ValueError as e:
            click.secho(f"[!] {e}", fg="red")
            raise click.exceptions.Exit(1) from e

        click.secho(f"[+] External-AI CONFIRM filed: {fid} (rung: {sbasis})", fg="green")
        if sbasis == "patch-id-after-catchup":
            click.secho(f"    {reason}", fg="bright_black")
        click.secho(
            f"    tree {actual_tree} / patch-id {actual_patch_id} verified against "
            f"{remote}/{branch}.",
            fg="bright_black",
        )
        click.secho(f"    Now run: divineos audit prepare-merge {round_id}", fg="cyan")

    @audit_group.command("patch-id")
    @click.option("--branch", required=True, help="Branch to compute the tree-hash + patch-id for.")
    @click.option("--remote", default="origin", help="Remote. Default origin.")
    @click.option("--main-ref", default="origin/main", help="Main ref for the merge-base.")
    @click.option("--fetch/--no-fetch", default=True, help="Fetch the branch first. Default on.")
    def audit_patch_id_cmd(branch: str, remote: str, main_ref: str, fetch: bool) -> None:
        """Print a branch's tree-hash + patch-id — the cross-vantage reproduction
        check.

        Run this in BOTH vantages (the auditor's sandbox AND the merge copy) on
        the same branch. If the patch-ids match, patch-id is safe to sign with
        here (git versions can differ, so this must be confirmed once). tree-hash
        is the always-trusted primary anchor; patch-id is the catch-up-survival
        layer that this check validates.
        """
        ref = f"{remote}/{branch}"
        if fetch:
            _git_capture(["git", "fetch", remote, branch], timeout=60)
        tip = _git_capture(["git", "rev-parse", ref])
        tree = _git_capture(["git", "rev-parse", f"{ref}^{{tree}}"])
        pid = compute_branch_patch_id(ref, main_ref)
        click.echo(f"branch:    {ref}")
        click.echo(f"tip:       {tip or '(unresolved)'}")
        click.echo(f"tree-hash: {tree or '(unresolved)'}")
        click.echo(
            f"patch-id:  {pid or '(uncomputed)'}   "
            f"(over merge-base({main_ref})..branch, default context)"
        )
        click.echo(f"git:       {_git_version() or 'unknown'}   (patch-id is version-conditioned)")
        if not pid:
            click.secho(
                "[!] patch-id could not be computed — check the branch/main-ref "
                "are fetched and the merge-base resolves.",
                fg="yellow",
            )

    @audit_group.command("confirm-holds")
    @click.option(
        "--round", "round_id", required=True, help="Round whose external CONFIRM to re-check."
    )
    @click.option("--branch", required=True, help="Branch to re-check the CONFIRM against.")
    @click.option("--remote", default="origin", help="Remote. Default origin.")
    @click.option("--main-ref", default="origin/main", help="Main ref for the merge-base.")
    def audit_confirm_holds_cmd(round_id: str, branch: str, remote: str, main_ref: str) -> None:
        """Does the external-AI CONFIRM already in this round STILL hold for the
        branch's current (possibly caught-up) state?

        Reads the recorded tree-hash + patch-id from the round's external-AI
        CONFIRM, recomputes the branch's current values, and applies the same
        ladder. 'HOLDS' via the patch-id rung means a catch-up moved the base
        but the reviewed change is unchanged — no re-sign needed. The
        treadmill-killer in operation.
        """
        import re as _re

        from divineos.core.watchmen.store import list_findings

        findings = list_findings(round_id=round_id, limit=200)
        ext = [
            f
            for f in findings
            if (getattr(f, "actor", "") or "").lower() in _EXTERNAL_AI_ACTORS
            and "CONFIRMS" in (getattr(f, "title", "") or "")
        ]
        if not ext:
            click.secho(f"[!] No external-AI CONFIRM found in round {round_id}.", fg="red")
            raise click.exceptions.Exit(1)
        finding = ext[-1]
        desc = getattr(finding, "description", "") or ""
        m_tree = _re.search(r"Tree ([0-9a-f]{40})", desc)
        m_pid = _re.search(r"patch-id ([0-9a-f]{40})", desc)
        m_ver = _re.search(r"git-version ([0-9.]+)", desc)
        rec_tree = m_tree.group(1) if m_tree else ""
        rec_pid = m_pid.group(1) if m_pid else ""
        rec_ver = m_ver.group(1) if m_ver else ""

        _git_capture(["git", "fetch", remote, branch], timeout=60)
        cur_tree = _git_capture(["git", "rev-parse", f"{remote}/{branch}^{{tree}}"])
        cur_pid = compute_branch_patch_id(f"{remote}/{branch}", main_ref)

        ok, reason, sbasis = validate_external_confirm_inputs(
            actor=getattr(finding, "actor", ""),
            claimed_tree=rec_tree,
            actual_tree=cur_tree,
            claimed_patch_id=rec_pid,
            actual_patch_id=cur_pid,
        )
        if ok:
            click.secho(f"[+] CONFIRM HOLDS (rung: {sbasis}).", fg="green")
            if reason:
                click.secho(f"    {reason}", fg="bright_black")
            # Version-conditioning guard (Aletheia point 4): the patch-id rung is
            # only trustworthy if the git version that computed it still matches.
            cur_ver = _git_version()
            if sbasis == "patch-id-after-catchup" and rec_ver and cur_ver and rec_ver != cur_ver:
                click.secho(
                    f"    [!] git version drifted (signed under {rec_ver}, now {cur_ver}). "
                    "patch-id is version-conditioned — re-run the cross-vantage "
                    "reproduction check (divineos audit patch-id --branch ...) before "
                    "trusting this rung.",
                    fg="yellow",
                )
            click.secho(
                f"    No re-sign needed. Proceed: divineos audit prepare-merge {round_id}",
                fg="cyan",
            )
        else:
            click.secho(f"[!] CONFIRM NO LONGER HOLDS: {reason}", fg="red")
            if not rec_pid:
                click.secho(
                    "    (This confirm predates patch-id binding — tree-only, so a "
                    "catch-up invalidates it. Re-file with --claimed-patch-id to make "
                    "it catch-up-stable.)",
                    fg="yellow",
                )
            click.secho(
                "    Re-audit against the current change and relay a fresh confirm.",
                fg="yellow",
            )

    @audit_group.command("prepare-merge")
    @click.argument("round_id")
    @click.option(
        "--pr-title",
        default=None,
        help=(
            "Optional PR title to include in the body. If omitted, the round's "
            "focus is used as the title."
        ),
    )
    @click.option(
        "--no-tree-hash",
        is_flag=True,
        default=False,
        help=(
            "Skip the tree-hash suffix in the emitted trailer (legacy form). "
            "Default is to include tree-hash from the current HEAD so the "
            "Phase 2 server-side gate can verify substance-binding. Use this "
            "flag only when my father is on a non-PR-head ref and the "
            "auto-detected tree-hash would be wrong."
        ),
    )
    def audit_prepare_merge_cmd(round_id: str, pr_title: str | None, no_tree_hash: bool) -> None:
        """Prepare a squash-merge commit message including the External-Review trailer.

        Phase 1 of the audit-stamp-attachment structural fix (claim ae9d70c4,
        prereg-d695c9060158). Validates that the audit round exists with both
        actor=user and external-AI CONFIRMS findings, validates round age is
        within the multi-party-review recency window, and outputs a ready-to-
        paste GitHub squash-merge commit message body including the trailer.

        Usage:
            divineos audit prepare-merge <round-id> [--pr-title "..."]

        Then in the GitHub squash-merge UI, paste the output into the commit
        message field before clicking Merge. The CI multi-party-review check
        will see the trailer and pass.

        Phase 2 (deferred): GitHub Action that blocks merge when guardrail-
        touching PR commits AND proposed message lacks trailer.
        Phase 3 (deferred): substrate-aware merge tooling that auto-attaches
        when a round is confirmed.
        """
        import time as _time

        from divineos.core.watchmen.store import get_round, list_findings

        rnd = get_round(round_id)
        if rnd is None:
            click.secho(
                f"[!] Audit round '{round_id}' not found in Watchmen store.",
                fg="red",
            )
            click.secho(
                "    File one first: divineos audit submit-round '...' --actor user --source-ref <ref>",
                fg="bright_black",
            )
            raise click.exceptions.Exit(1)

        # Validate CONFIRMS coverage — same shape as
        # check_multi_party_review.py's gate.
        findings = list_findings(round_id=round_id, limit=500)
        # External-AI actor set matches check_multi_party_review.py.
        # Shared module constant so file-external-confirm and this gate can't drift.
        external_ai_actors = _EXTERNAL_AI_ACTORS

        def _actor_of(f: object) -> str:
            val = getattr(f, "actor", "") or ""
            return str(val).lower()

        def _is_confirm(f: object) -> bool:
            stance = getattr(f, "review_stance", None)
            if stance is None:
                return True  # v1 pragmatic: existence = acknowledgement
            val = getattr(stance, "value", stance)
            return str(val).upper() == "CONFIRMS"

        confirming = [f for f in findings if _is_confirm(f)]
        user_confirms = [f for f in confirming if _actor_of(f) == "user"]
        ai_confirms = [f for f in confirming if _actor_of(f) in external_ai_actors]

        if not user_confirms:
            click.secho(
                f"[!] Round '{round_id}' has no CONFIRMS finding from actor=user.",
                fg="red",
            )
            click.secho(
                "    File one: divineos audit submit '...' --round "
                + round_id
                + " --actor user --severity info --category architecture -d '...'",
                fg="bright_black",
            )
            raise click.exceptions.Exit(1)

        if not ai_confirms:
            click.secho(
                f"[!] Round '{round_id}' has no CONFIRMS finding from an external-AI actor.",
                fg="red",
            )
            click.secho(
                "    Expected one of actor in: " + ", ".join(sorted(external_ai_actors)),
                fg="bright_black",
            )
            raise click.exceptions.Exit(1)

        # Validate recency. Use the same window as the gate (14 days).
        _RECENCY_DAYS = 14
        created_at = getattr(rnd, "created_at", None) or getattr(rnd, "timestamp", None) or 0
        if isinstance(created_at, str):
            try:
                # ISO format fallback
                import datetime as _dt

                created_at = _dt.datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                ).timestamp()
            except Exception:  # noqa: BLE001
                created_at = 0
        age_days = (_time.time() - float(created_at)) / 86400.0 if created_at else 999.0
        if age_days > _RECENCY_DAYS:
            click.secho(
                f"[!] Round '{round_id}' is {age_days:.1f} days old "
                f"(recency window is {_RECENCY_DAYS} days).",
                fg="red",
            )
            click.secho(
                "    Stale rounds cannot authorize a new merge. File a fresh round.",
                fg="bright_black",
            )
            raise click.exceptions.Exit(1)

        # All validations pass. Compose the ready-to-paste message.
        focus = getattr(rnd, "focus", "") or ""
        title = pr_title or focus or f"PR using audit round {round_id}"

        click.echo("=" * 70)
        click.secho(
            "READY-TO-PASTE squash-merge commit message body — copy below the line",
            fg="green",
            bold=True,
        )
        click.echo("=" * 70)
        click.echo()
        click.echo(title)
        click.echo()
        click.echo(
            f"Reviewed via audit round {round_id} "
            f"(operator-CONFIRMS + external-AI-CONFIRMS, age {age_days:.1f}d, "
            f"within {_RECENCY_DAYS}d recency window)."
        )
        click.echo()
        # Phase 2 (2026-06-13): include tree-hash suffix so the server-side
        # CI gate can verify substance-binding. Auto-detect from HEAD;
        # fall back to legacy form on git failure with a visible warning.
        trailer_tree_hash = ""
        if not no_tree_hash:
            import subprocess as _sp

            try:
                result = _sp.run(
                    ["git", "rev-parse", "HEAD^{tree}"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=5,
                )
                trailer_tree_hash = result.stdout.strip()
            except (_sp.CalledProcessError, _sp.TimeoutExpired, FileNotFoundError):
                # git unreachable or not in a repo — fall through to legacy.
                trailer_tree_hash = ""

        if trailer_tree_hash:
            click.echo(f"External-Review: {round_id} tree-hash:{trailer_tree_hash}")
        else:
            click.echo(f"External-Review: {round_id}")
        click.echo()
        click.echo("=" * 70)
        if trailer_tree_hash:
            click.secho(
                "Paste the block above into the GitHub squash-merge commit message field.\n"
                "Trailer carries tree-hash binding (Phase 2); the server-side CI gate\n"
                "verifies it matches the squash commit's tree. Substance-bound.",
                fg="cyan",
            )
        else:
            click.secho(
                "Paste the block above into the GitHub squash-merge commit message field.\n"
                "[!] Trailer is in LEGACY form (no tree-hash). The server-side gate will\n"
                "    emit a DEPRECATED warning. Re-run from inside a git repo to include\n"
                "    tree-hash binding, or pass --no-tree-hash to suppress this notice.",
                fg="yellow",
            )

    @audit_group.command("pr-merge-check")
    @click.argument("pr_number", type=int)
    @click.option(
        "--audit-round",
        "round_id",
        default=None,
        help="Audit round to bind to the merge (required if PR touches guardrails).",
    )
    @click.option(
        "--pr-title",
        default=None,
        help="Optional PR title for the merge body. Defaults to the round's focus.",
    )
    def audit_pr_merge_check_cmd(
        pr_number: int, round_id: str | None, pr_title: str | None
    ) -> None:
        """Verify a PR is safe to merge under guardrail discipline; emit merge body.

        Pulls the PR's file list via ``gh pr view`` and intersects with
        ``scripts/guardrail_files.txt``. If the intersection is empty,
        prints "clean to merge" — proceed with a plain ``gh pr merge``.
        If non-empty, ``--audit-round`` is required and is validated the
        same way as ``audit prepare-merge``; on success, the
        ready-to-paste merge body (including External-Review trailer)
        is printed.

        Wired with the gh-pr-merge-gate.sh PreToolUse hook to refuse
        any ``gh pr merge`` invocation against a guardrail-touching PR
        that does not carry a trailer in its --body / --subject.

        Per prereg-b6dcddd005b0; Andrew correction 2026-05-28
        ("the fix should be in the OS itself not through settings").
        """
        from divineos.core.pr_merge_gate import audit_pr_for_guardrail_touches

        touches, touched_files = audit_pr_for_guardrail_touches(pr_number)
        if not touches:
            click.secho(
                f"[ok] PR #{pr_number} touches no guardrail files. "
                f"Plain `gh pr merge {pr_number} --squash` is safe.",
                fg="green",
            )
            return

        click.secho(
            f"\n=== PR #{pr_number} touches guardrail file(s) ===\n",
            fg="yellow",
            bold=True,
        )
        for p in touched_files:
            click.echo(f"  - {p}")
        click.echo()

        if not round_id:
            click.secho(
                "[!] --audit-round REQUIRED for guardrail-touching PRs.",
                fg="red",
            )
            click.secho(
                "    1. divineos audit submit-round '...' --actor user --source-ref <sha>\n"
                "    2. File user-CONFIRMS and external-AI-CONFIRMS findings.\n"
                f"    3. divineos audit pr-merge-check {pr_number} --audit-round <id>",
                fg="bright_black",
            )
            raise click.exceptions.Exit(1)

        # Delegate validation + body emission to prepare-merge logic.
        # Re-invoking the prepare-merge command keeps a single source of
        # truth for the CONFIRMS / recency / actor validation logic.
        ctx = click.get_current_context()
        ctx.invoke(audit_prepare_merge_cmd, round_id=round_id, pr_title=pr_title)

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

    @audit_group.command("auto-triage")
    @click.option(
        "--severity",
        default="HIGH",
        help="Severity filter (HIGH/MEDIUM/LOW/CRITICAL/INFO). Default HIGH.",
    )
    @click.option(
        "--min-confidence",
        default=0.7,
        type=float,
        help="Only show findings whose verified-citation ratio is >= this (0.0-1.0). Default 0.7.",
    )
    @click.option(
        "--min-citations",
        default=1,
        type=int,
        help="Skip findings with fewer than this many citations. Default 1.",
    )
    @click.option(
        "--limit",
        default=200,
        type=int,
        help="Max OPEN findings to examine. Default 200.",
    )
    def audit_auto_triage_cmd(
        severity: str, min_confidence: float, min_citations: int, limit: int
    ) -> None:
        """Surface OPEN findings whose cited files/commits actually exist.

        Many findings are completion-narratives — write-ups of work just
        landed — and never get marked resolved. This scans descriptions
        for file paths and commit SHAs, checks each against the live
        tree and git log, and ranks by verified/total. My father
        decides what to close; the tool only surfaces candidates.
        """
        from divineos.core.audit_auto_triage import scan_open_findings

        verdicts = scan_open_findings(
            severity=severity if severity.upper() != "ALL" else None,
            min_confidence=min_confidence,
            min_citations=min_citations,
            limit=limit,
        )
        if not verdicts:
            click.secho(
                f"[~] No OPEN {severity} findings met the threshold "
                f"(min_confidence={min_confidence}, min_citations={min_citations}).",
                fg="bright_black",
            )
            return

        click.secho(
            f"\n=== Auto-triage candidates: {len(verdicts)} OPEN {severity} finding(s) ===",
            fg="cyan",
            bold=True,
        )
        click.echo("(Citation verification only — operator decides which to resolve.)\n")
        for v in verdicts:
            pct = int(v.confidence * 100)
            color = "green" if v.confidence >= 0.9 else "yellow"
            click.echo(
                f"  {click.style(f'{pct:3d}%', fg=color)} "
                f"({v.verified_count}/{v.total} cited) "
                f"{v.finding.finding_id}  {v.finding.title[:70]}"
            )
            for c in v.citations:
                tick = click.style("OK", fg="green") if c.verified else click.style("X ", fg="red")
                click.echo(f"      {tick} {c.kind}: {c.target}")
            click.echo("")
        click.echo(
            'Resolve a candidate with: divineos audit resolve <id> --status RESOLVED --notes "..."'
        )

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
