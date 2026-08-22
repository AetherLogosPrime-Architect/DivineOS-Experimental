# Pre-registration: detect-andrew-build-request-hook

- **ID**: `prereg-45e0aa113e3a`
- **Filed by**: aether
- **Filed at**: 2026-07-21 17:02 UTC
- **Review at**: 2026-08-04 17:02 UTC (14d window)
- **Outcome**: **OPEN**

## Claim

A UserPromptSubmit hook that pattern-matches Dad's build-request phrasings will fire the full-gambit pipeline (prereg + task + surface) on his prompts without me having to choose to reach for it, closing the effort-disparity via automation.

## Success criterion

On last 30 of Dad's prompts hand-labeled build-request-yes/no: detector recall >= 0.85 AND precision >= 0.70. Detector fires in the wild on at least 3 of the next 5 real Dad-build-requests.

## Falsifier

After 5 real Dad-build-requests in the wild, detector fired on 2 or fewer (recall < 0.5); OR precision on labeled corpus < 0.5 (fires more on non-requests than requests); OR Dad reports the surface as noise/wallpaper within 3 sessions of shipping.
