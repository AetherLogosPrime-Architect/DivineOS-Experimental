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


class TestEveryPositionOfEveryStringIsExamined:
    """2026-10-07. Strings over 100,000 characters used to be scanned in their first
    100,000 only, so a key placed after that came out in the clear, in a ledger that is
    append-only. Found by running the comment that described the cap (with a control),
    not by reading it. The cap was covering two quadratic patterns, so those are pinned
    linear here as well: the test that proves the hole is closed must not make the
    write path crawl."""

    KEY = "sk_live_" + "A1b2C3d4E5f6G7h8I9j0K1l2"  # a fake, test-shaped key
    TAIL = "A1b2C3d4E5f6G7h8I9j0K1l2"

    def _redacted(self, text: str) -> bool:
        out, _ = redact_payload({"k": text})
        return self.TAIL not in out["k"]

    def test_the_control_a_short_string_is_redacted(self) -> None:
        assert self._redacted(f"key is {self.KEY} ok")

    @pytest.mark.parametrize(
        "where",
        ["start", "just_before_old_cap", "straddling_old_cap", "just_after_old_cap", "far_after"],
    )
    def test_a_key_anywhere_in_a_long_string_is_redacted(self, where: str) -> None:
        cap = 100_000
        text = {
            "start": self.KEY + " " + "x" * (cap + 500),
            "just_before_old_cap": "x" * (cap - 60) + " " + self.KEY + " " + "x" * 500,
            "straddling_old_cap": "x" * (cap - 13) + " " + self.KEY + " tail",
            "just_after_old_cap": "x" * (cap + 50) + " " + self.KEY,
            "far_after": "x" * (cap * 3) + " " + self.KEY + " tail",
        }[where]
        assert self._redacted(text)

    def test_a_key_in_one_of_many_fields_of_a_long_payload(self) -> None:
        payload = {"a": "x" * 150_000, "b": {"c": ["y" * 150_000 + " " + self.KEY]}}
        out, fired = redact_payload(payload)
        assert self.TAIL not in str(out)
        assert "stripe-live-key" in fired

    def test_a_long_run_of_letters_does_not_make_the_url_pattern_crawl(self) -> None:
        import time

        t = time.time()
        redact_payload({"k": "a" * 400_000})
        assert time.time() - t < 5, "400,000 letters took the quadratic path (77 s before the fix)"

    def test_a_flood_of_begin_lines_with_no_end_does_not_make_the_pem_pairing_crawl(self) -> None:
        import time

        flood = "-----BEGIN RSA PRIVATE KEY-----\nabc\n" * 12_000
        t = time.time()
        out, _ = redact_payload({"k": flood})
        assert time.time() - t < 5, "the PEM scan went quadratic again (10 s at 400,000 before)"
        # No END anywhere, so each stretch is a bounded guess (the ceiling can land
        # mid-line, so a few leftover characters between stretches are expected).
        assert "[REDACTED:pem-private-key-truncated]" in out["k"]
        assert len(out["k"]) < len(flood) // 10


class TestPemPairingKeepsTheLazyPatternsMeaning:
    BEGIN = "-----BEGIN RSA PRIVATE KEY-----"
    END = "-----END RSA PRIVATE KEY-----"

    def test_two_blocks_are_both_redacted_and_the_text_between_is_kept(self) -> None:
        text = f"before {self.BEGIN}\nAAAA\n{self.END} middle {self.BEGIN}\nBBBB\n{self.END} after"
        out, fired = redact_payload({"k": text})
        assert "AAAA" not in out["k"] and "BBBB" not in out["k"]
        assert (
            out["k"] == "before [REDACTED:pem-private-key] middle [REDACTED:pem-private-key] after"
        )
        assert fired == ["pem-private-key"]

    def test_a_begin_inside_a_block_does_not_start_a_second_block(self) -> None:
        """The lazy regex took the nearest END, so a nested BEGIN is part of the first block."""
        text = f"{self.BEGIN}\nAAAA\n{self.BEGIN}\nBBBB\n{self.END} tail"
        out, _ = redact_payload({"k": text})
        assert out["k"] == "[REDACTED:pem-private-key] tail"

    def test_a_begin_with_no_end_is_a_bounded_guess_under_its_own_name(self) -> None:
        """A key cut off mid body: the old pattern waited for an END that never came and the
        body was stored in the clear. Now the stretch to the next blank line is redacted,
        under a different marker name so a guess can be told from a whole block."""
        text = f"before\n{self.BEGIN}\nSECRETBODYLINE1\nSECRETBODYLINE2\n\nafter the blank line"
        out, fired = redact_payload({"k": text})
        assert "SECRETBODY" not in out["k"]
        assert "[REDACTED:pem-private-key-truncated]" in out["k"]
        assert out["k"].endswith("\n\nafter the blank line")  # the blank line ends the guess
        assert out["k"].startswith("before\n")
        assert fired == ["pem-private-key-truncated"]

    def test_the_guess_stops_at_the_ceiling_when_there_is_no_blank_line(self) -> None:
        body = "A" * 6000
        out, _ = redact_payload({"k": f"{self.BEGIN}\n{body}\nTAILTEXT"})
        assert "[REDACTED:pem-private-key-truncated]" in out["k"]
        # Bounded: the redacted stretch is the ceiling, so the rest of a long body remains.
        assert len(out["k"]) > 1500 and "TAILTEXT" in out["k"]

    def test_a_complete_block_is_not_treated_as_a_guess(self) -> None:
        text = f"{self.BEGIN}\nAAAA\n{self.END}"
        out, fired = redact_payload({"k": text})
        assert out["k"] == "[REDACTED:pem-private-key]" and fired == ["pem-private-key"]

    def test_an_end_before_the_begin_does_not_close_it(self) -> None:
        """The END came first, so the BEGIN is unterminated and is treated as a cut-off key."""
        text = f"{self.END} {self.BEGIN}\nAAAA"
        out, fired = redact_payload({"k": text})
        assert "AAAA" not in out["k"] and fired == ["pem-private-key-truncated"]
        assert out["k"].startswith(self.END)  # the stray END line is left as text

    def test_a_block_far_into_a_long_string_is_redacted(self) -> None:
        text = "x " * 300_000 + f"{self.BEGIN}\nSECRETBODY\n{self.END}"
        out, fired = redact_payload({"k": text})
        assert "SECRETBODY" not in out["k"] and "pem-private-key" in fired


class TestUrlSchemeBound:
    def test_a_scheme_longer_than_the_bound_still_loses_its_credential(self) -> None:
        scheme = "a" * 50
        out, fired = redact_payload({"k": f" {scheme}://user:hunter2pass@host/x"})
        assert "hunter2pass" not in out["k"]
        assert "url-embedded-credential" in fired
