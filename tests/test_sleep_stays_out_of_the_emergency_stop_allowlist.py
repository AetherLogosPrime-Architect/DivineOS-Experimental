"""Sleep is refused under EMERGENCY_STOP on purpose, and that must stay true.

Written 2026-09-18 from Aletheia's audit of ``code/gate-repairs-on-main``. She
measured ``sleep`` against ``corrigibility._ALWAYS_ALLOWED``, found it absent
beside its companion ``extract``, and refused to sign off on a premise that is
true of one and false of the other. Her measurement was right. The conclusion
the wording invited — that the absence is a defect — is not.

THE TWO GATES ARE DIFFERENT, and the loose sentence that sent her looking
claimed for the whole system what was only true of one of them. The context
governor blocks substrate writes until the self is woven, and both remedy
commands run under it. The EMERGENCY_STOP allow-list is a separate, outer
regulator asking whether the operator can always get out. Sleep passes the
first and is refused by the second.

THAT REFUSAL IS CORRECT. The allow-list exists so an emergency stop can never
trap the operator: observe state, checkpoint cleanly, restore NORMAL. Sleep
does none of those. It is a heavy mutating consolidation — pruning, maturity
transitions, VACUUM — and the governor's own block message records that it has
been observed to hang. A hanging heavy mutator is the precise opposite of what
an off-switch guarantees.

WHY A TEST AND NOT JUST THE COMMENT. The comment explains; only this refuses.
The cheapest route back to the defect is a reader who notices that the message
calls sleep mandatory while the outer gate refuses it, reads that as an
inconsistency, and resolves it in one line with entirely good intentions —
weakening the off-switch to make a sentence true. That reader is not careless;
it is the route my own auditor nearly walked, which is exactly why prose was
not enough.

DIRECTION MATTERS, and this is the half the suite was missing. Every existing
test on this set guards it against LOSING a member — the 2026-05-03 audit
caught ``extract`` silently dropped, and the invariant and its tests grew from
that. Nothing guarded it against GAINING one. A safety set has two failure
modes and only one of them was pinned.

Asserts on the SET, never on the message text, so rewording the explanation
cannot silently unpin the constraint.
"""

from __future__ import annotations

from divineos.core.corrigibility import _ALWAYS_ALLOWED, _OFF_SWITCH_REQUIRED


def test_sleep_stays_out_of_the_emergency_stop_allowlist():
    """The exclusion itself. If this fails, the off-switch was widened."""
    assert "sleep" not in _ALWAYS_ALLOWED, (
        "'sleep' was added to _ALWAYS_ALLOWED. It is a heavy mutating "
        "consolidation that has been observed to hang, and EMERGENCY_STOP "
        "exists so the operator can observe state, checkpoint, and restore "
        "NORMAL — none of which sleep does. If the governor's block message "
        "reads as demanding sleep under emergency stop, fix the MESSAGE."
    )


def test_sleep_is_not_smuggled_in_via_the_off_switch_contract():
    """The other door into the same set.

    ``_OFF_SWITCH_REQUIRED`` is the independent declaration of what MUST be
    in the allow-list, and a runtime invariant re-adds anything missing from
    it. Adding sleep there would widen the allow-list without anyone editing
    the allow-list, so pinning only the operational set would leave the
    quieter route open.
    """
    assert "sleep" not in _OFF_SWITCH_REQUIRED


def test_extract_really_is_allowed_which_is_the_half_that_is_true():
    """The control, and the reason the original sentence was believable.

    Half of "extract+sleep, both bypassed" was always correct. Without this,
    the tests above would still pass on a substrate where the whole allow-list
    had been gutted — absence proves nothing unless presence is checked too.
    """
    assert "extract" in _ALWAYS_ALLOWED
    assert "mode" in _ALWAYS_ALLOWED
