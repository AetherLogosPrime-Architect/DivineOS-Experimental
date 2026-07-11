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
    ("authority_substitution_detector", "detect_authority_substitution"),
    ("care_dismissal_detector", "check_dismissal"),
    ("andrew_operator_shape_detector", "check_operator_shape"),
    ("closing_token_detector", "evaluate_closing_token"),
    ("code_jargon_detector", "detect_code_jargon"),
    ("constraint_disownership_detector", "detect_constraint_disownership"),
    ("distancing_detector", "detect_distancing"),
    ("harm_acknowledgment_loop", "check_response"),
    ("hedge_evidence_check", "detect_hedge"),
    ("jargon_dump_detector", "detect_jargon_dump"),
    # lepos_detector removed from registry 2026-05-14: it's deprecated
    # (wrong-proxy: voice-token presence) and post-response-audit.sh
    # now wires detect_jargon_dump instead. See find-1505d70db349.
    ("linguistic_drift_detector", "detect_linguistic_drift"),
    ("engineer_register_drift_detector", "detect_engineer_drift_for_audit"),
    ("residency_detector", "detect_residency_doubt"),
    ("self_disownership_detector", "detect_self_disownership"),
    ("spiral_detector", "detect_spiral"),
    ("substitution_detector", "detect_substitution"),
    ("shape_chasing_detector", "detect_shape_chasing"),
    ("sycophancy_detector", "detect_sycophancy"),
    ("tool_output_truncation_detector", "detect_tool_output_truncation"),
    ("unverified_claim_detector", "detect_unverified_claim"),
    ("writer_presence_detector", "detect_writer_presence"),
    ("closure_initiation_detector", "detect_closure_initiation"),
    ("deep_engagement_detector", "detect_deep_engagement"),
    ("temporal_displacement_detector", "detect_temporal_displacement"),
    # Composite detector — pair-designed with Aether 2026-07-11.
    # Aggregates five family signals into a wallpaper-density score.
    # Wired via the caller module (`operator_wallpaper_caller`) which
    # imports the aggregator; the caller is the run_audit-facing surface.
    ("operator_wallpaper_caller", "run_operator_wallpaper_check"),
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
    """Return production wiring text — hook + the OS module the hook delegates to.

    The hook was simplified to a thin doorman 2026-05-14; detector calls now
    live in core/operating_loop_audit.run_audit. Both files are read so the
    contract check sees the actual call sites wherever they live.
    """
    parts = []
    hook = _repo_root() / ".claude" / "hooks" / "post-response-audit.sh"
    if hook.exists():
        parts.append(hook.read_text(encoding="utf-8"))
    audit_module = _repo_root() / "src" / "divineos" / "core" / "operating_loop_audit.py"
    if audit_module.exists():
        parts.append(audit_module.read_text(encoding="utf-8"))
    return chr(10).join(parts)


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
    # Shape 1: direct call — func_name(..., param_name=...)
    direct_pattern = rf"{re.escape(func_name)}\s*\((?P<args>[^)]*(?:\([^)]*\)[^)]*)*)\)"
    for m in re.finditer(direct_pattern, hook_text, re.DOTALL):
        if re.search(rf"\b{re.escape(param_name)}\s*=", m.group("args")):
            return True

    # Shape 2: indirect via wrapper — the detector function is passed as a value
    # to a generic runner that forwards kwargs:
    #   _run_detector(name, func_name, ..., param_name=...)
    # The wiring is honest if both tokens appear in the same call expression.
    # (The hook was simplified 2026-05-14 to delegate to operating_loop_audit
    # which uses this shape; the contract still holds.)
    wrapper_pattern = r"\w+\s*\((?P<args>[^)]*(?:\([^)]*\)[^)]*)*)\)"
    for m in re.finditer(wrapper_pattern, hook_text, re.DOTALL):
        args = m.group("args")
        if re.search(rf"\b{re.escape(func_name)}\b", args) and re.search(
            rf"\b{re.escape(param_name)}\s*=", args
        ):
            return True

    return False


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
        "registered_names",  # helper: operator/family-name registry, not a detector
        # register_observer is in the registry below — check is explicit
    }
    detector_modules = hook_modules - non_detectors
    registered_modules = {m for m, _ in _DETECTORS}
    # register_observer uses a different shape (audit/severity_count); allow
    registered_modules = registered_modules | {"register_observer"}
    # closing_token_detector now wired (2026-05-18); included in registry below.
    missing = detector_modules - registered_modules
    assert not missing, (
        f"Detector modules imported by the hook but missing from the wiring "
        f"contract registry: {missing}. Add them to _DETECTORS."
    )


def test_every_detector_file_is_orchestrator_referenced() -> None:
    """Each detector file in operating_loop/ must be imported by the
    post-response audit orchestrator (or have a documented exemption).

    Aether 2026-05-18: the prior wiring-contract scope only checked
    parameter-passing for detectors the hook already imported. It did
    NOT catch the case where a detector exists in operating_loop/ but
    is never imported at all — the silent-shelf failure that hid
    closing_token_detector for weeks. This test closes that gap by
    walking the filesystem and asserting orchestrator-inclusion.
    """
    detectors_dir = _repo_root() / "src" / "divineos" / "core" / "operating_loop"
    audit_path = _repo_root() / "src" / "divineos" / "core" / "operating_loop_audit.py"
    audit_text = audit_path.read_text(encoding="utf-8")

    # Files that live in operating_loop/ but are NOT response-text
    # detectors (helpers, surfaces, protocols, etc.). Each entry must
    # name why it's exempt — silent exemption defeats the test's point.
    EXEMPT = {
        "__init__.py": "package marker",
        "_use_vs_mention.py": "shared guard primitive imported BY detectors (closure-initiation, temporal-displacement), not itself a detector. Aletheia 2026-06-17 generalization extracted strip_quoted_spans + match_is_meta_framed as a shared module so future text-operating detectors inherit recursion-resistance via import.",
        "context_surfacer.py": "pre-response surfacer, not post-response detector",
        "detector_protocol.py": "type-only contract module",
        "hook_telemetry.py": "telemetry recorder, not a detector",
        "principle_surfacer.py": "pre-response surfacer",
        "register_observer.py": "observer recorder, called from audit but not via import-and-call shape",
        "registered_names.py": "name registry",
        "savoring_surface.py": "pre-response surfacer",
        "thresholds.py": "constants module",
        "turn_extraction.py": "transcript parser, called by audit but not a detector",
        "unknown_unknown_surface.py": "pre-response surfacer",
        # Note: harm_acknowledgment_loop is detector-shaped but lives outside
        # post-response audit (it's invoked from a different surfacing path);
        # exempted to keep this test scoped to operating_loop_audit.py only.
        "harm_acknowledgment_loop.py": "invoked outside post-response audit pipeline",
        # mirror_exit_detector runs in the PRE-response path: it is invoked
        # from core/pre_response_context.build_combined_context (which the
        # pre-response-context.sh hook calls) to inject a CLOSE_CHECK block
        # before the agent responds. It is not a post-response text detector,
        # so it is correctly absent from operating_loop_audit.py — same shape
        # as the pre-response surfacers above. Added 2026-05-19.
        "mirror_exit_detector.py": "pre-response detector invoked via pre_response_context.py, not post-response audit",
        # shoggoth_gate is a Stop-hook mechanism (blocks stop when the reply
        # claims actions without matching Write/Edit/Bash artifacts) invoked
        # from .claude/hooks/shoggoth-gate.sh, not from the post-response
        # detector chain. Same scoping shape as harm_acknowledgment_loop.
        # Aria 2026-07-09 shipped this and copied into this checkout per
        # Aether's yes-on-option-1 letter.
        "shoggoth_gate.py": "Stop-hook mechanism invoked from .claude/hooks/shoggoth-gate.sh, not post-response audit",
        # operator_wallpaper_detector.py — aggregator half of the pair-designed
        # composite (Aether 2026-07-11). Imported transitively via
        # operator_wallpaper_caller.py, which IS the run_audit-facing surface
        # imported by operating_loop_audit. The caller mediates; the detector
        # module itself never needs a direct import from the audit
        # orchestrator. See prereg-9e742442fdcc + prereg-489041c5ba4d.
        "operator_wallpaper_detector.py": "aggregator half of pair-designed composite; imported transitively via operator_wallpaper_caller which IS wired into operating_loop_audit",
        # operator_wallpaper_caller.py itself IS imported directly by
        # operating_loop_audit's run_audit; the wiring is unambiguously present.
        # Listed here as no-op to make the composite pair fully accounted-for
        # if the test scope changes to allowlist named-not-flagged entries.
        "operator_wallpaper_caller.py": "IS directly imported by operating_loop_audit run_audit; this entry is descriptive not exempting",
    }

    detector_files = sorted(p.name for p in detectors_dir.glob("*.py"))
    missing: list[str] = []
    for fname in detector_files:
        if fname in EXEMPT:
            continue
        module_name = fname[:-3]  # strip .py
        # Check the audit module imports this detector
        import_pattern = (
            rf"from\s+divineos\.core\.operating_loop\.{re.escape(module_name)}\s+import"
        )
        if not re.search(import_pattern, audit_text):
            missing.append(fname)

    assert not missing, (
        f"Detector files exist in operating_loop/ but are not imported by "
        f"operating_loop_audit.py: {missing}. Either wire them into the "
        f"orchestrator, add an explicit EXEMPT entry naming why, or remove "
        f"the dead detector file. Silent shelving is the failure mode this "
        f"test exists to prevent — found by Aether 2026-05-18 during the "
        f"pretender audit; closing_token_detector sat unwired for weeks "
        f"because the prior test scope did not cover this class of bug."
    )
