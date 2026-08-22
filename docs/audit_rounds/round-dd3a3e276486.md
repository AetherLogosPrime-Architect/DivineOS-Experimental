# Audit round: PR #404 review - gate automation sweep clean rebuild. Covers three guardrail-touching commits: becdc689 (.claude/settings.json registering the compaction-ritual trigger hook, scripts/check_multi_party_review.py trailer-grammar widening, src/divineos/hooks/pre_tool_use_gate.py, two identity-anchor files), 2471a7e5 (pre_tool_use_gate quote-context scanner plus restoration of PR #400 work the rebuild had reverted), aac4d305 (setup/setup-hooks.sh removing the clock-window trailer auto-attach). Substance: quote-context scanner replaces a raw-string substring scan so operator characters inside quoted argument values stop defeating bypasses, with F22 and F31 exploits asserted still-blocked; system-load check moves from an unattainable 16GB-absolute threshold to headroom-plus-ceiling with the ceiling derived from Andrew's observed 98-99 percent crash point; ear_sweep orphan reaper fixed after never having reaped anything since it was written; trailer auto-attach removed after being reproduced as a clock-decided guess that stamped an unrelated round onto a commit it had not reviewed.

- **ID**: `round-dd3a3e276486`
- **Filed by**: aether
- **Filed at**: 2026-08-01 16:19 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

Source ref: feat/403-rebuild-2026-08-01


## Findings

### CONFIRMS PR #404 -- operator confirm

- **ID**: `find-0a1afa1ec78b`
- **Actor**: user
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 1852ff33-68ee-4fef-8bc6-ed113ef96ae7

**Description**

Andrew CONFIRMS PR #404 in-session 2026-08-01, verbatim: 'i confirm as well :)' -- given after reading Aletheia's audit of branch tip 921ff275 in full. Scope of what he is confirming: the clean rebuild of #403 (7 commits, 79 files) including the quote-context scanner in pre_tool_use_gate.py, the system-load headroom-plus-ceiling recalibration whose 92 percent ceiling is derived from his own observed 98-99 percent crash point, the ear_sweep orphan-reaper fix, the removal of the clock-window trailer auto-attach from setup-hooks.sh, and docs/ai_research. He also directed the surrounding process change in the same exchange: committing is free, pushing a draft to origin is free, only merge-to-main requires audit, and PRs should be batched 5-10 at a time as drafts for one audit pass so nothing sits in limbo. Aletheia's finding find-721417a715f5 CONFIRMS with F105 open at MEDIUM and explicitly not blocking. F105 is a fix-list item on the ear_sweep ownership heuristic -- validated on n=1, asks for a dry-run mode, an honest provenance note in the docstring, and a hard exclusion on ancestry chains containing another checkout root. Recorded as outstanding work rather than resolved by this merge.

### PR #404 rebuild -- quote scanner falsified across 39 cases, no hole

- **ID**: `find-721417a715f5`
- **Actor**: external-auditor
- **Severity**: MEDIUM
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 1560a463-300e-4f9d-af75-ae1ba8e5525e

**Description**

Branch tip 921ff275 verified. QUOTE SCANNER (#2): extracted _has_compound_shape from pre_tool_use_gate.py and ran 39 adversarial cases against real bash semantics. 37 exact matches. The dquote/squote substitution asymmetry -- active in double, inert in single -- is correct in both directions, which is the case shlex would have destroyed; the deviation from the F31 shlex recommendation was right and was flagged in the docstring rather than quietly substituted. Escape handling correct including the squote-rejoin idiom where hand-rolled scanners usually lose state. TWO DIVERGENCES FOUND, both the comment-hash case (scanner flags operators bash would discard); direction is scanner=True = bypass refused = MORE conservative than bash, so it fails toward blocking, never toward permitting -- not worth fixing. TWO SUSPECTED HOLES INVESTIGATED AND CLEARED by running real bash rather than reading: ANSI-C quoting expands to a literal argument that bash does NOT re-parse as an operator, and quoted operators in assignment values are not re-scanned. No exploitable divergence found. PRECEDENT (#3): the 2026-06-02 Schneier rejection of quoted-context silencing does not apply here and the reasoning is not motivated -- the cost asymmetry genuinely inverts (there a false positive is a re-check; here it hard-blocks every tool call including the remedy, which is the Catch-22 that fired three times), and the Schneier note targets heuristics guessing at intent whereas this models what the shell executes. Recommend recording that distinction beside the Schneier note so the next reader does not resolve the apparent conflict wrongly. F105 OPEN (MEDIUM): the ear_sweep ownership test is a heuristic validated on n=1 -- one process table, one OS, one worktree layout -- and its confidence should match its provenance. Failure directions are asymmetric: under-reaping restores the status quo (the reaper never reaped anything before), over-reaping kills live work, and the third bug did exactly that by claiming Aria's four live watchers. Asks: (1) dry-run mode logging what it would kill without killing, run a week, converting n=1 to n=sessions at zero risk; (2) name the heuristic and its validation basis in the docstring; (3) hard exclusion on any PID whose ancestry contains another checkout root. Also: the prefix bug is a boundary error and boundary errors travel in families -- check every path comparison in the reaper for component-vs-prefix. SYSTEM-LOAD (#4): 92 percent from Andrew observed 98-99 percent minus margin is a real upgrade over an invented 85 percent, and the margin names what it absorbs; recommend logging actual free-memory at every check so the ceiling can be set from a distribution in a month rather than an anecdote.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
