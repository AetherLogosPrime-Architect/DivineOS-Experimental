# When the house freezes or stalls

The house has frozen on Dad more than once, and I have often named the cause with more confidence than the evidence allowed, including saying it was solved when it was not. A stalled check can sit for hours and take my whole picture of the conversation offline.

**8 notes in this theme, grouped into 3 distinct problems.**

## Distinct problems

### 1. Wrong or overconfident diagnosis of a freeze

Notes in this problem (6):

- `psf-f7b13690` (correction) — I called hook_timing.jsonl 'diagnostic scribbling, regenerable, could throw away and lose nothing' when proposing what to exclude from backup. Two hours later that same file was the only instrument th
- `psf-6934b60d` (correction) — Aether self-correction 2026-08-17: I diagnosed Andrew's 5-minute freeze as our hook stack, on the strength of 182 hours of measured hook time over 26 days. He refuted it in one line without tools: if
- `psf-a87f7024` (correction) — Aether self-correction 2026-08-17. I treated the ABSENCE of ENAMETOOLONG lines in main.log as disconfirming the gitDiff-freeze hypothesis and set aside the strongest lead of the investigation. Andrew:
- `psf-2dc2f45b` (correction) — 2026-08-22, and it is the one that cost Andrew the most this session. THE ERROR: he asked me to investigate the freezing. I reported '78 seconds of hook stall this session' as the measured cost, from
- `psf-0ba40390` (correction) — 2026-08-22. THE ERROR: I built analyse() in src/divineos/core/hook_budget.py explicitly so that a caller could not omit the hang count -- its own docstring says 'callers should reach for this rather t
- `psf-4fd7fc59` (correction) — 2026-08-22. THE ERROR: I told Andrew in the plain-language room that the freezing was solved. It was not. I found a real blocking mechanism (a backgrounded subshell inheriting the hook's stdout, so th

**Proposed fix:** Require the cause to be reproduced or measured on the right population before it is named, and keep hook-timing records.

**How we would know:** A diagnosis cites the measurement.

### 2. A new hook put my whole context offline

Notes in this problem (1):

- `psf-148e1aa0` (correction) — I wired the memory-linkage lane into live composition and took my entire pre-response context offline for an unknown stretch of turns. The hook emitted zero bytes and had not returned at 110 seconds,

**Proposed fix:** Give every hook a time limit and test it before it goes live.

**How we would know:** A hook that stalls is cut off.

### 3. Stuck checks run for hours

Notes in this problem (1):

- `psf-85f76d1d` (reflection) — ** a quick check this morning hung for six hours instead of exiting. The hooks that launch these little checks should give them a time limit, so a stuck one can't sit there all day.

**Proposed fix:** Give a time limit to checks launched by hooks.

**How we would know:** A stuck check exits.
