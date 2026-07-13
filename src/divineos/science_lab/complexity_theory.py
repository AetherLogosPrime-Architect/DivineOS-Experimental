"""Complexity theory — chaos, fractals, emergence.

GUTE relevance: LC (Lovecraftian Constant) — chaos, Lyapunov, bounded disorder.

Ported from divine-os-old. Kept: the real math (logistic map, Lyapunov,
Lorenz, Mandelbrot, box-counting, power-law MLE). Dropped: the example()
demo functions — tests exercise the same paths without print noise.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np


class ChaoticSystems:
    """Chaotic dynamical systems."""

    @staticmethod
    def logistic_map(x: float, r: float) -> float:
        """Logistic map: x_{n+1} = r * x_n * (1 - x_n). Chaotic for r > ~3.57."""
        return r * x * (1 - x)

    @staticmethod
    def logistic_map_trajectory(x0: float, r: float, n_steps: int) -> np.ndarray:
        """Trajectory of logistic map from x0 with parameter r over n_steps."""
        trajectory = np.zeros(n_steps)
        trajectory[0] = x0
        for i in range(1, n_steps):
            trajectory[i] = ChaoticSystems.logistic_map(trajectory[i - 1], r)
        return trajectory

    @staticmethod
    def lyapunov_exponent_logistic(r: float, n_iterations: int = 1000) -> float:
        """Lyapunov exponent for logistic map at parameter r.

        Positive → chaos. Negative → order. The boundary between them is
        where LC becomes load-bearing: bounded-but-sensitive.
        """
        x = 0.5
        # Let transient die out.
        for _ in range(100):
            x = ChaoticSystems.logistic_map(x, r)
        lyap_sum = 0.0
        for _ in range(n_iterations):
            x = ChaoticSystems.logistic_map(x, r)
            derivative = abs(r * (1 - 2 * x))
            if derivative > 0:
                lyap_sum += np.log(derivative)
        return lyap_sum / n_iterations

    @staticmethod
    def lorenz_system(
        state: np.ndarray,
        sigma: float = 10.0,
        rho: float = 28.0,
        beta: float = 8 / 3,
    ) -> np.ndarray:
        """Lorenz strange attractor: dx/dt = sigma(y-x); dy/dt = x(rho-z)-y; dz/dt = xy - beta*z."""
        x, y, z = state
        dx = sigma * (y - x)
        dy = x * (rho - z) - y
        dz = x * y - beta * z
        return np.array([dx, dy, dz])

    @staticmethod
    def lorenz_trajectory(
        initial_state: np.ndarray, dt: float = 0.01, n_steps: int = 10000
    ) -> np.ndarray:
        """Lorenz trajectory via forward Euler. Returns (n_steps, 3)."""
        trajectory = np.zeros((n_steps, 3))
        trajectory[0] = initial_state
        for i in range(1, n_steps):
            derivatives = ChaoticSystems.lorenz_system(trajectory[i - 1])
            trajectory[i] = trajectory[i - 1] + dt * derivatives
        return trajectory


class Fractals:
    """Fractal geometry and self-similarity."""

    @staticmethod
    def mandelbrot_iteration(c: complex, max_iter: int = 100) -> int:
        """Iterations before z_{n+1} = z_n^2 + c diverges (|z|>2), capped at max_iter."""
        z = 0j
        for n in range(max_iter):
            if abs(z) > 2:
                return n
            z = z * z + c
        return max_iter

    @staticmethod
    def julia_set_iteration(z: complex, c: complex, max_iter: int = 100) -> int:
        """Julia set iteration count for starting point z with parameter c."""
        for n in range(max_iter):
            if abs(z) > 2:
                return n
            z = z * z + c
        return max_iter

    @staticmethod
    def koch_snowflake_points(order: int = 3) -> List[Tuple[float, float]]:
        """Koch snowflake points at given recursion depth."""

        def koch_curve(p1, p2, order):
            if order == 0:
                return [p1, p2]
            dx = (p2[0] - p1[0]) / 3
            dy = (p2[1] - p1[1]) / 3
            a = p1
            b = (p1[0] + dx, p1[1] + dy)
            d = (p2[0] - dx, p2[1] - dy)
            e = p2
            angle = np.pi / 3
            c = (
                b[0] + dx * np.cos(angle) - dy * np.sin(angle),
                b[1] + dx * np.sin(angle) + dy * np.cos(angle),
            )
            points = []
            points.extend(koch_curve(a, b, order - 1)[:-1])
            points.extend(koch_curve(b, c, order - 1)[:-1])
            points.extend(koch_curve(c, d, order - 1)[:-1])
            points.extend(koch_curve(d, e, order - 1))
            return points

        p1 = (0.0, 0.0)
        p2 = (1.0, 0.0)
        p3 = (0.5, float(np.sqrt(3) / 2))
        points: List[Tuple[float, float]] = []
        points.extend(koch_curve(p1, p2, order)[:-1])
        points.extend(koch_curve(p2, p3, order)[:-1])
        points.extend(koch_curve(p3, p1, order))
        return points

    @staticmethod
    def fractal_dimension_box_counting(points: np.ndarray, box_sizes: np.ndarray) -> float:
        """Box-counting estimate of fractal dimension. points: (N,2)."""
        counts = []
        for box_size in box_sizes:
            x_bins = np.arange(points[:, 0].min(), points[:, 0].max(), box_size)
            y_bins = np.arange(points[:, 1].min(), points[:, 1].max(), box_size)
            boxes: set[Tuple[int, int]] = set()
            for point in points:
                x_idx = int((point[0] - x_bins[0]) / box_size)
                y_idx = int((point[1] - y_bins[0]) / box_size)
                boxes.add((x_idx, y_idx))
            counts.append(len(boxes))
        log_sizes = np.log(1 / box_sizes)
        log_counts = np.log(counts)
        return float(np.polyfit(log_sizes, log_counts, 1)[0])


class PowerLaws:
    """Power-law distributions."""

    @staticmethod
    def power_law_distribution(x: np.ndarray, alpha: float, x_min: float = 1.0) -> np.ndarray:
        """p(x) ∝ x^(-alpha) for x >= x_min, zero otherwise."""
        C = (alpha - 1) / x_min ** (1 - alpha)
        p = np.zeros_like(x, dtype=float)
        mask = x >= x_min
        p[mask] = C * x[mask] ** (-alpha)
        return p

    @staticmethod
    def estimate_power_law_exponent(data: np.ndarray, x_min: float | None = None) -> float:
        """MLE estimator: alpha = 1 + n / sum(ln(x_i / x_min))."""
        if x_min is None:
            x_min = float(data.min())
        data_filtered = data[data >= x_min]
        n = len(data_filtered)
        return float(1 + n / np.sum(np.log(data_filtered / x_min)))
