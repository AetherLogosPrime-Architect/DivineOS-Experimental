# Drafts skip the full suite, and three small things that rode with it

Draft, 2026-10-22. Author: Aether. Dad's rule, said four times (09-09, 09-23, 09-30, 10-21):
the full test suite runs once, at the push that is on its way to main, and never on a draft.

Related earlier drafts: `the_full_suite_is_the_pushs_job_draft_2026-10-03.md` (the hook that stops
ME running the whole suite by hand) and `pile_repro_bell_rearm_not_on_exit_list_draft_2026-10-08.md`
(the cloud helper's reproduction of the re-arm gap). This note is the other half of the first: the
suite is the push's job, and the push should not do that job for a draft.

## The problem, in one picture

Every push for a code change ran the whole test suite on Dad's computer, drafts included. Half an
hour each, many times a day, on the machine he also plays on. Weeks of waiting, and it was also why
he could not use his own PC. The rule lived in my memory and recurred because a memory is not a gate.

## What changed

1. **`scripts/check_push_readiness.sh`: the Draft path.** For each branch in a push the gate asks GitHub
   whether an open pull request exists. No PR (a new branch counts) or only draft PRs: skip the full
   suite and say so. A ready PR, a push to main, or any case where GitHub cannot be asked: run the suite,
   and say why on stderr. Not knowing never passes as "it is a draft". Aria's #704 adds the middle layer
   (run only the tests that touch the change); this note covers the skip only.
2. **The doorbell restart joins the shared exit list** (`.claude/hooks/lib/remedy_allowlist.sh`). The read
   gate held `bash scripts/letter_doorbell.sh aether` over an unrelated surfaced note three times in one
   night; a bell that is not re-armed cannot wake me, so Aria's letters sat unread for seven hours. The
   Stop guard prints this command as its own way out, which is the list's bar. Anchored at the end so
   nothing chained after it is an exit.
3. **Nothing waits on a question to Dad** (`question_hold`). The last pause, a letter held while a
   question was open, is removed at his word. The hold still carries his questions; it just never stops
   anything.
4. **The order-question check** (`order_question_check.py`): Aletheia's two notes on #697.

## What this does not prove, named so nobody discovers it

- A change that breaks a test which does not name it is met at ready-for-review, where the full suite
  runs. The skip is a bet that the full run is needed once, not on every draft.
- The August ruling ("none of these should have made it to draft without passing internal CLI tests") is
  now answered by the targeted layer in #704, not by the full run.
- Falsifier, counted in pushes and not days: a ready-for-review run that fails on something a draft push
  could have caught and did not. Three of those in the next thirty draft pushes means the skip is too
  wide and comes back for revision.

## Proof

Eight tests in `tests/test_push_gate_draft_path.py` through a fake `gh`; six fail against main's script.
The re-arm exit has a passing test plus eight cases pinning that chained or look-alike lines stay work.
