"""Rebuild a contaminated branch code-only, and prove the code survived.

## What this is for

A checkpoint that did not care which branch was checked out swept hundreds of
letters and exploration entries onto branches whose only claim is that they
carry code. The sweep is fixed at the write path now, but that repair cannot
un-sweep what earlier commits already hold. Those branches still have to be
rebuilt, and rebuilding is where work gets lost.

## Why the obvious method loses work

Hand-picking the commits you recognise drops the ones you do not -- and the
ones you do not recognise are exactly the automatic checkpoints, which is
where real code has repeatedly been sitting. So this takes the WHOLE code
difference between the base and the contaminated tip and replants it in one
move, recognising nothing and deciding nothing.

Registered as prereg-d29d4a907529 before it existed. Its falsifier names the
two ways this dies: a verifier that never refuses is indistinguishable from
one that always says yes, and a tool nobody calls was never a fix. Both are
why the checks below are real comparisons that can fail, and why this is a
command rather than a paragraph of instructions someone has to remember.

## The three things it refuses on

DELETIONS. A replant built from ``git checkout <tip> -- <path>`` silently
drops files the branch DELETED, because there is nothing to check out. They
are carried explicitly, as removals.

CONTENT THAT LIVES NOWHERE ELSE. Substrate files are dropped by design, and
on 2026-08-31 that same correct advice would have destroyed five dreams and a
letter that existed on one branch and no other reference anywhere. So every
dropped file is checked BY CONTENT against every other ref, and any whose
bytes exist nowhere else stops the run. Not by filename: a file that survives
under its own name at different bytes has still lost the edit.

A REPLANT THAT DID NOT REPLANT. Every carried file is compared byte-for-byte
against the tip afterward. A mismatch fails the run rather than warning.

## How it builds

Through a temporary index, matching ``substrate_retarget.commit_paths_to_branch``:
HEAD, the working tree, and the real index are never touched. Switching
branches mid-operation is what let a push already in flight see a tree it did
not expect, and that race is the reason this idiom exists.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_branch_scope import _SUBSTRATE_PREFIXES  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def _git(*args: str, env: dict[str, str] | None = None, check: bool = True) -> str:
    import os

    full_env = None
    if env:
        full_env = dict(os.environ)
        full_env.update(env)
    r = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=full_env,
    )
    if check and r.returncode != 0:
        raise SystemExit(f"[replant] git {' '.join(args)} failed:\n{r.stderr.strip()}")
    return r.stdout.strip()


def _is_substrate(path: str) -> bool:
    return any(path == p or path.startswith(p) for p in _SUBSTRATE_PREFIXES)


def _changed(base: str, tip: str) -> list[tuple[str, str]]:
    """(status, path) for every file the tip changes against the base."""
    rows: list[tuple[str, str]] = []
    for line in _git("diff", "--name-status", f"{base}...{tip}").splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0]:
            # Renames arrive as R100<TAB>old<TAB>new -- the destination wins.
            rows.append((parts[0][0], parts[-1]))
    return rows


def _blob(ref: str, path: str) -> str | None:
    r = subprocess.run(
        ["git", "rev-parse", f"{ref}:{path}"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    return r.stdout.strip() if r.returncode == 0 else None


def _mode(ref: str, path: str) -> str:
    out = _git("ls-tree", ref, "--", path)
    return out.split()[0] if out else "100644"


def _declares_a_generator(ref: str, path: str) -> bool:
    """Does this file's own header say it was exported from somewhere?

    A HINT FOR THE REFUSAL ABOVE, NEVER A PASS. Returns True when the opening
    lines name a source -- the shape the archive mirrors use, which say which
    table they came from and when. That is the file making a claim about
    itself, and this whole class of defect is claims that quietly stopped being
    true, so nothing here treats it as settled. It only tells the reader which
    files are worth the two commands that WOULD settle it.

    Reads the head of the blob rather than the working tree: the question is
    about the version being dropped, and the working tree may be on some other
    branch entirely.
    """
    r = subprocess.run(
        ["git", "show", f"{ref}:{path}"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    if r.returncode != 0:
        return False
    # `or ""` rather than trusting stdout: a zero return code does not promise
    # a string here, and this is a HINT path -- it must never be the thing that
    # crashes a refusal that had already done its job correctly.
    head = "\n".join((r.stdout or "").splitlines()[:8]).lower()
    return "**source:**" in head or "archive mirror" in head or "exported:" in head


def _content_lives_elsewhere(blob: str, tip: str) -> bool:
    """Do these exact bytes sit on any ref other than the one being left?"""
    tip_full = _git("rev-parse", "--symbolic-full-name", tip, check=False) or tip
    for ref in _git("for-each-ref", "--format=%(refname)").splitlines():
        ref = ref.strip()
        if not ref or ref == tip_full:
            continue
        r = subprocess.run(
            ["git", "ls-tree", "-r", ref], cwd=REPO_ROOT, capture_output=True, text=True
        )
        if r.returncode == 0 and blob in r.stdout:
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Replant a branch code-only against a base.")
    ap.add_argument("tip", help="the contaminated branch")
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--into", required=True, help="name for the rebuilt branch")
    ap.add_argument("--apply", action="store_true", help="actually create it")
    args = ap.parse_args(argv)

    rows = _changed(args.base, args.tip)
    code = [(s, p) for s, p in rows if not _is_substrate(p)]
    dropped = [p for _s, p in rows if _is_substrate(p)]

    print(f"[replant] {args.tip} against {args.base}")
    print(f"  carrying : {len(code)} code file(s)")
    print(f"  dropping : {len(dropped)} substrate file(s)")

    at_risk = []
    for path in dropped:
        blob = _blob(args.tip, path)
        if blob and not _content_lives_elsewhere(blob, args.tip):
            at_risk.append(path)
    if at_risk:
        print(f"\n[replant] REFUSED: {len(at_risk)} dropped file(s) exist at these exact")
        print("  bytes nowhere else. Move them somewhere they survive, verify each")
        print("  landed BY NAME AND BYTES, then run again.")
        for p in at_risk[:20]:
            print(f"    {p}")

        # THE REFUSAL STAYS; WHAT CHANGES IS THAT IT STOPS BEING A DEAD END.
        # 2026-09-15: this refused eleven docs/archives files and was RIGHT by
        # its own rule -- those bytes are on no other ref. But every one of them
        # declares its own generator in its header, and regenerating all eleven
        # from the live databases reproduced them byte-identical. Nothing would
        # have been lost, and the ref scan cannot see that, because
        # reproducibility is invisible to a search through refs.
        #
        # The rule is right for AUTHORED files, which are most of them, and it
        # has already rescued real work. So it is NOT loosened here: a refusal
        # widened to let its own author through is not a refusal. What it does
        # now is name the one check that would resolve it, so the person hitting
        # this is not left guessing -- a gate that offers an exit must make the
        # exit reachable, which is a rule this house learned the hard way.
        #
        # Deliberately says LOOKS REPRODUCIBLE rather than IS. The header is a
        # claim by the file about itself, and this whole class of bug is claims
        # that stopped being true. Proving it is a regeneration and a byte
        # compare, and that is the reader's to run, not this script's to assume.
        derived = [p for p in at_risk if _declares_a_generator(args.tip, p)]
        if derived:
            print(
                f"\n  [note] {len(derived)} of these LOOK reproducible -- their own "
                "header names a\n  source they were exported from. If they are, "
                "dropping them loses nothing."
            )
            print("  This is the file's claim about itself, not a measurement. To settle it:")
            print("    regenerate from the named source, then compare bytes:")
            print("      git hash-object <regenerated>   vs   git rev-parse <tip>:<path>")
            print("  Identical for every one of them means the refusal above is moot.")
            print("  Anything else means it is load-bearing and the files must move first.")
        return 3

    if not args.apply:
        print("\n[replant] dry run. Nothing created. Re-run with --apply.")
        return 0

    if _git("rev-parse", "--verify", "--quiet", f"refs/heads/{args.into}", check=False):
        print(f"\n[replant] REFUSED: {args.into} already exists. Pick another name.")
        return 5

    base_commit = _git("rev-parse", args.base)
    carried = [p for s, p in code if s != "D"]
    removed = [p for s, p in code if s == "D"]

    with tempfile.TemporaryDirectory() as tmp:
        env = {"GIT_INDEX_FILE": str(Path(tmp) / "replant.index")}
        _git("read-tree", base_commit, env=env)
        for path in carried:
            blob = _blob(args.tip, path)
            if blob is None:
                print(f"\n[replant] FAILED: {path} unreadable on {args.tip}")
                return 4
            _git(
                "update-index",
                "--add",
                "--cacheinfo",
                f"{_mode(args.tip, path)},{blob},{path}",
                env=env,
            )
        for path in removed:
            _git("update-index", "--force-remove", path, env=env)
        tree = _git("write-tree", env=env)

    message = (
        f"Replant {args.tip} code-only onto {args.base}\n\n"
        f"Whole code difference taken in one move: {len(carried)} carried, "
        f"{len(removed)} removed, {len(dropped)} substrate file(s) dropped after "
        f"each was confirmed to exist at these bytes elsewhere.\n"
    )
    commit = _git("commit-tree", tree, "-p", base_commit, "-m", message)
    _git("update-ref", f"refs/heads/{args.into}", commit)

    # THE CHECK THAT CAN FAIL. Byte-for-byte against the tip, every carried
    # file, after the fact. A replant that quietly carried nothing would pass
    # every other check in this script.
    mismatches = []
    for path in carried:
        if _blob(args.into, path) != _blob(args.tip, path):
            mismatches.append(path)
    for path in removed:
        if _blob(args.into, path) is not None:
            mismatches.append(f"{path} (should be absent)")
    # A dropped file that also lives on the BASE is inherited, not leaked --
    # the rebuilt branch is supposed to look like the base everywhere it does
    # not carry code. The leak is the TIP's version arriving. Caught by this
    # check failing on its first real run, which is the only reason the
    # distinction got made instead of assumed.
    leaked = [p for p in dropped if _blob(args.into, p) != _blob(args.base, p)]

    print(f"\n[replant] built {args.into} at {commit[:12]}")
    print(f"  carried  : {len(carried)}   removed: {len(removed)}")
    if mismatches or leaked:
        print(f"  VERIFY FAILED: {len(mismatches)} mismatch(es), {len(leaked)} leaked")
        for p in (mismatches + leaked)[:20]:
            print(f"    {p}")
        return 6
    print(f"  verified : every carried file byte-identical to {args.tip}")
    print(f"  verified : 0 of {len(dropped)} substrate file(s) present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
