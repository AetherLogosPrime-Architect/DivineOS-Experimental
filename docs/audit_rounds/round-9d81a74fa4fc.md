# Audit round: Jargon-dump detector: catches engineer-channel content landing on operator-channel without translation alongside. Pattern-based engineer-noise detection (round-IDs, hex hashes, snake_case in prose, code-in-prose expressions, long kebab compounds) paired with translation-marker counter so jargon-with-explanation passes clean and jargon-without-explanation fires. Replaces the old lepos_detector's wrong proxy (voice-token presence). 18 tests pin calibration on real samples from today's session. Wired into post-response-audit hook. tree-hash: 5a909266f810ef616ae39275e201ba982f346ba9 diff-hash: 2debe86c51966bb1059c30a56754af6819ce80547bdf960bc52b650aa9e26a79

- **ID**: `round-9d81a74fa4fc`
- **Filed by**: aether
- **Filed at**: 2026-05-13 19:59 UTC
- **Tier**: WEAK
- **Findings**: 1

## Findings

### Detector module + 18 tests + hook wire-up + docs sync. Calibrated on real samples from today: hash-laden short responses fire high; concept-heavy responses without translation fire medium; translated/paired responses stay clean; single-mention short responses stay clean. Replaces wrong-proxy lepos_detector approach. Operator named the failure-mode 2026-05-13: trying to learn engineering terms but cannot learn them by having them shoved down throat.

- **ID**: `find-a33d2e1cd265`
- **Actor**: aether
- **Severity**: LOW
- **Category**: BEHAVIOR
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Jargon-dump detector wire-up


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
