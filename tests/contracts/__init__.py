"""Transformation-fidelity contracts (claim 4f2908ac).

Salvaged from old-OS Path Governor spec: *"Monitors transformation
fidelity (does data actually change, or just copy?)"*

The new OS's "no theater" rule is enforced via review register.
Mechanical enforcement requires test contracts that take a declared
transformation, run a sample through it, and assert the output
differs from the input on the dimensions the transformation claims
to alter.

Phase 1 ships the framework + one example contract. Future
transformations register additional contracts; the test runner
auto-parametrizes over them.
"""
