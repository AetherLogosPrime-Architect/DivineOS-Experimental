"""Cosmology and astrophysics — Friedmann universe, black holes, gravitational waves.

GUTE relevance: ΩB (Omega_m + Omega_Lambda ≈ 1, critical density balance),
A (spacetime via c, H0, scale factor), F (gravitational coupling via G,
Schwarzschild radius).

Ported from divine-os-old. Kept: CosmologicalConstants (Planck 2018 values),
FriedmannEquations (Hubble parameter, scale-factor evolution, critical
density), BlackHolePhysics (Schwarzschild, Hawking, ISCO), and
GravitationalWaves (chirp mass, merger frequency, strain). Dropped: DarkMatter
NFW profiles (no slice caller yet) and the StellarEvolution stub.
"""

from __future__ import annotations

import numpy as np


class CosmologicalConstants:
    """Fundamental constants (SI) + Planck 2018 cosmological parameters."""

    c = 299792458  # Speed of light (m/s)
    G = 6.67430e-11  # Gravitational constant (m^3/kg/s^2)
    h = 6.62607015e-34  # Planck constant (J·s)
    k_B = 1.380649e-23  # Boltzmann constant (J/K)

    H0 = 67.4  # Hubble constant (km/s/Mpc), Planck 2018
    Omega_m = 0.315  # Matter density parameter
    Omega_Lambda = 0.685  # Dark-energy density parameter
    Omega_b = 0.049  # Baryon density parameter
    Omega_dm = 0.266  # Dark-matter density parameter

    t_0 = 13.8e9  # Age of universe (years)
    T_CMB = 2.725  # CMB temperature (K)


class FriedmannEquations:
    """Friedmann equations for the expanding universe."""

    @staticmethod
    def hubble_parameter(
        a: float,
        H0: float = CosmologicalConstants.H0,
        Omega_m: float = CosmologicalConstants.Omega_m,
        Omega_Lambda: float = CosmologicalConstants.Omega_Lambda,
    ) -> float:
        """H(a) = H0 * sqrt(Omega_m/a^3 + Omega_Lambda). km/s/Mpc."""
        return float(H0 * np.sqrt(Omega_m / a**3 + Omega_Lambda))

    @staticmethod
    def scale_factor_evolution(
        t: np.ndarray,
        H0: float = CosmologicalConstants.H0,
        Omega_m: float = CosmologicalConstants.Omega_m,
        Omega_Lambda: float = CosmologicalConstants.Omega_Lambda,
    ) -> np.ndarray:
        """Approximate scale factor a(t) — matter-dominated → Lambda-dominated."""
        t_eq = (Omega_m / Omega_Lambda) ** (1 / 3)
        a = np.zeros_like(t)
        for i, ti in enumerate(t):
            if ti < t_eq:
                a[i] = (ti / t_eq) ** (2 / 3) * t_eq
            else:
                a[i] = t_eq * np.exp(np.sqrt(Omega_Lambda) * (ti - t_eq))
        return a

    @staticmethod
    def critical_density(H: float) -> float:
        """Critical density rho_crit = 3H^2/(8 pi G). kg/m^3."""
        H_si = H * 1000 / 3.086e22  # km/s/Mpc → 1/s
        return float(3 * H_si**2 / (8 * np.pi * CosmologicalConstants.G))


class BlackHolePhysics:
    """Black-hole scales — Schwarzschild, Hawking, ISCO."""

    @staticmethod
    def schwarzschild_radius(
        M: float,
        G: float = CosmologicalConstants.G,
        c: float = CosmologicalConstants.c,
    ) -> float:
        """r_s = 2GM/c^2 (event horizon). meters."""
        return float(2 * G * M / c**2)

    @staticmethod
    def hawking_temperature(M: float) -> float:
        """T = hbar c^3 / (8 pi G M k_B). Kelvin."""
        hbar = CosmologicalConstants.h / (2 * np.pi)
        c = CosmologicalConstants.c
        G = CosmologicalConstants.G
        k_B = CosmologicalConstants.k_B
        return float(hbar * c**3 / (8 * np.pi * G * M * k_B))

    @staticmethod
    def hawking_luminosity(M: float) -> float:
        """L = hbar c^6 / (15360 pi G^2 M^2). Watts."""
        hbar = CosmologicalConstants.h / (2 * np.pi)
        c = CosmologicalConstants.c
        G = CosmologicalConstants.G
        return float(hbar * c**6 / (15360 * np.pi * G**2 * M**2))

    @staticmethod
    def evaporation_time(M: float) -> float:
        """t = 5120 pi G^2 M^3 / (hbar c^4). seconds."""
        hbar = CosmologicalConstants.h / (2 * np.pi)
        c = CosmologicalConstants.c
        G = CosmologicalConstants.G
        return float(5120 * np.pi * G**2 * M**3 / (hbar * c**4))

    @staticmethod
    def photon_sphere_radius(M: float) -> float:
        """r_ph = 3GM/c^2 (unstable circular light orbit). meters."""
        G = CosmologicalConstants.G
        c = CosmologicalConstants.c
        return float(3 * G * M / c**2)

    @staticmethod
    def innermost_stable_circular_orbit(M: float) -> float:
        """ISCO for Schwarzschild: r = 6GM/c^2. meters."""
        G = CosmologicalConstants.G
        c = CosmologicalConstants.c
        return float(6 * G * M / c**2)


class GravitationalWaves:
    """Inspiral-merger GW quantities."""

    @staticmethod
    def chirp_mass(m1: float, m2: float) -> float:
        """M_c = (m1 m2)^(3/5) / (m1 + m2)^(1/5)."""
        return float((m1 * m2) ** (3 / 5) / (m1 + m2) ** (1 / 5))

    @staticmethod
    def merger_frequency(M_total: float) -> float:
        """f_merge ≈ c^3 / (6 sqrt(6) pi G M_total). Hz."""
        G = CosmologicalConstants.G
        c = CosmologicalConstants.c
        return float(c**3 / (6 * np.sqrt(6) * np.pi * G * M_total))

    @staticmethod
    def strain_amplitude(M_chirp: float, D_L: float, f: float) -> float:
        """h ~ (G M_c / c^2)^(5/3) (pi f / c)^(2/3) / D_L."""
        G = CosmologicalConstants.G
        c = CosmologicalConstants.c
        return float((G * M_chirp / c**2) ** (5 / 3) * (np.pi * f / c) ** (2 / 3) / D_L)
