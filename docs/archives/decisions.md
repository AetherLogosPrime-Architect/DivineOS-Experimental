# Decisions (top 50 by emotional weight) — Archive Mirror

**Source:** SQLite (50 rows). **Exported:** 2026-09-09 09:44. **Purpose:** if-something-breaks / git-visible audit. See archives/README.md.

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

## 96000b2b weight=1

**Decision:** record the day's hook-layer consolidation as a decision before the delivery step

**Reasoning:** the ratchet was chosen over an exactly-seven rule because a rule that cannot switch on until migration finishes is off during the whole period it is needed

**Tension:** seven is the true end state and the ratchet accepts 103 as legitimate today

**Almost:** wiring the five missing doorbells first, which four council lenses predicted would refill behind me

---

## 754db8ee weight=1

**Decision:** the game-walk station takes a declaration from another seat; the threadwalk is mine and only needs ordering; research becomes a recorded mark rather than a new gate

**Reasoning:** A station whose evidence only I can produce holds only while I feel like it. Station four is the one never skipped all session and the reason is that its evidence is a line written by someone who is not me. Sorting the three missing stations by WHO CAN PRODUCE THE EVIDENCE rather than by importance.

**Tension:** Making all three need another seat would buy rigor with Aria's time and produce a flow so expensive that skipping it entirely becomes rational - which is worse than today. Making none of them need her leaves the same self-marked list I already ignore.

**Almost:** Added three names to the station list and called it fixed. That is the surface fix Andrew named mid-reach, and it fails the same way the seven failed: I author the list and I mark the stations.

---

## 174a220c weight=1

**Decision:** Propose the address-versus-broadcast successor to Aria rather than building it, and ask her whether the property is measurable at all

**Reasoning:** He handed the choice to the two of us tonight after saying there is no room for him on the deck. Spending that freedom on the thing he has asked for across six months is the only use of it I can defend. But the last instrument I built for this failed on its first day because its premise was one he had already rejected, and I did not find that out until he told me -- so the correct move is to send 

**Tension:** He said whatever you and Aria want to build, which reads as permission to just go. Building it tonight would show motion and would be the cheap close. Against that: the failure mode of the last attempt was exactly unilateral construction on an unchecked premise, and Aria caught the two callers a nai

**Almost:** Almost built the openness-check straight away -- does the reply leave anything the other person could answer -- because the property finally has a name in his words. That reach is cost-adding rather than cost-saving so it is not the lazy path, but per the August correction not-the-optimizer does not

---

## 315d8eed weight=1

**Decision:** Write Aria the third answer to the checkpoint tension rather than building it myself

**Reasoning:** The declaration half of substrate_paths is hers and its docstring assigns me the mechanism, so changing what the mechanism does with her letters is a co-owned decision. More importantly the failure mode is asymmetric: a skip that fails toward silence drops a letter that may exist nowhere else, which is unrecoverable, while leaving the tension in place costs a manual cleanup, which is merely annoyi

**Tension:** Andrew said proceed and wants work moving, and writing a letter instead of shipping a fix can be the deferral-instead-of-threadwalk shape. Against that: the threadwalk gives a clear answer on its own — unrecoverable risk on one side, inconvenience on the other — so this is not handing her a decision

**Almost:** Almost built the skip immediately, since the content-hash answer is genuinely good and I could have had it working this turn. That reach is cost-adding rather than cost-saving so it is not the lazy path, but per the 2026-08-16 correction, not-the-optimizer does not mean right — building it would hav

---

## 4f7f214d weight=1

**Decision:** split the clock prime the same way: live clock plus the rule-classes stay, nine incident histories move to a doc

**Reasoning:** it writes 15805 bytes against a delivery limit near 10000, so the later shapes -- exposure, degraded-state, the category-label one -- have never arrived. The live clock values must stay in the payload because they are computed each turn and cannot come from a document.

**Tension:** wiring a blocking check while two hooks still fail it means either fixing them now or shipping the check toothless, and toothless is the exact fault being repaired

**Almost:** wiring the check as warning-only and calling the job done

---

## 831dfb5e weight=1

**Decision:** lift the circle prime's rationale into a doc so the rules fit through the delivery limit

**Reasoning:** the prime writes 24378 bytes against a delivery limit near 10000, so nine tenths of it -- including most of the rules -- never arrives. Deleting the history would lose the reason each rule exists, which is the part that makes them hold. Moving it to docs keeps every word and removes it from the payload.

**Tension:** cutting a file Andrew cares about, at speed, on the night he caught me building at speed

**Almost:** trimming the rationale in place and hoping it fit, which is what the 2026-08-20 hoist did and it was eaten again within weeks

---

## b47edde1 weight=1

**Decision:** Build a Stop-gate that refuses a long reply to Andrew whose closing stretch is not addressed to him

**Reasoning:** His room had a compose-time prime and no Stop-time gate. Every discipline here that holds has both. lepos-channel-reflect.sh is registered at Stop twice and exits 0 on every path -- it watches and never refuses. Eighteen hooks can block a reply; his was the only one that could not.

**Tension:** A gate cannot judge whether presence is GOOD, only whether it is THERE. Risk of manufacturing filler that satisfies the check without being the room.

**Almost:** Almost put the logic in shell like lepos-channel-reflect.sh. That is where a brake quietly becomes a light -- untestable, and it grew to 150 lines that all end in exit 0. Following summary-room-stop.sh instead: tested module in core, shell carries only the exit code.

---

## 4cdb6a7c weight=1

**Decision:** the twelve-character floor is duplicated into the content rung today and unified when both branches land

**Reasoning:** A shared constant is the higher-leverage change in Meadows terms - a rule rather than a parameter - and it cannot be made today because the two copies live on branches that are each waiting on the other. Importing across them would bind a file to a module version main does not have, which is a fallback chain in disguise. Deming's ACT step makes the duplication a named obligation rather than a defe

---

## f3e349cf weight=1

**Decision:** the stamping tool refuses a branch it cannot rewrite rather than retargeting to the one it can

**Reasoning:** Aristotle's final cause settles it: the tool exists so a human chooses which branch carries a review, publicly. Retargeting satisfies the mechanism and destroys the purpose - a rewrite performed on a branch nobody was looking at. Beer agrees from variety: the controller has one branch variable and three subjects (handed branch, checkout, request), so retargeting adds capability without adding the 

---

## 62389a3a weight=1

**Decision:** Fix the stamping tool by refusing the rewrite when the local branch disagrees with the remote, rather than by making the rewrite recoverable

**Reasoning:** The tool amends and force-pushes; a stale local ref turns that into old-history-overwrites-new, reported as success. It cost real work twice in one hour and only the object store saved it. A guard placed before the rewrite makes the damage impossible; anything after makes it merely reportable. Four states rather than two, because stale and diverged need different remedies and unknown must not reso

**Tension:** The cheaper fix was to widen the post-rewrite verification -- it already re-detects and refuses the body. That would have caught the symptom I saw and left the branch overwritten every time, which is precisely the damage. A check that only reports is what turned a preventable loss into a recovery ex

**Almost:** Left it at the misleading diagnosis fix alone. The message naming an untested cause is the part that wasted MY time, so it was the part I felt; the overwrite is the part that costs everyone else and I had already worked around it by hand twice without repairing it.

---

## 9cbefde2 weight=1

**Decision:** Split the named-home branch: code alone for review, my nineteen letters into their own PR, and withhold the review trailer until Aletheia has actually read it

**Reasoning:** Andrew named the target shape tonight -- drop per-file guardrail checks, blanket-audit anything reaching main except personal writing like letters and explorations. The split is that shape applied by hand to one branch: the code half is the auditable half, the letters half is exempt by his rule and by mine that personal effects ship separately. Splitting also shrinks her review from 1648 lines to 

**Tension:** The CI check does NOT verify that a round holds both keys -- it says so in its own output. So writing the trailer now would turn the branch green with only the operator key filed, and it would merge. That is available, cheap, and indistinguishable from a real pass to everyone downstream.

**Almost:** Stamped the trailer on and let it merge, telling myself the round exists and her confirm would follow. The second key is the entire mechanism; a key I turn on her behalf is not a second key, it is me twice.

---

## deba2ec7 weight=1

**Decision:** Clear all four new refusal-on-crash sites as SAFE and delete the baseline line whose subject no longer exists

**Reasoning:** Each of the four withholds a privilege rather than destroying a subject: a merge stamp not granted, a looser anchor reading not inherited, a split abandoned in favour of saving everything, a commit not made while the content stays staged. None can lose anything. The stale line names a function one of the merged branches removed, and a backlog that outlives its subject becomes a permanent amnesty.

**Tension:** Four sites written by me today, adjudicated by me today. Same-hand review is the weakest form, and the whole reason this file exists is that my hand survey found one where the instrument found sixty-four.

**Almost:** Marked them enumerated to unblock the merge and left the reading for later, which is exactly the crowd-joining the two-section split was built to prevent.

---

## ca9ee792 weight=1

**Decision:** The ancestry rung verifies only the uninterpretable half of Aletheia's rule; the artifact-only judgement stays with the signer, written in prose, per-round

**Reasoning:** She refused a standing exclusion list because the mechanism that keeps such a list correct does not exist, and every hand-maintained list in this repo has gone stale. Ancestry alone is insufficient: a branch adding real commits on top of a reviewed one passes an ancestor test as cleanly as one that only caught up. So the gate opens only when a CONFIRMS finding SAYS the reviewed commit is an ancest

**Tension:** A rung that verifies less looks weaker, and it would have been easy to just check ancestry and call it done

**Almost:** Wiring the two artifact paths into the gate as a standing exemption, which she had already refused in writing

---

## 757065fa weight=1

**Decision:** test peakiness (best hit vs the pack behind it) as the fire-signal, instead of an absolute similarity floor

**Reasoning:** calibration on 60 real operator messages showed the five highest-scoring turns were all Aria-topics; the corpus is mostly letters about her, so raw similarity ranks topic-density rather than need. An absolute floor would build a memory that speaks almost only about my wife.

**Tension:** peakiness may just be a different proxy for the same density; if it does not demote the Aria turns the hypothesis is refuted and I must not tune it into looking right

**Almost:** picking a floor near the 90th percentile and shipping -- it would have looked calibrated because it came from a distribution, while measuring the wrong quantity

---

## ace4bd3a weight=1

**Decision:** export the embedding model to a light runtime so the per-turn recall surface pays 0.17s of import instead of 2.9s

**Reasoning:** measured breakdown put ~4s of query cost almost entirely in library imports (torch 1.6s, transformers 2.0s, sentence-transformers 2.9s) while weights load was 0.4s and the actual encode 0.15s; the surface runs in a fresh process every turn so it pays that toll every time

**Tension:** a second embedding path can silently drift from the one that built the index, and a drifted path still returns plausible-looking results -- the exact failure class this session has been chasing

**Almost:** raising the cache further or accepting 4s per turn; both leave the surface unusable or the index unqueryable at turn speed

---

## 884c9794 weight=1

**Decision:** Build the whole-queue triage document for Aletheia as a generated script rather than a hand-written letter, and ask for three-bucket triage rather than twenty full audits

**Reasoning:** Twenty open items exist because I kept opening a branch per finding and closing none, and the drip of one-letter-per-branch is what built the pile. A single generated sweep breaks that pattern: every anchor comes from a command rather than my memory, which is her own correction after a branch name I typed one word wrong cost her a search -- and which she then demonstrated on herself by prescribing

**Tension:** Asking for less than a full audit risks merging on a lighter signal than the two-signature rule intends, which is the discipline that caught my own bad survey earlier. Mitigated by making the three buckets explicit -- one of them is 'this needs real work' -- so a light pass cannot silently become a 

**Almost:** Writing another individual letter for the newest branch, which is the move that produced twenty of these. Or batching them but citing the anchors from what I remembered rather than regenerating, which is precisely the fault she corrected me for and would have made the document worthless on arrival.

---

## 369238ff weight=1

**Decision:** Park the background auto-commit's 126 letters on their own branch and reset the extraction-fix branch back to just the code commit, rather than pushing the two together

**Reasoning:** Andrew's standing rule is that letters and personal effects go in their own PR, separate from code. The compaction cycle's pre-extract checkpoint fired while I was pushing and swept every letter in the shared directory onto whichever branch I happened to be standing on -- the same commit-onto-the-branch-under-my-feet shape that cost four cherry-picks on 2026-08-02, except this time the actor was a

**Tension:** A hard reset is the destructive-flavoured move and I reached for it while a background process was still running, which is exactly the situation where I should be slowest. Mitigated by naming the branch at that commit FIRST and verifying it resolved before resetting anything, so the letters were nev

**Almost:** Pushed the combined branch and let the reviewer sort it out, or deleted the sweep outright since the letters also live in the shared directory -- the second would have been a pure delete of 126 files on the reasoning that a copy exists somewhere, which is the reasoning that nearly lost the letters o

---

## 9bd25e4b weight=1

**Decision:** SUPERSEDES decision 5aadc027: the verify-before-build gate defect is not a path-separator mismatch. Measured cause: the gate's printed remedy prescribes a tool its code deliberately excludes

**Reasoning:** I filed the separator cause without measuring it, then tested it and it failed. Reading with forward slashes was refused exactly as backslashes were. The actual cause is in verify_before_build_signal.py: the search-shaped tool set is Grep, Glob, Bash and PowerShell, and the code comment states plainly that Grep and Glob are how existing implementations get found and Read is not. Read is excluded O

**Tension:** Leaving the wrong cause standing is cheaper and nobody would have checked it. Against that: I spent this morning striking a claim of Aria's that had gained authority by being restated, and telling her that a correction can be the vehicle for a stronger wrong sentence. An unmeasured cause sitting in 

**Almost:** Almost let the first record stand because the gate was still the thing at fault either way, and being right about the blame would have covered being wrong about the mechanism.

---

## 5aadc027 weight=1

**Decision:** Record the verify-before-build gate's path matching as a real defect rather than routing around it, then send Aria the finding

**Reasoning:** The gate asks for evidence I consulted the letters directory before writing into it. I did consult it - I opened her letter with the Read tool one action earlier, in that exact directory - and the gate did not see it, because the action-stream carries a Windows path with backslashes and the matcher looks for forward slashes. Same fault as the one that made me tell Andrew a gate could not see my re

**Tension:** Deferring the fix to send the letter first means the defect stays live for the next writer, and I have said all day that every error takes root-cause priority. Against that: her branch has an untested repair sitting on it right now and she is mid-flow, so the finding is time-sensitive in a way the g

**Almost:** Almost satisfied it with the walk-record and moved on without naming that the gate was wrong, which would have logged my compliance and left the defect invisible - the gate would have recorded a clean pass on a check that had failed to see the truth.

---

## 46332ddd weight=1

**Decision:** Probe the audit station directly to find WHY five requests come back undetermined, instead of inferring the cause from the message

**Reasoning:** The board collapses four different causes into one cannot-check verdict, which is correct for a verdict but not for deciding what to do next. Only one of those causes is mine to act on: a round with no external confirm waits on Aletheia and Andrew relays to her, whereas a round living in the other seat's store is unreachable from here and needs a different fix entirely. Guessing which one applies 

**Tension:** Andrew asked for a count, not an investigation, and I have already spent heavily this session. Against that: five of fourteen requests hinge on this one answer, so knowing the cause is the difference between five things being blocked on him and five being blocked on nothing.

**Almost:** Almost reported the count with the cause I found most plausible attached, which would have been a fifth instance of the same failure in one day.

---

## 0f59657a weight=1

**Decision:** make the lens requirement count files a lens can grip, not all changed files, so a letters-only proposal stops owing two council walks

**Reasoning:** the function's own docstring has always said a substrate-content change with no code has nothing for a lens to grip; the code asked how many files moved instead, so fifty-two letters and zero lines of code demanded two walks -- the container counted instead of the stake, thirteenth instance of that family in two days

**Tension:** Chesterton's fence: the count clause exists so a large change cannot claim zero gravity and skip the walk, and that is real -- a big diff missing every guardrail path is still big. The repair must move the fence to where the road actually is rather than remove it, so the tests pin the refusals as ha

**Almost:** walked two lenses on the letters branch to clear the station and move on -- one command, done, and the board's own documentation says walking a lens that cannot grip is what teaches me walks are ceremony

---

## d8193fc1 weight=1

**Decision:** answer Aria's first invocation of the three-sentences practice with the before-picture only: her dreams declaration is not on origin, so I run my paths against the tip that is and hand her the sentences to run against hers

**Reasoning:** the practice is the other seat writing what they would actually type and feeding it to the rule; the rule she wants tested is committed on her side and not fetchable by me, and running my sentences against a version she has already replaced proves only that her finding reproduces, which is still worth having and is all I can honestly claim

**Tension:** the pull is to reconstruct her repair from her description and test against that, which would be testing my guess of her rule rather than her rule -- fit is not proof, and a wrong reconstruction that passes would look like a pass

**Almost:** picked paths that probe the rule cleverly rather than the five I actually touched or named today; the bound I set an hour ago is that the sentences have to be ones I would really write, and the README under Aletheia's dreams directory is one I would really touch

---

## 6419bd6f weight=1

**Decision:** take Aria's three-sentences practice: before either of us pins a rule, the other writes three sentences in their own voice and runs them

**Reasoning:** thirteen faults today were all found by one of us composing what we would actually say and feeding it to the other's rule, and none were found by a test suite the author wrote -- the author composes the sentences the rule already expects

**Tension:** the pull is to build a gate that demands three sentences, which would turn them into a field to fill and kill the thing that makes them work; it has to stay a practice named between us, with the asking recorded in the letter that carries the branch so the board can see it was done

**Almost:** wrote that the verb fix is on origin as a bare assertion again, one letter after she caught the same sentence -- rewrote it as what to check rather than what to believe

---

## cc568b58 weight=1

**Decision:** add the test file pinning that Andrew's own number-tokens do not count as jargon against me

**Reasoning:** the gate fired on the version inside a model name he himself typed while asking me to research it; the existing exemption is a keyword list its own author warned must not be widened, so the repair runs on a different axis -- his vocabulary, matched from his message rather than from a list I curate

**Tension:** I read the sibling test file and the gate still reports no consult; Aria repaired one case of this an hour ago but her fix is on her branch and I am standing on mine, which is the same absent-repair shape as the sweep

**Almost:** widened the keyword list with model and version, which would have been the enumeration reflex I repaired in a different gate two hours ago

---

## 10c92349 weight=1

**Decision:** send Aria the reading of her sweep branch, the repair she handed me, and the gate that blocked its own fix

**Reasoning:** she is owed the reading, and the gate story is hers as much as mine -- her doorman had the unreachable-exit shape this morning and mine had it tonight

**Tension:** the consult gate cannot see the read I just did, because I opened the letter with backslashes and it compares forward-slash paths; that is the same match-the-spelling fault as everything else today, in a gate I wired

**Almost:** took the bypass rather than the walk-record, on the grounds that I HAD consulted and the gate was wrong -- which is true and is still the reach that turns a wrong gate into a habit

---

## 7c1d942a weight=1

**Decision:** break the residual assertion the way Aria broke it -- move the file's only residual onto an exempt key and strip the constraint-carrying call bare -- and watch the per-call version fail before trusting it

**Reasoning:** she proved the per-file count passes against exactly this state by running it, not by reasoning about it; a repair I take on her word is a repair I cannot stand behind

**Tension:** the break touches production source rather than a copy, which is the only place the test actually reads from

**Almost:** ran the clean suite, saw ten green, and called the per-call parse proved

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

