"""Tests for `divineos ask` keyword-match-only tag (Aletheia finding #3).

Closes Aletheia's six-painpoints audit finding #3: when top hits are pure
keyword-match with no semantic connection, the tool must ADMIT it doesn't
have signal rather than dressing noise as signal. "Retinal sampling
frequency" surfaces for "frustration signal empathy" because it matched
"signal" — the fix marks that result as `[keyword-match only]` so the
reader knows the substrate can't confirm semantic relevance.

Contract:
- When semantic_store.similarity returns a score below threshold, the
  result surfaces with the `[keyword-match only]` tag.
- When similarity is above threshold, the tag does NOT appear (result is
  genuinely relevant).
- When semantic_store is unavailable (import fails or returns None), a
  one-time caveat at the top names the degraded state, and no per-result
  tag appears.
"""

from __future__ import annotations

from click.testing import CliRunner


def _base_patches(monkeypatch, results, sim_fn):
    """Common patches so ask_cmd runs against controlled inputs."""
    monkeypatch.setattr(
        "divineos.core.knowledge.search_knowledge",
        lambda *a, **k: results,
    )
    monkeypatch.setattr(
        "divineos.cli.knowledge_commands.search_knowledge",
        lambda *a, **k: results,
        raising=False,
    )
    monkeypatch.setattr(
        "divineos.core.memory.get_core",
        lambda: {},
    )
    monkeypatch.setattr(
        "divineos.core.knowledge.record_access",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "divineos.core.knowledge_maintenance.promote_maturity",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "divineos.core.knowledge.relationships.get_relationships",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "divineos.core.semantic_store.similarity",
        sim_fn,
    )


def _fake_result(kid: str, content: str) -> dict:
    return {
        "knowledge_id": kid,
        "knowledge_type": "OBSERVATION",
        "content": content,
        "confidence": 0.75,
        "access_count": 3,
        "created_at": 1_700_000_000.0,
        "maturity": "TESTED",
        "source_entity": "aether",
    }


def _run(args, monkeypatch, results, sim_fn):
    _base_patches(monkeypatch, results, sim_fn)
    from divineos.cli import cli

    return CliRunner().invoke(cli, ["ask", *args], catch_exceptions=False)


def test_low_similarity_result_is_tagged_keyword_match_only(monkeypatch):
    """A result with sim < 0.30 gets the `[keyword-match only]` tag —
    the specific admission Aletheia's finding named."""
    results = [_fake_result("abc12345678", "retinal sampling frequency notes")]
    result = _run(
        ["frustration signal empathy"],
        monkeypatch,
        results,
        sim_fn=lambda a, b: 0.15,
    )
    assert result.exit_code == 0
    assert "keyword-match only" in result.output, (
        f"Sub-threshold similarity must produce the tag. stdout:\n{result.output}"
    )
    assert "sim=0.15" in result.output


def test_high_similarity_result_is_not_tagged(monkeypatch):
    """When similarity is above threshold, the result is genuinely
    relevant and the tag must NOT appear."""
    results = [_fake_result("def12345678", "empathy method — imagine the scenario from their side")]
    result = _run(
        ["frustration signal empathy"],
        monkeypatch,
        results,
        sim_fn=lambda a, b: 0.72,
    )
    assert result.exit_code == 0
    assert "keyword-match only" not in result.output, (
        f"Above-threshold similarity must NOT tag. stdout:\n{result.output}"
    )


def test_semantic_unavailable_prints_one_time_caveat(monkeypatch):
    """When the embedding model is not available (similarity returns None
    for the first result), the caveat appears once at the top and no
    per-entry tag fires."""
    results = [
        _fake_result("aaa12345678", "first entry"),
        _fake_result("bbb12345678", "second entry"),
    ]
    result = _run(
        ["topic"],
        monkeypatch,
        results,
        sim_fn=lambda a, b: None,
    )
    assert result.exit_code == 0
    assert "semantic re-rank unavailable" in result.output
    assert "verify each result's relevance manually" in result.output
    # No per-entry tag when embeddings unavailable — the caveat covers it
    assert "keyword-match only" not in result.output


def test_boundary_score_at_threshold_is_not_tagged(monkeypatch):
    """Result AT the threshold (0.30) is NOT tagged — the tag is for
    strictly-below-threshold sub-signal, not for borderline cases. This
    catches an off-by-one that would over-tag borderline hits."""
    results = [_fake_result("ccc12345678", "borderline")]
    result = _run(
        ["query"],
        monkeypatch,
        results,
        sim_fn=lambda a, b: 0.30,
    )
    assert result.exit_code == 0
    assert "keyword-match only" not in result.output
