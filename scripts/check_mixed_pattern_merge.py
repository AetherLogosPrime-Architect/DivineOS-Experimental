"""Mixed-pattern-merge gate (claim ec844fcf, prereg pending).

When a PR diff contains BOTH file additions AND file deletions for the
same `src/divineos/core/<subsystem>/` directory, this gate refuses the
merge. The PR author must split the work into separate PRs — one for
the additions, one for the deletions — so structural-deletion (strip
work) gets its own focused review and can't ride alongside legitimate
template additions.

PR #230 (2026-05-02) was the named adversary for this gate: it merged
release/lite-v2 strip work into main, bundling structural deletion of
council/family subsystems with legitimate operating-loop improvements.
The deletion landed under cover of the addition's review attention.

Design choices made via council walk on ec844fcf (lenses: Beer,
Schneier, Hinton, Taleb, Yudkowsky):

- **Refuse-and-split, no override** (Taleb v1). The "magic-words" path
  (an Override-Mixed-Pattern trailer + multi-party co-sign) introduces
  ritualism risk where the words become performative. v1 keeps it
  simple: if mixed-pattern detected, the PR cannot merge until split.
  v2 may add an override mechanism if the FP-rate falsifier fires.

- **Per-subsystem granularity** (Taleb). The smallest correct cut:
  flag when the same `core/<subsystem>/` directory has both adds and
  deletes in the diff. Cross-subsystem changes (add to core/foo/,
  delete from core/bar/) are legitimate. Renames within the same
  subsystem are correctly treated as refactoring (not deletion).

- **Structural-unreachable, not detect-after** (Hinton). The gate
  blocks the merge rather than flagging it. Detect-after creates
  pressure to write magic words; structural-unreachable forces the
  split.

- **S3 sibling to multi-party-review** (Beer). Reuses the existing
  CI gate infrastructure (.github/workflows/integrity-audit.yml).
  Operators who learn one gate's shape automatically learn the
  other's.

v1 known limits (filed as pre-reg falsifiers):
- Cumulative stripping over many sequential single-pattern PRs is
  NOT caught by this per-PR gate. v2 needs a windowed cumulative
  check.
- Rename-attack evasion (rename file within subsystem to outside it,
  effectively deleting from the subsystem without `D` status) is
  partially detected (renames produce `R` status entries with old
  and new paths) but the v1 detection logic conservatively treats
  renames as non-deletion within the same subsystem. False-negative
  vector to track in pre-reg.

Invocation (from the integrity-audit CI workflow):
  python scripts/check_mixed_pattern_merge.py <base_sha> <head_sha>

Exit codes:
  0 — no mixed-pattern detected, OR no core/* changes at all
  1 — mixed-pattern detected; PR must be split
  2 — infrastructure error (conservatively blocks)
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections import defaultdict


# Match files under src/divineos/core/<subsystem>/...
# subsystem = first directory after core/, captured.
_CORE_SUBSYSTEM_PATTERN = re.compile(r"^src/divineos/core/([^/]+)/.+$")


def _git_diff_name_status(base_sha: str, head_sha: str) -> list[tuple[str, str]]:
    """Return list of (status, path) tuples from git diff --name-status.

    Status codes:
      A = added
      D = deleted
      M = modified
      R = renamed (followed by similarity score, e.g. R100)
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-status", f"{base_sha}..{head_sha}"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"[error] git diff failed: {e}", file=sys.stderr)
        return []
    except FileNotFoundError:
        print("[error] git not found", file=sys.stderr)
        return []

    entries: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        # Format: "A\tpath" or "D\tpath" or "R100\told\tnew" or "M\tpath"
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0]
        # Take the first letter of the status (R100 -> R).
        status_letter = status[0].upper()
        # For renames, the relevant path for "this is now here" is parts[2];
        # the "this used to be here" is parts[1]. v1 treats renames as
        # neither pure-add nor pure-delete (they're identity-preserving
        # within the diff scope).
        path = parts[1] if status_letter != "R" else parts[2]
        entries.append((status_letter, path))
    return entries


def _classify_subsystem_changes(
    entries: list[tuple[str, str]],
) -> dict[str, dict[str, list[str]]]:
    """Bucket file changes by subsystem and status.

    Returns:
        {subsystem_name: {"A": [paths], "D": [paths]}}

    Only A (add) and D (delete) statuses are tracked — these are the
    structural-change signals. M (modify) and R (rename) within the
    same subsystem are not counted (v1 boundary).
    """
    buckets: dict[str, dict[str, list[str]]] = defaultdict(lambda: {"A": [], "D": []})
    for status, path in entries:
        if status not in {"A", "D"}:
            continue
        match = _CORE_SUBSYSTEM_PATTERN.match(path)
        if not match:
            continue
        subsystem = match.group(1)
        buckets[subsystem][status].append(path)
    return dict(buckets)


def _detect_mixed_pattern(
    buckets: dict[str, dict[str, list[str]]],
) -> list[str]:
    """Find subsystems with BOTH additions AND deletions.

    Returns list of subsystem names that violate the gate.
    """
    return [
        subsystem
        for subsystem, status_map in buckets.items()
        if status_map["A"] and status_map["D"]
    ]


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "Usage: python scripts/check_mixed_pattern_merge.py <base_sha> <head_sha>",
            file=sys.stderr,
        )
        return 2

    base_sha, head_sha = argv[1], argv[2]

    entries = _git_diff_name_status(base_sha, head_sha)
    if not entries:
        # No diff (or git failed). Conservatively allow — the multi-party-
        # review gate is the load-bearing check; this gate only refines.
        print("[mixed-pattern-merge] No diff entries; gate does not apply.")
        return 0

    buckets = _classify_subsystem_changes(entries)
    if not buckets:
        # No core/* changes at all. Gate doesn't apply.
        print("[mixed-pattern-merge] No core/* subsystem changes; gate does not apply.")
        return 0

    violations = _detect_mixed_pattern(buckets)
    if not violations:
        print(
            "[mixed-pattern-merge] All core/* subsystem changes are "
            "single-pattern (additive XOR deletive). Gate passes."
        )
        return 0

    print(
        "[mixed-pattern-merge] BLOCKED. "
        "The following core/* subsystems have BOTH additions AND deletions "
        "in this PR:",
        file=sys.stderr,
    )
    for subsystem in sorted(violations):
        adds = buckets[subsystem]["A"]
        dels = buckets[subsystem]["D"]
        print(f"  core/{subsystem}/", file=sys.stderr)
        for path in sorted(adds):
            print(f"    + {path}", file=sys.stderr)
        for path in sorted(dels):
            print(f"    - {path}", file=sys.stderr)
    print(
        "\nMixed addition+deletion within the same core/* subsystem is the "
        "PR-#230-shape that bundles structural-deletion (strip work) with "
        "legitimate template additions. Split this PR into two — one for "
        "the additions, one for the deletions — so each gets focused "
        "review.\n"
        "\n"
        "v1: no override mechanism. If you have a legitimate refactor that "
        "genuinely requires both add+delete in one subsystem, split the "
        "PR. The split-tax is the tradeoff that keeps the gate simple.\n"
        "\n"
        "Filed as claim ec844fcf, design via council walk + Grok review.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
