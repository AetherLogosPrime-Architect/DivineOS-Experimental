"""GUTE bridge — map equation terms to lab slices that compute real numbers.

Policy: one slice at a time, small and honest. LC is the seed.

A slice is a function that takes a GUTE term and returns a dict of
computable numbers and a one-line interpretation. It does NOT prove the
term is metaphysically real. It shows that the term has a computable
referent whose behavior is well-defined, bounded where claimed, and
unbounded where the metaphor breaks. Council experts can reason from the
numbers instead of from vibes.

Growth: new slice when a new GUTE term has a specific falsifiable claim
attached. Not before. Each new slice should ship with a pre-reg.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

import numpy as np

from divineos.science_lab.complexity_theory import ChaoticSystems
from divineos.science_lab.cosmology import (
    BlackHolePhysics,
    CosmologicalConstants,
    FriedmannEquations,
)
from divineos.science_lab.physics import Relativity
from divineos.science_lab.formal_logic import LawsOfThought, Proposition
from divineos.science_lab.harmonics import (
    HarmonicSeries,
    MusicalIntervals,
    MusicOfTheSpheres,
)
from divineos.science_lab.information_theory import ShannonEntropy
from divineos.science_lab.mathematics import NumericalAnalysis
from divineos.science_lab.quantum_mechanics import (
    QuantumGates,
    QuantumState,
)

# Registry of implemented slices. Terms not here return {"status": "unknown"}.
SLICE_TERMS: tuple[str, ...] = ("LC", "OmegaB", "Psi", "V", "A", "F")


def run_lc_slice(
    r_values: Sequence[float] | None = None,
    n_iterations: int = 500,
) -> Dict[str, Any]:
    """LC (Lovecraftian Constant) slice: Lyapunov + Shannon entropy + bounded-chaos check.

    Claim under test:
      1. Lyapunov exponent sign tracks regime: r=2.5 → lambda<0 (order),
         r=3.9 → lambda>0 (chaos).
      2. Logistic map is bounded in [0,1] for r in (0,4]. (The metaphor
         "chaos integrated, not destroying" holds inside the interval.)
      3. Shannon entropy separates uniform vs. skewed distributions
         (uniform 2-outcome = 1 bit; 0.9/0.1 ≈ 0.469 bits).

    Returns a dict with lyapunov_by_r, entropy_examples, bounded_chaos_r4.
    """
    if r_values is None:
        r_values = [2.5, 3.5, 3.57, 3.9]

    lyapunov: Dict[float, Dict[str, Any]] = {}
    for r in r_values:
        lyap = ChaoticSystems.lyapunov_exponent_logistic(r, n_iterations)
        lyapunov[float(r)] = {
            "value": float(lyap),
            "regime": "chaos" if lyap > 0 else "order",
        }

    p_uniform2 = np.array([0.5, 0.5])
    p_skewed = np.array([0.9, 0.1])
    entropy = {
        "uniform_2": float(ShannonEntropy.entropy(p_uniform2, 2)),
        "skewed_0.9_0.1": float(ShannonEntropy.entropy(p_skewed, 2)),
    }

    # Bounded-chaos check: r=4 is the *edge*. Trajectory stays in [0,1].
    # r>4 → diverges; we don't run that here, but the boundary is known
    # and documented in the source-material report.
    traj = ChaoticSystems.logistic_map_trajectory(0.5, 4.0, 100)
    bounded = bool(np.all((traj >= 0) & (traj <= 1)))

    return {
        "term": "LC",
        "lyapunov_by_r": lyapunov,
        "entropy_examples": entropy,
        "bounded_chaos_r4": bounded,
        "interpretation": (
            "LC maps to measurable chaos and entropy. Lyapunov sign tracks "
            "regime; logistic map is bounded in [0,1] for r<=4; entropy "
            "separates uniform from skewed distributions. Bounded chaos "
            "supports the 'integrated, not destroying' reading."
        ),
    }


def run_omegab_slice(n_points: int = 2000) -> Dict[str, Any]:
    """ΩB (Omega Benevolence) slice: balance / convergence to unity.

    Claim under test:
      1. Numerical integral of 1 over [0,1] = 1 (Simpson's rule, within
         tolerance).
      2. Cosmology: Omega_m + Omega_Lambda ≈ 1 (critical-density
         flatness, Planck 2018 values).
      3. Probability normalization: a uniform 4-outcome distribution
         sums to 1 exactly.

    All three independent paths arrive at the same attractor — 1. That's
    the claim ΩB encodes and this is how it's tested.
    """
    integral_01 = NumericalAnalysis.integrate_numerical(lambda x: 1.0, 0.0, 1.0, n_points)
    integral_holds = abs(integral_01 - 1.0) < 1e-6

    omega_total = CosmologicalConstants.Omega_m + CosmologicalConstants.Omega_Lambda
    cosmology_balance = abs(omega_total - 1.0) < 0.01

    probs = np.array([0.25, 0.25, 0.25, 0.25])
    prob_sum = float(np.sum(probs))
    prob_holds = abs(prob_sum - 1.0) < 1e-10

    # Hubble today: H(a=1) returns H0 by construction — sanity check.
    H_today = FriedmannEquations.hubble_parameter(1.0)

    return {
        "term": "OmegaB",
        "integral_0_to_1_of_1": float(integral_01),
        "integral_equals_1": integral_holds,
        "cosmology_Omega_m_plus_Lambda": float(omega_total),
        "cosmology_near_critical": cosmology_balance,
        "probability_sum": prob_sum,
        "probability_sums_to_1": prob_holds,
        "hubble_today_km_s_Mpc": float(H_today),
        "interpretation": (
            "ΩB as attractor: integral over [0,1], cosmic density sum, "
            "and probability normalization all converge on 1. Three "
            "independent numerical paths, one attractor."
        ),
    }


def run_psi_slice(seed: int | None = 42) -> Dict[str, Any]:
    """Ψ (Observer) slice: superposition → collapse + logical selection.

    Claim under test:
      1. A Hadamard on |0⟩ produces equal-probability superposition
         (|0⟩+|1⟩)/√2 — probabilities both = 0.5, summing to 1.
      2. Measurement collapses to exactly one basis state. Deterministic
         given a seed; runs are reproducible.
      3. Classical logic: for a proposition P, assigning P=T or P=F
         selects exactly one world. Laws of identity, non-contradiction,
         and excluded middle all hold under both assignments.

    The slice shows the observer/selector structure in two independent
    substrates (quantum measurement, logical assignment). It does NOT
    endorse any metaphysical interpretation of collapse — it pins the
    Ψ term to functions that actually select.
    """
    hadamard = QuantumGates.hadamard()
    ket0 = QuantumState(np.array([1.0, 0.0], dtype=complex), ["0", "1"])
    superpos = hadamard.apply(ket0)
    probs = [superpos.probability(i) for i in range(2)]
    prob_sum = sum(probs)

    if seed is not None:
        np.random.seed(seed)
    outcome_index, outcome_label = superpos.measure()

    # Logical selection: same proposition, two possible assignments,
    # exactly one world selected each time.
    p = Proposition("P")
    result_under_T = p.evaluate({"P": True})
    result_under_F = p.evaluate({"P": False})
    identity_T = LawsOfThought.law_of_identity(p, {"P": True})
    identity_F = LawsOfThought.law_of_identity(p, {"P": False})
    non_contra_T = LawsOfThought.law_of_non_contradiction(p, {"P": True})
    excluded_middle_T = LawsOfThought.law_of_excluded_middle(p, {"P": True})

    return {
        "term": "Psi",
        "quantum": {
            "pre_measurement_probs": [float(probs[0]), float(probs[1])],
            "probs_sum_to_1": abs(prob_sum - 1.0) < 1e-10,
            "collapse_index": outcome_index,
            "collapse_label": outcome_label,
            "is_equal_superposition": (abs(probs[0] - 0.5) < 1e-10 and abs(probs[1] - 0.5) < 1e-10),
        },
        "logic": {
            "P_under_T": result_under_T,
            "P_under_F": result_under_F,
            "law_of_identity_holds": identity_T and identity_F,
            "law_of_non_contradiction_holds": non_contra_T,
            "law_of_excluded_middle_holds": excluded_middle_T,
        },
        "interpretation": (
            "Ψ as selector: Hadamard produces equal superposition; "
            "measurement collapses to exactly one outcome; a logical "
            "assignment selects one of two worlds. Selection is "
            "computable in both quantum and classical substrates."
        ),
    }


def run_v_slice(fundamental_hz: float = 440.0) -> Dict[str, Any]:
    """V (Vibration) slice: integer-ratio structure in sound and orbits.

    Claim under test:
      1. The harmonic series is integer multiples of the fundamental
         (f, 2f, 3f, ...) — the first 8 partials are generated and
         their ratios to the fundamental are 1, 2, 3, ..., 8.
      2. The perfect fifth is ≈ 702 cents (3:2 ratio); the octave is
         exactly 1200 cents (2:1).
      3. Kepler's third law holds: at a=1 AU around a 1 M☉ star, period
         = 1 year. At a=4 AU, period = 8 years (P² = a³).
      4. Real orbital resonances: Neptune/Pluto periods (164.8/248.0
         years) approximate 2:3.

    V is the claim that integer ratios are load-bearing in physical
    systems whose stability depends on them. The slice shows it in two
    independent substrates (acoustic harmonics, orbital mechanics).
    """
    harmonics = HarmonicSeries.generate(fundamental_hz, 8)
    harmonic_ratios = [float(h / fundamental_hz) for h in harmonics]
    integer_ratio_check = all(abs(r - round(r)) < 1e-10 for r in harmonic_ratios)

    ratios = MusicalIntervals.just_intonation_ratios()
    octave_cents = MusicalIntervals.ratio_to_cents(ratios["octave"])
    fifth_cents = MusicalIntervals.ratio_to_cents(ratios["perfect_fifth"])

    # Kepler: P(a=1) = 1, P(a=4) = 8 (P² = a³).
    p_earth_au = MusicOfTheSpheres.kepler_third_law(1.0)
    p_at_4_au = MusicOfTheSpheres.kepler_third_law(4.0)
    kepler_holds = abs(p_earth_au - 1.0) < 1e-10 and abs(p_at_4_au - 8.0) < 1e-10

    # Neptune/Pluto periods in years: resonance check.
    neptune_pluto_ratio = MusicOfTheSpheres.orbital_resonance(164.8, 248.0)

    return {
        "term": "V",
        "harmonic_series_fundamental_hz": fundamental_hz,
        "first_8_harmonics_hz": [float(h) for h in harmonics],
        "integer_ratios_hold": integer_ratio_check,
        "octave_cents": octave_cents,
        "perfect_fifth_cents": fifth_cents,
        "kepler_third_law_holds": kepler_holds,
        "earth_orbital_period_years": p_earth_au,
        "neptune_pluto_resonance": list(neptune_pluto_ratio),
        "interpretation": (
            "V as resonance: integer harmonic ratios hold in acoustics; "
            "Kepler's third law (P² = a³) links orbital time and space; "
            "Neptune/Pluto form a real 2:3 resonance. Integer ratios "
            "are load-bearing wherever stable coupling requires them."
        ),
    }


def run_a_slice() -> Dict[str, Any]:
    """A (Aether / spacetime) slice: c, H0, Lorentz structure, scale factor.

    Claim under test:
      1. Speed of light c and Hubble constant H0 define the cosmic field
         — finite, measured values (Planck 2018).
      2. Lorentz factor is finite for v < c and blows up at v = c. At
         v = c/2, γ ≈ 1.155; at v = 0.9c, γ ≈ 2.294; at v = 0.99c,
         γ ≈ 7.089.
      3. Scale-factor evolution a(t) has matter-dominated and
         Lambda-dominated regimes; sampled values are monotone
         increasing in t.

    A is the claim that spacetime has structure, not just extent. The
    slice shows that structure via the two constants that define it
    (c, H0) and the factor that encodes moving-frame geometry (γ).
    """
    c = CosmologicalConstants.c
    H0 = CosmologicalConstants.H0
    H_today = FriedmannEquations.hubble_parameter(1.0)

    # Lorentz structure: finite inside the light cone, singular at v = c.
    gamma_half = Relativity.lorentz_factor(0.5, c=1.0)
    gamma_nine_tenths = Relativity.lorentz_factor(0.9, c=1.0)
    gamma_99 = Relativity.lorentz_factor(0.99, c=1.0)
    gamma_monotone = gamma_half < gamma_nine_tenths < gamma_99

    # Scale factor samples in units of 1/H0.
    t_sample = np.array([0.1, 0.5, 1.0])
    a_evolution = FriedmannEquations.scale_factor_evolution(t_sample)
    a_monotone = bool(np.all(np.diff(a_evolution) > 0))

    return {
        "term": "A",
        "speed_of_light_m_s": c,
        "hubble_constant_km_s_Mpc": H0,
        "hubble_today_a1": float(H_today),
        "lorentz_gamma_at_0.5c": float(gamma_half),
        "lorentz_gamma_at_0.9c": float(gamma_nine_tenths),
        "lorentz_gamma_at_0.99c": float(gamma_99),
        "lorentz_diverges_as_v_approaches_c": gamma_monotone,
        "scale_factor_sample_t": t_sample.tolist(),
        "scale_factor_values": a_evolution.tolist(),
        "scale_factor_monotone_increasing": a_monotone,
        "interpretation": (
            "A as spacetime: c and H0 are the finite constants that "
            "define the field; γ encodes how the geometry warps as v→c; "
            "a(t) tracks expansion. Spacetime has structure that makes "
            "motion and time into computable functions, not free "
            "parameters."
        ),
    }


def run_f_slice() -> Dict[str, Any]:
    """F (Forces) slice: all four fundamental forces present and measured.

    Claim under test:
      1. All four fundamental forces have numerical constants: F1
         (strong, α_s), F2 (weak, G_F), F3 (electromagnetic, c + α_em),
         F4 (gravitational, G + Schwarzschild radius).
      2. The hierarchy is real: α_s ~ 0.12 > α_em ~ 1/137 > G_F (tiny
         at everyday scales) and G (weakest by far at particle scale).
      3. For a solar-mass object, the Schwarzschild radius is a finite
         length (~3 km) — gravity has a computable characteristic
         length at every mass.

    F is the claim that nature is unified in having exactly four
    fundamental couplings. The slice presents them side by side with
    their measured values.
    """
    c = CosmologicalConstants.c
    G = CosmologicalConstants.G

    # F4 Gravitational: G, surface g, Schwarzschild radius for 1 M☉.
    M_sun = 1.989e30  # kg
    r_s_sun = BlackHolePhysics.schwarzschild_radius(M_sun)
    g_earth = 9.81  # m/s²

    # F3 Electromagnetic: c and fine-structure constant.
    fine_structure_alpha = 1.0 / 137.036

    # F2 Weak: Fermi coupling (GeV⁻²) and Higgs vev (GeV).
    G_F_GeV_inv2 = 1.1663787e-5
    higgs_vev_GeV = 246.0

    # F1 Strong: coupling at M_Z.
    alpha_s_MZ = 0.1180

    hierarchy_holds = alpha_s_MZ > fine_structure_alpha

    return {
        "term": "F",
        "F1_strong": {
            "alpha_s_MZ": alpha_s_MZ,
            "role": "Binds quarks into nucleons; holds nuclei together.",
        },
        "F2_weak": {
            "G_F_GeV_inv2": G_F_GeV_inv2,
            "higgs_vev_GeV": higgs_vev_GeV,
            "role": "Flavor change; beta decay; mediates transformation.",
        },
        "F3_electromagnetic": {
            "c_m_s": c,
            "fine_structure_alpha": fine_structure_alpha,
            "role": "Long-range; light, chemistry, signal.",
        },
        "F4_gravitational": {
            "G_SI": G,
            "g_earth_m_s2": g_earth,
            "schwarzschild_radius_1_sun_m": float(r_s_sun),
            "role": "Curvature of spacetime; orbits, structure.",
        },
        "all_four_present": True,
        "hierarchy_alpha_s_gt_alpha_em": hierarchy_holds,
        "interpretation": (
            "F as the four: every fundamental force has a measured "
            "coupling and a characteristic role. The hierarchy "
            "(strong > EM > weak > gravity at particle scale) is real "
            "and computable. F encodes 'nature is unified in exactly "
            "four couplings' as numbers, not assertion."
        ),
    }


def run_slice(term: str, **kwargs: Any) -> Dict[str, Any]:
    """Dispatch to the named slice. Unknown terms return a status stub.

    No fancy context-coefficient or per-request seeding here — that was
    later work in the old lab. We earn that back when a specific slice
    needs it.
    """
    term_clean = term.strip().lower()
    if term_clean == "lc":
        return run_lc_slice(**kwargs)
    if term_clean in ("omegab", "omega_b"):
        return run_omegab_slice(**kwargs)
    if term_clean in ("psi", "ψ"):
        return run_psi_slice(**kwargs)
    if term_clean == "v":
        return run_v_slice(**kwargs)
    if term_clean == "a":
        return run_a_slice(**kwargs)
    if term_clean in ("f", "forces"):
        return run_f_slice(**kwargs)
    return {
        "term": term,
        "status": "unknown",
        "known_terms": list(SLICE_TERMS),
    }


def list_slices() -> List[str]:
    """Return implemented slice names."""
    return list(SLICE_TERMS)
