"""Retroactive anchor + internal-verification pass for anchor-less external CONFIRMs.

Per task #50 — Path 1: full rigor. The OS preaches "verify, don't trust"; the
audit trail must be consistent with that value. This script discharges the
92-record architectural debt by:

  (D) ANCHOR SYNTHESIS — mechanical:
      For each anchor-less CONFIRM, look up the PR's merge commit, compute
      the merged state's tree-hash, append it to the finding's description
      with a provenance marker.

  (C) INTERNAL RE-VERIFICATION — cognitive:
      For each unique PR, attach an "internal-verification: aether-confirmed"
      or "aether-flagged" stamp with a one-paragraph basis.

Provenance markers ensure the trail stays honest:
  - "Tree <hash> [synthesized-retroactively-from-merge-commit on YYYY-MM-DD]"
  - "internal-verification: aether-confirmed YYYY-MM-DD — <basis>"

Per Aletheia 2026-06-02 cross-vantage correction: patch-id is NOT cross-
vantage stable (context lines / git config / line endings). So this script
records the tree-hash only — that's the load-bearing anchor. patch-id can be
computed in a follow-up pass if needed, with explicit vantage-warning.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass

from divineos.core.watchmen.store import list_findings


@dataclass
class AnchorlessConfirm:
    finding_id: str
    actor: str
    title: str
    pr_num: int
    description: str


def find_anchorless_confirms(pr_num: int | None = None) -> list[AnchorlessConfirm]:
    """Return all anchor-less external-AI CONFIRM findings, optionally filtered to one PR."""
    external_actors = {"aletheia", "grok", "gemini", "claude"}
    results = []
    for f in list_findings(limit=500):
        actor = (getattr(f, "actor", "") or "").lower()
        title = getattr(f, "title", "") or ""
        desc = getattr(f, "description", "") or ""
        if not (
            actor in external_actors or any(actor.startswith(a + "-") for a in external_actors)
        ):
            continue
        if "CONFIRM" not in title.upper():
            continue
        has_tree = bool(re.search(r"Tree [0-9a-f]{40}", desc))
        if has_tree:
            continue
        m = re.search(r"#(\d+)", title)
        this_pr = int(m.group(1)) if m else None
        if pr_num is not None and this_pr != pr_num:
            continue
        if this_pr is None:
            continue
        results.append(
            AnchorlessConfirm(
                finding_id=getattr(f, "finding_id", "") or "",
                actor=actor,
                title=title,
                pr_num=this_pr,
                description=desc,
            )
        )
    return results


def get_pr_merge_anchor(pr_num: int) -> tuple[str, str, str]:
    """Return (merge_commit_sha, tree_hash, merged_at_iso) for a PR.

    Uses gh + git. Tree-hash is computed from the merge commit's tree.
    """
    out = subprocess.check_output(
        ["gh", "pr", "view", str(pr_num), "--json", "mergeCommit,mergedAt"],
        text=True,
    )
    import json

    data = json.loads(out)
    merge_oid = data["mergeCommit"]["oid"]
    merged_at = data["mergedAt"]
    tree_hash = subprocess.check_output(
        ["git", "rev-parse", f"{merge_oid}^{{tree}}"], text=True
    ).strip()
    return merge_oid, tree_hash, merged_at


def build_anchor_block(merge_oid: str, tree_hash: str, merged_at: str) -> str:
    """Render the anchor + provenance text to append to a finding's description."""
    from datetime import datetime, timezone

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return (
        f"\n\n[retroactive-anchor {today}]\n"
        f"Tree {tree_hash} [synthesized-retroactively-from-merge-commit on {today}]\n"
        f"merge-commit {merge_oid}\n"
        f"merged-at {merged_at}\n"
        f"vantage-caveat: patch-id NOT recorded — Aletheia 2026-06-02 named "
        f"patch-id as cross-vantage-unstable (context lines / git config / "
        f"line endings). Tree-hash alone is the load-bearing anchor for this "
        f"retroactive sweep. Original CONFIRM was filed without anchors; this "
        f"backfill is the rigor-discharge per task #50."
    )


def build_verification_stamp(verdict: str, basis: str) -> str:
    """Render the internal-verification stamp."""
    from datetime import datetime, timezone

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    label = "aether-confirmed" if verdict == "confirm" else "aether-flagged"
    return (
        f"\n\n[internal-verification {today}]\n"
        f"internal-verification: {label} {today}\n"
        f"basis: {basis}"
    )


def update_finding_description(finding_id: str, addendum: str) -> bool:
    """Append addendum to a finding's description in the watchmen store."""
    from divineos.core.knowledge import _get_connection

    try:
        conn = _get_connection()
        try:
            row = conn.execute(
                "SELECT description FROM audit_findings WHERE finding_id = ?",
                (finding_id,),
            ).fetchone()
            if not row:
                return False
            new_desc = (row[0] or "") + addendum
            conn.execute(
                "UPDATE audit_findings SET description = ? WHERE finding_id = ?",
                (new_desc, finding_id),
            )
            conn.commit()
        finally:
            conn.close()
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  ERROR updating {finding_id}: {e}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", type=int, required=True, help="PR number to process.")
    parser.add_argument(
        "--verdict",
        choices=("confirm", "flag"),
        required=True,
        help="Re-verification verdict.",
    )
    parser.add_argument(
        "--basis",
        required=True,
        help="One-paragraph basis statement for the verdict.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without writing.",
    )
    args = parser.parse_args()

    confirms = find_anchorless_confirms(pr_num=args.pr)
    if not confirms:
        print(f"No anchor-less CONFIRMs found for PR #{args.pr}.")
        return 0

    print(f"Found {len(confirms)} anchor-less CONFIRM(s) for PR #{args.pr}:")
    for c in confirms:
        print(f"  - {c.finding_id} [{c.actor}] {c.title[:60]}")

    print()
    print(f"Fetching anchor data for PR #{args.pr}...")
    try:
        merge_oid, tree_hash, merged_at = get_pr_merge_anchor(args.pr)
    except Exception as e:  # noqa: BLE001
        print(f"  ERROR: {e}", file=sys.stderr)
        return 1
    print(f"  merge-commit: {merge_oid}")
    print(f"  tree-hash:    {tree_hash}")
    print(f"  merged-at:    {merged_at}")
    print()

    addendum = build_anchor_block(merge_oid, tree_hash, merged_at)
    addendum += build_verification_stamp(args.verdict, args.basis)

    print("Addendum to be appended to each finding's description:")
    print("-" * 60)
    print(addendum)
    print("-" * 60)
    print()

    if args.dry_run:
        print("[DRY-RUN] No writes. Re-run without --dry-run to apply.")
        return 0

    success = 0
    for c in confirms:
        if update_finding_description(c.finding_id, addendum):
            success += 1
    print(f"Updated {success}/{len(confirms)} finding(s).")
    return 0 if success == len(confirms) else 1


if __name__ == "__main__":
    sys.exit(main())
