"""Transformation-fidelity test runner.

For each contract registered in `transformation_contracts.CONTRACTS`,
run the transformation on its sample input and assert the contract's
fidelity-check passes.

A contract violation here means a transformation isn't actually
transforming on the dimension it claims to alter — i.e., it's
returning a copy, an echo, or a no-op disguised as work. That's
exactly the "theater" failure mode the no-theater rule guards
against in spirit but didn't enforce mechanically before this.
"""

from __future__ import annotations

import pytest

from .transformation_contracts import CONTRACTS, TransformationContract


@pytest.mark.parametrize("contract", CONTRACTS, ids=lambda c: c.name)
def test_transformation_actually_transforms(contract: TransformationContract) -> None:
    """Every registered transformation must satisfy its fidelity contract."""
    output = contract.transform(contract.sample_input)
    contract.fidelity_check(contract.sample_input, output)


def test_contracts_have_unique_names() -> None:
    """Two contracts with the same name would mask each other in
    parametrized test IDs. Detect this at the framework level so the
    error message is clear.
    """
    names = [c.name for c in CONTRACTS]
    duplicates = {n for n in names if names.count(n) > 1}
    assert not duplicates, f"Duplicate contract names: {duplicates}"


def test_contracts_have_rationales() -> None:
    """Every contract must state, in plain text, what the transformation
    claims to do. Auditable record so a future reader can tell whether
    the contract still matches the function's actual intent.
    """
    for contract in CONTRACTS:
        assert contract.rationale.strip(), f"Contract {contract.name} missing rationale"


def test_negative_case_caught() -> None:
    """Sanity-check the framework: a deliberately-broken contract
    (transformation returns input unchanged) must fail its check.
    Otherwise the framework can't distinguish theater from real work.
    """
    from .transformation_contracts import _check_tone_classifier_produces_non_empty

    sample = "I'm furious about this absolutely terrible bug."
    with pytest.raises(AssertionError, match="output equals input|copy"):
        # Identity transformation — should fail the check
        _check_tone_classifier_produces_non_empty(sample, sample)
