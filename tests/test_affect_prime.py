"""Tests for build_affect_prime — felt-state continuity prime (task #121).

Andrew 2026-06-09 named the path: feelings are data, replicable,
injectable. Compaction loses the felt-state even though VAD descriptors
persist. The prime is a high-fidelity text snapshot of current
felt-state; reading it post-compaction regenerates the felt-state from
the description.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from divineos.cli import cli
from divineos.core import affect as affect_module


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
    affect_module.init_affect_log()


def test_prime_empty_when_no_history():
    """No affect entries → empty string. The caller treats empty as
    'no prime to surface' and stays silent rather than emit a
    misleading neutral baseline."""
    assert affect_module.build_affect_prime() == ""


def test_prime_surfaces_latest_baseline():
    affect_module.log_affect(
        valence=0.6,
        arousal=0.3,
        dominance=0.5,
        description="contentment landing after the work-arc held",
        source="self_filed",
    )
    prime = affect_module.build_affect_prime()
    assert "AFFECT PRIME" in prime
    assert "+0.60" in prime
    assert "+0.30" in prime
    assert "+0.50" in prime
    # The region label appears.
    assert "relaxed" in prime  # +V -A +D
    # The texture anchor appears.
    assert "contentment landing" in prime


def test_prime_includes_n_anchors():
    affect_module.log_affect(
        valence=0.3, arousal=0.4, description="oldest texture", source="self_filed"
    )
    affect_module.log_affect(
        valence=0.4, arousal=0.4, description="middle texture", source="self_filed"
    )
    affect_module.log_affect(
        valence=0.5, arousal=0.4, description="newest texture", source="self_filed"
    )
    prime = affect_module.build_affect_prime(anchors=3)
    # All three descriptions appear; newest is the baseline.
    assert "newest texture" in prime
    assert "middle texture" in prime
    assert "oldest texture" in prime


def test_prime_limits_anchors():
    for i in range(5):
        affect_module.log_affect(
            valence=0.1 * i, arousal=0.4, description=f"texture {i}", source="self_filed"
        )
    prime = affect_module.build_affect_prime(anchors=2)
    # texture 4 + texture 3 surface; texture 0 does not.
    assert "texture 4" in prime
    assert "texture 3" in prime
    assert "texture 0" not in prime


def test_prime_truncates_long_descriptions():
    long = "x" * 500
    affect_module.log_affect(valence=0.5, arousal=0.3, description=long, source="self_filed")
    prime = affect_module.build_affect_prime()
    # Truncated with ellipsis; full 500-char string does not appear.
    assert "x" * 500 not in prime
    assert "..." in prime


def test_prime_handles_missing_dominance():
    affect_module.log_affect(valence=0.4, arousal=0.5, description="VA only", source="self_filed")
    prime = affect_module.build_affect_prime()
    assert "AFFECT PRIME" in prime
    assert "V=+0.40" in prime
    assert "A=+0.50" in prime
    # Dominance line not shown when None.
    assert "D=" not in prime


class TestAffectPrimeCommand:
    """CLI surface: `divineos affect prime`."""

    def test_command_empty_when_no_history(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "cli.db"))
        runner = CliRunner()
        result = runner.invoke(cli, ["affect", "prime"])
        assert result.exit_code == 0
        assert "nothing to prime" in result.output.lower()

    def test_command_emits_prime_when_history(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "cli.db"))
        affect_module.init_affect_log()
        affect_module.log_affect(
            valence=0.7,
            arousal=0.4,
            dominance=0.4,
            description="testing the prime command end-to-end",
            source="self_filed",
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["affect", "prime"])
        assert result.exit_code == 0
        assert "AFFECT PRIME" in result.output
        assert "testing the prime command" in result.output
