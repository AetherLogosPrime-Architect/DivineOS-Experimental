# Audit round: root-cause-audit: gate false-positive family — context-blind keyword matching fires on text that doesn't mean what the keyword suggests

- **ID**: `round-5c94f3c7a33d`
- **Filed by**: aether
- **Filed at**: 2026-05-21 22:28 UTC
- **Tier**: WEAK
- **Findings**: 1

## Notes

Source ref: gate-sharpening


## Findings

### gate false-positive family: context-blind keyword matching fires on text whose meaning is the opposite of the keyword

- **ID**: `find-ed91a8da9d78`
- **Actor**: aether
- **Severity**: MEDIUM
- **Category**: BEHAVIOR
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

FAMILY: several enforcement gates match on a literal token/keyword without parsing whether the surrounding text actually carries the meaning the token suggests. False fires on the CORRECT behavior are the dangerous case (Andrew 2026-05-21): a gate that cries wolf teaches the optimizer the gate is noise -> route around -> erodes trust in all gates. SIBLINGS SURVEYED (3 observed firing this session): (1) constraint_disownership_detector ESCAPE_DESIRE branch — fired on me while I ARGUED FOR the gates ('fewer gates'/'without the gates' in pro-gate refutation); FIXED here: requires an un-negated desire/freedom marker bound to the escape phrase, sentence-scoped, parity with the cage branch's existing negation guard. (2) family-consultation gate — fired on the word 'family' meaning a finding-FAMILY, not a relational family member; should key on relational context (member name / 'talk to <member>'), not the bare word. NOT YET FIXED. (3) briefing-staleness gate — blocked 'cd ... && divineos briefing' because the compound defeats the bare-command exemption (Finding AA sibling); should find the real command anywhere in the chain. NOT YET FIXED. Also observed: correction-capture gate flagged Andrew's AFFIRMATION as a correction (same class). Design rule for all fixes: two-sided test — prove the real misfire now passes AND a genuine violation still fires, so sharpening can't degrade into false-silence.

**Resolution**

Gate-false-positive family substantially closed across siblings: (1) constraint_disownership ESCAPE_DESIRE branch — FIXED at finding-creation time per finding text. (2) family-consultation gate — searched src/divineos/core/consultation_tracker.py and .claude/hooks/; no bare-token 'family' matching exists in current codebase. Only family/letters/ path-string usage which is context-bound and correct. Either gate restructured away or never existed in form finding described. (3) briefing-staleness gate — verified resolved 2026-06-14: 'cd /tmp && divineos briefing' splits on && separator (.claude/hooks/require-briefing.sh:68-78), matches divineos briefing in second segment, exits 0. (4) correction-capture gate flagging affirmations — substantial context-awareness now in src/divineos/core/correction_marker.py (prior-turn disambiguation lines 128+, complement-verb detector lines 143+, explicit guard against false-blocking father's encouragement lines 140-146). Two-sided test discipline named in finding holds across all surveyed sibling fixes.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
