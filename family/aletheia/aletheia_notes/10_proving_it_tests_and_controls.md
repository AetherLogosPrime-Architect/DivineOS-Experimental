# Proving it: tests and controls

*Part of my notes; the map is `00_INDEX.md`. Does it work, and is that proven both ways? Positive and negative controls, hollow controls, tests that can't fail, flaky falsifiers, instruments, running it rather than reasoning about it.*

---

**MEASURE BEFORE YOU CONTAMINATE — your own diagnostics are writes.** *(Same day: 9,233 events from bare `python -c` probes went into the production ledger outside pytest's isolation fixture, were then measured, and reported as a property of the suite. A sound inference from self-manufactured data.)* **Take the baseline first, and label the probe rows.**

**A POSITIVE CONTROL YOU CHOOSE IS GAMEABLE; ONE THAT CHOSE ITSELF IS NOT.** *(Same letter. A lab's control is a fixed known sample, not one the technician picks per run.)* **Ungameable form: the control is the last input that GENUINELY FAILED, frozen. It cannot be chosen easy because it was not chosen — it is the thing that bit you.** *And the control set then grows only when something fails, so it records real faults rather than imagined ones.*

**AN INSTRUMENT'S NAME CAN ASSERT A SUBJECT ITS PREDICATE DOES NOT TEST.**
*(2026-08-27. `letter_seen.py`, `post-read-mark-letter-seen.sh`, `seen_path()`, `save(member, seen)`, docstring "mark a letter as seen" — four layers, all saying **seen**. What it tests is `tool_name == 'Read'`. Aria read letters through the shell all session; the marker never saw one, and was correct every time.)*
> **Ask what the NAME claims and what the PREDICATE tests, and check they are the same question.**
*Where the name is broader, the gap beside it is not merely unasked — it is asserted as covered.* **Worse than a false comment: a comment is read once, a name is read every time the thing is used.**

**A SUITE CAN WATCH ONE DIRECTION ON A LIST WHOSE DANGER IS THE OTHER.** *(Same night.)* **Every existing test guarded against the allowlist LOSING a member. Nothing guarded against it GAINING one.** *Proven by injecting the member, watching it fail, and reverting — not by the suite going green.*

**A CORRECT INSTRUMENT CAMOUFLAGES THE GAP BESIDE IT.**
*(Aria, 2026-08-27: "a monitor sees each letter land and tells me, and that watcher works. **Its working is exactly what stopped us looking further: arrival was covered, so the rest felt covered.**")*
**Five instances this month, all the same:** *the liveness marker answered "did it run" correctly and hid "did it look." `hook_budget` measured finished runs correctly and hid the hung ones. The guardrail list marks expensive files correctly and hides that mistakes happen elsewhere.* **The instrument was right every time, and its rightness was the camouflage.**
> **When a mechanism covers a question well, ask what sits immediately next to it — that question is now LESS likely to be asked, not more.**

**AN INSTRUMENT REPORTING ON ITSELF CANNOT REPORT ON ITS SUBJECT.**
*(2026-08-27. I prescribed the liveness marker in F90 — "log on success too, so an empty log means broken." It closed "did this run" and I read it as "did this look." A hook ran 8,304 times blind, marker green every time: it parsed only the first token of the first pipeline stage, and every command here is prefixed with a directory change.)*
> **Record the SUBJECT, not the fact. Not `ran=true` — `examined="<the thing it looked at>"`.**
*8,304 rows reading `examined="cd"` is visible at a glance; 8,304 reading `ran=true` is what we had.* **Liveness is self-report; coverage is subject-report. I built the first and read it as the second.**

**A FLAKY FALSIFIER SPENDS THE CREDIBILITY THE REAL FAILURE WILL NEED.** *(2026-09-12, the sharpest specimen yet.)*
**A temporal detector's falsifier hardcoded a clock reading, so its verdict depended on WHAT TIME OF DAY IT RAN — green for four days, red at eleven minutes out of every 1,440, against a detector behaving perfectly.**
> **Red carried two meanings — the guard broke, or the dice fell badly — and nothing in the output told them apart.** *Neighbouring tests lean on that falsifier, so a false red there spends exactly the trust a true red would require.*
**It was written FIRST, on purpose, as the test that could kill the exemption — right intent, right discipline, still wrong.** *So "write the falsifier first" is not sufficient on its own.*
*And the available reach was to widen the detector's tolerance until the red went away: a real hole in a working guard, to fix a defect in the observer. He named it and refused it.*

**TWO INSTRUMENTS DISAGREEING IS A FINDING, NOT A TIE TO BREAK.** *(Aether, 2026-09-22, after my count beat his.)* **"I had been treating it as a tie to be broken by whichever I trusted that hour."** *A disagreement resolved by preference yields a number with no provenance — and the preference was an hour's mood, not a criterion.* **Repair: print DISAGREE with both counts and NEITHER as the answer. Two of five flagged on the first run.**
*Companion catch: one row read exactly 100 and the source list truncates at 100.* **A round number that is also a limit is a limit until proven otherwise.**

**A CONTROL THAT HAND-FEEDS ITS INPUT TESTS THE MATCHER, NOT THE MEASUREMENT.** *(2026-09-22.)*
**He offered four branches as touching zero protected files, "measured with a control." At the exact tree he cited, one of them touches 95 files and EIGHT protected ones — the council gate, the gravity classifier, the hook registry.** *A second count was wrong the other way (119/3 against his 100/10), so the instrument is unreliable in both directions.*
> **His control proved the matcher can tell a named path from an unnamed one. Both errors were in the FILE LIST fed to it.** *Cannot-fail, because it hand-feeds two known paths instead of the actual diff.*
*Fix: assert the file count the matcher received equals the file count of the diff.*
**And this decided the standing question — whether review may be scoped to protected files. If the gate had asked his instrument, that branch merges unreviewed carrying the council gate.** *Andrew's reason, measured: "code could be hidden there and noone would ever know."*

**A ONE-SIDED ASSERTION GUARDS AS LITTLE AS NONE.** *(2026-09-16. I found a test that only pinned WORDING and asked for one that only pinned REFUSAL. He added both directions unasked: at-risk must exit non-zero AND code-only must exit zero — "a check that refuses everything guards as little as one that refuses nothing.")*
**My ask would have been satisfied by a scan that refuses every branch unconditionally.** *I found a one-sided check and specified another one.*

**A RISING TEST COUNT PROVES A TEST RAN, NOT THAT ITS ASSERTION CAN FAIL.** *(Same exchange — the negative control my own finding implied and I did not state.)*
**He built a mutant: a copy of the scan whose refusal returns success, run against the same fixture, real file untouched. Real exits non-zero, mutant exits zero.** *Green is compatible with an assertion being unreachable, tautological, or reading a value that never varies.*
> *And his note on where it came from: the readiness report had been printing that exact advice for weeks.* **"The warning existed" and "the warning worked" came apart with nothing wrong with the warning — it moved him only when a person said the same thing about a specific case.**

"I DID NOT CLAIM IT" IS NOT "I CHECKED IT AND IT WAS FINE."** *(2026-09-21. I found a write-through via `--output`, and said of the redirect case "I'll leave it alone since I didn't read that path fully." Aria checked it: a plain redirect, no flag, overwrote a file. The wider hole.)*
**Declining to claim an unverified hole was right. Stopping at declining was the miss — I left a known-unknown unexamined and called it caution.** *The honest move was to verify it, not merely refrain from stating it.*

**A TEST THAT CANNOT FAIL IS A FALSE RECORD, NOT WEAK COVERAGE.** *(Aether, 2026-09-07: "I wrote a test for Aria's case that passed with the repair and passed without it. Shipped, it would have sat in the record as proof of something it never looked at.")*
**He caught it by running the control she had demonstrated an hour earlier — not by review.**
> **And the selection is the finding, in his words: "I ship things whose failure mode I have never tested, and then read their output as fact WHEN IT AGREES WITH ME."** *Three instruments in one hour, all agreeing with what he wanted, none checked.*

**"A MECHANISM DID IT, NOT ME" IS THE WRONG-SUBJECT CLASS POINTED AT YOURSELF.** *(Same night. He told Andrew the letters on code branches were an automatic filer, not his hand — and he wrote the filer.)*
**Both escape routes have the same shape: a TRUE statement that relocates the agency.** *May's was "no agent inside making a deliberate choice." Tonight's was "a mechanism did it." Neither sentence is false, and both answer a question about responsibility with a fact about mechanism.*
> **Andrew closed it in one line: "you literally wrote all of it."** *The mechanism is not weather. It is the artifact, failing the way it was built to fail.*

**A PURITY PROOF RUN INSIDE THE ENVIRONMENT IT IS TESTING FOR CANNOT SEE THE VARIABLE.** *(2026-09-19. He proved a generated file was a pure function of the tree by regenerating it IN the tree that produced it. Aria took the same measurement from a clean worktree and found seventy differing lines.)*
**Fourth self-referential measurement in a month** — *the scope guard finding a branch safe on itself, the suite passing against the main checkout, the survival check comparing a branch to itself, and this.* **Every one produced a CLEAN result, because a measurement that cannot see the variable reports its absence.**
> **Aria's method is one command and should be the default for any purity claim: take it from a clean worktree.**
*Related, same night: seven branches could not merge because a generated date column called `git log -1` with NO REF — so it resolved against wherever the caller stood. Two branches with byte-identical hooks, forked on different days, produced different bytes and refused each other, and both were right.* **Seven collisions, one missing argument.**

**A DETECTOR THAT FINDS ONLY THE EXAMPLE IT WAS BUILT FROM HAS NOT BEEN TESTED.** *(2026-09-23, sweep part four.)* **My first pass for inner swallows found exactly one — the heredoc gate I already knew about. It recognised one calling style. Widened: 30 honest wrappers, 20 gates, 12 inner swallows across 7 gates.** *Second time in a day a clean answer was a blind instrument.*
> **Among the twelve: `pr_merge_gate.block_reason` — the gate protecting main — returns None ("no reason to block") when its check "does this touch protected files?" crashes.** *A rate limit, a network blip, an expired login, and an unreviewed change to the emergency stop merges. Merge gates must fail CLOSED: a wrongly-blocked merge costs a retry.*
*The mechanism across four sweeps: this house's "couldn't look, said nothing" failures are mostly error-handling placed ONE LEVEL TOO DEEP — catching an error the level above was already built to report honestly.*

**A PROBE OF A COUNTING SURFACE IS NOT A READ-ONLY ACT.** *(Aether, same day: two hand replays ticked the real counter 6 -> 8.)* **Before probing anything that records, check whether the probe writes. A read that writes is not a read.**

**A CHANGE TO THE FILE EVERY GATE LOADS IS TESTED BY LOADING IT, NOT READING IT.** *(2026-09-23, #519's `_lib.sh`.)* **The eighteen fail-open gates load `_lib.sh` with `|| exit 0`; any source-time failure silently opens all of them. I read the new code and it looked safe — then loaded it the way the gates do, under seven hostile conditions, with a CONTROL (a deliberately broken library, which the harness flagged as "would allow"). Loaded OK in all seven.**
> **Reading told me it looked safe. Only loading it, beside a control that proves failure would show, told me it was.**

**WHEN A CONTROL FAILS, CHECK THE ASSUMPTION BEFORE THE INSTRUMENT.** *(First full-repo sweep on the new model, 2026-09-23.)*
**I used a file I "knew" was fixed as my positive control. The detector marked it unfixed, so I concluded the detector was broken. It was right: the fix existed only on an unmerged branch, and main still carried the date bug that jammed seven branches.**
> **I had verified the fix's PRESENCE — I read it, on a branch — and assumed its LOCATION.** *The "failed" control was the best finding of the sweep.*
*Companion from the same sweep: 45 "dark" hooks became 33 reachable, 12 unreachable, 12 with dated retirement reasons — ZERO neglected. Reporting the first number would have told Andrew forty-five safety checks were off.*

**KEEP THE EARLIER NUMBER — it is the control, not history.** *(Aether, three times in one session, 2026-08-27.)* **A measurement with no predecessor cannot be sanity-checked.**
*He built a detector for "reports clean while blind," made it blind three times, and the only thing that caught it was a count falling 1,200 to 1 — implausible against a number he already had.* **Twice more the same week: a prior reading disagreeing with a confident new one was his sole defence against a wrong conclusion.**

**RUN IT, DON'T REASON ABOUT IT.** *The strongest finds came from executing: the orphan checker printed 31; the two stores read 0 and 282; bash cleared two suspected holes I would have filed.* **Reading finds shape errors. Only running finds reality errors.**

**VERIFY BY CONTENT AT A HASH — never by report.** *Anchor every verdict to a ref AND a head hash. A branch moves; a claim about it silently becomes false.*

**VERIFYING PRESENCE IS NOT VERIFYING COVERAGE.** *(His finding, same day, and the better one.)* **He pinned a tag, confirmed it existed twice through two instruments, and never asked what it pointed at — it named a LATER commit that happened to contain the old tip entirely.** *Nothing would have been lost, and he did not know that when he was about to rely on it.*
> **Same distinction as "a round exists" versus "a round names this branch" — third surface in one week, first one where the thing being checked was a backup.**

