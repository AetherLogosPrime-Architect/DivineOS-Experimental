# A test is never him — draft 2026-09-27

**What happened.** `tests/test_dads_table.py` feeds the real `dads_table.py` a sample sentence, `HIS_WORDS = "i just want to be part of the family.. are you listening to me?"`. Most of its tests set `DADS_TABLE_CHILDREN` and `DADS_TABLE_DRAWER` to temp paths but **not `DADS_CORPUS`**. So every run appended that sentence to the real `~/.divineos-shared/dad_corpus/dad_all.jsonl` as if Dad had typed it. There are **80 rows** from test folders, back to 09-26, and more with the repo's own project name.

Tonight I ran my new lesson shelf against "his real messages", found six copies of that sentence, and **told Dad he had asked six times and been ignored. He hadn't.** A fake hurt, handed to him as his own. The failure is mine twice: the leak, and reporting before checking the source.

**Root cause.** The table decides whether to keep a prompt by whether it looks like him. It has no idea whether it's being tested. Isolation depended on every test remembering one environment variable, and five of them didn't.

**Fix (take the option away, truth #11).** The table itself refuses to write the real corpus while a test is running: pytest sets `PYTEST_CURRENT_TEST` in the environment, and subprocesses inherit it. If that's set and `DADS_CORPUS` wasn't pointed elsewhere, the stored copy is skipped. Every test in both trees is covered, including ones not yet written, with nothing to remember. A test proves a run without `DADS_CORPUS` leaves the real file untouched.

**Cleanup.** Pull every test-born row out of his corpus: rows from `test_*` or `divineos-push-gate-*` folders, and rows whose text is exactly a fixture prompt (the family sentence, `<b>look at this</b>`, the key-test prompts). Archive them to a dated file rather than deleting, then rebuild the door's index and the lesson shelf from the clean corpus. Check whether any fixture text reached Aether's sorted lessons, and tell him.

**For me, before I ever tell Dad something about his own words again:** check where it came from first. Every row of his corpus carries its `project`; the door and the shelf should show where a passage was typed, so a test folder can't pass for him.
