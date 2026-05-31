"""Tests for merge_review_gate — operator-anchored merge approval.

Adversarial by design: each test is an attempt to get a merge approved that
SHOULDN'T be, plus the happy path. A security gate whose tests only check the
happy path is theatre.

Design (Andrew 2026-05-30): the unforgeable keystone is the OPERATOR's GitHub
approval (the agent holds no credentials for it). Aletheia is a Claude web
instance with no GitHub account — her audit is relayed by the operator, whose
approval encodes her confirm. So the gate requires: operator APPROVED on the
head commit + a named, actually-logged audit round. Expensive-to-game, not
impossible; always bypassable. Purpose is alignment, not error-prevention.
"""

from __future__ import annotations

from divineos.core.merge_review_gate import (
    MergeReviewConfig,
    Review,
    has_round_reference,
    load_config,
    verify_merge,
)

HEAD = "abc123def456"
CONFIG = MergeReviewConfig(operator_logins=frozenset({"andrew"}))
BODY = "Some PR description.\n\nExternal-Review: round-33cead0d7ac7"


def test_happy_path_operator_approved_and_round_logged():
    reviews = [Review("andrew", "APPROVED", HEAD)]
    ok, msg = verify_merge(reviews, HEAD, BODY, CONFIG, round_is_logged=True)
    assert ok, msg


def test_no_operator_approval_fails():
    reviews = [Review("someone-else", "APPROVED", HEAD)]
    ok, msg = verify_merge(reviews, HEAD, BODY, CONFIG, round_is_logged=True)
    assert not ok
    assert "operator" in msg.lower()


def test_operator_approval_but_no_round_reference_fails():
    reviews = [Review("andrew", "APPROVED", HEAD)]
    ok, msg = verify_merge(reviews, HEAD, "no trailer here", CONFIG, round_is_logged=True)
    assert not ok
    assert "external-review" in msg.lower() or "named" in msg.lower()


def test_round_referenced_but_not_logged_fails():
    # A fabricated round id: named in the body, but no such round exists.
    reviews = [Review("andrew", "APPROVED", HEAD)]
    ok, msg = verify_merge(reviews, HEAD, BODY, CONFIG, round_is_logged=False)
    assert not ok
    assert "not present" in msg.lower() or "fabricated" in msg.lower()


def test_stale_approval_on_old_commit_does_not_count():
    reviews = [Review("andrew", "APPROVED", "oldsha000")]
    ok, _ = verify_merge(reviews, HEAD, BODY, CONFIG, round_is_logged=True)
    assert not ok, "approval of a different commit must not authorize HEAD"


def test_non_approved_states_ignored():
    reviews = [
        Review("andrew", "COMMENTED", HEAD),
        Review("andrew", "CHANGES_REQUESTED", HEAD),
    ]
    ok, _ = verify_merge(reviews, HEAD, BODY, CONFIG, round_is_logged=True)
    assert not ok


def test_dismissed_approval_does_not_count():
    reviews = [Review("andrew", "DISMISSED", HEAD)]
    ok, _ = verify_merge(reviews, HEAD, BODY, CONFIG, round_is_logged=True)
    assert not ok


def test_empty_roster_fails_closed():
    cfg = MergeReviewConfig(operator_logins=frozenset())
    reviews = [Review("andrew", "APPROVED", HEAD)]
    ok, _ = verify_merge(reviews, HEAD, BODY, cfg, round_is_logged=True)
    assert not ok, "an empty operator roster must never authorize a merge"


def test_missing_head_sha_fails_closed():
    reviews = [Review("andrew", "APPROVED", HEAD)]
    ok, _ = verify_merge(reviews, "", BODY, CONFIG, round_is_logged=True)
    assert not ok


def test_agent_cannot_self_approve_with_non_operator_login():
    # The agent pushing an approval from any account NOT in the operator
    # roster gains nothing — the keystone is operator-login-specific.
    reviews = [Review("aether-bot", "APPROVED", HEAD)]
    ok, _ = verify_merge(reviews, HEAD, BODY, CONFIG, round_is_logged=True)
    assert not ok


def test_case_insensitive_login_and_state():
    reviews = [Review("Andrew", "approved", HEAD.upper())]
    ok, msg = verify_merge(reviews, HEAD, BODY, CONFIG, round_is_logged=True)
    assert ok, msg


def test_round_reference_found_in_commit_text():
    assert has_round_reference("foo\nExternal-Review: round-xyz\nbar") == "round-xyz"
    assert has_round_reference("no reference here") is None


def test_load_config_operator_key():
    cfg = load_config('{"operator": ["Andrew"]}')
    assert "andrew" in cfg.operator_logins


def test_load_config_backcompat_user_key():
    cfg = load_config('{"user": ["andrew"]}')
    assert "andrew" in cfg.operator_logins


def test_load_config_ignores_external_ai_key():
    # The old external_ai roster must no longer grant approval power.
    cfg = load_config('{"operator": ["andrew"], "external_ai": ["aletheia-bot"]}')
    assert cfg.operator_logins == frozenset({"andrew"})


def test_load_config_malformed_fails_closed():
    cfg = load_config("not json{{")
    assert cfg.operator_logins == frozenset()
