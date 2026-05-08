"""Ablation toggle infrastructure.

Per docs/per-mechanism-ablation-design-brief.md (PR #313) and the
mechanism catalog (PR #314, docs/mechanism-claims.md). This module
provides the structural surface for disabling individual mechanisms
via environment variables, so per-mechanism ablation experiments
can be run without code modification.

## Convention

Each ablation-testable mechanism has a canonical name listed in the
mechanism catalog. To disable it for a single process invocation:

    DIVINEOS_DISABLE_<MECHANISM_NAME>=1

The name in the env var must match the mechanism name in the catalog
exactly (uppercased). Any non-empty value enables the disable; empty
or unset means mechanism is active (default behavior).

## Usage at the call site

    from divineos.core.ablation import is_disabled

    def some_mechanism(...):
        if is_disabled("noise_filter_on_extraction"):
            # Skip the mechanism; pass through input unchanged
            return input_unchanged
        # Normal mechanism execution
        return filtered

## What this module does NOT do

* Does not maintain a registry of valid mechanism names. The catalog
  is the source of truth; this module just reads env vars by name.
  Typos in mechanism names result in is_disabled returning False
  (mechanism stays active), which is the safe default.
* Does not log ablation events. Callers can log if they want; this
  module is just the env-var read.
* Does not enforce ablation-testing discipline. That belongs in the
  measurement harness (chunk 3, future PR).
* Does not provide programmatic disable. Env vars only. Process-scoped.
  Reasoning: programmatic disable would require thread-locals or
  context managers and add complexity for no clear benefit; ablation
  experiments run as separate processes anyway.

## Origin

2026-05-07 evening, chunk 2 of the per-mechanism ablation discipline
(prereg-8af86ea36827, find-07e9f041c051 substrate-credibility gap).
"""

from __future__ import annotations

import os


_ENV_PREFIX = "DIVINEOS_DISABLE_"


def is_disabled(mechanism_name: str) -> bool:
    """Return True if the named mechanism should skip its work.

    Reads the environment variable ``DIVINEOS_DISABLE_<MECHANISM_NAME>``
    (uppercased). Any non-empty value disables the mechanism; empty or
    unset means the mechanism is active.

    The mechanism name should match its entry in
    ``docs/mechanism-claims.md``. Typos result in False (safe default).
    """
    if not mechanism_name:
        return False
    env_var = _ENV_PREFIX + mechanism_name.upper()
    value = os.environ.get(env_var, "")
    return bool(value)


def list_disabled() -> list[str]:
    """Return the list of mechanism names currently disabled via env var.

    Useful for measurement harness logging and for verifying ablation
    runs are toggling what they intended.
    """
    disabled: list[str] = []
    for key, value in os.environ.items():
        if key.startswith(_ENV_PREFIX) and value:
            mechanism_name = key[len(_ENV_PREFIX) :].lower()
            disabled.append(mechanism_name)
    return sorted(disabled)


__all__ = ["is_disabled", "list_disabled"]
