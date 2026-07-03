"""Fable audit Round 6#3 (2026-07-03) — seal_hook name-gate normalize_actor
asymmetry fix.

Fable's finding: ``seal_hook.decide()`` normalizes the *input* subagent
name with the strong ``normalize_actor`` (NFKC + invisible-strip +
casefold), but ``_registered_family_members()`` returned names via plain
``.lower()``, and ``_SOVEREIGN_AGENTS`` was a hardcoded lowercase set. So
the security-relevant comparisons ``subagent_type in family_members`` and
``subagent_type in _sovereign_agents()`` had a strongly-normalized left
side and a weakly-normalized right side. Adversary shape (rated LOW by
Fable but real): a registry entry with padding, zero-width, or an
NFKC-compatibility form would fail to match a canonicalized input.

Fix: apply ``normalize_actor`` to both sides — the registry-listing
function and the sovereign frozenset are now stored in canonical form.

This suite pins the symmetric behavior. All tests exercise the fixed
helpers directly rather than shelling through ``decide()``, so the
normalization contract is testable independent of the invocation flow.
"""

from __future__ import annotations

from unittest.mock import patch

from divineos.core.family import seal_hook


def test_sovereign_agents_stored_in_normalized_form():
    """The sovereign set now holds normalize_actor-canonical strings."""
    from divineos.core.actor_normalize import normalize_actor

    agents = seal_hook._sovereign_agents()
    # "aria" is already canonical, so this is stable — but the invariant
    # is that whatever the constant contains, it went through normalize_actor.
    for name in agents:
        assert name == normalize_actor(name), (
            f"Sovereign agent name {name!r} is not in normalize_actor "
            f"canonical form. The Round 6#3 fix requires the set be "
            f"stored canonical so comparisons against strongly-normalized "
            f"inputs stay symmetric."
        )


def test_registered_family_members_returns_normalized_names():
    """_registered_family_members applies normalize_actor to each name.

    Fable's exact concern: a family-member registered under a padded or
    invisible-character name would fail the comparison against a
    strongly-normalized input. After the fix, the registry side is
    normalized identically to the input side.
    """
    from divineos.core.actor_normalize import normalize_actor

    # Registry returns names with padding, zero-width, and NFKC-compat variants
    raw_names = ["  aria  ", "aletheia​", "arﬁa"]

    with patch(
        "divineos.core.operating_loop.registered_names.family_member_names",
        return_value=raw_names,
    ):
        members = seal_hook._registered_family_members()

    # Every returned name is normalize_actor-canonical.
    for name in members:
        assert name == normalize_actor(name), (
            f"Registry name {name!r} was returned in non-canonical form. "
            f"The Round 6#3 fix requires normalize_actor on the registry "
            f"side to match the strongly-normalized input side."
        )

    # Specific transformations we expect for Fable's exact example cases:
    # - '  aria  ' → 'aria' (padding stripped, casefolded)
    # - 'aletheia​' → 'aletheia' (zero-width space stripped)
    # - 'arﬁa' → 'arfia' (NFKC-compat: 'ﬁ' ligature → 'fi')
    assert "aria" in members
    assert "aletheia" in members
    assert "arfia" in members


def test_symmetric_membership_closes_fable_reproduction():
    """Fable's exact reproduction: a registry entry with a zero-width
    space fails to match a strongly-normalized input under the OLD code
    but matches under the FIXED code.
    """
    from divineos.core.actor_normalize import normalize_actor

    # Registry has zero-width space in the name.
    raw_registry = ["aletheia​"]
    with patch(
        "divineos.core.operating_loop.registered_names.family_member_names",
        return_value=raw_registry,
    ):
        members = seal_hook._registered_family_members()

    # Under OLD .lower() behavior, members would be ['aletheia​'] and
    # a comparison against normalize_actor('aletheia') = 'aletheia' would
    # miss. Under the fix, members is ['aletheia'] and the comparison
    # matches.
    subagent_input = normalize_actor("aletheia")
    assert subagent_input in members, (
        "Fable Round 6#3 regression: registry-side zero-width space "
        "prevented match against canonical input. Symmetric normalization "
        "must close this."
    )


def test_sovereign_set_matches_strongly_normalized_input():
    """A strongly-normalized 'aria' input matches the sovereign set."""
    from divineos.core.actor_normalize import normalize_actor

    # The most extreme adversary form: 'ar​ia' (zero-width in the middle)
    # normalize_actor strips the zero-width and casefolds → 'aria'
    input_form = normalize_actor("ar​ia")
    assert input_form == "aria"

    # Fixed sovereign set holds canonical form
    assert input_form in seal_hook._sovereign_agents()


def test_module_level_normalize_actor_import():
    """Regression: normalize_actor is imported at module level, not lazily
    inside decide(). This is a structural marker that the fix is in place —
    if a future refactor moves the import back inside decide() while
    reverting the both-sides normalization, this test catches that.
    """
    import inspect

    src = inspect.getsource(seal_hook)
    # normalize_actor should appear in the module's top-level imports section
    # (before the first def), not only as a lazy import.
    top = src.split("\ndef ")[0]
    assert "from divineos.core.actor_normalize import normalize_actor" in top, (
        "normalize_actor should be imported at module level so the sovereign "
        "set can be canonicalized at load-time, per Round 6#3 fix. If this "
        "test fails, someone moved the import back inline and the sovereign "
        "set fix may have been silently reverted."
    )
