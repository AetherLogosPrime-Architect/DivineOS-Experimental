r"""Trailer-grammar regression tests for the multi-party-review gate.

Fixed 2026-07-31. Two gates read the same `External-Review:` trailer line and
wanted incompatible grammars:

  * ``scripts/ci_check_guardrail_trailer.sh`` expects
    ``External-Review: <round-id> tree-hash:<40-hex>``, reads the tree-hash
    out of the TRAILER, and warns when it is absent ("DEPRECATED: trailer
    should include tree-hash for substance binding").
  * ``scripts/check_multi_party_review.py`` matched ``(\S+)\s*$`` — round-id
    as the only token on the line — and reads the tree-hash out of the ROUND
    DESCRIPTION instead.

So no single trailer satisfied both. Satisfy the shell gate and this one
reported *"Guardrail files staged without External-Review trailer"* — missing,
not malformed — which is why the failure read as "you forgot the trailer" to
an operator who had just written one.

Measured against ``validate()`` before the change:

    External-Review: round-77a5374003e5                     -> PASS
    External-Review: round-77a5374003e5 tree-hash:f9c0112b… -> BLOCK

The pattern now tolerates trailing tokens, so either gate's guidance clears
both. Tree-hash sourcing is unchanged: this gate still reads the round
description, which is where ``divineos audit submit-round`` records it.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

_GATE = Path(__file__).resolve().parents[1] / "scripts" / "check_multi_party_review.py"
_RID = "round-77a5374003e5"
_TREE = "f9c0112b293a411cde8982f4b74f971c422d2d17"


def _trailer_pattern() -> re.Pattern[str]:
    spec = importlib.util.spec_from_file_location("_mpr_grammar", _GATE)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._TRAILER_PATTERN


def _parse(line: str) -> re.Match[str] | None:
    return _trailer_pattern().search(f"subject\n\n{line}\n")


class TestTrailerGrammarReconciliation:
    def test_bare_round_id_parses(self) -> None:
        m = _parse(f"External-Review: {_RID}")
        assert m is not None
        assert m.group(1) == _RID

    def test_round_id_with_tree_hash_parses(self) -> None:
        """The form the shell gate requires. Previously matched nothing."""
        m = _parse(f"External-Review: {_RID} tree-hash:{_TREE}")
        assert m is not None, "the other gate's required form must parse here too"
        assert m.group(1) == _RID

    def test_round_id_is_captured_not_the_whole_line(self) -> None:
        """Widening must not smuggle trailing tokens into the captured id.

        If the round-id captured as "round-x tree-hash:..." the store lookup
        would never find the round, and the gate would block with
        "round not found" — trading one confusing failure for another.
        """
        m = _parse(f"External-Review: {_RID} tree-hash:{_TREE}")
        assert m is not None
        assert "tree-hash" not in m.group(1)
        assert " " not in m.group(1)

    def test_still_requires_the_trailer_key(self) -> None:
        """Tolerating trailing tokens must not tolerate a missing trailer."""
        assert _parse(f"Reviewed-By: {_RID}") is None
        assert _parse(_RID) is None
