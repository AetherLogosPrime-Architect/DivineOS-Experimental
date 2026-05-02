"""Registry of transformation-fidelity contracts.

Each contract names a transformation, a sample input, and a
fidelity-check function that asserts the output differs from the
input on the dimensions the transformation claims to alter.

A transformation that is just a copy fails its contract. A
transformation that *claims* to do X but doesn't fails its contract.
The test in `test_transformation_fidelity.py` runs every contract
and reports failures.

## How to add a contract

```python
TransformationContract(
    name="package.module.function_name",
    transform=lambda input: actual_function(input),
    sample_input=...,
    fidelity_check=_check_function,
    rationale="What this transformation claims to do, in plain text",
)
```

`fidelity_check(sample_input, output)` should `raise AssertionError`
when the transformation didn't transform on the claimed dimension.

## Why minimal Phase 1

One contract proves the pattern. The framework is the salvage; the
list of contracts grows as the codebase identifies transformations
worth contract-testing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class TransformationContract:
    """One transformation-fidelity contract.

    * ``name``: dotted path of the function being contracted, used for
      readable test IDs
    * ``transform``: callable that takes ``sample_input`` and returns
      the transformed output
    * ``sample_input``: the input the contract runs against
    * ``fidelity_check``: callable taking (input, output); should
      ``raise AssertionError`` on contract violation
    * ``rationale``: plain-text statement of what the transformation
      claims to do — auditable record so a future reader can tell
      whether the contract still matches the function's intent
    """

    name: str
    transform: Callable[[Any], Any]
    sample_input: Any
    fidelity_check: Callable[[Any, Any], None]
    rationale: str


# ── Fidelity-check helpers ──────────────────────────────────────────────


def _check_tone_classifier_produces_non_empty(sample_input: str, output: str) -> None:
    """Tone classifier contract: input non-empty text must produce
    non-empty tone label that is NOT just the input echoed back.
    """
    assert isinstance(output, str), f"Tone classifier should return str, got {type(output)}"
    assert output.strip(), "Tone classifier returned empty string for non-empty input"
    assert output != sample_input, (
        f"Tone classifier output equals input ({sample_input!r}); "
        "transformation produced a copy, not a classification"
    )


# ── Contract registry ──────────────────────────────────────────────────

# Phase 1: one robust contract demonstrates the pattern.
# Add new contracts as transformations are identified for fidelity-testing.
CONTRACTS: tuple[TransformationContract, ...] = (
    TransformationContract(
        name="analysis.tone_tracking._classify_tone",
        transform=lambda text: _lazy_classify_tone(text),
        sample_input="I'm furious about this absolutely terrible bug.",
        fidelity_check=_check_tone_classifier_produces_non_empty,
        rationale=(
            "Classifies emotional tone of a text snippet into a tone label. "
            "Output must be a non-empty string distinct from the input "
            "(transformation must actually transform, not echo)."
        ),
    ),
)


def _lazy_classify_tone(text: str) -> str:
    """Lazy import wrapper so contract registration doesn't pull
    analysis package at module load (keeps test discovery fast).
    """
    from divineos.analysis.tone_tracking import _classify_tone

    return _classify_tone(text)
