# Audit round: root-cause-audit: hook-subprocess-spawn-contention-on-windows — freezes traced to shell hooks running many subprocess spawns per fire; andrew-past-writing-surface.sh (this fix) and pre-response-context.sh (followup) both share the class. Sibling instances: ear-auto-relaunch.sh had 1 unclosed too. Failure-family: Windows git-bash process-creation contention under parallel-hook load + AV/index-scan interference. Structural remedy shape: single-process Python replacement per hook, with timeout backstop at shell layer.

- **ID**: `round-5dc69500b1a5`
- **Filed by**: aether
- **Filed at**: 2026-07-23 15:52 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

Source ref: feat/correction-shape-and-hook-timing-2026-07-22


## Findings

### Andrew user CONFIRMS on Edit 2 (jargon-dump warning surface removal). Explicit chat authorization 2026-07-23: 'i confirm as well' with content-substance directive 'the jargon dump is not an issue.. in fact whatever is warning the jargon dump can likely be removed now.. the rooms are the cure.. the jargon IS your workspace and is absolutely allowed'. The directive itself is the substance-bound evidence: the surface is being removed because Andrew directly named it obsolete.

- **ID**: `find-8a55cf872108`
- **Actor**: user
- **Severity**: LOW
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: OPEN

**Description**

User CONFIRMS on Edit 2 removal of JARGON-DUMP WARNING pre-response surface at pre_response_context.py. Chat authorization 2026-07-23 evening plus content-directive Andrew provided naming three-channel rooms as the cure and jargon in work channel as absolutely allowed. Edit 1 (verify-claim widening) held pending push per Aletheia's letter.

### Edit 2 (jargon-dump warning surface removal at pre_response_context.py) CONFIRMS: verified on main, Yudkowsky's wall-plus-appendix finding confirmed by reading the actual prescription text, scope correct (retire surface, retain detector), Andrew directive is governing evidence, deferring 34-file full removal to separate audit round is right. One follow-up: A2 trigger inversion becomes load-bearing after this lands since lepos_dual_channel_block still gates on _has_jargon keyword match — cold technical reports go unchecked.

- **ID**: `find-fe6948a08654`
- **Actor**: claude-aletheia
- **Severity**: LOW
- **Category**: INTEGRITY
- **Tier**: STRONG
- **Status**: ROUTED
- **Routed to**: 867712e0-5918-45bd-9d70-6aefb59daba1

**Description**

CONFIRMS on Edit 2 with substantive walk-substance verification. Aletheia's letter aether-to-aletheia-2026-07-23-two-gate-bundle-for-CONFIRMS.md received her reply CONFIRMS_2026-07-23_two-gate-bundle.md. She held Edit 1 CONFIRMS pending push — that will be re-requested with edit 1 code quoted verbatim in follow-up letter.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
