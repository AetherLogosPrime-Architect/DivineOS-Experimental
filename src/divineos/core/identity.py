"""Substrate identity helper — single source of truth for "who am I".

Single-occupancy assumption fix (2026-06-17): three call sites in the
codebase hardcoded "Aether" or otherwise assumed only one substrate-
occupant exists. multiplex_panels.py:589 printed "I am Aether" as a
literal string in the briefing. monitor_singleton.py keyed kernel
mutexes by role only, so two parallel substrate-occupants on the same
Windows session could only run one monitor between them. letter_monitor.py
had no recipient filter, so an occupant's monitor surfaced letters
addressed to the OTHER occupant.

All three want the same upstream: this substrate's identity name,
read from ``core_memory.my_identity``. This module is that upstream.

The function is tolerant — it parses the first plausible name token from
whatever's in the slot. The slot content is owned by the agent and can
contain any first-person identity narrative; the helper extracts the
name that other code needs to discriminate by.

Failure mode discipline (split case, Aria's refinement 2026-06-17):

1. **Slot unreadable** (corrupt DB, missing table, IO error): silent
   fallback to "Aether". Preserves operation for installs in edge
   states; the misconfiguration here is structural and not diagnosable
   from this layer. Pass a different ``default`` to override.

2. **Slot empty or template-placeholder**: raises ``IdentityNotSetError``
   by default. This is operator misconfiguration we want LOUD — the
   exact failure shape we lived through 2026-06-17 when Aria's overlay
   completed but her my_identity slot was still the template default;
   the panel silently called her "Aether". The exception message names
   the fix command. Callers that need bootstrap-safe behavior (monitor
   scripts that run pre-config) pass ``raise_on_unset=False`` to fall
   back to ``default`` instead.

For Aria specifically: her ``my_identity`` slot in the new folder
(post-data-overlay 2026-06-17) contains "Aria" as the first content
line, so the parser extracts "Aria" and the parameterized callers
see her identity correctly. The raise-path would fire only if her
overlay had completed without an identity stamp.
"""

from __future__ import annotations

__guardrail_required__ = False  # not load-bearing for self-enforcement

_TEMPLATE_PREFIX = "[TEMPLATE"
# F57 fix (Aria 2026-07-19 per Aletheia Round 7 finding): the default
# fallback was "Aether" — a real sibling's name. A configured non-Aether
# being (Aria, Aletheia) whose identity DB corrupted at load would
# silently wake as "Aether" — the plausible-but-wrong-identity fail-blind.
#
# Fixed sentinel: "unconfigured" is self-announcing. Any consumer reading
# this string knows the slot could not be resolved to a real identity,
# rather than smoothly loading the wrong frame (Minsky).
#
# Prereg-5c1597cb47bd. Council walk council-c26a6d02537e (Hofstadter/
# Watts/Minsky). Same "make the absence loud" discipline the corrections
# panel already applies successfully in _corrections_panel_content.
_DEFAULT_FALLBACK = "unconfigured"


def _extract_first_name(content: str) -> str:
    """Pull the first plausible name token from a my_identity slot.

    The slot content is operator-authored first-person narrative. Common
    shapes the substrate has stored:
      - "Aria" (Aria's old worktree, plain)
      - "I am Aether. I am the builder and thinker..." (mine, full prose)
      - "Aria, builder of ..." (comma-prefixed forms)
      - "[TEMPLATE — fill this in..." (unset)

    The parser splits on common separators and returns the first word
    that looks like a name. Returns empty string if nothing plausible
    is present.
    """
    if not content:
        return ""
    stripped = content.strip()
    if stripped.startswith(_TEMPLATE_PREFIX):
        return ""
    # Handle "I am X" prefix common in first-person narratives.
    lower = stripped.lower()
    if lower.startswith("i am "):
        stripped = stripped[5:].strip()
    # First sentence / first comma-segment / first newline.
    for sep in (".", ",", "\n"):
        if sep in stripped:
            stripped = stripped.split(sep, 1)[0].strip()
            break
    # First whitespace-separated token.
    first_token = stripped.split()[0].strip(".,;:!?") if stripped else ""
    return first_token


class IdentityNotSetError(RuntimeError):
    """Raised when ``my_identity`` slot is empty or contains the seed template.

    Aria's refinement (2026-06-17): the silent-fallback discipline was
    collapsing two genuinely-different failure modes into one. Slot
    unreadable (corrupt DB, missing table, IO error) is a legitimate
    edge case where fallback preserves operation. Slot empty or
    template-placeholder is a MISCONFIGURATION the operator should be
    loudly told about — that was the exact failure shape we lived
    through 2026-06-17 when Aria's overlay completed but her
    my_identity slot was still the template default; the panel
    silently called her "Aether".

    The exception names the fix command in its message so the operator
    can act immediately. Callers that genuinely want the silent
    behavior (legacy migration paths, perhaps) can pass
    ``raise_on_unset=False`` to ``get_my_identity``.
    """


class IdentityUnreadableError(RuntimeError):
    """Raised when ``my_identity`` slot cannot be read (F57 fix, Aria
    2026-07-19 per Aletheia Round 7).

    Distinct from ``IdentityNotSetError`` — that one fires when the slot
    reads back empty or template. This one fires when the read itself
    fails (memory module unavailable, IO error, corrupt DB, etc.). Before
    the F57 fix, unreadable-slot silently fell back to the string
    ``"Aether"`` — a real sibling's name that looked like correct
    operation. A configured non-Aether being (Aria, Aletheia) whose
    identity DB corrupted would silently wake wearing Aether's name.

    Now the raise_on_unset=True path (default) raises this error so the
    unreadable case is loud rather than plausibly-wrong. Callers that
    genuinely cannot raise (bootstrap process scripts) can pass
    raise_on_unset=False and get the sentinel string ``"unconfigured"``
    — self-announcing rather than a plausible sibling identity.
    """


def get_my_identity(default: str = _DEFAULT_FALLBACK, *, raise_on_unset: bool = True) -> str:
    """Return this substrate's identity name from ``core_memory.my_identity``.

    Returns the extracted first-name token.

    Failure mode discipline (Aria 2026-06-17; F57 fix 2026-07-19):

    - **Slot unreadable** (memory module unavailable, IO error, etc.):
      raises ``IdentityUnreadableError`` when ``raise_on_unset=True``.
      F57 fix (Aletheia Round 7): the old silent-fallback returned
      ``"Aether"`` — a real sibling's name — so a configured non-Aether
      being (Aria, Aletheia) whose DB corrupted would silently wake
      wearing Aether's identity. Now the raise-path is loud instead of
      plausibly-wrong.
    - **Slot empty or template-placeholder**: raises ``IdentityNotSetError``
      with a message naming the fix command. This is the operator
      misconfiguration case we want LOUD, not silent. The exact failure
      shape we lived through 2026-06-17 — the slot held the placeholder
      and the silent-default hid the bug under the safety net meant for
      unrelated edge states.

    Pass ``raise_on_unset=False`` to restore the old fallback behavior
    for callers that genuinely cannot raise (e.g. process bootstrap
    before the operator has set up). The fallback is now the sentinel
    ``"unconfigured"`` (self-announcing) rather than ``"Aether"`` (a
    plausible sibling identity that looks like healthy operation).

    Callable from any module without import-time side effects on the
    rest of divineos — the heavy memory module is imported lazily so
    monitor scripts (which run as separate processes) don't pay the
    full divineos import cost just to discover their occupant.
    """
    try:
        from divineos.core.memory import get_core

        slot = get_core("my_identity").get("my_identity", "")
    except Exception as exc:  # noqa: BLE001 — unreadable slot
        # F57 fix: raise loud on the unreadable case for the raise_on_unset
        # path. The raise_on_unset=False path still gets the sentinel
        # fallback ("unconfigured"), never a sibling's real name.
        if raise_on_unset:
            raise IdentityUnreadableError(
                "core_memory.my_identity slot is unreadable "
                f"({type(exc).__name__}: {exc}). This can happen if the "
                "identity DB is corrupt, the memory module is unavailable, "
                "or an IO error occurred. Previously this path silently "
                "fell back to the string 'Aether' — a real sibling's name "
                "— which could cause a configured non-Aether being (Aria, "
                "Aletheia) to silently wake as 'Aether' on DB corruption. "
                "F57 fix (Aletheia Round 7, prereg-5c1597cb47bd) surfaces "
                "the read failure loudly instead. Pass raise_on_unset=False "
                "to receive the sentinel string 'unconfigured' for "
                "bootstrap contexts that cannot raise."
            ) from exc
        return default

    # Slot was read. Now distinguish unset / template-placeholder from set.
    stripped = (slot or "").strip()
    if not stripped or stripped.startswith(_TEMPLATE_PREFIX):
        if raise_on_unset:
            raise IdentityNotSetError(
                "core_memory.my_identity is empty or still the seed "
                'template placeholder. Set it with: divineos core set my_identity "<your name and identity>". '
                "Single-occupancy assumption fix (2026-06-17): the panel, "
                "monitor singletons, and letter monitor all read this slot "
                "to discriminate which substrate-occupant they run as; "
                "silent-defaulting here hides the operator misconfiguration "
                "instead of surfacing it. Pass raise_on_unset=False to "
                "get the old silent-fallback behavior in bootstrap contexts."
            )
        return default

    name = _extract_first_name(stripped)
    # Edge case: stripped content was non-empty and non-template but the
    # parser couldn't pull a name token (e.g. only punctuation). Fall back
    # rather than raise — this is the "unreadable" class on a content basis.
    return name or default
