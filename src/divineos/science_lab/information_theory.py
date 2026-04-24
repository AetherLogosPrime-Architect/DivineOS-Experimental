"""Information theory — entropy, mutual information, channel capacity.

GUTE relevance: LC (entropy, uncertainty), Ψ (information as selection).

Ported from divine-os-old. Kept: Shannon/joint/conditional entropy, mutual
information, KL divergence, Huffman-length approximation, BSC and AWGN
capacity, Hamming distance, von Neumann entropy, Hamming(7,4) encode, and
repetition code. Dropped: example() demos.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

import numpy as np


class ShannonEntropy:
    """Shannon entropy and related information measures."""

    @staticmethod
    def entropy(probabilities: np.ndarray, base: float = 2) -> float:
        """H(X) = -sum(p * log_base(p)). Zeros skipped to avoid log(0)."""
        p = probabilities[probabilities > 0]
        return float(-np.sum(p * np.log(p) / np.log(base)))

    @staticmethod
    def entropy_from_data(data: List[Any], base: float = 2) -> float:
        """Entropy from empirical frequencies of data samples."""
        counts = Counter(data)
        total = len(data)
        probabilities = np.array([count / total for count in counts.values()])
        return ShannonEntropy.entropy(probabilities, base)

    @staticmethod
    def joint_entropy(p_xy: np.ndarray, base: float = 2) -> float:
        """H(X,Y) from joint distribution p_xy (2D)."""
        p = p_xy[p_xy > 0]
        return float(-np.sum(p * np.log(p) / np.log(base)))

    @staticmethod
    def conditional_entropy(p_xy: np.ndarray, base: float = 2) -> float:
        """H(Y|X) = H(X,Y) - H(X)."""
        p_x = np.sum(p_xy, axis=1)
        h_xy = ShannonEntropy.joint_entropy(p_xy, base)
        h_x = ShannonEntropy.entropy(p_x, base)
        return float(h_xy - h_x)

    @staticmethod
    def mutual_information(p_xy: np.ndarray, base: float = 2) -> float:
        """I(X;Y) = H(X) + H(Y) - H(X,Y)."""
        p_x = np.sum(p_xy, axis=1)
        p_y = np.sum(p_xy, axis=0)
        h_x = ShannonEntropy.entropy(p_x, base)
        h_y = ShannonEntropy.entropy(p_y, base)
        h_xy = ShannonEntropy.joint_entropy(p_xy, base)
        return float(h_x + h_y - h_xy)

    @staticmethod
    def kl_divergence(p: np.ndarray, q: np.ndarray, base: float = 2) -> float:
        """D_KL(P||Q) over the support where both are positive."""
        mask = (p > 0) & (q > 0)
        return float(np.sum(p[mask] * np.log(p[mask] / q[mask]) / np.log(base)))


class DataCompression:
    """Data compression (Huffman approximation)."""

    @staticmethod
    def huffman_code_lengths(probabilities: np.ndarray) -> Dict[int, int]:
        """Approximate Huffman code lengths via ceil(-log2 p). Not optimal, but close."""
        n = len(probabilities)
        if n == 1:
            return {0: 1}
        sorted_indices = np.argsort(probabilities)
        code_lengths: Dict[int, int] = {}
        for idx in sorted_indices:
            code_lengths[int(idx)] = max(1, int(np.ceil(-np.log2(probabilities[idx]))))
        return code_lengths

    @staticmethod
    def average_code_length(probabilities: np.ndarray) -> float:
        """Expected length under the approximate Huffman code."""
        code_lengths = DataCompression.huffman_code_lengths(probabilities)
        return float(sum(probabilities[i] * code_lengths[i] for i in range(len(probabilities))))

    @staticmethod
    def compression_ratio(original_entropy: float, compressed_length: float) -> float:
        """Compression ratio = compressed_length / original_entropy."""
        return compressed_length / original_entropy if original_entropy > 0 else 1.0


class ChannelCapacity:
    """Channel capacity and coding theory."""

    @staticmethod
    def binary_symmetric_channel_capacity(p_error: float) -> float:
        """C_BSC = 1 - H_b(p). Equals 1 at p=0 or p=1 (noise-free and inverted)."""
        if p_error == 0 or p_error == 1:
            return 1.0
        h_p = -p_error * np.log2(p_error) - (1 - p_error) * np.log2(1 - p_error)
        return float(1 - h_p)

    @staticmethod
    def awgn_channel_capacity(snr: float, bandwidth: float = 1.0) -> float:
        """Shannon-Hartley: C = B * log2(1 + SNR), SNR linear."""
        return float(bandwidth * np.log2(1 + snr))

    @staticmethod
    def snr_db_to_linear(snr_db: float) -> float:
        """Convert SNR from dB to linear ratio."""
        return float(10 ** (snr_db / 10))

    @staticmethod
    def hamming_distance(x: str, y: str) -> int:
        """Number of positions at which x and y differ."""
        if len(x) != len(y):
            raise ValueError("Strings must have equal length")
        return sum(c1 != c2 for c1, c2 in zip(x, y))


class QuantumInformation:
    """Quantum-information measures."""

    @staticmethod
    def von_neumann_entropy(rho: np.ndarray) -> float:
        """S(rho) = -Tr(rho log2 rho), via eigenvalues."""
        eigenvalues = np.linalg.eigvalsh(rho)
        eigenvalues = eigenvalues[eigenvalues > 1e-10]
        return float(-np.sum(eigenvalues * np.log2(eigenvalues)))

    @staticmethod
    def qubit_entropy(p0: float) -> float:
        """Entropy of a qubit mixed state rho = p0|0><0| + (1-p0)|1><1|."""
        if p0 == 0 or p0 == 1:
            return 0.0
        p1 = 1 - p0
        return float(-p0 * np.log2(p0) - p1 * np.log2(p1))


class ErrorCorrection:
    """Basic error-correction codes."""

    @staticmethod
    def hamming_7_4_encode(data: str) -> str:
        """Hamming(7,4): encode 4 data bits to 7 (can correct any 1-bit error)."""
        if len(data) != 4:
            raise ValueError("Data must be 4 bits")
        d = [int(b) for b in data]
        p1 = d[0] ^ d[1] ^ d[3]
        p2 = d[0] ^ d[2] ^ d[3]
        p3 = d[1] ^ d[2] ^ d[3]
        return f"{p1}{p2}{d[0]}{p3}{d[1]}{d[2]}{d[3]}"

    @staticmethod
    def repetition_code_encode(bit: str, n: int = 3) -> str:
        """Repeat bit n times."""
        return bit * n

    @staticmethod
    def repetition_code_decode(encoded: str) -> str:
        """Majority-vote decode."""
        ones = encoded.count("1")
        zeros = encoded.count("0")
        return "1" if ones > zeros else "0"
