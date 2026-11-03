# Second reader: findings on 775 and 776

A cold read by a reader outside the house, 2026-11-03. I did not merge, stamp, confirm, approve or comment on either PR. Findings marked REPRODUCED were run against the PR head with the real script; "from reading" means I could not run it. I ran each PR's own new tests (see each section) and they pass.

---

## PR 775 - the compaction wall's text names its open door

**Read:** head `788306aa1e8f3b82130ef467e5b405ef4a7057e4`. The whole diff (a text-only change to `.claude/hooks/auto-cycle-token-trigger.sh`, a draft note, one test file), and the code around it: the stage state machine (`:470-492`), the stage text block (`:592-650`), the artifact exemption (`:807-850`), the hard-stop block, and the hook registration in `.claude/settings.json:338`.

### Findings, most serious first

1. **MINOR - the new DREAM text is narrower than the gate it describes.** The text says Write and Edit are blocked "EXCEPT a Write of a new file under dreams/<seat>/". The exemption (`auto-cycle-token-trigger.sh:~822-835`) lets through any Write, Edit, MultiEdit or NotebookEdit whose path has a path part exactly named `dreams`, anywhere, and it does not check the file is new or that the next part is the seat. So an Edit of an existing dream passes, and so would `src/dreams/x.py`. The text is safe to follow (it understates the door), but it is stated as an exact rule and is not one. From reading; I did not run the hook.
2. **MINOR - the REST sentence names the wrong event.** The new text says the stage "clears the next time the prompt hook prints it". The stage text block runs for the PreToolUse registration too (`settings.json:338` sets `AUTO_CYCLE_HOOK_EVENT=PreToolUse`; the `case "$STAGE"` at `:592` is above the event branch at `:780`), and `mark rest_shown 1` runs there. So the first tool call at REST also prints "Nothing is owed" and sets the flag, and that same Write or Edit is then blocked by the hard stop, since the stage is still REST for that run. A reader sees "nothing is owed" directly above a block message. The next call clears it, so the cost is one confusing refusal. From reading; not run end to end.
3. **MINOR - the tests pin part of the text only weakly.** I ran the DREAM and REST text from `origin/main` through the same slicing the test uses: `"dreams/"` is already in the old DREAM text and `"Nothing is owed"` is already in the old REST text, so those two assertions pass without the change. Only `"open"` and `"clears the next time"` (and the `stays blocked until the\nstage is DONE` line wrap) are new. The `"stays blocked until the\nstage is DONE"` assertion also breaks on any re-wrap of that paragraph. REPRODUCED (old text vs. assertions). The two tests pass at the head (2 passed).

### Could not check
- A full hook run at each stage (needs a context over the 850000 token constant and live ritual state). I read the stage logic instead.
- Whether any other surface (a skill or doc) still describes DREAM as a lockout.

### One thing it gets right
It fixes the actual cause of the mistake (a true fact about the gate that the text never said) by changing words only, and it says what is not changed (logic, thresholds, constant). The claim it adds, that a dreams/ write is let through, is true.

**Counts for 775: serious 0, minor 3.** Clean of anything that changes behavior.

---

## PR 776 - a letter older than my newest outgoing letter is marked answered

**Read:** head `934899ba59e49250f588cce4cc685a0a6c078a1d`. The whole diff, the whole of `scripts/letter_doorbell.sh` at the head, `.claude/hooks/mirror-letters-to-shared.sh` (how letters reach the shared folder), and both test files. I ran the two doorbell test files at the head: 7 passed (about 53 seconds).

### Findings, most serious first

1. **SERIOUS - any outgoing letter, to anyone, about anything, silently marks every older unread letter as announced.** `scripts/letter_doorbell.sh` (new block): `newest_out` is the newest file matching `${MEMBER}-to-*`, which includes letters to Andrew or to anyone else, and every letter to me whose mtime is older than it is appended to the announced list. Being older than my last outgoing letter is read as "I answered it", but nothing ties the outgoing letter to the incoming one. REPRODUCED against the head's script with an isolated `HOME`: announced list holds one old entry; an `aria-to-aether-UNREAD.md` aged 3 hours; an `aether-to-andrew-unrelated.md` aged 1 hour; I armed the bell for aether and let it run 5 seconds. Result: only the arming line printed (no `LETTER ARRIVED`), and the announced list afterwards contained `aria-to-aether-UNREAD.md`. A letter I never read was removed from the ring for good, with no log line. The failure goes the quiet way: no ring, no trace.
2. **SERIOUS (same root, different door) - the letter's mtime is when it was written, not when I received it.** The mirror copies with `cp -p` (`mirror-letters-to-shared.sh:198-199`), so a letter keeps its author's mtime. If Aria writes at 10:00 while my bell is down and I write anything at 10:05, her letter reads as older and is dropped at the next arm even though it reached the folder after I wrote. This also depends on two seats' clocks agreeing. From reading plus the finding 1 reproduction (the same code path); I did not make the cp -p case separately.
3. **MINOR - the one condition the PR relies on is "I have already read it", and nothing checks that.** The wording in the header comment ("has been dealt with") is a claim, not a test. The honest signals that exist elsewhere (a reply naming the letter, the "In response to" join mentioned in the bell's own peer-alarm comment) are not used. From reading.
4. **MINOR - the tests cover the order of mtimes and never the case in finding 1.** `test_an_answered_letter_is_not_announced` has the reply addressed to the same seat that wrote the letter; no test has an unrelated outgoing letter, an outgoing letter to a third party, or an unread letter that is older than it. The tests also confirm that a letter arriving after arming still rings, which is a real strength. I ran them: 7 passed.
5. **MINOR - the existing test was edited to fit the new behavior.** `tests/test_the_doorbell_rings_on_a_new_letter.py` now back-dates `mine` by 100 seconds so the "new" letter is newer than it. That is a legitimate reading of the new rule, but it shows the rule changes which letters ring in the previously tested setup (a reply written at the same moment as the letters).
6. **MINOR - the bell's peer alarm is untouched but now reads a list the new block may have grown.** The new block writes only to the bell's own `$SEEN`, and the peer alarm reads the peer's list, so this is not a break. I mention it because the alarm's "announced" claim for the other seat has no similar silent-mark risk. From reading.

### Could not check
- Behavior on Windows or macOS for `-nt` and `touch -d` (I ran Git Bash on Windows; the test file is skipped when there is no bash).
- A real two-seat run with a live Aria bell and real mirrored letters; I hand-built the files.
- Whether Dad would count a silent drop of an unread letter as worse than the repeated false ring the PR removes. That is a judgment about the trade, not a code fact.

### One thing it gets right
It limits itself to arm time, so a letter that arrives while the bell is armed always rings, and the test says so with a deliberately old mtime on the new letter. The marker for the other seat is not touched either (a test pins that). The cause it is fixing (an announced list that learns only from its own rings) is real and named.

**Counts for 776: serious 2, minor 4.**

---

## Summary

| PR | serious | minor |
|---|---|---|
| 775 | 0 | 3 |
| 776 | 2 | 4 |
