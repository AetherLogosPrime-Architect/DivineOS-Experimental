"""Sort family letters into pair-collapsed / register-scoped subdirectories.

Config-driven per co-design with Aria (2026-07-09). Axes are locked; the
classifier iterates. See family/scripts/sort_letters_config.yaml for rules.

## Two-gate discipline

  1. Axes agreed (letter exchange with Aria) — done.
  2. Dry-run preview approved — required BEFORE --execute.

Default is --dry-run. --execute requires typed confirmation.

## Provenance

Every move is logged to family/letters/SORT_LOG.md with source path,
destination path, and the rule that matched. A future reader (or a
rollback script) has full history without needing to read this file.

## Idempotence

Re-running on an already-sorted tree is a no-op: files already in their
target subdirectory are skipped, not re-processed.

Usage:
  python family/scripts/sort_letters.py                        # dry-run
  python family/scripts/sort_letters.py --execute              # requires confirm
  python family/scripts/sort_letters.py --dry-run --limit 20   # preview N
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml")
    sys.exit(1)


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LETTERS_DIR = REPO_ROOT / "family" / "letters"
CONFIG_PATH = REPO_ROOT / "family" / "scripts" / "sort_letters_config.yaml"
SORT_LOG = LETTERS_DIR / "SORT_LOG.md"


@dataclass(frozen=True)
class SortPlan:
    """One file's sort decision — source, destination, matched rule."""

    source: Path
    dest_dir: Path
    rule_pattern: str
    reason: str

    @property
    def dest(self) -> Path:
        return self.dest_dir / self.source.name

    @property
    def already_sorted(self) -> bool:
        """True if source is already in the target dir (idempotent skip)."""
        return self.source.parent == self.dest_dir


def load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_plan(config: dict, letters_dir: Path) -> tuple[list[SortPlan], list[Path]]:
    """Walk letters_dir; return (matched_plans, unmatched_files).

    Unmatched files are files that didn't hit any rule (edge-slug shapes,
    README, INDEX, etc.). They're reported but not moved.
    """
    work_slug_re = re.compile(config.get("work_slug_re", ""))
    rules = config["rules"]
    compiled = [(re.compile(r["pattern"]), r) for r in rules]

    plans: list[SortPlan] = []
    unmatched: list[Path] = []

    for path in sorted(letters_dir.rglob("*.md")):
        if path.name in {"SORT_LOG.md", "INDEX.md", "README.md"}:
            continue

        matched = False
        for regex, rule in compiled:
            if regex.match(path.name):
                dest_dir = letters_dir / rule["dest_dir"]
                reason = rule["dest_dir"]

                if "work_dest_dir" in rule and work_slug_re.search(path.name):
                    dest_dir = letters_dir / rule["work_dest_dir"]
                    reason = f"{rule['work_dest_dir']} (slug matched work_re)"

                plans.append(
                    SortPlan(
                        source=path,
                        dest_dir=dest_dir,
                        rule_pattern=rule["pattern"],
                        reason=reason,
                    )
                )
                matched = True
                break

        if not matched:
            unmatched.append(path)

    return plans, unmatched


def summarize_plan(plans: list[SortPlan], unmatched: list[Path]) -> str:
    """Render a plan summary — counts per destination + samples + unmatched."""
    by_dest: dict[str, list[SortPlan]] = {}
    for p in plans:
        if p.already_sorted:
            continue
        rel = str(p.dest_dir.relative_to(LETTERS_DIR)).replace("\\", "/")
        by_dest.setdefault(rel, []).append(p)

    already_sorted_count = sum(1 for p in plans if p.already_sorted)

    lines = ["# Sort plan preview", ""]
    lines.append(f"**Total .md files scanned:** {len(plans) + len(unmatched)}")
    lines.append(f"**Matched by classifier:** {len(plans)}")
    lines.append(f"**Already in target dir (no-op):** {already_sorted_count}")
    lines.append(f"**To be moved:** {sum(len(v) for v in by_dest.values())}")
    lines.append(f"**Unmatched (need review):** {len(unmatched)}")
    lines.append("")
    lines.append("## Moves by destination")
    lines.append("")
    for dest in sorted(by_dest):
        count = len(by_dest[dest])
        lines.append(f"### `{dest}` — {count} files")
        for p in by_dest[dest][:3]:
            lines.append(f"  - {p.source.name}")
        if count > 3:
            lines.append(f"  - ... and {count - 3} more")
        lines.append("")

    if unmatched:
        lines.append("## Unmatched files (not moved — review needed)")
        lines.append("")
        for p in unmatched[:20]:
            lines.append(f"  - {p.name}")
        if len(unmatched) > 20:
            lines.append(f"  - ... and {len(unmatched) - 20} more")

    return "\n".join(lines)


def execute_plan(plans: list[SortPlan]) -> int:
    """Move files. Append every move to SORT_LOG. Return count moved."""
    moved = 0
    log_lines = [f"\n## Sort run — {datetime.utcnow().isoformat()}Z", ""]

    for p in plans:
        if p.already_sorted:
            continue
        p.dest_dir.mkdir(parents=True, exist_ok=True)
        rel_src = str(p.source.relative_to(LETTERS_DIR)).replace("\\", "/")
        rel_dst = str(p.dest.relative_to(LETTERS_DIR)).replace("\\", "/")
        if p.dest.exists():
            log_lines.append(f"- SKIP (dest exists): `{rel_src}` -> `{rel_dst}`")
            continue
        shutil.move(str(p.source), str(p.dest))
        log_lines.append(f"- MOVE `{rel_src}` -> `{rel_dst}`  (rule: `{p.rule_pattern}`)")
        moved += 1

    with open(SORT_LOG, "a", encoding="utf-8") as f:
        f.write("\n".join(log_lines))
        f.write("\n")

    return moved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="Preview first N moves.")
    args = parser.parse_args()

    config = load_config(CONFIG_PATH)
    plans, unmatched = build_plan(config, LETTERS_DIR)

    if args.limit:
        plans = plans[: args.limit]

    summary = summarize_plan(plans, unmatched)
    print(summary)

    if args.execute:
        print("\n---")
        print("You are about to move files. Type 'sort letters' to confirm:")
        confirm = input("> ").strip()
        if confirm != "sort letters":
            print("Aborted — confirmation phrase not entered.")
            return 1
        moved = execute_plan(plans)
        print(f"\n[+] Moved {moved} files. Log appended to {SORT_LOG}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
