"""One council walk over all the changes, checked at the push.

Dad, 2026-07-30, 2026-10-07 and 2026-10-12: the full paperwork on every single change is
brutal. Make the changes, then do ONE walk over all of them before the push. The design,
the council that reviewed it and Aria's cold read are in
docs/drafts/one_walk_before_the_push_not_one_per_edit_draft_2026-10-12.md.

THE INVARIANT. Every authored change that leaves one of our seats for the remote is
covered by a closed walk bound to its diff. This file establishes it at the push; the
stamp station re-establishes it for pushes that come from outside. Exactly two exceptions
exist: main arriving in a branch (not authored work) and an edit made on main itself (no
later gate to defer to, so the per-edit rule stays as it was). A third exception proposed
for convenience is a hole in the proof.

WHAT IT CHECKS, said plainly so a pass is never read as a review: that a closed walk
exists, names every changed file, and matches the current diff. It cannot check that the
thinking inside the walk was real. Same limit as before this change.

COULD-NOT-LOOK REFUSES. If the diff, the walk store or the repository cannot be read, the
push is refused with a message saying so. An unreadable state read as a pass is the
oldest hole in this house.

The walk is bound to the PATCH-ID of the diff it covered, not to a clock: rebase rewrites
commit dates, tools disagree about time, and main arriving in a branch leaves the authored
patch-id unchanged. Walks closed before the binding existed fall back to comparing times
against the last authored commit.
"""

from __future__ import annotations

import re
import shlex
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

BASE = "origin/main"

# The largest follow-up an amendment may absorb, in added plus removed lines. One number,
# here, where Dad can read and change it. Larger or wider changes need a fresh walk.
AMEND_MAX_LINES = 30
MIN_AMEND_FINDING_CHARS = 40

_SEPARATORS = ("&&", "||", ";", "|", "&")
_WRAPPERS = ("cd", "set", "export", "env", "source", ".", "exec", "sudo", "time")
_PUSH_SCRIPT = "divineos_push.sh"


@dataclass(frozen=True)
class PushDecision:
    allow: bool
    message: str = ""


def _git(repo: Path, *args: str, stdin: str | None = None) -> str | None:
    """Run git in ``repo``; None means could-not-look (never an empty answer)."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=repo,
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def is_push_command(command: str) -> bool:
    """Does any segment of this shell line run ``git push`` or the push wrapper?"""
    try:
        lexer = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return False
    segments: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token in _SEPARATORS:
            if current:
                segments.append(current)
            current = []
        else:
            current.append(token)
    if current:
        segments.append(current)
    for seg in segments:
        while seg and "=" in seg[0] and seg[0].split("=", 1)[0].isidentifier():
            seg = seg[1:]
        if not seg:
            continue
        head = re.split(r"[\\/]", seg[0])[-1].lower().removesuffix(".exe")
        if head in _WRAPPERS:
            continue
        if head == "git" and _git_subcommand(seg[1:]) == "push":
            return True
        if head in ("bash", "sh") and any(t.endswith(_PUSH_SCRIPT) for t in seg[1:3]):
            return True
        if head == _PUSH_SCRIPT:
            return True
    return False


def _git_subcommand(args: list[str]) -> str | None:
    """The subcommand after git's own global options (-C <dir>, -c k=v, --git-dir=...)."""
    i = 0
    while i < len(args):
        token = args[i]
        if token in ("-C", "-c", "--git-dir", "--work-tree", "--namespace"):
            i += 2
            continue
        if token.startswith("-"):
            i += 1
            continue
        return token
    return None


def on_main(repo: Path) -> bool | None:
    """True on main; False on any other branch or a detached HEAD; None if unreadable.

    Decided by what HEAD is, never by a branch name pattern: many work copies sit on a
    detached HEAD, and those are not main (Aria's cold read).
    """
    if _git(repo, "rev-parse", "--git-dir") is None:
        return None
    try:
        proc = subprocess.run(
            ["git", "symbolic-ref", "-q", "--short", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return False
    return proc.stdout.strip() == "main"


def changed_files(repo: Path, base: str = BASE) -> tuple[str, ...] | None:
    out = _git(repo, "diff", "--name-only", f"{base}...HEAD")
    if out is None:
        return None
    return tuple(sorted(line.strip() for line in out.splitlines() if line.strip()))


def diff_identity(repo: Path, base: str = BASE) -> str | None:
    """The patch-id of everything this branch changes against ``base``; "" for no change."""
    diff = _git(repo, "diff", f"{base}...HEAD")
    if diff is None:
        return None
    if not diff.strip():
        return ""
    out = _git(repo, "patch-id", "--stable", stdin=diff)
    if out is None or not out.split():
        return None
    return out.split()[0]


def head_sha(repo: Path) -> str | None:
    out = _git(repo, "rev-parse", "HEAD")
    return out.strip() if out else None


def _last_authored_commit_time(repo: Path, base: str = BASE) -> float | None:
    """When the newest commit that is not a merge was made. Merges are main arriving."""
    out = _git(repo, "log", "--no-merges", "-1", "--format=%ct", f"{base}..HEAD")
    if out is None:
        return None
    return float(out.strip()) if out.strip() else 0.0


def _sections(diff: str) -> dict[str, Counter]:
    """Changed lines by file: the +/- lines of each file's section, as a multiset."""
    files: dict[str, Counter] = {}
    current: Counter | None = None
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            name = line.rsplit(" b/", 1)[-1]
            current = files.setdefault(name, Counter())
        elif current is not None and line[:1] in "+-" and not line.startswith(("+++", "---")):
            current[line] += 1
    return files


def change_between(repo: Path, old_head: str, base: str = BASE) -> tuple[int, set[str]] | None:
    """The AUTHORED change since ``old_head``: lines added or removed, and files touched.

    Both sides are measured against ``base`` and compared, so main arriving in between
    contributes nothing: only lines that differ between the old branch diff and the new
    one count.
    """
    old = _git(repo, "diff", f"{base}...{old_head}")
    new = _git(repo, "diff", f"{base}...HEAD")
    if old is None or new is None:
        return None
    old_files, new_files = _sections(old), _sections(new)
    lines = 0
    touched: set[str] = set()
    for name in set(old_files) | set(new_files):
        before, after = old_files.get(name, Counter()), new_files.get(name, Counter())
        delta = sum(((after - before) + (before - after)).values())
        if delta:
            lines += delta
            touched.add(name)
    return lines, touched


# The features a BUILDING edit fires. On a branch these pass without a per-edit walk,
# because the covering walk at the push reads the same diff at a point it can still be
# fixed. Every other feature (substrate-write commands, consolidation, the kiln layer)
# is not branch work and goes back to the old strict gate untouched: freeing "every
# council-required command on a branch" would let a prereg or audit filing skip the walk.
BUILDING_FEATURES = frozenset(
    {"git-commit", "edit-src-divineos", "edit-guardrail", "edit-guardrail-listed"}
)


@dataclass(frozen=True)
class BranchRule:
    """What the branch rule decided: ``handled`` means the hook stops with ``exit_code``."""

    handled: bool
    exit_code: int = 0
    message: str = ""


def record_free_pass(fingerprint: str) -> None:
    """One line per free pass, so an unwalked edit is visible and the order is recoverable.

    Goes to a file and never to the screen: a line printed on every edit becomes wallpaper
    within a day. A log that cannot be written does not block the edit (a hostile failure
    mode for a harmless one), but the failure is returned loudly by the caller.
    """
    import json
    import time

    from divineos.core.paths import divineos_home

    path = divineos_home() / "branch_edit_passthrough.log"
    line = json.dumps({"at": time.time(), "fingerprint": fingerprint})
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def target_dir(file_paths: tuple[str, ...], bash_command: str, default: Path) -> Path | None:
    """The folder a call acts in, or None when it cannot be told (the caller stays strict).

    The hook runs from the session's checkout, not from the work copy being edited, so
    asking git about the hook's own folder would judge the wrong repository. For an edit it
    is the folder of the file; for a shell line it is the last ``cd <dir>`` or ``git -C
    <dir>`` before the act, read in order, because the order inside the line decides which
    folder an act happens in. A line with neither acts where it started.
    """
    if file_paths:
        folder = Path(file_paths[0]).parent
        while not folder.exists() and folder != folder.parent:
            folder = folder.parent
        return folder if folder.exists() else None
    if not bash_command:
        return Path(default)
    try:
        lexer = shlex.shlex(bash_command.replace("\n", " ; "), posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return None
    where = Path(default)
    segment: list[str] = []
    for token in [*tokens, ";"]:
        if token not in _SEPARATORS and token != ";":
            segment.append(token)
            continue
        if segment:
            head = re.split(r"[\\/]", segment[0])[-1].lower().removesuffix(".exe")
            if head == "cd" and len(segment) >= 2:
                where = (
                    (where / segment[1]) if not Path(segment[1]).is_absolute() else Path(segment[1])
                )
            elif head == "git" and "-C" in segment[1:3]:
                value = (
                    segment[segment.index("-C") + 1]
                    if segment.index("-C") + 1 < len(segment)
                    else ""
                )
                if value:
                    where = (where / value) if not Path(value).is_absolute() else Path(value)
        segment = []
    return where if where.exists() else None


def branch_rule(
    repo: Path, tool_name: str, bash_command: str, fired_features: tuple[str, ...], fingerprint: str
) -> BranchRule:
    """The one place the rule lives: building on a branch is free, the push is the choke.

    Main is not handled here (an edit made on main has no later gate to defer to). A
    push on a branch is judged by ``decide_push``. A building edit on a branch passes and
    leaves a line. Anything else, including an unreadable branch, is NOT handled and falls
    through to the old strict gate, which is the safe direction.
    """
    if bash_command and is_push_command(bash_command):
        if on_main(repo) is True:
            return BranchRule(False)
        decision = decide_push(repo, bash_command)
        return BranchRule(True, 0 if decision.allow else 2, decision.message)
    if on_main(repo) is False and fired_features and set(fired_features) <= BUILDING_FEATURES:
        try:
            record_free_pass(fingerprint)
        except OSError as exc:
            return BranchRule(True, 0, f"[branch-rule] free pass not recorded: {exc}")
        return BranchRule(True, 0, "")
    return BranchRule(False)


def open_command(files: tuple[str, ...], guardrail_hit: bool) -> str:
    gravity = "high" if guardrail_hit else "normal"
    scope = " ".join(f"--scope {f}" for f in files)
    return (
        'divineos walk open "Does this change hold across every file it changes?" '
        f"--gravity {gravity} {scope}"
    )


def decide_push(repo: Path, command: str) -> PushDecision:
    """May this command push? Anything that is not a push is nothing to this."""
    if not is_push_command(command):
        return PushDecision(True)
    repo = Path(repo)
    main = on_main(repo)
    if main is None:
        return PushDecision(
            False,
            "I could not tell which branch this is, so the push is refused rather than "
            "guessed at. Run it from inside the work copy.",
        )
    if main:
        return PushDecision(True)  # main keeps the per-edit rule; nothing later defers it
    files = changed_files(repo)
    if files is None:
        return PushDecision(
            False,
            f"I could not read what this branch changes against {BASE}, so the push is "
            "refused rather than guessed at. Fetch origin and try again.",
        )
    if not files:
        return PushDecision(True)

    from divineos.core import council_walk

    coverage = council_walk.coverage_for(files)
    if coverage.state == "cannot-check":
        return PushDecision(
            False,
            f"I could not read the walk store ({coverage.reason}), so the push is refused "
            "rather than guessed at.",
        )
    if coverage.state != "covered":
        return PushDecision(False, _needs_a_walk(repo, files, coverage.reason))

    current = diff_identity(repo)
    if current is None:
        return PushDecision(
            False, "I could not read the diff to compare it with the walk, so the push is refused."
        )
    if coverage.bound_diff:
        if coverage.bound_diff == current:
            return PushDecision(True)
        return PushDecision(
            False,
            f"The changes have changed since {coverage.walk_id} was closed. A small follow-up "
            f"(up to {AMEND_MAX_LINES} lines, inside the files already walked) is one command: "
            f'divineos walk amend {coverage.walk_id} --finding "<what changed and why it is '
            'safe>". Anything larger needs a fresh pass, in one sitting.',
        )
    # A walk closed before the binding existed: compare times, the older and weaker way.
    last = _last_authored_commit_time(repo)
    if last is None:
        return PushDecision(False, "I could not read the commit times, so the push is refused.")
    if coverage.closed_at is not None and coverage.closed_at >= last:
        return PushDecision(True)
    return PushDecision(
        False,
        f"{coverage.walk_id} was closed before your last commit, so it has not seen the "
        "final changes. " + _needs_a_walk(repo, files, ""),
    )


def _needs_a_walk(repo: Path, files: tuple[str, ...], why: str) -> str:
    from divineos.core import pr_scope

    guard, _ = pr_scope.load_guardrail_set(repo)
    hit = bool(guard and set(files) & guard)
    lead = f"{why}. " if why else ""
    return (
        f"{lead}Before this goes up, one council pass over everything it changes "
        f"({len(files)} file(s)), done in one sitting (read each lens and walk it within "
        "45 minutes, not an hour apart). One command opens it with every file filled in:\n"
        f"  {open_command(files, hit)}\n"
        "Apply each lens, close it, then push again. This checks that the pass exists, "
        "names every changed file and matches the changes; nothing can check the thinking "
        "inside it."
    )
