# Audit round: operating-loop findings persistence is broken across all 16 detectors

- **ID**: `round-eef42ce9a3c2`
- **Filed by**: aether
- **Filed at**: 2026-05-14 23:44 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

Findings-count diagnostic across 50 invocations of operating_loop_findings.json shows ONLY theater_fabrication entries. Every other detector (lepos, sycophancy, code_jargon, ack_theater, linguistic_drift, hedge_evidence, distancing, residency, spiral, substitution, etc.) has zero persisted findings. Either detectors return empty every turn, findings_log dict doesn't accumulate, or write fails silently. Found via Grok cross-vantage Option C (source-read + findings-data combination).

## Findings

### Rolling-window-of-50 in operating_loop_findings.json squeezes sparse-writer entries

- **ID**: `find-1505d70db349`
- **Actor**: aether
- **Severity**: LOW
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Two Stop hooks write to the same JSON file with separate appends + last-50 rolling truncation. detect-theater.sh fires more frequently (fabrication patterns are easier to trip than the 16 behavioral detectors), squeezing out any post-response-audit entries that land. Aether diagnostic 2026-05-14: post-response-audit's 16 detectors honestly return 0 on well-formed text (code-fence stripping is correct); when they DO fire, the entry ages out of the window before becoming visible.

**Recommendation**

Either separate files per hook (operating_loop_findings.json + theater_fabrication_findings.json) or aggregate entries from both hooks under a single shared timestamp window. Filed for next cycle.

**Resolution**

Two fixes shipped: (a) post-response-audit.sh now wires detect_jargon_dump instead of deprecated detect_lepos — replaces voice-token wrong-proxy with the live engineer-channel-noise detection the lepos module's own docstring recommends. WiringContract registry updated to swap entries. (b) Rolling window bumped 50->200 in both detect-theater.sh and post-response-audit.sh so sparse-writer entries (post-response-audit) coexist with high-frequency writes (detect-theater) instead of being squeezed out. Deferred deeper fix (per-source rolling window) noted in code comment.

### post-response-audit.sh writes never land — 16 detectors are upstream of broken persistence

- **ID**: `find-d02ad80f3f1a`
- **Actor**: aether
- **Severity**: HIGH
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: WONT_FIX

**Description**

50 entries in ~/.divineos/operating_loop_findings.json, ALL theater_fabrication-only. detect-theater.sh writes are landing; post-response-audit.sh writes are not. The whole post-response detector pipeline appears to be running but its output is being lost between the 'set findings_log[kind] = [...]' lines and the 'write_text(json.dumps(existing))' line. The night's detector-wiring work (hedge_evidence_check, code_jargon_detector, acknowledgment_theater_detector, linguistic_drift_detector wiring + Grok's WiringContract) is structurally upstream of this break — wiring is clean but output is dead. THIS is the dead-in-production class the completion-check probe should have flagged but couldn't because the probe checks wiring presence, not output landing.

**Recommendation**

Three hypotheses to test: (1) instrument post-response-audit.sh with diagnostic stderr to see whether total > 0 ever occurs; (2) check whether the bash-embedded Python is hitting a quoting/syntax issue mid-script that exits silently; (3) check whether the write_text path actually writes (permissions, encoding, race with detect-theater.sh).

**Resolution**

Finding was wrong-shape. The persistence layer works — detectors honestly return 0 on real text (code-fence stripping is correct behavior). The smaller true finding: rolling-window-of-50 squeezes sparse hook entries. Filing as separate LOW finding for next cycle.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
