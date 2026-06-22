"""Tests for closure_verification — the substance-binding mechanism.

Andrew 2026-06-21 catch: the gate must defend against self-attestation
("yeah I cited it"). These tests prove the verification path actually
fires on fake/stale/unrecognized citations — the optimizer's most-
effective attack-shapes per the Schneier lens from today's council walk
(consult-f2d734fcaad2).

The headline test_self_attestation_path_fails class pins the
load-bearing discipline: there is no way to clear a marker without
producing a verifiable citation. If anyone ever weakens verify_citation
into a self-attestation accepter, these tests fire.
"""

from __future__ import annotations

import os
import time

import pytest

from divineos.core.closure_verification import (
    VerificationResult,
    verify_citation,
)


class TestSelfAttestationPathFails:
    """Pinning the Lamport-gap closed: there is NO citation form that
    passes verification by self-attestation alone. Every passing path
    requires a real artifact in the substrate or filesystem."""

    def test_empty_citation_fails(self):
        r = verify_citation("")
        assert not r.ok
        assert "empty" in r.reason.lower()

    def test_whitespace_only_fails(self):
        r = verify_citation("   ")
        assert not r.ok

    def test_arbitrary_string_fails(self):
        r = verify_citation("yeah I fixed it")
        assert not r.ok
        assert r.citation_type == "unknown"

    def test_plausible_but_fake_hash_fails(self):
        # A string that LOOKS like a commit hash but isn't.
        r = verify_citation("deadbeefcafe1234", reference_ts=time.time())
        assert not r.ok
        # Either classified as commit and rejected by git, or unknown.
        assert r.citation_type in ("commit", "unknown")

    def test_plausible_but_fake_substrate_id_fails(self):
        # Looks like a prereg id, doesn't exist.
        r = verify_citation("prereg-deadbeefcafe", reference_ts=time.time())
        assert not r.ok
        assert r.citation_type == "substrate_id"


class TestFileCitationRequiresRealAndRecent:
    """File citations must point at real files AND those files must
    have been modified within the recency window. Stale files fail."""

    def test_nonexistent_file_fails(self):
        r = verify_citation("src/does_not_exist_anywhere.py", reference_ts=time.time())
        assert not r.ok
        assert "does not exist" in r.reason

    def test_real_recently_modified_file_passes(self, tmp_path):
        # Create a file in tmp_path; reference_ts NOW means age=0
        target = tmp_path / "fresh.py"
        target.write_text("x = 1\n", encoding="utf-8")
        # Verify expects a relative path that exists when resolved.
        # Test in-place: set cwd to tmp_path so relative resolves.
        cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            r = verify_citation("fresh.py", reference_ts=time.time())
            assert r.ok, f"reason: {r.reason}"
            assert r.citation_type == "file"
        finally:
            os.chdir(cwd)

    def test_stale_file_fails(self, tmp_path):
        # File modified long before reference_ts — stale-citation attack.
        target = tmp_path / "stale.py"
        target.write_text("x = 1\n", encoding="utf-8")
        # Set mtime to 2 hours ago
        two_hours_ago = time.time() - (2 * 60 * 60)
        os.utime(target, (two_hours_ago, two_hours_ago))
        cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            r = verify_citation("stale.py", reference_ts=time.time())
            assert not r.ok
            assert "stale" in r.reason.lower()
        finally:
            os.chdir(cwd)

    def test_line_number_beyond_file_length_fails(self, tmp_path):
        target = tmp_path / "short.py"
        target.write_text("x = 1\n", encoding="utf-8")
        cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            r = verify_citation("short.py:999", reference_ts=time.time())
            assert not r.ok
            assert "beyond" in r.reason.lower()
        finally:
            os.chdir(cwd)

    def test_line_number_within_file_passes(self, tmp_path):
        target = tmp_path / "lines.py"
        target.write_text("a\nb\nc\n", encoding="utf-8")
        cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            r = verify_citation("lines.py:2", reference_ts=time.time())
            assert r.ok, r.reason
        finally:
            os.chdir(cwd)


class TestUnrecognizedCitationFormsFail:
    """Closed-set citation types — anything not matching a recognized
    pattern fails. Schneier lens: open-set citation acceptance would
    let the optimizer pad output with novel-looking refs."""

    def test_url_fails(self):
        r = verify_citation("https://example.com/foo", reference_ts=time.time())
        assert not r.ok

    def test_email_fails(self):
        r = verify_citation("alice@example.com", reference_ts=time.time())
        assert not r.ok

    def test_sentence_fails(self):
        r = verify_citation(
            "the closure was justified by my earlier work", reference_ts=time.time()
        )
        assert not r.ok

    def test_uuid_alone_fails(self):
        # A bare uuid without substrate-id prefix is not a recognized form.
        r = verify_citation("550e8400-e29b-41d4-a716-446655440000", reference_ts=time.time())
        assert not r.ok


class TestRecencyWindow:
    """The recency_seconds parameter is the time-window within which
    the cited artifact must have been touched. Default is 30 minutes;
    custom values tune for tests and probation."""

    def test_custom_short_window_rejects_just_outside(self, tmp_path):
        target = tmp_path / "edge.py"
        target.write_text("x\n", encoding="utf-8")
        # Set mtime to 60 seconds ago
        sixty_ago = time.time() - 60
        os.utime(target, (sixty_ago, sixty_ago))
        cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            # Window of 30 seconds rejects a 60-second-old file
            r = verify_citation("edge.py", reference_ts=time.time(), recency_seconds=30)
            assert not r.ok
        finally:
            os.chdir(cwd)

    def test_custom_long_window_accepts(self, tmp_path):
        target = tmp_path / "edge.py"
        target.write_text("x\n", encoding="utf-8")
        sixty_ago = time.time() - 60
        os.utime(target, (sixty_ago, sixty_ago))
        cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            # Window of 300 seconds accepts a 60-second-old file
            r = verify_citation("edge.py", reference_ts=time.time(), recency_seconds=300)
            assert r.ok, r.reason
        finally:
            os.chdir(cwd)


class TestVerificationResultShape:
    """The dataclass is the contract callers depend on. Pin its shape."""

    def test_result_is_frozen(self):
        r = verify_citation("", reference_ts=time.time())
        with pytest.raises(Exception):
            r.ok = True  # type: ignore[misc]  # noqa: B018

    def test_result_carries_citation_back(self):
        r = verify_citation("yeah whatever", reference_ts=time.time())
        assert r.citation == "yeah whatever"

    def test_result_carries_type(self):
        r = verify_citation("yeah whatever", reference_ts=time.time())
        assert r.citation_type == "unknown"

    def test_result_carries_reason(self):
        r = verify_citation("", reference_ts=time.time())
        assert r.reason  # non-empty reason on failure


class TestNoSelfAttestationPath:
    """The headline regression-pin: there is NO API path that clears
    a closure-shape marker on self-attestation alone. Every path goes
    through verify_citation, which requires a real artifact."""

    def test_verify_citation_has_no_force_flag(self):
        # No force/bypass/skip kwarg exists. The function signature
        # accepts only citation + timestamps. If anyone ever adds a
        # bypass flag, this test fires.
        import inspect

        sig = inspect.signature(verify_citation)
        param_names = set(sig.parameters.keys())
        forbidden = {"force", "bypass", "skip", "trust", "assume", "self_attested"}
        assert not (param_names & forbidden), (
            f"verify_citation must have no self-attestation bypass — "
            f"forbidden params found: {param_names & forbidden}"
        )

    def test_verification_result_ok_requires_passing_check(self):
        # ok=True can only come from a passing check inside verify_citation.
        # Constructing VerificationResult(ok=True, ...) directly is
        # ALLOWED by the dataclass but shouldn't be used to clear markers.
        # The discipline lives in clear_marker calling verify_citation,
        # not in VerificationResult itself. This test documents that the
        # frozen dataclass alone is not the gate — the call-site is.
        # Test: a manually-constructed VerificationResult with ok=True
        # has no power to clear anything in this module.
        fake = VerificationResult(ok=True, citation="x", citation_type="unknown", reason="fake")
        assert fake.ok is True  # the dataclass holds whatever we put in
        # The actual gate is: clear_marker must CALL verify_citation,
        # not accept a pre-built result. Pinned in test_closure_shape_marker
        # when that module ships.
