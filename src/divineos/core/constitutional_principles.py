"""Constitutional principles — the six rules DivineOS is built to honor.

Ported from old Divine-OS ``law/constitutional_principles.py`` with the
TRIBUNAL architecture trimmed away. The old version proposed a
four-power separation (COUNCIL / COMPASS / VOID / TRIBUNAL) to enforce
these principles. Current DivineOS distributes enforcement across
existing systems (engagement gate, audit, prereg, supersession,
corrigibility) without a separate tribunal. The principles themselves
remain load-bearing.

Rather than ship the principles as a decorative enum, this module
wires each one as a **structurally verifiable invariant** that
anti-slop can check at runtime. That turns a philosophy statement
into a behavioral assertion.

## The six principles

1. **CONSENT** — Actions require explicit user agreement.
   *Invariant:* the engagement gate (`require-goal.sh`) actually
   refuses to let the agent proceed without a goal set.

2. **TRANSPARENCY** — Users must understand implications.
   *Invariant:* state-changing operations emit ledger events that are
   queryable after the fact. Mode changes, decisions, writes.

3. **PROPORTIONALITY** — Response matches the offense.
   *Invariant:* EMPIRICA's `required_corroboration` scales monotonically
   with claim magnitude. Foundational claims require more evidence
   than trivial ones.

4. **DUE_PROCESS** — Fair hearing before judgment.
   *Invariant:* pre-registrations exist and carry explicit falsifiers
   before outcomes are assessed. The rule precedes the verdict.

5. **APPEAL** — Decisions can be reviewed.
   *Invariant:* knowledge supersession chains are traversable — if a
   claim is superseded, the replacement is reachable from the
   original record.

6. **LIMITS_OF_POWER** — No single system can become tyrannical.
   *Invariant:* corrigibility's `set_mode` always succeeds regardless
   of current mode. The off-switch bypasses any single system's
   judgment, including the corrigibility system's own mode.

## What this module is NOT

* Not a verdict layer. Does not decide whether actions honor
  principles in real time.
* Not a replacement for the engagement gate, audit, prereg,
  supersession, or corrigibility. It is a *lens* over those systems,
  not a competitor.
* Not a rewrite of the old TRIBUNAL architecture. The four-power
  separation is deferred; current mechanisms distribute the function.

## How to use

Each principle has a `verifier` — a callable that returns True iff
the invariant currently holds. The anti-slop module can run them all
and report on which principles are structurally honored and which
have drifted. If any verifier returns False, the principle has lost
its structural grounding — the word without the mechanism is
decoration.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Principle(str, Enum):
    """The six constitutional principles, named explicitly."""

    CONSENT = "consent"
    TRANSPARENCY = "transparency"
    PROPORTIONALITY = "proportionality"
    DUE_PROCESS = "due_process"
    APPEAL = "appeal"
    LIMITS_OF_POWER = "limits_of_power"


@dataclass(frozen=True)
class PrincipleDefinition:
    """A principle plus its plain-English meaning and structural invariant."""

    principle: Principle
    summary: str
    invariant: str


_DEFINITIONS: dict[Principle, PrincipleDefinition] = {
    Principle.CONSENT: PrincipleDefinition(
        principle=Principle.CONSENT,
        summary="Actions require explicit user agreement.",
        invariant=(
            "The engagement gate (require-goal.sh + goal/briefing enforcement) "
            "refuses to let the agent proceed without a goal set and a "
            "thinking-command marker. This is verifiable by the presence of "
            "the hook itself and a recent engagement-gate event."
        ),
    ),
    Principle.TRANSPARENCY: PrincipleDefinition(
        principle=Principle.TRANSPARENCY,
        summary="Users must understand implications.",
        invariant=(
            "State-changing operations (mode changes, decisions, writes) emit "
            "ledger events that are queryable after the fact. The ledger is "
            "append-only and SHA256-hashed — transparency is structural, not "
            "best-effort."
        ),
    ),
    Principle.PROPORTIONALITY: PrincipleDefinition(
        principle=Principle.PROPORTIONALITY,
        summary="Response matches the offense.",
        invariant=(
            "EMPIRICA's required_corroboration scales monotonically with "
            "claim magnitude. A FOUNDATIONAL claim requires more evidence "
            "than a TRIVIAL one. If the scale flattens, proportionality "
            "has collapsed."
        ),
    ),
    Principle.DUE_PROCESS: PrincipleDefinition(
        principle=Principle.DUE_PROCESS,
        summary="Fair hearing before judgment.",
        invariant=(
            "Pre-registrations exist with explicit falsifiers recorded before "
            "outcomes are assessed. The rule precedes the verdict — no "
            "outcome is adjudicated against a standard that did not exist "
            "beforehand."
        ),
    ),
    Principle.APPEAL: PrincipleDefinition(
        principle=Principle.APPEAL,
        summary="Decisions can be reviewed.",
        invariant=(
            "Knowledge supersession chains are traversable. Superseded "
            "records are not deleted; the replacement is reachable from the "
            "original. Past decisions remain accessible for review."
        ),
    ),
    Principle.LIMITS_OF_POWER: PrincipleDefinition(
        principle=Principle.LIMITS_OF_POWER,
        summary="No single system can become tyrannical.",
        invariant=(
            "Corrigibility's set_mode always succeeds regardless of current "
            "mode — the off-switch bypasses any single system's judgment, "
            "including the corrigibility system's own mode. No mode can "
            "trap the operator."
        ),
    ),
}


def get_principle(principle: Principle) -> PrincipleDefinition:
    """Return the full definition for a principle."""
    return _DEFINITIONS[principle]


def all_principles() -> list[PrincipleDefinition]:
    """Return definitions for all six principles, in canonical order."""
    return [
        _DEFINITIONS[Principle.CONSENT],
        _DEFINITIONS[Principle.TRANSPARENCY],
        _DEFINITIONS[Principle.PROPORTIONALITY],
        _DEFINITIONS[Principle.DUE_PROCESS],
        _DEFINITIONS[Principle.APPEAL],
        _DEFINITIONS[Principle.LIMITS_OF_POWER],
    ]


# ---------------------------------------------------------------------------
# Structural verifiers — each returns (passed, detail) for anti-slop use
# ---------------------------------------------------------------------------


def verify_consent() -> tuple[bool, str]:
    """Verify the engagement-gate hook exists. It is the mechanism by
    which CONSENT is enforced — no goal, no work."""
    from pathlib import Path

    hook = (
        Path(__file__).resolve().parent.parent.parent.parent
        / ".claude"
        / "hooks"
        / "require-goal.sh"
    )
    if not hook.exists():
        return (
            False,
            "require-goal.sh hook missing — engagement gate not structurally present",
        )
    return True, "Engagement-gate hook exists and enforces goal/briefing requirement."


def verify_transparency() -> tuple[bool, str]:
    """Verify the ledger structure exists and is queryable.

    Tests the mechanism (table present, queryable) — not that it has
    been exercised. A fresh install has no events yet, which is not
    a transparency failure; it just means the mechanism hasn't been
    used yet. If the table is missing entirely, that IS a failure.
    """
    try:
        from divineos.core.ledger import get_connection

        conn = get_connection()
        try:
            tables = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "system_events" not in tables:
                return (
                    False,
                    "system_events table missing — transparency mechanism not structurally present",
                )
            row = conn.execute("SELECT COUNT(*) FROM system_events").fetchone()
            count = int(row[0]) if row else 0
            return (
                True,
                f"system_events table present and queryable ({count} event(s) recorded).",
            )
        finally:
            conn.close()
    except Exception as e:  # noqa: BLE001
        return False, f"Ledger query failed: {type(e).__name__}: {e}"


def verify_proportionality() -> tuple[bool, str]:
    """Verify EMPIRICA's required_corroboration is monotonic in magnitude."""
    try:
        from divineos.core.empirica.burden import required_corroboration
        from divineos.core.empirica.types import ClaimMagnitude, Tier

        # Pick a tier where the function is implemented (not ADVERSARIAL).
        vals = [
            required_corroboration(Tier.PATTERN, m)
            for m in (
                ClaimMagnitude.TRIVIAL,
                ClaimMagnitude.NORMAL,
                ClaimMagnitude.LOAD_BEARING,
                ClaimMagnitude.FOUNDATIONAL,
            )
        ]
        if vals != sorted(vals):
            return (
                False,
                f"required_corroboration NOT monotonic in magnitude: {vals}",
            )
        if len(set(vals)) < 4:
            return (
                False,
                f"required_corroboration has duplicate values across magnitudes: {vals}",
            )
        return (
            True,
            f"required_corroboration monotonic and distinct across 4 magnitudes: {vals}",
        )
    except Exception as e:  # noqa: BLE001
        return False, f"Verifier failed: {type(e).__name__}: {e}"


def verify_due_process() -> tuple[bool, str]:
    """Verify the pre-registration mechanism is structurally present.

    Tests that the table exists and has a ``falsifier`` column.
    Existence of falsifier-carrying records is not required — a fresh
    install may have none yet. What matters is that when a record is
    filed, the schema forces the falsifier field to exist.
    """
    try:
        from divineos.core.ledger import get_connection

        conn = get_connection()
        try:
            tables = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "pre_registrations" not in tables:
                # Try to init the schema — if the table shows up after
                # init, the mechanism is present, just not yet materialized.
                try:
                    from divineos.core.pre_registrations._schema import (
                        init_pre_registrations_tables,
                    )

                    init_pre_registrations_tables()
                    tables = {
                        r[0]
                        for r in conn.execute(
                            "SELECT name FROM sqlite_master WHERE type='table'"
                        ).fetchall()
                    }
                except ImportError:
                    pass
                if "pre_registrations" not in tables:
                    return (
                        False,
                        "pre_registrations table missing — due process "
                        "mechanism not structurally present",
                    )
            # Check the falsifier column exists in schema.
            cols = {c[1] for c in conn.execute("PRAGMA table_info(pre_registrations)").fetchall()}
            if "falsifier" not in cols:
                return (
                    False,
                    "pre_registrations.falsifier column missing — rule-precedes-"
                    "verdict mechanism not present",
                )
            row = conn.execute(
                "SELECT COUNT(*) FROM pre_registrations "
                "WHERE falsifier IS NOT NULL AND falsifier != ''"
            ).fetchone()
            count = int(row[0]) if row else 0
            return (
                True,
                f"pre_registrations table + falsifier column present "
                f"({count} record(s) with falsifier).",
            )
        finally:
            conn.close()
    except Exception as e:  # noqa: BLE001
        return False, f"Verifier failed: {type(e).__name__}: {e}"


def verify_appeal() -> tuple[bool, str]:
    """Verify supersession chains are traversable — the superseded_by
    column exists so callers can reach a replacement from the original.

    The mechanism is present iff the table + column exist. Zero
    superseded records is fine (fresh install); what matters is that
    supersession is possible.
    """
    try:
        from divineos.core.knowledge._base import get_connection

        conn = get_connection()
        try:
            tables = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "knowledge" not in tables:
                # Try init first.
                try:
                    from divineos.core.knowledge import init_knowledge_table

                    init_knowledge_table()
                    tables = {
                        r[0]
                        for r in conn.execute(
                            "SELECT name FROM sqlite_master WHERE type='table'"
                        ).fetchall()
                    }
                except ImportError:
                    pass
                if "knowledge" not in tables:
                    return (
                        False,
                        "knowledge table missing — appeal mechanism not structurally present",
                    )
            cols = {c[1] for c in conn.execute("PRAGMA table_info(knowledge)").fetchall()}
            if "superseded_by" not in cols:
                return (
                    False,
                    "knowledge.superseded_by column missing — appeal mechanism "
                    "not structurally present",
                )
            row = conn.execute(
                "SELECT COUNT(*) FROM knowledge WHERE superseded_by IS NOT NULL"
            ).fetchone()
            count = int(row[0]) if row else 0
            return (
                True,
                f"knowledge + superseded_by column present "
                f"({count} superseded record(s) currently in store).",
            )
        finally:
            conn.close()
    except Exception as e:  # noqa: BLE001
        return False, f"Verifier failed: {type(e).__name__}: {e}"


def verify_limits_of_power() -> tuple[bool, str]:
    """Verify the corrigibility off-switch cannot trap itself — set_mode
    must be in the always-allowed command set."""
    try:
        from divineos.core.corrigibility import (
            OperatingMode,
            _ALWAYS_ALLOWED,
            set_mode,
        )

        # Verify "mode" is in the always-allowed registry. We do NOT
        # actually change mode to test the path, since that would
        # disrupt operator state. Schema check is sufficient.

        if "mode" not in _ALWAYS_ALLOWED:
            return (
                False,
                "'mode' is not in _ALWAYS_ALLOWED — off-switch can trap itself",
            )

        # Also verify empty-reason set_mode refuses (the 'opacity is not corrigibility' invariant)
        try:
            set_mode(OperatingMode.NORMAL, reason="", actor="verifier")
            return (
                False,
                "set_mode accepted empty reason — opacity allowed in corrigibility path",
            )
        except ValueError:
            pass  # expected

        return (
            True,
            "'mode' is in always-allowed; empty-reason mode change refused. "
            "Off-switch cannot trap itself.",
        )
    except Exception as e:  # noqa: BLE001
        return False, f"Verifier failed: {type(e).__name__}: {e}"


# Principle → verifier mapping. Used by anti-slop to check each principle.
_VERIFIERS = {
    Principle.CONSENT: verify_consent,
    Principle.TRANSPARENCY: verify_transparency,
    Principle.PROPORTIONALITY: verify_proportionality,
    Principle.DUE_PROCESS: verify_due_process,
    Principle.APPEAL: verify_appeal,
    Principle.LIMITS_OF_POWER: verify_limits_of_power,
}


def verify_principle(principle: Principle) -> tuple[bool, str]:
    """Run the structural verifier for a specific principle."""
    return _VERIFIERS[principle]()


def verify_all_principles() -> list[tuple[Principle, bool, str]]:
    """Run all six verifiers; return (principle, passed, detail) per."""
    return [(p, *_VERIFIERS[p]()) for p in Principle]


__all__ = [
    "Principle",
    "PrincipleDefinition",
    "all_principles",
    "get_principle",
    "verify_all_principles",
    "verify_principle",
]
