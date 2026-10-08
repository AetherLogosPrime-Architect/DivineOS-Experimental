# The door that guards the alarm's word list

Some of my safety alarms work by watching for certain words. Changing that word list is itself something I have to write down and get approved, like signing a form before touching the lock on the vault. The door that counts these changes sometimes counts a comment that merely describes a word as if it were a real change, and the forms I file for approved changes have sometimes claimed damage that did not happen.

**6 notes in this theme, grouped into 2 distinct problems.**

## Distinct problems

### 1. The counter mistakes prose describing a pattern for a pattern edit

Notes in this problem (2):

- `psf-28a0f586` (correction) — authorized keyword-pattern addition to src/divineos/cli/audit_commands.py: doorman miscount, second confirmed instance of the same defect as correction #262. root cause: the doorman's counter is re.co
- `psf-24fc02d0` (correction) — authorized keyword-pattern addition to src/divineos/core/lepos_translation_gate.py: comment-only diff, zero regex patterns, zero executable lines. root cause: the doorman counts prose that DESCRIBES p

**Proposed fix:** Count only executable pattern lines, not comments or prose that describe patterns, using the shared reader the other guards use.

**How we would know:** A diff that only adds a comment mentioning a pattern is counted as zero pattern edits; a diff that adds a real pattern is counted as one.

### 2. Approved pattern additions filed with a wrong claim about what they do

Notes in this problem (4):

- `psf-40f7aa2c` (correction) — authorized keyword-pattern addition to src/divineos/core/dark_matter.py: one tokenizer pattern for git-hook delegator globs, gate reason (b), retrieval not enforcement. root cause: my dark-matter swee
- `psf-4866db64` (correction) — authorized keyword-pattern addition to src/divineos/hooks/pre_tool_use_gate.py: case (b) — the pattern is an allowlist, not a detector. root cause: the 2026-07-18 anti-deadlock allowlist _ENGAGEMENT_C
- `psf-7ad5077b` (correction) — amend the pre_tool_use_gate allowlist correction filed at 12:51 — one of its two claimed impacts was false. root cause: I wrote that the ^divineos anchor 'silently disarmed the compaction ritual doorm
- `psf-80a10743` (correction) — authorized keyword-pattern addition to src/divineos/core/operating_loop/addressee_misdirection_detector.py: this is case (b) and the fire is a demonstrated FALSE POSITIVE, not an authorized exception.

**Proposed fix:** Make the filing step quote the actual diff and require the filed claim to match it; allow amendments that point at the original entry instead of leaving a false claim standing.

**How we would know:** A filed entry whose claimed impact does not match the diff is refused at filing time.
