"""Tests for scripts/check_broad_exceptions.py (extended scan).

2026-05-07: extended from single-pattern (Exception only) to three
patterns per Dijkstra's audit-walk observation. Tests the AST-based
detection of all three shapes.
"""

from __future__ import annotations

import sys
from pathlib import Path

# scripts/ isn't a package — add project root to sys.path
_project_root = str(Path(__file__).parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from scripts.check_broad_exceptions import _find_in_tree  # noqa: E402


def _scan(source: str) -> list[str]:
    """Scan a source string as if it were a file at fake path 'mod.py'."""
    fake = Path("mod.py")
    return _find_in_tree(fake, source.splitlines())


class TestExceptException:
    def test_flags_unmarked(self):
        src = "try:\n    x = 1\nexcept Exception:\n    pass\n"
        violations = _scan(src)
        assert len(violations) == 1
        assert "'except Exception'" in violations[0]

    def test_skips_with_noqa(self):
        src = "try:\n    x = 1\nexcept Exception:  # noqa: BLE001\n    pass\n"
        assert _scan(src) == []

    def test_skips_specific_exception(self):
        src = "try:\n    x = 1\nexcept ValueError:\n    pass\n"
        assert _scan(src) == []


class TestBareExcept:
    def test_flags_bare_except(self):
        src = "try:\n    x = 1\nexcept:\n    pass\n"
        violations = _scan(src)
        assert len(violations) == 1
        assert "bare 'except:'" in violations[0]

    def test_skips_with_noqa(self):
        src = "try:\n    x = 1\nexcept:  # noqa: BLE001\n    pass\n"
        assert _scan(src) == []


class TestRaiseFromNone:
    def test_flags_raise_from_none(self):
        src = (
            "try:\n"
            "    x = int('foo')\n"
            "except ValueError:\n"
            "    raise RuntimeError('bad') from None\n"
        )
        violations = _scan(src)
        assert len(violations) == 1
        assert "from None" in violations[0]
        assert "context-swallowing" in violations[0]

    def test_skips_with_noqa(self):
        src = (
            "try:\n"
            "    x = int('foo')\n"
            "except ValueError:\n"
            "    raise RuntimeError('bad') from None  # noqa: BLE001\n"
        )
        assert _scan(src) == []

    def test_skips_raise_from_other(self):
        """raise X from other_exc preserves chain — fine."""
        src = (
            "try:\n"
            "    x = int('foo')\n"
            "except ValueError as e:\n"
            "    raise RuntimeError('bad') from e\n"
        )
        assert _scan(src) == []

    def test_skips_implicit_chain(self):
        """Plain raise without 'from' preserves implicit chain."""
        src = "try:\n    x = int('foo')\nexcept ValueError:\n    raise RuntimeError('bad')\n"
        assert _scan(src) == []


class TestCombined:
    def test_multiple_violations_in_one_file(self):
        src = (
            "try:\n"
            "    x = 1\n"
            "except Exception:\n"
            "    pass\n"
            "try:\n"
            "    y = 2\n"
            "except:\n"
            "    pass\n"
            "try:\n"
            "    z = 3\n"
            "except KeyError:\n"
            "    raise ValueError('z') from None\n"
        )
        violations = _scan(src)
        assert len(violations) == 3
        kinds = " ".join(violations)
        assert "'except Exception'" in kinds
        assert "bare 'except:'" in kinds
        assert "from None" in kinds


class TestRealRepoPasses:
    """The full src/divineos/ tree should pass after this PR."""

    def test_full_scan_clean(self):
        from scripts.check_broad_exceptions import find_violations

        violations = find_violations()
        assert violations == [], f"Found {len(violations)} unsuppressed violations:\n" + "\n".join(
            violations
        )
