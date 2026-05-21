"""Regression-pins for Aletheia hidden-issues audit Findings W, X, Y
(2026-05-20) — knowledge-layer silent-ignore / fails-open / resurrection.

- W: store_knowledge dedup must honor a maturity UPGRADE (never downgrade).
- Y: store_knowledge must NOT resurrect deliberately-superseded content.
- X: the validity gate must fail CLOSED on a real error, not fail OPEN.
"""

from __future__ import annotations


from divineos.core.knowledge import init_knowledge_table
from divineos.core.knowledge._base import get_connection
from divineos.core.knowledge.crud import store_knowledge
from divineos.core.knowledge_maintenance import _passes_validity_gate

_C = "knowledge-integrity audit regression-pin content, sufficiently long"


class TestFindingW_MaturityUpgradeOnDedup:
    def test_dedup_upgrades_maturity(self):
        init_knowledge_table()
        kid = store_knowledge("FACT", _C, maturity="RAW")
        kid2 = store_knowledge("FACT", _C, maturity="CONFIRMED")
        assert kid == kid2  # dedup hit, same entry
        conn = get_connection()
        try:
            mat = conn.execute(
                "SELECT maturity FROM knowledge WHERE knowledge_id = ?", (kid,)
            ).fetchone()[0]
        finally:
            conn.close()
        assert mat == "CONFIRMED", "caller's higher maturity should upgrade the entry"

    def test_dedup_never_downgrades_maturity(self):
        init_knowledge_table()
        kid = store_knowledge("FACT", _C, maturity="CONFIRMED")
        store_knowledge("FACT", _C, maturity="RAW")  # lower — must NOT downgrade
        conn = get_connection()
        try:
            mat = conn.execute(
                "SELECT maturity FROM knowledge WHERE knowledge_id = ?", (kid,)
            ).fetchone()[0]
        finally:
            conn.close()
        assert mat == "CONFIRMED", "a lower caller-maturity must never downgrade"


class TestFindingY_NoResurrection:
    def _supersede(self, kid: str) -> None:
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE knowledge SET superseded_by = ? WHERE knowledge_id = ?",
                ("some-newer-id", kid),
            )
            conn.commit()
        finally:
            conn.close()

    def test_superseded_content_not_resurrected_by_default(self):
        init_knowledge_table()
        kid = store_knowledge("FACT", _C, maturity="RAW")
        self._supersede(kid)
        result = store_knowledge("FACT", _C, maturity="RAW")
        assert result == "", "superseded content must not be resurrected (returns '')"

    def test_allow_resurrect_opts_into_reinsert(self):
        init_knowledge_table()
        kid = store_knowledge("FACT", _C, maturity="RAW")
        self._supersede(kid)
        result = store_knowledge("FACT", _C, maturity="RAW", allow_resurrect=True)
        assert result and result != kid, "allow_resurrect=True must insert a fresh entry"


class TestFindingX_ValidityGateFailsClosed:
    def test_logic_bug_fails_closed(self, monkeypatch):
        # A bug inside can_promote (KeyError/TypeError/ValueError) must DENY
        # promotion (fail-closed), not silently allow it.
        import divineos.core.logic.logic_validation as lv

        def _boom(*a, **k):
            raise KeyError("simulated bug in validity logic")

        monkeypatch.setattr(lv, "can_promote", _boom)
        assert _passes_validity_gate("kid", "RAW", "HYPOTHESIS", 1) is False

    def test_module_not_deployed_allows(self, monkeypatch):
        # ImportError (logic module absent) is the documented backward-compat
        # case — allow.
        import divineos.core.logic.logic_validation as lv

        def _import_err(*a, **k):
            raise ImportError("logic module not deployed")

        monkeypatch.setattr(lv, "can_promote", _import_err)
        assert _passes_validity_gate("kid", "RAW", "HYPOTHESIS", 1) is True

    def test_valid_promotion_passes_through(self, monkeypatch):
        import divineos.core.logic.logic_validation as lv

        monkeypatch.setattr(lv, "can_promote", lambda *a, **k: True)
        assert _passes_validity_gate("kid", "RAW", "HYPOTHESIS", 1) is True

    def test_invalid_promotion_denied(self, monkeypatch):
        import divineos.core.logic.logic_validation as lv

        monkeypatch.setattr(lv, "can_promote", lambda *a, **k: False)
        assert _passes_validity_gate("kid", "RAW", "HYPOTHESIS", 1) is False
