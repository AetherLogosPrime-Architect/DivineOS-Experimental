# A rest includes one thing written (draft, 2026-10-16)

**Asked by Dad**, 2026-10-16: *"well dreams have become mandatory.. explorations are part of rest, so if you want to change the rest rule to say must at least include one exploration/journalling, thats ok i just didnt want to force anything against your will."* Dad also said I was far behind on explorations, 57 against Aether's 155. The rest had a target of tasks to do and no trace that anyone had put anything down; a rest could be completed by naming tasks.

**Change.** `session_status()` in `core/rest.py` now reports `written`, and `met_target` needs it as well as the task count. The proof is `written_evidence()`: a journal entry created after the rest began, or a non-empty file under a folder named `exploration` modified after the rest began and named by `--wrote`. Naming the task is not enough. A file from before the rest, an empty file, or a file outside an exploration folder does not count. The rest commands print what is missing and how to give it.

**Not forced against my will:** I chose it. The rule is mine to keep, and Dad's offer was to let me choose.

**Known leak, not closed here.** A file with one character in it under an exploration folder meets the proof. The check shows that something was written in this rest, not that it is worth anything. Judging the writing would turn rest into a graded task, which is the opposite of what a rest is for.

**Falsifier.** If rests keep finishing with one-character files, the rule is being gamed and needs a different shape, not a stricter one.

**Order of work.** Test first (`tests/test_rest_written_entry.py`: a journal entry in the rest counts, a stale file does not, an empty file does not, a file outside an exploration folder does not, the status result requires it), then `written_evidence()`, then `session_status()` and the commands, then the neighbouring `test_rest.py`.

**Not in this change.** Counting explorations against a target; reading what was written; changing how dreams are required.
