"""Work copies clean themselves up: finished ones are removed, doubtful ones are listed, nothing is guessed.

Dad, 2026-10-20, after about ninety of my old work copies were found in his C drive (19.4 GB, links not
followed): "we have built programs to prevent AI slop lol but nothing to prevent you being an AI slob ...
so we need to automate it so when something is done and no longer needed it gets deleted", and "my computer
is your home so i do not mind you having stuff in different places ... i dont want it to turn into a
hoaders den". His yes to the shape: remove the clearly finished ones by itself, show him the doubtful ones.

THE RULE, asked of the folder itself and never of a clock:
  finished         its branch landed (PR MERGED or CLOSED with nothing local beyond what was published,
                   or the branch is already in origin/main); a detached copy is finished only if a remote ref
                   reaches its HEAD
  nothing unique   no uncommitted or untracked files and no ignored files outside a named regenerable set
                   (git also destroys ignored files on removal: local databases, env files)
  links safe       every link inside points inside the folder, dangles, or is the known link to the main
                   checkout's own .venv. Anything else is a link to something real and makes the copy doubtful

Yes to all three: remove it, links first (a link is removed as a link, never walked: on 2026-10-20
`git worktree remove --force` followed a .venv junction and emptied my real venv, correction #392).
Anything else is never touched and goes on a list. UNREADABLE IS NEVER FINISHED: a host that could not be
asked, a git call that failed, a state this module does not model, each of them is SHOW.

Never touched whatever the answers: the main checkout, the copy the sweep runs from, a copy modified in the
last two hours (a guard against pulling a floor out from under work in progress; it keeps, it never deletes).

The four answers are re-asked immediately before each removal, not trusted from the listing, and every
removal is appended to a log with what was true at that moment, so a removal can be audited afterwards.

Walked as walk-91a1bab8430a (12 seated lenses, 5 added); pre-registered as prereg-64b58b46e1bc.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

RECENT_SECONDS = 2 * 3600

# Ignored paths a work copy regenerates by itself. Anything ELSE that is ignored may hold work that
# exists nowhere else, and git removes ignored files along with the folder.
_REGENERABLE_NAMES = frozenset(
    {
        "tmp",
        ".venv",
        ".direnv",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".hypothesis",
        "dist",
        "build",
    }
)


class Verdict(Enum):
    REMOVE = "remove"
    SHOW = "show"
    KEEP = "keep"


class WorkCopyRefused(RuntimeError):
    """A refusal is the mechanism working, not an error to route around."""


PrInfo = Callable[[str], "tuple[str, str] | None"]


def gh_pr_info(branch: str) -> tuple[str, str] | None:
    """(state, head_oid) of the newest pull request from this branch, or None if it could not be read."""
    try:
        done = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--head",
                branch,
                "--state",
                "all",
                "--json",
                "state,headRefOid",
                "--limit",
                "1",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if done.returncode != 0:
            return None
        rows = json.loads(done.stdout or "[]")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None
    if not rows:
        return None
    return str(rows[0].get("state", "")), str(rows[0].get("headRefOid", ""))


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def main_root_of(path: Path) -> Path:
    """The main checkout of the repository that `path` belongs to."""
    done = _git(path, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if done.returncode != 0:
        raise WorkCopyRefused(f"not inside a git repository: {path}")
    return Path(done.stdout.strip()).parent.resolve()


def list_copies(main_root: Path) -> list[Path]:
    done = _git(main_root, "worktree", "list", "--porcelain")
    if done.returncode != 0:
        raise WorkCopyRefused(f"could not list work copies: {done.stderr.strip()}")
    return [
        Path(line[len("worktree ") :]).resolve()
        for line in done.stdout.splitlines()
        if line.startswith("worktree ")
    ]


def _regenerable(rel: str) -> bool:
    parts = [p for p in rel.replace("\\", "/").strip('"').split("/") if p]
    if not parts:
        return True
    return (
        parts[0] in _REGENERABLE_NAMES
        or "__pycache__" in parts
        or parts[-1].endswith(".pyc")
        or parts[-1] == ".coverage"
    )


def _is_gate_scratch(wt: Path) -> bool:
    """A checkout `check_push_readiness.sh` made in the system temp folder for one test run.

    Made at a pushed commit and removed by the gate itself; an interrupted push leaks it (the script says
    so in a comment). It is the one class decided by NAME, so the guard is two-sided: the name AND the
    folder it lives in, and the usual in-use and link checks still apply. A look-alike anywhere else is
    an ordinary copy.
    """
    return (
        wt.name.startswith("divineos-push-gate-")
        and wt.parent.resolve() == Path(tempfile.gettempdir()).resolve()
    )


def _is_link(entry: os.DirEntry) -> bool:
    return entry.is_symlink() or (hasattr(entry, "is_junction") and entry.is_junction())


def _links_in(root: Path) -> list[Path]:
    """Every link inside root, found without ever walking into one."""
    found: list[Path] = []
    stack = [root]
    while stack:
        here = stack.pop()
        try:
            with os.scandir(here) as it:
                for entry in it:
                    if _is_link(entry):
                        found.append(Path(entry.path))
                    elif entry.is_dir(follow_symlinks=False):
                        stack.append(Path(entry.path))
        except OSError:
            continue
    return found


def _plain(p: str) -> str:
    """Windows hands back extended-length paths for junction targets; compare plain ones."""
    return p[4:] if p.startswith("\\\\?\\") else p


def _target_of(link: Path) -> Path | None:
    try:
        return Path(_plain(os.path.realpath(_plain(os.readlink(link)))))
    except (OSError, ValueError):
        return None


def _link_is_safe(link: Path, wt: Path, main_root: Path) -> bool:
    target = _target_of(link)
    if target is None or not target.exists():
        return True  # dangling: nothing real on the other end
    t = str(target).lower()
    inside = t == str(wt).lower() or t.startswith(str(wt).lower() + os.sep)
    known_venv = t == str((main_root / ".venv").resolve()).lower() and link.name == ".venv"
    return inside or known_venv


def _unlink(link: Path) -> None:
    """Remove a link as a link. Never touches what it points at."""
    if link.is_dir() and os.name == "nt":
        os.rmdir(link)  # a junction or directory symlink: removes the link only
    else:
        os.unlink(link)


@dataclass
class CopyState:
    path: str
    branch: str = ""
    head: str = ""
    detached: bool = False
    dirty: list[str] = field(default_factory=list)
    ignored_unique: list[str] = field(default_factory=list)
    unsafe_links: list[str] = field(default_factory=list)
    finished: bool = False
    finished_how: str = ""
    published: bool = False
    recent: bool = False


def _newest_touch(wt: Path) -> float:
    stamps = [wt.stat().st_mtime]
    gitdir = _git(wt, "rev-parse", "--path-format=absolute", "--git-dir")
    if gitdir.returncode == 0:
        g = Path(gitdir.stdout.strip())
        for name in ("index", "HEAD", "logs/HEAD"):
            try:
                stamps.append((g / name).stat().st_mtime)
            except OSError:
                pass
    return max(stamps)


def assess(
    main_root: Path,
    wt: Path,
    *,
    pr_info: PrInfo = gh_pr_info,
    now: float | None = None,
    self_path: Path | None = None,
    recent_seconds: int = RECENT_SECONDS,
) -> tuple[Verdict, CopyState, list[str]]:
    """One work copy -> (verdict, what was true, reasons). A total function: every state answers."""
    now = time.time() if now is None else now
    wt = wt.resolve()
    state = CopyState(path=str(wt))
    if wt == main_root.resolve():
        return Verdict.KEEP, state, ["the main checkout"]
    if self_path is not None and wt == self_path.resolve():
        return Verdict.KEEP, state, ["the copy this sweep is running from"]
    try:
        return _assess_copy(main_root, wt, state, pr_info, now, recent_seconds)
    except Exception as exc:  # noqa: BLE001 - a state this module does not model is doubt, never a crash and never finished
        return (
            Verdict.SHOW,
            state,
            [f"could not read this copy's state: {type(exc).__name__}: {exc}"],
        )


def _assess_copy(
    main_root: Path, wt: Path, state: CopyState, pr_info: PrInfo, now: float, recent_seconds: int
) -> tuple[Verdict, CopyState, list[str]]:
    reasons: list[str] = []
    head = _git(wt, "rev-parse", "HEAD")
    if head.returncode != 0:
        return (
            Verdict.SHOW,
            state,
            [f"could not read this copy's state: {head.stderr.strip() or 'git failed'}"],
        )
    state.head = head.stdout.strip()
    state.branch = _git(wt, "branch", "--show-current").stdout.strip()
    state.detached = not state.branch

    status = _git(wt, "status", "--porcelain", "--untracked-files=normal", "--ignored")
    if status.returncode != 0:
        return Verdict.SHOW, state, [f"could not read this copy's state: {status.stderr.strip()}"]
    scratch = _is_gate_scratch(wt)
    for line in status.stdout.splitlines():
        code, rel = line[:2], line[3:].strip().strip('"')
        if scratch or _regenerable(rel):
            continue  # the push gate's scratch checkout holds nothing of its own, whatever its tests left in it
        (state.ignored_unique if code == "!!" else state.dirty).append(rel)

    remote_reach = _git(wt, "for-each-ref", "--contains", "HEAD", "refs/remotes")
    state.published = remote_reach.returncode == 0 and bool(remote_reach.stdout.strip())
    in_main = _git(wt, "merge-base", "--is-ancestor", "HEAD", "origin/main").returncode == 0

    pr = None
    pr_note = ""
    if state.branch:
        try:
            pr = pr_info(state.branch)
        except Exception as exc:  # noqa: BLE001 - the lookup failing is doubt, not a verdict
            pr_note = f"could not read the pull request state: {exc}"
    if scratch:
        state.finished, state.finished_how = True, "the push gate's own scratch checkout"
    elif in_main:
        state.finished, state.finished_how = True, "already in origin/main"
    elif state.detached:
        reasons.append(
            "detached copy that no remote branch and not main reaches (no branch holds its commits)"
        )
    elif pr is None:
        reasons.append(
            pr_note
            or "could not read the pull request state, so the branch is not known to be finished"
        )
    elif pr[0] in ("MERGED", "CLOSED"):
        if pr[1] == state.head or state.published:
            state.finished, state.finished_how = True, f"pull request {pr[0].lower()}"
        else:
            reasons.append(
                "the pull request landed but this copy holds commits no remote has (not published)"
            )
    else:
        reasons.append(f"pull request state is {pr[0].lower()}, not finished")

    for rel in state.dirty:
        reasons.append(f"uncommitted or untracked: {rel}")
    for rel in state.ignored_unique:
        reasons.append(f"ignored file outside the regenerable set, git would destroy it: {rel}")
    for link in _links_in(wt):
        if not _link_is_safe(link, wt, main_root):
            state.unsafe_links.append(f"{link.relative_to(wt)} -> {_target_of(link)}")
    for rel in state.unsafe_links:
        reasons.append(f"link to something real outside this folder: {rel}")

    state.recent = (now - _newest_touch(wt)) < recent_seconds
    if state.recent:
        return Verdict.KEEP, state, ["modified in the last two hours, so in use"]
    if reasons or not state.finished:
        return Verdict.SHOW, state, reasons
    return Verdict.REMOVE, state, [f"finished ({state.finished_how}), nothing unique, links safe"]


def remove_copy(main_root: Path, wt: Path, *, snapshot: bool = False) -> str:
    """Remove one work copy: refuse unique work (or keep it in refs/rescue/<name> with snapshot), unlink, then git."""
    wt, main_root = wt.resolve(), main_root.resolve()
    if wt == main_root:
        raise WorkCopyRefused(f"that is the main checkout, not a work copy: {wt}")
    state = CopyState(path=str(wt))
    state.branch = _git(wt, "branch", "--show-current").stdout.strip()
    for line in _git(
        wt, "status", "--porcelain", "--untracked-files=normal", "--ignored"
    ).stdout.splitlines():
        code, rel = line[:2], line[3:].strip().strip('"')
        if not _regenerable(rel):
            (state.ignored_unique if code == "!!" else state.dirty).append(rel)
    reached = _git(
        wt, "for-each-ref", "--contains", "HEAD", "refs/heads", "refs/remotes"
    ).stdout.strip()
    unreached = not state.branch and not reached
    note = ""
    if state.dirty or state.ignored_unique or unreached:
        if not snapshot:
            raise WorkCopyRefused(
                f"{wt} holds work that exists nowhere else: {(state.dirty + state.ignored_unique)[:5]}"
                f"{' and a detached HEAD no branch reaches' if unreached else ''}. Re-run with snapshot to keep it in refs/rescue."
            )
        _git(wt, "add", "-A", "--", ".", ":(exclude).venv", ":(exclude)tmp", ":(exclude).direnv")
        tree = _git(wt, "write-tree").stdout.strip()
        sha = _git(
            wt,
            "commit-tree",
            tree,
            "-p",
            "HEAD",
            "-m",
            f"rescue snapshot of {wt} before its folder was removed",
        ).stdout.strip()
        ref = f"refs/rescue/{wt.name}"
        _git(wt, "update-ref", ref, sha)
        if _git(wt, "rev-parse", f"{ref}^{{tree}}").stdout.strip() != tree:
            raise WorkCopyRefused("the snapshot did not hold the work; leaving the copy alone")
        note = f" (snapshot {ref} = {sha[:9]})"
    for link in sorted(_links_in(wt), key=lambda p: len(str(p)), reverse=True):
        _unlink(link)
    done = _git(main_root, "worktree", "remove", "--force", str(wt))
    if done.returncode != 0:
        raise WorkCopyRefused(f"git could not remove {wt}: {done.stderr.strip()}")
    _git(main_root, "worktree", "prune")
    return f"removed {wt}{note}"


@dataclass
class SweepReport:
    removed: list[dict] = field(default_factory=list)
    shown: list[dict] = field(default_factory=list)
    kept: list[dict] = field(default_factory=list)
    could_not_read: int = 0
    dry_run: bool = False

    def summary(self) -> str:
        total = len(self.removed) + len(self.shown) + len(self.kept)
        verb = "would be removed" if self.dry_run else "removed"
        parts = [
            f"{total} work copies: {len(self.removed)} {verb} because finished",
            f"{len(self.shown)} need your word",
            f"{len(self.kept)} in use or the main checkout",
        ]
        line = "; ".join(parts)
        if self.could_not_read:
            line += f"; could not read the state of {self.could_not_read} (counted as doubtful, never as finished)"
        return line


def sweep(
    repo: Path,
    *,
    pr_info: PrInfo = gh_pr_info,
    now: float | None = None,
    dry_run: bool = False,
    self_path: Path | None = None,
    log_path: Path | None = None,
) -> SweepReport:
    """Remove every finished work copy of this repository; list the rest. See the module docstring for the rule."""
    now = time.time() if now is None else now
    main_root = main_root_of(Path(repo))
    report = SweepReport(dry_run=dry_run)
    for wt in list_copies(main_root):
        verdict, state, reasons = assess(
            main_root, wt, pr_info=pr_info, now=now, self_path=self_path
        )
        if verdict == Verdict.REMOVE and not dry_run:
            again, state, reasons = assess(
                main_root, wt, pr_info=pr_info, now=now, self_path=self_path
            )
            if again != Verdict.REMOVE:
                verdict, reasons = (
                    again,
                    [f"changed between the listing and the removal: {r}" for r in reasons],
                )
            else:
                remove_copy(main_root, wt)
        entry: dict = {
            "path": str(wt),
            "branch": state.branch,
            "head": state.head[:9],
            "reasons": reasons,
        }
        if verdict == Verdict.REMOVE:
            entry |= {
                "finished": state.finished,
                "finished_how": state.finished_how,
                "nothing_unique": True,
                "links_safe": True,
            }
            report.removed.append(entry)
        elif verdict == Verdict.SHOW:
            report.shown.append(entry)
            report.could_not_read += any(r.startswith("could not read") for r in reasons)
        else:
            report.kept.append(entry)
    _record(report, log_path, now)
    return report


def _default_log() -> Path:
    from divineos.core.paths import divineos_home

    home = divineos_home()
    home.mkdir(exist_ok=True)
    return home / "work_copy_sweeps.jsonl"


def last_sweep_line(log_path: Path | None = None) -> str:
    """One line for the briefing: when the last sweep ran and what it did. 'Never swept' reads loudly on purpose."""
    path = log_path or _default_log()
    try:
        last = path.read_text(encoding="utf-8").strip().splitlines()[-1]
        row = json.loads(last)
    except (OSError, IndexError, ValueError):
        return "work copies have never been swept: nothing removes my old ones, so they pile up"
    kind = "dry run" if row.get("dry_run") else "sweep"
    return f"last work-copy {kind} {row.get('at', '?')}: {row.get('summary', '?')}"


def _record(report: SweepReport, log_path: Path | None, now: float) -> None:
    if log_path is None:
        log_path = _default_log()
    row = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now)),
        "dry_run": report.dry_run,
        "summary": report.summary(),
        "removed": report.removed,
        "shown": report.shown,
        "kept": report.kept,
        "could_not_read": report.could_not_read,
    }
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")


def main(argv: list[str] | None = None) -> int:
    """`python -m divineos.core.work_copy_sweep [--sweep] [--dry-run] | remove PATH [--snapshot]`."""
    import argparse

    ap = argparse.ArgumentParser(prog="work_copy_sweep", description=__doc__.split("\n")[0])
    ap.add_argument(
        "--sweep",
        action="store_true",
        help="remove the finished copies (default: only list what would happen)",
    )
    ap.add_argument("--dry-run", action="store_true", help="with --sweep, change nothing")
    sub = ap.add_subparsers(dest="cmd")
    rm = sub.add_parser(
        "remove", help="remove one work copy safely: links first, refuse unique work"
    )
    rm.add_argument("path")
    rm.add_argument(
        "--snapshot", action="store_true", help="keep uncommitted work in refs/rescue/<name> first"
    )
    args = ap.parse_args(argv)
    here = Path(__file__).resolve().parents[3]
    if args.cmd == "remove":
        print(remove_copy(main_root_of(Path(args.path)), Path(args.path), snapshot=args.snapshot))
        return 0
    report = sweep(here, dry_run=(args.dry_run or not args.sweep), self_path=here)
    for entry in report.removed:
        print(
            f"{'would remove' if report.dry_run else 'removed'}: {entry['path']}  ({entry['reasons'][0]})"
        )
    for entry in report.shown:
        print(f"needs your word: {entry['path']}")
        for reason in entry["reasons"]:
            print(f"    - {reason}")
    print(report.summary())
    print(last_sweep_line())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
