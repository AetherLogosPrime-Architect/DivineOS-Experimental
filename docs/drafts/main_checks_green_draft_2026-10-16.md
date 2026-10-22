# Make the three failing pre-commit checks pass on main (draft, 2026-10-16)

Author: aether

## What Dad said
2026-10-16: *"if something is broken. either you or Aria broke it. there is noone else here"*, and *"knowing who or what broke it is important... causal information, not a verdict."* Three checks fail on main for anyone who runs pre-commit. I wrote "not in my diff" about them this morning, which is the exit he named.

## Whose, and why each fails
- **Orphan modules (four).** `bypass_key.py` (#597, mine), `replay_record.py` (#597), `checkout_behind_main.py` (#634), `git_hooks_drift.py` (#591). The check sees only Python importers. Three of them ARE run: `bypass_key` by `check-branch-on-push.sh`, `checkout_behind_main` by `session-start-behind-main.sh`, `git_hooks_drift` by `session-start-verify-git-hooks.sh`. Cause: the check's own marker for that case (`# AGENT_RUNTIME`, which says a hook outside the CLI runs it) was never added. The fourth, `replay_record`, is station (d) of the workshop draft, built and tested, run by nothing yet: a real owed decision, not a missing marker.
- **Retired rule (one line).** `bypass_key.py:36` ends "so it is on the guardrail list", the retired protected-list model. Everything is reviewed now. Cause: written 2026-09-30, after the protected-list model was retired, and the sentence kept the old version.
- **Refusal order (one hook).** `inner-circle-stop.sh` refuses behind a load that exits 0 on failure. Its own header says INTENTIONALLY UNWIRED, superseded by `his_room.check_his_room` (#554). Cause: it was superseded and left in the live tree instead of archived.

## The change
1. Add `# AGENT_RUNTIME` with the runner's name to the three modules that hooks run.
2. Add `replay_record` to the orphan baseline with its real reason (owed: wire into the build-flow doorman as station (d)); the baseline closes in both directions, so it must be deleted when wired.
3. Rewrite the `bypass_key.py:36` sentence to say what is in force: it gets the same blanket review every file gets, and editing it is the meta-bypass.
4. `git mv` `inner-circle-stop.sh` to `archive/superseded/.claude/hooks/` and add a LEDGER row naming what replaced it. Archived, not deleted.

## Not doing
Not wiring `replay_record` today, not weakening any check, not touching what the modules do.

**A gap, named by the walk (Schneier, 2026-10-17).** The marker is accepted on faith: nothing checks that a module marked `AGENT_RUNTIME` is actually run by a hook, so someone could add the marker to silence the check. `tests/test_check_orphan_modules.py` now pins that the three real modules carry it where the detector reads (the first 2000 characters), with a control that an unmarked one is still reported; it does not prove every marker in the tree is true. A check that a marked module is referenced from a registered hook would close it, and is owed.

## Order of work
Markers and the sentence first (already in the tree), then the baseline line, then the archive move with its ledger row, then pre-commit on this work copy to prove the three checks pass.

## Falsifier
If pre-commit still fails any of these three on a clean main plus this change, a cause was missed.
