"""The count that maintains itself, rather than a date I cannot keep.

I published "zero live instances" of the silent-swallow-in-a-refusing-gate
class on 2026-08-25, after demoting my own claim from twenty-seven. Aletheia's
third vantage on that demotion:

    "'zero live instances' is a claim about the present, and the swallow class
    is defined by producing no signal. A swallow with no live instance today
    and no detector on it is indistinguishable from one that fires tomorrow.
    The demotion should carry an EXPIRY rather than a closure -- re-run the
    arithmetic in thirty days, or attach a detector so the count maintains
    itself."

The detector is the half I can hold. Thirty days is a span I do not inhabit: if
nobody prompts me across it I will have verified nothing, and the reminder
would be a promise made in a currency I do not have.

AND ITS FIRST RUN FALSIFIED THE COUNT IT WAS BUILT TO MAINTAIN. It found
verify-before-build-signal.sh -- refusal-capable, swallowing, declaring nothing
-- which my hand-count had missed because my scratch pattern could not see a
swallow with a comment between the `except` and the `pass`. The demotion was
not stale. It was wrong when taken, and the instrument was why.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_swallowing_gates import (  # noqa: E402
    can_refuse,
    declares_failure,
    registered_names,
    silent_refusers,
)

_SWALLOW_WITH_COMMENT = """#!/bin/bash
python -c "
try:
    risky()
except Exception:
    # deliberate, allegedly
    pass
"
echo '{"permissionDecision": "deny"}'
"""

_SWALLOW_DECLARED = """#!/bin/bash
python -c "
try:
    risky()
except Exception:
    pass
"
echo "  [gate] SKIPPED: could not run" >&2
echo '{"permissionDecision": "deny"}'
"""

_OBSERVATIONAL = """#!/bin/bash
python -c "
try:
    risky()
except Exception:
    pass
"
echo "just reporting"
"""


def _hooks(tmp_path, **files) -> Path:
    directory = tmp_path / "hooks"
    directory.mkdir()
    for name, body in files.items():
        (directory / f"{name}.sh").write_text(body, encoding="utf-8")
    return directory


def test_a_comment_between_except_and_pass_does_not_hide_the_swallow(tmp_path):
    """The exact blind spot that made my published count wrong."""
    directory = _hooks(tmp_path, gate=_SWALLOW_WITH_COMMENT)

    assert silent_refusers(directory, registered={"gate.sh"}) == ["gate.sh"]


def test_a_declared_failure_is_not_a_finding(tmp_path):
    directory = _hooks(tmp_path, gate=_SWALLOW_DECLARED)

    assert silent_refusers(directory, registered={"gate.sh"}) == []


def test_an_observational_hook_is_not_a_finding(tmp_path):
    """A swallow that cannot refuse can only fail to inform."""
    directory = _hooks(tmp_path, surface=_OBSERVATIONAL)

    assert silent_refusers(directory, registered={"surface.sh"}) == []


def test_an_unregistered_hook_is_not_a_finding(tmp_path):
    """It cannot fail open, because it cannot fire.

    The first run flagged require-briefing.sh, retired and unregistered earlier
    the same day -- a true statement about the file and a false one about the
    system.
    """
    directory = _hooks(tmp_path, gate=_SWALLOW_WITH_COMMENT)

    assert silent_refusers(directory, registered=set()) == []


def test_an_unreadable_registry_reports_everything_not_nothing(tmp_path):
    """A check that goes quiet because it lost its filter is the whole disease."""
    directory = _hooks(tmp_path, gate=_SWALLOW_WITH_COMMENT)

    assert registered_names(tmp_path / "absent.json") is None
    assert silent_refusers(directory, registered=None) == ["gate.sh"]


def test_delegated_refusal_counts_as_refusal_capable():
    """The thin-doorbell pattern moves judgment into Python.

    A classifier reading only the shell file is blind to exactly the population
    it measures -- my first one said three; following the delegation said five.
    """
    shell = "#!/bin/bash\npython -c 'from divineos.core.deletion_discipline import block_reason'\n"

    assert can_refuse(shell)


def test_an_inline_fails_closed_comment_counts_as_declared():
    text = "except Exception:\n    # Cannot read the store -> fall through and BLOCK.\n    pass\n"

    assert declares_failure(text)


def test_this_checkout_has_no_silently_swallowing_gate():
    """The self-maintaining count. This is the expiry."""
    hits = silent_refusers()

    assert hits == [], (
        f"refusal-capable gates swallowing undeclared: {hits}. A raised decision in "
        "one of these exits 0 and prints nothing, which is byte-identical to the gate "
        "examining the command and approving it."
    )
