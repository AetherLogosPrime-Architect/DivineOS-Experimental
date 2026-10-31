---
name: council-log-semicolons-split-findings
description: "Mechanics of `divineos council log` that cost me several rejected attempts on 2026-10-07 - a semicolon inside --finding splits it into separate findings, so the last segment is read as the lens's whole finding and fails the 30-token minimum; each lens also needs a recent real `council walk` trace (45 min) and a loaded methodology."
metadata:
  node_type: memory
  type: reference
  originSessionId: 4a7d6a79-a3cb-46f7-ba1d-aa44fb7e7578
  modified: 2026-10-07T19:30:08.453Z
---

`divineos council log --finding 'Lens=text'` treats a semicolon as a separator between findings (its own help says to keep semicolons out of the text). I wrote long findings with semicolons and got "finding is too short (24 tokens < 30)" because only the segment after the last semicolon was counted for that lens. Commas fix it. The `--synthesis` text must also name at least two lenses and be 50+ tokens.

Other mechanics that cost time:
- A lens needs `divineos mansion council --show <lens>` loaded in this window, then `divineos council walk --edit <fp> --lens <L> --problem ...` with a typed reflection on stdin (use printf, not a heredoc with escapes), then the log. The trace expires after about 45 minutes.
- Findings must carry a keyword from the lens's own question list; the walk output prints the allowed words.
- An identical record for a second fingerprint is rejected as a copy; write distinct text, or use `--scope` naming the other files.
- `git add ... && git commit` as one line is fingerprinted as `bash:git add`; run the add and the commit as separate commands.
- Do not import `divineos.core.question_hold` at the top of a test file: it fixes the board path at collection time and breaks `test_question_hold_own_seat`. Import inside the test.

Why this note exists: Dad told me the walk is a matter of judgment (not for a one-line change) and the per-edit ceremony is a known mismatch with his protocol. Until the change-grading assessor lands, these mechanics are the price of any edit I do not bypass.

Related: [[dad-most-corrections-are-lessons-bars-only-in-building]], [[walk-the-council-where-dad-can-see]].
