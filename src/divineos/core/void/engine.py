"""VOID engine — TRAP / ATTACK / EXTRACT / SEAL / SHRED orchestrator.

Per design brief §7 (merged PR #208).

The engine is the only module callers should use to run an adversarial
invocation. It enforces the lifecycle:

* TRAP    — set mode_marker active, log VOID_INVOCATION_STARTED
* ATTACK  — produce persona-attack text against a target
* EXTRACT — turn attack text into a Finding (caller-supplied callback;
            the engine validates structure and severity)
* SEAL    — append VOID_FINDING to void_ledger, write one-way pointer
            to main event_ledger
* SHRED   — clear mode_marker, log VOID_SHRED. Always runs (loud SHRED
            for nyarlathotep; SHRED is bounded — frame-residue is real
            but the marker clears regardless)

The engine refuses to:
* run a persona without going through persona_loader (gate §4.3)
* invoke nyarlathotep unless ``allow_high_bar=True``
* accept HIGH or CRITICAL findings from the mirror persona (§5.6)

The engine does NOT:
* generate persona-attack text itself — callers supply attack callbacks
* address findings — that lives in the address command (Phase 2)
* run rationale-checks — Reductio-on-rationale lives in Phase 2
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable

from . import ledger as void_ledger
from . import mode_marker
from .finding import Finding, Severity
from .persona_loader import Persona, load_by_name


class VoidScopeError(RuntimeError):
    """Raised when persona-prompt assembly is attempted outside an
    active invocation, or invocation rules are violated."""


# Personas that may not produce HIGH/CRITICAL findings (§5.6).
_CLARIFICATION_ONLY = frozenset({"mirror"})

# Personas that require allow_high_bar=True (§6.1).
_HIGH_BAR = frozenset({"nyarlathotep"})


@dataclass(frozen=True)
class InvocationResult:
    persona: str
    invocation_id: str
    finding: Finding | None
    void_event_id: str | None
    void_content_hash: str | None


def _validate_invocation(persona: Persona, *, allow_high_bar: bool) -> None:
    if persona.name in _HIGH_BAR and not allow_high_bar:
        raise VoidScopeError(
            f"persona {persona.name!r} requires allow_high_bar=True "
            "(frame-residue isolation per design brief §6.1)"
        )


def _validate_finding(finding: Finding, persona: Persona) -> None:
    if finding.persona != persona.name:
        raise VoidScopeError(
            f"finding.persona={finding.persona!r} does not match invoked persona {persona.name!r}"
        )
    if persona.name in _CLARIFICATION_ONLY and finding.severity in {
        Severity.HIGH,
        Severity.CRITICAL,
    }:
        raise VoidScopeError(
            f"persona {persona.name!r} is clarification-only (§5.6); "
            f"may not emit {finding.severity.value} findings"
        )


@contextmanager
def invoke(
    persona_name: str,
    *,
    target: str,
    session_id: str | None = None,
    allow_high_bar: bool = False,
    personas_path=None,
    void_db_path=None,
):
    """Context manager wrapping TRAP and SHRED around an invocation.

    Yields a dict with the persona, invocation_id, and a ``seal``
    callback the caller invokes with a Finding (or None to abort).

    Always SHREDs on exit — even if the caller raises. The marker
    clears regardless of frame-residue concerns; the marker is the
    architectural surrogate, not a guarantee.
    """
    persona = load_by_name(persona_name, path=personas_path)
    _validate_invocation(persona, allow_high_bar=allow_high_bar)

    invocation_id = mode_marker.write_marker(persona.name, session_id=session_id)
    try:
        started = void_ledger.append_event(
            "VOID_INVOCATION_STARTED",
            {
                "target": target,
                "invocation_id": invocation_id,
                "session_id": session_id,
                "high_bar": persona.name in _HIGH_BAR,
            },
            persona=persona.name,
            path=void_db_path,
        )
    except Exception:  # noqa: BLE001 — fail-closed marker clear is intentionally any-exception; symmetry is the safety property, not the failure category
        mode_marker.clear_marker()
        raise

    state: dict = {"sealed": False, "result": None}

    def seal(finding: Finding | None) -> InvocationResult:
        if state["sealed"]:
            raise VoidScopeError("invocation already sealed")
        state["sealed"] = True
        if finding is None:
            result = InvocationResult(
                persona=persona.name,
                invocation_id=invocation_id,
                finding=None,
                void_event_id=None,
                void_content_hash=None,
            )
            state["result"] = result
            return result
        _validate_finding(finding, persona)
        appended = void_ledger.append_event(
            "VOID_FINDING",
            finding.to_payload() | {"invocation_id": invocation_id, "target": target},
            persona=persona.name,
            path=void_db_path,
        )
        void_ledger.write_main_ledger_pointer(appended["event_id"], appended["content_hash"])
        result = InvocationResult(
            persona=persona.name,
            invocation_id=invocation_id,
            finding=finding,
            void_event_id=appended["event_id"],
            void_content_hash=appended["content_hash"],
        )
        state["result"] = result
        return result

    yielded = {
        "persona": persona,
        "invocation_id": invocation_id,
        "started_event_id": started["event_id"],
        "seal": seal,
    }
    try:
        yield yielded
    finally:
        # SHRED: always runs.
        void_ledger.append_event(
            "VOID_SHRED",
            {
                "invocation_id": invocation_id,
                "sealed": state["sealed"],
                "had_finding": state["result"] is not None and state["result"].finding is not None,
                "loud": persona.name in _HIGH_BAR,
            },
            persona=persona.name,
            path=void_db_path,
        )
        mode_marker.clear_marker()


def run(
    persona_name: str,
    *,
    target: str,
    attack: Callable[[Persona, str], Finding | None],
    session_id: str | None = None,
    allow_high_bar: bool = False,
    personas_path=None,
    void_db_path=None,
) -> InvocationResult:
    """Convenience wrapper: invoke + caller-supplied ATTACK callback.

    The attack callback receives the loaded Persona and the target
    string; it returns a Finding or None.
    """
    with invoke(
        persona_name,
        target=target,
        session_id=session_id,
        allow_high_bar=allow_high_bar,
        personas_path=personas_path,
        void_db_path=void_db_path,
    ) as inv:
        finding = attack(inv["persona"], target)
        result: InvocationResult = inv["seal"](finding)
        return result


def assemble_persona_prompt(persona_name: str, *, personas_path=None) -> str:
    """Return the persona prompt body. Refuses if mode_marker is not
    active (§6.3 — persona-prompt assembly is invocation-scoped).
    """
    if not mode_marker.is_active():
        # Log the violation to the main ledger via void_ledger event;
        # the void ledger is where scope violations belong.
        void_ledger.append_event(
            "VOID_SCOPE_VIOLATION",
            {"reason": "persona_prompt_outside_invocation", "persona": persona_name},
            persona=persona_name,
        )
        raise VoidScopeError(
            f"persona-prompt assembly for {persona_name!r} attempted "
            "without active mode_marker — invocation scope violation"
        )
    persona = load_by_name(persona_name, path=personas_path)
    return persona.body
