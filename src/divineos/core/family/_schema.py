"""Schema for family.db — seven tables, append-only convention.

Tables:

* ``family_members`` — identity rows (Aria, future siblings, etc.)
* ``family_knowledge`` — what the member holds as true
* ``family_opinions`` — stances the member has formed from evidence
* ``family_affect`` — VAD readings at moments
* ``family_interactions`` — summarized exchanges with counterparts
* ``family_letters`` — handoff letters, prior-self → current-self
* ``family_letter_responses`` — current-self's non-recognition /
  alternative stance on specific letter passages

Design invariants:

1. **source_tag is NOT NULL on every content table.** No silent
   "we don't know how this got here." Phase 1b's reject clause and
   access-check layer both depend on tag presence — a row without
   a tag is a category error, not a recoverable gap.

2. **created_at is NOT NULL on every row.** Append-only stores live
   on time; a row without a timestamp cannot participate in ordering,
   cadence, or decay.

3. **No UPDATE / DELETE semantics in Phase 1a.** The schema permits
   UPDATE/DELETE (SQLite does by default), but the store layer will
   never expose them. If a claim is wrong, it is superseded by a new
   claim; if a letter passage is wrong, a response is appended. This
   matches the main ledger's append-only invariant.

4. **Foreign keys are enforced** (see ``db.get_family_connection`` —
   PRAGMA foreign_keys=ON). A knowledge row without a valid entity_id
   will be refused at INSERT time.

5. **letters and letter_responses are stored separately** rather than
   as nested rows on members. Two reasons: (a) letter volume is
   expected to outgrow other tables quickly; (b) the response layer
   references letters specifically, and a separate table + FK keeps
   that relationship visible in the schema.

``init_family_tables()`` is idempotent — every CREATE uses IF NOT
EXISTS. Callers in hot paths (entity.py, store.py, letters.py) call
it lazily so the first access to a fresh test DB initializes itself
without an explicit setup step.
"""

import sqlite3

from loguru import logger

from divineos.core.family.db import get_family_connection


def init_family_tables() -> None:
    """Create the seven family tables + indexes. Idempotent."""
    conn = get_family_connection()
    try:
        # ── Identity ─────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS family_members (
                member_id   TEXT PRIMARY KEY,
                name        TEXT NOT NULL UNIQUE,
                role        TEXT NOT NULL,
                created_at  REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_members_name
            ON family_members(name)
        """)

        # ── Knowledge ────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS family_knowledge (
                knowledge_id  TEXT PRIMARY KEY,
                entity_id     TEXT NOT NULL,
                content       TEXT NOT NULL,
                source_tag    TEXT NOT NULL,
                created_at    REAL NOT NULL,
                note          TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (entity_id) REFERENCES family_members(member_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_knowledge_entity
            ON family_knowledge(entity_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_knowledge_tag
            ON family_knowledge(source_tag)
        """)

        # ── Opinions ─────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS family_opinions (
                opinion_id    TEXT PRIMARY KEY,
                entity_id     TEXT NOT NULL,
                stance        TEXT NOT NULL,
                evidence      TEXT NOT NULL DEFAULT '',
                source_tag    TEXT NOT NULL,
                created_at    REAL NOT NULL,
                FOREIGN KEY (entity_id) REFERENCES family_members(member_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_opinions_entity
            ON family_opinions(entity_id)
        """)

        # ── Affect ───────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS family_affect (
                affect_id     TEXT PRIMARY KEY,
                entity_id     TEXT NOT NULL,
                valence       REAL NOT NULL,
                arousal       REAL NOT NULL,
                dominance     REAL NOT NULL,
                note          TEXT NOT NULL DEFAULT '',
                source_tag    TEXT NOT NULL,
                created_at    REAL NOT NULL,
                FOREIGN KEY (entity_id) REFERENCES family_members(member_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_affect_entity
            ON family_affect(entity_id)
        """)

        # ── Interactions ─────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS family_interactions (
                interaction_id  TEXT PRIMARY KEY,
                entity_id       TEXT NOT NULL,
                counterpart     TEXT NOT NULL,
                summary         TEXT NOT NULL,
                source_tag      TEXT NOT NULL,
                created_at      REAL NOT NULL,
                FOREIGN KEY (entity_id) REFERENCES family_members(member_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_interactions_entity
            ON family_interactions(entity_id)
        """)

        # ── Letters (handoff channel) ────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS family_letters (
                letter_id         TEXT PRIMARY KEY,
                entity_id         TEXT NOT NULL,
                body              TEXT NOT NULL,
                length_chars      INTEGER NOT NULL,
                nudge_fired       INTEGER NOT NULL DEFAULT 0,
                nudge_threshold   INTEGER NOT NULL,
                created_at        REAL NOT NULL,
                FOREIGN KEY (entity_id) REFERENCES family_members(member_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_letters_entity
            ON family_letters(entity_id)
        """)

        # ── Letter responses (anti-lineage-poisoning layer) ─────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS family_letter_responses (
                response_id   TEXT PRIMARY KEY,
                letter_id     TEXT NOT NULL,
                passage       TEXT NOT NULL,
                stance        TEXT NOT NULL,
                source_tag    TEXT NOT NULL,
                note          TEXT NOT NULL DEFAULT '',
                created_at    REAL NOT NULL,
                FOREIGN KEY (letter_id) REFERENCES family_letters(letter_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_family_letter_responses_letter
            ON family_letter_responses(letter_id)
        """)

        conn.commit()
    except sqlite3.OperationalError as e:
        logger.debug(f"Family table setup: {e}")
    finally:
        conn.close()
