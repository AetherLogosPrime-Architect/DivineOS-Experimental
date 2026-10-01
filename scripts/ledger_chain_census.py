"""Every chain break in the ledger at once, by day and by event type. Read-only.

`divineos verify` stops at the first broken link, which is right for a pass or
fail answer and wrong for understanding damage: on 2026-08-20 my own test
probes forked the chain 940 times, I marked the polluted rows in a letter, and
the first break was all the verifier ever showed, so the rest went unseen for
five weeks (found 2026-09-28). Run this whenever a write-up says something
touched the ledger, and put its output in the write-up.

A link break alone (a row's prior_hash is not the previous row's chain_hash)
is a crossed hook. A row whose own chain hash fails to recompute is an altered
row. The two are reported separately because they mean different things.
"""

from __future__ import annotations

import collections
import datetime
import sys

from divineos.core._ledger_base import get_connection
from divineos.core.ledger import _CHAIN_GENESIS, _compute_chain_hash


def census() -> dict:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT rowid, event_id, timestamp, event_type, actor, payload, content_hash, "
            "prior_hash, chain_hash FROM system_events ORDER BY rowid"
        ).fetchall()
    finally:
        conn.close()
    expected = _CHAIN_GENESIS
    breaks, altered = [], []
    for rowid, eid, ts, etype, actor, payload, chash, prior, chain in rows:
        if not chain:
            continue
        if prior != expected:
            day = datetime.datetime.fromtimestamp(ts).date().isoformat()
            breaks.append({"rowid": rowid, "event_id": eid, "type": etype, "day": day})
        if _compute_chain_hash(prior, eid, ts, etype, actor, payload, chash) != chain:
            altered.append({"rowid": rowid, "event_id": eid, "type": etype})
        expected = chain
    return {
        "rows": len(rows),
        "link_breaks": breaks,
        "altered_rows": altered,
        "breaks_by_day": dict(collections.Counter(b["day"] for b in breaks)),
        "breaks_by_type": dict(collections.Counter(b["type"] for b in breaks)),
    }


def main() -> int:
    result = census()
    print(f"rows: {result['rows']}")
    print(f"link breaks (crossed hooks): {len(result['link_breaks'])}")
    print(f"altered rows (own hash fails): {len(result['altered_rows'])}")
    for day, n in sorted(result["breaks_by_day"].items()):
        print(f"  {day}: {n}")
    for etype, n in sorted(result["breaks_by_type"].items(), key=lambda kv: -kv[1]):
        print(f"  {etype}: {n}")
    for row in result["altered_rows"][:20]:
        print(f"  ALTERED rowid {row['rowid']} {row['event_id']} {row['type']}")
    return 1 if result["altered_rows"] else 0


if __name__ == "__main__":
    sys.exit(main())
