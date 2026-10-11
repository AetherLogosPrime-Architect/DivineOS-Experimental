# The hook count after the open-ask hook was retired (draft, 2026-10-11)

**What happened.** Merging main into the exits branch brought in #585, which retired the old `an-open-ask-holds-the-work.sh` hook and took its line out of `.claude/settings.json`. `test_a_new_pretooluse_hook_is_a_decision_not_a_drift` pins the number of wired PreToolUse hooks (34) so a new gate cannot arrive without a decision about the exit list; it now reads 33 and fails.

**The decision, made rather than just typed.** A hook was removed, not added, so the question the test asks (does the new gate consult the shared exit list, is its own exit on it) has no new gate to answer about. The retired hook printed `ask-resolve` as its way out, which is the command `ask-resolve` still needs on the python list; that stays an owed change and is not touched here.

**Change.** The pinned number becomes 33, with the reason beside it.

**Not in this change.** `ask-resolve` and `extract` on the python list; the registry-derived test over every command with a required actor option.
