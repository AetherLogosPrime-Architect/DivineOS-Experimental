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


class TestFableAuditFinding6:
    """2026-07-02 Fable audit: coverage gaps for stated-in-docstring key shapes.

    The docstring commits to recall-over-precision. These four shapes were
    named as gaps: Stripe live keys, HuggingFace tokens, PEM private key
    blocks, URL-embedded credentials. Each is distinctive enough that
    matching them is a real credential (low false-positive risk) and each
    is high-severity by exposure impact. Tests defend the addition against
    regression.
    """

    def test_redacts_stripe_live_key(self) -> None:
        # Fixture is obviously-fake so GitHub's secret scanner doesn't
        # flag this file as containing a real key. Regex is
        # sk_live_[0-9a-zA-Z]{24,} — alphanumeric only, no underscores
        # in the body. EXAMPLETESTfixture pattern is 26+ alphanumeric
        # chars that don't match Stripe's real key format.
        payload = {"k": "sk_live_EXAMPLETESTfixturenotarealkeyXYZ123abc"}
        out, fired = redact_payload(payload)
        assert "EXAMPLETESTfixture" not in out["k"]
        assert "[REDACTED:stripe-live-key]" in out["k"]
        assert "stripe-live-key" in fired

    def test_redacts_stripe_test_key(self) -> None:
        # Test keys are also secrets — smaller blast radius, but still
        # need redaction so they don't leak into audit-exported ledgers.
        # Alphanumeric-only body per regex.
        payload = {"k": "sk_test_EXAMPLETESTfixturenotarealkeyXYZ123abc"}
        out, fired = redact_payload(payload)
        assert "EXAMPLETESTfixture" not in out["k"]
        assert "[REDACTED:stripe-test-key]" in out["k"]

    def test_redacts_huggingface_token(self) -> None:
        # HuggingFace regex is hf_[A-Za-z0-9]{34,} — alphanumeric only.
        payload = {"k": "hf_EXAMPLETESTfixturenotarealtoken1234567890abcd"}
        out, fired = redact_payload(payload)
        assert "EXAMPLETESTfixture" not in out["k"]
        assert "[REDACTED:huggingface-token]" in out["k"]
        assert "huggingface-token" in fired

    def test_redacts_pem_rsa_private_key_block(self) -> None:
        # Multi-line block — pattern uses DOTALL so the whole block
        # BEGIN..END is redacted, not just the header line.
        pem_block = (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIEpAIBAAKCAQEA1234567890abcdefghijklmnop\n"
            "qrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n"
            "-----END RSA PRIVATE KEY-----"
        )
        payload = {"k": pem_block}
        out, fired = redact_payload(payload)
        assert "MIIEpAIBAAKCAQEA" not in out["k"]  # key body gone
        assert "-----END RSA PRIVATE KEY-----" not in out["k"]  # end line gone
        assert "[REDACTED:pem-private-key]" in out["k"]
        assert "pem-private-key" in fired

    def test_redacts_pem_ec_private_key_block(self) -> None:
        # Pattern matches BEGIN [A-Z ]* PRIVATE KEY — covers EC, DSA,
        # ED25519, and plain "PRIVATE KEY" (pkcs8) forms.
        pem_block = (
            "-----BEGIN EC PRIVATE KEY-----\n"
            "MHcCAQEEIExample_body_XYZ123\n"
            "-----END EC PRIVATE KEY-----"
        )
        payload = {"k": pem_block}
        out, _fired = redact_payload(payload)
        assert "MHcCAQEEIExample_body" not in out["k"]
        assert "[REDACTED:pem-private-key]" in out["k"]

    def test_redacts_url_embedded_password(self) -> None:
        # scheme://user:password@host/path — the scheme://user:password@
        # prefix gets replaced with the marker; the host/path segment is
        # preserved for debugging.
        payload = {"k": "postgres://dbuser:s3cretPW@db.internal:5432/prod"}
        out, fired = redact_payload(payload)
        assert "s3cretPW" not in out["k"]
        assert "[REDACTED:url-embedded-credential]" in out["k"]
        # Host preserved
        assert "db.internal:5432/prod" in out["k"]
        assert "url-embedded-credential" in fired

    def test_redacts_url_embedded_password_various_schemes(self) -> None:
        # Multiple schemes redacted with same pattern.
        for scheme in ("https", "http", "redis", "mongodb", "amqp", "mysql"):
            payload = {"k": f"{scheme}://user:secretpass@host/path"}
            out, _fired = redact_payload(payload)
            assert "secretpass" not in out["k"], f"{scheme} url leaked"
            assert "[REDACTED:url-embedded-credential]" in out["k"]

    def test_url_without_credentials_not_redacted(self) -> None:
        # Plain URLs (no user:pass@) should not fire.
        payload = {"k": "https://example.com/path?query=1"}
        out, fired = redact_payload(payload)
        assert out["k"] == "https://example.com/path?query=1"
        assert "url-embedded-credential" not in fired

    def test_pem_public_key_block_not_redacted(self) -> None:
        # Public keys are not secrets; pattern must not match them.
        pem_public = (
            "-----BEGIN PUBLIC KEY-----\n"
            "MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEA\n"
            "-----END PUBLIC KEY-----"
        )
        payload = {"k": pem_public}
        out, fired = redact_payload(payload)
        assert out["k"] == pem_public
        assert "pem-private-key" not in fired
