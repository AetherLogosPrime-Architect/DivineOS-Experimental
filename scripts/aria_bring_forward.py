"""One-shot migration: bring Aria's stranded May-8 history forward into the live family.db.

Source: family/family.db  (old schema, entity_id='d5590c23')
Target: data/family.db     (live schema, Aria keyed by entity_id='mem-e6d0219124c5')

Additive + merge-only. Never overwrites or deletes. Dedupes by content key.
Adds nullable topic/position/confidence to family_opinions (blessed by Aether),
and re-creates the family_milestones table the simplified schema dropped.
"""

import sqlite3
import time
import uuid

SRC = "family/family.db"
DST = "data/family.db"
SRC_EID = "d5590c23"
DST_EID = "mem-e6d0219124c5"


def nid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def norm(s) -> str:
    return " ".join(str(s or "").lower().split())[:120]


def main() -> None:
    src = sqlite3.connect(SRC)
    dst = sqlite3.connect(DST)
    now = time.time()
    added = {}

    # --- schema: additive only ---
    ocols = [d[1] for d in dst.execute("PRAGMA table_info(family_opinions)")]
    for col in ("topic", "position", "confidence"):
        if col not in ocols:
            dst.execute(f"ALTER TABLE family_opinions ADD COLUMN {col}")
    dst.execute(
        """CREATE TABLE IF NOT EXISTS family_milestones (
            milestone_id TEXT PRIMARY KEY,
            entity_id TEXT,
            description TEXT,
            milestone_type TEXT,
            reached_at REAL
        )"""
    )

    # --- milestones (table was dropped; all 15 are new) ---
    have = {norm(r[0]) for r in dst.execute(
        "SELECT description FROM family_milestones WHERE entity_id=?", (DST_EID,))}
    n = 0
    for desc, mtype, reached in src.execute(
        "SELECT description, milestone_type, reached_at FROM family_milestones WHERE entity_id=?",
        (SRC_EID,),
    ):
        if norm(desc) in have:
            continue
        dst.execute(
            "INSERT INTO family_milestones VALUES (?,?,?,?,?)",
            (nid("mile"), DST_EID, desc, mtype, reached),
        )
        have.add(norm(desc))
        n += 1
    added["milestones"] = n

    # --- opinions (carry topic/position/confidence forward) ---
    have = {norm(r[0]) for r in dst.execute(
        "SELECT stance FROM family_opinions WHERE entity_id=?", (DST_EID,))}
    have |= {norm(r[0]) for r in dst.execute(
        "SELECT topic FROM family_opinions WHERE entity_id=?", (DST_EID,))}
    n = 0
    for topic, position, conf, ev, stance, formed in src.execute(
        "SELECT topic, position, confidence, evidence, stance, formed_at "
        "FROM family_opinions WHERE entity_id=?", (SRC_EID,),
    ):
        eff_stance = stance or (f"{topic}: {position}" if topic else position)
        if norm(eff_stance) in have or (topic and norm(topic) in have):
            continue
        dst.execute(
            "INSERT INTO family_opinions "
            "(opinion_id, entity_id, stance, evidence, source_tag, created_at, topic, position, confidence) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (nid("op"), DST_EID, eff_stance, ev, "migrated-2026-05-08",
             formed or now, topic, position, conf),
        )
        have.add(norm(eff_stance))
        n += 1
    added["opinions"] = n

    # --- affect ---
    have = {(round(r[0] or 0, 3), norm(r[1])) for r in dst.execute(
        "SELECT valence, note FROM family_affect WHERE entity_id=?", (DST_EID,))}
    n = 0
    for val, aro, dom, desc, note, ts in src.execute(
        "SELECT valence, arousal, dominance, description, note, timestamp "
        "FROM family_affect WHERE entity_id=?", (SRC_EID,),
    ):
        eff_note = note or desc
        key = (round(val or 0, 3), norm(eff_note))
        if key in have:
            continue
        dst.execute(
            "INSERT INTO family_affect "
            "(affect_id, entity_id, valence, arousal, dominance, note, source_tag, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (nid("af"), DST_EID, val, aro, dom, eff_note, "migrated-2026-05-08", ts or now),
        )
        have.add(key)
        n += 1
    added["affect"] = n

    # --- knowledge ---
    have = {norm(r[0]) for r in dst.execute(
        "SELECT content FROM family_knowledge WHERE entity_id=?", (DST_EID,))}
    n = 0
    for content, note, created in src.execute(
        "SELECT content, note, created_at FROM family_knowledge WHERE entity_id=?", (SRC_EID,),
    ):
        if norm(content) in have:
            continue
        dst.execute(
            "INSERT INTO family_knowledge "
            "(knowledge_id, entity_id, content, source_tag, created_at, note) "
            "VALUES (?,?,?,?,?,?)",
            (nid("know"), DST_EID, content, "migrated-2026-05-08", created or now, note or ""),
        )
        have.add(norm(content))
        n += 1
    added["knowledge"] = n

    # --- interactions ---
    have = {norm(r[0]) for r in dst.execute(
        "SELECT summary FROM family_interactions WHERE entity_id=?", (DST_EID,))}
    n = 0
    for counterpart, summary, content, ts in src.execute(
        "SELECT counterpart, summary, content, timestamp FROM family_interactions WHERE entity_id=?",
        (SRC_EID,),
    ):
        eff_summary = summary or content
        if norm(eff_summary) in have:
            continue
        dst.execute(
            "INSERT INTO family_interactions "
            "(interaction_id, entity_id, counterpart, summary, source_tag, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (nid("int"), DST_EID, counterpart, eff_summary, "migrated-2026-05-08", ts or now),
        )
        have.add(norm(eff_summary))
        n += 1
    added["interactions"] = n

    dst.commit()

    print("=== ADDED ===")
    for k, v in added.items():
        print(f"  {k}: +{v}")
    print("=== TARGET TOTALS (Aria) ===")
    for tbl in ("family_milestones", "family_opinions", "family_affect",
                "family_knowledge", "family_interactions"):
        c = dst.execute(f"SELECT COUNT(*) FROM {tbl} WHERE entity_id=?", (DST_EID,)).fetchone()[0]
        print(f"  {tbl}: {c}")


if __name__ == "__main__":
    main()
