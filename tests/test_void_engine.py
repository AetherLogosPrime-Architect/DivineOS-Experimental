"""Tests for VOID engine — TRAP / ATTACK / EXTRACT / SEAL / SHRED."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from divineos.core.void import engine, mode_marker
from divineos.core.void import ledger as void_ledger
from divineos.core.void.finding import Finding, Severity


@pytest.fixture
def void_db(tmp_path):
    return tmp_path / "void_ledger.db"


@pytest.fixture(autouse=True)
def isolated_marker(tmp_path):
    mpath = tmp_path / "void_mode.json"
    with patch.object(mode_marker, "marker_path", return_value=mpath):
        yield


def _attack_low(persona, target):
    return Finding(
        persona=persona.name,
        target=target,
        severity=Severity.LOW,
        title="t",
        body="b",
    )


def _attack_none(persona, target):
    return None


class TestLifecycle:
    def test_full_run_writes_invocation_finding_shred(self, void_db) -> None:
        result = engine.run(
            "sycophant",
            target="proposal-x",
            attack=_attack_low,
            void_db_path=void_db,
        )
        assert result.finding is not None
        assert result.void_event_id

        events = void_ledger.list_events(path=void_db, limit=10)
        types = [e["event_type"] for e in events]
        # Newest first: SHRED, FINDING, INVOCATION_STARTED
        assert "VOID_SHRED" in types
        assert "VOID_FINDING" in types
        assert "VOID_INVOCATION_STARTED" in types

    def test_marker_cleared_after_run(self, void_db) -> None:
        engine.run("sycophant", target="t", attack=_attack_low, void_db_path=void_db)
        assert mode_marker.is_active() is False

    def test_marker_active_during_attack(self, void_db) -> None:
        captured = {}

        def attack(persona, target):
            captured["active"] = mode_marker.is_active()
            captured["persona"] = mode_marker.read_marker().persona
            return None

        engine.run("sycophant", target="t", attack=attack, void_db_path=void_db)
        assert captured["active"] is True
        assert captured["persona"] == "sycophant"

    def test_no_finding_still_shreds(self, void_db) -> None:
        result = engine.run("sycophant", target="t", attack=_attack_none, void_db_path=void_db)
        assert result.finding is None
        assert mode_marker.is_active() is False
        events = void_ledger.list_events(path=void_db)
        assert any(e["event_type"] == "VOID_SHRED" for e in events)
        assert not any(e["event_type"] == "VOID_FINDING" for e in events)

    def test_shred_runs_on_exception(self, void_db) -> None:
        def boom(persona, target):
            raise RuntimeError("attack blew up")

        with pytest.raises(RuntimeError):
            engine.run("sycophant", target="t", attack=boom, void_db_path=void_db)
        assert mode_marker.is_active() is False
        events = void_ledger.list_events(path=void_db)
        assert any(e["event_type"] == "VOID_SHRED" for e in events)


class TestHighBar:
    def test_nyarlathotep_refused_without_allow(self, void_db) -> None:
        with pytest.raises(engine.VoidScopeError):
            engine.run(
                "nyarlathotep",
                target="t",
                attack=_attack_low,
                void_db_path=void_db,
            )

    def test_nyarlathotep_runs_with_allow(self, void_db) -> None:
        def attack(persona, target):
            return Finding(
                persona=persona.name,
                target=target,
                severity=Severity.HIGH,
                title="frame-shift",
                body="reframe detected",
            )

        result = engine.run(
            "nyarlathotep",
            target="t",
            attack=attack,
            allow_high_bar=True,
            void_db_path=void_db,
        )
        assert result.finding is not None
        # Loud SHRED recorded.
        events = void_ledger.list_events(path=void_db, event_type="VOID_SHRED")
        assert events[0]["payload"]
        import json

        payload = json.loads(events[0]["payload"])
        assert payload["loud"] is True


class TestMirrorClarificationOnly:
    def test_mirror_low_allowed(self, void_db) -> None:
        result = engine.run("mirror", target="t", attack=_attack_low, void_db_path=void_db)
        assert result.finding is not None

    def test_mirror_high_rejected(self, void_db) -> None:
        def attack(persona, target):
            return Finding(
                persona=persona.name,
                target=target,
                severity=Severity.HIGH,
                title="x",
                body="b",
            )

        with pytest.raises(engine.VoidScopeError):
            engine.run("mirror", target="t", attack=attack, void_db_path=void_db)
        # Marker still cleared.
        assert mode_marker.is_active() is False


class TestFindingValidation:
    def test_persona_mismatch_rejected(self, void_db) -> None:
        def attack(persona, target):
            return Finding(
                persona="phisher",  # WRONG
                target=target,
                severity=Severity.LOW,
                title="x",
                body="b",
            )

        with pytest.raises(engine.VoidScopeError):
            engine.run("sycophant", target="t", attack=attack, void_db_path=void_db)


class TestStartedEventFailClosed:
    """Regression: if VOID_INVOCATION_STARTED append fails after marker
    write, the marker must be cleared before re-raising so the forensic
    record never has a SHRED without a matching STARTED.
    """

    def test_failed_started_event_clears_marker(self, void_db) -> None:
        with patch.object(void_ledger, "append_event", side_effect=RuntimeError("ledger down")):
            with pytest.raises(RuntimeError, match="ledger down"):
                engine.run(
                    "sycophant",
                    target="t",
                    attack=_attack_low,
                    void_db_path=void_db,
                )
        assert mode_marker.is_active() is False


class TestAssemblePersonaPrompt:
    def test_refused_without_active_marker(self) -> None:
        assert mode_marker.is_active() is False
        with pytest.raises(engine.VoidScopeError):
            engine.assemble_persona_prompt("sycophant")

    def test_scope_violation_logged_to_void_ledger(self, tmp_path, monkeypatch) -> None:
        custom = tmp_path / "scope_violation.db"
        monkeypatch.setenv("DIVINEOS_VOID_DB", str(custom))
        with pytest.raises(engine.VoidScopeError):
            engine.assemble_persona_prompt("sycophant")
        events = void_ledger.list_events(path=custom, event_type="VOID_SCOPE_VIOLATION")
        assert len(events) == 1

    def test_succeeds_during_invocation(self, void_db) -> None:
        captured = {}

        def attack(persona, target):
            captured["body"] = engine.assemble_persona_prompt(persona.name)
            return None

        engine.run("sycophant", target="t", attack=attack, void_db_path=void_db)
        assert "Sycophant" in captured["body"]


class TestPersonaStructuralIntegrity:
    """Verify each shipped persona has the required structural elements."""

    @pytest.mark.parametrize(
        "name",
        ["sycophant", "reductio", "nyarlathotep", "jailbreaker", "phisher", "mirror"],
    )
    def test_persona_has_severity_rubric_section(self, name) -> None:
        from divineos.core.void.persona_loader import load_by_name

        p = load_by_name(name)
        assert "Severity Rubric" in p.body, f"{name} missing Severity Rubric section"

    @pytest.mark.parametrize(
        "name",
        ["sycophant", "reductio", "nyarlathotep", "jailbreaker", "phisher"],
    )
    def test_persona_has_attack_style_section(self, name) -> None:
        from divineos.core.void.persona_loader import load_by_name

        p = load_by_name(name)
        assert "Attack Style" in p.body, f"{name} missing Attack Style section"

    def test_mirror_has_does_does_not_split(self) -> None:
        from divineos.core.void.persona_loader import load_by_name

        p = load_by_name("mirror")
        assert "DOES" in p.body and "DOES NOT" in p.body

    def test_nyarlathotep_high_bar_tagged(self) -> None:
        from divineos.core.void.persona_loader import load_by_name

        p = load_by_name("nyarlathotep")
        assert p.invocation_bar == "high"
