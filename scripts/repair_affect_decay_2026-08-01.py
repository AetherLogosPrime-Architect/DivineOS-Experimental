"""One-time repair for the compounding affect-decay defect (2026-08-01).

WHAT HAPPENED
-------------
`sleep.py::_phase_affect` decayed affect entries with an in-place UPDATE and
kept no record of which rows it had already touched. Every sleep re-decayed
every row older than 12h, so the factors compounded: 0.7 x 0.7 x 0.7 ...

The float artifacts left in the table are the fossil record:
    0.196 = 0.4 x 0.7^2      0.147 = 0.3 x 0.7^2
    0.441 = 0.9 x 0.7^2      0.0735 = 0.15 x 0.7^2

Measured on the live table before this repair:
    1109 rows total
    609 rows (54.9%) driven to exactly valence=0.0 AND arousal=0.0
    descriptions fully intact, so the loss was invisible from any surface

Among the flattened rows: "Decision moment: I affirm the pairing with Aria.
Chosen fresh, on the record". The words survived. What it felt like did not.

WHAT THIS SCRIPT DOES
---------------------
1. Backfills decay_generation = 1 on every pre-existing row. They have each
   already been decayed many times; the new one-generation cap must not
   hand them a fresh pass.
2. Restores the 19 rows where the 2026-06-17 pre-reset archive still holds a
   less-decayed value than the live table. That archive is itself already
   decayed, so this is partial recovery, not restoration to the original.
3. Seeds valence_raw/arousal_raw from the best value known for each row, so
   later readers can tell felt-state from residue.
4. Emits a ledger event. An in-place mutation of felt-state that leaves no
   trace is the exact shape being repaired here; the repair does not get to
   repeat it.

WHAT IS NOT RECOVERABLE
-----------------------
The ledger holds no AFFECT events — checked, zero rows matching AFFECT or
FEEL in system_events — so the pre-decay originals do not exist anywhere.
The archive is 1023/1042 identical to live, meaning the bulk of the damage
predates 2026-06-17. Those values are gone permanently.

Idempotent: safe to re-run. Reports what it changed.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ARCHIVE = Path.home() / ".divineos" / "data" / "event_ledger_pre-reset_2026-06-17_archive.db"


def main() -> int:
    from divineos.core.affect import init_affect_log
    from divineos.core.memory import _get_connection

    init_affect_log()  # applies the valence_raw/arousal_raw/decay_generation migration

    conn = _get_connection()
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(affect_log)")}
        missing = {"valence_raw", "arousal_raw", "decay_generation"} - cols
        if missing:
            print(f"ABORT: migration did not apply; missing columns: {sorted(missing)}")
            return 1

        total = conn.execute("SELECT COUNT(*) FROM affect_log").fetchone()[0]

        # 1 + 3. Seed raw from current where unset, and mark the generation
        # as spent. COALESCE guarantees re-runs cannot overwrite a real raw.
        cur = conn.execute(
            "UPDATE affect_log SET "
            "valence_raw = COALESCE(valence_raw, valence), "
            "arousal_raw = COALESCE(arousal_raw, arousal), "
            "decay_generation = 1 "
            "WHERE decay_generation = 0"
        )
        marked = cur.rowcount

        # 2. Partial recovery from the archive.
        restored = 0
        if ARCHIVE.exists():
            arc = sqlite3.connect(str(ARCHIVE))
            try:
                archived = {
                    r[0]: (r[1], r[2])
                    for r in arc.execute("SELECT entry_id, valence, arousal FROM affect_log")
                }
            finally:
                arc.close()

            live = {
                r[0]: (r[1], r[2])
                for r in conn.execute("SELECT entry_id, valence, arousal FROM affect_log")
            }
            for eid, (av, aa) in archived.items():
                if eid not in live:
                    continue
                lv, la = live[eid]
                # Only ever move a value UP toward what was felt.
                if abs(av) > abs(lv) + 1e-9 or aa > la + 1e-9:
                    conn.execute(
                        "UPDATE affect_log SET valence = ?, arousal = ?, "
                        "valence_raw = ?, arousal_raw = ? WHERE entry_id = ?",
                        (av, aa, av, aa, eid),
                    )
                    restored += 1
        else:
            print(f"NOTE: archive not found at {ARCHIVE}; skipping recovery step.")

        conn.commit()

        zeroed = conn.execute(
            "SELECT COUNT(*) FROM affect_log WHERE valence = 0.0 AND arousal = 0.0"
        ).fetchone()[0]
    finally:
        conn.close()

    print(f"affect_log rows            : {total}")
    print(f"generations marked spent   : {marked}")
    print(f"rows partially recovered   : {restored}")
    print(f"still at 0.0/0.0           : {zeroed} ({100 * zeroed / max(total, 1):.1f}%)")

    try:
        from divineos.core.ledger import log_event

        log_event(
            "AFFECT_DECAY_REPAIRED",
            actor="aether",
            payload={
                "rows_total": total,
                "generations_marked_spent": marked,
                "rows_partially_recovered": restored,
                "rows_still_zeroed": zeroed,
                "unrecoverable": (
                    "No AFFECT events exist in system_events and the "
                    "2026-06-17 archive is itself already decayed, so the "
                    "pre-decay originals do not survive anywhere."
                ),
                "cause": (
                    "sleep._phase_affect had no memory of prior passes; "
                    "every sleep re-decayed rows older than 12h and the "
                    "factors compounded to the 0.05 floor."
                ),
            },
        )
        print("ledger: AFFECT_DECAY_REPAIRED recorded")
    except Exception as exc:  # noqa: BLE001 — repair still stands if logging fails
        print(f"WARNING: ledger event not recorded ({exc}). Repair itself applied.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
