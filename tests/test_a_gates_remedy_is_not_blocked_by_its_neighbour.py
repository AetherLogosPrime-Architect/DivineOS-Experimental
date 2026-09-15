"""A gate's own prescribed remedy was refused by the gate standing next to it.

The correction-shape-v2 Stop gate prescribes exactly ONE remedy for a false
positive: run the labeller. That gate is a sibling of the correction-marker
gate, and each one sets its OWN marker. So a fire on the shape gate armed the
marker gate, and the marker gate then refused the shape gate's only prescribed
exit. It happened three times in one session, 2026-09-15, and each time the way
through was to clear the OTHER gate's marker first — a sequencing trick I had
to already know rather than a door anyone could find from the refusal text.

The clear-marker script had been exempted for exactly this reason weeks
earlier, with the general form written out in its comment. Its sibling was
never added. That is the finding worth more than the fix: naming a class in a
comment does not sweep the class, and the second instance sat unexempted
directly beside the first.

The assertion is a PAIR, not a single path, because asserting one path is
precisely what let the second one hide next to the passing one.
"""

from __future__ import annotations

import pytest

from divineos.hooks.pre_tool_use_gate import _is_bypass_command

_REASON = "x" * 60

# Every remedy the correction gates name in their own refusal text. A gate that
# prints an exit must not have that exit nailed shut by its neighbour, so this
# list is the contract: if a gate starts prescribing a new script, it belongs
# here on the same commit that starts prescribing it.
PRESCRIBED_REMEDIES = (
    f'python scripts/clear_correction_marker.py --reason "{_REASON}"',
    f'python scripts/label_correction_shape_false_positive.py --reason "{_REASON}"',
)


@pytest.mark.parametrize("cmd", PRESCRIBED_REMEDIES)
def test_a_prescribed_remedy_passes_the_neighbouring_gate(cmd: str) -> None:
    assert _is_bypass_command(cmd), (
        "a gate prints this command as the way out, and the gate beside it "
        f"refuses the command: {cmd}"
    )


def test_the_exemption_is_not_a_blanket_on_the_scripts_directory() -> None:
    """The remedy passes; a neighbour in the same directory does not.

    Without this, the test above would still pass if someone widened the
    exemption to every script under that folder, which would be a far larger
    hole wearing the same green tick.
    """
    assert not _is_bypass_command("python scripts/precommit.sh"), (
        "the exemption must name its remedies, not open the directory"
    )
    assert not _is_bypass_command("python scripts/replant_branch.py --dry-run"), (
        "the exemption must name its remedies, not open the directory"
    )
