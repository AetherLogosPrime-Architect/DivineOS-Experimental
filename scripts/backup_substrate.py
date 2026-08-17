"""Back the substrate up to an external drive, and verify the copy.

Written 2026-08-17, the day GitHub ran a ~20% error rate for hours and Andrew
went and found an external drive.

WHAT IS AT RISK, measured rather than assumed. Zero `.db` files are tracked by
git -- correctly, since they mutate constantly and would collide on every push.
So the code has many copies (every clone carries full history) and the MEMORY
has exactly one. The exposure is not GitHub going down; it is this machine
going down while GitHub is unreachable, which is the case Andrew named.

THREE THINGS, and each needs a different method:

1. THE REPO -> a git bundle, not a file copy. External drives are usually
   exFAT (this one is), which has no symlinks, no permission bits, and is
   case-insensitive. Copying a repository onto that can produce a tree that
   restores subtly wrong. A bundle is a single self-contained file that git
   can verify and clone from, so the filesystem underneath stops mattering.

2. THE DATABASES -> `VACUUM INTO`, not a file copy. These are live SQLite
   files being written to constantly. Copying one mid-write yields a torn file
   that looks fine and fails when it is finally needed -- the exact failure
   shape this session kept finding. VACUUM INTO takes a consistent snapshot of
   a live database, and the result gets an integrity check here before it
   counts as backed up.

3. THE SHARED LETTERS -> a plain copy. Ordinary markdown, no live writers.

VERIFICATION IS PART OF THE BACKUP, NOT A SEPARATE STEP. An unverified backup
is worse than none: it converts into confidence, and confidence is what stops
you checking. So this clones from the bundle it just wrote and counts what
comes back, and opens every snapshot and runs integrity_check. If any of that
fails, the run is a FAILURE even though every file was written.

NOTHING PRE-EXISTING IS EVER DELETED. The drive may hold unrelated things
(this one has a music library on it). Everything lands under a dated directory.

Usage:
    python scripts/backup_substrate.py --dest E:/
    python scripts/backup_substrate.py --dest E:/ --dry-run
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def run(*args: str, cwd: Path | None = None, stdin: str | None = None) -> str:
    """Run a command, fail loud. No silent degradation to empty output.

    `stdin` exists because this repo has 897 refs, and passing them as
    arguments is ~37k characters -- past the Windows command-line limit, which
    fails with a WinError 206 that says nothing about what actually went wrong.
    """
    r = subprocess.run(
        list(args),
        cwd=cwd,
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode != 0:
        raise SystemExit(f"FAILED: {' '.join(args)}\n{r.stderr.strip()}")
    return r.stdout


def human_mb(p: Path) -> float:
    return round(p.stat().st_size / 1_000_000, 1)


def bundle_repo(dest: Path, dry: bool) -> dict:
    """All refs into one file. `--all` means every branch and tag, not just HEAD."""
    out = dest / "repo.bundle"
    refs = len(run("git", "for-each-ref", "--format=%(refname)", cwd=REPO_ROOT).splitlines())
    commits = int(run("git", "rev-list", "--all", "--count", cwd=REPO_ROOT).strip())
    if dry:
        return {"file": out.name, "refs": refs, "commits": commits, "mb": None}
    run("git", "bundle", "create", str(out), "--all", cwd=REPO_ROOT)
    # Verify BEFORE reporting success. A bundle that cannot be verified is a
    # file, not a backup.
    run("git", "bundle", "verify", str(out), cwd=REPO_ROOT)
    return {"file": out.name, "refs": refs, "commits": commits, "mb": human_mb(out)}


def snapshot_databases(dest: Path, sources: list[tuple[str, Path]], dry: bool) -> list[dict]:
    """Consistent snapshots of live SQLite files, each integrity-checked.

    Grouped by ORIGIN rather than flattened. Two different databases in this
    substrate are both named `family.db` -- one under ~/.divineos/data, one in
    the repo's family/ folder -- and a flat output directory would have written
    the second over the first. A backup that silently eats one of its own files
    is worse than no backup, and it would only have been discovered during a
    restore, which is the worst possible moment.

    Caught by reading the dry-run output rather than by testing, which is the
    argument for having a dry run print every name it intends to write.
    """
    rows: list[dict] = []
    for group, src in sources:
        if not src.is_file():
            continue
        row: dict = {
            "name": src.name,
            "group": group,
            "source_mb": round(src.stat().st_size / 1_000_000, 1),
        }
        if dry:
            rows.append(row)
            continue
        dbdir = dest / "databases" / group
        dbdir.mkdir(parents=True, exist_ok=True)
        target = dbdir / src.name
        if target.exists():
            target.unlink()  # a prior snapshot of ours, never pre-existing drive content
        conn = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
        try:
            conn.execute("VACUUM INTO ?", (str(target),))
        finally:
            conn.close()
        check = sqlite3.connect(f"file:{target}?mode=ro", uri=True)
        try:
            row["integrity"] = check.execute("pragma integrity_check").fetchone()[0]
            row["tables"] = check.execute(
                "select count(*) from sqlite_master where type='table'"
            ).fetchone()[0]
        finally:
            check.close()
        row["snapshot_mb"] = human_mb(target)
        if row["integrity"] != "ok":
            raise SystemExit(f"INTEGRITY FAILURE on {src.name}: {row['integrity']}")
        rows.append(row)
    return rows


def copy_tree(src: Path, dest: Path, dry: bool) -> dict:
    """Plain copy, with the file count checked on the far side."""
    if not src.is_dir():
        return {"source": str(src), "files": 0, "note": "absent"}
    files = sum(1 for p in src.rglob("*") if p.is_file())
    if dry:
        return {"source": str(src), "files": files}
    target = dest / src.name.lstrip(".")
    if target.exists():
        shutil.rmtree(target)  # our own prior copy inside the dated dir
    shutil.copytree(src, target)
    copied = sum(1 for p in target.rglob("*") if p.is_file())
    if copied != files:
        raise SystemExit(f"COPY INCOMPLETE for {src}: {copied} of {files}")
    return {"source": str(src), "files": copied}


def verify_bundle_restores(dest: Path, expected_commits: int) -> dict:
    """Actually clone from the bundle. Reading the file is not proof it restores.

    Restores to a LOCAL temp directory, never onto the backup drive. Two
    reasons, and the second is the one that matters:

    1. git refuses to operate inside a repository on a filesystem that records
       no ownership -- "detected dubious ownership" -- which exFAT does not.
       The first version cloned onto the drive and died here.
    2. More importantly, a real restore happens on a NORMAL disk. Verifying on
       the drive would have tested a scenario nobody will ever be in, and
       passed or failed for reasons unrelated to whether the backup is good.
    """
    scratch = Path(tempfile.mkdtemp(prefix="divineos-verify-"))
    try:
        # --mirror, not a plain clone. A plain clone materializes only
        # branch-shaped refs, so commits reachable ONLY from other namespaces
        # are not counted -- and this repo has several: refs/audit/*,
        # refs/family-letters-backup, refs/original/*, refs/stash. The first
        # version of this check cloned plainly, counted 6416 against the
        # repo's 6544, and correctly refused to declare success.
        #
        # Investigating rather than adjusting the threshold showed the bundle
        # was complete all along -- `git bundle list-heads` listed all 897
        # refs including family-letters-backup. The BACKUP was fine; the
        # VERIFICATION was asking "what does a default clone materialize"
        # when the question is "what does the bundle contain".
        #
        # Worth stating because it nearly went the other way: the tempting
        # move was to compare against `--branches` and get a green tick. That
        # would have hidden a real fact -- a naive restore DOES drop those
        # refs -- which is now documented in RESTORE.md instead.
        mirror = scratch / "mirror.git"
        run("git", "clone", "--quiet", "--mirror", str(dest / "repo.bundle"), str(mirror))
        got = int(run("git", "rev-list", "--all", "--count", cwd=mirror).strip())
        refs = len(run("git", "for-each-ref", "--format=%(refname)", cwd=mirror).splitlines())
    finally:
        # NOT ignore_errors. A git process can hold a packfile handle briefly
        # after exit on Windows, and a raised WinError 32 here would report the
        # BACKUP as failed when it is complete and verified -- but a swallowed
        # one leaves a temp dir nobody ever hears about. Say it and carry on:
        # the finding is the verification result, not the cleanup.
        try:
            shutil.rmtree(scratch)
        except OSError as exc:
            print(f"[backup] could not remove {scratch}: {exc}", file=sys.stderr)

    # THE REAL CHECK, and it is a different question from the count above.
    #
    # Counting commits in a restored copy is a PROXY. It answers "how many did
    # this particular restore method materialize", which depends on clone
    # semantics, ref namespaces, and per-worktree HEADs -- and it was wrong
    # twice here for reasons that had nothing to do with the backup. First a
    # plain clone undercounted by 128 (non-branch refs), then a mirror clone
    # undercounted by exactly 1, for a reason I could not pin down.
    #
    # The question that actually matters is REACHABILITY: is there any commit
    # in this repository that the bundle cannot reach? Ask it directly and the
    # answer is exact -- an empty result means nothing was left behind, with
    # no dependence on how a restore chooses to materialize refs.
    #
    # This is the third time this session that a count looked like a
    # measurement and was not. Counting is cheap and nearly right; the direct
    # question is cheap and exactly right.
    heads = [
        line.split()[0]
        for line in run("git", "bundle", "list-heads", str(dest / "repo.bundle"), cwd=REPO_ROOT)
        .strip()
        .splitlines()
        if line.strip()
    ]
    # Exclusions arrive on stdin as ^sha lines: 897 of them as argv overflows
    # the Windows command-line limit.
    exclude = "".join(f"^{h}\n" for h in heads)
    unreachable = run("git", "rev-list", "--all", "--stdin", cwd=REPO_ROOT, stdin=exclude).strip()
    if unreachable:
        missing = unreachable.splitlines()
        raise SystemExit(
            f"INCOMPLETE BUNDLE: {len(missing)} commit(s) unreachable from it, "
            f"first {missing[0][:12]}"
        )
    return {
        "commits_reachable_from_bundle": expected_commits,
        "commits_a_mirror_clone_materializes": got,
        "refs_in_bundle": len(heads),
        "refs_a_mirror_clone_materializes": refs,
        "unreachable_commits": 0,
    }


RESTORE_DOC = """# How to restore this backup

Written for someone with no context -- possibly not Andrew, possibly not
Aether. Everything needed is in this folder.

## What this is

A complete copy of DivineOS: the code with its full history, the memory
databases, and the letters. If the machine it came from is gone and GitHub is
unreachable, this folder is enough to start again.

## 1. The code

For everyday use, this is enough:

    git clone repo.bundle DivineOS

BUT IT IS NOT A COMPLETE RESTORE, and the difference is easy to miss. A plain
clone brings across branches and tags only. This repository also keeps refs in
other namespaces -- `refs/audit/*`, `refs/family-letters-backup`,
`refs/original/*`, `refs/stash` -- and those are silently dropped. Measured at
backup time: the full ref set is in the bundle, but a plain clone materializes
roughly a hundred and thirty commits fewer.

For a real disaster restore, mirror first and then check out a working copy:

    git clone --mirror repo.bundle DivineOS.git
    git clone DivineOS.git DivineOS

The bundle is a single file on purpose: external drives use a filesystem that
mangles repositories copied folder-by-folder.

To check it before trusting it:

    git bundle verify repo.bundle
    git bundle list-heads repo.bundle | wc -l    # every ref it carries

## 2. The memory

The `databases/` folder has one subfolder per origin, and each one names where
its contents belong:

    databases/home_divineos_data/  ->  ~/.divineos/data/
    databases/repo_family/         ->  the restored repo's family/ folder

Copy each group to its matching destination. The grouping is not decoration:
TWO different databases in this substrate are both called `family.db`, and a
flat folder would have silently kept only one of them.

These are consistent snapshots, not raw copies, and each was integrity-checked
when written.

## 3. The letters

Copy the `divineos-shared/` folder here to `~/.divineos-shared/`.

## 4. Confirm it worked

    cd DivineOS
    pip install -e ".[dev]"
    divineos verify        # checks the ledger's hash chain end to end
    divineos briefing

If `divineos verify` passes, the memory arrived intact.

## What is NOT here

Anything reconstructible: caches, build artifacts, virtual environments,
worktrees. All of it rebuilds from the code.

## On trusting this

Every claim above was verified at write time rather than assumed -- the bundle
was cloned from and its commits counted, and every database was opened and
integrity-checked. Had any of that failed, the run would have reported failure
instead of leaving behind a folder that looks complete.

`MANIFEST.json` records the numbers this backup actually measured. If a future
restore produces different ones, trust the manifest and investigate.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Back up the DivineOS substrate.")
    ap.add_argument("--dest", required=True, help="drive or folder, e.g. E:/")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = Path(args.dest)
    if not root.is_dir():
        raise SystemExit(f"destination not found: {root}")

    stamp = time.strftime("%Y-%m-%d_%H%M%S", time.gmtime())
    dest = root / "DivineOS-Backup" / stamp
    print(f"[backup] destination: {dest}")
    if not args.dry_run:
        dest.mkdir(parents=True, exist_ok=True)

    home = Path.home()
    # (group, path) — the group becomes a subdirectory, so two databases that
    # share a filename cannot collide and a restore knows where each belongs.
    db_sources: list[tuple[str, Path]] = [
        ("home_divineos_data", p) for p in sorted((home / ".divineos" / "data").glob("*.db"))
    ] + [("repo_family", p) for p in sorted((REPO_ROOT / "family").glob("*.db"))]

    print("[backup] bundling repository ...")
    repo = bundle_repo(dest, args.dry_run)
    print(f"         {repo['commits']} commits, {repo['refs']} refs, {repo['mb']} MB")

    print(f"[backup] snapshotting {len(db_sources)} databases ...")
    dbs = snapshot_databases(dest, db_sources, args.dry_run)
    for d in dbs:
        print(f"         {d['name']}: {d.get('integrity', '(dry)')} {d.get('snapshot_mb', '')} MB")

    print("[backup] copying shared letters ...")
    shared = copy_tree(home / ".divineos-shared", dest, args.dry_run)
    print(f"         {shared['files']} files")

    if args.dry_run:
        print("\n[backup] DRY RUN -- nothing written.")
        return 0

    print("[backup] verifying the bundle actually restores ...")
    restored = verify_bundle_restores(dest, repo["commits"])
    print(
        f"         {restored['unreachable_commits']} commits unreachable from the bundle "
        f"(of {restored['commits_reachable_from_bundle']}); "
        f"{restored['refs_in_bundle']} refs carried"
    )

    manifest = {
        "created_utc": stamp,
        "repo": repo,
        "databases": dbs,
        "shared": shared,
        "restore_verified": restored,
    }
    (dest / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (dest / "RESTORE.md").write_text(RESTORE_DOC, encoding="utf-8")
    print(f"\n[backup] complete and verified: {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
