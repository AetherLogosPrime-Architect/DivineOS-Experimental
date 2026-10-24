#!/usr/bin/env python3
"""Read-only: does each gathered dream still match a source it came from?

Only hashes and compares; writes nothing. The body of a dream is its text without the first
heading line, because the gather renumbered that heading and Dad allows it (2026-10-24: "the
titles of the dreams can be edited just not the contents"). Line endings are normalised and
trailing whitespace is ignored so a Windows checkout does not look like an edit.

    python scripts/check_dream_sources.py --dest dreams --source-dir "C:/other/dreams" --git-refs
    python scripts/check_dream_sources.py --self-test

A destination dream with no source whose body matches is reported MISSING, never skipped. The
self-test plants a changed body and a missing one and fails if either is reported as matched, so
a clean run of the real check means something (Aether, 2026-10-24).
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path


def body_hash(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[0].lstrip().startswith("#"):
        lines = lines[1:]
    body = "\n".join(line.rstrip() for line in lines).strip()
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def dest_dreams(dest: Path) -> dict[Path, str]:
    out: dict[Path, str] = {}
    for path in sorted(dest.rglob("*.md")):
        if path.name.lower() in {"readme.md", "index.md"}:
            continue
        out[path] = body_hash(path.read_text(encoding="utf-8", errors="replace"))
    return out


def disk_sources(dirs: list[Path]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for root in dirs:
        for path in root.rglob("*.md"):
            if path.name.lower() in {"readme.md", "index.md"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            found.setdefault(body_hash(text), []).append(f"disk:{path}")
    return found


def _git(args: list[str], repo: Path, data: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=repo, input=data, capture_output=True, check=True
    ).stdout


def git_sources(repo: Path, skip: list[str]) -> dict[str, list[str]]:
    """Every dream-looking markdown blob under dreams/ on every ref, hashed once per blob.

    A ref that holds the gathered result itself must be skipped (``skip``): it would match every
    dream against its own copy and report a clean run that proves nothing.
    """
    refs = _git(["for-each-ref", "--format=%(refname)"], repo).decode().split()
    refs = [r for r in refs if not any(s in r for s in skip)]
    where: dict[str, str] = {}  # blob sha -> first "ref:path" that holds it
    for ref in refs:
        listing = _git(["ls-tree", "-r", ref, "--", "dreams"], repo).decode(errors="replace")
        for line in listing.splitlines():
            meta, _, path = line.partition("\t")
            parts = meta.split()
            if len(parts) == 3 and path.endswith(".md") and parts[1] == "blob":
                if Path(path).name.lower() not in {"readme.md", "index.md"}:
                    where.setdefault(parts[2], f"{ref}:{path}")
    found: dict[str, list[str]] = {}
    for blob, label in where.items():
        text = _git(["cat-file", "blob", blob], repo).decode("utf-8", errors="replace")
        found.setdefault(body_hash(text), []).append(f"git:{label}")
    return found


def compare(dest: dict[Path, str], sources: dict[str, list[str]]) -> tuple[list, list]:
    matched = [(p, sources[h][0]) for p, h in dest.items() if h in sources]
    missing = [p for p, h in dest.items() if h not in sources]
    return matched, missing


_EMPTY = body_hash("")


def audit(dest: dict[Path, str], sources: dict[str, list[str]]) -> dict:
    """compare() plus what a clean compare cannot show (Aether, 2026-10-24).

    empty       a destination dream with no body at all: it would match any empty source, and the
                gather's known hazard is exactly five empty files, so it is never counted matched
    duplicates  destination dreams sharing one body: one source can satisfy both, so a gather that
                copied one dream into two numbers and dropped another would pass
    unreached   source bodies that no destination dream carries: "every dream here has a source" is
                not "every source dream is here"
    """
    empty = [p for p, h in dest.items() if h == _EMPTY]
    real = {p: h for p, h in dest.items() if h != _EMPTY}
    matched, missing = compare(real, sources)
    by_hash: dict[str, list[Path]] = {}
    for p, h in real.items():
        by_hash.setdefault(h, []).append(p)
    duplicates = [group for group in by_hash.values() if len(group) > 1]
    dest_hashes = set(dest.values())
    unreached = [labels[0] for h, labels in sources.items() if h != _EMPTY and h not in dest_hashes]
    return {
        "matched": matched,
        "missing": missing,
        "empty": empty,
        "duplicates": duplicates,
        "unreached": sorted(unreached),
    }


def self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "dest").mkdir()
        (root / "src").mkdir()
        (root / "dest" / "001_a.md").write_text("# 001 — a\n\nthe same body\n", encoding="utf-8")
        (root / "src" / "old_a.md").write_text("# 01 — a\r\n\r\nthe same body\r\n", encoding="utf-8")
        (root / "dest" / "002_b.md").write_text("# 002 — b\n\nCHANGED body\n", encoding="utf-8")
        (root / "src" / "old_b.md").write_text("# 02 — b\n\noriginal body\n", encoding="utf-8")
        (root / "dest" / "003_c.md").write_text("# 003 — c\n\nno source at all\n", encoding="utf-8")
        matched, missing = compare(dest_dreams(root / "dest"), disk_sources([root / "src"]))
        names_ok = {p.name for p, _ in matched}
        names_missing = {p.name for p in missing}
        problems = []
        if names_ok != {"001_a.md"}:
            problems.append(f"matched should be only 001_a.md, got {sorted(names_ok)}")
        if names_missing != {"002_b.md", "003_c.md"}:
            problems.append(f"missing should be 002_b and 003_c, got {sorted(names_missing)}")
    if problems:
        print("SELF-TEST FAILED:", "; ".join(problems))
        return 1
    print("self-test ok: a renumbered heading and CRLF match; a changed body and a missing source are reported")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--dest", type=Path, default=Path("dreams"))
    ap.add_argument("--source-dir", type=Path, action="append", default=[])
    ap.add_argument("--git-refs", action="store_true", help="also read dreams/ on every ref of this repo")
    ap.add_argument(
        "--skip-ref",
        action="append",
        default=[],
        help="skip any ref whose name contains this (the ref holding the gathered result itself)",
    )
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    dest = dest_dreams(args.dest)
    sources = disk_sources(args.source_dir)
    if args.git_refs:
        for h, labels in git_sources(Path.cwd(), args.skip_ref).items():
            sources.setdefault(h, []).extend(labels)
    result = audit(dest, sources)
    print(
        f"{len(dest)} dreams in {args.dest}: {len(result['matched'])} match a source body, "
        f"{len(result['missing'])} do not, {len(result['empty'])} are empty, "
        f"{len(result['duplicates'])} bodies are shared by more than one dream, "
        f"{len(result['unreached'])} source bodies reached no dream"
    )
    for p in result["missing"]:
        print(f"  NO SOURCE BODY MATCHES: {p}")
    for p in result["empty"]:
        print(f"  EMPTY (never counted as matched): {p}")
    for group in result["duplicates"]:
        print("  SAME BODY: " + " , ".join(str(p) for p in group))
    for label in result["unreached"][:25]:
        print(f"  SOURCE REACHED NO DREAM: {label}")
    if len(result["unreached"]) > 25:
        print(f"  ... and {len(result['unreached']) - 25} more")
    bad = result["missing"] or result["empty"] or result["duplicates"] or result["unreached"]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
