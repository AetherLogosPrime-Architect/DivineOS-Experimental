"""Operator approval by comment, including the head-commit time lookup.

The lookup is tested against a REAL `gh api` response shape rather than a
hand-fed timestamp. That distinction is the whole reason this file exists:
the first version of these tests passed a datetime straight into the
approval matcher, so `_head_commit_time` was never called, and it was
broken -- `gh --jq` prints the selected string raw and unquoted, which is
not valid JSON, so the parse failed and returned None. Every bare
confirmation was then refused for want of an ordering it could not read,
while the gate reported "no approval on the current commit."

A test that mocks past the call it is meant to cover proves the caller,
not the code.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ci_merge_review_check.py"


def _load():
    spec = importlib.util.spec_from_file_location("ci_merge_review_check", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


HEAD = "02a831014c492cc70b928fe3530bf789cdb3a4fb"
HEAD_TIME = "2026-08-15T00:21:36Z"

# The shape `gh api repos/{repo}/commits/{sha}` actually returns.
COMMIT_PAYLOAD = {"sha": HEAD, "commit": {"committer": {"date": HEAD_TIME}}}


def _with_comments(module, comments):
    def fake(args):
        if "/issues/" in args[1]:
            return comments
        return COMMIT_PAYLOAD

    module._gh_json = fake
    return module


def _comment(body: str, created_at: str, login: str = "AetherLogosPrime-Architect"):
    return {"body": body, "created_at": created_at, "user": {"login": login}}


def test_head_commit_time_parses_real_gh_payload():
    module = _load()
    module._gh_json = lambda args: COMMIT_PAYLOAD
    assert module._head_commit_time("o/r", HEAD) == datetime(
        2026, 8, 15, 0, 21, 36, tzinfo=timezone.utc
    )


def test_head_commit_time_none_when_payload_is_not_a_dict():
    """A raw string is what --jq produced, and it must not read as a time."""
    module = _load()
    module._gh_json = lambda args: HEAD_TIME
    assert module._head_commit_time("o/r", HEAD) is None


def test_bare_confirm_after_head_is_accepted():
    module = _with_comments(_load(), [_comment("i confirm", "2026-08-15T02:40:00Z")])
    assert module._fetch_comment_approvals("o/r", 429, HEAD)


def test_bare_confirm_before_head_is_refused():
    """Approval cannot inherit onto work written after it."""
    module = _with_comments(_load(), [_comment("i confirm", "2026-08-14T23:00:00Z")])
    assert module._fetch_comment_approvals("o/r", 429, HEAD) == []


def test_bare_confirm_refused_when_ordering_is_unavailable():
    module = _load()

    def fake(args):
        if "/issues/" in args[1]:
            return [_comment("i confirm", "2026-08-15T02:40:00Z")]
        return None  # commit lookup failed

    module._gh_json = fake
    assert module._fetch_comment_approvals("o/r", 429, HEAD) == []


def test_named_sha_does_not_need_ordering():
    """An old comment naming the current head is still a valid approval."""
    module = _with_comments(_load(), [_comment("MERGE-APPROVED: 02a83101", "2026-01-01T00:00:00Z")])
    assert module._fetch_comment_approvals("o/r", 429, HEAD)


def test_wrong_sha_is_refused():
    module = _with_comments(_load(), [_comment("MERGE-APPROVED: deadbeef", "2026-08-15T02:40:00Z")])
    assert module._fetch_comment_approvals("o/r", 429, HEAD) == []


def test_comment_without_an_approval_phrase_is_refused():
    module = _with_comments(_load(), [_comment("looks good to me", "2026-08-15T02:40:00Z")])
    assert module._fetch_comment_approvals("o/r", 429, HEAD) == []
