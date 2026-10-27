"""`divineos landing` -- where each waiting fix stands toward the auditor.

Dad, 2026-10-10: the pile is fixes that never land. The auditor is on another
platform and her letters are carried by hand, so the state of a fix is worked
out from the letters that exist and the live heads, never from memory. See
docs/drafts/the_landing_line_draft_2026-10-10.md and core/landing_status.py.

Read-only. It sends nothing and merges nothing; ``--request`` only prints the
confirm-only letter for me to read and send.
"""

from __future__ import annotations

import json
import subprocess

import click

from divineos.core.landing_homework import (
    ClerkRefused,
    confirm_steps,
    explain_station,
    her_confirm_filed_at,
    her_confirmed_sha,
    his_words_were_typed,
    parse_patch_id_output,
    parse_round_id,
    render_header,
    round_step,
)
from divineos.core.watchmen.store import get_round, list_findings
from divineos.core.landing_status import (
    CHANGED,
    CONFIRMED,
    NEVER_TOLD,
    NO_ANSWER,
    READY,
    UNKNOWN,
    classify_pile,
    letters_read_line,
    open_prs,
    read_letters,
    render_request,
    today,
)

_ORDER = (READY, CONFIRMED, CHANGED, NO_ANSWER, NEVER_TOLD, UNKNOWN)
_NEEDS_HER = (NEVER_TOLD, NO_ANSWER, CHANGED)
# Not stations a person clears: the draft flag is the state being left, and the
# merge station only restates whatever else is held.
_NOT_HELD = ("7-draft", "9-merge")


def _held_by_pr() -> dict[int, tuple[str, ...]] | None:
    from divineos.cli.build_flow_commands import collect
    from divineos.core.build_flow import Status as FlowStatus

    statuses, _why, _roster = collect()
    if statuses is None:
        return None
    return {
        s.number: tuple(
            r.station
            for r in s.stations
            if r.status is not FlowStatus.SATISFIED and r.station not in _NOT_HELD
        )
        for s in statuses
    }


def _held_stations(pr: int) -> list[tuple[str, str]] | None:
    """(station, detail) for every unproven station of one request, or None."""
    from divineos.cli.build_flow_commands import collect
    from divineos.core.build_flow import Status as FlowStatus

    statuses, _why, _roster = collect()
    if statuses is None:
        return None
    mine = next((s for s in statuses if s.number == pr), None)
    if mine is None:
        return None
    return [(r.station, r.detail) for r in mine.stations if r.status is not FlowStatus.SATISFIED]


def _pr_facts(pr: int) -> dict:
    """branch, live head and title of one open request, or a plain refusal."""
    try:
        run = subprocess.run(
            ["gh", "pr", "view", str(pr), "--json", "headRefName,headRefOid,title,commits"],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        parsed = json.loads(run.stdout)
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError) as exc:
        raise ClerkRefused(f"could not read request #{pr} from GitHub: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ClerkRefused(f"request #{pr} came back from GitHub in a shape I cannot read")
    return parsed


def _changed_files(branch: str) -> list[str]:
    run = subprocess.run(
        ["git", "diff", "--name-only", f"origin/main...origin/{branch}"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if run.returncode != 0:
        raise ClerkRefused(f"could not list the changed files of {branch}: {run.stderr.strip()}")
    return [line.strip() for line in run.stdout.splitlines() if line.strip()]


def _run_audit(argv: list[str]) -> str:
    """Run one existing audit command and return what it printed.

    The clerk shells out to the audit commands that already hold the rules
    (walk-4fbd1daa1539, Carmack): no second implementation of the round or the
    confirm ladder. A non-zero exit is a refusal, shown as the command said it.
    """
    run = subprocess.run(argv, capture_output=True, text=True, timeout=300, check=False)
    out = (run.stdout or "") + (run.stderr or "")
    if run.returncode != 0:
        raise ClerkRefused(f"{' '.join(argv[:3])} refused: {out.strip()[:400]}")
    return out


def register(cli: click.Group) -> None:
    @cli.group("landing", invoke_without_command=True)
    @click.option(
        "--request",
        "show_request",
        is_flag=True,
        help="Print the confirm-only letter for the fixes that need her. Sends nothing.",
    )
    @click.pass_context
    def landing_cmd(ctx: click.Context, show_request: bool) -> None:
        """One line per waiting fix: where it stands toward the auditor."""
        if ctx.invoked_subcommand is not None:
            return
        prs = open_prs()
        if prs is None:
            click.secho(
                "[!] COULD NOT READ the open PR list. That is not 'nothing waiting'.", fg="red"
            )
            raise SystemExit(2)

        held = _held_by_pr()
        # A board that could not be read holds everything (classify_pile): could
        # not look is not a pass, so READY is impossible without it.
        letters = read_letters()
        rows = classify_pile(prs, letters, today(), held)

        counts = {label: sum(1 for _, s in rows if s.label == label) for label in _ORDER}
        click.secho(
            "  ".join(f"{label} {counts[label]}" for label in _ORDER if counts[label]),
            bold=True,
        )
        # Says what it looked at, so a count of none is "looked and found none" and a blind board
        # cannot pass for a clean one (walk-29a4e57b49ce, Angelou).
        click.secho(letters_read_line(letters), dim=True)
        for label in _ORDER:
            group = [(pr, s) for pr, s in rows if s.label == label]
            if not group:
                continue
            # The next step is the same for the whole group, so it is said once.
            click.secho(f"\n{label} -> {group[0][1].next_step}", bold=True)
            for pr, status in group:
                click.echo(
                    f"  #{pr['number']:<4} {str(pr.get('headRefName'))[:38]:<38} {status.detail}"
                )
        if held is None:
            click.secho(
                "[!] The readiness board could not be read, so nothing can show READY.",
                fg="yellow",
            )

        if show_request:
            waiting = [
                (int(pr["number"]), str(pr.get("title") or ""), str(pr.get("headRefOid") or ""))
                for pr, status in rows
                if status.label in _NEEDS_HER and pr.get("headRefOid")
            ]
            from divineos.core.sibling_audit_rounds import this_seat

            # A letter to her signed by the wrong seat is worse than no letter (she answers
            # whoever signs), so an unknown seat refuses rather than defaulting to Aether.
            seat = this_seat()
            if waiting and seat is None:
                click.secho(
                    "[!] Cannot sign the request: this checkout's data home matches no known "
                    "seat (set DIVINEOS_HOME to your seat's home). Nothing printed.",
                    fg="red",
                )
                raise SystemExit(2)
            text = render_request(waiting, signed_by=(seat or "").title())
            click.echo("")
            click.echo(text or "(nothing needs her confirm right now)")

    @landing_cmd.command("homework")
    @click.argument("pr", type=int)
    def homework_cmd(pr: int) -> None:
        """What each unproven station of one fix needs, in plain words. Read-only."""
        try:
            facts = _pr_facts(pr)
            branch, head = str(facts["headRefName"]), str(facts["headRefOid"])
            files = _changed_files(branch)
            held = _held_stations(pr)
        except ClerkRefused as exc:
            raise SystemExit(f"[landing] REFUSED: {exc}") from exc
        her = her_confirmed_sha(read_letters(), pr, head) is not None
        click.echo(render_header(pr))
        if held is None:
            click.secho(
                "[!] The readiness board could not be read, so the missing stations are "
                "unknown. That is not 'nothing missing'.",
                fg="yellow",
            )
            return
        if not held:
            click.echo("The board holds nothing for this fix.")
        for station, detail in held:
            click.echo("")
            for line in explain_station(station, detail, pr, files, her):
                click.echo(f"  {line}")

    @landing_cmd.command("file-confirm")
    @click.argument("pr", type=int)
    @click.option(
        "--round",
        "round_id",
        default=None,
        help="Second step: the round filed by the first step. Files his confirm into it.",
    )
    @click.option(
        "--andrew-said",
        default=None,
        help="His own words, quoted, typed AFTER her confirm was recorded. Needs --round.",
    )
    def file_confirm_cmd(pr: int, round_id: str | None, andrew_said: str | None) -> None:
        """Two steps for ONE fix whose live head she confirmed: file hers, then his.

        His yes counts only if typed after the audit store recorded her confirm, a time
        the filer cannot set. So the first call files the round and her confirm and stops;
        the second, with --round and his fresh words, files his.
        """
        try:
            facts = _pr_facts(pr)
            branch, head = str(facts["headRefName"]), str(facts["headRefOid"])
            title = str(facts.get("title") or "")
            if round_id is None and andrew_said is not None:
                raise ClerkRefused(
                    "his words wait for the second step: file her confirm first, then give "
                    "--round with his words typed after it was recorded."
                )
            if round_id is not None and not andrew_said:
                raise ClerkRefused("the second step needs his words: --andrew-said.")
            her_short = her_confirmed_sha(read_letters(), pr, head)
            if her_short is None:
                raise ClerkRefused(
                    f"no letter of hers names the live head of #{pr} ({head[:9]}). "
                    "Nothing is filed on a remembered yes."
                )
            tip, tree, patch = parse_patch_id_output(
                _run_audit(["divineos", "audit", "patch-id", "--branch", branch])
            )
            if tip != head:
                raise ClerkRefused(f"the branch tip {tip[:9]} is not the live head {head[:9]}")
            if round_id is None:
                made = _run_audit(
                    round_step(
                        pr=pr,
                        title=title,
                        branch=branch,
                        tree=tree,
                        patch_id=patch,
                        her_short=her_short,
                    )
                )
                new_round = parse_round_id(made)
                her_steps = confirm_steps(
                    pr=pr,
                    title=title,
                    branch=branch,
                    tip=tip,
                    tree=tree,
                    patch_id=patch,
                    her_short=her_short,
                    andrew_said=None,
                    round_id=new_round,
                )
                her_out = _run_audit(her_steps["external"])
                click.echo(render_header(pr))
                click.echo(f"round: {new_round}")
                click.echo(her_out.strip())
                click.echo(
                    "Her confirm is on the record. Now ask him for a fresh word, typed after this "
                    f"moment, then: divineos landing file-confirm {pr} --round {new_round} "
                    '--andrew-said "<his words>"'
                )
                return
            audit_round = get_round(round_id)
            if audit_round is None:
                raise ClerkRefused(f"no round {round_id} in the audit store")
            her_time = her_confirm_filed_at(
                audit_round.notes, list_findings(round_id=round_id, limit=500), tree
            )
            if her_time is None:
                raise ClerkRefused(
                    f"round {round_id} holds no confirm of hers for this head's tree, or its "
                    "filing time cannot be read. Nothing is filed on a yes I cannot place in time."
                )
            typed = his_words_were_typed(str(andrew_said), after=her_time)
            if typed is None:
                raise ClerkRefused(
                    "could not read the file of what he has typed, so these words cannot be "
                    "checked. That is not a pass: nothing is filed on words I cannot find."
                )
            if not typed:
                raise ClerkRefused(
                    "these words are not found in anything he typed AFTER her confirm was "
                    "recorded. Text he pasted does not count as typed, so a line of a letter "
                    "he forwarded is not his yes. His confirm says her audit was done, so it "
                    "comes after it: ask him for a fresh word, not a sentence made to sound "
                    "like him and not a yes from before."
                )
            his_steps = confirm_steps(
                pr=pr,
                title=title,
                branch=branch,
                tip=tip,
                tree=tree,
                patch_id=patch,
                her_short=her_short,
                andrew_said=str(andrew_said),
                round_id=round_id,
            )
            his_out = _run_audit(his_steps["user"])
        except ClerkRefused as exc:
            raise SystemExit(f"[landing] REFUSED: {exc}") from exc
        click.echo(render_header(pr))
        click.echo(f"round: {round_id}")
        click.echo(his_out.strip())
        click.echo(
            f"Next, in your own hands: divineos stamp-ready {pr} --audit-round {round_id} --dry-run"
        )
