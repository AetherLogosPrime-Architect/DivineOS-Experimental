"""divineos ship <pr> -- the merge checks in order, then the button.

Dad, 2026-10-02: "if you are forgetting rules then those are rife for
automation so they cannot be forgotten". First cut: every check runs
read-only, one line per step, stopping at the first that fails. When all
pass, the merge command is printed with its trailer written literally. It is
never run here and auto-merge is never turned on: the machine hands me the
button and the press stays mine.

Draft: docs/drafts/one_command_from_confirm_to_main_draft_2026-10-02.md.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import click

from divineos.core.ship_steps import confirm_in

_PASSING = frozenset({"SUCCESS", "SKIPPED", "NEUTRAL"})


@dataclass(frozen=True)
class Step:
    name: str
    ok: bool
    reason: str


def _pr_facts(pr: int) -> dict:
    out = subprocess.run(
        ["gh", "pr", "view", str(pr), "--json", "state,isDraft,headRefOid,statusCheckRollup"],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    facts: dict = json.loads(out.stdout)
    return facts


def read_step(facts: dict, pr: int) -> Step:
    if facts.get("state") != "OPEN":
        return Step("read", False, f"#{pr} is {str(facts.get('state', '?')).lower()}, not open")
    if facts.get("isDraft"):
        return Step("read", False, f"#{pr} is still a draft")
    return Step("read", True, f"#{pr} is open at {facts['headRefOid'][:9]}")


def user_confirm_step(findings, round_id: str, pr: int, head: str) -> Step:
    """Dad's confirm in her round. Found, never written here."""
    line = re.compile(rf"CONFIRMS:\s*#{pr}\s+at\s+`?([0-9a-f]{{7,40}})", re.IGNORECASE)
    for f in findings:
        if str(getattr(f, "round_id", "")) != round_id:
            continue
        if str(getattr(f, "actor", "")).lower() != "user":
            continue
        m = line.search(str(getattr(f, "title", "") or ""))
        if m and head.lower().startswith(m.group(1).lower()):
            return Step("dad", True, f"his confirm of #{pr} at {head[:9]} is in {round_id}")
    return Step("dad", False, f"no confirm of his for #{pr} at {head[:9]} in {round_id}")


def checks_step(facts: dict) -> Step:
    rollup = facts.get("statusCheckRollup") or []
    if not rollup:
        return Step("checks", False, "no checks have reported on this head yet")
    waiting: list[str] = []
    failed: list[str] = []
    succeeded = 0
    for c in rollup:
        name = c.get("name") or c.get("context") or "?"
        state = (c.get("conclusion") or c.get("state") or "").upper()
        if state in _PASSING:
            succeeded += state == "SUCCESS"
            continue
        (
            waiting if state in ("", "PENDING", "QUEUED", "IN_PROGRESS", "EXPECTED") else failed
        ).append(name)
    if failed:
        return Step("checks", False, "failed: " + ", ".join(sorted(failed)))
    if waiting:
        return Step("checks", False, "still running: " + ", ".join(sorted(waiting)))
    # Skipped is not evidence the suite ran (Aria's cold read, 2026-10-03).
    if not succeeded:
        return Step("checks", False, f"no check concluded SUCCESS: all {len(rollup)} were skipped")
    return Step(
        "checks", True, f"{succeeded} passed, {len(rollup) - succeeded} skipped, none failed"
    )


# The house's own form: watchmen/store.py, round- plus twelve hex of a uuid4.
_ROUND_ID = re.compile(r"round-[0-9a-f]{12}")


def button(pr: int, round_id: str) -> str:
    """The merge line to paste. The id is checked first, because the line acts
    in whoever pastes it (Aria's cold read, 2026-10-03)."""
    if not _ROUND_ID.fullmatch(round_id):
        raise ValueError(f"round id {round_id!r} is not in the house's form; nothing printed")
    # The trailer must START a line: the merge guard reads it that way and
    # refused the one-line form this used to print (Breaker, 2026-10-04).
    return f'gh pr merge {pr} --squash --body "Merged with divineos ship.\n\nExternal-Review: {round_id}"'


def _her_signed_versions(findings, pr: int) -> list[str]:
    """The versions of this PR she confirmed in a recorded finding, newest first.

    Hex only, via the same line her letters are read with, so an approval
    naming a ref ("at main") never becomes a candidate (Schneier, 2026-10-05).
    """
    from divineos.core.ship_steps import _confirm_line

    pattern = _confirm_line(pr)
    seen: list[str] = []
    for f in reversed(list(findings)):
        if str(getattr(f, "actor", "")).lower() != "aletheia":
            continue
        m = pattern.search(str(getattr(f, "title", "") or ""))
        if m and m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def run_steps(
    pr: int, facts: dict, findings, letters_dir: Path, prove=None
) -> tuple[list[Step], str | None]:
    """Each step in order; stops at the first that fails. Returns the button if all pass.

    ``prove(confirmed_sha, head_sha) -> Verdict`` is the floor proof
    (ship_steps.head_is_only on this repo). When her confirm names an earlier
    version, the head may still ship if it is only that version plus main: Dad's
    standing permission for floor-only moves (09-03, 09-05, 09-24, 10-05). Both
    signatures must name that same version (Lamport), and the floor is its own
    step so it never reads as "she confirmed the head" (Norman). Without a
    prover the button behaves as before: her confirm must name the head.
    """
    steps = [read_step(facts, pr)]
    if not steps[-1].ok:
        return steps, None
    head = facts["headRefOid"]
    signed_at = head
    verdict = confirm_in(findings, pr, head, letters_dir)
    if not verdict.ok and prove is not None:
        for version in _her_signed_versions(findings, pr):
            earlier = confirm_in(findings, pr, version, letters_dir)
            if not earlier.ok or earlier.confirm is None:
                continue
            floor = prove(version, head)
            steps.append(Step("her", True, earlier.reason))
            steps.append(Step("floor", floor.ok, floor.reason))
            if not floor.ok:
                return steps, None
            verdict, signed_at = earlier, version
            break
    if signed_at == head:
        steps.append(Step("her", verdict.ok, verdict.reason))
    if not verdict.ok or verdict.confirm is None:
        return steps, None
    round_id = verdict.confirm.round_id
    steps.append(user_confirm_step(findings, round_id, pr, signed_at))
    if not steps[-1].ok:
        return steps, None
    steps.append(checks_step(facts))
    if not steps[-1].ok:
        return steps, None
    return steps, button(pr, round_id)


def register(cli: click.Group) -> None:
    @cli.command("ship")
    @click.argument("pr_number", type=int)
    @click.option(
        "--letters",
        "letters_dir",
        type=click.Path(file_okay=False, path_type=Path),
        default=None,
        help="Folder holding her letters. Defaults to this house's family/letters.",
    )
    def ship(pr_number: int, letters_dir: Path | None) -> None:
        """Check a PR step by step and, if every step passes, print its merge command."""
        from divineos.core.auto_commit import find_repo_root
        from divineos.core.watchmen.store import list_findings

        if letters_dir is None:
            root = find_repo_root(Path.cwd())
            if root is None:
                raise click.ClickException("not inside the house; pass --letters")
            letters_dir = root / "family" / "letters"
        try:
            facts = _pr_facts(pr_number)
        except (subprocess.SubprocessError, OSError, ValueError) as exc:
            raise click.ClickException(f"could not read #{pr_number} from GitHub: {exc}") from exc
        from divineos.core.ship_steps import head_is_only

        prove = None
        repo = find_repo_root(Path.cwd())
        if repo is not None:
            here: Path = repo

            def prove(confirmed: str, head: str):
                # The head must be visible here for the proof to read it; if the
                # fetch fails the proof says it could not see the commit and
                # refuses (Pearl: a commit that cannot be seen is never a pass).
                # Main too (Aria's cold read, 2026-10-05): the proof asks whether
                # the merged-in parent is on origin/main as THIS computer last saw
                # it. Stale can only refuse a good catch-up, never pass a bad one.
                for ref in (f"pull/{pr_number}/head", "main"):
                    subprocess.run(
                        ["git", "-C", str(here), "fetch", "-q", "origin", ref],
                        capture_output=True,
                    )
                return head_is_only(here, confirmed, head)

        steps, merge = run_steps(
            pr_number, facts, list_findings(limit=1000), letters_dir, prove=prove
        )
        for s in steps:
            click.echo(f"[{'ok' if s.ok else 'STOP'}] {s.name}: {s.reason}")
        if merge is None:
            raise SystemExit(1)
        click.echo("")
        click.echo("Every step passed. The button, to press by hand:")
        click.echo(f"  {merge}")
