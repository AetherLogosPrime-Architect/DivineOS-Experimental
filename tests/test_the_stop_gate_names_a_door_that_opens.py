"""The correction-shape gate's false-positive remedy must be one its neighbour lets through.

The gate prescribed `python scripts/label_correction_shape_false_positive.py`.
The correction-marker gate beside it matches bypasses as `divineos <subcommand>`
only -- deliberately, since widening it loosens a check on arbitrary shell -- so
the prescribed remedy was refused by the neighbour every time. `divineos
label-fire` was built on 2026-08-05 to be the passable form; the message never
learned its name. Hit live three times on 2026-09-15.

These tests read the prescription out of the hook's own message and hand it to
the neighbour's real matcher, so a message that drifts back to a shut door fails.
"""

from __future__ import annotations

import re
from pathlib import Path

from divineos.hooks.pre_tool_use_gate import _is_bypass_command

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / ".claude" / "hooks" / "correction-shape-v2-stop.sh"


def _prescribed_false_positive_command() -> str:
    text = HOOK.read_text(encoding="utf-8")
    match = re.search(r"label the fire with:\s*\n\s*(.+)", text)
    assert match, "the gate no longer says how to label a false positive"
    return match.group(1).strip()


def test_the_prescribed_remedy_passes_the_neighbouring_gate():
    command = _prescribed_false_positive_command().replace(
        '"<what class of MENTION was misread as USE, >= 40 chars>"',
        '"the reply named a correction as a topic rather than admitting a new one"',
    )
    assert _is_bypass_command(command), (
        f"the gate prescribes {command!r}, which the correction-marker gate refuses"
    )


def test_the_raw_script_form_is_the_shut_door_this_replaced():
    """The control: the old prescription really is refused, so the test above can fail."""
    assert not _is_bypass_command(
        'python scripts/label_correction_shape_false_positive.py --reason "x"'
    )
