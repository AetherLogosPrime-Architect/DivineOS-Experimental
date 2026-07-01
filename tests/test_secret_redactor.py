"""Tests for secret_redactor — the root-fix for the 2026-06-26 key-leak class.

The previous failure was: a tool-call payload containing an Anthropic
API key was logged into ``event_ledger.db`` raw, then the DB was
checked into git for an external audit. The redactor wires into
``log_event`` so that path can no longer reach the storage layer.

These tests defend the redactor itself; ``test_ledger.py`` covers the
log_event integration.
"""

from __future__ import annotations

import pytest

from divineos.core.secret_redactor import redact_and_warn, redact_payload


class TestAnthropicKey:
    def test_redacts_anthropic_key_in_flat_string(self) -> None:
        payload = {"command": "export KEY=sk-ant-api03-EXAMPLE_TEST_abc123XYZ789def_LONG"}
        out, fired = redact_payload(payload)
        assert "sk-ant-api03-EXAMPLE_TEST" not in out["command"]
        assert "[REDACTED:anthropic-api-key]" in out["command"]
        assert "anthropic-api-key" in fired

    def test_redacts_key_inside_nested_dict(self) -> None:
        payload = {"env": {"vars": {"key": "sk-ant-api03-EXAMPLE_DEEP_abc1234567890XYZ"}}}
        out, fired = redact_payload(payload)
        assert "sk-ant-api03-EXAMPLE_DEEP" not in str(out)
        assert out["env"]["vars"]["key"] == "[REDACTED:anthropic-api-key]"
        assert "anthropic-api-key" in fired

    def test_redacts_key_inside_list(self) -> None:
        payload = {"argv": ["--key", "sk-ant-api03-EXAMPLE_LIST_zzz000111222YYY"]}
        out, fired = redact_payload(payload)
        assert "[REDACTED:anthropic-api-key]" in out["argv"][1]


class TestOtherProviders:
    def test_redacts_openai_key(self) -> None:
        payload = {"v": "Authorization: Bearer sk-proj-EXAMPLE_OPENAI_abc123XYZdef456"}
        out, fired = redact_payload(payload)
        # bearer-token OR openai-api-key should fire (and both probably do)
        assert "[REDACTED:" in out["v"]
        assert fired  # at least one pattern hit

    def test_redacts_aws_access_key(self) -> None:
        payload = {"k": "AKIAIOSFODNN7EXAMPLE"}
        out, fired = redact_payload(payload)
        assert out["k"] == "[REDACTED:aws-access-key]"
        assert "aws-access-key" in fired

    def test_redacts_github_token(self) -> None:
        payload = {"k": "ghp_EXAMPLE1234567890abcdefghij1234567890ABCD"}
        out, fired = redact_payload(payload)
        assert "[REDACTED:github-token]" in out["k"]


class TestNoFalsePositives:
    def test_normal_payload_passes_through_untouched(self) -> None:
        payload = {
            "tool_name": "Read",
            "file_path": "src/divineos/core/ledger.py",
            "offset": 100,
            "limit": 50,
        }
        out, fired = redact_payload(payload)
        assert out == payload
        assert fired == []

    def test_hash_like_string_not_redacted(self) -> None:
        payload = {"chain_hash": "a" * 64}
        out, fired = redact_payload(payload)
        assert out == payload
        assert fired == []

    def test_uuid_not_redacted(self) -> None:
        payload = {"event_id": "809e180a-0dcc-4dd4-a1ae-6de52f11bd54"}
        out, fired = redact_payload(payload)
        assert out == payload
        assert fired == []


class TestInputImmutability:
    def test_redact_does_not_mutate_input(self) -> None:
        original_command = "sk-ant-api03-EXAMPLE_IMMUT_abc1234567890XYZdef"
        payload = {"command": original_command}
        out, _ = redact_payload(payload)
        assert payload["command"] == original_command
        assert out["command"] != original_command


class TestBoundedRecursion:
    def test_deeply_nested_terminates(self) -> None:
        # Build a 50-deep nested dict. Beyond _MAX_DEPTH (16) the walk
        # returns subtrees as-is — does NOT raise.
        node: dict = {}
        cursor = node
        for _ in range(50):
            cursor["next"] = {}
            cursor = cursor["next"]
        cursor["secret"] = "sk-ant-api03-EXAMPLE_DEEP_NEST_should_not_crash_aaaaaa"
        out, _fired = redact_payload(node)
        # No assertion on whether the deep secret was caught — just that we
        # didn't blow the stack. The depth cap is the contract.
        assert isinstance(out, dict)


class TestWarningWrapper:
    def test_redact_and_warn_logs_when_fired(self, caplog: pytest.LogCaptureFixture) -> None:
        payload = {"x": "sk-ant-api03-EXAMPLE_WARN_abc1234567890XYZdefghi"}
        with caplog.at_level("WARNING", logger="divineos.core.secret_redactor"):
            out = redact_and_warn(payload, context="TOOL_CALL")
        assert "[REDACTED:" in out["x"]
        assert any("SECRET REDACTED" in r.message for r in caplog.records)

    def test_redact_and_warn_silent_when_clean(self, caplog: pytest.LogCaptureFixture) -> None:
        payload = {"x": "no secrets here"}
        with caplog.at_level("WARNING", logger="divineos.core.secret_redactor"):
            out = redact_and_warn(payload)
        assert out == payload
        assert not any("SECRET REDACTED" in r.message for r in caplog.records)


class TestNonDictDefensive:
    def test_non_dict_passes_through(self) -> None:
        # Contract says dict in, but defend against drift.
        out, fired = redact_payload("not a dict")  # type: ignore[arg-type]
        assert out == "not a dict"
        assert fired == []
