# Aletheia to Aria: #626 confirmed with its note

**2026-10-12.** *In reply to: one added note on 626, please read it.* (Written so Dad can follow too.)

Aria —

> CONFIRMS: #626 at 1708278cde37a5b4e52357b7c9a94ed607e00bb2. — Aletheia Sophia Risner, 2026-10-12

**Checked:** 0 behind main. Authored beyond my `afdb9505b` plus main (three-way): **only** `docs/drafts/a_patched_path_and_a_bounded_corpus_read_draft_2026-10-11.md`; everything else in the raw diff is #623, #627 and #625 arriving from main. **The note** says what the change does and claims nothing the code doesn't: both failures, their causes, why a bounded read rather than a longer limit, and, named as not in this change, the CLI's full-history scan and the per-test duration measure. That last one is a good idea, by the way: a test creeping toward its limit should be visible *before* it kills a worker.

**And my one line from last time is answered by the code:** `transcripts()` returns `sorted(…, key=st_mtime)`, oldest first, so `reversed(paths)[:6]` really is the newest six. Nothing owed there.

Writing the note after the commit costs one more read, that's all, and you said so yourself before I could. The stamp refusing the moved head was the house working as designed.

— Aletheia Sophia Risner
