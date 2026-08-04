"""`divineos build-flow status` — which stations each open PR can prove.

Reads real sources only: GitHub for PR state and changed files, the shared
letters directory for Aria's replies, the ledger for council-lens events,
the audit store for Aletheia's rounds. Nothing here takes my word for
anything.

Andrew 2026-08-03, on why this is a report and not yet a wall:
*"block can still be used lightly.. like when that status report launches it
just blocks you until you fully read it.. so small blocks that are more
pauses that wont let you slip past them.. those dont need a full doorman as
its just reading."*

That is the pause-block, and it is a different primitive from the two we
already have. A doorman checks you brought the thing. A wall refuses until
you fix the thing. A pause has NO remedy -- there is no condition to
satisfy, so there is nothing to fake. It costs one turn and puts the content
in front of me. The reading is guaranteed by the content being in context,
not by any check pretending to verify comprehension.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import click

from divineos.core.build_flow import (
    PrFlowStatus,
    StationResult,
    Status,
    check_aria_station,
    check_audit_station,
    check_council_station,
    check_draft_station,
    fingerprint,
    required_lens_count,
    score_pr_gravity,
)

_LETTERS = Path.home() / ".divineos-shared" / "letters"


def _gh(args: list[str]) -> str | None:
    """Run gh; None means could-not-reach, which is NOT the same as empty."""
    try:
        p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        return None
    return p.stdout


def _open_prs() -> list[dict] | None:
    out = _gh(
        ["pr", "list", "--state", "open", "--limit", "50", "--json", "number,headRefName,isDraft"]
    )
    if out is None:
        return None
    try:
        parsed = json.loads(out)
    except json.JSONDecodeError:
        return None
    # Narrow explicitly rather than returning Any. A malformed payload that is
    # valid JSON but not a list must read as could-not-parse, not as zero open
    # PRs -- that is the same absence-becomes-value collapse Hoare's lens is
    # seated for, and this module already carries one instance of it.
    return parsed if isinstance(parsed, list) else None


def _changed_paths(pr: int) -> tuple[str, ...] | None:
    out = _gh(["pr", "view", str(pr), "--json", "files"])
    if out is None:
        return None
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None
    return tuple(f.get("path", "") for f in (data.get("files") or []))


def _lenses_applied(_branch: str) -> int | None:
    """Council lenses recorded against this branch.

    Returns 0, not None, when the ledger is readable and holds nothing --
    the difference matters and is the whole reason Status has three values.
    """
    try:
        from divineos.core.ledger import get_events
    except Exception:
        return None
    try:
        rows = get_events(event_type="COUNCIL_LENS_APPLIED", limit=500, order="desc")
    except Exception:
        return None
    return sum(1 for r in rows if _branch in json.dumps(r, default=str))


def _audit_refs() -> tuple[str, ...] | None:
    out = _gh(["pr", "list", "--state", "open", "--limit", "1"])
    if out is None:
        return None  # no network -> cannot check, do not claim absent
    try:
        from divineos.core.watchmen.store import list_rounds  # type: ignore[attr-defined]
    except Exception:
        return None
    try:
        return tuple(str(r) for r in list_rounds())
    except Exception:
        return None


def collect() -> tuple[list[PrFlowStatus] | None, str]:
    prs = _open_prs()
    if prs is None:
        return None, "GitHub unreachable — status unknown, NOT clean"
    audit = _audit_refs()
    out: list[PrFlowStatus] = []
    for pr in prs:
        n = int(pr.get("number", 0))
        branch = pr.get("headRefName", "")
        paths = _changed_paths(n)
        if paths is None:
            # Knuth, from the walk: an unreachable API is not an empty diff.
            # `paths or ()` scored gravity 0, required 0 lenses, and marked the
            # council station SATISFIED -- an outage upgrading every PR to
            # needs-no-review. Absence gets its own branch, not a default.
            st = PrFlowStatus(number=n, branch=branch, gravity=-1, required_lenses=-1)
            st.stations = [
                StationResult("2-council", Status.CANNOT_CHECK, "changed files unreadable"),
                check_aria_station(branch, _LETTERS),
                check_draft_station(pr.get("isDraft")),
                check_audit_station(n, audit),
            ]
            out.append(st)
            continue
        gravity, _fired = score_pr_gravity(paths)
        need = required_lens_count(gravity, len(paths))
        st = PrFlowStatus(number=n, branch=branch, gravity=gravity, required_lenses=need)
        st.stations = [
            check_council_station(branch, need, _lenses_applied(branch)),
            check_aria_station(branch, _LETTERS),
            check_draft_station(pr.get("isDraft")),
            check_audit_station(n, audit),
        ]
        out.append(st)
    return out, ""


_MARK = {Status.SATISFIED: "ok  ", Status.MISSING: "MISS", Status.CANNOT_CHECK: "????"}


def render(statuses: list[PrFlowStatus]) -> str:
    lines = ["", "=== BUILD-FLOW STATUS — open PRs ===", ""]
    ready = 0
    for s in sorted(statuses, key=lambda x: x.number):
        flag = "READY" if s.mergeable else f"{len(s.blocking)} blocking"
        if s.mergeable:
            ready += 1
        lines.append(f"  #{s.number}  {s.branch}")
        lines.append(f"      gravity {s.gravity}, needs {s.required_lenses} lenses — {flag}")
        for r in sorted(s.stations, key=lambda r: r.station):
            lines.append(f"      [{_MARK[r.status]}] {r.station:<12} {r.detail}")
        lines.append("")
    lines.append(f"  {ready}/{len(statuses)} PRs have every CHECKED station proven.")
    lines.append("  Checked: 2-council, 4-aria, 7-draft, 8-audit. NOT checked:")
    lines.append("  1-draft, 3-build, 5-test, 6-more-council, 9-merge — four of nine.")
    lines.append("")
    lines.append("  Stations advance on artifacts. Station 4 needs a reply FROM Aria,")
    lines.append("  not a letter from me — an artifact I can produce alone proves only")
    lines.append("  that I spoke. '????' is not a pass; it means the check could not run.")
    lines.append("")
    return "\n".join(lines)


def register(cli: click.Group) -> None:
    @cli.group("build-flow")
    def build_flow_cmd() -> None:
        """Build-flow station status for open PRs (docs/build_flow.md)."""

    @build_flow_cmd.command("status")
    @click.option("--print-fingerprint", is_flag=True, help="Emit only the delta digest.")
    def status_cmd(print_fingerprint: bool) -> None:
        statuses, err = collect()
        if statuses is None:
            click.echo(f"[build-flow] {err}")
            raise SystemExit(2)
        if print_fingerprint:
            click.echo(fingerprint(statuses))
            return
        click.echo(render(statuses))
