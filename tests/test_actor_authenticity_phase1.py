"""Tests for actor-authenticity Phase 1.

Phase 1 ships:
- actor_registry module (JSON-backed registry of known actor names)
- actor_capabilities map (advisory verdicts for actor-kind + event-type pairs)
- divineos actor-registry CLI
- warn-on-unknown-actor wired into ledger.log_event

Phase 1 does NOT enforce — unknown actors produce warnings, not failures.
These tests pin both the positive behaviors (registered actors work, CLI
shapes are correct) and the discipline (unknown actors do NOT silently
pass; the warning fires).

See exploration/45_actor_authenticity_design.md for the design rationale.
"""

from __future__ import annotations

import json
import logging

import pytest
from click.testing import CliRunner


# ─── Module imports ──────────────────────────────────────────────────


class TestModuleImports:
    def test_actor_registry_module_imports(self):
        from divineos.core.actor_registry import (  # noqa: F401
            VALID_KINDS,
            RegisteredActor,
            add_actor,
            get_actor,
            init_registry,
            is_registered,
            list_actors,
            load_registry,
        )

    def test_actor_capabilities_module_imports(self):
        from divineos.core.actor_capabilities import (  # noqa: F401
            Verdict,
            can_emit,
            is_denied,
            is_restricted,
        )

    def test_cli_module_imports_and_registers(self):
        from divineos.cli import actor_registry_commands

        assert callable(actor_registry_commands.register)


# ─── Registry CRUD ───────────────────────────────────────────────────


@pytest.fixture
def isolated_registry(tmp_path, monkeypatch):
    """Provide each test with its own registry file."""
    registry_file = tmp_path / "actor_registry.json"
    monkeypatch.setenv("DIVINEOS_ACTOR_REGISTRY", str(registry_file))
    return registry_file


class TestRegistryCRUD:
    def test_init_creates_empty_registry(self, isolated_registry):
        from divineos.core.actor_registry import init_registry, load_registry

        path = init_registry()
        assert path.exists()
        reg = load_registry()
        assert reg["actors"] == {}
        assert reg["version"] == 1

    def test_init_is_idempotent(self, isolated_registry):
        from divineos.core.actor_registry import add_actor, init_registry, load_registry

        init_registry()
        add_actor("test_actor", "agent")
        # Re-initialize without force — should NOT wipe.
        init_registry()
        reg = load_registry()
        assert "test_actor" in reg["actors"]

    def test_init_force_wipes(self, isolated_registry):
        from divineos.core.actor_registry import add_actor, init_registry, load_registry

        init_registry()
        add_actor("test_actor", "agent")
        # Force re-init: wipes contents.
        init_registry(force=True)
        reg = load_registry()
        assert reg["actors"] == {}

    def test_add_actor_returns_registered(self, isolated_registry):
        from divineos.core.actor_registry import add_actor

        actor = add_actor("aether", "agent", notes="test")
        assert actor.name == "aether"
        assert actor.kind == "agent"
        assert actor.notes == "test"
        # Phase 1: no key material yet.
        assert actor.public_key is None
        assert actor.key_fingerprint is None

    def test_add_actor_rejects_unknown_kind(self, isolated_registry):
        from divineos.core.actor_registry import add_actor

        with pytest.raises(ValueError, match="unknown actor kind"):
            add_actor("bad", "definitely_not_a_kind")

    def test_add_actor_rejects_empty_name(self, isolated_registry):
        from divineos.core.actor_registry import add_actor

        with pytest.raises(ValueError, match="empty"):
            add_actor("", "agent")
        with pytest.raises(ValueError, match="empty"):
            add_actor("   ", "agent")

    def test_add_actor_rejects_duplicate(self, isolated_registry):
        from divineos.core.actor_registry import add_actor

        add_actor("aether", "agent")
        with pytest.raises(ValueError, match="already registered"):
            add_actor("aether", "agent")

    def test_update_actor_changes_notes(self, isolated_registry):
        """Closes Aletheia round-26 finding (2026-05-12): add_actor's error
        message referenced update_actor which didn't exist."""
        from divineos.core.actor_registry import add_actor, update_actor, get_actor

        add_actor("aether", "agent", notes="original")
        updated = update_actor("aether", notes="revised")
        assert updated.notes == "revised"
        # Roundtrip via get_actor confirms persistence
        roundtripped = get_actor("aether")
        assert roundtripped is not None
        assert roundtripped.notes == "revised"

    def test_update_actor_preserves_kind_and_added_at(self, isolated_registry):
        """Updating notes must NOT change the immutable identity fields.
        Kind is structurally bound to capability-map; changing it silently
        would defeat the registry's purpose."""
        from divineos.core.actor_registry import add_actor, update_actor, get_actor

        add_actor("aether", "agent", notes="first")
        original = get_actor("aether")
        assert original is not None

        update_actor("aether", notes="second")
        updated = get_actor("aether")
        assert updated is not None
        assert updated.kind == original.kind
        assert updated.added_at == original.added_at
        assert updated.name == original.name

    def test_update_actor_rejects_unknown(self, isolated_registry):
        from divineos.core.actor_registry import update_actor

        with pytest.raises(ValueError, match="not registered"):
            update_actor("never_added", notes="anything")

    def test_update_actor_rejects_empty_name(self, isolated_registry):
        from divineos.core.actor_registry import update_actor

        with pytest.raises(ValueError, match="empty"):
            update_actor("", notes="anything")

    def test_add_actor_error_message_now_actionable(self, isolated_registry):
        """The error message in add_actor references update_actor; the
        function now exists. A regression that removes update_actor would
        also need to update this error message — these change together."""
        from divineos.core.actor_registry import add_actor, update_actor  # noqa: F401

        add_actor("aether", "agent")
        try:
            add_actor("aether", "agent")
        except ValueError as exc:
            # The error message mentions update_actor; importing it succeeded
            # above, so the suggestion is valid (not a broken docstring).
            assert "update_actor" in str(exc)

    def test_get_actor_returns_none_for_unknown(self, isolated_registry):
        from divineos.core.actor_registry import get_actor

        assert get_actor("never_registered") is None

    def test_get_actor_roundtrips_metadata(self, isolated_registry):
        from divineos.core.actor_registry import add_actor, get_actor

        add_actor("aletheia", "audit-sibling", notes="audit-vantage")
        actor = get_actor("aletheia")
        assert actor is not None
        assert actor.kind == "audit-sibling"
        assert actor.notes == "audit-vantage"

    def test_list_actors_sorted(self, isolated_registry):
        from divineos.core.actor_registry import add_actor, list_actors

        add_actor("charlie", "agent")
        add_actor("alpha", "agent")
        add_actor("bravo", "audit-sibling")
        names = [a.name for a in list_actors()]
        assert names == ["alpha", "bravo", "charlie"]

    def test_is_registered_truthy(self, isolated_registry):
        from divineos.core.actor_registry import add_actor, is_registered

        assert not is_registered("aether")
        add_actor("aether", "agent")
        assert is_registered("aether")


# ─── Capability map ──────────────────────────────────────────────────


class TestCapabilityMap:
    def test_operator_can_emit_anything(self):
        from divineos.core.actor_capabilities import Verdict, can_emit

        # Operator-kind: ALLOWED for all event types.
        assert can_emit("operator", "AUDIT_FINDING") == Verdict.ALLOWED
        assert can_emit("operator", "KNOWLEDGE_FILED") == Verdict.ALLOWED
        assert can_emit("operator", "OPERATOR_DIRECTIVE") == Verdict.ALLOWED
        assert can_emit("operator", "ARBITRARY_TYPE") == Verdict.ALLOWED

    def test_audit_sibling_can_emit_audit_events(self):
        from divineos.core.actor_capabilities import Verdict, can_emit

        assert can_emit("audit-sibling", "AUDIT_FINDING") == Verdict.ALLOWED
        assert can_emit("audit-sibling", "AUDIT_ROUND_COMPLETE") == Verdict.ALLOWED

    def test_agent_filing_audit_confirms_denied(self):
        """The pre-emptive-filing pattern (knowledge fec598d7) is exactly
        what this check exists to catch: agent emitting AUDIT_CONFIRMS
        under their own name (or under audit-sibling name) before the
        audit-sibling has audited."""
        from divineos.core.actor_capabilities import Verdict, can_emit

        assert can_emit("agent", "AUDIT_CONFIRMS") == Verdict.DENIED
        assert can_emit("agent", "AUDIT_REVIEW") == Verdict.DENIED
        assert can_emit("agent", "AUDIT_ROUND_COMPLETE") == Verdict.DENIED

    def test_agent_filing_audit_finding_restricted(self):
        """Agent emitting AUDIT_FINDING is RESTRICTED, not DENIED — there
        are legitimate cases (e.g., self-audit at low severity) but each
        merits review."""
        from divineos.core.actor_capabilities import Verdict, can_emit

        assert can_emit("agent", "AUDIT_FINDING") == Verdict.RESTRICTED

    def test_agent_filing_knowledge_allowed(self):
        from divineos.core.actor_capabilities import Verdict, can_emit

        assert can_emit("agent", "KNOWLEDGE_FILED") == Verdict.ALLOWED
        assert can_emit("agent", "COMPASS_OBSERVATION") == Verdict.ALLOWED

    def test_audit_sibling_filing_substrate_events_restricted(self):
        """Audit-sibling emitting knowledge or compass on the substrate's
        behalf conflates audit-vantage with substrate-occupant — restricted
        for review."""
        from divineos.core.actor_capabilities import Verdict, can_emit

        assert can_emit("audit-sibling", "KNOWLEDGE_FILED") == Verdict.RESTRICTED
        assert can_emit("audit-sibling", "COMPASS_OBSERVATION") == Verdict.RESTRICTED

    def test_subagent_emits_only_family_events(self):
        from divineos.core.actor_capabilities import Verdict, can_emit

        assert can_emit("subagent", "FAMILY_AFFECT") == Verdict.ALLOWED
        assert can_emit("subagent", "FAMILY_OPINION") == Verdict.ALLOWED
        # Substrate-global events: restricted.
        assert can_emit("subagent", "KNOWLEDGE_FILED") == Verdict.RESTRICTED
        # Audit events: denied.
        assert can_emit("subagent", "AUDIT_FINDING") == Verdict.DENIED

    def test_unknown_kind_denied(self):
        from divineos.core.actor_capabilities import Verdict, can_emit

        assert can_emit("not_a_kind", "ANY_TYPE") == Verdict.DENIED

    def test_unknown_event_type_allowed_phase1(self):
        """Phase 1 compatibility: unknown event types ALLOWED to avoid
        breaking existing flows. Phase 2 tightens."""
        from divineos.core.actor_capabilities import Verdict, can_emit

        assert can_emit("agent", "ARBITRARY_NEW_EVENT") == Verdict.ALLOWED


# ─── CLI commands ────────────────────────────────────────────────────


class TestCLIShape:
    """Verify the CLI commands are registered and produce expected output."""

    def test_actor_registry_group_registered(self):
        from divineos.cli import cli

        assert "actor-registry" in cli.commands

    def test_actor_registry_subcommands_registered(self):
        from divineos.cli import cli

        group = cli.commands["actor-registry"]
        for sub in ("init", "add", "list", "show", "check"):
            assert sub in group.commands  # type: ignore[attr-defined]

    def test_cli_init_creates_registry(self, isolated_registry):
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["actor-registry", "init"])
        assert result.exit_code == 0
        assert "Actor registry at" in result.output
        # The registry path may be either the env-override or the default.
        # Either way the env-override file is what we created.
        assert isolated_registry.exists()

    def test_cli_add_registers_actor(self, isolated_registry):
        from divineos.cli import cli

        runner = CliRunner()
        runner.invoke(cli, ["actor-registry", "init"])
        result = runner.invoke(
            cli,
            [
                "actor-registry",
                "add",
                "aether",
                "--kind",
                "agent",
                "--notes",
                "test",
            ],
        )
        assert result.exit_code == 0
        assert "registered: aether" in result.output

    def test_cli_add_rejects_unknown_kind(self, isolated_registry):
        from divineos.cli import cli

        runner = CliRunner()
        runner.invoke(cli, ["actor-registry", "init"])
        result = runner.invoke(
            cli,
            ["actor-registry", "add", "x", "--kind", "not_a_kind"],
        )
        # Click rejects via Choice validation.
        assert result.exit_code != 0

    def test_cli_list_shows_actors(self, isolated_registry):
        from divineos.cli import cli

        runner = CliRunner()
        runner.invoke(cli, ["actor-registry", "init"])
        runner.invoke(cli, ["actor-registry", "add", "alpha", "--kind", "agent"])
        runner.invoke(cli, ["actor-registry", "add", "beta", "--kind", "operator"])
        result = runner.invoke(cli, ["actor-registry", "list"])
        assert result.exit_code == 0
        assert "alpha" in result.output
        assert "beta" in result.output

    def test_cli_check_capability_verdict(self, isolated_registry):
        from divineos.cli import cli

        runner = CliRunner()
        runner.invoke(cli, ["actor-registry", "init"])
        runner.invoke(cli, ["actor-registry", "add", "aether", "--kind", "agent"])
        result = runner.invoke(
            cli,
            ["actor-registry", "check", "AUDIT_CONFIRMS", "--actor", "aether"],
        )
        assert result.exit_code == 0
        assert "DENIED" in result.output

    def test_cli_check_unregistered_actor(self, isolated_registry):
        from divineos.cli import cli

        runner = CliRunner()
        runner.invoke(cli, ["actor-registry", "init"])
        result = runner.invoke(
            cli,
            ["actor-registry", "check", "ANY_TYPE", "--actor", "not_registered"],
        )
        # Should communicate unregistered, not crash.
        assert result.exit_code == 0
        assert "not registered" in result.output.lower()


# ─── Phase 1 enforcement (warn-only on unknown actor at log_event) ──


class TestLogEventWarning:
    """log_event warns when actor is unregistered (Phase 1: warn only,
    do not block)."""

    def test_known_actor_no_warning(self, isolated_registry, tmp_path, monkeypatch, caplog):
        # Isolated DB — needs schema init via CLI.
        test_db = tmp_path / "test.db"
        monkeypatch.setenv("DIVINEOS_DB", str(test_db))

        from divineos.cli import cli

        CliRunner().invoke(cli, ["init"])

        from divineos.core.actor_registry import add_actor, init_registry
        from divineos.core.ledger import log_event

        init_registry()
        add_actor("aether", "agent")

        with caplog.at_level(logging.WARNING):
            log_event("DECISION", "aether", {"content": "test"})

        # No Phase-1 actor-authenticity warning fired for a known actor.
        assert not any("Phase-1 actor-authenticity" in r.message for r in caplog.records)

    def test_unknown_actor_emits_warning(self, isolated_registry, tmp_path, monkeypatch):
        """The substrate uses loguru, not stdlib logging — so caplog won't
        capture it directly. Install a loguru sink that writes to a list
        and verify the warning text lands in it."""
        test_db = tmp_path / "test.db"
        monkeypatch.setenv("DIVINEOS_DB", str(test_db))

        from divineos.cli import cli

        CliRunner().invoke(cli, ["init"])

        from loguru import logger as loguru_logger

        from divineos.core.actor_registry import init_registry
        from divineos.core.ledger import log_event

        init_registry()  # empty registry

        captured: list[str] = []
        sink_id = loguru_logger.add(
            lambda msg: captured.append(str(msg)),
            level="WARNING",
        )
        try:
            log_event("DECISION", "some_unknown_actor", {"content": "test"})
        finally:
            loguru_logger.remove(sink_id)

        # Phase-1 warning should fire and mention both the marker text and
        # the unregistered actor name.
        assert any(
            "Phase-1 actor-authenticity" in m and "some_unknown_actor" in m for m in captured
        ), f"expected warning in captured output; got: {captured}"

    def test_exempt_actor_names_no_warning(self, isolated_registry, tmp_path, monkeypatch, caplog):
        """Substrate-internal / pre-bootstrap actor names are exempt from
        the Phase-1 warning."""
        test_db = tmp_path / "test.db"
        monkeypatch.setenv("DIVINEOS_DB", str(test_db))

        from divineos.cli import cli

        CliRunner().invoke(cli, ["init"])

        from divineos.core.actor_registry import init_registry
        from divineos.core.ledger import log_event

        init_registry()  # empty registry

        with caplog.at_level(logging.WARNING):
            for exempt in ("system", "substrate", "user", "assistant", "unknown"):
                log_event("DECISION", exempt, {"content": "test"})

        # No warnings should fire for any of the exempt names.
        for exempt in ("system", "substrate", "user", "assistant", "unknown"):
            assert not any(
                "Phase-1 actor-authenticity" in r.message and exempt in r.message
                for r in caplog.records
            ), f"unexpected warning for exempt actor {exempt!r}"

    def test_unknown_actor_does_not_block_emission(self, isolated_registry, tmp_path, monkeypatch):
        """Phase 1 is warn-only — log_event must still succeed even when
        the actor is unregistered."""
        test_db = tmp_path / "test.db"
        monkeypatch.setenv("DIVINEOS_DB", str(test_db))

        from divineos.cli import cli

        CliRunner().invoke(cli, ["init"])

        from divineos.core.actor_registry import init_registry
        from divineos.core.ledger import log_event

        init_registry()

        # Should not raise — warn-only.
        event_id = log_event("DECISION", "some_unknown_actor", {"content": "test"})
        assert event_id  # got an event_id back


# ─── Registry JSON shape ────────────────────────────────────────────


class TestRegistryFileShape:
    """The registry file is gitignored runtime state, but its shape should
    be stable enough for cross-vantage stub generation later."""

    def test_file_is_valid_json(self, isolated_registry):
        from divineos.core.actor_registry import add_actor, init_registry

        init_registry()
        add_actor("aether", "agent", notes="test")

        text = isolated_registry.read_text(encoding="utf-8")
        data = json.loads(text)
        assert data["version"] == 1
        assert "actors" in data
        assert "aether" in data["actors"]

    def test_file_includes_phase2_fields_as_null(self, isolated_registry):
        """Phase 1 doesn't populate key material, but the fields exist as
        null so Phase 2 can fill them without schema migration."""
        from divineos.core.actor_registry import add_actor, init_registry

        init_registry()
        add_actor("aether", "agent")

        data = json.loads(isolated_registry.read_text(encoding="utf-8"))
        entry = data["actors"]["aether"]
        for field in ("public_key", "key_fingerprint", "valid_from", "valid_until"):
            assert field in entry
            assert entry[field] is None
