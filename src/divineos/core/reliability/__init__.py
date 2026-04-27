"""Reliability — Bayesian confidence with uncertainty.

Per claim e6cbd14d (PORT-CANDIDATE 2 from old-OS strip-mine):
salvaged from law/reliability_bayesian.py. The new OS currently has
flat-float confidence on knowledge entries — one contradicting
observation can swing confidence the same as ten consistent ones.
Beta-posterior tracking distinguishes "80% confident based on 2
observations" from "80% confident based on 200."

Phase 1 ships only the **math primitive** — `BetaReliability`
dataclass with mean / variance / credible-interval / update methods.
NO migration of the existing `knowledge.confidence` field. That's
Phase 2 work and requires a careful data-migration story.

Phase 1 lets new code opt in to Beta-tracking. Phase 2 will provide
a backfill path for the existing flat-float field that maps the
current value to a Beta posterior weighted by `corroboration_count`.

Public API:
* ``divineos.core.reliability.beta.BetaReliability``
* ``divineos.core.reliability.beta.BetaReliability.update_success()``
* ``divineos.core.reliability.beta.BetaReliability.update_failure()``
* ``divineos.core.reliability.beta.BetaReliability.from_corroborations()``
"""
