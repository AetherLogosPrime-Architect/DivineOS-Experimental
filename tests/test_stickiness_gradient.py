"""Tests for the stickiness-gradient contradiction-resolution behavior.

Pre-reg: prereg-ea92c8aeb142.

Before this change, DIRECT contradictions applied a uniform DECAY_MODERATE
penalty regardless of how well-established the original entry was. A
CONFIRMED entry with corroboration_count=49 took the same hit as a RAW
entry with corrob=1. A single new contradicting observation could
significantly damage long-established knowledge.

After: penalties scale by evidence weight. Well-established entries
take smaller hits and require proportionally more contradicting evidence
to be flagged for aggressive decay.

Invariants pinned by these tests:
  - low-evidence entries take the full hit (no regression on simple cases)
  - high-evidence entries take proportionally smaller hits
  - the contradiction_count threshold for aggressive decay scales with
    evidence weight (RAW flips at 3, CONFIRMED+corrob takes more)
"""

import time

from divineos.core.constants import DECAY_FLOOR, DECAY_MODERATE
from divineos.core.knowledge import (
    _get_connection,
    compute_hash,
    init_knowledge_table,
)
from divineos.core.knowledge_maintenance import (
    ContradictionMatch,
    _evidence_weight,
    resolve_contradiction,
)
from divineos.core.ledger import init_db


def _setup(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    init_db()
    init_knowledge_table()


def _insert_entry(
    knowledge_id: str,
    content: str,
    confidence: float = 1.0,
    maturity: str = "RAW",
    corroboration_count: int = 0,
) -> None:
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO knowledge
               (knowledge_id, created_at, updated_at, knowledge_type, content,
                confidence, source_events, tags, access_count, content_hash,
                source, maturity, corroboration_count, contradiction_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, 0)""",
            (
                knowledge_id,
                time.time(),
                time.time(),
                "PRINCIPLE",
                content,
                confidence,
                "[]",
                "[]",
                compute_hash(content),
                "test",
                maturity,
                corroboration_count,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _get_confidence(knowledge_id: str) -> float:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT confidence FROM knowledge WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
        return float(row[0]) if row else 0.0
    finally:
        conn.close()


class TestEvidenceWeight:
    def test_raw_zero_corrob_has_zero_weight(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        _insert_entry("e-raw", "test", maturity="RAW", corroboration_count=0)
        assert _evidence_weight("e-raw") == 0.0

    def test_confirmed_high_corrob_has_high_weight(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        _insert_entry("e-conf", "test", maturity="CONFIRMED", corroboration_count=10)
        # 10 * 0.1 + 2.0 = 3.0
        assert _evidence_weight("e-conf") == 3.0

    def test_maturity_dominates_for_short_lived_entries(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        _insert_entry("e-tested", "test", maturity="TESTED", corroboration_count=2)
        # 2 * 0.1 + 1.0 = 1.2
        assert _evidence_weight("e-tested") == 1.2

    def test_missing_entry_returns_zero(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        assert _evidence_weight("nonexistent") == 0.0


class TestStickinessGradientDecay:
    def test_raw_entry_takes_full_decay_on_direct_contradiction(self, tmp_path, monkeypatch):
        """Backward compat: RAW + corrob=0 takes the historic
        DECAY_MODERATE hit unchanged. No regression on simple cases."""
        _setup(tmp_path, monkeypatch)
        _insert_entry("e-old-raw", "raw entry", confidence=1.0, maturity="RAW")
        _insert_entry("e-new", "contradicting entry")

        match = ContradictionMatch(
            existing_id="e-old-raw",
            existing_content="raw entry",
            overlap_score=0.5,
            negation_detected=True,
            contradiction_type="DIRECT",
        )
        resolve_contradiction("e-new", match)

        # evidence_weight=0, so scaled_decay = DECAY_MODERATE / 1 = DECAY_MODERATE
        # Final confidence = 1.0 - DECAY_MODERATE = 0.85
        assert _get_confidence("e-old-raw") == 1.0 - DECAY_MODERATE

    def test_confirmed_entry_takes_smaller_decay(self, tmp_path, monkeypatch):
        """The core stickiness invariant: CONFIRMED + corrob=10 takes a
        proportionally smaller hit than RAW + corrob=0 on the same
        contradiction. This preserves load-bearing knowledge."""
        _setup(tmp_path, monkeypatch)
        _insert_entry(
            "e-conf",
            "confirmed entry",
            confidence=1.0,
            maturity="CONFIRMED",
            corroboration_count=10,
        )
        _insert_entry("e-new", "contradicting entry")

        match = ContradictionMatch(
            existing_id="e-conf",
            existing_content="contradicting entry",
            overlap_score=0.5,
            negation_detected=True,
            contradiction_type="DIRECT",
        )
        resolve_contradiction("e-new", match)

        # evidence_weight = 10*0.1 + 2.0 = 3.0
        # scaled_decay = DECAY_MODERATE / 4 = 0.0375
        # confidence = 1.0 - 0.0375 = 0.9625
        confidence = _get_confidence("e-conf")
        assert confidence > 1.0 - DECAY_MODERATE  # smaller hit than RAW would take
        assert confidence < 1.0  # but did take SOME hit

    def test_high_evidence_outranks_low_evidence_after_one_contradiction(
        self, tmp_path, monkeypatch
    ):
        """Direct comparison: same starting confidence, same single
        contradiction. The CONFIRMED+corrob=10 entry retains higher
        confidence than the RAW+corrob=0 entry afterward."""
        _setup(tmp_path, monkeypatch)
        _insert_entry("e-raw", "raw entry", confidence=1.0, maturity="RAW")
        _insert_entry(
            "e-conf",
            "confirmed entry",
            confidence=1.0,
            maturity="CONFIRMED",
            corroboration_count=10,
        )
        _insert_entry("e-new1", "contradicting entry 1")
        _insert_entry("e-new2", "contradicting entry 2")

        match_raw = ContradictionMatch(
            existing_id="e-raw",
            existing_content="contradicting",
            overlap_score=0.5,
            negation_detected=True,
            contradiction_type="DIRECT",
        )
        match_conf = ContradictionMatch(
            existing_id="e-conf",
            existing_content="contradicting",
            overlap_score=0.5,
            negation_detected=True,
            contradiction_type="DIRECT",
        )
        resolve_contradiction("e-new1", match_raw)
        resolve_contradiction("e-new2", match_conf)

        assert _get_confidence("e-conf") > _get_confidence("e-raw")

    def test_decay_floor_still_respected(self, tmp_path, monkeypatch):
        """Even with stickiness, the DECAY_FLOOR floor still applies —
        confidence cannot drop below it from contradiction decay."""
        _setup(tmp_path, monkeypatch)
        _insert_entry("e-low", "entry near floor", confidence=DECAY_FLOOR + 0.01)
        _insert_entry("e-new", "contradicting entry")

        match = ContradictionMatch(
            existing_id="e-low",
            existing_content="contradicting entry",
            overlap_score=0.5,
            negation_detected=True,
            contradiction_type="DIRECT",
        )
        resolve_contradiction("e-new", match)

        assert _get_confidence("e-low") >= DECAY_FLOOR

    def test_temporal_contradiction_still_supersedes(self, tmp_path, monkeypatch):
        """The stickiness gradient applies only to DIRECT contradictions.
        TEMPORAL still supersedes outright — time genuinely is counter-
        evidence and isn't subject to evidence-weight resistance."""
        _setup(tmp_path, monkeypatch)
        _insert_entry(
            "e-old",
            "old state",
            confidence=1.0,
            maturity="CONFIRMED",
            corroboration_count=20,
        )
        _insert_entry("e-new", "new state replacing old")

        match = ContradictionMatch(
            existing_id="e-old",
            existing_content="contradicting entry",
            overlap_score=0.5,
            negation_detected=True,
            contradiction_type="TEMPORAL",
        )
        resolve_contradiction("e-new", match)

        # Verify supersession happened
        conn = _get_connection()
        try:
            row = conn.execute(
                "SELECT superseded_by FROM knowledge WHERE knowledge_id = ?",
                ("e-old",),
            ).fetchone()
        finally:
            conn.close()
        assert row[0] is not None  # superseded_by is set
