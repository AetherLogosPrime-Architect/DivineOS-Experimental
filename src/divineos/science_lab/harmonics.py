"""Harmonics — integer ratios in sound and orbits.

GUTE relevance: V (Vibration) — resonance as structure. The claim is that
integer ratios are load-bearing in physical systems whose stability
depends on them (musical consonance, orbital resonances).

Ported from divine-os-old. Kept: HarmonicSeries.generate (f_n = n f_0),
MusicalIntervals.just_intonation_ratios and ratio_to_cents (logarithmic
interval measure), MusicOfTheSpheres.kepler_third_law and orbital_resonance
(real physics: T^2 ∝ a^3; commensurate orbits from rational-approximation
of period ratio).

Dropped: synthesize_tone (audio synthesis isn't a slice), arbitrary
planetary-frequency scalings, Titius-Bode (empirical but not physical law),
TuningSystems and HarmonicOscillator (no slice caller yet).
"""

from __future__ import annotations

from fractions import Fraction
from typing import Tuple

import numpy as np


class HarmonicSeries:
    """Fundamental + overtones. f_n = n * f_0, n = 1, 2, 3, ..."""

    @staticmethod
    def generate(fundamental: float, n_harmonics: int = 16) -> list[float]:
        """Integer multiples of the fundamental: [f, 2f, 3f, ...]."""
        return [n * fundamental for n in range(1, n_harmonics + 1)]


class MusicalIntervals:
    """Just-intonation ratios and cents conversion."""

    @staticmethod
    def just_intonation_ratios() -> dict[str, Tuple[int, int]]:
        """Simple-integer ratios for the diatonic intervals."""
        return {
            "unison": (1, 1),
            "minor_second": (16, 15),
            "major_second": (9, 8),
            "minor_third": (6, 5),
            "major_third": (5, 4),
            "perfect_fourth": (4, 3),
            "tritone": (45, 32),
            "perfect_fifth": (3, 2),
            "minor_sixth": (8, 5),
            "major_sixth": (5, 3),
            "minor_seventh": (16, 9),
            "major_seventh": (15, 8),
            "octave": (2, 1),
        }

    @staticmethod
    def ratio_to_cents(ratio: Tuple[int, int]) -> float:
        """cents = 1200 * log2(num/den). Octave = 1200; fifth ≈ 702."""
        num, den = ratio
        return float(1200 * np.log2(num / den))

    @staticmethod
    def cents_to_ratio(cents: float) -> float:
        """Inverse: ratio = 2^(cents/1200)."""
        return float(2 ** (cents / 1200))

    @staticmethod
    def consonance_score(ratio: Tuple[int, int]) -> int:
        """Sum of numerator + denominator — lower = more consonant."""
        return ratio[0] + ratio[1]


class MusicOfTheSpheres:
    """Orbital physics — Kepler's third law and orbital resonance."""

    @staticmethod
    def kepler_third_law(semi_major_axis_au: float, mass_star_solar: float = 1.0) -> float:
        """P (years) = sqrt(a^3 / M) in solar-system units.

        Real physics, not metaphor: Earth at a=1 AU around a 1-solar-mass
        star has period 1 year. This is the hard link between orbital
        distance and time that makes planetary harmonics computable.
        """
        return float(np.sqrt(semi_major_axis_au**3 / mass_star_solar))

    @staticmethod
    def orbital_resonance(
        period1: float, period2: float, max_denominator: int = 10
    ) -> Tuple[int, int]:
        """Approximate period1/period2 as a simple integer ratio.

        Returns (p, q) such that period1/period2 ≈ p/q with q ≤
        max_denominator. Real resonances in nature (Neptune-Pluto 3:2,
        Jupiter moons Io-Europa-Ganymede 1:2:4) show up as small
        integers.
        """
        frac = Fraction(period1 / period2).limit_denominator(max_denominator)
        return (frac.numerator, frac.denominator)
