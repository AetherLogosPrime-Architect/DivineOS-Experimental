"""Tests for `divineos ask --explain` (recall-explains-why).

Closes prereg-7bdd86bb0882: every search result must carry a one-line
WHY-it-surfaced breakdown so the operator can answer "why is this
here?" without reading opaque scores. The substrate primitive
(``core.active_memory.explain_importance``) was already shipped; the
CLI consumer on `divineos ask` was the missing wire.

Tests verify the contract:
- The --explain flag is accepted by the click command.
- When --explain is set, each rendered result includes a "why:" line.
- When --explain is NOT set, no "why:" line appears (no output bloat
  for the default path).
- The reasons listed map to entries in ``explain_importance``'s output
  (type label, confidence band, access count, recency, etc.).
"""

from __future__ import annotations

from click.testing import CliRunner


def _invoke_ask(args, monkeypatch):
    """Invoke `divineos ask` against a controlled in-memory result set
    so the test does not depend on whatever happens to be in the live
    knowledge store. Returns the CliRunner result object."""
    fake_results = [
        {
            "knowledge_id": "abc1234567890",
            "knowledge_type": "BOUNDARY",
            "content": "Compaction monitor must not over-fire on stale transcripts",
            "confidence": 0.95,
            "access_count": 12,
            "created_at": 1_700_000_000.0,
            "maturity": "CONFIRMED",
            "source_entity": "aether",
        },
    ]
    # Patch at the canonical location AND at the import-site in
    # knowledge_commands. The CLI module does `from ... import
    # search_knowledge` at module-top, which captures the function
    # into its own namespace at import time. When the full pytest
    # suite has already imported knowledge_commands (some other test
    # exercised the CLI), patching only the canonical location leaves
    # the CLI's bound reference stale — tests pass standalone but
    # fail in the full suite. Patching both closes the pollution gap.
    monkeypatch.setattr(
        "divineos.core.knowledge.search_knowledge",
        lambda *a, **k: fake_results,
    )
    monkeypatch.setattr(
        "divineos.cli.knowledge_commands.search_knowledge",
        lambda *a, **k: fake_results,
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

    from divineos.cli import cli

    runner = CliRunner()
    return runner.invoke(cli, ["ask", *args], catch_exceptions=False)


def test_ask_with_explain_includes_why_line(monkeypatch):
    """Per prereg-7bdd86bb0882 success criterion (b): divineos ask
    output shows breakdown alongside results."""
    result = _invoke_ask(["compaction", "--explain"], monkeypatch)
    assert result.exit_code == 0
    assert "why:" in result.output, (
        f"--explain must emit a 'why:' line per result. stdout:\n{result.output}"
    )


def test_ask_without_explain_omits_why_line(monkeypatch):
    """Default path stays clean — no output bloat for callers that
    didn't opt into the explanation surface."""
    result = _invoke_ask(["compaction"], monkeypatch)
    assert result.exit_code == 0
    assert "why:" not in result.output, (
        f"default path must not include the why-breakdown. stdout:\n{result.output}"
    )


def test_ask_explain_surfaces_known_reason_categories(monkeypatch):
    """The breakdown must include recognizable reason categories that
    map to explain_importance's output (type label, confidence band,
    access count, recency). This is the readability contract — the
    breakdown is useful only if the categories are themselves legible."""
    result = _invoke_ask(["compaction", "--explain"], monkeypatch)
    assert result.exit_code == 0
    out = result.output
    # The fake entry is BOUNDARY-typed with high confidence and 12 access counts.
    # explain_importance should mention type, confidence band, and access count.
    assert "BOUNDARY" in out
    assert "confidence" in out
    assert "accessed" in out


def test_ask_explain_fails_soft_when_explain_importance_raises(monkeypatch):
    """If explain_importance raises (substrate corruption, missing
    helper), the ask command must NOT crash — fail-soft so the
    explanation is opportunistic, not load-bearing for the search."""

    def boom(*a, **k):
        raise RuntimeError("simulated explain failure")

    monkeypatch.setattr(
        "divineos.core.active_memory.explain_importance",
        boom,
    )

    result = _invoke_ask(["compaction", "--explain"], monkeypatch)
    assert result.exit_code == 0
    # Even with the explainer broken, the result line itself must appear.
    assert "BOUNDARY" in result.output
