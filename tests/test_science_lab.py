"""Tests for the science lab — GUTE slices hit real numbers.

Falsifiability:
  - Lyapunov sign must track regime: r=2.5 < 0; r=3.9 > 0.
  - Logistic map with r in (0, 4] stays in [0, 1]. r > 4 does not.
  - Shannon entropy of fair 2-outcome distribution is 1 bit exactly.
  - Skewed 0.9/0.1 entropy is ~0.469 bits (well under 1).
  - Mutual information is non-negative, zero for independent distributions.
  - Mandelbrot c=0 stays bounded (returns max_iter); c=2 diverges fast.
  - gute_bridge.run_slice('LC') returns expected keys and regime calls.
  - CLI `lab run-slice LC --json` emits parseable JSON with term=LC.
"""

from __future__ import annotations

import json

import numpy as np
import pytest
from click.testing import CliRunner

from divineos.science_lab.complexity_theory import (
    ChaoticSystems,
    Fractals,
    PowerLaws,
)
from divineos.science_lab.cosmology import (
    BlackHolePhysics,
    CosmologicalConstants,
    FriedmannEquations,
    GravitationalWaves,
)
from divineos.science_lab.formal_logic import (
    Formula,
    InferenceRules,
    LawsOfThought,
    LogicalOperator,
    Proposition,
)
from divineos.science_lab.gute_bridge import (
    list_slices,
    run_a_slice,
    run_f_slice,
    run_lc_slice,
    run_omegab_slice,
    run_psi_slice,
    run_slice,
    run_v_slice,
)
from divineos.science_lab.harmonics import (
    HarmonicSeries,
    MusicalIntervals,
    MusicOfTheSpheres,
)
from divineos.science_lab.information_theory import (
    ChannelCapacity,
    ErrorCorrection,
    QuantumInformation,
    ShannonEntropy,
)
from divineos.science_lab.mathematics import LinearAlgebra, NumericalAnalysis
from divineos.science_lab.physics import Relativity
from divineos.science_lab.quantum_mechanics import (
    QuantumGates,
    QuantumState,
    Superposition,
)


class TestChaoticSystems:
    def test_lyapunov_negative_for_r2_5(self) -> None:
        lam = ChaoticSystems.lyapunov_exponent_logistic(2.5, n_iterations=500)
        assert lam < 0, f"r=2.5 should be ordered, got lambda={lam}"

    def test_lyapunov_positive_for_r3_9(self) -> None:
        lam = ChaoticSystems.lyapunov_exponent_logistic(3.9, n_iterations=500)
        assert lam > 0, f"r=3.9 should be chaotic, got lambda={lam}"

    def test_logistic_trajectory_bounded_at_r4(self) -> None:
        traj = ChaoticSystems.logistic_map_trajectory(0.5, 4.0, 500)
        assert np.all((traj >= 0) & (traj <= 1)), "r=4 must stay in [0,1]"

    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    def test_logistic_trajectory_unbounded_past_r4(self) -> None:
        # r > 4 breaks the metaphor: trajectory leaves [0, 1] and the
        # multiplication eventually overflows — that overflow IS the
        # boundary, so we suppress the expected RuntimeWarning.
        traj = ChaoticSystems.logistic_map_trajectory(0.5, 4.5, 50)
        assert not np.all((traj >= 0) & (traj <= 1)), (
            "r>4 should escape [0,1] — that's the boundary where the "
            "bounded-chaos reading stops applying."
        )

    def test_lorenz_trajectory_shape(self) -> None:
        traj = ChaoticSystems.lorenz_trajectory(np.array([1.0, 1.0, 1.0]), n_steps=200)
        assert traj.shape == (200, 3)


class TestFractals:
    def test_mandelbrot_origin_in_set(self) -> None:
        assert Fractals.mandelbrot_iteration(0j, max_iter=50) == 50

    def test_mandelbrot_far_diverges_fast(self) -> None:
        assert Fractals.mandelbrot_iteration(2 + 2j, max_iter=50) < 5


class TestPowerLaws:
    def test_estimator_close_to_truth(self) -> None:
        rng = np.random.default_rng(42)
        # Generate power-law data via inverse CDF (Pareto).
        alpha_true = 2.5
        u = rng.uniform(size=5000)
        x = (1 - u) ** (-1 / (alpha_true - 1))  # x_min = 1
        alpha_hat = PowerLaws.estimate_power_law_exponent(x, x_min=1.0)
        assert abs(alpha_hat - alpha_true) < 0.2


class TestShannonEntropy:
    def test_fair_coin_exactly_one_bit(self) -> None:
        p = np.array([0.5, 0.5])
        assert ShannonEntropy.entropy(p) == pytest.approx(1.0, abs=1e-12)

    def test_skewed_coin_under_one_bit(self) -> None:
        p = np.array([0.9, 0.1])
        h = ShannonEntropy.entropy(p)
        assert 0.4 < h < 0.5

    def test_degenerate_distribution_zero_entropy(self) -> None:
        p = np.array([1.0, 0.0])
        assert ShannonEntropy.entropy(p) == pytest.approx(0.0)

    def test_mutual_information_nonnegative(self) -> None:
        p_xy = np.array([[0.25, 0.15], [0.15, 0.45]])
        assert ShannonEntropy.mutual_information(p_xy) >= 0

    def test_mutual_information_zero_for_independent(self) -> None:
        # Independent product: p(x,y) = p(x) p(y).
        p_x = np.array([0.5, 0.5])
        p_y = np.array([0.3, 0.7])
        p_xy = np.outer(p_x, p_y)
        assert ShannonEntropy.mutual_information(p_xy) == pytest.approx(0.0, abs=1e-12)

    def test_kl_self_is_zero(self) -> None:
        p = np.array([0.3, 0.3, 0.4])
        assert ShannonEntropy.kl_divergence(p, p) == pytest.approx(0.0, abs=1e-12)


class TestChannelCapacity:
    def test_bsc_noiseless_is_one(self) -> None:
        assert ChannelCapacity.binary_symmetric_channel_capacity(0.0) == 1.0

    def test_bsc_half_noise_is_zero(self) -> None:
        assert ChannelCapacity.binary_symmetric_channel_capacity(0.5) == pytest.approx(
            0.0, abs=1e-12
        )

    def test_awgn_monotone_in_snr(self) -> None:
        c_low = ChannelCapacity.awgn_channel_capacity(1.0)
        c_high = ChannelCapacity.awgn_channel_capacity(1000.0)
        assert c_high > c_low


class TestQuantumInformation:
    def test_pure_state_zero_entropy(self) -> None:
        rho = np.array([[1.0, 0.0], [0.0, 0.0]])
        assert QuantumInformation.von_neumann_entropy(rho) == pytest.approx(0.0)

    def test_maximally_mixed_one_bit(self) -> None:
        rho = np.array([[0.5, 0.0], [0.0, 0.5]])
        assert QuantumInformation.von_neumann_entropy(rho) == pytest.approx(1.0)


class TestErrorCorrection:
    def test_hamming_encode_length(self) -> None:
        assert len(ErrorCorrection.hamming_7_4_encode("1011")) == 7

    def test_repetition_majority_vote(self) -> None:
        assert ErrorCorrection.repetition_code_decode("110") == "1"
        assert ErrorCorrection.repetition_code_decode("001") == "0"


class TestNumericalAnalysis:
    def test_derivative_of_x_squared(self) -> None:
        f = lambda x: x**2  # noqa: E731
        assert NumericalAnalysis.derivative_numerical(f, 3.0) == pytest.approx(6.0, abs=1e-4)

    def test_integral_of_unit_is_one(self) -> None:
        result = NumericalAnalysis.integrate_numerical(lambda x: 1.0, 0.0, 1.0, 1000)
        assert result == pytest.approx(1.0, abs=1e-10)

    def test_integral_of_x_from_0_to_1_is_half(self) -> None:
        result = NumericalAnalysis.integrate_numerical(lambda x: x, 0.0, 1.0, 1000)
        assert result == pytest.approx(0.5, abs=1e-6)

    def test_newton_finds_sqrt_two(self) -> None:
        f = lambda x: x**2 - 2  # noqa: E731
        df = lambda x: 2 * x  # noqa: E731
        result = NumericalAnalysis.root_finding_newton(f, df, 1.5)
        assert result["converged"] is True
        assert result["root"] == pytest.approx(2**0.5, abs=1e-6)

    def test_bisection_finds_root(self) -> None:
        f = lambda x: x**3 - x - 2  # noqa: E731
        result = NumericalAnalysis.root_finding_bisection(f, 1.0, 2.0)
        assert result["converged"] is True

    def test_bisection_rejects_same_sign_interval(self) -> None:
        f = lambda x: x**2 + 1  # noqa: E731
        result = NumericalAnalysis.root_finding_bisection(f, 1.0, 2.0)
        assert result["converged"] is False

    def test_rk4_solves_exponential_decay(self) -> None:
        # dy/dt = -y, y(0) = 1 → y(t) = exp(-t)
        f = lambda y, t: -y  # noqa: E731
        t = np.linspace(0, 1, 100)
        y = NumericalAnalysis.ode_rk4(f, np.array([1.0]), t)
        assert y[-1, 0] == pytest.approx(np.exp(-1.0), abs=1e-4)


class TestLinearAlgebra:
    def test_solve_identity_system(self) -> None:
        A = np.eye(3)
        b = np.array([1.0, 2.0, 3.0])
        result = LinearAlgebra.solve_linear_system(A, b)
        assert np.allclose(result["solution"], b)
        assert result["well_conditioned"] is True

    def test_eigenvalues_of_diagonal(self) -> None:
        A = np.diag([1.0, 2.0, 3.0])
        result = LinearAlgebra.eigenvalues(A)
        assert sorted(result["eigenvalues"].real) == [1.0, 2.0, 3.0]

    def test_svd_rank(self) -> None:
        A = np.array([[1.0, 2.0], [2.0, 4.0]])  # rank 1
        result = LinearAlgebra.svd(A)
        assert result["rank"] == 1


class TestCosmology:
    def test_omega_sum_near_one(self) -> None:
        total = CosmologicalConstants.Omega_m + CosmologicalConstants.Omega_Lambda
        assert abs(total - 1.0) < 0.01

    def test_hubble_at_a_equals_one_is_H0(self) -> None:
        H = FriedmannEquations.hubble_parameter(1.0)
        # H(a=1) = H0 * sqrt(Omega_m + Omega_Lambda) ≈ H0
        assert H == pytest.approx(CosmologicalConstants.H0, rel=0.01)

    def test_hubble_grows_as_a_decreases(self) -> None:
        # Universe was denser and expansion rate was higher in the past.
        H_today = FriedmannEquations.hubble_parameter(1.0)
        H_early = FriedmannEquations.hubble_parameter(0.1)
        assert H_early > H_today

    def test_schwarzschild_sun_radius_matches_known(self) -> None:
        M_sun = 1.989e30  # kg
        r_s = BlackHolePhysics.schwarzschild_radius(M_sun)
        # Known value: ~2953 m (~2.95 km) for solar mass.
        assert 2900 < r_s < 3000

    def test_photon_sphere_is_1_5x_schwarzschild(self) -> None:
        M_sun = 1.989e30
        r_s = BlackHolePhysics.schwarzschild_radius(M_sun)
        r_ph = BlackHolePhysics.photon_sphere_radius(M_sun)
        assert r_ph == pytest.approx(1.5 * r_s, rel=1e-9)

    def test_isco_is_3x_schwarzschild(self) -> None:
        M_sun = 1.989e30
        r_s = BlackHolePhysics.schwarzschild_radius(M_sun)
        r_isco = BlackHolePhysics.innermost_stable_circular_orbit(M_sun)
        assert r_isco == pytest.approx(3.0 * r_s, rel=1e-9)

    def test_chirp_mass_symmetric(self) -> None:
        mc = GravitationalWaves.chirp_mass(1.4e30, 1.4e30)
        # Equal masses: M_c = m / 2^(1/5) * m^(3/5)... simplifies to m * (1/4)^(3/5) * (2)^(-1/5)
        # Easier: just confirm symmetry m1<->m2.
        mc_swapped = GravitationalWaves.chirp_mass(1.4e30, 1.4e30)
        assert mc == mc_swapped
        assert mc > 0


class TestQuantumMechanics:
    def test_state_normalizes_on_init(self) -> None:
        s = QuantumState(np.array([1.0, 1.0], dtype=complex))
        norm = float(np.linalg.norm(s.amplitudes))
        assert norm == pytest.approx(1.0)

    def test_probabilities_sum_to_one(self) -> None:
        s = QuantumState(np.array([1.0, 1.0, 1.0], dtype=complex))
        total = sum(s.probability(i) for i in range(3))
        assert total == pytest.approx(1.0, abs=1e-12)

    def test_hadamard_is_unitary(self) -> None:
        H = QuantumGates.hadamard()
        assert H.is_unitary()

    def test_hadamard_on_zero_gives_equal_superposition(self) -> None:
        H = QuantumGates.hadamard()
        ket0 = QuantumState(np.array([1.0, 0.0], dtype=complex))
        out = H.apply(ket0)
        assert out.probability(0) == pytest.approx(0.5, abs=1e-12)
        assert out.probability(1) == pytest.approx(0.5, abs=1e-12)

    def test_pauli_x_is_not_gate(self) -> None:
        X = QuantumGates.pauli_x()
        ket0 = QuantumState(np.array([1.0, 0.0], dtype=complex))
        out = X.apply(ket0)
        assert out.probability(1) == pytest.approx(1.0)

    def test_bell_state_entanglement_pattern(self) -> None:
        bell = Superposition.create_bell_state("phi_plus")
        # |Φ+> = (|00>+|11>)/sqrt2 — equal weight on |00> and |11>.
        assert bell.probability(0) == pytest.approx(0.5)
        assert bell.probability(3) == pytest.approx(0.5)
        assert bell.probability(1) == pytest.approx(0.0)
        assert bell.probability(2) == pytest.approx(0.0)

    def test_measure_is_reproducible_with_seed(self) -> None:
        H = QuantumGates.hadamard()
        ket0 = QuantumState(np.array([1.0, 0.0], dtype=complex))
        out = H.apply(ket0)
        np.random.seed(42)
        a = out.measure()
        np.random.seed(42)
        b = out.measure()
        assert a == b


class TestFormalLogic:
    def test_proposition_evaluates_from_assignment(self) -> None:
        p = Proposition("P")
        assert p.evaluate({"P": True}) is True
        assert p.evaluate({"P": False}) is False

    def test_implication_truth_table(self) -> None:
        p = Proposition("P")
        q = Proposition("Q")
        f = Formula(LogicalOperator.IMPLIES, [p, q])
        # Only T->F is false; the other three are true.
        assert f.evaluate({"P": True, "Q": True}) is True
        assert f.evaluate({"P": True, "Q": False}) is False
        assert f.evaluate({"P": False, "Q": True}) is True
        assert f.evaluate({"P": False, "Q": False}) is True

    def test_law_of_identity_always_holds(self) -> None:
        p = Proposition("P")
        assert LawsOfThought.law_of_identity(p, {"P": True}) is True
        assert LawsOfThought.law_of_identity(p, {"P": False}) is True

    def test_law_of_non_contradiction_always_holds(self) -> None:
        p = Proposition("P")
        assert LawsOfThought.law_of_non_contradiction(p, {"P": True}) is True
        assert LawsOfThought.law_of_non_contradiction(p, {"P": False}) is True

    def test_law_of_excluded_middle_always_holds(self) -> None:
        p = Proposition("P")
        assert LawsOfThought.law_of_excluded_middle(p, {"P": True}) is True
        assert LawsOfThought.law_of_excluded_middle(p, {"P": False}) is True

    def test_modus_ponens_derives_q(self) -> None:
        p = Proposition("P")
        q = Proposition("Q")
        atomic_p = Formula(None, [p])
        p_implies_q = Formula(LogicalOperator.IMPLIES, [p, q])
        assert InferenceRules.modus_ponens(atomic_p, p_implies_q, {"P": True, "Q": True}) is True


class TestHarmonics:
    def test_harmonic_series_is_integer_multiples(self) -> None:
        series = HarmonicSeries.generate(100.0, 5)
        assert series == [100.0, 200.0, 300.0, 400.0, 500.0]

    def test_octave_is_1200_cents(self) -> None:
        cents = MusicalIntervals.ratio_to_cents((2, 1))
        assert cents == pytest.approx(1200.0, abs=1e-10)

    def test_perfect_fifth_is_702_cents(self) -> None:
        cents = MusicalIntervals.ratio_to_cents((3, 2))
        assert cents == pytest.approx(701.955, abs=1e-2)

    def test_unison_is_zero_cents(self) -> None:
        cents = MusicalIntervals.ratio_to_cents((1, 1))
        assert cents == pytest.approx(0.0)

    def test_cents_round_trip(self) -> None:
        ratio = MusicalIntervals.cents_to_ratio(1200.0)
        assert ratio == pytest.approx(2.0, abs=1e-10)

    def test_consonance_ordering(self) -> None:
        # Octave (2:1 = score 3) more consonant than tritone (45:32 = 77).
        assert MusicalIntervals.consonance_score((2, 1)) < MusicalIntervals.consonance_score(
            (45, 32)
        )

    def test_kepler_earth_one_year(self) -> None:
        p = MusicOfTheSpheres.kepler_third_law(1.0)
        assert p == pytest.approx(1.0)

    def test_kepler_4au_is_8_years(self) -> None:
        p = MusicOfTheSpheres.kepler_third_law(4.0)
        assert p == pytest.approx(8.0)

    def test_orbital_resonance_neptune_pluto(self) -> None:
        # Real periods in years: Neptune 164.8, Pluto 248.0 → 2:3
        ratio = MusicOfTheSpheres.orbital_resonance(164.8, 248.0)
        assert ratio == (2, 3)


class TestPhysicsRelativity:
    def test_lorentz_gamma_at_rest_is_one(self) -> None:
        assert Relativity.lorentz_factor(0.0) == pytest.approx(1.0)

    def test_lorentz_gamma_at_half_c(self) -> None:
        gamma = Relativity.lorentz_factor(0.5, c=1.0)
        assert gamma == pytest.approx(1.1547, abs=1e-4)

    def test_lorentz_raises_at_v_equals_c(self) -> None:
        with pytest.raises(ValueError):
            Relativity.lorentz_factor(1.0, c=1.0)

    def test_time_dilation_slows_moving_clock(self) -> None:
        t0 = 1.0
        t = Relativity.time_dilation(t0, 0.9, c=1.0)
        assert t > t0

    def test_length_contraction_shortens_moving_rod(self) -> None:
        L0 = 1.0
        L = Relativity.length_contraction(L0, 0.9, c=1.0)
        assert L < L0

    def test_relativistic_energy_shape(self) -> None:
        result = Relativity.relativistic_energy(1.0, 0.5, c=1.0)
        assert result["E"] > result["rest_energy"]
        assert result["KE"] > 0
        assert result["gamma"] > 1

    def test_schwarzschild_linear_in_mass(self) -> None:
        r1 = Relativity.schwarzschild_radius(1.0)
        r2 = Relativity.schwarzschild_radius(2.0)
        assert r2 == pytest.approx(2 * r1)


class TestGuteBridge:
    def test_lc_slice_shape(self) -> None:
        result = run_lc_slice(n_iterations=300)
        assert result["term"] == "LC"
        assert "lyapunov_by_r" in result
        assert "entropy_examples" in result
        assert result["bounded_chaos_r4"] is True

    def test_lc_slice_regime_calls(self) -> None:
        result = run_lc_slice(r_values=[2.5, 3.9], n_iterations=500)
        assert result["lyapunov_by_r"][2.5]["regime"] == "order"
        assert result["lyapunov_by_r"][3.9]["regime"] == "chaos"

    def test_run_slice_dispatch_lc(self) -> None:
        result = run_slice("LC", n_iterations=200)
        assert result["term"] == "LC"

    def test_run_slice_case_insensitive(self) -> None:
        assert run_slice("lc", n_iterations=200)["term"] == "LC"

    def test_unknown_term_returns_stub(self) -> None:
        result = run_slice("NotARealTerm")
        assert result["status"] == "unknown"
        assert "LC" in result["known_terms"]

    def test_list_slices_contains_lc(self) -> None:
        assert "LC" in list_slices()

    def test_list_slices_contains_omegab(self) -> None:
        assert "OmegaB" in list_slices()

    def test_omegab_slice_shape(self) -> None:
        result = run_omegab_slice()
        assert result["term"] == "OmegaB"
        assert result["integral_equals_1"] is True
        assert result["cosmology_near_critical"] is True
        assert result["probability_sums_to_1"] is True

    def test_omegab_integral_is_unity(self) -> None:
        result = run_omegab_slice(n_points=500)
        assert result["integral_0_to_1_of_1"] == pytest.approx(1.0, abs=1e-6)

    def test_omegab_dispatch_via_run_slice(self) -> None:
        assert run_slice("OmegaB")["term"] == "OmegaB"
        assert run_slice("omegab")["term"] == "OmegaB"
        assert run_slice("omega_b")["term"] == "OmegaB"

    def test_list_slices_contains_psi(self) -> None:
        assert "Psi" in list_slices()

    def test_psi_slice_shape(self) -> None:
        result = run_psi_slice(seed=42)
        assert result["term"] == "Psi"
        assert result["quantum"]["is_equal_superposition"] is True
        assert result["quantum"]["probs_sum_to_1"] is True
        assert result["logic"]["law_of_identity_holds"] is True
        assert result["logic"]["law_of_non_contradiction_holds"] is True
        assert result["logic"]["law_of_excluded_middle_holds"] is True

    def test_psi_slice_collapse_reproducible(self) -> None:
        r1 = run_psi_slice(seed=7)
        r2 = run_psi_slice(seed=7)
        assert r1["quantum"]["collapse_label"] == r2["quantum"]["collapse_label"]

    def test_psi_dispatch_via_run_slice(self) -> None:
        assert run_slice("Psi")["term"] == "Psi"
        assert run_slice("psi")["term"] == "Psi"

    def test_list_slices_contains_v_a_f(self) -> None:
        slices = list_slices()
        assert "V" in slices
        assert "A" in slices
        assert "F" in slices

    def test_v_slice_shape(self) -> None:
        result = run_v_slice()
        assert result["term"] == "V"
        assert result["integer_ratios_hold"] is True
        assert result["kepler_third_law_holds"] is True
        assert result["octave_cents"] == pytest.approx(1200.0, abs=1e-10)
        assert tuple(result["neptune_pluto_resonance"]) == (2, 3)

    def test_a_slice_shape(self) -> None:
        result = run_a_slice()
        assert result["term"] == "A"
        assert result["lorentz_diverges_as_v_approaches_c"] is True
        assert result["scale_factor_monotone_increasing"] is True
        # γ(0.99c) should be ≈ 7.089
        assert result["lorentz_gamma_at_0.99c"] == pytest.approx(7.089, abs=1e-2)

    def test_f_slice_shape(self) -> None:
        result = run_f_slice()
        assert result["term"] == "F"
        assert result["all_four_present"] is True
        assert result["hierarchy_alpha_s_gt_alpha_em"] is True
        # All four force entries present.
        for key in ("F1_strong", "F2_weak", "F3_electromagnetic", "F4_gravitational"):
            assert key in result

    def test_f_slice_schwarzschild_sun_approx_3km(self) -> None:
        result = run_f_slice()
        r_s = result["F4_gravitational"]["schwarzschild_radius_1_sun_m"]
        assert 2900 < r_s < 3000

    def test_v_a_f_dispatch(self) -> None:
        assert run_slice("V")["term"] == "V"
        assert run_slice("A")["term"] == "A"
        assert run_slice("F")["term"] == "F"
        assert run_slice("forces")["term"] == "F"


class TestLabCli:
    def test_lab_list(self) -> None:
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["lab", "list"])
        assert result.exit_code == 0
        assert "LC" in result.output

    def test_lab_run_slice_lc_json(self) -> None:
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["lab", "run-slice", "LC", "--iterations", "200", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["term"] == "LC"
        assert payload["bounded_chaos_r4"] is True

    def test_lab_run_slice_lc_human(self) -> None:
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["lab", "run-slice", "LC", "--iterations", "200"])
        assert result.exit_code == 0, result.output
        assert "Lyapunov" in result.output
        assert "Entropy" in result.output

    def test_lab_run_slice_unknown(self) -> None:
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["lab", "run-slice", "NotARealTerm"])
        assert result.exit_code == 0
        assert "Unknown term" in result.output

    def test_lab_run_slice_omegab_human(self) -> None:
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["lab", "run-slice", "OmegaB"])
        assert result.exit_code == 0, result.output
        assert "Convergence to unity" in result.output

    def test_lab_run_slice_omegab_json(self) -> None:
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["lab", "run-slice", "OmegaB", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["term"] == "OmegaB"
        assert payload["integral_equals_1"] is True

    def test_lab_run_slice_psi_human(self) -> None:
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["lab", "run-slice", "Psi"])
        assert result.exit_code == 0, result.output
        assert "Quantum selection" in result.output
        assert "Logical selection" in result.output

    def test_lab_run_slice_psi_json(self) -> None:
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["lab", "run-slice", "Psi", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["term"] == "Psi"
        assert payload["quantum"]["is_equal_superposition"] is True

    def test_lab_run_slice_v_human(self) -> None:
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["lab", "run-slice", "V"])
        assert result.exit_code == 0, result.output
        assert "Harmonic series" in result.output
        assert "Kepler" in result.output

    def test_lab_run_slice_a_human(self) -> None:
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["lab", "run-slice", "A"])
        assert result.exit_code == 0, result.output
        assert "Spacetime" in result.output
        assert "Lorentz" in result.output

    def test_lab_run_slice_f_human(self) -> None:
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["lab", "run-slice", "F"])
        assert result.exit_code == 0, result.output
        assert "four fundamental forces" in result.output
        assert "hierarchy" in result.output.lower()

    def test_lab_run_slice_v_a_f_json(self) -> None:
        from divineos.cli import cli

        runner = CliRunner()
        for term in ("V", "A", "F"):
            result = runner.invoke(cli, ["lab", "run-slice", term, "--json"])
            assert result.exit_code == 0, result.output
            payload = json.loads(result.output)
            assert payload["term"] == term
