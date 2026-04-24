"""Science Lab — numerical test harness for GUTE terms and derived claims.

Ported from the old DivineOS (divine-os-old/DivineOS/districts/engines/science_lab/).
The lab lets any term in the founding equation (or any derived claim) be pinned
to a computable referent and run through real numbers. A claim that cannot
be expressed as a slice cannot be tested here — which is itself a signal.

Foundational slice: LC (Lovecraftian Constant) — chaos/entropy, computed via
Lyapunov exponent of the logistic map and Shannon entropy of sample
distributions. Bounded chaos (r in (0,4]) supports the "integrated, not
destroying" reading; r > 4 → unbounded, which is how we know the boundary.

Growth policy: same as scaffold_invocations and the pre-reg system — small,
conservative, each module earns its place by providing a computable referent
for a claim that the council actually wants to reason from.
"""

from __future__ import annotations

__all__ = ["complexity_theory", "information_theory", "gute_bridge"]
