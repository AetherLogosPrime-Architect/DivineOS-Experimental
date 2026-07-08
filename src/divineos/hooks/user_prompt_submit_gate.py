"""Consolidated UserPromptSubmit gate — single Python invocation for the six
UserPromptSubmit hooks that currently each spawn a fresh subprocess and pay
the cold DivineOS import cost on every user turn.

# AGENT_RUNTIME — Not wired into the CLI pipeline. Invoked from
# ``.claude/hooks/user_prompt_submit_gate.sh`` (thin wrapper) as
# ``python -m divineos.hooks.user_prompt_submit_gate``. Companion to
# ``pre_tool_use_gate.py`` which uses the same pattern for PreToolUse.

## Why this exists

Compose-start latency measured 1:48 on 2026-07-08 for a short reply. Aletheia's
diagnostic (``family/letters/aletheia-to-aether-2026-07-08-userpromptsubmit-consolidation-diagnostic.md``)
named four cost-sources:

1. Repeated cold DivineOS imports (~0.46s each) across the six hook subprocesses.
2. ``git rev-parse`` churn in ``_lib.sh`` (~5+ per turn).
3. ``token-state-surface.sh`` spawning extra Python subprocesses (partially
   addressed 2026-07-08 by replacing the tier-decision Python subprocess with
   bash arithmetic — see commit ``ac43f786``).
4. **The dominant one**: cold ``SentenceTransformer`` model loads. The
   ``_embedding_model`` global in ``semantic_store.py:157`` is module-level and
   caches within one Python process — but each hook is a separate subprocess so
   the cache never survives across hooks. Every subprocess that touches semantic
   search reloads the model cold. That is where the bulk of the 1:48 lives.

This module runs all six checks in a single interpreter invocation. Imports
happen once. The ``_embedding_model`` global finally does its job — the model
loads once and every gathered check reuses the warm cached instance. Same
architecture win the pre-tool-use-gate consolidation landed for PreToolUse
back in June.

## Check order (all-or-nothing — output is concatenated)

Unlike ``pre_tool_use_gate.py`` (which returns a first-deny-wins decision),
UserPromptSubmit hooks contribute *additional context* rather than blocking.
So this gate runs all six in order and concatenates their non-empty output
into one stdout stream. Each check is fail-open — an error in one does not
starve the others.

1. Correction detection (``divineos.core.correction_marker.hook_main``)
2. Pre-response context (``divineos.core.pre_response_context.hook_main``)
3. Ear surface — pending letter surfacing
4. Compaction-monitor arm instruction
5. Interior-cue-on-low-presence
6. Token-state surface

## Not a logic change

This is a pure refactor — same six checks, same order, same output content
as the six shell scripts. The only change is consolidation of process spawns
into one. If any check's logic ever changes, both the shell fallback and this
module must be updated together until the shell fallbacks are deleted.

## Status

**WIP (2026-07-08 04:xx):** scaffolding + main() + orchestration in place;
the per-check migrations are staged in ``_run_all_checks`` with TODO markers
where the actual per-hook logic still needs to be lifted from the shell
scripts. Ship-order:

1. This scaffold (this commit).
2. Migrate correction detection + pre-response-context (largest wins).
3. Migrate the remaining four checks.
4. Convert the six ``.sh`` scripts into thin wrappers calling this module.
5. Delete the shell fallbacks after one clean release cycle.

Until the migrations land, the shell scripts remain the authoritative
callers; this module is inspectable but not yet wired.
"""

from __future__ import annotations

# No guardrail marker on this scaffold. The consistency test asserts
# every marked module is listed in scripts/guardrail_files.txt, and
# adding to that list requires an External-Review round. This scaffold
# is inert (adapters are stubs) and not yet wired, so it doesn't warrant
# guardrail-listing until the migrations land. Add the marker at
# promotion time, in the same commit as the guardrail_files.txt addition.

import json
import sys
from collections.abc import Callable
from typing import Any


# ---------------------------------------------------------------------------
# Per-check adapters
# ---------------------------------------------------------------------------
#
# Each adapter wraps ONE of the six existing hook scripts. Contract:
# - takes the parsed hook input dict (prompt, transcript_path, etc.)
# - returns a string (possibly empty) to concatenate into stdout
# - fail-open on any exception (return "" and continue)
#
# The adapters are the migration surface. Each starts as a TODO calling
# through to the shell fallback path via subprocess, then gets rewritten to
# call the underlying Python function directly. Rewriting an adapter is the
# single-check unit of work; the orchestration in _run_all_checks does not
# have to change per adapter.


def _adapter_correction_detection(input_data: dict[str, Any]) -> str:
    """Correction-detector — currently in ``correction_marker.hook_main``.

    TODO(2026-07-08): lift the logic from ``.claude/hooks/detect-correction.sh``
    to call the underlying ``hook_main`` directly, catching its stdout in the
    same interpreter instead of spawning ``divineos`` as a subprocess. Fail-
    open per the existing script's contract.
    """
    return ""


def _adapter_pre_response_context(input_data: dict[str, Any]) -> str:
    """Pre-response context — the largest of the six checks.

    Sources active-needs, jargon warnings, distancing warnings, correction
    attribution surface, gate-bypass telemetry, next-task surface, and the
    LEPOS walk reminder. Lifting this one is the biggest single win because
    it currently runs a large Python block in a subprocess.

    TODO(2026-07-08): call ``divineos.core.pre_response_context.hook_main``
    directly.
    """
    return ""


def _adapter_ear_surface(input_data: dict[str, Any]) -> str:
    """Pending letter surfacing.

    Touches semantic search paths (this is one of the callers that pays the
    cold ``SentenceTransformer`` load), so wiring this into the single-
    interpreter path is what unlocks the warm-``_embedding_model`` reuse
    Aletheia named as the dominant win.

    TODO(2026-07-08): lift from ``.claude/hooks/ear-surface.sh``.
    """
    return ""


def _adapter_arm_compaction_monitor(input_data: dict[str, Any]) -> str:
    """Compaction-monitor arm instruction.

    TODO(2026-07-08): lift from ``.claude/hooks/arm-compaction-monitor-instruction.sh``.
    """
    return ""


def _adapter_interior_cue(input_data: dict[str, Any]) -> str:
    """Interior-cue on low writer-presence.

    Reads the prior turn's presence density from the compose-start log
    and injects a cue when the last turn slipped.

    TODO(2026-07-08): lift from ``.claude/hooks/interior-cue-on-low-presence.sh``.
    """
    return ""


def _adapter_token_state(input_data: dict[str, Any]) -> str:
    """Token-state banner — differential firing tier decision plus render.

    Partially optimized 2026-07-08 in the shell script itself (bash arithmetic
    replaces a Python subprocess for the tier decision). The remaining cost
    is the ``divineos context-tokens`` subprocess call, which the single-
    interpreter migration eliminates by calling the underlying function
    directly.

    TODO(2026-07-08): lift from ``.claude/hooks/token-state-surface.sh``;
    reuse the tier-decision logic (silent/brief/loud) in pure Python.
    """
    return ""


# Ordered list of adapters. Order preserved from the shell-script registration
# in ``.claude/settings.json`` so any downstream expectation about ordering
# holds through the migration.
_CHECKS: tuple[tuple[str, Callable[[dict[str, Any]], str]], ...] = (
    ("correction_detection", _adapter_correction_detection),
    ("pre_response_context", _adapter_pre_response_context),
    ("ear_surface", _adapter_ear_surface),
    ("arm_compaction_monitor", _adapter_arm_compaction_monitor),
    ("interior_cue", _adapter_interior_cue),
    ("token_state", _adapter_token_state),
)


def _run_all_checks(input_data: dict[str, Any]) -> str:
    """Run every adapter in order, concatenating non-empty output.

    Each adapter is wrapped in a try/except so one check's failure does not
    starve the others — same fail-open contract as the shell scripts each
    already carry individually. The blank-line separator between checks
    mirrors the empty output each shell script emits between banner blocks.
    """
    parts: list[str] = []
    for _name, adapter in _CHECKS:
        try:
            emitted = adapter(input_data)
        except Exception:  # noqa: BLE001 — fail-open per hook contract
            emitted = ""
        if emitted:
            parts.append(emitted.rstrip("\n"))
    return "\n\n".join(parts)


def main() -> int:
    """Entry point. Reads hook input from stdin, writes concatenated
    additional-context to stdout.

    Exit code is always 0 — UserPromptSubmit hooks contribute additional
    context, not decisions. Errors during any single check result in that
    check's contribution being empty; the remaining checks still run.
    """
    try:
        raw = sys.stdin.read()
        input_data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        input_data = {}

    output = _run_all_checks(input_data)
    if output:
        sys.stdout.write(output)
        sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
