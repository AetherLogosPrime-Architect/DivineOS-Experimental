"""Physics — classical mechanics and relativity.

GUTE relevance: A (Aetheric / spacetime — c as the constant that defines
the field; Lorentz factor as the structure of spacetime at speed; time
dilation and length contraction as what that structure produces).

Ported from divine-os-old. Kept: Relativity (lorentz_factor, time_dilation,
length_contraction, relativistic_energy, schwarzschild_radius). Dropped:
ClassicalMechanics (projectile, pendulum, harmonic oscillator) and
QuantumMechanics (particle-in-box, hydrogen wavefunction) — real math but
no current slice caller. Port when a claim needs them.
"""

from __future__ import annotations

import numpy as np


class Relativity:
    """Special-relativity kinematics + Schwarzschild radius."""

    @staticmethod
    def lorentz_factor(v: float, c: float = 1.0) -> float:
        """γ = 1 / sqrt(1 - (v/c)²). Raises if |v| ≥ c."""
        beta = v / c
        if abs(beta) >= 1:
            raise ValueError("Velocity must be less than speed of light")
        return float(1 / np.sqrt(1 - beta**2))

    @staticmethod
    def time_dilation(t0: float, v: float, c: float = 1.0) -> float:
        """t = γ t₀. Moving clocks run slow."""
        return Relativity.lorentz_factor(v, c) * t0

    @staticmethod
    def length_contraction(L0: float, v: float, c: float = 1.0) -> float:
        """L = L₀ / γ. Moving objects shorten along motion."""
        return L0 / Relativity.lorentz_factor(v, c)

    @staticmethod
    def relativistic_energy(m: float, v: float, c: float = 1.0) -> dict[str, float]:
        """Returns E, p, KE, gamma, rest_energy."""
        gamma = Relativity.lorentz_factor(v, c)
        E = gamma * m * c**2
        p = gamma * m * v
        KE = E - m * c**2
        return {
            "E": float(E),
            "p": float(p),
            "KE": float(KE),
            "gamma": float(gamma),
            "rest_energy": float(m * c**2),
        }

    @staticmethod
    def schwarzschild_radius(M: float, G: float = 1.0, c: float = 1.0) -> float:
        """r_s = 2GM/c² in the given unit system."""
        return float(2 * G * M / c**2)
