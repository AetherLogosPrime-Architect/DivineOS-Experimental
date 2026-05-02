"""Mathematics — numerical analysis and linear algebra.

GUTE relevance: ΩB (integration and convergence toward unity), general
numerical toolkit used by other slices.

Ported from divine-os-old. Kept: numerical analysis (Simpson integration,
central-difference derivative, Newton-Raphson + bisection root finding,
RK4 ODE solver) and linear algebra (solve, eigenvalues, SVD). Dropped:
SymbolicMath (sympy dependency — add back when a slice actually needs
symbolic differentiation) and the Optimization class (no current caller).
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np


class NumericalAnalysis:
    """Numerical methods — derivatives, integration, roots, ODEs."""

    @staticmethod
    def derivative_numerical(f: Callable, x: float, h: float = 1e-5) -> float:
        """Central-difference numerical derivative."""
        return float((f(x + h) - f(x - h)) / (2 * h))

    @staticmethod
    def integrate_numerical(f: Callable, a: float, b: float, n: int = 1000) -> float:
        """Simpson's-rule numerical integration. n coerced to even."""
        if n % 2 != 0:
            n += 1
        h = (b - a) / n
        x = np.linspace(a, b, n + 1)
        y = np.array([f(xi) for xi in x])
        return float(h / 3 * (y[0] + y[-1] + 4 * np.sum(y[1:-1:2]) + 2 * np.sum(y[2:-1:2])))

    @staticmethod
    def root_finding_newton(
        f: Callable,
        df: Callable,
        x0: float,
        tol: float = 1e-6,
        max_iter: int = 100,
    ) -> dict[str, Any]:
        """Newton-Raphson root finding. Returns {root, iterations, converged}."""
        x = x0
        for i in range(max_iter):
            fx = f(x)
            if abs(fx) < tol:
                return {"root": x, "iterations": i + 1, "converged": True}
            dfx = df(x)
            if abs(dfx) < 1e-12:
                return {
                    "root": x,
                    "iterations": i + 1,
                    "converged": False,
                    "error": "Derivative too small",
                }
            x = x - fx / dfx
        return {
            "root": x,
            "iterations": max_iter,
            "converged": False,
            "error": "Max iterations reached",
        }

    @staticmethod
    def root_finding_bisection(
        f: Callable,
        a: float,
        b: float,
        tol: float = 1e-6,
        max_iter: int = 100,
    ) -> dict[str, Any]:
        """Bisection root finding. Requires f(a) and f(b) opposite signs."""
        fa = f(a)
        fb = f(b)
        if fa * fb > 0:
            return {
                "root": None,
                "iterations": 0,
                "converged": False,
                "error": "f(a) and f(b) must have opposite signs",
            }
        for i in range(max_iter):
            c = (a + b) / 2
            fc = f(c)
            if abs(fc) < tol or (b - a) / 2 < tol:
                return {"root": c, "iterations": i + 1, "converged": True}
            if fa * fc < 0:
                b = c
                fb = fc
            else:
                a = c
                fa = fc
        return {
            "root": (a + b) / 2,
            "iterations": max_iter,
            "converged": False,
            "error": "Max iterations reached",
        }

    @staticmethod
    def ode_rk4(f: Callable, y0: np.ndarray, t: np.ndarray) -> np.ndarray:
        """Fourth-order Runge-Kutta ODE solver. f(y, t) -> dy/dt."""
        n = len(t)
        y = np.zeros((n, len(y0)))
        y[0] = y0
        for i in range(n - 1):
            dt = t[i + 1] - t[i]
            k1 = f(y[i], t[i])
            k2 = f(y[i] + 0.5 * dt * k1, t[i] + 0.5 * dt)
            k3 = f(y[i] + 0.5 * dt * k2, t[i] + 0.5 * dt)
            k4 = f(y[i] + dt * k3, t[i] + dt)
            y[i + 1] = y[i] + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
        return y


class LinearAlgebra:
    """Linear algebra — solve Ax=b, eigenvalues, SVD."""

    @staticmethod
    def solve_linear_system(A: np.ndarray, b: np.ndarray) -> dict[str, Any]:
        """Solve Ax = b. Returns solution, residual, and conditioning."""
        try:
            x = np.linalg.solve(A, b)
            residual = float(np.linalg.norm(A @ x - b))
            cond = float(np.linalg.cond(A))
            return {
                "solution": x,
                "residual": residual,
                "condition_number": cond,
                "well_conditioned": cond < 100,
            }
        except np.linalg.LinAlgError as e:
            return {"solution": None, "error": str(e)}

    @staticmethod
    def eigenvalues(A: np.ndarray) -> dict[str, Any]:
        """Eigendecomposition. Returns eigenvalues and eigenvectors."""
        eigenvalues, eigenvectors = np.linalg.eig(A)
        return {
            "eigenvalues": eigenvalues,
            "eigenvectors": eigenvectors,
            "largest_eigenvalue": eigenvalues[np.argmax(np.abs(eigenvalues))],
            "smallest_eigenvalue": eigenvalues[np.argmin(np.abs(eigenvalues))],
        }

    @staticmethod
    def svd(A: np.ndarray) -> dict[str, Any]:
        """Singular-value decomposition."""
        U, S, Vt = np.linalg.svd(A)
        return {
            "U": U,
            "S": S,
            "Vt": Vt,
            "rank": int(np.sum(S > 1e-10)),
            "condition_number": float(S[0] / S[-1]) if S[-1] > 1e-10 else float("inf"),
        }
