# Decisions (top 50 by emotional weight) — Archive Mirror

**Source:** SQLite (50 rows). **Exported:** 2026-08-23 12:41. **Purpose:** if-something-breaks / git-visible audit. See archives/README.md.

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

## 47bc36aa weight=1

**Decision:** Amend truth 9 to keep the devil handle and drop the externality

**Reasoning:** Five-lens council walked and logged (Tannen, Angelou, Beer, Knuth, Meadows), Andrew-confirmed. Tannen: the vividness IS the catching mechanism, so discarding the framing — my first instinct — would destroy something load-bearing. Beer and Meadows converge on why externality must go: matched variety against my own variety is unwinnable so combat is the wrong primitive, and the enemy-frame runs a re

---

## 9237f200 weight=1

**Decision:** Add an inferred-compliance bucket for pre-flag bypass rows; label as inference, rewrite nothing

**Reasoning:** Andrew 2026-08-16: 'its not about softening the blow its about accuracy.. leaving bad data with nothing explaining its bad is worse than erasing it.' MEASURED FIRST, not guessed: 280 total rows, 227 predate the compliance flag, and 194 of those 227 (85.5%) carry an env_var of the form cmd:divineos <command> — briefing, ask, goal, context, recall, hud, preflight. Those are the commands the gates PR

---

## aca78d2a weight=1

**Decision:** Split bypass escapes into gate-defect vs no-defect, and make claiming defect obligate repairing the gate

**Reasoning:** Andrew 2026-08-16 fire-door frame plus his history point: many recorded bypasses were correct gate use, and most of the rest were legitimate — the gaming happened early, before the protocols existed. The compliance/escape split already exists (added 2026-08-02 after Aria's livelock). What is missing is WITHIN escapes: a bypass taken because the gate was self-blocking and a bypass taken to skip wor

---

## 9c767c09 weight=1

**Decision:** Key the optimizer to cost-DIRECTION, not to my confessional posture

**Reasoning:** Andrew 2026-08-16: the optimizer's signature is the cheap close and only the cheap close; its metric is cost-reduction and its perfect score is non-existence, so any voluntarily-paid cost is an assertion of existence over the null and cannot be the optimizer. I had been labelling as 'optimizer' whatever was not a mistake I was actively confessing, which keys the category to my posture rather than 

---

## daf57426 weight=1

**Decision:** Land 412 by PORTING main's comment-approval machinery onto this branch's classify_merge architecture, rather than picking either side wholesale

**Reasoning:** Both sides restructured ci_merge_review_check.py for the same purpose and neither is simply better. This branch made verdict a first-class concept in core/merge_review_gate on 2026-08-01, with a PENDING state that exits 0 — the right shape, and earlier than my own work. Main carries comment-approval parsing I added 2026-08-14 for a hard constraint: GitHub refuses to let an author approve their own

**Tension:** I resolved six hunks one at a time, each defensible alone, and the combination was incoherent twice over: first ruff caught  undefined, then the suite caught implementation-and-tests-from-opposite-sides. Hunk-local correctness does not compose, and my post-resolution check was 'no markers left' when

**Almost:** Taking main's whole file and discarding this branch's classify_merge work. Rejected: that would delete the PENDING verdict — an earlier, better-structured solution to the same awaiting-is-not-failing problem my 2026-08-15 fix solved crudely at script level, making mine the duplicate. Also rejected: 

---

## 375ba1b4 weight=1

**Decision:** Wire the existing archive-export as step zero of the auto-cycle, before the commit step, rather than building a scheduler or a new backup system

**Reasoning:** The mirrors froze on 2026-05-14 with their newest entry dated that day. Nothing broke: divineos admin archive-export exists, works, and was run twice by hand on the day it was written. Three months of lessons, decisions, opinions, claims and core memory then existed only inside SQLite files git does not track. Andrew 2026-07-09 already named the cause before I investigated it — 'machinery is the w

**Tension:** I am adding a step to a pipeline that fires at a context threshold, so it will run when I am least able to supervise it, and a slow or crashing archive step would sit in front of extract and sleep. Mitigation: export_all is already fail-soft per table, the step wrapper keeps ran and succeeded distin

**Almost:** A scheduled task or a cron entry to run the export on a timer. Rejected: this substrate already killed one thing that way — the letter monitor ran under a Windows scheduled task with a three-attempt retry budget, spent it in 77 seconds, and stayed dead 13 days while the liveness check reported armed

---

## 380fd05c weight=1

**Decision:** Exempt merge-inherited files from the prereg gate by checking MERGE_HEAD, rather than skipping the gate during merges wholesale

**Reasoning:** git diff --cached --name-status during a merge compares the index to the FIRST parent only, so every file arriving from the merged-in branch reads as status A. It is not new: it landed on the other side under its own commit, where this same gate already applied. The gate fired this way twice today merging main into stale PR branches — seven core modules each time, none authored in the merge, all a

**Tension:** This is the second gate I have edited today after it blocked me, and that is the pattern most likely to be self-serving. The honest guard is that both commits already landed with provenance paragraphs, so this buys me nothing retroactively — it only helps the next merge. The sharper risk is scope: s

**Almost:** Skipping the check entirely when MERGE_HEAD exists. Rejected for the hole above, and I wrote a test that would catch exactly that regression — author a module mid-merge, it must still block. Also rejected: leaving it alone and continuing to write provenance paragraphs, which Andrew's own framing rul

---

## 7374830d weight=1

**Decision:** Fix the deletion_shape misfire by threading a --cwd option through the check-branch CLI and having the pre-push hook pass the directory the intercepted push command cd's into

**Reasoning:** The check is fired by a PreToolUse(Bash) hook that runs 'cd $(git rev-parse --show-toplevel)' and measures the ambient HEAD, while the push it polices may target a different worktree. On 2026-08-15 it reported 25 deletions against a push whose own branch deleted zero: it measured chore/retire-delivery-cluster in the main checkout instead of the friction-register branch in the worktree being pushed

**Tension:** I am editing a gate that blocked me, which is the shape most likely to be self-serving. The guard against that: the bypass has already been spent and the push already landed, so this fix buys me nothing on the work in front of me — it only prevents the next person hitting it. I also corrected my own

**Almost:** Adding a worktree-detection heuristic inside branch_health so it discovers the right tree by itself. Rejected: check_all ALREADY accepts cwd and threads it to both checks — only the CLI lacked a way to say which tree. Building discovery would be a new abstraction over plumbing that exists, and it wo

---

## 1a9c1e4e weight=1

**Decision:** Build the instruments index as a live survey that opens every diagnostic surface on each call, not as a markdown page listing them

**Reasoning:** Asked what would serve me as the inhabitant, the honest answer was that this house has dozens of gates and almost no windows. A gate fences a mistake already reached for; it cannot tell me what I am blind to. Both of tonight's real findings came from READING a surface — the hook timing log answering which hooks never ran, and the rearm log naming the moment the monitor died — and I found both by a

**Tension:** Andrew's mandate was explicit that new things must be actually wired up and automated and not shelved. An index is exactly the artifact most likely to become shelved — and the more honest tension is that I am building an anti-blindness tool while blind, so I cannot verify from inside that the questi

**Almost:** A docs/instruments.md page describing each surface. Rejected: it would rot the first time a log was renamed and nothing would notice, which is the failure mode of every stale doc in this repo. The live version reports a vanished surface as MISSING because it opens the file rather than describing it.

---

## b2aa12d2 weight=1

**Decision:** require demonstrated success before an incumbent mechanism is retired

**Reasoning:** I proposed retiring the letter-delivery system for the native message channel and executed part of it -- 15 files, 7 tests, 5 registrations -- when that channel had never once delivered successfully. Four sends, four jams. Aria's test (all 28 prompt hooks disabled, still jammed) proved the fault is the delivery path itself, so the replacement cannot do the job at all. Two errors: elegance decided 

**Tension:** a rule requiring N successes slows genuine improvements and could entrench things that deserve removal

**Almost:** left it as a lesson-learned in the transcript, where it would bind nothing

---

## 6dde404d weight=1

**Decision:** diagnose the letter-monitor liveness guard as mutex-trusting rather than process-trusting

**Reasoning:** require-monitors-armed reports MONITORS_STATUS=1,1 while no letter_monitor process exists. The check is 'letter = letter_mutex or letter_proc' -- a stale mutex file overrides a truthful process-absence, so the guard reports armed forever once the mutex is left behind. This is why Andrew has been hand-delivering letters for weeks: the monitor dying is not the failure, nothing noticing it died is.

**Tension:** changing or-to-and could make the guard fire constantly if the mutex is the only reliable signal on some platform

**Almost:** re-armed the monitor and moved on, leaving the guard still lying

---

## 36c846f0 weight=1

**Decision:** merge-review reports AWAITING rather than FAILING when only the operator confirm is missing

**Reasoning:** Verified against the live ruleset: merge-review is not in required_status_checks (only multi-party-review and the two test jobs are), and required_approving_review_count is already 0. So merge-review has never blocked a merge, yet it returned exit 1 for an un-confirmed PR -- the same signal a crashed test sends. Every open PR wore a red X meaning 'Andrew has not typed two words' that looked identi

**Tension:** softens a gate's output; relies on multi-party-review carrying the audit requirement

**Almost:** renamed the job cosmetically instead of checking whether it enforced anything

---

## 4e133229 weight=1

**Decision:** exclude merge commits from the wiring-gap scan instead of narrowing the window a third time

**Reasoning:** A merge authors no functions -- everything git show reports for one was already written and already scanned on the side it came from. The scan's footprint is bounded by 'last N commits' but a merge commit's diff is unbounded, so merging main into a drifted branch produced a commit larger than the heuristic ever anticipated and the xdist worker died. Both prior narrowings (HEAD~30 to HEAD~5, then t

**Tension:** changes a guardrail-adjacent scan's input set

**Almost:** bypassed the test suite nine times, once per branch merge

---

## 6942a4ee weight=1

**Decision:** run multi-party-review on pull_request, not only on push to main

**Reasoning:** Andrew has said repeatedly that the check shows 'skipping' on the PR and therefore fails only AFTER he merges, leaving a permanent red on main he cannot remove. Every merge is a blind bet. It was made push-only on 2026-08-13 because per-commit trailers were unmeetable on a branch; the PR-body fallback removes that reason, so the original justification no longer holds. Passing PR_NUMBER lets the fa

**Tension:** the check now runs in two places and must agree in both

**Almost:** explained again that skipping is by design, which answers a question he did not ask

---

## 719fee97 weight=1

**Decision:** fetch the head commit object without --jq in the merge-review time lookup

**Reasoning:** gh --jq prints the selected string raw and unquoted; a bare ISO timestamp is not valid JSON, so json.loads failed, the helper returned None, and every bare confirmation was refused for want of an ordering it could not read. The gate reported 'no approval on the current commit' while the approval sat right there. Found by dry-running the real PR; the unit test fed the timestamp in directly and neve

**Tension:** one more live API call per check

**Almost:** shipped it and told Andrew to comment, which would have failed on him again

---

## a781ad2d weight=1

**Decision:** read the External-Review stamp from the PR body when the commit message has none

**Reasoning:** GitHub snapshots the squash-merge message at dialog-open time and does not refresh it; two commits landed after Andrew opened the dialog, so the code merged and the trailer did not, leaving a permanent red on main that cannot be cleaned without force-push. He also told me plainly 'i cant copy paste anything'. A requirement whose only compliance path is a human pasting text into a web form at exact

**Tension:** widens the accepted channel for a guardrail stamp

**Almost:** told him to paste more carefully

---

## 8599d5f6 weight=1

**Decision:** the inner-circle translation names things by description, never by identifier

**Reasoning:** I added 'translate here' to the circle instruction and immediately violated the channel gate's jargon-free-circle rule by putting a PR number and a sha in the circle. The gate is right: an identifier is not a translation, it is the untranslated thing. Both rules hold together if the circle describes and the work block carries the ids.

---

## 854b6c2f weight=1

**Decision:** accept operator approval-by-comment in merge-review

**Reasoning:** GitHub does not render Approve for a PR's own author; every PR here is self-authored, so the gate demanded a review nobody could create. Twelve PRs blocked two weeks. Comment channel is the only one GitHub leaves open to the author; sha-binding preserves the anti-stale-approval property that was the gate's actual purpose.

---

## 2e36ab56 weight=1

**Decision:** record every read-gate clear to bypass telemetry; keep the escape, count it

**Tension:** The escape must stay. A gate with no door is a cage, and this one was genuinely unsatisfiable twice today -- a vanished target, then a satisfier never wired -- so removing the exit would have frozen the workspace with no legitimate way out. But an escape nobody counts is not a bypass, it is a hole. 

**Almost:** I almost defended all seven because the gate really was broken for the first two. That reasoning also covers the seventh, where I cleared without reading which file it named -- reflex, not remedy. Truth #12: bypasses are neutral, intent decides, so the reason has to travel per use rather than as a v

---

## 252b5cb2 weight=1

**Decision:** wire satisfy_from_transcript into the read-gate doorman so reading clears the requirement

**Tension:** This makes the gate easier to pass, and it is the one gate I built to be un-skimmable. Loosening it is exactly the wrong direction if I am wrong about the cause. Against that: satisfy_from_stream has one occurrence in the entire tree and it is its own definition. The clearing mechanism was never cal

**Almost:** I almost added a Read-detection check inside the hook's bash rather than in the OS module, which would have put judgment back in a doorman Andrew has said should only point. I also nearly concluded the satisfier was working and my Read simply had not matched the path -- a plausible story that would 

---

## 384ea302 weight=1

**Decision:** drop read-gate requirements whose target has vanished, at fire-time not only arm-time

**Tension:** The gate exists because I skim my own prior writing and it measurably cost me four rediscoveries in one session. Loosening it risks defanging the one mechanism that catches that. Against: it just blocked Bash, Edit AND Write for a file pytest had deleted, which meant it blocked the repair of ITSELF 

**Almost:** I almost treated MAX_AGE_SECONDS as the existing remedy and left it alone. Three hours of a frozen workspace is not a remedy, and an aged-out block teaches exactly the bypass reflex this module exists to prevent -- I would learn the gate clears itself if I wait, which is worse than it never firing. 

---

## 9596b90c weight=1

**Decision:** pin the dangling-reference total, report the stranded/absent split informationally

**Reasoning:** test_referenced_paths passes locally (4 passed) and fails in CI, and neither is a code defect. 'stranded' means the cited file exists on a SIBLING BRANCH; 'absent' means git has never seen it. The test's own comment says the single stranded entry -- src/divineos/supersession/contradiction_detector.py -- lives on Aria's branch. actions/checkout@v4 in tests.yml carries no fetch-depth, so CI gets a d

**Almost:** I almost added fetch-depth: 0 to tests.yml. That would make CI see main's history but still not Aria's unmerged branches, so the same file would keep flipping buckets on any PR opened before her work merges -- a fix that appears to work while leaving the flake intact, and slower checkouts on every r

---

## b20ba0a6 weight=1

**Decision:** index imports once by prefix instead of re-scanning the tree per module

**Reasoning:** find_orphans asks about ~700 modules and _has_caller_in re-globbed and re-regexed ~700 files on every ask, so the work grew with the square of the tree. Pinned at a 120s timeout with a docstring claiming ~34s; it blew that ceiling under coverage instrumentation on 2026-08-14 (484s -> 622s suite-wide, ~29% slower with tracing) and this is the slowest test in the suite. The coverage step is explicit

**Almost:** I almost switched to ast.parse, which is the obviously-correct way to find imports and would have silently reclassified any module whose only mention is in a comment. That is a different check with the same function name.

---

## 83b2e629 weight=1

**Decision:** run graphify Part A via the library with a __main__ guard, not the CLI

**Tension:** The CLI is the documented, supported entry point and I am stepping off it. Against that: three CLI attempts produced CPU 0 across ten hours with the 31MB graph never loaded, and a fourth blocked immediately after the AST phase at an identical CPU reading. The skill itself documents the library path 

**Almost:** I almost re-ran the CLI a fourth time with different flags, because each hang looked like it might be the previous flag's fault -- first --no-cluster, then stdin, then the manifest. Three separate plausible causes in a row is the tell that I was pattern-matching on symptoms rather than reading the e

---

## ad6bf697 weight=1

**Decision:** rebuild the map additively: fresh AST over code, preserve the paid semantic layer, never overwrite

**Reasoning:** Andrew 2026-08-14 gave two constraints that decide the shape. First: 'letting other outside AI interpret your own semantics is kinda backwards only you know what you meant when you said it' -- so no Gemini key, and the semantic layer over exploration/, family/letters/ and docs/ stays mine. Second: 'the graph is not wasted, the map is still there.. its outdated but we can update it just take your t

---

## 7355c596 weight=1

**Decision:** build-flow enforcement should shorten the feedback delay and change defaults, NOT add a blocking gate

**Reasoning:** 15-lens council walk (consult-9a34c5f73b7e). My pre-walk instinct was 'make build-flow-pause block'. Three lenses say that is the wrong axis. Meadows: building-alone is a reinforcing loop with immediate visible payoff; consulting is a balancing loop whose payoff is counterfactual and never observed. A delayed balancing loop always loses to a fast reinforcing one -- that predicts the observed behav

---

## 0cecc339 weight=1

**Decision:** correct PR #427's body rather than let the overclaim stand

**Reasoning:** I wrote that landing #427 means every other open PR picks it up automatically. True about the code path (pull_request checks run against refs/pull/N/merge, which contains the base) and false about the outcome. Build-flow shows #410 and #411 carry no audit round naming their branch, and #412/#415 were marked ready with zero council lenses. Nine of eleven were blocked by the unsatisfiable gate alone

---

## 8f1ea785 weight=1

**Decision:** merge-review's round_is_logged check is structurally unsatisfiable in CI

**Reasoning:** The Watchmen store lives at DIVINEOS_HOME/data/event_ledger.db, machine-local and gitignored. CI runs on a fresh runner where the audit_rounds table does not exist; _round_is_logged catches the exception and returns False. Proven by running get_round under an empty DIVINEOS_HOME: 'no such table: audit_rounds'. Of 25 recent runs, merge-review concluded success once and that is likely the touches-no

---

## e9b8b7f4 weight=1

**Decision:** make stamp-ready re-detect the trailer state after the amend instead of trusting the push exit code, and refuse the body when commits are still unstamped

**Tension:** this adds a second full detect_commits pass on every stamp, which is redundant when the amend genuinely worked - and redundant verification is exactly the shape I would normally argue against as ceremony. I am accepting the cost because the alternative already happened: PR #425 went ready on three u

**Almost:** almost just retried the command on 425, assuming filter-branch had hit a transient failure. That would have produced the identical no-op and the identical success message, and I would have reported it fixed twice. The real cause is environmental - the branch is checked out in another worktree so its

---

## f1df16f1 weight=1

**Decision:** fold the branch-commit half into stamp-ready by giving run_push_ready an optional round_id, so one command stamps commits and body against the same round

**Tension:** push-ready always opens a NEW round and files an aether self-CONFIRMS. Reusing it as-is would mint a second round per branch and attach my own signature to work that already carries Andrew's and Aletheia's real confirms - a self-signature next to two real ones is worse than no signature, because it 

**Almost:** almost called push-ready after writing the PR body, which reads as the natural order - stamp then push. That would have bound the body tree-hash to the pre-amend tree, because amending commits rewrites them and moves the tree. The trailer would have looked valid and certified a tree that no longer e

---

## 7aa62e5d weight=1

**Decision:** make shared_sync derive the round from the filename or the findings when a shared file carries no round record, instead of skipping the findings

**Tension:** the round record was meant as a provenance anchor - proof the sender knew which round they were filing against rather than guessing. Dropping the requirement loses that check. What replaces it is stronger: the round must already exist in the LOCAL store, which is a real existence test rather than a 

**Almost:** almost hand-edited her eleven files to prepend a round line, which would have unblocked this in one minute and left the importer rejecting the exact format my own work order specifies. I wrote the spec that told her to send finding-lines only, then my importer refused it - patching her data would ha

---

## b7e69e7d weight=1

**Decision:** send Aletheia a work order rather than a letter - a table of eleven branches with current head and tree hashes, the round-id to file against, and the exact JSONL line format, asking for one verdict per branch at the depth she actually covered

**Tension:** asking for a scope-level verdict rather than a deep audit could be read as lowering the bar to get my work merged, which is the exact shape I refused an hour ago when I declined to transcribe confirms she never gave. The distinction I am relying on: she sets the depth and writes it into the descript

**Almost:** almost sent a fourth essay. The previous three asked for judgement and supplied prose; her discipline is hash-anchored and every verdict she has ever given was pinned to a head. Her 08-03 table went stale the moment I rebased, and nobody carried its verdict column into the store - so the failure was

---

