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


# Titles that announce the finding is NOT a signature. This house writes them
# in a fixed form, and the form is the only reliable place to read a verdict --
# the body of a withheld clearance says the word "confirming" more often than a
# real confirm does, because refusing takes more words than agreeing.
_WITHHELD_TITLE = re.compile(
    r"^\s*(?:SHAPE-CLEARED|NOT[-\s]CONFIRM|NOT[-\s]A[-\s]CONFIRM|DECLINE|REFUS|WITHHELD)",
    re.IGNORECASE,
)


def _title_withholds(finding: object) -> bool:
    """Does this finding's TITLE say it is not a signature?

    FOUND BY ALETHEIA'S OFFERED TEST, 2026-09-03, in shipped code. She wrote a
    triage clearance whose body reads *"I am not confirming the thirteen in
    bucket one as READ"* and insisted the record carry the distinction:

        "The distinction has to survive in the record, or it stops existing."

    A reporting script of mine searched finding bodies for the word "confirms"
    and printed her name against thirteen branches she had explicitly refused.
    The same substring filter is what selects findings here, so a withheld
    clearance that happened to quote a tree would have supplied that tree as
    though she had signed it.

    THIS IS A NEGATIVE FILTER ON PURPOSE, and the choice is load-bearing. The
    obvious repair -- select only titles that BEGIN with CONFIRMS -- reads
    stricter and is not. Older rounds predate that convention, so it would drop
    genuine confirms, and a round whose confirms all vanish stops refusing and
    starts merely warning. Narrowing a false positive must not widen a real
    one; so this removes what announces itself as withheld and leaves the
    existing net otherwise intact.
    """
    title = str(getattr(finding, "title", "") or "")
    return bool(_WITHHELD_TITLE.search(title))


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
        if _title_withholds(f):
            continue
        text = f"{getattr(f, 'title', '') or ''} {getattr(f, 'description', '') or ''}"
        if "confirms" not in text.lower():
            continue
        trees.update(m.group(1).lower() for m in _TREE_NEAR.finditer(text))
    return trees


# Content identifiers appear as "patch-id 91fc90e6", "patch-id: <40hex>", and
# "pid 46112ab3". Anchored on the word for the same reason the tree pattern is:
# a bare hex scan also matches the tail of a round id.
_PATCH_ID_NEAR = re.compile(
    r"\b(?:patch[-\s]?id|pid)[-\s]*(?:hash|sha)?[:\s]+([0-9a-f]{8,40})\b",
    re.IGNORECASE,
)

# Shortest abbreviation this rung will JUDGE, as opposed to the shortest it
# will read. The pattern above deliberately still admits eight characters:
# raising its lower bound would make a too-short claim vanish, and this rung
# would then report that no identifier was named when one was -- a true
# sentence about the wrong subject, which is the fault this whole branch is
# about.
#
# Aria found the gap 2026-09-05 reading this branch: the sibling rule in the
# validator sets twelve, and nothing between extraction and verdict here
# tested length at all, so an eight-character claim prefix-matched and
# returned HOLDS. The direction is the bad one -- it licenses a stamp rather
# than withholding one.
#
# Her strength-claim, carried because it is the honest one: the mechanism is
# certain from the code, but she found no eight-character identifier in our
# traffic, so this was a loaded condition rather than a live break.
#
# The number is duplicated from the validator ON PURPOSE and only for now.
# The validator's copy lives on a branch that is not yet merged and that is
# itself waiting on this rung to land, so importing it today would bind this
# file to a module version that does not exist on main. When both land they
# become one constant, and that unification is the point at which this
# comment stops being true.
_MIN_CONTENT_PREFIX = 12


def _confirmed_patch_ids(round_id: str) -> set[str]:
    """Content identifiers named by the CONFIRMS findings on this round.

    Same shape and same known limit as ``_confirmed_trees``: read from the
    findings rather than the round notes, matched by prefix in both
    directions because these are quoted abbreviated as often as in full, and
    unable to tell an identifier a finding CONFIRMS from one it merely
    mentions.
    """
    from divineos.core.watchmen.store import list_findings

    ids: set[str] = set()
    try:
        findings = list_findings(round_id=round_id, limit=200) or []
    except Exception:  # noqa: BLE001 - an unreadable store is not "no identifiers"
        return ids
    for f in findings:
        if _title_withholds(f):
            continue
        text = f"{getattr(f, 'title', '') or ''} {getattr(f, 'description', '') or ''}"
        if "confirms" not in text.lower():
            continue
        ids.update(m.group(1).lower() for m in _PATCH_ID_NEAR.finditer(text))
    return ids


def _content_rung(round_id: str, branch: str) -> tuple[bool, str]:
    """Does the reviewed CHANGE still match, when the tree no longer does?

    Andrew 2026-09-05: *"if the code itself is unchanged then her review
    stands, as the floor changes underneath it when its pushed... it only
    needs to be re-audited if the code has changed... otherwise this becomes a
    slog and an endless run-around reviewing the same things over and over."*

    WHY THIS RUNG WAS MISSING, which Aria measured and named.

    The rule already existed -- in the wrong file. The tool that FILES a
    confirm computes content identifiers and has a whole rung for
    catch-up-does-not-invalidate. The tool that SPENDS one, this one, only
    described that rung in a docstring and offered two doors: an exact tree
    match, or a written ancestry claim. Unchanged-content opened neither.

    Her count: content identifiers appear three times in this file, all inside
    prose, against seventy-five times in the validator where they are actually
    computed. A rule reaching one mechanism and not the other, which is the
    same shape as a review living in one store and nowhere else.

    And the tree rung is guaranteed to fail here. Aletheia's own reason,
    quoted in this file above: an anchor bound to the whole tree *"inherits
    the volatility of the least stable thing inside what it measures"* -- so
    every commit anyone lands moves it. Catching a branch up to main is the
    one act required to make it mergeable, and it breaks the only rung that
    was wired. The branch becomes unmergeable by being made mergeable.

    I hit this an hour before writing it and got past it by re-filing the
    confirm through the validator, which computed the rung the stamper lacks.
    Routing through the other tool to obtain a verdict this one could not
    reach IS the finding, and I took it as a workaround at the time.

    Returns ``(holds, why)``. Could-not-compute never returns True: the
    reading that would license the stamp is exactly the one unavailable, and
    it is reported as unknown rather than as a mismatch, because those two
    have different remedies.
    """
    confirmed = _confirmed_patch_ids(round_id)
    if not confirmed:
        return False, "no CONFIRMS finding on this round names a content identifier"

    try:
        from divineos.cli.audit_commands import compute_branch_patch_id
    except Exception as exc:  # noqa: BLE001 - import failure is not a mismatch
        return False, f"could not load the content-identity computation ({exc})"

    current = compute_branch_patch_id(f"origin/{branch}")
    if not current:
        return False, (
            "the branch's content identifier could not be computed, so this "
            "rung cannot answer -- unknown, not unchanged"
        )

    cur = current.lower()

    # A too-short claim is UNANSWERABLE, never proof of either verdict. It
    # must not return holds -- that stamps on a claim nothing verified -- and
    # it must not fall through to the change-moved message, which asserts a
    # cause this rung never tested. It gets its own sentence, the way the
    # sibling rule in the validator does.
    judgeable = {c for c in confirmed if len(c) >= _MIN_CONTENT_PREFIX}
    if not judgeable:
        short = ", ".join(sorted(confirmed))
        return False, (
            f"the round names content identifier(s) {short}, all shorter than "
            f"{_MIN_CONTENT_PREFIX} characters -- too short to tell whether they "
            "name this change. Unanswerable, NOT evidence the change moved: "
            "re-file the CONFIRMS carrying the full identifier."
        )

    for claimed in judgeable:
        if cur.startswith(claimed) or claimed.startswith(cur):
            return True, (
                f"the reviewed change is unchanged (content identifier "
                f"{claimed[:12]} still matches the branch); only the floor moved"
            )
    named = ", ".join(sorted(c[:12] for c in judgeable))
    return False, (
        f"the content identifier moved: round names {named}, branch computes "
        f"{cur[:12]} -- the reviewed change itself differs, not just its floor"
    )


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


# "tip 968d0b930d55", "tip-hash: <sha>", "commit: <sha>". Anchored on the word
# for the same reason _TREE_NEAR is: a bare hex scan also matches the hex tail
# of a round id, and a round id mistaken for a commit is a silent wrong answer.
_TIP_NEAR = re.compile(
    r"\b(?:tip|commit|head)[-\s]*(?:hash|sha|oid)?[:\s]+([0-9a-f]{8,40})\b",
    re.IGNORECASE,
)

# The ancestry rung only opens if a CONFIRMS finding SAYS, in words, that the
# commit its author reviewed is still in this branch's history.
_ANCESTRY_CLAIM = re.compile(r"\bancest(?:or|ry|ral)\b", re.IGNORECASE)


def _pr_head_oid(pr_number: int) -> str:
    """The PR head commit sha, or "" when it could not be read.

    Empty means CANNOT LOOK, never "no head". Every caller here treats it as a
    refusal rather than as an absence, which is the whole lesson of the fault
    class this file keeps turning up: a failed lookup that renders as an
    innocent value is worse than one that raises, because it reports safety.
    """
    try:
        out = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "headRefOid"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        return str(json.loads(out.stdout).get("headRefOid", "") or "")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return ""
    except (json.JSONDecodeError, KeyError, TypeError):
        return ""


def _is_ancestor(tip: str, head_sha: str) -> bool | None:
    """Is ``tip`` an ancestor of ``head_sha``? ``None`` means could not tell.

    Three states, not two, and the third one is the point. ``git merge-base
    --is-ancestor`` exits 1 for "no" and also non-zero when the object is not
    here at all. Collapsing those lets an unfetched commit read as an orphaned
    one -- or, under the opposite sign, lets a lookup failure read as a pass.
    The object is resolved first so the two stay separable.
    """
    if not tip or not head_sha:
        return None
    try:
        subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"{tip}^{{commit}}"],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None  # both-empty: the object is not here, git is not here, or the
        # question timed out -- three ways of not knowing, and the caller's only
        # honest move is identical for all of them, so they are one answer.
    try:
        res = subprocess.run(
            ["git", "merge-base", "--is-ancestor", tip, head_sha],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None  # both-empty: same not-knowing as above, one step later.
    if res.returncode == 0:
        return True
    if res.returncode == 1:
        return False
    return None  # both-empty: git answered with neither yes nor no, which is the
    # same not-knowing the handlers above report; the caller must refuse either way.


def _ancestry_rung(round_id: str, head_sha: str) -> tuple[bool, str]:
    """Does this round carry a written ancestry claim that actually holds?

    Returns ``(holds, why)``, where ``why`` is printable in both directions.

    Aletheia's amended anchor rule, 2026-09-03, written after her first one
    broke within twelve hours -- and broken by the act of USING it, because
    catching a branch up to main rewrites a generated artifact, and any anchor
    bound to the code inherits the volatility of the least stable thing inside
    what it measures::

        TIP unchanged                          -> holds.
        TIP moved, patch-id unchanged          -> holds (catch-up).
        TIP moved, patch-id moved, SIGNED TIP IS AN ANCESTOR, and the only
          differences are in files neither of us authored
                                               -> holds, with the exclusion
                                                  reading NAMED in the record.
        TIP moved, patch-id moved, otherwise   -> re-read.
        TIP orphaned                           -> re-read. No exception.

    WHY THE WRITTEN CLAIM IS REQUIRED AND NOT MERELY THE GIT CHECK. Ancestry
    alone is not sufficient, and the gap is not theoretical: a branch that
    adds real new commits on top of the reviewed one passes an ancestor test
    exactly as cleanly as one that only caught up. What separates row three
    from row four is whether the differences are artifact-only -- a judgement
    about which files count -- and that is precisely the judgement she refused
    to let this repository keep in a list::

        "I will not have a rule that says movement in these paths is exempt.
        Not because your two paths are wrong. Because the mechanism that keeps
        the list correct does not exist."

    Her reason was that every hand-maintained list in this house has gone
    stale, and this one would go stale in the direction that matters: a path
    added that is not purely generated makes her signature cover something she
    never read, with nothing anywhere to show it.

    So the interpretive half stays with the reviewer, per round, in their own
    hand, and this verifies the half that has no interpretation in it. A round
    claiming no ancestry gets no rung at all and falls through to the refusal
    below -- which means the looser reading cannot be inherited by accident. It
    has to be written down by someone willing to sign it.

    KNOWN LIMIT, in the permissive direction, inherited from
    ``_confirmed_trees``: this cannot tell a commit a finding CONFIRMS from one
    it merely MENTIONS. It is narrower than the tree case only because the
    finding must assert an ancestry in prose before any hash inside it is read
    at all.
    """
    from divineos.core.watchmen.store import list_findings

    if not head_sha:
        return False, "the PR head commit could not be resolved, so nothing could be checked"
    try:
        findings = list_findings(round_id=round_id, limit=200) or []
    except Exception:  # noqa: BLE001 - an unreadable store is not "no claim"
        return False, "the audit store could not be read, so no claim could be found"

    claimed: set[str] = set()
    for f in findings:
        # Same withheld-title filter as the tree rung, and needed here for a
        # sharper reason: a clearance that DECLINES to read a branch is exactly
        # the kind of note that explains why -- and "the tip I signed is still
        # an ancestor, but I have not read what sits on top of it" carries both
        # the word and the hash while granting nothing.
        if _title_withholds(f):
            continue
        text = f"{getattr(f, 'title', '') or ''} {getattr(f, 'description', '') or ''}"
        if "confirms" not in text.lower():
            continue
        if not _ANCESTRY_CLAIM.search(text):
            continue
        claimed.update(m.group(1).lower() for m in _TIP_NEAR.finditer(text))

    if not claimed:
        return False, (
            "no CONFIRMS finding on this round claims the reviewed commit is an ancestor"
        )

    unresolvable: list[str] = []
    orphaned: list[str] = []
    for tip in sorted(claimed):
        state = _is_ancestor(tip, head_sha)
        if state is True:
            return True, (
                f"reviewed commit {tip[:12]} is an ancestor of head {head_sha[:12]}, "
                "so that review was built upon rather than superseded"
            )
        if state is False:
            orphaned.append(tip[:12])
        else:
            unresolvable.append(tip[:12])

    if orphaned and not unresolvable:
        return False, (
            f"the commit(s) claimed as ancestors ({', '.join(orphaned)}) are NOT in this "
            "head's history -- that tip is orphaned, and an orphaned tip owes a re-read "
            "with no exception available"
        )
    return False, (
        f"the claimed commit(s) ({', '.join(unresolvable + orphaned)}) could not all be "
        "resolved here, and a lookup that failed must not be read as a pass -- fetch the "
        "branch and re-run"
    )


_BASE_BRANCH = "origin/main"


def _commits_behind_base(branch: str) -> tuple[int, str]:
    """(commits_behind, reason_it_could_not_be_determined) for ``branch``.

    Returns ``(n, "")`` when the answer is known and ``(0, why)`` when it is
    not. The two are kept apart because a caller that collapses them ends up
    reporting a cause it never established -- which is how the first version
    of this preflight came to blame a branch for a missing shell.

    MEASURES THE PR'S BRANCH, NOT HEAD (fixed 2026-08-21). This compared
    ``HEAD..origin/main``, so it answered about whichever branch the invoking
    checkout happened to be standing on -- which for a PR command is almost
    never the PR's branch. Caught on #412: the branch was 0 behind
    origin/main and had just been merged forward and pushed, and the gate
    refused to stamp it because the main checkout sat on an unrelated branch
    that was 3 behind. Measured side by side:

        HEAD..origin/main                            3   <- what it used
        origin/split/ci-merge-review-visibility..    0   <- the real answer

    A confident wrong answer about the wrong subject, which is the class this
    module's own comments keep naming. It is also a second instance of
    claim-795eacd8: the verdict came from the checkout rather than from the
    data. The remote-tracking ref is the right subject because it is what
    GitHub will merge -- a local branch of the same name can be stale or
    absent in whichever tree the command was run from.

    Straight git, no shell. The freshness logic is `fetch` plus `rev-list
    --count`, and shelling out to a .sh for it introduced a dependency on
    which `bash` happens to be first on PATH. On this box that is WSL's, which
    cannot see the Windows filesystem and failed with an execvpe error that
    said nothing about branches. Two commands inline have no such surface.
    """
    if not branch:
        return 0, "no branch resolved for this PR"
    try:
        fetch = subprocess.run(
            ["git", "fetch", "--quiet", "origin", "main", branch],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
        if fetch.returncode != 0:
            return 0, f"could not fetch {_BASE_BRANCH}/{branch}: {fetch.stderr.strip()[:80]}"
        head_ref = f"origin/{branch}"
        resolved = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"{head_ref}^{{commit}}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
        if resolved.returncode != 0:
            # Unpushed branch: genuinely unknown, and unknown must not read as
            # safe when the next step rewrites history.
            return 0, f"{head_ref} does not exist on the remote"
        count = subprocess.run(
            ["git", "rev-list", "--count", f"{head_ref}..{_BASE_BRANCH}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )
        if count.returncode != 0:
            return 0, f"rev-list failed: {count.stderr.strip()[:80]}"
        return int(count.stdout.strip() or 0), ""
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return 0, f"{type(exc).__name__}: {exc}"


def _worktrees_holding(branch: str) -> list[str]:
    """Paths of worktrees with ``branch`` checked out. Empty when none do.

    Exists so the failure message can say which causes it TESTED rather than
    naming a plausible one it did not. Returns empty on any error: a check
    that cannot run must not manufacture a holder, since the whole point is
    to stop asserting an untested cause.
    """
    try:
        out = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        )
        if out.returncode != 0:
            return []  # both-empty: the caller asks only "which holders can I NAME",
            # and neither a failed listing nor an absent one can name any. The
            # distinction that would matter -- could-not-look versus looked-and-
            # found-none -- is not one this caller acts on differently: it prints
            # the holders it has, and printing none is correct either way. What
            # must never happen is manufacturing a holder from a check that did
            # not run, and both branches refuse that identically.
    except OSError:
        return []  # both-empty: same reason as the returncode branch above.

    holders: list[str] = []
    current_path = ""
    for line in out.stdout.splitlines():
        if line.startswith("worktree "):
            current_path = line[len("worktree ") :].strip()
        elif line.startswith("branch "):
            ref = line[len("branch ") :].strip()
            if ref in (f"refs/heads/{branch}", branch):
                holders.append(current_path)
    return holders


def _round_by_id(round_id: str):
    """The round record, or None. Lookup by id, never by position."""
    from divineos.core.watchmen.store import list_rounds

    for rnd in list_rounds(limit=500):
        if getattr(rnd, "round_id", "") == round_id:
            return rnd
    return None


def sibling_rounds_naming(branch: str) -> tuple[list[str], list[str]]:
    """Rounds in the OTHER seats' stores whose text names this branch.

    Returns (found, unreadable) — the matching round strings, and the names of
    any seat that is present but could not be read.

    ## Why this exists, measured 2026-09-10

    Andrew: *"you need to fix the root cause of why you skipped those 3 build
    flow steps."* The chain, each link checked rather than reasoned:

    The three stations I skipped live on the half of the flow that only exists
    once a work item is open. The doorman that forces one open at the first
    edit is written, wired and tested — and is not installed here; the module
    is absent from this branch and the hook is not in this checkout's wiring.
    It is not installed because its pull request is still a draft. It is still
    a draft because taking it out of draft requires an audit round naming its
    branch, and this command said there was none.

    **There were two.** Both in Aria's store, both naming the branch. The
    readiness board reads the union of every seat and has therefore been
    printing READY for that door for two days. This command reads one store,
    found nothing, and said *No audit round names branch ...* — a statement
    about MY store published with the scope of ALL of them.

    So the door that would have stopped me skipping those stations has been
    held shut by an instrument reporting an absence it was not in a position
    to see.

    ## What this does NOT do

    It does not authorize a stamp from a sibling round, and it must not. The
    validator reads confirms out of the local store by id; a round it cannot
    open is a round whose two CONFIRMS it cannot check, and a merge stamped on
    an unvalidated round is worse than one that never happened. What this buys
    is that the refusal tells the truth: the round exists, here is its id, and
    here is why this seat cannot act on it — rather than an absence that sends
    someone off to file a round that is already filed.

    A seat present-but-unreadable is reported separately for the same reason.
    Could-not-look is not found-nothing.
    """
    found: list[str] = []
    unreadable: list[str] = []
    tail = branch.rsplit("/", 1)[-1] if branch else ""
    if not branch:
        return found, unreadable
    try:
        from divineos.core.sibling_audit_rounds import read_other_seats, this_seat

        seats = read_other_seats(this_seat())
    except Exception as exc:  # noqa: BLE001
        return found, [f"sibling reader unavailable: {type(exc).__name__}: {exc}"]

    for seat in seats:
        name = getattr(seat, "name", "?")
        if getattr(seat, "error", None) is not None:
            unreadable.append(f"{name}: {seat.error}")
            continue
        if getattr(seat, "absent", False):
            continue
        for text in getattr(seat, "rounds", None) or ():
            text = str(text)
            if branch in text or (tail and tail in text):
                found.append(f"{name}: {text[:200]}")
    return found, unreadable


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
                # SAY WHOSE STORE WAS SEARCHED. This used to read "No audit
                # round names branch X" while the readiness board, reading
                # every seat, printed READY for the same branch. See
                # sibling_rounds_naming for the chain that cost.
                elsewhere, unreadable = sibling_rounds_naming(branch)
                click.secho(
                    f"[!] No audit round in THIS seat's store names branch {branch}.",
                    fg="red",
                )
                for line in unreadable:
                    click.secho(
                        f"    could not read another seat — {line}",
                        fg="yellow",
                    )
                if elsewhere:
                    click.secho(
                        f"    But {len(elsewhere)} round(s) in another seat's store name it:",
                        fg="yellow",
                    )
                    for line in elsewhere:
                        click.echo(f"      {line}")
                    click.secho(
                        "    This seat cannot validate a round it cannot open, so it "
                        "will not stamp on one. Sync that round into this store, or "
                        "pass --audit-round once it is here.",
                        fg="bright_black",
                    )
                elif not unreadable:
                    click.secho(
                        "    No other seat names it either. File one, or pass "
                        "--audit-round explicitly.",
                        fg="bright_black",
                    )
                else:
                    click.secho(
                        "    Whether another seat names it is UNKNOWN — a seat was "
                        "unreadable. Not the same as none.",
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

        # PREFLIGHT BEFORE REWRITING. run_push_ready amends every
        # guardrail-touching commit to carry the trailer, which rewrites their
        # identities, and only THEN tries to push. So a push that was never
        # going to be accepted still costs a full history rewrite -- and leaves
        # the branch diverged from origin with the PR body unwritten, which is
        # a half-finished state that looks like nothing happened until the next
        # ordinary push is refused for reasons that have nothing to do with
        # what the person was doing at the time.
        #
        # Observed 2026-08-17 on PR #412: seven commits amended, then
        # "[freshness-check] BLOCKED: branch is 2 commit(s) behind
        # origin/main". Every individual step was correct. The ORDER was not.
        #
        # This module already holds the principle -- "Order is load-bearing: a
        # failure between the two leaves a draft carrying a valid trailer,
        # which is recoverable" -- and simply had not extended it past the
        # body/ready pair to the rewrite itself. Whether the push will be
        # refused is knowable in advance: it is a comparison against a ref.
        #
        # The check is read-only (fetch + merge-base) and exits 0 for safe,
        # 1 for blocked, so it can be asked without committing to anything.
        #
        # RUNS IN DRY-RUN TOO. The first version of this preflight skipped it
        # under --dry-run, reasoning that a dry run rewrites nothing so there
        # is nothing to protect. That gets the purpose backwards: a dry run
        # exists to say what WOULD happen, and one that reports a clean
        # preview of an operation that would actually be refused is a
        # confident wrong answer -- the exact class this session kept finding.
        behind, why = _commits_behind_base(branch)
        if why:
            # COULD NOT CHECK is not the same as WOULD BE REFUSED, and saying
            # the wrong one is its own bug. The first version of this preflight
            # shelled out to the freshness script and printed "the branch
            # cannot be pushed as it stands" whenever that returned non-zero --
            # including when it had not run at all. Dogfooding it produced
            # exactly that: `bash` resolved to WSL's bash, which could not find
            # /bin/bash, and the refusal blamed the branch for a shell that was
            # never there.
            #
            # That is the same misattribution repaired in build_flow's station
            # 8 earlier the same day, rewritten by me hours later. Refusing on
            # an unreadable check is right -- this guards a destructive rewrite
            # and unknown must not read as safe -- but the MESSAGE has to say
            # which of the two happened.
            click.secho(
                f"[!] Not stamping: could not determine whether this branch is\n"
                f"    behind {_BASE_BRANCH} ({why}). Stamping rewrites history, so an\n"
                "    unreadable check is treated as unsafe rather than as fine.",
                fg="red",
            )
            click.secho("    Nothing was changed.", fg="bright_black")
            raise click.exceptions.Exit(1)
        if behind:
            click.secho(
                f"[!] Not stamping: this branch is {behind} commit(s) behind "
                f"{_BASE_BRANCH},\n"
                "    so the push would be refused -- and stamping rewrites history\n"
                "    BEFORE it finds that out, leaving the branch diverged with the\n"
                "    PR body unwritten.",
                fg="red",
            )
            click.secho(
                f"    Nothing was changed. Merge {_BASE_BRANCH}, then re-run.",
                fg="bright_black",
            )
            raise click.exceptions.Exit(1)

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
                    "    Not writing the body, not clearing draft. This guard "
                    "sees the missing trailer, not the reason -- and there is "
                    "more than one. The branch may be held by another worktree "
                    "so its history cannot be rewritten from here; or the "
                    "rewrite may have run against a different branch entirely. "
                    "Check which branch is checked out here before assuming "
                    "the worktree.",
                    fg="bright_black",
                )
                # NAME WHAT WAS TESTED, NOT WHAT IS PLAUSIBLE. This used to
                # assert a "common cause" -- the branch being checked out in
                # another worktree -- that it had never checked. On 2026-09-05
                # that sent me hunting a worktree holding the branch. None did.
                # The rewrite HAD run; it ran against a local ref the server had
                # moved past, so the amend was real and landed on old history.
                # A confidently-named untested cause costs more than silence,
                # because it aims the search away from the actual fault.
                for holder in _worktrees_holding(branch):
                    click.secho(
                        f"    Checked: {holder} has {branch} checked out, which "
                        "prevents rewriting it from here.",
                        fg="bright_black",
                    )
                    break
                else:
                    click.secho(
                        f"    Checked: no worktree holds {branch}, so that is not "
                        "the cause here. Compare the local branch against "
                        f"origin/{branch} -- a rewrite of a stale local ref "
                        "amends history the server has already moved past.",
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
                # THE TREE IS THE STRICT RUNG, NOT THE ONLY ONE.
                #
                # A tree hash moves when ANY byte under it moves, including a
                # generated file that no reviewer wrote. So catching a branch
                # up to main -- the one act required to make it mergeable --
                # rewrites the capability catalogue and breaks this rung, and
                # the branch becomes unmergeable by having been made
                # mergeable. That happened on this very PR on 2026-09-03: the
                # remedy withdrew the licence it was granted under, which is
                # the fourth instance of that shape in this correspondence and
                # the first one built here rather than found.
                #
                # Aletheia's amended rule puts ANCESTRY under the tree: if the
                # commit she read is still in this history, her reading was
                # built upon rather than superseded. See ``_ancestry_rung``
                # for the full table and for why the rung demands a written
                # claim instead of trusting the git check alone.
                holds, why = _ancestry_rung(round_id, _pr_head_oid(pr_number))
                if holds:
                    click.secho(
                        f"[+] Head tree {tree_hash[:12]} is not one this round names, but the\n"
                        f"    ANCESTRY rung holds: {why}.\n"
                        "    Proceeding on a reviewer's written claim, verified here rather\n"
                        "    than taken on its word.",
                        fg="green",
                    )
                    content_holds = False
                    content_why = "not reached; ancestry already held"
                else:
                    # THE CONTENT RUNG, under ancestry and above refusal.
                    #
                    # Aria measured the gap: this rule was implemented in the
                    # tool that FILES a confirm and only described in this one,
                    # which spends them. Andrew's ruling is the frame -- if the
                    # code itself is unchanged the review stands, because the
                    # floor moving is not the reviewer's subject changing, and
                    # re-auditing on floor-movement is an endless run-around
                    # over the same work.
                    #
                    # Placed AFTER ancestry rather than before because ancestry
                    # rests on a reviewer's written claim and this rests on a
                    # computation; when a person has said it in their own hand,
                    # that is the stronger evidence and should be reported as
                    # what carried.
                    content_holds, content_why = _content_rung(round_id, branch)

                if content_holds:
                    click.secho(
                        f"[+] Head tree {tree_hash[:12]} is not one this round names, and the\n"
                        f"    ancestry rung did not hold ({why}).\n"
                        f"    The CONTENT rung does: {content_why}.\n"
                        "    Computed here the same way the confirm validator computes it,\n"
                        "    rather than inferred from the trees disagreeing.",
                        fg="green",
                    )
                elif not holds:
                    named = ", ".join(sorted(t[:12] for t in confirmed))
                    click.secho(
                        f"[!] Round {round_id} CONFIRMS tree(s) {named}, but this PR's head\n"
                        f"    tree is {tree_hash[:12]}. Pairing them would assert a review\n"
                        "    that did not happen.\n"
                        f"    The ancestry rung does not save it either: {why}.\n"
                        f"    Nor the content rung: {content_why}.\n"
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
