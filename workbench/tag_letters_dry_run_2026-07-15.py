"""Dry-run: derive letter-type tags from current categorized-subdir location.

For each letter in family/letters/personal/, family/letters/work/, or
family/letters/cross-family/, find its flat top-level twin (same basename)
and report the type-tag that would be assigned.

Type derivation rule:
  personal/*  -> type: personal
  work/*      -> type: work
  cross-family/* -> type: cross-family
  self-logs/* -> type: self-log
  archive/*   -> type: archive

Handles multi-tag case: if the same basename appears in multiple
categorized subdirs, all tags accrue (comma-separated).

DRY RUN — reads only, writes nothing. Prints a proposed action per
letter, and a summary at the end. Sanity-check the output before
approving the wet run.

Usage:
    python workbench/tag_letters_dry_run_2026-07-15.py [--limit N]
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

LETTERS_ROOT = Path(__file__).resolve().parent.parent / "family" / "letters"
CATEGORY_SUBDIRS = ("personal", "work", "cross-family", "self-logs", "archive")

# type-derivation mapping
TYPE_MAP = {
    "personal": "personal",
    "work": "work",
    "cross-family": "cross-family",
    "self-logs": "self-log",
    "archive": "archive",
}

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def read_existing_type(path: Path) -> str | None:
    """Return existing `type:` value in frontmatter, or None if absent."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    for line in m.group(1).splitlines():
        if line.strip().startswith("type:"):
            return line.split(":", 1)[1].strip()
    return None


def derive_tags_for_basename(basename: str, subdir_index: dict[str, list[str]]) -> list[str]:
    """Return sorted list of derived tags for a filename appearing in the
    categorized subdirs."""
    tags = set()
    for subdir, files in subdir_index.items():
        if basename in files:
            top = subdir.split("/")[0]
            if top in TYPE_MAP:
                tags.add(TYPE_MAP[top])
    return sorted(tags)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max number of letters to report on (default: 10). Use 0 for all.",
    )
    args = parser.parse_args()

    if not LETTERS_ROOT.exists():
        print(f"ERROR: {LETTERS_ROOT} does not exist", file=sys.stderr)
        return 1

    # Index every file in every categorized subdir (basename -> list of subdir paths).
    subdir_index: dict[str, list[str]] = defaultdict(list)
    for sub in CATEGORY_SUBDIRS:
        sub_root = LETTERS_ROOT / sub
        if not sub_root.exists():
            continue
        for p in sub_root.rglob("*.md"):
            rel = p.relative_to(LETTERS_ROOT)
            # rel like: personal/aether-aria/foo.md
            key = str(rel).replace("\\", "/")
            subdir_index[key].append(p.name)

    # Flat top-level letters (not in any category subdir)
    flat_files = sorted(
        p.name for p in LETTERS_ROOT.glob("*.md") if p.is_file()
    )

    # Reverse index: basename -> list of relative subdir paths where it lives
    basename_to_subdirs: dict[str, list[str]] = defaultdict(list)
    for sub_rel, basenames in subdir_index.items():
        for bn in basenames:
            basename_to_subdirs[bn].append(sub_rel)

    reported = 0
    would_tag = 0
    already_tagged = 0
    no_subdir_copy = 0
    all_flat = len(flat_files)

    print(f"# DRY RUN — flat letters: {all_flat}, category-indexed basenames: {len(basename_to_subdirs)}\n")

    for basename in flat_files:
        flat_path = LETTERS_ROOT / basename

        if basename not in basename_to_subdirs:
            no_subdir_copy += 1
            continue

        subdir_paths = basename_to_subdirs[basename]
        tags = derive_tags_for_basename(basename, subdir_index)

        if not tags:
            continue

        existing = read_existing_type(flat_path)
        if existing:
            already_tagged += 1
            if args.limit and reported >= args.limit:
                continue
            print(f"[SKIP: already tagged '{existing}'] {basename}")
            reported += 1
            continue

        would_tag += 1
        if args.limit and reported >= args.limit:
            continue

        tag_str = ", ".join(tags)
        subdirs_str = ", ".join(subdir_paths)
        print(f"[WOULD TAG] {basename}")
        print(f"    type: {tag_str}")
        print(f"    (derived from: {subdirs_str})")
        reported += 1

    print(f"\n# SUMMARY")
    print(f"  flat letters total:               {all_flat}")
    print(f"  flat letters with subdir twin:    {all_flat - no_subdir_copy}")
    print(f"  flat letters WITHOUT subdir twin: {no_subdir_copy}")
    print(f"  would newly tag:                  {would_tag}")
    print(f"  already have a type tag:          {already_tagged}")
    print(f"  reported above (limit={args.limit}): {reported}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
