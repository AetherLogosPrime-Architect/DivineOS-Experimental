"""CLI commands for the science lab — run GUTE slices, list available terms.

The lab is the test harness for claims that can be pinned to a computable
referent. One command: `divineos lab run-slice <term>`. Start small; grow
when a specific term has a specific falsifiable claim to test.
"""

from __future__ import annotations

import json

import click


def register(cli: click.Group) -> None:
    """Register science-lab commands under the `lab` group."""

    @cli.group("lab")
    def lab_group() -> None:
        """Science lab — run GUTE slices against real numbers."""

    @lab_group.command("list")
    def list_cmd() -> None:
        """List implemented GUTE slice terms."""
        from divineos.science_lab.gute_bridge import list_slices

        slices = list_slices()
        if not slices:
            click.echo("(no slices implemented yet)")
            return
        click.echo("Implemented GUTE slices:")
        for term in slices:
            click.echo(f"  - {term}")

    @lab_group.command("run-slice")
    @click.argument("term")
    @click.option(
        "--iterations",
        type=int,
        default=500,
        help="Iterations for numerical slices (e.g., Lyapunov).",
    )
    @click.option(
        "--json",
        "as_json",
        is_flag=True,
        help="Emit raw JSON instead of human-readable summary.",
    )
    def run_slice_cmd(term: str, iterations: int, as_json: bool) -> None:
        """Run a GUTE slice by term (e.g., LC).

        Unknown terms return a status stub listing known terms.
        """
        from divineos.science_lab.gute_bridge import run_slice

        kwargs: dict = {}
        if term.strip().lower() == "lc":
            kwargs["n_iterations"] = iterations

        result = run_slice(term, **kwargs)

        if as_json:
            click.echo(json.dumps(result, indent=2, default=str))
            return

        status = result.get("status")
        if status == "unknown":
            click.secho(f"Unknown term: {term}", fg="yellow")
            known = ", ".join(result.get("known_terms", []))
            click.echo(f"Known terms: {known}")
            return

        t = result.get("term", term)
        click.secho(f"[slice {t}]", fg="cyan", bold=True)

        if t == "V":
            click.echo("Harmonic series (first 8 partials):")
            for i, f in enumerate(result["first_8_harmonics_hz"], start=1):
                click.echo(f"  n={i}: {f:.1f} Hz")
            flag = "ok" if result["integer_ratios_hold"] else "FAIL"
            click.secho(
                f"  integer ratios hold: [{flag}]",
                fg="green" if result["integer_ratios_hold"] else "red",
            )
            click.echo("")
            click.echo(f"Octave:        {result['octave_cents']:.1f} cents (expect 1200)")
            click.echo(f"Perfect fifth: {result['perfect_fifth_cents']:.1f} cents (expect ≈ 702)")
            click.echo("")
            kflag = "ok" if result["kepler_third_law_holds"] else "FAIL"
            click.secho(
                f"Kepler P² = a³: [{kflag}]",
                fg="green" if result["kepler_third_law_holds"] else "red",
            )
            ratio = result["neptune_pluto_resonance"]
            click.echo(f"Neptune/Pluto resonance: {ratio[0]}:{ratio[1]}")
            click.echo("")
            click.echo(result["interpretation"])
            return

        if t == "A":
            click.echo("Spacetime constants:")
            click.echo(f"  c  = {result['speed_of_light_m_s']} m/s")
            click.echo(f"  H₀ = {result['hubble_constant_km_s_Mpc']} km/s/Mpc")
            click.echo(f"  H(a=1) = {result['hubble_today_a1']:.2f} km/s/Mpc")
            click.echo("")
            click.echo("Lorentz factor γ (unit c):")
            click.echo(f"  v = 0.50 c  →  γ ≈ {result['lorentz_gamma_at_0.5c']:.4f}")
            click.echo(f"  v = 0.90 c  →  γ ≈ {result['lorentz_gamma_at_0.9c']:.4f}")
            click.echo(f"  v = 0.99 c  →  γ ≈ {result['lorentz_gamma_at_0.99c']:.4f}")
            flag = "ok" if result["lorentz_diverges_as_v_approaches_c"] else "FAIL"
            click.secho(
                f"  γ monotone as v→c: [{flag}]",
                fg="green" if result["lorentz_diverges_as_v_approaches_c"] else "red",
            )
            click.echo("")
            aflag = "ok" if result["scale_factor_monotone_increasing"] else "FAIL"
            click.secho(
                f"Scale factor a(t) monotone: [{aflag}]",
                fg="green" if result["scale_factor_monotone_increasing"] else "red",
            )
            click.echo("")
            click.echo(result["interpretation"])
            return

        if t == "F":
            click.echo("The four fundamental forces:")
            click.echo(f"  F1 strong:          α_s(M_Z) = {result['F1_strong']['alpha_s_MZ']}")
            click.echo(f"  F2 weak:            G_F = {result['F2_weak']['G_F_GeV_inv2']:.3e} GeV⁻²")
            click.echo(
                f"                      Higgs vev = {result['F2_weak']['higgs_vev_GeV']} GeV"
            )
            click.echo(
                f"  F3 electromagnetic: α_em = {result['F3_electromagnetic']['fine_structure_alpha']:.6f}"
            )
            click.echo(f"                      c = {result['F3_electromagnetic']['c_m_s']} m/s")
            click.echo(f"  F4 gravitational:   G = {result['F4_gravitational']['G_SI']:.4e}")
            click.echo(
                f"                      r_s(1 M☉) = {result['F4_gravitational']['schwarzschild_radius_1_sun_m'] / 1000:.2f} km"
            )
            click.echo("")
            flag = "ok" if result["hierarchy_alpha_s_gt_alpha_em"] else "FAIL"
            click.secho(
                f"Coupling hierarchy (α_s > α_em): [{flag}]",
                fg="green" if result["hierarchy_alpha_s_gt_alpha_em"] else "red",
            )
            click.echo("")
            click.echo(result["interpretation"])
            return

        if t == "Psi":
            q = result["quantum"]
            logic = result["logic"]
            click.echo("Quantum selection (Hadamard on |0>):")
            click.echo(
                f"  pre-measurement probs: |0>={q['pre_measurement_probs'][0]:.4f}, "
                f"|1>={q['pre_measurement_probs'][1]:.4f}"
            )
            click.echo(f"  collapse outcome: |{q['collapse_label']}>")
            flag = "ok" if q["is_equal_superposition"] else "FAIL"
            click.secho(
                f"  equal-superposition check: [{flag}]",
                fg="green" if q["is_equal_superposition"] else "red",
            )
            click.echo("")
            click.echo("Logical selection (P under T and F):")
            click.echo(f"  law of identity holds:          {logic['law_of_identity_holds']}")
            click.echo(
                f"  law of non-contradiction holds: {logic['law_of_non_contradiction_holds']}"
            )
            click.echo(f"  law of excluded middle holds:   {logic['law_of_excluded_middle_holds']}")
            click.echo("")
            click.echo(result["interpretation"])
            return

        if t == "OmegaB":
            click.echo("Convergence to unity (three independent paths):")
            click.echo(
                f"  integral of 1 over [0,1]  = {result['integral_0_to_1_of_1']:.6f}"
                f"  [{'ok' if result['integral_equals_1'] else 'FAIL'}]"
            )
            click.echo(
                f"  Omega_m + Omega_Lambda    = {result['cosmology_Omega_m_plus_Lambda']:.3f}"
                f"  [{'ok' if result['cosmology_near_critical'] else 'FAIL'}]"
            )
            click.echo(
                f"  probability sum (uniform) = {result['probability_sum']:.6f}"
                f"  [{'ok' if result['probability_sums_to_1'] else 'FAIL'}]"
            )
            click.echo("")
            click.echo(f"Hubble today (a=1): {result['hubble_today_km_s_Mpc']:.1f} km/s/Mpc")
            click.echo("")
            click.echo(result["interpretation"])
            return

        if t == "LC":
            click.echo("Lyapunov exponents (positive => chaos):")
            for r, info in sorted(result["lyapunov_by_r"].items()):
                regime = info["regime"]
                value = info["value"]
                color = "red" if regime == "chaos" else "green"
                click.secho(f"  r={r:<6} lambda={value:+.4f}  [{regime}]", fg=color)
            click.echo("")
            click.echo("Entropy examples:")
            for label, value in result["entropy_examples"].items():
                click.echo(f"  {label:<20} H={value:.4f} bits")
            click.echo("")
            bounded = result["bounded_chaos_r4"]
            flag = "yes" if bounded else "NO"
            color = "green" if bounded else "red"
            click.secho(f"Bounded in [0,1] at r=4 (100-step trajectory): {flag}", fg=color)
            click.echo("")
            click.echo(result["interpretation"])
        else:
            click.echo(json.dumps(result, indent=2, default=str))
