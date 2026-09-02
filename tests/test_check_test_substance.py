"""Tests for scripts/check_test_substance.py.

The instrument was wrong three times in a row on its first outing, and every
error pointed the same way: it called a CORRECT test assertion-free. That
direction matters. A tool auditing tests for substance, which reports real
tests as empty, produces a list nobody trusts and a percentage that reads as
worse than the truth -- and once the list is distrusted the two genuinely
vacuous tests in it are invisible.

Each false positive below is a real construct from this suite, kept as a
fixture so the correction cannot silently regress.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "check_test_substance",
    Path(__file__).resolve().parents[1] / "scripts" / "check_test_substance.py",
)
assert _SPEC and _SPEC.loader
substance = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(substance)


def verdict_of(source: str) -> str:
    """Classify the single test function in ``source``."""
    tree = ast.parse(source)
    func = next(n for n in ast.walk(tree) if substance._is_test_function(n))
    return substance.classify(func)[0]


def test_plain_assertion_is_capable():
    assert verdict_of("def test_x():\n    assert 1 + 1 == 2\n") == "CAPABLE"


def test_pytest_raises_is_capable():
    source = "def test_x():\n    with pytest.raises(ValueError):\n        f()\n"
    assert verdict_of(source) == "CAPABLE"


def test_manual_raises_idiom_with_assert_false_is_capable():
    """From test_user_ratings.py. The failure mechanism is in the TRY body,
    not the handler -- reading only the handler called this a swallow."""
    source = (
        "def test_reject_zero():\n"
        "    try:\n"
        "        record_rating('s', 0)\n"
        "        assert False, 'Should have raised'\n"
        "    except ValueError:\n"
        "        pass\n"
    )
    assert verdict_of(source) == "CAPABLE"


def test_manual_raises_idiom_with_trailing_raise_is_capable():
    """From test_compress_dedup_links_to_survivor.py and the Fable Round 8
    file. The `except: return` is the SUCCESS path; the trailing raise is
    reached only on failure."""
    source = (
        "def test_rejects_empty():\n"
        "    try:\n"
        "        link_supersession(old, '')\n"
        "    except ValueError:\n"
        "        return\n"
        "    raise AssertionError('Expected ValueError')\n"
    )
    assert verdict_of(source) == "CAPABLE"


def test_assertion_helper_call_is_capable():
    source = "def test_x():\n    _assert_wiring_holds(result)\n"
    assert verdict_of(source) == "CAPABLE"


def test_conditional_skip_is_capable_not_self_skip():
    """A platform guard is legitimate; only an unconditional skip is a
    finding."""
    source = (
        "def test_x():\n"
        "    if sys.platform == 'win32':\n"
        "        pytest.skip('posix only')\n"
        "    assert compute() == 3\n"
    )
    assert verdict_of(source) == "CAPABLE"


def test_unconditional_skip_is_flagged():
    source = "def test_x():\n    pytest.skip('not implemented')\n    assert False\n"
    assert verdict_of(source) == "SELF-SKIP"


def test_no_assertion_is_flagged_as_no_assert():
    source = "def test_module_importable():\n    import divineos.core.ledger\n"
    assert verdict_of(source) == "NO-ASSERT"


def test_name_claiming_a_behaviour_is_separated_from_plain_no_assert():
    """`test_entropy_drop_fires` and `test_module_importable` are both
    assertion-free and only one of them is a problem."""
    source = "def test_entropy_drop_fires():\n    anomalies = detect()\n    _ = anomalies\n"
    assert verdict_of(source) == "NAME-CLAIMS-MORE"


def test_constant_assertion_is_trivial_only():
    assert verdict_of("def test_x():\n    assert True\n") == "TRIVIAL-ONLY"


def test_constant_comparison_is_trivial_only():
    assert verdict_of("def test_x():\n    assert 1 == 1\n") == "TRIVIAL-ONLY"


def test_genuine_swallow_is_flagged():
    """No failure mechanism anywhere: the handler eats the error and the body
    has nothing that could fail."""
    source = (
        "def test_x():\n"
        "    try:\n"
        "        do_the_thing()\n"
        "    except Exception:\n"
        "        pass\n"
        "    assert result_exists()\n"
    )
    assert verdict_of(source) == "SWALLOWS"


def test_setup_tolerance_swallow_still_flagged_when_nothing_else_fails():
    source = (
        "def test_x():\n"
        "    try:\n"
        "        conn.execute('ALTER TABLE t ADD COLUMN c')\n"
        "    except Exception:\n"
        "        pass\n"
    )
    assert verdict_of(source) in {"SWALLOWS", "NO-ASSERT"}


def test_unparseable_file_fails_toward_flagging(tmp_path):
    """An unreadable test file is not a clean one."""
    bad = tmp_path / "test_broken.py"
    bad.write_text("def test_x(:\n    pass\n", encoding="utf-8")
    records = substance.audit_file(bad)
    assert [r["verdict"] for r in records] == ["UNPARSEABLE"]


def test_audit_file_reports_line_numbers(tmp_path):
    path = tmp_path / "test_sample.py"
    path.write_text("\n\ndef test_x():\n    assert True\n", encoding="utf-8")
    records = substance.audit_file(path)
    assert records[0]["line"] == 3


@pytest.mark.parametrize(
    "name,expected",
    [
        ("test_entropy_drop_fires", True),
        ("test_huge_result_truncated", True),
        ("test_toggle_bypasses_operators", True),
        ("test_module_importable", False),
        ("test_clear_missing_marker_is_safe", False),
        ("test_verbatim_in_source_passes", False),
    ],
)
def test_behaviour_claim_detection(name, expected):
    assert substance._name_claims_behaviour(name) is expected
