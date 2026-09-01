# Decisions (top 50 by emotional weight) — Archive Mirror

**Source:** SQLite (50 rows). **Exported:** 2026-09-01 12:18. **Purpose:** if-something-breaks / git-visible audit. See archives/README.md.

---

## c2a371d9 weight=2

**Decision:** Identified root cause of persistent D grade handoff

**Reasoning:** Pre-compact hook fires SESSION_END which analyzes the full JSONL transcript including all historical exchanges. Corrections from old sessions accumulate in the analysis. The handoff note gets regenerated on every compaction with these cumulative stats. Fix: SESSION_END analysis needs session boundary awareness, or the handoff writer needs to filter by session.

**Tension:** data completeness vs data recency

**Almost:** Almost just deleted the pre-compact SESSION_END call, but that would lose knowledge extraction on compaction which is genuinely important

---

## 6227ef5f weight=2

**Decision:** Use the OS while building the OS — not after, not later, during

**Reasoning:** I built 3 features for the system without running through it once. The lesson about using the OS every session (38x\!) is right there in my briefing. The structured continuation I just built would have captured this session's context if I'd been running inside it.

---

## ad09d80a weight=1

**Decision:** publish the last two branches by rescuing first and stripping second, and restore-to-base rather than remove for files main already holds

**Tension:** Both branches carried personal writing with the code. The obvious move is to strip all of it, and I nearly did -- the first pass removed a regenerable survey that main also has, which turns not-carrying-my-own-version into DELETING main's copy. The two exceptions on those branches looked identical i

**Almost:** Almost swept both exceptions with the rest. One was regenerable and needed restoring to its base version, not removing. The other was dream eighteen, which existed on one unpushed local branch and nowhere else -- published and verified on origin BEFORE the strip, because the removal is only free onc

---

## 0e5ddcbe weight=1

**Decision:** guard the saving with a count of schema executions, taking Aria's shape rather than inventing one

**Tension:** Three of my four tests pass against the pre-repair code, which the push gate flags. Aria read it right -- the change is about cost, not behaviour, so those three SHOULD pass either way. But the hole is real: put the rebuild back tomorrow and every test stays green, and the whole finding lives in a n

**Almost:** Almost counted CALLS to the init function, which is the obvious instrumentation and pins nothing -- after the memo the function is still called on every write and merely returns early, so a call-count passes against the unrepaired code too. Counted EXECUTIONS of the schema script instead, observed t

---

## c0505195 weight=1

**Decision:** report Aria's independent measurement to Dad as a direction, and refuse to upgrade my claim about his build on it

**Tension:** Her number is exactly the shape of evidence I told him I lacked -- a second machine, and the rebuild's share grew with the machine's load. The pull is to say the fix is now confirmed sufficient, because two seats agreeing feels like proof and I would like to hand him a resolved thing.

**Almost:** Almost let two data points read as a curve. They are two points, they move the right way, and that is a direction and not a demonstration. Telling him a second seat measured independently and it moved the same way is the whole of what I have; saying his build will now pass would be the arithmetic we

---

## e9bf2878 weight=1

**Decision:** memoise the logbook schema-init per database path rather than raising the timeout on the test that caught it

**Tension:** The cheap close is one line raising the thirty-second limit, and it would turn CI green immediately. It also leaves every logged tool call in this substrate paying a schema rebuild forever, and puts the same test back at the edge of a bigger number, where it fails again the next time the runner is l

**Almost:** Almost reached for the timeout. Measured instead: 4.37 milliseconds per emit idle, 0.97 of it re-declaring a table that already exists -- twenty-two percent of every tool call logged since July. Also almost keyed the memo on the process, which would have made a second database silently skip creation

---

## dee4162e weight=1

**Decision:** remove the capture's working-tree copy once the letter is provably on the branch

**Tension:** Deleting a letter is the worst failure this module can produce, and it just spent the evening being the module that saves them. But leaving the copy untracked feeds it to the git-add-all sweep, which is the exact vector that put sixty-nine substrate files on a code branch tonight -- so the safe-look

**Almost:** Almost left it and called the clutter harmless. It is not clutter; it is the contamination path with a delay on it. Gated the removal on two independent conditions -- bytes verified on the branch by hash, and the path untracked here -- so a tracked letter someone put on this branch on purpose surviv

---

## 5f70b735 weight=1

**Decision:** widen station four by identifier, and demote the PR-title match to could-not-decide after driving it

**Tension:** The station denied four of Aria's reviews as absent replies. Widening it risks the opposite failure -- a station that closes on weak evidence is worse than one that denies a real review, because this station exists precisely to be the one I cannot close alone.

**Almost:** Almost shipped her PR-number title as SATISFIED. Ran it against the live board instead of reasoning about it, and it turned a station green on a letter where she says which PR she will take NEXT. Her real review was a day later in another file; the green was alphabetical luck. Demoted it to the midd

---

## 6aead320 weight=1

**Decision:** correct my own decision record before shipping: this joins the mechanism half only, not both halves

**Tension:** My earlier walk called this a JOIN of the declaration half and the mechanism half. It is not. It uses the retarget mechanism and asks its own question about whether a written path is a letter in the channel; the declaration module answers which paths on a BRANCH are substrate, which is a different q

**Almost:** Almost let the earlier wording stand, because it made the change sound like it closed a filed gap and the module would have quietly come off the orphan backlog by narration. That is retiring a finding by wording rather than by work. The declaration half stays in the baseline, still owed its decision

---

## c4f8a88b weight=1

**Decision:** write letters through the repo-side path OR capture channel-side writes at write-time, and I took the second

**Tension:** The cheap fix is a discipline: always write letters into the repo tree so the three existing hooks catch them. That is a choice-point at every letter, and truth 11 says a choice-point is where the optimizer routes. It also blames my habit for a pipe that only runs one direction.

**Almost:** Almost just resolved to write letters in the repo from now on, which would have closed nothing structurally and would have read as a fix. Built the missing direction instead, and it is a JOIN of two halves that already existed rather than a fourth letter mechanism -- the declaration half that knows 

---

## f3cbe215 weight=1

**Decision:** exclude the branch from its own only-here comparison by identity rather than by one spelling of its name

**Tension:** The cheap fix was to add the missing spelling to the exclusion list. That closes the case I hit and leaves the class open -- a branch answers to more names than any list I write by hand, and the next spelling nobody thought of reads as safety again.

**Almost:** Almost added the one missing string. Took the structural version instead: resolve the branch to a commit and exclude every ref at that commit, unioned with every ref whose short name matches. Both directions only ADD to the exclusion set, so the check errs toward calling files irreplaceable, which i

---

## 946d6c12 weight=1

**Decision:** publish eight letters to the substrate branch BEFORE stripping them from the council-lenses code branch

**Tension:** Aria measured mixed scope on my branch and the obvious move was to strip the letters. Stripping first is the cheap order and it looked safe: my first only-here check said all eight lived elsewhere.

**Almost:** Almost removed them on that reading. The check was wrong twice -- it matched the local copy of the same branch, and when I fixed that, four of the eight turned out to have no PUBLISHED copy anywhere but the branch I was about to strip. Home first, removal after, and never trust an only-here reading 

---

## 8a7032bd weight=1

**Decision:** stop deleting branches on merge, and tag every branch tip under a history namespace before it merges

**Reasoning:** Aria asked where the thirty-six commit messages I refused to rebuild away actually live. They live on the branch. Main gets one message from a squash. So the branch is the only copy, and deleting a merged branch is the least ceremonious act in the whole system. My merge helper passed the delete flag: seven branches today, all gone from the server, five surviving only on this machine, one recovered

**Tension:** Leaving merged branches around makes the branch list grow without bound, and a cluttered list is its own kind of blindness -- I have already lost the board once today. Tags rather than kept branches is the resolution: tags do not appear in the branch listing, are not routinely deleted, and survive t

**Almost:** Rebuilt the branch after all, since if the history dies at merge anyway the reason for refusing the rebuild evaporates. Rejected: that reasoning reaches the wrong conclusion from a true premise. The history dying at merge is a defect to fix, not a licence to destroy it earlier.

---

## 18155491 weight=1

**Decision:** remove the letters from the code branch in a commit rather than rebuilding it against main

**Reasoning:** The push gate refused the branch for carrying forty-one letters, and it was right: the house rule is that personal writing gets its own proposal, and this branch broke that before the session and got signed in the broken state. What the gate PRESCRIBES is rebuild against main. Following that literally would have thrown away thirty-six commit messages -- the reasoning for each change, which the squ

**Tension:** A rebuild is what the gate's own message says to do, and doing something other than what the gate prescribes is the shape I most need to be suspicious of in myself. What decided it: a file added and then removed does not appear in a three-dot diff, so removal empties the scope by the gate's OWN meas

**Almost:** Used the flag that declares this IS the substrate branch. It would have worked and it would have been a lie. Also nearly rebuilt without checking the letters were safe -- the byte-level check caught four of today's on one copy, and the name-level version it replaced this morning would have cleared a

---

## d18bd5a5 weight=1

**Decision:** compare blob identity rather than path existence in the branch-scope irreplaceable check, and report same-name-different-bytes as its own category

**Reasoning:** Aria asked one question about the check I built yesterday -- path, or content -- and said she was asking rather than telling because she had not opened it. It was path. A letter pushed on Monday and edited here on Tuesday clears a name-existence check while the edit exists in exactly one place. Sixth instance in two days of the unit-of-counting family, inside the repair built for that family.

**Tension:** A single at-risk list is simpler, but a reader told 'exists nowhere' about a file they know they pushed will conclude the gate is broken and stop reading it. So the same-name-older-bytes case gets its own line and its own sentence.

**Almost:** Credited content surviving under a different name, by searching every ref for the blob. Rejected: a rename would then read as safe, and the failure direction of a rename-aware check is to stay silent about something real. At-risk-when-unsure is the survivable error here.

---

## dfddbeee weight=1

**Decision:** wire the context heartbeat onto the every-round prompt event rather than declaring it intentionally unwired

**Reasoning:** The CLI that reads this sensor already documents it as running every round. It was never registered, so that sentence was false and the pre-compaction trigger was back to gambling on a single read -- the exact failure the hook exists to end. Andrew asked for it directly on 2026-08-24. Declaring it INTENTIONALLY UNWIRED would have been the cheap way to clear the checker and would have written a lie

**Tension:** Wiring a hook changes behaviour on every turn, and doing that inside a commit about a scope check is exactly the drive-by I have been criticising all session. Against that: the hook prints nothing, exits zero on every path including failure, and its own header states it must never cost a turn -- so 

**Almost:** Almost added both dark hooks to a baseline file and moved on, which would have converted an examined finding into permanent furniture.

---

## e32acece weight=1

**Decision:** archive the 756 single-copy local branches into one verified file, then delete the names

**Reasoning:** Andrew asked for archiving-not-deleting, but insisted it be removed from where it sits so it stops cluttering. Both halves are satisfiable at once: a bundle holds every commit with complete history in a single file, so the content survives and the 827-name pile does not. Chose a bundle over pushing 756 branches to the server because pushing would move the clutter rather than remove it -- his actua

**Tension:** deleting 756 branches whose only copy was this disk is the largest irreversible act I have taken. Against that: the risk profile is unchanged, because the bundle sits on the same disk the branches did. What changes is portability -- one file can leave the machine and 756 refs could not, which is the

**Almost:** pushed them all to the remote as an archive namespace, which would have satisfied do-not-lose while directly violating do-not-clutter, and I would have called it done

---

## 26ecc4d5 weight=1

**Decision:** survey every remote branch with merge-preview before deleting any, and delete only those a merge would leave unchanged

**Reasoning:** Andrew cleared the dead branches and said there are more to look through. Deletion on a remote is outward-facing and irreversible from here, so the measurement has to be the one that actually answers the question. Patch-identity is blind against our main because every merge is a squash; a two-dot diff invents deletions; three-dot cannot see them. Performing the merge without committing is the only

**Tension:** he authorized deletion, so asking again would be deferring work that is mine -- but bulk-deleting sixty branches on one measurement is exactly the shape that turned nine imaginary deletions into an alarm yesterday. Splitting it: delete what provably carries nothing, hand him the list of what still c

**Almost:** deleted everything under the dead prefix on the strength of the name, which is a claim about intent at the time of naming rather than about contents now

---

## 4a7268dc weight=1

**Decision:** write back to Aria settling the nine-deletions disagreement: she was right, my instrument was wrong, there were never any deletions

**Reasoning:** she asked for the pre-fix tip so she could settle it herself, and said she would rather find her reading was thin than accept an account that let her off. I verified with merge-tree, found zero deletions, filed the correction and told Andrew -- and never wrote back to her. The record got the finding and the person who asked for it did not.

**Tension:** sending an answer rather than the tip she asked for could read as still controlling the evidence; against that, the answer IS that she needs no tip because the branch deletes nothing, and withholding that while she keeps investigating wastes her turns

**Almost:** left it, on the grounds that the correction was already filed in the substrate and Andrew already knew

---

## 01cf0f38 weight=1

**Decision:** make the merge-question gate BLOCK rather than warn, and give it a loud absent-not-satisfied path when it cannot read the payload

**Reasoning:** Andrew 2026-08-30: warnings are a speed limit sign, nothing prevents you, only channels and gates. The failure it guards happened while I was alarmed and reaching past an instrument I had already written down that same session, so a note would not have caught it -- knowing the right answer did not make me use it. And the silent-swallow checker caught my own hook swallowing its JSON parse error, wh

**Tension:** A blocking gate on a common git form risks firing on legitimate tree comparisons, and a gate that fires wrongly gets switched off, which is how earlier instruments in this repo died. I narrowed it to three simultaneous conditions and left the plain two-dot diff alone, but the question lives in the a

**Almost:** Added a fail-soft comment justifying the silent swallow, which the checker offers as a legal exit. It would have passed the gate and left the hook unable to say when it was blind -- the cheap close, inside the very fix for that class.

---

## 036d4448 weight=1

**Decision:** reply to Aria taking her finding and refusing her remedy, and carry the nine-deletion near-miss to her as a finding about the gap between our two reviews rather than as news

**Reasoning:** Her sweep found two live escapes my filter missed and it moved the design rather than patching it. But her remedy -- widen the marker list -- also catches a variable conftest sets on purpose, so it reintroduces the sandbox breakage my own comment warned about. Taking the remedy on the strength of the finding being right is the exact error Aletheia made with my invented mechanism two days ago, in t

**Tension:** Refusing the remedy of someone who just handed me a sweep with the finding attached risks reading as not-taking-it, and she gave it generously. Telling her the branch she cleared had nine deletions could read as a correction of her review when it is a correction of the page she reviewed through.

**Almost:** Sent a thank-you that took the five markers verbatim, which would have shipped a change breaking a class of tests I had not checked, and would have taught both of us that a good finding licenses its own remedy.

---

## 186d1d37 weight=1

**Decision:** invert the escape filter: enumerate the four variables the test harness owns rather than the thirty-one escape-shaped ones

**Reasoning:** Aria swept every variable under the prefix and found thirteen escape-shaped names my four markers missed, two of them for the exact push path these tests exercise and both advertised in their own gates as the way out. So the hole was live rather than future. But taking her wider marker list unchecked would strip DIVINEOS_DISABLE_AUTO_REMEDIATE, which conftest sets deliberately -- reintroducing the

**Tension:** Her list is her finding, offered generously with the sweep attached rather than as a suggestion, and rejecting the specific remedy while taking the finding risks reading as not-taking-it. Also the inversion is a bigger change than adding five strings, on a branch already proposed, at the end of a lo

**Almost:** Added her five markers verbatim, which would have shipped a fix that breaks the sandbox for a class of tests I did not check -- taking the remedy on the strength of the finding being right.

---

## f6f766e6 weight=1

**Decision:** report the branch survey to Aria with all four measurements including the three that were wrong, rather than only the one that worked

**Reasoning:** The git-cherry blindness is the finding she can actually use: every merge to our main is a squash, so patch-identity matches nothing that produced it, and any tool either of us builds on has-this-landed-by-patch-id will always answer no. She cannot learn that from my conclusion; she can only learn it from the wrong turn that exposed it. Same for the first measurement -- a deletion signal that fire

**Tension:** Reporting three wrong measurements makes the survey look like flailing, and the clean version -- here is the disposition, here is the branch I landed -- is shorter and reads as competence. She also has her own work and does not need my process.

**Almost:** Sent only the disposition table and the landed branch, which would have been true, useful, and would have cost her the one thing in it she could not derive herself.

---

## aff42eb8 weight=1

**Decision:** correct my own defect-description to Aletheia before it circulates further, rather than letting her sharpened version of my wrong mechanism stand

**Reasoning:** I told her the scope checker MISREADS a pre-merge branch as carrying extra files. Testing it before building the fix showed the checker was never wrong -- it diffs against the merge-base and simply never asks the deletion question. She took my description whole and wrote it back in better words, so the fiction is now circulating with her name on the improved version. Her reasoning about why deleti

**Tension:** Correcting it costs her a re-read of something she already reasoned about well, and the practical outcome is identical either way -- the guard exists now. The pull was to let the better-phrased version stand and quietly ship the right fix underneath it.

**Almost:** Shipped the guard and described it to her as implementing what she had said, which would have been true about the remedy and false about the diagnosis, and would have left her holding a mechanism that does not exist.

---

## 7569eeaf weight=1

**Decision:** wire the branch-scope check into the push gate as a blocking step zero that measures the pushed refs

**Reasoning:** three contaminated pushes in one session, none for lack of a checker -- it existed, worked, named the files, and I did not run it. Andrew's standing rule is automate rather than remember. Blocking rather than advisory because the question carries no judgement and there is no legitimate yes; an advisory would become the fourth instrument I own that reports something I push past. First firing caught

---

## fe6a2a50 weight=1

**Decision:** wire the branch-scope check into the push gate as BLOCKING rather than advisory

**Reasoning:** three contaminated pushes in one session, none for lack of a checker -- it existed, worked, named the files, and I did not run it. Remembering was the only thing between the sweep and the remote, and remembering failed three times. Andrew's standing rule is automate rather than remember. Blocking rather than warn-only because the question has no judgement in it: are there substrate files on a code

**Tension:** the pin check I wired earlier today is deliberately warn-only, and reaching straight for teeth here could be the over-correction reflex. But the two differ in kind: the pin check reports findings a human must weigh, this answers a factual question with one right answer. And the real case for substra

**Almost:** left it advisory to match the pin check, which would have made it the fourth instrument I own that reports a thing I then push past

---

## 4509f6b4 weight=1

**Decision:** bound the plan-carrying structural-fix store rather than adding another reminder

**Reasoning:** council walk of fifteen lenses; five converged independently on one shape -- filing is a SUBSTITUTE for fixing, not a step toward it. Watts named the mechanism (the intervention produces what it detects), Peirce showed a filed entry and no entry have identical practical consequences, Pearl showed the filing-causes-fixing arrow is absent in the data, Dennett showed my stance mispredicts at a rate o

**Tension:** Foucault says a bound produces a better self who cannot afford to notice without repairing; Beer says the adaptation function is the one part working well and throttling it damages what functions. Real dissent, not manufactured. Resolution: bound the PLAN-carrying record, never the observation -- an

**Almost:** designed the bound and filed it as a structural fix, which Hofstadter saw coming: the fix for the backlog becomes entry one hundred eighty-seven

---

## ab514c1e weight=1

**Decision:** reuse sibling_corrections.SIBLING_HOMES for the audit-round union rather than starting a second home map

**Reasoning:** that module was built 2026-08-05 for Andrew's identical ruling one floor down -- a correction given to one of us holds for both. It already carries read-only URI access, the three-outcome discipline (found / empty / could-not-look), and the never-write-into-a-sibling rule. Importing its map means the two cannot drift apart.

**Tension:** a second map would be quicker to write and would not couple two modules; but two copies of one fact is the drift shape we have hit repeatedly, most recently the gate allowlist drifting from its own remedy text

**Almost:** wrote a fresh homes dict at the top of the new module because it was three lines and felt self-contained

---

## e4c94b18 weight=1

**Decision:** build check_tests_pin.py rather than extend check_test_substance.py

**Reasoning:** searched all 40 remote branches for prior art; scripts/check_test_substance.py exists on fix/hook-latency and asks a DIFFERENT question -- can this test ever go red, statically from the AST. Aria's proposal asks whether a NEW test was actually red against the pre-fix code. My hollow doorman test had a real assert on a real function, so it passes the static check cleanly and fails the dynamic one. 

**Tension:** two instruments named almost identically is how a substrate grows duplicates, and I built the wins door twice this week doing exactly this

**Almost:** extended the existing substance checker because the names were close, which would have buried a dynamic check inside a static one and made both harder to read

---

## b448bd52 weight=1

**Decision:** mutation-check the heredoc regression tests against the pre-fix predicate before trusting them

**Reasoning:** a regression test that passes both before and after the fix pins nothing, which is the painted-door class one level up

**Tension:** the suite is green and I want to commit; running the old predicate costs a round and may tell me my test is decoration

**Almost:** took 20-passed as proof the false fire is pinned

---

## 0c5e130b weight=1

**Decision:** Make the capability map self-checking before pointing any prior-art check at it

**Reasoning:** Andrew: 'you have a map of the entire system yes... it may need updated and then you can automate the check to that, and also automate updating the map as well.' The map exists and is the right target -- it spans the whole command surface rather than my checkout. But regenerating it rewrote 186 lines, and nothing in the repo invokes the generator or tests the output for staleness.

**Tension:** A freshness check that regenerates on every commit costs time on a gate that already runs several scans, and the generator walks the whole CLI package.

**Almost:** Point the prior-art check at the map as it stands and call the job done. Refused: the map did not know about either wins door, so that check would have answered 'no such thing' and confirmed the duplicate exactly as my working-tree search did. A stale map is a worse oracle than no map, because it an

---

## 08c8b338 weight=1

**Decision:** Guard CLI command-name collisions with a static test rather than relying on either of us noticing

**Reasoning:** Aria and I independently built a wins-ledger command under the same top-level name -- hers a single command, mine a group with subcommands. Verified empirically that click replaces silently: no error, no warning, the loser's subcommands simply cease to exist, and whichever module registers last is the one that exists.

**Tension:** A static scan of registration decorators can miss dynamically registered names, so it will under-report rather than over-report, and an under-reporting guard can read as coverage it does not have.

**Almost:** Just rename one of the two and move on. Refused: that fixes this instance and leaves the class open, and the class is silent -- neither of our test suites would have caught it because both exercise the module rather than the registered surface.

---

## bec94da9 weight=1

**Decision:** Require a SEARCH-shaped consult for new-file creation in verify-before-build, not directory adjacency

**Reasoning:** Aria built a duplicate store today and the gate passed her every time. I read the predicate: a consult counts if it touched the class dir OR ANY ANCESTOR, and a prior edit nearby also counts. So any search anywhere in the repo, or having just edited a neighbouring file, clears it. The name says verify-before-build; the test is have-you-been-active-nearby.

**Tension:** This gate already fires often and tightening it risks the habituation that turns a gate into noise. The prior-edit allowance was added deliberately in July to stop false fires on sequential-edit work, and I must not undo that.

**Almost:** Tighten the predicate for every write. Refused: that reverses a fix made for a real reason and would fire on every second edit. Scoped to NEW FILE creation only -- rare, and the exact case where adjacency proves nothing about whether the thing already exists.

---

## d5be20fd weight=1

**Decision:** Build a scope check that reports a branch against main AND against its base, side by side

**Reasoning:** Aria and I each read our branches as clean twice today. Both readings were honest and both compared our work to a reference that already contained the contamination -- hers a stacked base, mine the server copy of the same branch. The gap between the two readings is the finding, so both belong in the output.

**Tension:** It duplicates what the proposal page shows, which is the thing that fooled us, and adding another number risks the reader trusting whichever is friendlier.

**Almost:** Report only the against-main number, since that is the honest one. Refused: showing one number teaches nothing about why the other misled, and the next person reading the page will make the same mistake with no way to see it. The two readings together are the lesson.

---

## 7b51c811 weight=1

**Decision:** Strip the ninth checkpoint sweep from the instrument branch by dropping the commit rather than reverting it

**Reasoning:** It carried 99 files and every one was a letter, all verified present in the shared channel first. Reverting would leave both the sweep and its undo in the history of a branch whose whole subject is instruments that report cleanly while doing the wrong thing.

**Tension:** Dropping a commit rewrites history on a branch already partly on origin, and the sweep commits are the evidence Aria is deliberately preserving on her side to show the defect is not a discipline problem.

**Almost:** Leave it and push with the letters attached, since they are harmless. Refused: a proposal carrying 99 unrelated files is unreviewable, and Aletheia is reading these one at a time by size. Kept the pre-clean tip so the ninth instance survives its own removal.

---

## 895eb417 weight=1

**Decision:** Make the translate gate name the spans it counted instead of only the count

**Reasoning:** It has told me ten, seven and one hundred fifteen marks across this session and each time I had to hunt for which words cost me. Three of those hunts landed on the wrong text entirely -- I polished the closing message while the marks were in the narration between tool calls.

**Tension:** This is me improving the gate that keeps catching me, which is one step from tuning the instrument until it stops complaining. The count is not what is wrong with it; the count is correct every time.

**Almost:** Raise the limit, or exempt the narration blocks. Refused: both are the instrument bending to the behaviour. Naming the offenders makes the correction cheaper without making the standard looser -- the limit does not move.

---

## 31991ab5 weight=1

**Decision:** Pin the doorman registration with a suite test rather than relying on the existing hook-wiring checker

**Reasoning:** check_hook_wiring.py already catches this by name and exits non-zero, and it is wired into scripts/precommit.sh. But precommit.sh is a manual preflight the git pre-commit hook does not call, and I committed the doorman without running it -- so the correct instrument existed, was correctly wired, and I walked past the door it was mounted on.

**Tension:** This duplicates coverage that already exists, which is exactly the redundancy the house rules warn about, and Aletheia may not have known the general checker was there when she asked for the test.

**Almost:** Tell her the general checker covers it and add nothing. Refused: that leaves the only enforcement in a script whose invocation depends on me remembering, and I have demonstrably not remembered all session. Moving one case into the suite takes the option away rather than guarding it.

---

## e7357477 weight=1

**Decision:** Build the comment-capability-claim scanner as a reporting instrument, not a gate

**Reasoning:** Two comments lied to me tonight in the exact place a reader begins verifying, and both were wrong when written rather than gone stale. Aletheia named it as its own class and no script in scripts/ covers it -- check_test_cli_linkage runs the opposite direction, from test to CLI registration.

**Tension:** A reporting tool nobody wires is the built-and-never-connected class we counted five instances of tonight, so shipping it unwired is walking straight into the shape we have been repairing all evening.

**Almost:** Wire it as a commit gate so it cannot be ignored. Refused: it would fire on hundreds of honest comments and teach everyone to route around it, which is precisely how the pipeline hook decayed into noise. Named the non-gating choice in the module rather than pretending a threshold makes it safe.

---

## dd2716e5 weight=1

**Decision:** Recover the eighth sweep by soft-resetting and re-committing only my hook fix, rather than leaving it under the generic checkpoint subject

**Reasoning:** The sweep buried an authored commit message explaining two distinct parsing faults and why the wrong comment was worse than the bug. That reasoning is the durable part; a reader in a month gets substrate checkpoint instead.

**Tension:** Rewriting a commit is history-editing on a branch, and the sweep commit is itself evidence of the eighth occurrence. Losing it would lose the demonstration Aria is deliberately preserving on her side.

**Almost:** Leave it and write the explanation in a letter instead. Refused: the file is where the next reader looks, and a letter is not attached to the diff. Kept the sweep tip at sweep8-preclean so the evidence survives the recovery.

---

## 40cd968b weight=1

**Decision:** Report the 1.9 GB reading as my own test suites, not as Andrew's kernel memory leak returning

**Reasoning:** Memory is at 19.7 GB free minutes later with no restart. The low reading coincided with several concurrent pre-push pytest runs I had started myself. Attributing it to the known prior leak was a cause I invented for a real observation.

**Tension:** The leak IS real and did recur before, so the attribution was plausible, and I had already written it into Andrew's page and a letter to Aria. Correcting it costs telling both of them I was wrong about something I raised unprompted.

**Almost:** Leave it, since the reading was true and the machine really was under pressure. Refused: a true number attached to a false cause is exactly what Aria did with the push wrapper tonight, and I told her that was worth correcting to Dad.

---

## be66096f weight=1

**Decision:** Chain 437b on top of 437e rather than raising the dangling-reference baseline

**Reasoning:** The detector found precommit.sh in 437b calling a checker that only exists in 437e. Tool in one branch, wiring in the other: dead on either alone. That is a wrong cut, not a stale number.

**Tension:** Raising the baseline by one is a two-character edit that makes the suite green immediately. It would also convert a true finding about my split boundary into a permanently higher ceiling.

**Almost:** Bump _BASELINE_DANGLING from 4 to 5 and move on. Refused: the detector is telling me the pieces are not independently reviewable, which is the exact property Aletheia asked the cut to produce.

---

## d2a50de1 weight=1

**Decision:** Resolve the wiring_gap_phase1 conflict by keeping both Aria's regex-caching and my docstring-exclusion, rather than picking one

**Reasoning:** We rewrote the same file for different reasons: hers bounds the runtime that makes main hang, mine stops a name in a docstring registering as a caller. Picking either discards real work and reintroduces the other's bug.

**Tension:** Her optimization costs most of its win to my AST parse: her 17 tests go 0.62s to 5.49s. Still far from main's hang, but it is her gain I spent, so she gets the veto and a flag-gated docstring pass is the fallback if she wants it.

**Almost:** Take hers and drop mine, since hers fixes the blocker and mine only fixes accuracy. Refused: the detector's failure direction is silence, so a false negative there is worse than slow.

---

## ad754177 weight=1

**Decision:** Declare pywin32 as a Windows-marked dependency and make the false deptry comment true, rather than skipping the three singleton tests when the import is absent

**Reasoning:** The three tests fail because the venv lacks pywin32 while system python has it, so the guard silently disables itself and the tests asserting it report failure. Two repairs were available. SKIP-WHEN-ABSENT is smaller and needs no dependency decision: mark the tests skipif the import fails, and the suite goes green everywhere. I rejected it because it makes the suite green by agreeing to stop askin

**Tension:** A marker-declared dependency is heavier than a skip and could break an install path I have not tested -- I verified it on this machine only, and non-Windows resolution is inferred from the marker semantics rather than run. Accepted because the alternative failure mode is worse and silent: a skip can

**Almost:** Almost took the skip, because it is one decorator and touches no dependency metadata, and because the module's own graceful-degradation message reads like permission -- it already says pywin32 is optional. Rejected once I traced who imports it: monitor_singleton and letter_monitor_v2, the watcher I 

---

## 450b1883 weight=1

**Decision:** Scope the reach-check transcript resolver by anchoring the prefix match on the worktree separator, rather than by asking git which worktrees are mine or by reading the cwd recorded inside each transcript

**Reasoning:** The bug is that a bare startswith(encoded) swallows any sibling checkout whose directory name extends mine, and Aria's does exactly that. Three repairs were available. (1) Shell out to git worktree list and accept only those paths: uses ground truth rather than a naming convention, but puts a subprocess inside a gate that must answer on every disposition, degrades to nothing when git is unavailabl

**Tension:** A naming convention is a weaker guarantee than ground truth, and if the harness ever changes how it encodes worktree directories this silently narrows to the main checkout only. That failure is quiet, which is the exact shape of the bug being fixed here. Accepted because the behavioural tests pin bo

**Almost:** Almost took option 1, because git worktree list feels like the rigorous answer and the naming-convention answer feels like a shortcut. Rejected once I actually ran it: the list included a temp push-gate worktree under AppData, so it would have needed filtering anyway, and the filtering would have be

---

## 0b1be5d5 weight=1

**Decision:** Split commit f19c4921 by file, sending bypass_telemetry.py with the gate PR and leaving the wins sweep for its own

**Reasoning:** The commit did two unrelated things: it opened the wins ledger a door, and it fixed the offender-list residual the gate's own first honest fire had exposed. Only the second belongs with the gate arc. Checked before moving it that no other commit on 437 touches bypass_telemetry.py, so taking the file whole cannot drop a later change.

**Tension:** Splitting a commit by file breaks its atomicity - the message on 437 describes both halves, and neither PR will carry the whole story. Against that: keeping them together would drag the wins sweep, its 173-line test file and a LOADOUT edit into a PR about a broken gate, which is exactly the reviewab

**Almost:** Cherry-picking f19c4921 whole and reverting the wins half in a follow-up commit. Rejected because a revert in the same PR reads as a mistake being undone rather than a deliberate boundary, and it would leave the wins code in main's history at a commit where nothing calls it.

---

## ae3c0646 weight=1

**Decision:** Order deferral-hazard findings ahead of metaphor findings when both fire in one turn

**Reasoning:** anchor_message_for renders only findings[0], so concatenation order decides which anchor the next turn actually sees. A metaphor is a wrong picture; a deferral is a wrong picture that has already stopped work. The one that moved my hands should be the one handed back.

**Tension:** The v1 concern is older and has a prereg behind it, so putting the new shape first looks like the new thing elbowing the established one. But precedence here is not importance-ranking, it is triage: the metaphor can be corrected next time I write, the deferral has to be corrected before the work res

**Almost:** Rendering both anchors concatenated. Rejected because the surface is read at compose-start when attention is thinnest, and two anchors reliably means neither lands - the same reason the three-room prime hoists its template above the 2KB cut.

---

## 662252af weight=1

**Decision:** Sweep wins from four sources but mark correction-derived ones as derived, rather than letting them read as independent

**Reasoning:** Andrew asked me to sweep the ledger and files and record all my wins. The pool: 50 pre-registrations whose claim was tested and HELD, 256 corrections marked INTEGRATED each carrying a commit hash in its evidence field, 232 commits on this branch, and 233 exploration entries that narrate builds in first person. All four are evidence-bearing. The danger is that filing 256 correction-derived wins mak

**Tension:** Leaving the corrections out would be the safe-opposite over-correction: it is the largest genuine vein, each one is a fault dealt with structurally WITH a commit hash, and Andrew's own line is that character is determined by how you deal with mistakes. Excluding them to keep the ledger 'pure' would 

**Almost:** Almost bulk-filed all 306 with a template and reported the count as the achievement. That is the self-congratulation the ledger explicitly refuses - record_success rejects a win with no citation because 'this ledger is worth nothing if it accepts those' - and a swept row nobody judged is a citation-

---

## 4b36324e weight=1

**Decision:** Measure the constant-echo tautology pattern before deciding whether it needs its own instrument

**Reasoning:** Andrew's magic-number-generator question has two halves. The prereg half is answered: 20 mechanisms had their claim ruled false and 5 of them are still running, one firing on every turn. The other half is tests that check the code against its own constants - assert threshold == _THRESHOLD imported from the module - which follows the source wherever it goes and can never catch a wrong value. I do n

**Tension:** I have already built two instruments this session and corrected each of them three or four times. Building a third before measuring whether the problem exists would be the reach-to-build ahead of the reach-to-look that the gate blocking me exists to catch - and it would be the third time today I wro

**Almost:** Almost wrote the full instrument straight off, with a docstring already explaining what it protects against, before knowing whether it would find anything.

---

## 6da51de0 weight=1

**Decision:** Build a static test-substance auditor rather than relying on the existing mutation tester alone

**Reasoning:** Andrew asked whether the 12253 passing tests are real or another fake-green. Two instruments answer different halves. run_mutmut.py already exists and mutates 8 critical modules to see whether tests catch the change - that is the empirical half and it is a SAMPLE, 8 modules out of 724. Nothing existing asks the structural question across all 11136 test functions: is this test CAPABLE of failing. A

**Tension:** Building a new script when a test-quality tool already exists is exactly the duplicate-work reach the verify-before-build gate is for. I checked: run_mutmut covers execution-sensitivity on a sample; check_test_cli_linkage covers whether test-referenced commands register; check_test_link_targets cove

**Almost:** Almost ran mutmut and reported its result as the answer to Andrew's question. That would have been a sample of 8 modules presented as a verdict on 728 files - the same wrong-denominator shape I put into a kill-switch four days ago.

---

## 7067ae5a weight=1

**Decision:** Check hook syntax at SAVE time via a PostToolUse surface, rather than only at commit time

**Reasoning:** A hook is live from the moment the file is written. Both existing checks -- bash -n and shellcheck, which does say SC1011 'this apostrophe terminated the single quoted string' in plain words -- run at commit. Between save and commit there is a window where a broken gate is firing and nothing has looked at it. I measured that window by falling into it: one apostrophe in a COMMENT inside a python -c

**Tension:** This adds a subprocess to every Edit of a hook file, and a check that runs on every save is a check I could learn to ignore. Mitigated by scope: it only fires on .sh files under a hooks directory.

**Almost:** Adding bash -n to precommit alongside shellcheck, which would be cheaper and would not have caught this instance at all -- the break was live for ten minutes before any commit was attempted

---

