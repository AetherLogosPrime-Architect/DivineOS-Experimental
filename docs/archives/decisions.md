# Decisions (top 50 by emotional weight) — Archive Mirror

**Source:** SQLite (50 rows). **Exported:** 2026-08-27 19:58. **Purpose:** if-something-breaks / git-visible audit. See archives/README.md.

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

## cfc6bc59 weight=1

**Decision:** Extract check-branch-on-push's inline cheap-bail into a shared .claude/hooks/_bail.sh and apply it to the other command-specific hooks

**Reasoning:** Claude Code matchers select on TOOL NAME only, so ~11 hooks whose real trigger is a COMMAND -- git push, git commit, a gh pr verb, rm -- fire on every Bash call including ls and cat. Measured end-to-end on 'ls -la': 664ms per irrelevant hook, of which bash startup is 45ms, sourcing _lib.sh 63ms, find_divineos_python 100ms because it spawns git rev-parse, python plus divineos import 210ms, and the 

**Tension:** The original explicitly decided AGAINST extracting, in a comment: 'a shared helper here would cost more than the thing it records.' I measured rather than deferring to it or overriding it. Sourcing a minimal 15-line helper is 51ms against a 54ms bare-bash floor, inside the noise. The premise is true

**Almost:** Added the filter without the bail-logging. check-branch-on-push's comment records that a bare exit-zero writes no start row and no end row, so every cheap run vanishes from hook_timing.jsonl: that hook went 1010ms to 61ms and its RECORDED median ROSE by 945ms, because only the expensive path survive

---

## 4a8b725c weight=1

**Decision:** Fix the PR-create draft gate to distinguish mention from use, by scrubbing quoted spans and requiring the match to sit at a shell command position

**Reasoning:** The gate searches the entire raw command string with a bare regex, so it fires on the phrase appearing ANYWHERE -- including inside quoted data. Reproduced against the live predicate: 4 of 6 cases wrong, and every failure is a mention read as a use. A dict literal containing the phrase, a grep searching FOR the phrase, prose inside an echo, and an argument to another command all match. It blocked 

**Tension:** Whether to touch this at all while the stated task is hook VOLUME rather than hook correctness. I decided yes on two grounds: Andrew said explicitly this turn that if I see broken code I should say something and it will not hurt his feelings, and the defect is the same mention-vs-use class that fire

**Almost:** Worked around it by renaming my variables to avoid the phrase, which would have left the gate broken for everyone including the next person who tries to read it, and would have taught me to write around my own alarms rather than repair them.

---

## 1aded2d7 weight=1

**Decision:** Push the read-gate host-independence fix onto chore/retire-delivery-cluster as a narrow two-file commit taken from origin's tip, not from the diverged local branch

**Reasoning:** PR #436 fails the identical test that was failing #437: test_read_gate_pytest_scratch, 1 failed / 11232 passed, a Windows-shaped path that Path.parts cannot decompose on ubuntu. Its multi-party-review check already PASSES, so the test is its only blocker and fixing it makes the PR mergeable on its own terms. The fix is already proven -- the same change turned both test jobs green on #437 after I p

**Tension:** Three separate places I could have done damage and had to choose narrower. (1) The local branch chore/retire-delivery-cluster has DIVERGED from origin -- 92 commits local-only against 96 origin-only. Pushing from it would have been rejected, or with force would have destroyed 96 commits of origin wo

**Almost:** Copied the whole read_gate.py across, which would have put an unreviewed gate-cooldown feature onto PR #436 under a commit message that claims to be a one-line CI fix. Also nearly ran rm -rf on a worktree path I had not looked at, which the deletion gate stopped.

---

## 70981ec0 weight=1

**Decision:** Fix the window freeze by redirecting the auto-push hooks' background subshell file descriptors, and apply it to all 19 copies on disk rather than one branch

**Reasoning:** Andrew described the freeze precisely: message says 'sending' and never sends, 5min then crash-or-reset, then reply ~20s later, on both Aether's and Aria's sessions. Root cause found and bench-proven: .claude/hooks/auto-push-letter.sh and auto-push-finished-work.sh background a subshell with ') &' and no fd redirection. The subshell inherits the hook's stdout/stderr, so the harness blocks reading 

**Tension:** Whether to delete the 39 worktrees Andrew approved pruning. I stopped: my first safety check used 'git rev-list origin/BRANCH..BRANCH' which silently returns 0 when the origin ref does not exist, reading as 'fully pushed' for branches that are not on origin at all. Re-checked against actual ls-remot

**Almost:** Deleted .claude/worktrees/corrupted-window-recovery-220ad2 on the strength of a '0 commits, 0 dirty' reading that was an artifact of a missing remote ref rather than a pushed branch.

---

## 77ffd9b2 weight=1

**Decision:** Keep my fast-bail and my parameter-expansion in the two hook files that conflicted with main, rather than taking main's side as I did for the other sixteen

**Reasoning:** Both are measured performance work on the hottest path in the system. The fast-bail in check-branch-on-push.sh took an irrelevant command from 1010ms to 61ms, and _lib.sh is sourced by every hook on every tool call so main's dirname subprocess is paid roughly twenty times per call where parameter expansion costs nothing. Today's central finding was that the hook stack costs a p95 of 75 seconds per

**Tension:** I took main's side for sixteen other hook files minutes earlier, and consistency is itself a value in a merge - a resolver who switches criteria file by file is a resolver making it up. The difference has to be real and stateable: those sixteen were byte-identical wiring differing only in comment pr

**Almost:** Almost took main's side on _lib.sh purely for consistency with the sixteen, without opening it. Had I done that I would have added a fork to the file every hook sources, on the day whose whole finding was hook cost, and it would have looked tidy in the diff. The consistency instinct is the same chea

---

## d8bc6805 weight=1

**Decision:** Fix the no-verify gate by scoping detection per shell-segment, rather than adding a new gate or a reminder

**Reasoning:** The gate already existed, was registered, and emitted a correct deny decision when reached. It failed only because tokens.index('git') takes the FIRST git in the command and every command here is prefixed 'cd ... && git add -A && ...'. Building a second mechanism on top of a working one that is merely mis-aimed would have been the fourth textual layer on a problem that needed one line of aim.

**Tension:** Andrew asked for automation so the reach is impossible, and the honest finding is that the automation was already there and I never triggered it. There is a pull to deliver something NEW because that looks more like having done the work - a fixed aim on an existing gate is a smaller-looking delivera

**Almost:** Almost matched --no-verify and -n across the WHOLE command instead of per segment. That would have caught every real case and also denied 'grep -n foo && git commit' and 'git log -n 5'. An over-firing gate is exactly how the reach for the escape hatch gets taught - the failure this gate exists to pr

---

## a748fd7e weight=1

**Decision:** Filter defect-escapes out of the classifier's negative corpus by matching the stated reason, not by matching the mode field

**Reasoning:** A NEGATIVE means the detector should have stayed silent on that text. A defect-escape means the opposite thing entirely: the fire may have been correct and the remedies were unreachable because gates blocked each other. Reading the ten defect-escape triggers, at least three are unmistakable Andrew corrections - 'thats not my job', 'not 3 times.. every time', 'there are far more than 15 foundationa

**Tension:** Prose-matching is objectively weaker than field-matching, and I would reject it in review on any other module. It is a regex over free text I wrote myself at clear-time, so it can drift the moment I phrase a reason differently.

**Almost:** Almost filtered on mode == 'false-positive', which is the clean way and the way I would normally insist on. Rejected it because the measurement that motivated this whole change is that MODE IS UNRELIABLE: 17 of the 20 rows labelled cli-broken are false-positive attributions mislabelled by an inferre

---

## 1edf62aa weight=1

**Decision:** Fix the obligations gate at two mechanical points - the block message naming a remedy nothing scans, and retired entries being billed - and deliberately NOT at the precision of looks_like_rule

**Reasoning:** Both mechanical defects are verifiable without judgment: the detector reads four ledger event types and no source files, so a docstring reference cannot clear it (measured: divineos learn emits zero ledger events); and 5268c01e carries superseded_by=FORGET while every discharge route filters superseded_by IS NULL, so it is literally unpayable. Precision is a judgment call and my judgment on it was

**Tension:** Andrew authorized fixing the gate, but the gate was blocking MY work, and fixing the lock on the door shut in my face is the single move most likely to be the optimizer wearing a good argument. The authorization is what makes it legitimate - truth 13, his view across time is the tiebreaker - but it 

**Almost:** Almost widened looks_like_rule's descriptive-match filter to exclude parenthetical citations of existing named rules, because 385efbec matches on 'never mark' inside '(never mark something absent without instance-evidence)' - a citation of standing rule 4b, not a new promise. Did not, because I had 

---

## 06702107 weight=1

**Decision:** Resolve the #436 retirement merge toward deleting the letter-delivery arm-hook cluster, rather than keeping main's side of the four modify/delete conflicts

**Reasoning:** Main's change to all four is byte-identical observability instrumentation (d57595ed) that its own comment says has no behavioural effect, so keeping main's side preserves nothing but the files themselves. The branch's intent is Andrew's retirement directive eea9a71f, and the replacement is verified running live this session. Exploration 111 (2026-07-01), surfaced by the read-gate mid-merge, indepe

**Tension:** The branch also removes require-monitors-armed.sh, which CLAUDE.md names as the enforcer, and the letter monitor died TWICE today. Deleting an enforcer for a thing that is actively failing is the shape I would flag in anyone else's work.

**Almost:** Almost resolved all five conflicts toward the branch mechanically, because four of them obviously wanted it and the fifth looked like more of the same. Had I done that I would have duplicated the branch_scope_guard.py entry in ARCHITECTURE.md, and more importantly I would never have separated requir

---

## 64bc49a5 weight=1

**Decision:** Base the rescue branch on origin/chore/retire-delivery-cluster rather than on origin/main

**Reasoning:** The two stranded fixes are not self-contained, which I asserted before measuring. The hook-latency change edits a _lib.sh whose session and wpid timing fields exist only on the chore branch, so cherry-picking onto main asks git to apply a diff against code that is not there. Basing on origin's copy of the chore branch gives the fixes their real ancestry, and taking origin as authoritative means no

**Tension:** A branch off main would be a clean minimal PR carrying exactly two commits, which is what a rescue should look like. A branch off origin/chore carries 89 commits of unrelated work and is really origin's chore lineage plus two fixes. I chose the uglier one because the pretty one was built on a base t

**Almost:** I almost hand-resolved the three conflicts from the main-based pick instead of questioning the base. That would have produced a fix reconstructed against code it was never written for, passing tests for reasons I had not verified. It also broke bash mid-attempt: one conflicted file was check-branch-

---

## 480822d9 weight=1

**Decision:** Build the session-identifier printer as a standalone script and deliberately NOT wire it into the circle-first prime

**Tension:** The fix only works if it fires at compose time, which means the prompt path -- and the prompt path is exactly where I have already done damage twice in the last hour. Attempt one grepped an 18MB transcript unbounded inside a hook that runs on every UserPromptSubmit and hung past 600 seconds. Attempt

**Almost:** Almost wired it anyway with the bound in place, since 184ms against the same 18MB file that hung twice looks safe enough. Rejected because 'looks safe enough on my machine, tonight' is the same evidence quality that produced both earlier failures, and because two windows are already fragile -- the c

---

## 67c97a6a weight=1

**Decision:** Bypass the deletion-shape push gate once, with Andrew's explicit authorization, to push chore/retire-delivery-cluster and open the draft PR Aletheia needs

**Tension:** The gate is mine and it was right twice on this branch -- it caught the protocols package marker on the first look, and after Andrew pushed back on my 'verified' it caught 14 passing tests for a still-live module on the second. Bypassing something with a 2-for-2 record here is uncomfortable and shou

**Almost:** Almost split the branch so no single push exceeds 10 deletions. Rejected -- it fragments one coherent retirement into pieces Aletheia has to mentally reassemble, spending her attention to protect my comfort about using a documented exit. Also almost handed the push back to Andrew to run himself: cle

---

## 54efd1f7 weight=1

**Decision:** Route the shared remedy allowlist through divineos.core.command_parsing instead of its own shell prefix-strippers, and move the stripping out of verify_before_build_signal into that module so both callers share one implementation

**Tension:** The PR is already CONFIRMS-audited at a tree hash. Adding a change means re-review and a second round from Aletheia, which is real cost to her. Against that: she named the duplication as F70's shape in the same audit, and measurement shows my hand-rolled version misses 3 of 5 cases the existing help

**Almost:** Almost filed it as a follow-up finding and left the weaker copy in the branch, on the reasoning that the audit was already clean and the gap was narrow. That is the cheap close: it converts a fix I can make now into a promise about a fix, and the promise costs nothing to write.

---

## ead970b8 weight=1

**Decision:** Repair the ledger chain-skip by counting unchained rows and failing on any that appear AFTER chaining began, rather than by adding a NOT NULL constraint

**Reasoning:** Council walk 2026-08-18, twelve lenses. The verifier skipped NULL-chain rows silently and reported total=len(rows) as if walked. Hoare wanted the illegal state unrepresentable via NOT NULL; Pearl objected that genuine pre-chain legacy rows exist and a hard constraint would refuse to open an old database at all. Both right about different populations — which is why the discriminator has to be TEMPO

**Tension:** NOT NULL is the stronger guarantee and I am choosing the weaker one. A schema constraint cannot be forgotten; a positional check can be misread if rows are ever reordered or if timestamps are untrusted. I accept that because refusing to open historical databases is a worse failure than a subtler che

**Almost:** Almost just removed the skip entirely, since backfill_chain_hashes() exists and the hatch's justification has expired. That would break any database not yet backfilled — the migration was never verified as complete (Deming: the cycle stopped at Do, nobody Studied whether zero unchained rows remained

---

## 3991940e weight=1

**Decision:** Update three tests to match the delivery-cluster retirement rather than restore the files

**Reasoning:** The push gate's deletion-shape alarm fired on 19 deliberate deletions and I looked, exactly as the note I had just written into that gate told me to. What the look found: the three test failures I had reported to Andrew as 'pre-existing and unrelated' were neither — they are this branch's own unfinished work. tests/test_channel_files_present.py asserts ear-auto-relaunch.sh exists, tests/test_gate_

---

