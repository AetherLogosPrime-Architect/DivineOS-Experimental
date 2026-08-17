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
import sqlite3
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

# Every one of these means "could not check", never "checked and found none" --
# which is exactly the distinction Status carries three values for. A bare
# `except Exception` here would also swallow a real bug in the ledger or audit
# store and report it as an unreadable source, turning a defect into a shrug.
_BF_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


def _gh(args: list[str]) -> str | None:
    """Run gh; None means could-not-reach, which is NOT the same as empty.

    ``encoding``/``errors`` are pinned because ``text=True`` alone decodes
    with the platform default — cp1252 on this box. Any gh response carrying
    a byte outside cp1252 (a patch hunk with an em-dash, a curly quote, a
    name with an accent) raised UnicodeDecodeError inside subprocess's reader
    THREAD, which does not propagate: stdout came back empty, the exit code
    was still 0, and this function returned "" — the one value its own
    docstring promises to distinguish from None.

    Found 2026-08-17 chasing why station 2 read 0 lenses for PR #412. The
    changed-file fetch was returning an empty string because the diff
    contained a smart quote, so the PR appeared to change no files. Every
    caller of this function had the same exposure; this is not a file-list
    bug, it is a decode bug that happened to surface there first. Same shape
    as the read-gate hook that died on an inlined em-dash under cp1252 and
    exited 0, which is to say: fail-quiet on an encoding boundary.
    """
    try:
        p = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
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


"""``gh pr view --json files`` returns at most this many entries, with no
warning and no pagination. A result of exactly this length cannot be
distinguished from a truncated one."""
_GH_PR_FILES_CAP = 100


def _paginated_filenames(raw: str) -> tuple[str, ...]:
    """Filenames from ``gh api --paginate`` output.

    ``--paginate`` concatenates one JSON array per page with nothing between
    them — ``[{...}][{...}]`` — which is not a JSON document, so a plain
    ``json.loads`` raises on any PR past the first page. Decoding
    incrementally reads each array in turn and stops cleanly at the end.
    """
    dec = json.JSONDecoder()
    names: list[str] = []
    i, n = 0, len(raw)
    while i < n:
        while i < n and raw[i].isspace():
            i += 1
        if i >= n:
            break
        page, i = dec.raw_decode(raw, i)
        for entry in page if isinstance(page, list) else []:
            if isinstance(entry, dict):
                names.append(str(entry.get("filename") or ""))
    return tuple(names)


def _changed_paths(pr: int) -> tuple[str, ...] | None:
    """Every path this PR changes, or None when the set cannot be trusted.

    ``gh pr view --json files`` SILENTLY CAPS AT 100 FILES. It does not
    paginate, does not warn, and returns a well-formed list that looks
    complete. Found 2026-08-17 on PR #412, which changes 443 files: the
    truncated list stopped inside ``docs/audit_rounds/`` and never reached
    ``src/``, so the module the PR is actually about was absent from its own
    changed-file set. Station 2 keyed its lens lookup off that set and
    reported ``0/2 lenses walked`` while two matching walks sat in the ledger
    with the correct fingerprint.

    That is the same false ACCUSATION this function's caller was repaired for
    on 2026-08-07, one layer up: the data was present and the query could not
    reach it. A station that can only fail teaches me to discount it, and a
    discounted gate is a dead gate. The earlier fix corrected the key; this
    one corrects the corpus the key is looked up in.

    ``gh api --paginate`` walks the Link headers and returns the whole set.
    The 100-length check afterwards is the belt: if pagination is ever
    unavailable or silently capped again, an exactly-100 result is
    indistinguishable from a truncation, so it is reported as
    CANNOT_CHECK rather than as a confident set. A PR with exactly 100 files
    loses nothing real -- it is downgraded from a possibly-wrong answer to an
    honestly-unknown one, which is the direction this house errs in.
    """
    repo = _gh(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])
    if repo:
        # No ``-q``: gh's jq filter yields NOTHING under ``--paginate`` off a
        # tty, and does it with exit code 0 — an empty success, which would
        # read here as "this PR changes no files". Parsing the JSON ourselves
        # keeps the failure mode an exception instead of a plausible zero.
        out = _gh(["api", f"repos/{repo.strip()}/pulls/{pr}/files", "--paginate"])
        if out is not None:
            paths = tuple(f for f in _paginated_filenames(out) if f)
            if paths:
                return paths

    # Fall back to the capped view, but refuse to present a truncated set as
    # a complete one.
    out = _gh(["pr", "view", str(pr), "--json", "files"])
    if out is None:
        return None
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None
    paths = tuple(f.get("path", "") for f in (data.get("files") or []))
    if len(paths) >= _GH_PR_FILES_CAP:
        return None  # may be truncated; unknown is not zero
    return paths


def _lenses_applied(paths: tuple[str, ...] | None) -> int | None:
    """Council lenses recorded against the FILES this PR changes.

    Returns 0, not None, when the ledger is readable and holds nothing --
    the difference matters and is the whole reason Status has three values.

    2026-08-07, found by dogfooding this command rather than reading it.
    The previous version searched the walk events for the BRANCH NAME. A
    council walk records an edit fingerprint -- `edit:<path>` -- and never
    a branch. Measured: 279 COUNCIL_LENS_APPLIED events in the ledger,
    zero containing any branch name. So station 2 reported `0/N lenses
    walked` for every PR, always, and could never have reported anything
    else.

    That is a false ACCUSATION rather than a false pass, and it is the
    worse direction for this house: a station that can only fail teaches
    me to discount it, and a discounted gate is a dead gate. The data was
    present and the query could not reach it -- a third state the module's
    own three-value docstring does not cover, because the ledger was
    readable AND non-empty AND still yielded nothing.

    Correct key is the changed-file set, which `collect()` already fetches
    for gravity scoring. `paths=None` means gh could not tell us what
    changed, which is genuinely CANNOT_CHECK and must not read as zero.
    """
    if paths is None:
        return None
    try:
        from divineos.core.ledger import get_events
    except _BF_ERRORS:
        return None
    try:
        rows = get_events(event_type="COUNCIL_LENS_APPLIED", limit=500, order="desc")
    except _BF_ERRORS:
        return None
    wanted = {p.replace("\\", "/") for p in paths if p}
    if not wanted:
        return 0

    # Count DISTINCT LENSES, not walk events -- the requirement is phrased
    # "needs 6 lenses" and counting events answers a different question.
    #
    # Measured before choosing: counting events gave #409 sixty-eight, of
    # which thirty-one came from a single file (.claude/settings.json)
    # that nearly every PR touches. A PR inherited a passing score for
    # brushing a high-traffic file. Distinct-lens counting collapses those
    # thirty-one to one, because they are one expert applied repeatedly to
    # a shared file, not six perspectives on this work.
    seen: set[str] = set()
    for row in rows:
        payload = row.get("payload") or {}
        fingerprint = str(payload.get("edit_fingerprint") or "")
        if not fingerprint.startswith("edit:"):
            continue
        target = fingerprint[len("edit:") :].replace("\\", "/")
        # Walks may record an absolute path; a changed-file path is
        # repo-relative. Match on suffix so both spellings land.
        if any(target.endswith(p) or p.endswith(target) for p in wanted):
            seen.add(str(payload.get("expert_name") or "").strip().lower())
    seen.discard("")
    return len(seen)


def _audit_refs() -> tuple[str, ...] | None:
    out = _gh(["pr", "list", "--state", "open", "--limit", "1"])
    if out is None:
        return None  # no network -> cannot check, do not claim absent
    try:
        from divineos.core.watchmen.store import list_rounds  # type: ignore[attr-defined]
    except _BF_ERRORS:
        return None
    try:
        return tuple(str(r) for r in list_rounds())
    except _BF_ERRORS:
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
                check_audit_station(n, branch, audit),
            ]
            out.append(st)
            continue
        gravity, _fired = score_pr_gravity(paths)
        need = required_lens_count(gravity, len(paths))
        st = PrFlowStatus(number=n, branch=branch, gravity=gravity, required_lenses=need)
        st.stations = [
            # paths, not branch: council walks are keyed by edit
            # fingerprint. See _lenses_applied for the measurement.
            check_council_station(branch, need, _lenses_applied(paths)),
            check_aria_station(branch, _LETTERS),
            check_draft_station(pr.get("isDraft")),
            check_audit_station(n, branch, audit),
        ]
        out.append(st)
    return out, ""


_MARK = {Status.SATISFIED: "ok  ", Status.MISSING: "MISS", Status.CANNOT_CHECK: "????"}


def _is_draft(s: PrFlowStatus) -> bool:
    return any(r.station == "7-draft" and r.status is Status.SATISFIED for r in s.stations)


def render(statuses: list[PrFlowStatus]) -> str:
    """Report in-flight state in in-flight grammar.

    Andrew 2026-08-05: *"13 PRs arent sitting there.. 13 DRAFTS are lol that
    is why its perfectly fine.. theres no red marks they can be edited and
    repushed after the proper build flow"*

    This line used to read "0/15 PRs have every CHECKED station proven",
    which is failure grammar for the healthy case. I read it and wrote
    "stalled" and "parked" about fifteen drafts doing exactly what drafts do.
    A draft with stations pending is the flow WORKING -- pending is what
    draft means. The case that warrants alarm is a PR marked
    ready-for-review whose stations are not proven, and check_draft_station
    already separates the two; only this summary threw the distinction away.
    """
    lines = ["", "=== BUILD-FLOW STATUS — open PRs ===", ""]
    ready = 0
    in_flight = 0
    attention: list[int] = []
    for s in sorted(statuses, key=lambda x: x.number):
        if s.mergeable:
            flag = "READY — every checked station proven"
            ready += 1
        elif _is_draft(s):
            flag = f"in flight — {len(s.blocking)} station(s) still ahead of it"
            in_flight += 1
        else:
            flag = f"ATTENTION — marked ready for review, {len(s.blocking)} station(s) unproven"
            attention.append(s.number)
        lines.append(f"  #{s.number}  {s.branch}")
        lines.append(f"      gravity {s.gravity}, needs {s.required_lenses} lenses — {flag}")
        for r in sorted(s.stations, key=lambda r: r.station):
            lines.append(f"      [{_MARK[r.status]}] {r.station:<12} {r.detail}")
        lines.append("")
    lines.append(
        f"  {ready} ready, {in_flight} in flight, {len(attention)} needing attention"
        f" (of {len(statuses)})."
    )
    if attention:
        lines.append(f"  Needing attention: {', '.join(f'#{n}' for n in attention)}")
    else:
        lines.append("  Nothing is off-track. Drafts with stations ahead of them are drafts.")
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
