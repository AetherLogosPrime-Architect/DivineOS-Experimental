"""Structural test — every Gate 1.48 address-command must bypass the gate.

Aletheia round-5cdc2f48c642 Finding 37 named the class-level rule:
when adding a hard-block gate, the address-commands the block message
names as recovery paths MUST be in the bypass list. Otherwise the
gate blocks its own remedy — the catch-22 pattern that originated
with the `learn` block on 2026-04-23 (gate fires on correction →
`learn` blocked → correction-marker can never clear).

This test enforces the rule structurally for Gate 1.48 (stale-
engagement). It walks the block_message rendering for every area
defined in stale_engagement._AREA_ADDRESS_EVENTS, extracts every
`divineos <subcmd>` reference, and asserts that each first subcommand
token is in _BYPASS_DIVINEOS_SUBCOMMANDS.

If this test fails, the gate has acquired an address-command that
isn't in the bypass list — re-introducing the catch-22 risk.

THIS TEST IS THE CLASS-FIX. It converts what was a convention
("remember to bypass address commands") into a structural requirement
("commits that violate this rule fail CI").
"""

from __future__ import annotations

import re

from divineos.core.stale_engagement import (
    _AREA_ADDRESS_EVENTS,
    block_message,
)
from divineos.hooks.pre_tool_use_gate import _BYPASS_DIVINEOS_SUBCOMMANDS


_DIVINEOS_SUBCMD_RE = re.compile(r"\bdivineos\s+(\w[\w-]*)")


def _first_subcommands_in_block_message() -> set[str]:
    """Render block_message for every known area; extract every
    divineos-subcommand referenced; return the set of FIRST tokens."""
    msg = block_message(list(_AREA_ADDRESS_EVENTS.keys()))
    return {m.group(1) for m in _DIVINEOS_SUBCMD_RE.finditer(msg)}


def test_every_address_command_in_block_message_is_in_bypass() -> None:
    """LOAD-BEARING: every divineos-subcommand referenced in a Gate
    1.48 block message must be in _BYPASS_DIVINEOS_SUBCOMMANDS,
    otherwise the gate denies its own remedy.

    Class-fix per Aletheia round-5cdc2f48c642 Finding 37. The
    convention 'remember to bypass address commands' failed to apply
    on Gate 1.48 ship (2026-05-14); this test makes the rule
    structural.
    """
    referenced = _first_subcommands_in_block_message()
    missing = referenced - _BYPASS_DIVINEOS_SUBCOMMANDS
    assert not missing, (
        f"Gate 1.48 catch-22 risk: block_message names these "
        f"divineos subcommands as recovery paths, but they are NOT "
        f"in _BYPASS_DIVINEOS_SUBCOMMANDS: {sorted(missing)}. "
        f"Add each to the bypass list in src/divineos/hooks/"
        f"pre_tool_use_gate.py, or remove the reference from "
        f"core/stale_engagement.block_message(). Same pattern as the "
        f"learn catch-22 from 2026-04-23 — do not ship a gate that "
        f"blocks its own remedy."
    )


def test_block_message_actually_references_recovery_commands() -> None:
    """The block message MUST contain divineos-subcommand references,
    otherwise an operator hitting Gate 1.48 has no documented path
    out and the gate is a softlock by omission rather than by
    catch-22."""
    referenced = _first_subcommands_in_block_message()
    assert referenced, (
        "Gate 1.48 block_message contains NO divineos-subcommand "
        "references. Operators have no documented recovery path. "
        "Either add drill-down hints to block_message or remove the "
        "gate."
    )


def test_all_known_areas_have_drill_downs() -> None:
    """Every area declared in _AREA_ADDRESS_EVENTS must have a
    drill-down entry in block_message's hard-coded map, otherwise
    the area can fire but the block message says only 'investigate
    this area' (no recovery command)."""
    for area in _AREA_ADDRESS_EVENTS:
        single_msg = block_message([area])
        assert "investigate this area" not in single_msg, (
            f"Area '{area}' has _AREA_ADDRESS_EVENTS but no specific "
            f"drill-down in block_message's hard-coded map. Falls "
            f"through to the generic 'investigate this area' text — "
            f"the operator has no documented recovery command for this "
            f"area. Add a drill-down entry."
        )
