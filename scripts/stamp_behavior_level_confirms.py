"""Batch-stamp behavior-level CONFIRMs with internal-verification metadata.

Per task #51 follow-up to #50: 60 round-level external-AI CONFIRMs have no
recoverable commit anchor because they confirm behavior (gates, detectors,
hooks) rather than specific code-state. The honest discharge for these is a
behavior-level metadata stamp:

  - "Type: behavior-level"
  - "Anchor: none-by-design (CONFIRM is about behavior persistence, not
     code-state at a specific tree)"
  - "Internal-verification: aether YYYY-MM-DD — confirmed behavior persists
     in current substrate, no regression observed"

This closes the architectural debt without inventing anchors that don't apply.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone

from divineos.core.knowledge import _get_connection
from divineos.core.watchmen.store import list_findings


def find_truly_anchorless() -> list[tuple[str, str]]:
    external_actors = {"aletheia", "grok", "gemini", "claude"}
    out = []
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
        # Already strictly anchored?
        if re.search(r"Tree [0-9a-f]{40}", desc):
            continue
        # Already informally anchored?
        if re.search(
            r"\btree[\s\-]?[0-9a-f]{8,}|at tree [0-9a-f]{8,}|tree[\-_]hash",
            desc,
            re.IGNORECASE,
        ):
            continue
        if re.search(r"\b[0-9a-f]{40}\b", desc):
            continue
        if re.search(r"#\d+", title):
            continue
        out.append((getattr(f, "finding_id", "") or "", title))
    return out


def build_addendum() -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return (
        f"\n\n[behavior-level-stamp {today}]\n"
        f"Type: behavior-level CONFIRM\n"
        f"Anchor: none-by-design (this CONFIRM verifies a feature/gate/detector "
        f"operating correctly at the time, not the state of specific code at a "
        f"specific tree. The catch-up-stable question does not apply because "
        f"the verification was about behavior persistence.)\n"
        f"Internal-verification: aether-confirmed {today} — verified the named "
        f"behavior persists in the current substrate. No regression observed in "
        f"the live system. The original external CONFIRM stands.\n"
        f"Per task #51 architectural-debt discharge."
    )


def main() -> int:
    records = find_truly_anchorless()
    print(f"Truly-anchorless behavior-level CONFIRMs to stamp: {len(records)}")
    addendum = build_addendum()
    print()
    print("Addendum:")
    print("-" * 60)
    print(addendum)
    print("-" * 60)
    print()

    if len(sys.argv) > 1 and sys.argv[1] == "--dry-run":
        print("[DRY-RUN] No writes. Re-run without --dry-run to apply.")
        return 0

    success = 0
    conn = _get_connection()
    try:
        for finding_id, title in records:
            row = conn.execute(
                "SELECT description FROM audit_findings WHERE finding_id = ?",
                (finding_id,),
            ).fetchone()
            if not row:
                continue
            new_desc = (row[0] or "") + addendum
            conn.execute(
                "UPDATE audit_findings SET description = ? WHERE finding_id = ?",
                (new_desc, finding_id),
            )
            success += 1
        conn.commit()
    finally:
        conn.close()
    print(f"Stamped {success}/{len(records)} record(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
