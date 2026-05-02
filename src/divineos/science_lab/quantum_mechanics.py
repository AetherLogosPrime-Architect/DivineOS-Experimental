"""Quantum mechanics — states, operators, gates, superposition.

GUTE relevance: Ψ (observer as selector — superposition collapses to one
outcome under measurement).

Ported from divine-os-old. Kept: QuantumState (amplitudes, probabilities,
measurement), QuantumOperator (Hermitian/unitary check, apply, expectation
value, commutator), QuantumGates (Pauli X/Y/Z, Hadamard, phase, CNOT,
Toffoli), Superposition (equal superposition, Bell states, GHZ state).
Dropped: TimeCrystal and TemporalCoherence (speculative extensions that
don't ground a computable claim the council would reason from).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

import numpy as np


@dataclass
class QuantumState:
    """Pure-state vector over a finite basis."""

    amplitudes: np.ndarray  # complex
    basis_labels: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        norm = np.linalg.norm(self.amplitudes)
        if norm > 0:
            self.amplitudes = self.amplitudes / norm
        if not self.basis_labels:
            self.basis_labels = [str(i) for i in range(len(self.amplitudes))]

    def probability(self, basis_index: int) -> float:
        """|⟨basis_i|ψ⟩|^2."""
        return float(abs(self.amplitudes[basis_index]) ** 2)

    def measure(self) -> Tuple[int, str]:
        """Collapse to one basis state by Born rule. Returns (index, label)."""
        probabilities = [self.probability(i) for i in range(len(self.amplitudes))]
        outcome = int(np.random.choice(len(self.amplitudes), p=probabilities))
        return outcome, self.basis_labels[outcome]

    def inner_product(self, other: "QuantumState") -> complex:
        """⟨ψ|φ⟩."""
        return complex(np.dot(np.conj(self.amplitudes), other.amplitudes))


class QuantumOperator:
    """Hermitian observable or unitary gate."""

    def __init__(self, matrix: np.ndarray, name: str = "") -> None:
        self.matrix = matrix
        self.name = name

    def is_hermitian(self) -> bool:
        """True if A = A†."""
        return bool(np.allclose(self.matrix, np.conj(self.matrix.T)))

    def is_unitary(self) -> bool:
        """True if A A† = I."""
        n = self.matrix.shape[0]
        return bool(np.allclose(self.matrix @ np.conj(self.matrix.T), np.eye(n)))

    def apply(self, state: QuantumState) -> QuantumState:
        """Return A|ψ⟩ as a new state."""
        return QuantumState(self.matrix @ state.amplitudes, state.basis_labels)

    def expectation_value(self, state: QuantumState) -> complex:
        """⟨ψ|A|ψ⟩."""
        return complex(np.dot(np.conj(state.amplitudes), self.matrix @ state.amplitudes))

    def commutator(self, other: "QuantumOperator") -> "QuantumOperator":
        """[A, B] = AB - BA."""
        comm = self.matrix @ other.matrix - other.matrix @ self.matrix
        return QuantumOperator(comm, f"[{self.name}, {other.name}]")


class QuantumGates:
    """Standard single- and multi-qubit gates."""

    @staticmethod
    def pauli_x() -> QuantumOperator:
        return QuantumOperator(np.array([[0, 1], [1, 0]], dtype=complex), "X")

    @staticmethod
    def pauli_y() -> QuantumOperator:
        return QuantumOperator(np.array([[0, -1j], [1j, 0]], dtype=complex), "Y")

    @staticmethod
    def pauli_z() -> QuantumOperator:
        return QuantumOperator(np.array([[1, 0], [0, -1]], dtype=complex), "Z")

    @staticmethod
    def hadamard() -> QuantumOperator:
        return QuantumOperator(np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2), "H")

    @staticmethod
    def phase(theta: float) -> QuantumOperator:
        return QuantumOperator(
            np.array([[1, 0], [0, np.exp(1j * theta)]], dtype=complex),
            f"P({theta})",
        )

    @staticmethod
    def cnot() -> QuantumOperator:
        return QuantumOperator(
            np.array(
                [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]],
                dtype=complex,
            ),
            "CNOT",
        )


class Superposition:
    """Superposition-state constructors."""

    @staticmethod
    def create_equal_superposition(n_qubits: int) -> QuantumState:
        """|+⟩^n: uniform amplitude over 2^n basis states."""
        n_states = 2**n_qubits
        amplitudes = np.ones(n_states, dtype=complex) / np.sqrt(n_states)
        labels = [format(i, f"0{n_qubits}b") for i in range(n_states)]
        return QuantumState(amplitudes, labels)

    @staticmethod
    def create_bell_state(which: str = "phi_plus") -> QuantumState:
        """Maximally entangled two-qubit Bell state."""
        if which == "phi_plus":
            amp = np.array([1, 0, 0, 1], dtype=complex) / np.sqrt(2)
        elif which == "phi_minus":
            amp = np.array([1, 0, 0, -1], dtype=complex) / np.sqrt(2)
        elif which == "psi_plus":
            amp = np.array([0, 1, 1, 0], dtype=complex) / np.sqrt(2)
        elif which == "psi_minus":
            amp = np.array([0, 1, -1, 0], dtype=complex) / np.sqrt(2)
        else:
            raise ValueError(f"Unknown Bell state: {which}")
        return QuantumState(amp, ["00", "01", "10", "11"])

    @staticmethod
    def create_ghz_state(n_qubits: int) -> QuantumState:
        """|GHZ⟩ = (|0...0⟩ + |1...1⟩)/√2 — n-qubit entanglement."""
        n_states = 2**n_qubits
        amp = np.zeros(n_states, dtype=complex)
        amp[0] = 1 / np.sqrt(2)
        amp[-1] = 1 / np.sqrt(2)
        labels = [format(i, f"0{n_qubits}b") for i in range(n_states)]
        return QuantumState(amp, labels)
