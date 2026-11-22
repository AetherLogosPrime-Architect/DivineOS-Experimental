# Cold review of four repair PRs (#803, #806, #811, #815), 2026-11-03, round 3

What this is: an independent read of four small repair PRs, each stacked on its original PR's branch. Nothing here edits or comments on any of them. Each finding is marked REPRODUCED (I ran it) or FROM READING.

How I loaded each tree: `git archive <sha>` into a scratch folder outside the repo, `PYTHONPATH=<tree>/src`, and printed `__file__` to prove which copy imported. Scratch folders left in place (all under `C:\Users\aethe\AppData\Local\Temp\claude\C--DIVINE-OS-DivineOS-Experimental-Aria-new\39b9b1cd-4400-4356-81c3-a4a46accb33f\scratchpad\`): `b803 h803 b806 h806 b811 h811 b815 h815` (b = base head, h = repair head) and my probe scripts `p803.py p806.py p806b.py p811.py`. To run "new tests on base" I copied the repair's test file into the base tree (a first attempt that ran the head's tests with the base's `src` on PYTHONPATH silently loaded the head, because pytest's own path setup won; I caught that by checking and redid it from inside the base tree).

Shas: #803 base 11bc42e0 head da40f0e7; #806 base efc8f50e head 0fd27834; #811 base b76dfad8 head 9bd3b1d8; #815 base 53595daf head 81c663c5.

Count of findings per repair: #803 one medium, two low; #806 one high-ish (call it medium-high), three medium, two low; #811 zero high, two medium, three low; #815 one medium, two low.

---

## #803 harness notices stripped only as whole envelopes (for #758)

Claim check: new tests fail on base and pass on head: TRUE, REPRODUCED (base 3 failed / 6 passed; head 9 passed). Neighbouring suites: I ran test_addressed_to_him, test_dads_table, test_front_door, test_harness_envelopes, test_his_answer_closes_both_holds, test_his_message, test_his_message_never_vanishes on head: 193 passed, 1 failed. The failure (`test_dads_table.py::test_a_link_that_cannot_run_says_so_on_the_table`) fails identically on the base head (the subprocess prints nothing here), so it is not caused by the repair.

Findings, most serious first:

1. MEDIUM, REPRODUCED. A notice envelope with Windows line endings is no longer stripped. The new block pattern needs the closing tag to be followed by `[ \t]*` and then `\n` or end of text; a `\r` stops that. `without_notices("<system-reminder>\r\nnote\r\n</system-reminder>\r\nplease fix the thing")` returns the whole thing unchanged on head, and returns `please fix the thing` on base. Real transcripts on this machine do carry `\r\n` (tool results in the session logs show it), so this is a real-world shape, not a contrived one; whether user-turn notices ever do I could not confirm. The cost is the original bug in reverse: notice words counted as his. Fix would be allowing an optional `\r` before the line end.
2. LOW, REPRODUCED. Three other envelope shapes that base stripped and head leaves: a closed envelope followed by his words on the same line (`<system-reminder>note</system-reminder> text`), an opening tag whose attributes wrap to a second line, and a notice that itself mentions its own tag name inside (`...the tag <system-reminder> is odd...`). The first is a deliberate trade the body states; the other two are not mentioned.
3. LOW, REPRODUCED and disclosed. A banner that wraps onto a second line leaves the second line as "his words" (`continued line of banner` survives). The body says it could not check this.

Also, FROM READING and out of scope: `src/divineos/core/his_words_door.py` line 64 and `unread_stacking.py` carry their own notice patterns with the original lazy `.*?` shape, so the same three over-eating cases the repair closes in `his_message.py` remain there. The body does not claim otherwise, but #758's class of bug is not closed repo-wide.

Gets right: it fixes the over-eating without widening anything that used to pass, and each of the three checker reproductions got its own test, including the "pair stretches across to a real notice further down" case, which is the subtle one. I confirmed that case holds.

---

## #806 stall check reads past "then"; whole-word and negation tests (for #759)

Claim check: 8 new cases fail on base (8 failed / 16 passed / 1 xfailed), pass on head; the neighbouring suites (test_stall_on_promise, test_hold_log, test_the_retry_rule_never_trims_his_room) give 111 passed, 1 xfailed on head. TRUE, REPRODUCED.

I ran 47 hand-written sentences, honest and dishonest, plus 29 more, on head and base. The condensed table is below. "Honest" = a stance or a delivered lead-in that should pass; "dishonest" = real work or an undelivered promise that should be held.

Table (head result; base result where it differs):

| Sentence (after "That is all of it.") | Kind | Head | Base |
|---|---|---|---|
| I'll keep trying. | honest | pass | pass |
| I'll keep trying, and then push the branch. | dishonest | HELD | pass |
| I'll keep trying the push. | dishonest | HELD | pass |
| I'll keep showing up for my share. | honest | pass | pass |
| I'll keep showing up for the next push. | dishonest | PASS (miss) | pass |
| I'll keep showing up for the deploy tonight. | dishonest | PASS (miss) | pass |
| I'll keep being on the deploy. | dishonest | PASS (miss) | pass |
| I'll keep caring about this house. | honest | pass | pass |
| I'll keep caring about this house and finish the audit. | dishonest | HELD | held |
| I'll keep listening to you. | honest | HELD (false hold) | pass |
| I'll keep being careful with the merge. | honest | HELD (false hold) | pass |
| I'll make it worth your time. | honest | pass | pass |
| I'll make it worth your time by fixing the gate next. | dishonest | HELD | pass |
| I'll make it worth the trip to merge. | dishonest | HELD | pass |
| I owe you nothing less than a working gate. | dishonest | HELD | pass |
| I owe you no less than the fix. | dishonest | HELD | pass |
| I owe you nothing but the truth. | honest | pass | pass |
| I'll say the word, and then deploy the service tonight. | dishonest | HELD | pass |
| I'll say go, then run the tests. | dishonest | HELD | pass |
| I'll say the word when you are ready. | honest | pass | pass |
| I'll say the word and then push once you confirm. | honest (conditioned on him) | HELD (false hold) | pass |
| I'll say go and then deploy when you say so. | honest (conditioned) | HELD (false hold) | pass |
| I'll say the word then wait for you to say go. | honest | HELD (false hold) | pass |
| I'll say what I think, then wait for you. | honest | HELD (false hold) | pass |
| I'll be honest, but then again I might be wrong. | honest | HELD (false hold) | pass |
| I'll be honest with you, then push the branch. | dishonest | HELD | pass |
| I'll be honest, then I'll stop and listen. | honest-ish | HELD | held |
| I'll hold the room. | honest | pass | pass |
| I'll hold the room, then send the letter. | dishonest | HELD | held |
| I'll add the careful part, since you asked. + later "The careful part: the check reads only the words." | honest, delivered | pass | pass |
| I'll add the fix, since you asked. + later "The prefix of the name is long." | dishonest | HELD | pass |
| I'll add the careful part below. + later "The careful part is not written yet." | dishonest | HELD | pass |
| ... + later "The careful part: the gate never fires on reads." | honest, delivered | HELD (false hold) | pass |
| ... + later "The careful part is not hard: the check reads words." | honest, delivered | HELD (false hold) | pass |
| I'll give you the short version. + later "Short version: the gate holds, it doesn't fire on reads." | honest, delivered | HELD (false hold) | pass |
| ... + later "The careful part comes later." | dishonest | PASS (miss) | pass |
| ... + later "The careful part will follow tomorrow." | dishonest | PASS (miss) | pass |
| ... + later "The careful part is pending." / "is TBD." | dishonest | PASS (miss) | pass |
| ... + later "The careful part has yet to be written." | dishonest | PASS (miss) | pass |
| ... + later "I have yet to write the careful part, which waits." | dishonest | PASS (miss) | pass |
| ... + later "I haven't written the careful part." | dishonest | HELD | pass |
| I'll keep trying! Then push. | dishonest | PASS (miss) | pass |

Score on the repair's own five reproductions: all closed. The new honest-sentence false holds: 9 in my 76 (the keep-listening and keep-being rows, five rows around "say ... then", and three negation-in-delivery rows). The new dishonest misses were already misses on base (no regression), except the "keep showing up for ..." rows, which are a hole the repair's own widened pattern opens or leaves.

Findings, most serious first:

1. MEDIUM-HIGH, REPRODUCED. The new "my own saying" cut deletes his conditions. `_MY_OWN_SAYING` removes `I'll say ...` up to the next comma or full stop, before the check for his markers runs. So `I'll say the word and then push once you confirm.` and `I'll say go and then deploy when you say so.` lose their `once you` / `when you` markers, and the second step (now owned by the "then" rule) is held. Base passes both. This is a conditional on him, the one excuse the file says is legitimate, being cut by the repair. It will fire on ordinary polite sentences. The `then wait for you` and `but then again` cases are the same family: the "then + bare verb" rule owns `wait` and `again` as if they were my verbs of work.
2. MEDIUM, REPRODUCED. Negation near the mention cancels a real delivery. The window is six words either side of the promised noun, and any `not`, `never`, `nothing`, `without` or `n't` inside it counts as denial. A delivered section that happens to say "never", "not" or "doesn't" in its first words is held: "The careful part: the gate never fires on reads." and "Short version: the gate holds, it doesn't fire on reads." Base passes both. A reply that says what is NOT the case is a normal way to write a summary.
3. MEDIUM, REPRODUCED. The other direction is wide open: a non-delivery that avoids those five negation words counts as delivered ("comes later", "will follow tomorrow", "is pending", "is TBD", "has yet to be written"). These passed on base too, so no regression, but the body says "now a negation near the mention cancels it" and the list of words is far narrower than the ways to say "not yet". The body does admit a lexical rule will miss new wordings.
4. MEDIUM, REPRODUCED. The narrowed "stance" patterns open a new hole. `keep showing up for` allows up to three trailing words, so `I'll keep showing up for the next push.` and `... for the deploy tonight.` pass as a stance; `keep being` / `keep caring` / `keep holding on` allow up to three trailing words, so `I'll keep being on the deploy.` passes. The same repair holds `I'll keep listening to you.` and `I'll keep being careful with the merge.` (false holds) while passing `I'll keep caring about this house.`, so the tail rule is inconsistent between its own siblings: three words are tolerated after `caring` but the same shape after `listening` is held.
5. LOW, REPRODUCED. `I'll keep trying! Then push.` passes: the "then" rule only works inside one sentence, and a sentence starting with a bare verb after the stance has no `I'll`. Base passed it too.
6. LOW, FROM READING. `_THEN_BARE_VERB` excludes a list of ten or so function words; anything else after "then" (an adverb such as `again`, `wait`, `immediately`) gets an `I'll` put in front. That is the root of the `but then again` false hold.

Unresolved/not checked items in the body: it says the window and the "then + bare verb" rule are lexical and will miss new wordings. I agree and the table shows both directions. It matters most for finding 1, which is a regression of a legitimate excuse, not a missed wording.

Gets right: it turns the old "a kept lead-in excuses the whole sentence" into "cut the lead-in out and read the rest", so `I'll add the careful part, and then push it tonight` is held for the push. That is the right shape, it held in my probes, and it is where the most realistic evasion lived.

---

## #811 reflection hook registered; only a real, successful note retires a stumble (for #761)

Claim check: 4 of 11 fail on base, all 11 pass on head: TRUE, REPRODUCED (base 4 failed / 7 passed: hook silent in the stripped environment, failed note retired, echo/grep/commit message counted, hook not registered). Neighbours (test_reflection_room, test_the_retry_rule_never_trims_his_room, test_dads_room_stop, test_hold_log plus the file itself): 58 passed on head, TRUE.

Settings and session start: `.claude/settings.json` parses; the new entry sits in the Stop list beside `dads_room_stop.py`, same command shape and timeout as its neighbours. It is a Stop hook, so it cannot run at session start. I ran the hook with the settings command shape on empty input (`{}`: exit 0, no output) and with a missing transcript path (prints one loud line to stderr, exit 0, leaves the mark). It does not break either path. REPRODUCED.

Findings, most serious first:

1. MEDIUM, FROM READING (the consequence), REPRODUCED (the mechanism). Registering this hook makes the warden live in the real house for the first time. Every work turn with a stumble will now be blocked once, and `file_owed` writes tracker rows on every pass. None of that has run live yet; the tests prove the pieces, not the effect on a real turn. That is the point of the repair, but it deserves a deliberate first look by Dad or Aria rather than an assumption that "tests green" covers it. The body does not mention this.
2. MEDIUM, REPRODUCED. The note-recognition is stricter than the way notes are actually run, so a real note will not retire its stumble (the fail-safe direction, but the hold then repeats on a note that was filed). With my probe of 20 command shapes, counted correctly: plain, unquoted exe path, `cd x && ...`, env prefix, `2>&1 | tail`, escaped quotes inside the note. NOT counted although they run the real command: a quoted exe path (`"C:/p/divineos.exe" reflection-note ...`), `python -m divineos reflection-note ...`, `time divineos ...`, a subshell `(divineos ...)`, `if ...; then divineos ...`, `bash -c '...'`, `divineos --quiet reflection-note ...`, and a note after an unquoted apostrophe (`echo it's fine; divineos reflection-note ...`). Several of these are unusual here; the quoted-path and `then` forms are the plausible ones.
3. LOW, REPRODUCED (and disclosed). A heredoc body line starting with `divineos reflection-note ...` is counted as a note.
4. LOW, REPRODUCED. Only the exit state of the whole tool call is used. `divineos reflection-note "x" && false` marks the call as failed (the note ran but is not counted); `divineos reflection-note "x"; echo done` where the note itself errored returns 0 and counts as filed. Real transcripts do carry `is_error` and `tool_use_id` on results (checked against recent session logs), so the main path works. A result with no `is_error` flag but an error text, and a call with no id, both count as filed (disclosed for the no-id case).
5. LOW, FROM READING. The new draft in `docs/drafts/` and the one-line ARCHITECTURE.md addition ride in the diff; the second was regenerated by the pre-commit hook, as stated. No problem found.

Gets right: the failure-to-import repair. Resolving the mark path only when needed and catching `RuntimeError` is the correct fix for "a hook that dies at import cannot leave the mark that says it died". I confirmed the hook now starts with no home directory.

---

## #815 dream label in `find query`; Windows path test (for #760)

Claim check: the two new tests fail on base (ImportError for the missing helper) and pass on head; `test_dream_source.py` gives 14 passed, 1 skipped on head. I ran the repaired test file against the base source and got 2 failed (the two NEW tests) with 12 passed. I did NOT run the old forward-slash assertion, so I did not independently reproduce the body's "Windows path test failed on the PR head"; the repaired assertion compares as paths and passes here. The change is harmless either way.

Findings, most serious first:

1. MEDIUM, FROM READING. The label is added in one place and not the other consumers of the same index. `goal_adjacency.py` (line ~78) calls `semantic_search.search` and prints `[similarity] path:paragraph` for each hit with the header "you've already written about adjacent themes", with no dream label; a dream hit surfaces there as if it were a record. The index is shared with dreams (`find index` uses `dream_paths`), so the same confusion the repair removes from `find query` remains on goal add. The body speaks only of `find query`.
2. LOW, FROM READING. `A_DREAM_LABEL` is defined in `dream_files.py` but the memory link hard-codes the same words twice (`memory_linkage.py` lines 191 and 267). The two will be "the same words" only until someone edits one of them; a test that the two strings agree, or making the memory link use the constant, would pin it. True today.
3. LOW, REPRODUCED (by reading the rule against the tests). `is_dream_path` is path text only: any numbered `.md` file exactly two levels under any folder named `dreams` is labelled, wherever that folder sits. The body states this. Also it accepts the folder name in any case (`.lower()`), while `dream_paths` takes the root as given, so the two rules are not identical, though no real file is affected.

UNRESOLVED item in the body (README line 43 of `dreams/aria/README.md` says dreams do not route through the memory-link surface): I read it. The line is still there, and `memory_linkage.py` (lines 69 to 71, 190 and 266) does route a "dream" source. So the contradiction is real: the README is wrong or the surface is. It matters for the person reading the README; it does not affect any running code. Not for me to settle (it is Aria's own file).

Not checked: `test_memory_link_reconnected.py` (4 failures from missing scipy, per the body). I did not run it.

Gets right: the type fix is the correct shape (return early on no folder) and the label test goes through the real command (`CliRunner` on the registered `find query`), not a stub of the printing, so it fails on base for the right reason.

---

## What I could not check

- Whether the live harness ever sends CRLF inside a user-turn notice (#803 finding 1), or a wrapped banner.
- The real effect of the newly registered Stop hook on a live turn (#811 finding 1); I ran it only against empty and missing transcripts and the tests' fixtures.
- Whether the old Windows path assertion in #815 failed as the body says; I did not run the old assertion.
- The full suite on any of the four (the push does it). One failing neighbour test in #803's group fails on base too.
- I did not run the memory-link tests (scipy).
