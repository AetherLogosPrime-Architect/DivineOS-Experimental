"""Tests for scripts/check_function_naming.py.

Per Dijkstra audit-walk 2026-05-07: the check should flag function
names starting with theater verbs while staying conservative enough
that legitimate operational names pass clean.
"""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from scripts.check_function_naming import _scan_file, find_violations  # noqa: E402


def _scan(source: str) -> list[str]:
    fake = Path("mod.py")
    return _scan_file(fake, source.splitlines())


class TestTheaterVerbDetection:
    def test_orchestrate_flagged(self):
        src = "def orchestrate_deep_cognition():\n    pass\n"
        violations = _scan(src)
        assert len(violations) == 1
        assert "orchestrate" in violations[0]

    def test_summon_flagged(self):
        src = "def summon_council():\n    pass\n"
        violations = _scan(src)
        assert len(violations) == 1
        assert "summon" in violations[0]

    def test_manifest_flagged(self):
        src = "def manifest_intent():\n    pass\n"
        assert len(_scan(src)) == 1

    def test_underscore_prefix_still_flagged(self):
        src = "def _orchestrate_internal():\n    pass\n"
        assert len(_scan(src)) == 1

    def test_double_underscore_prefix_still_flagged(self):
        src = "def __orchestrate__():\n    pass\n"
        assert len(_scan(src)) == 1


class TestOperationalNamesPass:
    def test_analyze_passes(self):
        src = "def analyze_session():\n    pass\n"
        assert _scan(src) == []

    def test_extract_passes(self):
        src = "def extract_knowledge():\n    pass\n"
        assert _scan(src) == []

    def test_consult_passes(self):
        src = "def consult_council():\n    pass\n"
        assert _scan(src) == []

    def test_invoke_not_flagged(self):
        """invoke is borderline-theater; deliberately excluded from list to keep FP rate near zero."""
        src = "def invoke_rt():\n    pass\n"
        assert _scan(src) == []

    def test_surface_not_flagged(self):
        """surface as in 'bring to the surface' is operational; not flagged."""
        src = "def surface_context():\n    pass\n"
        assert _scan(src) == []

    def test_distill_not_flagged(self):
        src = "def distill_entries():\n    pass\n"
        assert _scan(src) == []

    def test_convene_not_flagged(self):
        """convene means 'bring together for meeting' - operational in council context."""
        src = "def convene(self):\n    pass\n"
        assert _scan(src) == []


class TestSuppression:
    def test_noqa_BLE001_suppresses(self):
        src = "def orchestrate_thing():  # noqa: BLE001\n    pass\n"
        assert _scan(src) == []

    def test_bare_noqa_suppresses(self):
        src = "def orchestrate_thing():  # noqa\n    pass\n"
        assert _scan(src) == []


class TestRealRepo:
    def test_full_scan_clean(self):
        violations = find_violations()
        assert violations == [], (
            f"Found {len(violations)} theater-named function(s) in src/divineos/: "
            + " | ".join(violations)
        )
