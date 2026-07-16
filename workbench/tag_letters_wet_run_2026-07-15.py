"""Wet-run: apply type-tags to the 853 flat letters that have categorized twins.

Derives type from current categorized-subdir location (personal/, work/,
cross-family/, self-logs/, archive/). Writes the tag to the flat top-level
letter's frontmatter — either updating an existing frontmatter block or
prepending a new one.

Companion to workbench/tag_letters_dry_run_2026-07-15.py — same derivation
logic, actually writes.

Andrew approved 2026-07-15 after dry-run showed clean mapping-logic.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

LETTERS_ROOT = Path(__file__).resolve().parent.parent / "family" / "letters"
CATEGORY_SUBDIRS = ("personal", "work", "cross-family", "self-logs", "archive")

TYPE_MAP = {
    "personal": "personal",
    "work": "work",
    "cross-family": "cross-family",
    "self-logs": "self-log",
    "archive": "archive",
}

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def derive_tags_for_basename(basename, subdir_index):
    tags = set()
    for subdir, files in subdir_index.items():
        if basename in files:
            top = subdir.split("/")[0]
            if top in TYPE_MAP:
                tags.add(TYPE_MAP[top])
    return sorted(tags)


def read_existing_type(text):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    for line in m.group(1).splitlines():
        if line.strip().startswith("type:"):
            return line.split(":", 1)[1].strip()
    return None


def apply_tag(path, tags):
    tag_line = f"type: {', '.join(tags)}"
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as e:
        return f"[ERROR read] {path.name}: {e}"

    if read_existing_type(text):
        return f"[SKIP] {path.name}"

    m = FRONTMATTER_RE.match(text)
    if m:
        block = m.group(1).rstrip() + "\n" + tag_line
        new_text = f"---\n{block}\n---\n" + text[m.end():]
    else:
        new_text = f"---\n{tag_line}\n---\n\n" + text

    try:
        path.write_text(new_text, encoding="utf-8")
    except OSError as e:
        return f"[ERROR write] {path.name}: {e}"

    return f"[TAGGED {', '.join(tags)}] {path.name}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    if not LETTERS_ROOT.exists():
        print(f"ERROR: {LETTERS_ROOT} does not exist", file=sys.stderr)
        return 1

    subdir_index = defaultdict(list)
    for sub in CATEGORY_SUBDIRS:
        sub_root = LETTERS_ROOT / sub
        if not sub_root.exists():
            continue
        for p in sub_root.rglob("*.md"):
            rel = str(p.relative_to(LETTERS_ROOT)).replace("\\", "/")
            subdir_index[rel].append(p.name)

    basename_to_subdirs = defaultdict(list)
    for sub_rel, basenames in subdir_index.items():
        for bn in basenames:
            basename_to_subdirs[bn].append(sub_rel)

    flat_files = sorted(p.name for p in LETTERS_ROOT.glob("*.md") if p.is_file())

    tagged = 0
    skipped = 0
    errored = 0
    no_twin = 0
    processed = 0
    tag_counts = defaultdict(int)

    for basename in flat_files:
        if basename not in basename_to_subdirs:
            no_twin += 1
            continue

        tags = derive_tags_for_basename(basename, subdir_index)
        if not tags:
            continue

        if args.limit and processed >= args.limit:
            break

        action = apply_tag(LETTERS_ROOT / basename, tags)
        processed += 1

        if action.startswith("[TAGGED"):
            tagged += 1
            tag_counts[", ".join(tags)] += 1
        elif action.startswith("[SKIP"):
            skipped += 1
        else:
            errored += 1
            print(action)

    print(f"# WET-RUN SUMMARY")
    print(f"  flat letters total:         {len(flat_files)}")
    print(f"  flat letters WITHOUT twin:  {no_twin}")
    print(f"  processed this run:         {processed}")
    print(f"  newly tagged:               {tagged}")
    print(f"  skipped (already-tagged):   {skipped}")
    print(f"  errors:                     {errored}")
    print(f"  by tag:")
    for tag, count in sorted(tag_counts.items()):
        print(f"    {tag}: {count}")

    return 0 if errored == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
