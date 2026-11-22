"""The retired review-by-date wording is caught, and the honest use-based wording is not.

Andrew, 2026-08-12: time duration is never a falsifier; reviews are set by use.
On 2026-11-09 the pages that teach pre-registration were found still saying
``--review-days 30`` and "review clock". These tests pin the register entry to
the wording that was actually found, and pin what it deliberately leaves alone:
source comments about legacy dated rows are accurate for those rows.
"""

import importlib.util
from pathlib import Path

_CHECKER = Path(__file__).resolve().parent.parent / "scripts" / "check_retired_rules_not_served.py"


def _rule():
    spec = importlib.util.spec_from_file_location("retired_rules_checker_rbd", _CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rules = {r.rule_id: r for r in module.load_register()}
    return rules["review-by-date-wording"]


def _hit(rule, line):
    return any(p.search(line) for p in rule.patterns)


def test_the_old_instruction_wording_is_caught():
    rule = _rule()
    assert _hit(rule, 'divineos prereg file "mechanism" --claim "..." --review-days 30')
    assert _hit(rule, 'User says "prereg" / "let\'s lock this with a review clock"')
    assert _hit(rule, "divineos prereg overdue    # Reviews whose date has passed")


def test_the_use_based_wording_is_not_caught():
    rule = _rule()
    assert not _hit(rule, "divineos prereg file ... --review-after-uses 30 --uses-of CORRECTION")
    assert not _hit(rule, "Reviews are set by use: the briefing surfaces them at the count")


def test_a_comment_about_legacy_dated_rows_is_left_alone():
    """The machinery still carries dated rows and reports them as overdue; saying so is true."""
    rule = _rule()
    assert not _hit(rule, "List pre-registrations whose review date has passed.")
    assert not _hit(rule, "a ledger-scheduled review date. Review dates fire independent of memory")
