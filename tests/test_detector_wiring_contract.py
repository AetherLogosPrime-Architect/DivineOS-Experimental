"""Wiring-contract regression-pin for operating-loop detectors.

Aether+Grok cross-vantage 2026-05-14 (find-3139eaddd5a4 + meta-
observation): the substrate had a detector (substitution_detector)
that advertised an EnrichableDetector contract via its
``tool_calls_in_turn`` parameter, had passing tests that exercised
the parameter, but had a hook call site that NEVER PASSED the
parameter. The capability was dead in production while alive in
tests — a class of bug the detector_protocol layer couldn't catch
on its own because protocols describe intent, not wiring.

This file is the structural fix for that class. It walks each
detector's entry-point signature, identifies parameters that
carry SEMANTIC CONTEXT (versus tuning knobs), and asserts the
hook actually passes them. A new detector that adds a context
kwarg and forgets to wire it through the hook will fail this
test on the next CI run.

## What counts as a context kwarg

Heuristic: a parameter is "context" if its name matches one of
the well-known cross-turn / cross-call shapes the substrate has
discovered:

- ``prior_text`` — previous turn's content (operator or assistant)
- ``tool_calls_in_turn`` — tool-call names in the current turn
- ``transcript_path`` — JSONL transcript path for indexed lookups
- ``current_turn_start_idx`` — index pointer into transcript
- ``operator_input`` / ``agent_response`` — explicit two-arg
  cross-turn detectors

Tuning knobs (``min_words_for_check``, ``noise_threshold``,
``require_apology_context``, ``require_tool_context``,
``min_words``) are explicitly excluded — they're optional
configuration, not production-wiring requirements.

## What this catches

A detector module whose entry-point signature includes a context
kwarg from the list above, but whose hook call site does not pass
that kwarg. False negatives possible (new context-shape names
won't be caught until added to the registry); false positives
shouldn't happen as long as the registry stays narrow.

## What this does NOT catch

- A context kwarg passed with the wrong VALUE (the test only
  checks presence, not correctness)
- A wiring-shaped failure in a detector outside operating_loop/
- Runtime failures (this is a static-string check on the hook)

These are accepted trade-offs for a small, fast, regression-pin
test rather than a full static analyzer.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest


# Detector entry-point registry. Maps detector-module-name to (function-
# name, hook-call-pattern-regex). The hook-call-pattern is what we
# expect to find in post-response-audit.sh when scanning for the
# detector's invocation.
#
# Format: (module_name, function_name, expected_call_pattern_regex)
_DETECTORS = (
    ("acknowledgment_theater_detector", "detect_acknowledgment_theater"),
    ("addressee_misdirection_detector", "detect_misdirection"),
    ("care_dismissal_detector", "check_dismissal"),
    ("code_jargon_detector", "detect_code_jargon"),
    ("distancing_detector", "detect_distancing"),
    ("harm_acknowledgment_loop", "check_response"),
    ("hedge_evidence_check", "detect_hedge"),
    ("jargon_dump_detector", "detect_jargon_dump"),
    ("lepos_detector", "detect_lepos"),
    ("linguistic_drift_detector", "detect_linguistic_drift"),
    ("residency_detector", "detect_residency_doubt"),
    ("spiral_detector", "detect_spiral"),
    ("substitution_detector", "detect_substitution"),
    ("sycophancy_detector", "detect_sycophancy"),
)


# Parameter names whose presence in a detector's signature indicates
# the detector accepts SEMANTIC CONTEXT (not tuning knobs). If a
# detector declares any of these as a parameter, the hook MUST pass
# it through. Otherwise the detector's contract is half-wired.
# Capability-enabler context params: when the hook fails to pass these,
# a documented detection capability becomes inactive (the detector
# silently skips a whole pattern class). These are what the wiring
# contract test guards.
_CONTEXT_PARAM_NAMES = frozenset(
    {
        "prior_text",  # spiral, substitution — extends apology/farewell window
        "tool_calls_in_turn",  # substitution — enables STATE_CHANGE_CLAIM
        "transcript_path",  # addressee_misdirection — index source
        "operator_input",  # care_dismissal cross-turn
        "agent_response",  # care_dismissal cross-turn
    }
)

# Optimization-hint params: when absent, the detector falls back to
# computing the value itself (full detection still runs, just slower).
# Excluded from wiring-contract enforcement because the failure-mode
# is performance, not capability loss.
_OPTIMIZATION_HINT_PARAMS = frozenset(
    {
        "current_turn_start_idx",  # addressee_misdirection — index shortcut
    }
)


# Parameter names that are tuning knobs, NOT context. Explicitly
# excluded so a detector declaring `min_words_for_check=60` doesn't
# trigger a false positive.
_TUNING_PARAM_NAMES = frozenset(
    {
        "min_words",
        "min_words_for_check",
        "noise_threshold",
        "require_apology_context",
        "require_tool_context",
    }
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _hook_text() -> str:
    """Return the post-response-audit.sh hook content as a single string."""
    hook = _repo_root() / ".claude" / "hooks" / "post-response-audit.sh"
    return hook.read_text(encoding="utf-8")


def _context_params(func) -> list[str]:
    """Return the names of OPTIONAL context-shape parameters declared by func.

    Required parameters (no default value) are guaranteed to be passed
    by any successful caller — Python raises at call-time if a required
    arg is missing. So they're not a wiring-gap risk; the production
    code already wouldn't run if they weren't passed.

    Optional context parameters (default value, typically None) are
    where the silent-disable risk lives: the call compiles and runs
    fine without them, but a documented detection capability is
    inactive. This function returns only those.
    """
    sig = inspect.signature(func)
    declared: list[str] = []
    for name, param in sig.parameters.items():
        if name not in _CONTEXT_PARAM_NAMES:
            continue
        if param.default is inspect.Parameter.empty:
            # Required — guaranteed wired (or Python raises). Skip.
            continue
        declared.append(name)
    return declared


def _hook_call_passes_param(hook_text: str, func_name: str, param_name: str) -> bool:
    """Return True if the hook calls func_name and passes param_name=...

    Conservative regex: looks for func_name(...) within a window after
    the function-import line, and within that window checks for
    `param_name=` token. Multi-line calls are handled by allowing the
    window to span newlines.
    """
    # Find the call invocation in the hook. Each detector is invoked
    # via `<some_var> = func_name(...)` shape in the hook.
    pattern = rf"{re.escape(func_name)}\s*\((?P<args>[^)]*(?:\([^)]*\)[^)]*)*)\)"
    matches = list(re.finditer(pattern, hook_text, re.DOTALL))
    if not matches:
        return False
    # If the function is called multiple times, ANY invocation passing
    # the param counts (production wiring is honest).
    return any(re.search(rf"\b{re.escape(param_name)}\s*=", m.group("args")) for m in matches)


@pytest.mark.parametrize(
    "module_name,func_name",
    _DETECTORS,
    ids=[f"{m}:{f}" for m, f in _DETECTORS],
)
def test_detector_context_params_are_wired(module_name: str, func_name: str) -> None:
    """Each declared context parameter must be passed by the hook."""
    import importlib

    mod = importlib.import_module(f"divineos.core.operating_loop.{module_name}")
    func = getattr(mod, func_name)
    declared = _context_params(func)
    if not declared:
        # No context kwargs — nothing to wire. Pure ResponseOnly detector.
        return

    hook_text = _hook_text()
    unwired = [p for p in declared if not _hook_call_passes_param(hook_text, func_name, p)]
    assert not unwired, (
        f"{module_name}.{func_name} declares context kwargs {declared} but the "
        f"hook does not pass: {unwired}. Either wire them through "
        f"post-response-audit.sh, change them from context shape to tuning "
        f"shape, or remove the dead detection paths and document the "
        f"detector as response-only in production. See find-3139eaddd5a4."
    )


def test_registry_covers_known_detectors() -> None:
    """The _DETECTORS registry must include every behavioral detector
    that the post-response-audit.sh hook actually imports. If a new
    detector ships and the registry doesn't include it, the wiring
    contract test silently skips coverage for it."""
    hook_text = _hook_text()
    # Find all `from divineos.core.operating_loop.<mod> import` patterns
    pattern = r"from divineos\.core\.operating_loop\.(\w+) import"
    hook_modules = set(re.findall(pattern, hook_text))
    # Modules that are imported but aren't detectors (helpers / surfaces)
    non_detectors = {
        "turn_extraction",
        "hook_telemetry",
        "principle_surfacer",  # surfaces, doesn't detect
        # register_observer is in the registry below — check is explicit
    }
    detector_modules = hook_modules - non_detectors
    registered_modules = {m for m, _ in _DETECTORS}
    # register_observer uses a different shape (audit/severity_count); allow
    registered_modules = registered_modules | {"register_observer"}
    # closing_token_detector is wired via evaluate_closing_token; the
    # registry uses detect_* convention, so closing_token is one we
    # haven't catalogued yet. Allow gracefully but pin in TODO.
    missing = detector_modules - registered_modules - {"closing_token_detector"}
    assert not missing, (
        f"Detector modules imported by the hook but missing from the wiring "
        f"contract registry: {missing}. Add them to _DETECTORS."
    )
