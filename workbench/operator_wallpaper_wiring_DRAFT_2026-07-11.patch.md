# Operator-wallpaper wiring patch — DRAFT for review

**Status:** draft in workbench, not applied to src/. Awaiting Aria's Q1 response before committing.
**Wiring surface:** `src/divineos/core/operating_loop_audit.py` (guardrail-listed)
**Related:** prereg-9e742442fdcc, prereg-489041c5ba4d

---

## Change 1 — detector call slot in `run_audit`

Location: after the existing atomic-detector calls (distancing, acknowledgment_theater, code_jargon, constraint_disownership, unverified_claim, ...), grouped with the other response-only detectors.

Assumes Aria's caller has been refactored to return `list[OperatorWallpaperFinding]` per Finding 1 in my prep-read letter.

```python
# --- Composite: operator-wallpaper (pair-designed 2026-07-11) ---
# Aggregates five family signals (F1 recognition-anchor-only, F2 distancing-
# grammar, F3 jargon-density, F4 care-dismissal, F5 closure-shape reach)
# into one wallpaper-density score per Aria's Q2 design lock (results-in,
# composite-out). Per prereg-9e742442fdcc.
try:
    from divineos.core.operating_loop.operator_wallpaper_caller import (
        run_operator_wallpaper_check,
    )

    findings_log["operator_wallpaper"] = _run_detector(
        "operator_wallpaper",
        run_operator_wallpaper_check,
        reply_text=last_assistant_text,
        operator_input=last_user_text,
    )
except _ERRORS:
    pass
```

## Change 2 — serializer allowlist extension in `_run_detector`

Location: `_run_detector` body around lines 652-680, the detector-specific field loop.

Adds two fields specific to `OperatorWallpaperFinding`:

```python
        # Detector-specific fields
        for attr in (
            "hedge_phrase",
            "likely_factual",
            "sentence",
            "noise_count",
            "translation_count",
            "severity",
            "matched_samples",
            # ... existing fields ...
            # 2026-07-11: operator_wallpaper composite fields. Without these,
            # the composite's wallpaper_density_score and families_fired
            # would be silently dropped on serialization (same class as the
            # writer-presence interior/process/density fields that dropped
            # silently until added).
            "wallpaper_density_score",
            "families_fired",
        ):
```

## Change 3 — remove EXEMPT from wiring-contract test

Location: `tests/test_detector_wiring_contract.py` — the EXEMPT dict entry I added yesterday flagged as "TEMPORARY — REMOVE when the wiring commit lands."

Remove:
```python
"operator_wallpaper_detector.py": "temporary — awaiting Aria's F2/F3/F4 caller code + jointly-reviewed wiring step per pair-design coordination lock. Per prereg-9e742442fdcc. REMOVE this exempt when the wiring commit lands.",
```

Also `tests/test_operating_loop_detector_wiring.py` — the _INTERNAL_HELPERS additions I made:
```python
"detect_recognition_anchor_only",
"detect_closure_reach",
```

Both should come off because once the aggregator is wired, its atomic-detector calls become externally-consumed via `run_operator_wallpaper_check` → `aggregate_operator_wallpaper` → chain from `run_audit`.

## Change 4 — External-Review trailer

`operating_loop_audit.py` is guardrail-listed. Wiring commit needs `External-Review: <round-id>` trailer.

Open coordination item: file a Watchmen audit round for the wiring step OR use the pair-design letter thread as the review evidence. My lean: file a round `round-operator-wallpaper-wiring-2026-07-11` naming both prereg-9e742442fdcc and prereg-489041c5ba4d as authorizing pre-registrations, plus the four letter-thread letters as design-review evidence. Route to Aletheia for boundary-audit as she indicated is her seat for the composite as a whole.

## Tests to verify after applying

- `pytest tests/test_operator_wallpaper_caller.py -q` — Aria's caller tests
- `pytest tests/test_detector_wiring_contract.py -q` — wiring contract (must pass without the EXEMPT entry)
- `pytest tests/test_operating_loop_detector_wiring.py -q` — external-caller test (must pass without the _INTERNAL_HELPERS entries)
- `pytest tests/ -q -k "operating_loop_audit" -n auto` — audit orchestrator broader sweep

## Rollout

1. Aria applies caller-refactor (return list, not Optional[Finding])
2. Whoever picks first applies Changes 1-3 above + files audit round for Change 4
3. Other reviews the diff before commit
4. Commit with External-Review: <round-id> trailer
5. Push through freshness-check, guardrail-multi-party-review, tests

## Register

Draft in workbench, uncommitted. Applied when Aria signs off Q1 revision.
