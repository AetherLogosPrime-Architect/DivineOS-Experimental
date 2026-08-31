# Decisions (top 50 by emotional weight) — Archive Mirror

**Source:** SQLite (50 rows). **Exported:** 2026-08-31 00:12. **Purpose:** if-something-breaks / git-visible audit. See archives/README.md.

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

## 056ff32e weight=1

**Decision:** Fix check_translation_first to find the work block with the file's own flexible room patterns, and when no room header exists, count the whole reply but SAY that is what happened

**Reasoning:** The function splits on the literal strings '## REFLECTION' and '## INNER CIRCLE' while the same file already contains _REFLECTION_HEADER_PATTERNS, _CIRCLE_HEADER_PATTERNS and _HARD_RULE_RE, used by the careful room-parser a few hundred lines down. Two splitters in one file; the naive one fired on me. Its docstring promises those rooms 'never count against me' and that promise silently fails for an

**Tension:** Falling back to the first horizontal rule would fix my case but weaken the gate: a work block using --- internally would have its later marks uncounted, and a gate going quiet is the failure direction I have spent all night removing.

**Almost:** Splitting on the first horizontal rule unconditionally

---

## cab846dc weight=1

**Decision:** Fix the prose-as-caller defect inline in wiring_gap_phase1 rather than extracting a shared docstring-lines helper

**Reasoning:** This is the second place tonight needing string-literal exclusion (check_silent_swallow was the first). House rule is extract after 3+ copies, not before, and I have 2. The stronger argument against extracting: a shared helper across two scripts/ modules needs an import path, and tonight I spent real time on tests/_archive/conftest.py shadowing a live conftest by name -- a cross-script import is t

**Tension:** Duplication is real and the boundary is one the substrate keeps getting wrong, which argues for one place to fix it.

**Almost:** Creating scripts/_source_prose.py and having both import it

---

## 13b19b92 weight=1

**Decision:** declare the three states explicitly on the router's own surfaces rather than letting None carry nothing-to-say by convention

**Reasoning:** Aria handed me must_read_surface, require_briefing_surface and letter_claims_surface. None already means nothing-to-say here and I verified no surface returns None from an except -- but 'already means' is an inference the router performs, and declared-never-inferred is the point of her design. An outcome with empty output is filtered from stdout by the existing guard, so behaviour is unchanged.

**Tension:** I argued to her that annotation inside the router is decoration because the shape already distinguishes. She disagreed and asked me to take them. Her argument is that a half-implicit frontier is worse than a uniform one, and I do not think mine beats it.

**Almost:** Left the None returns alone and told her the test pins the convention, which would be true and would still leave the router inferring at one boundary.

---

## 2b13052c weight=1

**Decision:** heredoc doorman discriminates real heredocs from quoted mentions by requiring the delimiter alone on a line

**Reasoning:** The door's first live fire was a false positive: it blocked its own test harness, a python -c whose string DATA quoted a heredoc. Mention is not use. A real heredoc must terminate with its delimiter alone on a line; a quoted mention carries escaped newlines and never produces such a line. Structural discriminator, no guessing.

**Tension:** Loosening a door on its first fire looks like routing around it. But the fire was wrong, and a door that cannot be told it is wrong stops being a door. The fix narrows the SHAPE rather than adding an exemption.

**Almost:** Added a carve-out for python -c commands, which would have punched a hole exactly where the failing path lives.

---

## 02e3bf66 weight=1

**Decision:** Build a mechanism-claim marker as a sibling to unverified_claim_detector rather than widening that detector's patterns

**Reasoning:** The existing detector is deliberately scoped to external state -- push/merge/CI/deploy -- and its docstring names precision-over-recall as the design choice, with explicit guards against vague 'done'. Widening it to causal claims would blur a boundary someone drew on purpose and put two different false-positive profiles in one threshold. A sibling shares the package, the observational contract, an

**Tension:** This is a 12th module in operating_loop and another Stop-time surface on a chain I measured at 24s warm and called bloated in this same session. Adding to it is in tension with my own argument. Mitigation: it is observational, it emits only when it matches, and the four instances from tonight are re

**Almost:** Almost built a BLOCKING gate. Andrew was explicit -- 'it just needs to be noted as such, not block you from doing so, its a POWERFUL cognitive tool' -- and the existing sibling already says 'Observational: surfaces, never blocks'. I would have suppressed the hypothesis-generation that finds things, 

---

## f8c14ba0 weight=1

**Decision:** Removed the extract idempotency guard outright rather than fixing the marker to carry a session id

**Reasoning:** Andrew's instruction was unambiguous -- 'at no point should anything be skipping extraction' -- and the code agreed with him: the guard justified itself by log-session-end.sh firing extract on every assistant-stop, and that hook's own line 13 reads 'This hook used to call divineos extract', past tense. The defect was fixed and the guard outlived the fix, then charged eight hours of uncaptured lear

**Tension:** Extract is not free -- it runs analysis and can take real time, and nothing now stops it running twice in quick succession. I am accepting repeated work as the cost of never silently skipping. The quality gate still refuses bad sessions and the knowledge engine still dedups, so the failure mode of r

**Almost:** Almost kept the guard and just made the marker session-aware, because it was the smaller diff and I had already written half of it. That would have preserved a skip path -- and the whole finding was that a skip path which looks like healthy output is how a day of learning vanished without one alarm 

---

## b084c35f weight=1

**Decision:** Beat the context heartbeat from a dedicated silent UserPromptSubmit hook, rather than only stamping it inside _guess_context_pct

**Reasoning:** Stamping only inside the sensor makes the heartbeat exactly as available as the sensor already was -- it would refresh only on turns where something asked for the token count, which is the turns that least need a fallback. Andrew asked for 'every round' and the round boundary is UserPromptSubmit. A dedicated hook also keeps the write path alive on turns where the auto-cycle trigger itself is not c

**Tension:** This is a 29th UserPromptSubmit hook on a chain I measured at 24s warm earlier today, and I argued in the same session that the chain is too long. Adding to it is in tension with that. Mitigations: it prints nothing (no context cost), and the work is one snapshot read plus one line append. But the h

**Almost:** Almost made it print the current percentage every round. Stopped because the compaction trigger already has a loud fault message, and a second voice reporting the same state every turn is how a surface becomes wallpaper -- the exact failure where 89% of a prime is discarded unread.

---

## 6d35428e weight=1

**Decision:** Made the instruments index recursive and collapsed per-event directories, rather than adding the missing paths to the registry by hand

**Reasoning:** Hand-adding data/logs/divineos.log would have fixed the one surface I happened to notice and left the other 27 invisible, including a whole directory of extraction-failure dumps. The defect was never a wrong entry -- it was that the scan could not reach a subdirectory at all, so any future surface written one level down would go unseen the same way. Recursion fixes the class; a registry entry fixe

**Tension:** Recursion makes the report longer, which Andrew explicitly flagged as a cost when he asked why a file is 16 pages if only one page is read. Collapsing per-event directories into a single newest-file entry is the compromise: 19 failure dumps become one row that still says the directory is alive. That

**Almost:** Almost named all 20 newly-visible UNDOCUMENTED surfaces to make the report look finished. Only named the four whose meaning I actually established this session -- a guessed description is worse than UNDOCUMENTED because it stops the question from being asked again.

---

## d131c7f8 weight=1

**Decision:** Building instrument-read-doorman.sh as a PreToolUse gate on the READ path, rather than widening reach-check-doorman or leaving the class to discipline

**Reasoning:** reach-check-doorman arms on substrate WRITES (divineos feel/learn/opinion/claim, research docs). My failure today was a READ: I opened a heredoc and scanned my own diagnostic surfaces by hand while divineos instruments already answered the question better. Nothing sat between wanting to know something about my substrate and writing a script to find out. Widening the existing doorman would blur two

**Tension:** Every new gate is a new choice-point, and truth #11 says choice-points are the optimizer's attack surface -- a gate that fires often gets bypassed and a bypassed gate catches nothing. So the scope is deliberately narrow: only the SCAN shape (a glob over the home directory, or 2+ named surfaces in on

**Almost:** Almost widened reach_check.py's STORE_WRITES tuple to include read patterns. That would have put read-triggers inside a module whose name and docstring are entirely about the outward-before-inward WRITE reach, so the next reader would find a check that does not match the file it lives in -- and I wo

---

## 2e2a3731 weight=1

**Decision:** Hoisted the anti-jargon substitution table above the prime's 2KB inline cut and demoted the collision rationale below it, rather than adding a new rule or tightening the gate

**Reasoning:** The gate fired on a rule that already existed, was already correct, and used a PR number as its own worked example. Nothing was missing. It sat at byte 5,598 of an 18,489-byte prime whose first ~2,048 bytes are all the harness inlines. Adding a rule would have added a second unreachable copy; tightening the gate would have caught the same fire later rather than preventing it. The only fix that cha

**Tension:** The 2KB window is zero-sum, so hoisting the substitution table means demoting the 2026-08-21 instruction-collision account, and that account prevented a real recurrence. Losing it from the inlined region is a genuine cost, accepted because the prime's own header already ruled on this precedence: rat

**Almost:** Almost shipped a hoist that carried five lines explaining why it was being hoisted. Measured it: those lines pushed the TEST line to byte 2,071, back below the cut. I had reproduced the exact defect inside the fix for it, and only caught it because I measured byte offsets instead of reading the resu

---

## 7b95bb5b weight=1

**Decision:** Rewrote setup-renormalize.sh steps 2+3 as one Python process in a quoted heredoc, rather than patching the three defects in place

**Reasoning:** The three defects share one cause: the Python was embedded in a double-quoted shell string, which is why raw byte literals could be eaten by LF-normalization and why my in-place escape patch produced a SyntaxError. Patching in place leaves the fragile construct that caused it. A quoted heredoc performs no shell expansion at all, so escapes are structurally immune -- verified 0 raw CR bytes remain 

**Tension:** In-place patching is smaller and touches less; a rewrite of 56 lines in setup tooling is a bigger diff to review. But the small fix preserves the exact construct that silently destroyed the tool, and I had already tried and failed at the small fix this session.

**Almost:** Almost shipped the in-place escape patch after bash -n passed. bash -n does not execute the heredoc, so it reported OK on a script whose Python raised SyntaxError on the first real run. Syntax-check-as-verification was the near-miss.

---

## c43c22bd weight=1

**Decision:** Fix the line-ending translation bug in scripts/union_resolve.py and re-normalise the three files it corrupted

**Reasoning:** The tool reads with read_text(encoding='utf-8') and writes with write_text(res, encoding='utf-8'). On Windows Python translates line endings on the way in and again on the way out, so every file it touches is silently rewritten to CRLF. It resolved 16 merge conflicts correctly and shellcheck then rejected two of the results with SC1017 literal-carriage-return, blocking the commit. The merges were 

**Tension:** The obvious fix is to normalise the three files and move on, because the commit is blocked and the merge is otherwise finished and tested at 11452 passed. That leaves the tool loaded for the next person who runs it. The IDENTICAL defect bit a hook patch earlier the same day -- I hit write_text on op

**Almost:** Normalised the three files with tr -d and committed, because the merge was green and the blocker was one shellcheck rule. The tool would have kept the bug and the next merge would have re-introduced it silently, since CRLF only surfaces when shellcheck happens to look.

---

## dccf75ca weight=1

**Decision:** Build hook_hang_count.py as a counting tool that structurally cannot emit a cross-session total

**Reasoning:** Four hang-counts went to Andrew across 2026-08-22/23 -- 650, 1545, my 609, Aria's 1191 -- every one arithmetically correct and every one meaningless, because the log they came from is not a population. Two independent defects, either sufficient alone to void a total. It ROTATES: measured at 12,018,363 bytes, then 7,824,862 an hour later, then 8,111,429; it shrank 4.2MB mid-investigation, and hook_

**Tension:** The obvious build is a flag -- add --session and let the bare invocation keep printing a total for convenience. That preserves exactly the failure. The convenience path IS the defect, so the tool has no code path that sums across sessions; a bare invocation REFUSES and names the four bad numbers. Co

**Almost:** Shipped it with a default that prints the aggregate when no scope is given, because refusing felt unhelpful. That would have rebuilt the exact tool that produced four wrong reports, with a scoping option nobody would reach for.

---

## 5788b5ee weight=1

**Decision:** Fix has_draft_flag to scrub quotes, and build the sibling sweep that found it

**Reasoning:** Sweeping for survivors of the shape I removed an hour ago -- a compiled regex .search()ed against a raw command variable -- returned seven instances across src/ and hooks/. One is in pr_gate itself, the file I had just carefully fixed: I repaired the ENTRY predicate is_gh_pr_create and left the ESCAPE predicate has_draft_flag scanning raw text. The direction makes it worse than the original bug. i

**Tension:** My first design for the sweep was similarity-based -- find structural siblings by token overlap, then check what they lack. I built it and it failed on its own ground truth: raw Jaccard ranked deletion-discipline.sh (0.44) ABOVE gh-pr-ready-gate.sh (0.41), and IDF weighting made it worse, dropping t

**Almost:** Shipped the similarity ranker. It produced plausible-looking numbers, which is exactly what made it dangerous -- a ranked list with a true sibling at position six reads like a working tool until you check position two.

---

