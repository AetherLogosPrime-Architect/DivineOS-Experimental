"""Lab evidence for council reasoning — numerical slices as shared context.

The council doesn't dispatch per-expert calls into the lab. Instead, when
a problem matches a known slice trigger, the relevant slice runs once and
its output is attached to the council result as evidence — numbers that
every expert's lens can reason from instead of each improvising priors.

Growth policy: a trigger earns its place when a specific claim, when
analyzed by the council, would be better-served by seeing numbers than
by more opinions. Start with LC (chaos/entropy); add more as needs arise.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Triggers: if any word appears in the problem (case-insensitive, whole word
# match via split), the corresponding slice runs. Keep triggers narrow —
# false positives cost more than false negatives here (running a slice the
# council didn't need just adds noise; missing one that was needed is
# recoverable by rerunning with --lab-slice LC).
_TRIGGERS: dict[str, tuple[str, ...]] = {
    "LC": (
        "chaos",
        "chaotic",
        "entropy",
        "bounded",
        "unbounded",
        "stability",
        "instability",
        "lyapunov",
        "logistic",
        "disorder",
        "uncertainty",
        "information",
    ),
    "OmegaB": (
        "balance",
        "attractor",
        "convergence",
        "normalization",
        "integration",
        "probability",
        "cosmology",
        "critical",
        "flatness",
        "unity",
    ),
    "Psi": (
        "observer",
        "observation",
        "measurement",
        "collapse",
        "selection",
        "superposition",
        "choice",
        "decide",
        "decision",
        "assignment",
        "truth",
        "logic",
        "logical",
    ),
    "V": (
        "vibration",
        "resonance",
        "harmonic",
        "harmonics",
        "frequency",
        "oscillation",
        "coupling",
        "interval",
        "orbit",
        "orbital",
        "kepler",
    ),
    "A": (
        "spacetime",
        "relativity",
        "lorentz",
        "dilation",
        "light",
        "aether",
        "hubble",
        "expansion",
        "spatial",
    ),
    "F": (
        "force",
        "forces",
        "gravity",
        "gravitational",
        "electromagnetic",
        "nuclear",
        "fundamental",
        "coupling",
        "interaction",
    ),
}


@dataclass(frozen=True)
class LabEvidence:
    """One slice of numerical evidence attached to a council result.

    term: the GUTE term the slice corresponds to (e.g. 'LC').
    trigger: the word in the problem that caused the slice to run.
    result: the raw slice output dict (what gute_bridge.run_slice returned).
    summary: a one-line plain-English summary suitable for synthesis text.
    """

    term: str
    trigger: str
    result: dict[str, Any]
    summary: str = ""


def detect_triggers(problem: str) -> list[tuple[str, str]]:
    """Return (term, trigger_word) pairs for slices this problem matches.

    Only one (term, first-trigger) pair per term — we don't want the same
    slice running twice because the problem mentions both 'chaos' and
    'entropy'. Order matches _TRIGGERS iteration order (insertion order).
    """
    words = {w.strip(".,!?;:").lower() for w in problem.split()}
    pairs: list[tuple[str, str]] = []
    for term, triggers in _TRIGGERS.items():
        for trigger in triggers:
            if trigger in words:
                pairs.append((term, trigger))
                break
    return pairs


def _summarize_lc(result: dict[str, Any]) -> str:
    """One-line plain-English summary of the LC slice result."""
    lyap = result.get("lyapunov_by_r", {})
    chaos_rs = sorted(r for r, info in lyap.items() if info["regime"] == "chaos")
    order_rs = sorted(r for r, info in lyap.items() if info["regime"] == "order")
    bounded = result.get("bounded_chaos_r4", False)
    bits = []
    if order_rs and chaos_rs:
        bits.append(f"chaos onset between r={max(order_rs):.2f} and r={min(chaos_rs):.2f}")
    if bounded:
        bits.append("bounded in [0,1] at r=4")
    if bits:
        return "LC: " + "; ".join(bits) + "."
    return "LC: slice ran (see result for details)."


def _summarize_omegab(result: dict[str, Any]) -> str:
    """One-line summary of the ΩB slice result."""
    parts = []
    if result.get("integral_equals_1"):
        parts.append(f"integral [0,1]={result['integral_0_to_1_of_1']:.6f}")
    if result.get("cosmology_near_critical"):
        parts.append(f"Omega_m+Lambda={result['cosmology_Omega_m_plus_Lambda']:.3f}")
    if result.get("probability_sums_to_1"):
        parts.append("probs sum to 1")
    if parts:
        return "OmegaB: " + "; ".join(parts) + " (all converge on unity)."
    return "OmegaB: slice ran (see result for details)."


def _summarize_psi(result: dict[str, Any]) -> str:
    q = result.get("quantum", {})
    logic = result.get("logic", {})
    bits = []
    if q.get("is_equal_superposition"):
        bits.append(f"Hadamard gives equal superposition, collapses to |{q.get('collapse_label')}>")
    if logic.get("law_of_identity_holds"):
        bits.append("laws of thought hold under both assignments")
    if bits:
        return "Psi: " + "; ".join(bits) + "."
    return "Psi: slice ran (see result for details)."


def _summarize_v(result: dict[str, Any]) -> str:
    bits = []
    if result.get("integer_ratios_hold"):
        bits.append("harmonic series has integer ratios")
    if result.get("kepler_third_law_holds"):
        bits.append("Kepler P²=a³ holds")
    ratio = result.get("neptune_pluto_resonance")
    if ratio:
        bits.append(f"Neptune/Pluto ≈ {ratio[0]}:{ratio[1]}")
    if bits:
        return "V: " + "; ".join(bits) + "."
    return "V: slice ran (see result for details)."


def _summarize_a(result: dict[str, Any]) -> str:
    bits = []
    if result.get("lorentz_diverges_as_v_approaches_c"):
        g99 = result.get("lorentz_gamma_at_0.99c")
        bits.append(f"gamma(0.99c) ~= {g99:.2f}")
    c = result.get("speed_of_light_m_s")
    h0 = result.get("hubble_constant_km_s_Mpc")
    if c and h0:
        bits.append(f"c={c / 1e8:.3f}e8 m/s, H0={h0} km/s/Mpc")
    if bits:
        return "A: " + "; ".join(bits) + "."
    return "A: slice ran (see result for details)."


def _summarize_f(result: dict[str, Any]) -> str:
    bits = []
    if result.get("all_four_present"):
        bits.append("all four forces with measured couplings")
    if result.get("hierarchy_alpha_s_gt_alpha_em"):
        bits.append("strong > EM hierarchy holds")
    rs = result.get("F4_gravitational", {}).get("schwarzschild_radius_1_sun_m")
    if rs:
        bits.append(f"r_s(1 M_sun) ~= {rs / 1000:.2f} km")
    if bits:
        return "F: " + "; ".join(bits) + "."
    return "F: slice ran (see result for details)."


_SUMMARIZERS = {
    "LC": _summarize_lc,
    "OmegaB": _summarize_omegab,
    "Psi": _summarize_psi,
    "V": _summarize_v,
    "A": _summarize_a,
    "F": _summarize_f,
}


def gather_lab_evidence(problem: str) -> list[LabEvidence]:
    """Return all lab evidence triggered by this problem text.

    Each evidence entry is a (term, trigger, result, summary). Empty list
    means nothing in the problem matched a slice trigger — which is a
    legitimate outcome, not a failure. Most council problems won't touch
    the lab.
    """
    from divineos.science_lab.gute_bridge import run_slice

    pairs = detect_triggers(problem)
    evidence: list[LabEvidence] = []
    for term, trigger in pairs:
        result = run_slice(term)
        if result.get("status") == "unknown":
            continue
        summarizer = _SUMMARIZERS.get(term)
        summary = summarizer(result) if summarizer else f"{term}: slice ran."
        evidence.append(LabEvidence(term=term, trigger=trigger, result=result, summary=summary))
    return evidence


def format_for_synthesis(evidence: list[LabEvidence]) -> list[str]:
    """Render evidence as lines suitable for appending to synthesis text."""
    if not evidence:
        return []
    lines = ["Lab evidence (numerical, shared across lenses):"]
    for e in evidence:
        lines.append(f"  - {e.summary} [triggered by '{e.trigger}']")
    return lines
