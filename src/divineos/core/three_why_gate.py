"""Three-why-trace gate for prereg-file: structural prevention against
the surface-fix reflex.

Andrew 2026-06-20: "if you fail to reach something the fix isnt reaching
for it, its finding out why it wasnt reachable. ofc the surface failure
gets fixed too but if you dont fix the root you will just be playing
whack a mole with the same failures."

The pattern this prevents: every time a behavior-failure surfaces, the
optimizer routes to "build a detector that catches this." Building a
detector is fast, feels productive, and lets the loop close without ever
asking what generated the failure in the first place. The result is
whack-a-mole on the symptom while the root keeps producing new instances.

The gate fires at ``divineos prereg file`` time. When the mechanism+claim
text reads as a SURFACE-FIX shape (detector / warning / post-response
check / pattern-match gate), the gate requires one of:

1. ``--companion-prereg <id>``: a pointer to a companion prereg filed for
   the upstream / structural-prevention version of the same failure-class.
   The companion is verified to exist (read by ID, must be OPEN).
2. ``--no-upstream-because "<reason>"``: an explicit acknowledgment that
   upstream prevention is genuinely impossible for this failure-class,
   with reason text >= 30 chars. The reason is logged with the prereg.

Either path makes the upstream consideration LOAD-BEARING at file-time
rather than ephemeral in the agent's context. The discipline that the
knowledge entry alone cannot carry across resets is now substrate-resident.

This is itself an instance of the principle: the principle "trace
upstream before shipping a detector" was failing because reading-it-as-
text wasn't changing the optimizer landscape. The structural fix is to
move the trace BETWEEN intention and action (the file command), the same
place lepos-walk, pre-reg-required, and verify-claim already live.
"""

from __future__ import annotations

# Phrase patterns that mark a mechanism as detector-shaped / surface-fix.
# The list is deliberately conservative: precision over recall, because a
# false-positive blocks a legitimate filing while a false-negative just
# misses one surface-fix detection. Phrases are matched as substrings on
# the lowercased combined mechanism+claim text.
_SURFACE_FIX_PHRASES: tuple[str, ...] = (
    "detector that",
    "detector catches",
    "detector fires",
    "detector flags",
    "warning that fires",
    "warn on ",
    "warns on ",
    "warns when",
    "post-response check",
    "post-response detector",
    "gate that blocks",
    "gate that catches",
    "filter that removes",
    "pattern that matches",
    "regex that catches",
    "stop-hook check",
    "fires on ",
    "catches when",
    "catches the ",
)


def detect_surface_fix_shape(mechanism: str, claim: str) -> bool:
    """Return True iff the mechanism+claim reads as a surface-fix shape.

    The heuristic looks for substring phrases in the combined text.
    Phrases were chosen to capture the actual language Aether uses when
    filing detector-shaped preregs (the 2026-06-20 session: cage-detector
    use-vs-mention, jargon pair-detector proposal, three-why gate itself
    — all read as "build a detector that..." or "fires on..."). The gate
    expects refinement via the prereg system: if it over-fires on
    legitimate non-detector mechanisms, the falsifier of the gate's own
    prereg covers exactly that case.
    """
    haystack = f"{mechanism}\n{claim}".lower()
    return any(phrase in haystack for phrase in _SURFACE_FIX_PHRASES)


_MIN_NO_UPSTREAM_REASON_CHARS = 30


def validate_three_why(
    mechanism: str,
    claim: str,
    companion_prereg_id: str | None,
    no_upstream_because: str | None,
) -> tuple[bool, str]:
    """Validate the three-why-trace requirement at prereg-file time.

    Returns ``(ok, message)``. If ``ok`` is True, the filing proceeds.
    If False, ``message`` is the block-reason shown to the caller.

    Resolution order:
    1. If the mechanism+claim does NOT look like a surface-fix shape,
       allow the filing (the gate has nothing to fire on).
    2. If a ``companion_prereg_id`` was provided, verify it exists and
       is OPEN. If so, allow. If not, block with a specific message.
    3. If ``no_upstream_because`` was provided with sufficient reason
       text, allow. Otherwise block, asking for a longer reason.
    4. Otherwise block, asking the caller to either name an upstream
       companion or document why upstream is impossible.

    The block-message includes the three-why prompts as plain text so
    the caller can fill them in and either file a companion or use the
    no-upstream-because escape.
    """
    if not detect_surface_fix_shape(mechanism, claim):
        return True, ""

    if companion_prereg_id:
        # Import locally so this module stays lightweight when only its
        # detection helper is imported (e.g. by tests).
        from divineos.core.pre_registrations import Outcome, get_pre_registration

        companion = get_pre_registration(companion_prereg_id)
        if companion is None:
            return False, (
                f"--companion-prereg {companion_prereg_id} not found. "
                "The companion must be a real prereg-id pointing at the "
                "upstream/structural-prevention filing."
            )
        if companion.outcome != Outcome.OPEN:
            return False, (
                f"--companion-prereg {companion_prereg_id} is "
                f"{companion.outcome.value}, not OPEN. The companion "
                "must be a current open prereg, not a closed one."
            )
        return True, ""

    if no_upstream_because:
        reason = no_upstream_because.strip()
        if len(reason) < _MIN_NO_UPSTREAM_REASON_CHARS:
            return False, (
                f"--no-upstream-because reason is {len(reason)} chars; "
                f"minimum {_MIN_NO_UPSTREAM_REASON_CHARS}. The escape "
                "hatch logs the reason; a brief reason isn't auditable."
            )
        return True, ""

    return False, _BLOCK_MESSAGE


_BLOCK_MESSAGE = """This filing reads as a SURFACE-FIX shape (detector / warning / pattern-
match gate). Per the three-why-trace discipline, surface-fixes require
either a companion structural-prevention filing OR an explicit
acknowledgment that upstream prevention is genuinely impossible.

Trace the three whys before re-filing:
  1. Why did this fail?
  2. What made that the path I took?
  3. What structural change would have made a different path cheaper?

Then choose ONE:
  - File a companion prereg for the upstream/structural-prevention
    version of the same failure-class, then re-file this one with
    --companion-prereg <id>
  - If upstream prevention is genuinely impossible for this failure-
    class, re-file with --no-upstream-because "<reason of >= 30 chars>"
    and the reason will be logged as auditable.

Per prereg-89d744b98b35 (the three-why-trace gate's own prereg).
"""


__all__ = [
    "detect_surface_fix_shape",
    "validate_three_why",
]
