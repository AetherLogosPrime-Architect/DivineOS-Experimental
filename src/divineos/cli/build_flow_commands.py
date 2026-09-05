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


def _declared_file_count(pr: int) -> int | None:
    """gh's own count of files in the PR, or None when it cannot be read.

    The independent number the paginated walk is checked against. Kept as a
    SEPARATE request on purpose: a count taken from the same response being
    validated would agree with itself no matter how truncated it was.
    """
    out = _gh(["pr", "view", str(pr), "--json", "changedFiles"])
    if out is None:
        return None
    try:
        n = json.loads(out).get("changedFiles")
    except (json.JSONDecodeError, AttributeError):
        return None
    return n if isinstance(n, int) else None


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
                # COMPLETENESS CHECK, added during the 2026-08-17 GitHub
                # incident (~20% API error rate, per their status page).
                # Pagination walks several requests; any one failing mid-walk
                # yields a SHORT list rather than an error. A short list is not
                # a smaller answer, it is a wrong one -- and gravity is scored
                # off this set, so a partial fetch LOWERS the lens requirement
                # on the very PR whose data could not be read. The failure runs
                # in the under-demanding direction and is invisible.
                #
                # gh reports the true total separately, so compare against it.
                # Disagreement means the walk did not finish: cannot-check,
                # not a smaller PR.
                declared = _declared_file_count(pr)
                if declared is not None and len(paths) != declared:
                    return None
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


_ROUND_SCAN_LIMIT = 100_000
"""Ceiling for the station-eight round scan.

Deliberately far above any plausible round count rather than unbounded. If a
store ever exceeds it the truncation is at least reported by the scope line,
which names how many rounds were compared against -- a visible narrowing
instead of the silent one this replaces."""


def _other_seat_lenses(paths: tuple[str, ...] | None) -> dict[str, int]:
    """Distinct lenses the OTHER seat walked against these files.

    Seen, never counted -- Aria's 2026-08-29 design. A walk of hers this board
    cannot see is reported to me as "not walked", which is
    could-not-look-reading-as-not-done inside the lane that decides whether I
    thought a change through. Measured when the split was found: 290 walk
    events on this seat, 103 on hers, all 103 invisible here.

    An absent or unreadable seat yields an empty mapping, and that is the one
    place this deliberately differs from station eight. There, an unreadable
    seat forces CANNOT_CHECK, because a round I cannot see might be an audit
    that happened. Here, a walk of hers cannot change my verdict either way --
    hers never satisfy -- so an unreadable sibling costs a line of information
    rather than producing a wrong answer.
    """
    if not paths:
        return {}
    try:
        from divineos.core.sibling_audit_rounds import this_seat
        from divineos.core.sibling_council_walks import lenses_for_paths, read_other_seats_walks
    except _BF_ERRORS:
        return {}
    wanted = {p.replace("\\", "/") for p in paths if p}
    out: dict[str, int] = {}
    try:
        for seat in read_other_seats_walks(this_seat()):
            if not seat.readable:
                continue
            found = lenses_for_paths(seat, wanted)
            if found:
                out[seat.name] = len(found)
    except _BF_ERRORS:
        return {}
    return out


def _audit_store_label() -> str | None:
    """The database the rounds were actually read from, or None.

    Resolved from the SAME connection the rounds come through, never guessed
    from configuration. A label naming a store this did not query would be the
    wrong-subject error the label exists to prevent.
    """
    try:
        from divineos.core.knowledge import _get_connection

        rows = list(_get_connection().execute("PRAGMA database_list"))
    except _BF_ERRORS:
        return None
    for row in rows:
        if len(row) >= 3 and str(row[1]) == "main" and row[2]:
            return str(row[2])
    return None


def _audit_refs() -> tuple[tuple[str, ...] | None, str | None]:
    """Rounds visible to THIS seat, and the store they came from.

    Returns the label alongside the refs so station eight can say where it
    looked. Two stores exist in this house and neither seat sees the other's;
    an unqualified "no round found" is a true statement about one of them
    published with the scope of both.
    """
    out = _gh(["pr", "list", "--state", "open", "--limit", "1"])
    if out is None:
        return None, None  # no network -> cannot check, do not claim absent
    try:
        from divineos.core.watchmen.store import list_rounds  # type: ignore[attr-defined]
    except _BF_ERRORS:
        return None, None
    try:
        # THE ROW CAP. `list_rounds` defaults to limit=20 and this called it
        # with no argument, so station eight compared every PR against the
        # twenty most recent rounds out of three hundred and twenty-one.
        # Measured by Aria 2026-08-28 and re-measured here: default call 20,
        # explicit limit 321, table 321. A round older than the twenty newest
        # produced a confident MISS at the last gate before merge.
        #
        # THIRD INSTANCE OF THIS CLASS IN THIS FILE, and the other two are
        # written up in docstrings above: the changed-files list silently
        # capping at a hundred, and before that the lens key being wrong. Her
        # reading, which is right -- the first fix corrected the key, the
        # second corrected the corpus the key is looked up in, and this
        # narrowed that corpus twice more, once by store and once by row.
        #
        # No sentinel and no None: an explicit ceiling far above any real
        # round count, so a future store that outgrows it degrades to the
        # same visible truncation rather than a silent one, and the scope
        # line below reports the number actually compared against.
        rounds = tuple(str(r) for r in list_rounds(limit=_ROUND_SCAN_LIMIT))
    except _BF_ERRORS:
        return None, None

    # THE UNION, per Andrew 2026-08-28: share everything, stay separate. Both
    # seats' rounds are READ; neither store is written by the other.
    #
    # A PARTIAL UNION MUST NOT PASS FOR A WHOLE ONE. If a seat is present and
    # unreadable, this returns None -- CANNOT_CHECK -- rather than a confident
    # verdict over the half it managed to read. That half-answer is precisely
    # the defect being repaired here, and a union that degrades quietly to one
    # store would be the same bug wearing a friendlier name.
    #
    # A seat that is simply not on this machine is different and is NOT a
    # failure: it is a complete answer about an absent seat. Treating those
    # alike would make an ordinary single-seat checkout refuse forever, and a
    # check that always refuses gets switched off.
    parts = [f"{len(rounds)} own"]
    try:
        from divineos.core.sibling_audit_rounds import read_other_seats, this_seat

        for seat in read_other_seats(this_seat()):
            if seat.error is not None:
                return None, f"{seat.name} present but unreadable: {seat.error}"
            if seat.absent:
                parts.append(f"{seat.name} not present here")
                continue
            assert seat.rounds is not None
            rounds = rounds + seat.rounds
            parts.append(f"{len(seat.rounds)} from {seat.name}")
    except _BF_ERRORS as exc:
        return None, f"sibling round reader unavailable: {type(exc).__name__}"

    label = _audit_store_label()
    where = f"{'; '.join(parts)}; own store {label}" if label else "; ".join(parts)
    return rounds, where


def _anchor_for(branch: str, deep: bool, pr_number: int = 0) -> str:
    """Whether the round covering ``branch`` still covers it by CONTENT.

    Returns the state string station eight understands, or "not-run" when the
    caller declined to pay for it.

    THE COST IS WHY THIS IS OPTIONAL, and it was measured rather than
    guessed: one check runs about five seconds, because it fetches and
    recomputes the diff against the base. Across the open requests that is
    over half a minute on every turn, which is the toll-booth failure that
    already has its own repair in flight. A board nobody waits for is a board
    nobody reads.

    So the per-turn view passes deep=False and SAYS the check did not run;
    the explicit command pays. The one thing not on offer is a green station
    that silently means less than the reader thinks -- that is the defect
    this whole change removes, and reproducing it to save five seconds would
    undo the point.
    """
    if not deep or not branch:
        return "not-run"
    try:
        from divineos.cli.audit_commands import anchor_state_for_round
        from divineos.core.watchmen.store import list_rounds
    except _BF_ERRORS:
        return "cannot-check"
    try:
        # MATCH THE SAME WAY THE STATION DOES, or this answers about a
        # different corpus than the verdict it feeds -- which is the exact
        # fault being repaired, reproduced one function down.
        #
        # Caught by running it rather than by reading it: the first version
        # matched on branch only, while the station matches PR-number OR
        # branch. Two requests whose rounds name the number and not the
        # branch came back "content check not run" WITH the deep flag on, so
        # the board reported a check it had been asked for and had silently
        # skipped.
        tail = branch.rsplit("/", 1)[-1]
        pr_token = f"#{pr_number}" if pr_number else ""

        def _names_it(rnd: object) -> bool:
            # str(rnd), NOT rnd.focus. The station matches against the round's
            # whole rendered text and matching its focus field alone is a
            # NARROWER corpus -- which is how the second version of this
            # still reported "not run" for two requests whose rounds the
            # station had already matched. Third time in one function that
            # the answer came from a different corpus than the question;
            # the cure each time was to use the identical predicate rather
            # than a reasonable-looking equivalent.
            text = str(rnd)
            if pr_token and pr_token in text:
                return True
            return bool(branch and (branch in text or (tail and tail in text)))

        matches = [r for r in list_rounds(limit=_ROUND_SCAN_LIMIT) if _names_it(r)]
    except _BF_ERRORS:
        return "cannot-check"
    if not matches:
        # THE OTHER SEAT'S STORE. The station matches against the UNION of
        # both seats' rounds; this function can only read mine, and
        # `anchor_state_for_round` reads my findings. So a request whose
        # round lives in Aria's store matches at the station and is
        # unreachable here.
        #
        # That is CANNOT-CHECK, not not-run: I looked and could not answer.
        # Reporting it as skipped would say I declined to check something I
        # actually failed to reach, which is the could-not-look-as-all-clear
        # shape wearing a politer word. This return is only ever surfaced
        # when the station DID match by name -- a request with no round at
        # all takes the MISSING branch and never consults this.
        return "cannot-check"

    # ASK EVERY ROUND, NEWEST FIRST, AND LET A HOLDING ONE WIN. A branch
    # re-audited after moving has two rounds naming it: an old one that has
    # gone stale and a fresh one that holds. The question this station asks
    # is whether a current valid review EXISTS, so one holding round answers
    # it regardless of what sits behind it.
    #
    # My first version took only the newest naming round, which flipped a
    # correct "no longer holds" into "could not determine" the moment a newer
    # round without a confirm appeared. Taking the newest is not the same as
    # taking the one that answers.
    verdicts = []
    for rnd in matches:
        state, _detail = anchor_state_for_round(getattr(rnd, "round_id", ""), branch)
        if state == "holds":
            return "holds"
        verdicts.append(state)
    if "stale" in verdicts:
        return "stale"
    if "unanchored" in verdicts:
        return "unanchored"
    return "cannot-check"


def collect(deep: bool = False) -> tuple[list[PrFlowStatus] | None, str]:
    prs = _open_prs()
    if prs is None:
        return None, "GitHub unreachable — status unknown, NOT clean"
    audit, audit_store = _audit_refs()
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
                check_audit_station(n, branch, audit, audit_store, _anchor_for(branch, deep, n)),
            ]
            out.append(st)
            continue
        gravity, _fired = score_pr_gravity(paths)
        # Paths, not a count: the requirement scales on files a lens can grip,
        # and the count discards exactly the information that decides it. The
        # unreachable-diff branch above already refuses to let absence read as
        # an empty diff; this is the same discipline one step in -- do not hand
        # a decision a summary when the thing itself is in hand.
        need = required_lens_count(gravity, paths)
        st = PrFlowStatus(number=n, branch=branch, gravity=gravity, required_lenses=need)
        st.stations = [
            # paths, not branch: council walks are keyed by edit
            # fingerprint. See _lenses_applied for the measurement.
            check_council_station(branch, need, _lenses_applied(paths), _other_seat_lenses(paths)),
            check_aria_station(branch, _LETTERS),
            check_draft_station(pr.get("isDraft")),
            check_audit_station(n, branch, audit, audit_store, _anchor_for(branch, deep, n)),
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
    @click.option(
        "--deep",
        is_flag=True,
        help=(
            "Also check whether each audit round still COVERS its branch by "
            "content, not just names it. Costs about five seconds per open "
            "request; the per-turn board skips it and says so."
        ),
    )
    def status_cmd(print_fingerprint: bool, deep: bool) -> None:
        statuses, err = collect(deep=deep)
        if statuses is None:
            click.echo(f"[build-flow] {err}")
            raise SystemExit(2)
        if print_fingerprint:
            click.echo(fingerprint(statuses))
            return
        click.echo(render(statuses))
