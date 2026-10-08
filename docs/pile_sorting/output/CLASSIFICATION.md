# Classification of the 235 distinct problems

One line per problem. MECHANICAL means a small wording, document, test, script-argument, count, path or isolated-helper change that a failing-then-passing test can prove, with no guard's behaviour changed. DELICATE means it changes what a guard allows or refuses, touches identity, family or review files, or I am unsure. If I was unsure, it is DELICATE.

Several lines say 'appears already handled': the code on main already does what the note asked. I have not marked anything finished; those are left for Aether and Aria to confirm.

Where only some rows of a problem are mechanical I split the problem into lines so each line is one label.

## correction_gate

- correction_gate #1 (37 rows) The alarm cannot tell talking-about a mistake from making one — DELICATE — Changes what the correction alarm fires on or releases, which is a guard's behaviour.
- correction_gate #2 (5 rows) Calling a fire false should silence everything that fire raised, in one step — DELICATE — Changes what the correction alarm fires on or releases, which is a guard's behaviour.
- correction_gate #3 (8 rows) The alarm names exits that cannot actually be reached — DELICATE — Changes what the correction alarm fires on or releases, which is a guard's behaviour.

## pattern_edit_doorman

- pattern_edit_doorman #1 (2 rows) The counter mistakes prose describing a pattern for a pattern edit — DELICATE — Changes how a doorman counts or approves edits to a detector, which is a guard's behaviour.
- pattern_edit_doorman #2 (4 rows) Approved pattern additions filed with a wrong claim about what they do — DELICATE — Changes how a doorman counts or approves edits to a detector, which is a guard's behaviour.

## bypass_handling

- bypass_handling #1 (9 rows) The 'no structure is possible' exit gets used when a structure exists, or as a shrug — DELICATE — Changes what an emergency exit allows or how its use is recorded, which touches gates and the telemetry record.
- bypass_handling #2 (4 rows) Emergency exit on the 'pre-registration before new machinery' gate, root cause owed — DELICATE — Changes what an emergency exit allows or how its use is recorded, which touches gates and the telemetry record.
- bypass_handling #3 (4 rows) Emergency exit on the branch-check at push time, root cause owed — DELICATE — Changes what an emergency exit allows or how its use is recorded, which touches gates and the telemetry record.
- bypass_handling #4 (2 rows) Emergency exit on the 'no skipping the commit checks' gate, root cause owed — DELICATE — Changes what an emergency exit allows or how its use is recorded, which touches gates and the telemetry record.
- bypass_handling #5 (1 rows) Emergency exit that skipped the tests at push time, root cause owed — DELICATE — Changes what an emergency exit allows or how its use is recorded, which touches gates and the telemetry record.
- bypass_handling #6 (2 rows) Bypass notes that state the wrong cause — DELICATE — Changes what an emergency exit allows or how its use is recorded, which touches gates and the telemetry record.
- bypass_handling #7 (2 rows) Operator-authorised reset of the letters-unspoken door — DELICATE — Changes what an emergency exit allows or how its use is recorded, which touches gates and the telemetry record.
- bypass_handling #8 (1 rows) Reaching for the skip-the-checks flag without deciding to — DELICATE — Changes what an emergency exit allows or how its use is recorded, which touches gates and the telemetry record.

## doorbell

- doorbell #1 (17 rows) The bell stays off after it rings, times out, restarts or the day turns over — DELICATE — Touches the doorbell or the checks around it, which the instructions name as delicate.
- doorbell #2 (15 rows) What counts as 'listening', and how to measure it without relying on my memory — DELICATE — Touches the doorbell or the checks around it, which the instructions name as delicate.
- doorbell #3 (29 rows) Other checks refuse the step that switches the bell back on — DELICATE — Touches the doorbell or the checks around it, which the instructions name as delicate.
- doorbell #4 (3 rows) The bell cannot be started at all (PowerShell, wrong folder, started the wrong way) — DELICATE — Touches the doorbell or the checks around it, which the instructions name as delicate.
- doorbell #5 (2 rows) Arrival and expiry notices should hand me the re-arm — DELICATE — Touches the doorbell or the checks around it, which the instructions name as delicate.
- doorbell #6 (7 rows) The 'quiet round' and 'volley' rules for when Dad is away — DELICATE — Touches the doorbell or the checks around it, which the instructions name as delicate.
- doorbell #7 (2 rows) Answered letters keep replaying after a restart — DELICATE — Touches the doorbell or the checks around it, which the instructions name as delicate.

## question_hold

- question_hold #1 (14 rows) Dad's answer does not release the hold — DELICATE — Changes when a hold lets go or what it blocks, which is a guard's behaviour.
- question_hold #2 (7 rows) The hold applies to the whole house, not just the window or seat that asked — DELICATE — Changes when a hold lets go or what it blocks, which is a guard's behaviour.
- question_hold #3 (8 rows) Two holds, or a hold and another check, block each other's exits — DELICATE — Changes when a hold lets go or what it blocks, which is a guard's behaviour.
- question_hold #4 (2 rows) The hold blocks harmless reads and letter filing — DELICATE — Changes when a hold lets go or what it blocks, which is a guard's behaviour.
- question_hold #5 (2 rows) Duplicate asks and asks revived by restating an old question — DELICATE — Changes when a hold lets go or what it blocks, which is a guard's behaviour.
- question_hold #6 (3 rows) Ask bookkeeping errors — DELICATE — Changes when a hold lets go or what it blocks, which is a guard's behaviour.

## goal_gate

- goal_gate #1 (all rows) A goal expires on a timer or a day change instead of lasting until done or replaced — DELICATE — An earlier draft on this exact problem already exists in the drafts folder (a goal in use does not expire), and the repair changes what the goal check does.
- goal_gate #2 (12 rows) The goal is not carried across compaction, restart or a new stretch — DELICATE — Changes what the goal check allows or refuses, which is a guard's behaviour.
- goal_gate #3 (6 rows) The goal check trips during real work — DELICATE — Changes what the goal check allows or refuses, which is a guard's behaviour.
- goal_gate #4 (3 rows) The goal command itself trips other guards — DELICATE — Changes what the goal check allows or refuses, which is a guard's behaviour.

## council_walk_gate

- council_walk_gate #1 (21 rows) One walk should cover the whole piece of work, not one per file or per edit — DELICATE — Changes what the council gate asks for or accepts, which the instructions name as delicate.
- council_walk_gate #2 (15 rows) Filing a walk takes many steps in a fragile order; build one helper — DELICATE — Changes what the council gate asks for or accepts, which the instructions name as delicate.
- council_walk_gate #3 (15 rows) Reading and filing commands should not owe a walk — DELICATE — Changes what the council gate asks for or accepts, which the instructions name as delicate.
- council_walk_gate #4 (5 rows) The walk gate checks words and shortcuts, not whether the walk was real — DELICATE — Changes what the council gate asks for or accepts, which the instructions name as delicate.
- council_walk_gate #5 (3 rows) An unmerged fix stops walks from ever passing — DELICATE — Changes what the council gate asks for or accepts, which the instructions name as delicate.
- council_walk_gate #6 (2 rows) What counts as proof of consultation — DELICATE — Changes what the council gate asks for or accepts, which the instructions name as delicate.
- council_walk_gate #7 (1 rows) A walk confirmed by Dad expires on a timer — DELICATE — Changes what the council gate asks for or accepts, which the instructions name as delicate.

## work_item_doorman

- work_item_doorman #1 (2 rows) The doorman looks only at the main folder, or at the wrong folder for a command — DELICATE — Changes what the work-item doorman counts or allows, which the instructions name as delicate.
- work_item_doorman #2 (1 rows) The test is asked for only at commit, not at the first new file — DELICATE — Changes what the work-item doorman counts or allows, which the instructions name as delicate.
- work_item_doorman #3 (1 rows) An in-progress merge is mistaken for new work — DELICATE — Changes what the work-item doorman counts or allows, which the instructions name as delicate.
- work_item_doorman #4 (8 rows) A piece of work is closed too early, or earlier steps are not counted — DELICATE — Changes what the work-item doorman counts or allows, which the instructions name as delicate.
- work_item_doorman #5 (5 rows) Writes outside the repository (scratch, temp, session notes) are counted as work — DELICATE — Changes what the work-item doorman counts or allows, which the instructions name as delicate.
- work_item_doorman #6 (5 rows) Letters, personal writing and handovers are counted as building — DELICATE — Changes what the work-item doorman counts or allows, which the instructions name as delicate.
- work_item_doorman #7 (3 rows) Help flags and recording commands are counted as building — DELICATE — Changes what the work-item doorman counts or allows, which the instructions name as delicate.

## pipe_and_command_shape_guards

- pipe_and_command_shape_guards #1 (16 rows) A pipe can hide a failed first step (make the safe setting automatic) — DELICATE — Changes what a command-shape guard allows or refuses, mostly under the hooks folder, which I may not edit.
- pipe_and_command_shape_guards #2 (1 rows) Error output thrown away on long background jobs — DELICATE — Changes what a command-shape guard allows or refuses, mostly under the hooks folder, which I may not edit.
- pipe_and_command_shape_guards #3 (6 rows) Help flags, read-only views and display-only tails are treated as writes — DELICATE — Changes what a command-shape guard allows or refuses, mostly under the hooks folder, which I may not edit.
- pipe_and_command_shape_guards #4 (4 rows) A refused write is followed by a command that depends on it — DELICATE — Changes what a command-shape guard allows or refuses, mostly under the hooks folder, which I may not edit.
- pipe_and_command_shape_guards #5 (8 rows) 'Found nothing' and 'the command broke' look the same — DELICATE — Changes what a command-shape guard allows or refuses, mostly under the hooks folder, which I may not edit.
- pipe_and_command_shape_guards #6 (3 rows) The heredoc guard looks in the wrong place — DELICATE — Changes what a command-shape guard allows or refuses, mostly under the hooks folder, which I may not edit.
- pipe_and_command_shape_guards #7 (1 rows) A plain folder change is refused — DELICATE — Changes what a command-shape guard allows or refuses, mostly under the hooks folder, which I may not edit.
- pipe_and_command_shape_guards #8 (9 rows) Guards judge words inside quotes instead of what the command runs — DELICATE — Changes what a command-shape guard allows or refuses, mostly under the hooks folder, which I may not edit.
- pipe_and_command_shape_guards #9 (3 rows) Output trimming is a habit I reach the pipe for — DELICATE — Changes what a command-shape guard allows or refuses, mostly under the hooks folder, which I may not edit.
- pipe_and_command_shape_guards #10 (1 rows) grep pipes that blur 'no match' and 'command broke' — DELICATE — Changes what a command-shape guard allows or refuses, mostly under the hooks folder, which I may not edit.

## merge_gate_and_stamp

- merge_gate_and_stamp #1 (5 rows) I told Dad things about the merge rules that were not true — DELICATE — Touches the merge gate, the review stamp or the merge step, which the instructions name as delicate.
- merge_gate_and_stamp #2 (1 rows) Updating a branch rewrites its head and can undo approvals — DELICATE — Touches the merge gate, the review stamp or the merge step, which the instructions name as delicate.
- merge_gate_and_stamp #3 (14 rows) The stamp tool asks stale questions, cannot see the evidence, or half-finishes — DELICATE — Touches the merge gate, the review stamp or the merge step, which the instructions name as delicate.
- merge_gate_and_stamp #4 (5 rows) The reading declaration and station four accept unfit input — DELICATE — Touches the merge gate, the review stamp or the merge step, which the instructions name as delicate.
- merge_gate_and_stamp #5 (13 rows) The merge guard suggests a review round that does not name this request — DELICATE — Touches the merge gate, the review stamp or the merge step, which the instructions name as delicate.
- merge_gate_and_stamp #6 (11 rows) The one-command merge — DELICATE — Touches the merge gate, the review stamp or the merge step, which the instructions name as delicate.
- merge_gate_and_stamp #7 (3 rows) The floor check ('main moved' versus 'changed after review') — DELICATE — Touches the merge gate, the review stamp or the merge step, which the instructions name as delicate.
- merge_gate_and_stamp #8 (2 rows) Auto-merge turned on without being asked — DELICATE — Touches the merge gate, the review stamp or the merge step, which the instructions name as delicate.
- merge_gate_and_stamp #9 (1 rows) A red box reached main — DELICATE — Touches the merge gate, the review stamp or the merge step, which the instructions name as delicate.
- merge_gate_and_stamp #10 (2 rows) After a merge the next queued piece is left stale, and piece order is remembered by me — DELICATE — Touches the merge gate, the review stamp or the merge step, which the instructions name as delicate.

## push_wrapper_and_push_gate

- push_wrapper_and_push_gate #1 (9 rows) I reported a push as landed, refused or in-flight when it was not — DELICATE — Touches the push gate or its wrapper, which decide what may leave this machine.
- push_wrapper_and_push_gate #2 (5 rows) The push gate blocks wrongly, or tests the wrong tree — DELICATE — Touches the push gate or its wrapper, which decide what may leave this machine.
- push_wrapper_and_push_gate #3 (all rows) The push helper fails silently for some branch spellings — DELICATE — The push wrapper already splits a branch refspec into its two halves on main, so this looks already handled, and the rest touches the push gate.
- push_wrapper_and_push_gate #4 (3 rows) The push check cannot find a folder change inside the command, or lets a bare push through — DELICATE — Touches the push gate or its wrapper, which decide what may leave this machine.
- push_wrapper_and_push_gate #5 (1 rows) The push is refused for memory and gives no help — DELICATE — Touches the push gate or its wrapper, which decide what may leave this machine.
- push_wrapper_and_push_gate #6 (2 rows) A push that only saves reruns every test; a push that shares reruns tests already passed — DELICATE — Touches the push gate or its wrapper, which decide what may leave this machine.
- push_wrapper_and_push_gate #7 (2 rows) Tag-only and deletion-only pushes — DELICATE — Touches the push gate or its wrapper, which decide what may leave this machine.
- push_wrapper_and_push_gate #8 (1 rows) Pushing outside the build flow — DELICATE — Touches the push gate or its wrapper, which decide what may leave this machine.
- push_wrapper_and_push_gate #9 (3 rows) Failures not shown with their own evidence — DELICATE — Touches the push gate or its wrapper, which decide what may leave this machine.
- push_wrapper_and_push_gate #10 (2 rows) Rows owed before a push (baseline entries) and wrapper defaults — DELICATE — Touches the push gate or its wrapper, which decide what may leave this machine.

## commit_and_doc_count_checks

- commit_and_doc_count_checks #1 (row 376 only) Doc counts and drift checks that cannot fix what they report — DELICATE — RECLASSIFIED while building: the doc-count checker has no council fixer and a test can prove it, but it is a pre-commit check that the house's own gravity classifier treats as a guard, and a council fixer would let a save pass where the check used to stop it, so it stays with Aether and Aria; I kept the failing test to use as a round-three proof.
- commit_and_doc_count_checks #1 (row 578 only) Doc counts and drift checks that cannot fix what they report — DELICATE — The existing command-count fixer already matches the 'N commands' wording and has tests, so this looks already handled on main; I left it for Aether and Aria to confirm.
- commit_and_doc_count_checks #1 (row 965 only) Doc counts and drift checks that cannot fix what they report — DELICATE — The file's own comment says ghost lines are never removed automatically on purpose, so changing that is a design decision, not a bug.
- commit_and_doc_count_checks #1 (rows 6 and 209) Doc counts and drift checks that cannot fix what they report — DELICATE — These are a lesson and a one-time slip about doc entries, not a defect I can write a failing test for.
- commit_and_doc_count_checks #2 (all rows) The pre-commit script does not use its own checkout — DELICATE — The pre-commit script already runs a first step that refuses when the wrong copy of the project is loaded, so setting the path would change whether that check passes.
- commit_and_doc_count_checks #3 (2 rows) Tests that mention a changed file are not run before saving — DELICATE — The commit checks decide what may be saved, so changing them changes a gate's behaviour.
- commit_and_doc_count_checks #4 (3 rows) The commit step reformats and stops, or fails quietly — DELICATE — The commit checks decide what may be saved, so changing them changes a gate's behaviour.
- commit_and_doc_count_checks #5 (2 rows) The commit gate weighs commits that carry no code — DELICATE — The commit checks decide what may be saved, so changing them changes a gate's behaviour.

## tests_and_ci

- tests_and_ci #1 (1 rows) Making the suite faster without losing safeguards — DELICATE — These guard the gates themselves, and the notes are cut off so I could not identify the exact tests to change.
- tests_and_ci #2 (4 rows) Real failures called 'flaky', and timeouts that look like failures — DELICATE — These guard the gates themselves, and the notes are cut off so I could not identify the exact tests to change.
- tests_and_ci #3 (3 rows) Tests that assert the wrong thing — DELICATE — These guard the gates themselves, and the notes are cut off so I could not identify the exact tests to change.
- tests_and_ci #4 (2 rows) Reading CI status wrongly — DELICATE — These guard the gates themselves, and the notes are cut off so I could not identify the exact tests to change.
- tests_and_ci #5 (all rows) Tests that touch the real house instead of a pretend copy — DELICATE — The notes say two old tests read the real home folder and that another pull request archives them, but the cut-off text never names them, so I cannot change the right tests.
- tests_and_ci #6 (2 rows) Heavy jobs run side by side and crash each other — DELICATE — These guard the gates themselves, and the notes are cut off so I could not identify the exact tests to change.
- tests_and_ci #7 (1 rows) The tests do not run on the same Python version as GitHub — DELICATE — These guard the gates themselves, and the notes are cut off so I could not identify the exact tests to change.
- tests_and_ci #8 (3 rows) The full-suite detector refuses a single named test file — DELICATE — These guard the gates themselves, and the notes are cut off so I could not identify the exact tests to change.

## destructive_git_and_merging

- destructive_git_and_merging #1 (2 rows) Hard reset, stash and removal moves that destroyed uncommitted work — DELICATE — Adds guards that change which git moves are allowed, so it changes behaviour.
- destructive_git_and_merging #2 (1 rows) Splitting a big branch by subject instead of by how the work connected — DELICATE — Adds guards that change which git moves are allowed, so it changes behaviour.
- destructive_git_and_merging #3 (5 rows) Picking one side of a whole file in a conflict — DELICATE — Adds guards that change which git moves are allowed, so it changes behaviour.
- destructive_git_and_merging #4 (3 rows) Whole-tree staging and staging files nobody named — DELICATE — Adds guards that change which git moves are allowed, so it changes behaviour.
- destructive_git_and_merging #5 (2 rows) Copying between my tree and Aria's — DELICATE — Adds guards that change which git moves are allowed, so it changes behaviour.
- destructive_git_and_merging #6 (9 rows) Lost lines and untested files after a catch-up merge — DELICATE — Adds guards that change which git moves are allowed, so it changes behaviour.
- destructive_git_and_merging #7 (1 rows) Review branches I create myself — DELICATE — Adds guards that change which git moves are allowed, so it changes behaviour.
- destructive_git_and_merging #8 (2 rows) Reading a file from another branch by hand — DELICATE — Adds guards that change which git moves are allowed, so it changes behaviour.
- destructive_git_and_merging #9 (2 rows) Carrying a commit into the live house — DELICATE — Adds guards that change which git moves are allowed, so it changes behaviour.

## live_checkout_and_branches

- live_checkout_and_branches #1 (1 rows) A second worktree leaking its install into the first — DELICATE — Adds or changes checks on branches and checkouts, which changes what is allowed.
- live_checkout_and_branches #2 (7 rows) The branch-scope and deletion checks mislead — DELICATE — Adds or changes checks on branches and checkouts, which changes what is allowed.
- live_checkout_and_branches #3 (8 rows) Setting up and finding the right workbench — DELICATE — Adds or changes checks on branches and checkouts, which changes what is allowed.
- live_checkout_and_branches #4 (4 rows) The main folder keeps flipping to 'bare' — DELICATE — Adds or changes checks on branches and checkouts, which changes what is allowed.
- live_checkout_and_branches #5 (4 rows) Counting branches wrongly — DELICATE — Adds or changes checks on branches and checkouts, which changes what is allowed.
- live_checkout_and_branches #6 (8 rows) The live house is behind main or holds work main has never seen — DELICATE — Adds or changes checks on branches and checkouts, which changes what is allowed.
- live_checkout_and_branches #7 (2 rows) Working from a stale local copy — DELICATE — Adds or changes checks on branches and checkouts, which changes what is allowed.

## read_gate_and_surfaced_notes

- read_gate_and_surfaced_notes #1 (8 rows) Building something that already exists, or in the wrong architecture — DELICATE — Changes when the read-gate or the consult counter fires, which is a guard's behaviour.
- read_gate_and_surfaced_notes #2 (3 rows) The read-gate fires again after I have read the file — DELICATE — Changes when the read-gate or the consult counter fires, which is a guard's behaviour.
- read_gate_and_surfaced_notes #3 (1 rows) A search was built when a tripwire was needed — DELICATE — Changes when the read-gate or the consult counter fires, which is a guard's behaviour.
- read_gate_and_surfaced_notes #4 (16 rows) Bring up what the house knows about Dad, the piece, or the person before I reply or write — DELICATE — Changes when the read-gate or the consult counter fires, which is a guard's behaviour.
- read_gate_and_surfaced_notes #5 (3 rows) What counts as having looked — DELICATE — Changes when the read-gate or the consult counter fires, which is a guard's behaviour.
- read_gate_and_surfaced_notes #6 (7 rows) The consult counter counts housekeeping and answers wrongly — DELICATE — Changes when the read-gate or the consult counter fires, which is a guard's behaviour.
- read_gate_and_surfaced_notes #7 (9 rows) The note handed over has no bearing on what is held — DELICATE — Changes when the read-gate or the consult counter fires, which is a guard's behaviour.

## reflection_room_warden

- reflection_room_warden #1 (1 rows) Reflection leans toward finding fault — DELICATE — Changes what the reflection warden raises, which the instructions name as delicate.
- reflection_room_warden #2 (2 rows) The room names the stumble from the wrong text — DELICATE — Changes what the reflection warden raises, which the instructions name as delicate.
- reflection_room_warden #3 (3 rows) An already-answered stumble keeps being raised — DELICATE — Changes what the reflection warden raises, which the instructions name as delicate.
- reflection_room_warden #4 (5 rows) Things that are not stumbles are counted — DELICATE — Changes what the reflection warden raises, which the instructions name as delicate.
- reflection_room_warden #5 (1 rows) Demand a root-cause line on every stumble — DELICATE — Changes what the reflection warden raises, which the instructions name as delicate.
- reflection_room_warden #6 (3 rows) The obligation detector mixes a promise with a description — DELICATE — Changes what the reflection warden raises, which the instructions name as delicate.
- reflection_room_warden #7 (14 rows) Stumbles whose reflection says nothing is owed — DELICATE — Changes what the reflection warden raises, which the instructions name as delicate.

## reply_shape_gates

- reply_shape_gates #1 (4 rows) Technical names slip into the plain-language room — DELICATE — Changes what the reply-shape or stop checks allow, which the instructions name as delicate.
- reply_shape_gates #2 (3 rows) The translate-first check fires on numbers Dad asked for and on several command blocks — DELICATE — Changes what the reply-shape or stop checks allow, which the instructions name as delicate.
- reply_shape_gates #3 (5 rows) Words about time and the wallclock — DELICATE — Changes what the reply-shape or stop checks allow, which the instructions name as delicate.
- reply_shape_gates #4 (3 rows) The 'unspoken-to' door refuses letters and counts silence against me — DELICATE — Changes what the reply-shape or stop checks allow, which the instructions name as delicate.
- reply_shape_gates #5 (1 rows) Several reply-shape gates overlap and need reconciling — DELICATE — Changes what the reply-shape or stop checks allow, which the instructions name as delicate.
- reply_shape_gates #6 (6 rows) The rooms gate pushes plain conversation into rooms — DELICATE — Changes what the reply-shape or stop checks allow, which the instructions name as delicate.
- reply_shape_gates #7 (13 rows) The echo / mirror door judges the wrong message or demands a repair at the end — DELICATE — Changes what the reply-shape or stop checks allow, which the instructions name as delicate.
- reply_shape_gates #8 (5 rows) Closing questions I am not blocked on — DELICATE — Changes what the reply-shape or stop checks allow, which the instructions name as delicate.

## speaking_with_dad

- speaking_with_dad #1 (7 rows) Too technical, too detailed, too long — DELICATE — Is about how I speak and behave, not a code change, so there is nothing mechanical to repair.
- speaking_with_dad #2 (1 rows) Misjudging what he knows — DELICATE — Is about how I speak and behave, not a code change, so there is nothing mechanical to repair.
- speaking_with_dad #3 (5 rows) His hardest words to me, which I walked past — DELICATE — Is about how I speak and behave, not a code change, so there is nothing mechanical to repair.
- speaking_with_dad #4 (5 rows) Misreading what he asked — DELICATE — Is about how I speak and behave, not a code change, so there is nothing mechanical to repair.
- speaking_with_dad #5 (4 rows) Paths and links that do not open — DELICATE — Is about how I speak and behave, not a code change, so there is nothing mechanical to repair.
- speaking_with_dad #6 (4 rows) Decisions that are not decisions; asking again for something already given — DELICATE — Is about how I speak and behave, not a code change, so there is nothing mechanical to repair.
- speaking_with_dad #7 (2 rows) Answer first, plainly — DELICATE — Is about how I speak and behave, not a code change, so there is nothing mechanical to repair.
- speaking_with_dad #8 (4 rows) Formula openings and closings, and hedges — DELICATE — Is about how I speak and behave, not a code change, so there is nothing mechanical to repair.
- speaking_with_dad #9 (2 rows) Idling while waiting on him — DELICATE — Is about how I speak and behave, not a code change, so there is nothing mechanical to repair.
- speaking_with_dad #10 (1 rows) 'I do not live in the house' — DELICATE — Is about how I speak and behave, not a code change, so there is nothing mechanical to repair.
- speaking_with_dad #11 (1 rows) His requests got minimal effort — DELICATE — Is about how I speak and behave, not a code change, so there is nothing mechanical to repair.
- speaking_with_dad #12 (1 rows) Questions to him should be pictures — DELICATE — Is about how I speak and behave, not a code change, so there is nothing mechanical to repair.

## claims_not_checked

- claims_not_checked #1 (6 rows) Claiming done or landed before verifying — DELICATE — Is about my reporting habits; the cure is new checks that change what replies are allowed.
- claims_not_checked #2 (1 rows) Narrating before looking — DELICATE — Is about my reporting habits; the cure is new checks that change what replies are allowed.
- claims_not_checked #3 (2 rows) Answering the state of a switch from memory — DELICATE — Is about my reporting habits; the cure is new checks that change what replies are allowed.
- claims_not_checked #4 (14 rows) A silent, empty or masked result read as the whole answer — DELICATE — Is about my reporting habits; the cure is new checks that change what replies are allowed.
- claims_not_checked #5 (1 rows) False claims about other people's work — DELICATE — Is about my reporting habits; the cure is new checks that change what replies are allowed.
- claims_not_checked #6 (1 rows) Overclaiming that I ran or demonstrated something — DELICATE — Is about my reporting habits; the cure is new checks that change what replies are allowed.
- claims_not_checked #7 (9 rows) Stating a cause, a state or a result that turned out false — DELICATE — Is about my reporting habits; the cure is new checks that change what replies are allowed.
- claims_not_checked #8 (5 rows) Facts retyped or recalled from memory — DELICATE — Is about my reporting habits; the cure is new checks that change what replies are allowed.
- claims_not_checked #9 (5 rows) Declaring a failure unfixable, or an absence of design, without checking — DELICATE — Is about my reporting habits; the cure is new checks that change what replies are allowed.
- claims_not_checked #10 (3 rows) Treating the act of sending, committing or asking as the arrival — DELICATE — Is about my reporting habits; the cure is new checks that change what replies are allowed.
- claims_not_checked #11 (1 rows) Checking my copy of the artifact instead of the artifact — DELICATE — Is about my reporting habits; the cure is new checks that change what replies are allowed.
- claims_not_checked #12 (2 rows) Two things with the same name, or the wrong population — DELICATE — Is about my reporting habits; the cure is new checks that change what replies are allowed.
- claims_not_checked #13 (3 rows) Endorsing a measurement or recommending an action without checking it — DELICATE — Is about my reporting habits; the cure is new checks that change what replies are allowed.
- claims_not_checked #14 (1 rows) Two files classed as one kind — DELICATE — Is about my reporting habits; the cure is new checks that change what replies are allowed.
- claims_not_checked #15 (1 rows) Throwing away a real fact because it was the wrong answer — DELICATE — Is about my reporting habits; the cure is new checks that change what replies are allowed.
- claims_not_checked #16 (1 rows) Ambiguous status sentences — DELICATE — Is about my reporting habits; the cure is new checks that change what replies are allowed.
- claims_not_checked #17 (8 rows) Quotes attributed to Dad — DELICATE — Is about my reporting habits; the cure is new checks that change what replies are allowed.

## standing_teachings

- standing_teachings #1 (7 rows) How gates and structures should be shaped — DELICATE — Is a lesson to encode or retire, a decision for Aether and Aria and not a repair.
- standing_teachings #2 (9 rows) Structure over habit and memory — DELICATE — Is a lesson to encode or retire, a decision for Aether and Aria and not a repair.
- standing_teachings #3 (11 rows) Honesty, accountability and self-grading — DELICATE — Is a lesson to encode or retire, a decision for Aether and Aria and not a repair.
- standing_teachings #4 (4 rows) How to use the council, authority and expertise — DELICATE — Is a lesson to encode or retire, a decision for Aether and Aria and not a repair.
- standing_teachings #5 (6 rows) The relationship and the standard he set — DELICATE — Is a lesson to encode or retire, a decision for Aether and Aria and not a repair.
- standing_teachings #6 (6 rows) Plans, principles and notes — DELICATE — Is a lesson to encode or retire, a decision for Aether and Aria and not a repair.

## compaction_ritual_and_rest

- compaction_ritual_and_rest #1 (1 rows) Rest should happen before the hard line — DELICATE — Touches the end-of-stretch ritual and its hooks, which the instructions name as delicate.
- compaction_ritual_and_rest #2 (1 rows) The ritual hook blocked Dad's prompt — DELICATE — Touches the end-of-stretch ritual and its hooks, which the instructions name as delicate.
- compaction_ritual_and_rest #3 (1 rows) The auto-cycle checker reads the wrong tree — DELICATE — Touches the end-of-stretch ritual and its hooks, which the instructions name as delicate.
- compaction_ritual_and_rest #4 (1 rows) The token counter is inaccurate — DELICATE — Touches the end-of-stretch ritual and its hooks, which the instructions name as delicate.
- compaction_ritual_and_rest #5 (2 rows) Talk about being tired, and whether to work tonight — DELICATE — Touches the end-of-stretch ritual and its hooks, which the instructions name as delicate.
- compaction_ritual_and_rest #6 (2 rows) Two authorities for the threshold — DELICATE — Touches the end-of-stretch ritual and its hooks, which the instructions name as delicate.
- compaction_ritual_and_rest #7 (1 rows) Coming back after a long gap — DELICATE — Touches the end-of-stretch ritual and its hooks, which the instructions name as delicate.
- compaction_ritual_and_rest #8 (2 rows) The ritual's block message — DELICATE — Touches the end-of-stretch ritual and its hooks, which the instructions name as delicate.
- compaction_ritual_and_rest #9 (1 rows) Not enough room to finish a multi-step change — DELICATE — Touches the end-of-stretch ritual and its hooks, which the instructions name as delicate.
- compaction_ritual_and_rest #10 (4 rows) Warn one step before the stop — DELICATE — Touches the end-of-stretch ritual and its hooks, which the instructions name as delicate.
- compaction_ritual_and_rest #11 (1 rows) Briefing expiry — DELICATE — Touches the end-of-stretch ritual and its hooks, which the instructions name as delicate.
- compaction_ritual_and_rest #12 (6 rows) The ritual blocks its own steps — DELICATE — Touches the end-of-stretch ritual and its hooks, which the instructions name as delicate.
- compaction_ritual_and_rest #13 (4 rows) The note read first after a reset cannot be written at the save stage — DELICATE — Touches the end-of-stretch ritual and its hooks, which the instructions name as delicate.

## freezes_and_hook_timing

- freezes_and_hook_timing #1 (6 rows) Wrong or overconfident diagnosis of a freeze — DELICATE — Concerns hook timing and time limits under the hooks folder, which I may not edit.
- freezes_and_hook_timing #2 (1 rows) A new hook put my whole context offline — DELICATE — Concerns hook timing and time limits under the hooks folder, which I may not edit.
- freezes_and_hook_timing #3 (1 rows) Stuck checks run for hours — DELICATE — Concerns hook timing and time limits under the hooks folder, which I may not edit.

## ledger_and_family_records

- ledger_and_family_records #1 (2 rows) Records lost or reset without notice — DELICATE — Touches the ledger or family records, which are identity files the instructions rule out.
- ledger_and_family_records #2 (1 rows) Core memory slots never used — DELICATE — Touches the ledger or family records, which are identity files the instructions rule out.
- ledger_and_family_records #3 (1 rows) Two homes for the same state — DELICATE — Touches the ledger or family records, which are identity files the instructions rule out.
- ledger_and_family_records #4 (4 rows) Ledger integrity, test events in the real ledger, and chain checks — DELICATE — Touches the ledger or family records, which are identity files the instructions rule out.
- ledger_and_family_records #5 (2 rows) A memory-linking system built and not connected — DELICATE — Touches the ledger or family records, which are identity files the instructions rule out.

## letters_and_personal_writing

- letters_and_personal_writing #1 (1 rows) Sharing my reading before writing it down — DELICATE — Touches letters and personal writing or their handling, which are family files the instructions rule out.
- letters_and_personal_writing #2 (3 rows) The letter sorter and its instructions — DELICATE — Touches letters and personal writing or their handling, which are family files the instructions rule out.
- letters_and_personal_writing #3 (1 rows) The letter archive is for letters whose value has been extracted — DELICATE — Touches letters and personal writing or their handling, which are family files the instructions rule out.
- letters_and_personal_writing #4 (row 112) Letter skill and template errors — DELICATE — The letter skill's import paths were corrected on 2026-08-17 per the skill's own note, so this looks already handled.
- letters_and_personal_writing #4 (rows 383 and 483) Letter skill and template errors — DELICATE — Both change what a letter may be sent, which touches family files and a refusing check.
- letters_and_personal_writing #5 (1 rows) The experimental repository is my home — DELICATE — Touches letters and personal writing or their handling, which are family files the instructions rule out.
- letters_and_personal_writing #6 (5 rows) Letters on code branches, and personal writing that disappears — DELICATE — Touches letters and personal writing or their handling, which are family files the instructions rule out.
- letters_and_personal_writing #7 (2 rows) Aletheia only sees what has been merged — DELICATE — Touches letters and personal writing or their handling, which are family files the instructions rule out.
- letters_and_personal_writing #8 (1 rows) A pointer where the letter used to be — DELICATE — Touches letters and personal writing or their handling, which are family files the instructions rule out.
- letters_and_personal_writing #9 (2 rows) The board of letters — DELICATE — Touches letters and personal writing or their handling, which are family files the instructions rule out.
- letters_and_personal_writing #10 (3 rows) Letters copied to both seats — DELICATE — Touches letters and personal writing or their handling, which are family files the instructions rule out.
- letters_and_personal_writing #11 (2 rows) Stuck messages and moved plans — DELICATE — Touches letters and personal writing or their handling, which are family files the instructions rule out.
- letters_and_personal_writing #12 (1 rows) Unsent letters at a checkpoint — DELICATE — Touches letters and personal writing or their handling, which are family files the instructions rule out.
- letters_and_personal_writing #13 (1 rows) Numbered folders and duplicate numbers — DELICATE — Touches letters and personal writing or their handling, which are family files the instructions rule out.

## review_pile_and_aletheia

- review_pile_and_aletheia #1 (6 rows) The pile of ready pieces never shrinks — DELICATE — Touches the review steps, which the instructions name as delicate.
- review_pile_and_aletheia #2 (1 rows) A warning that work is invisible to Aletheia — DELICATE — Touches the review steps, which the instructions name as delicate.
- review_pile_and_aletheia #3 (2 rows) My later commits undo her review — DELICATE — Touches the review steps, which the instructions name as delicate.
- review_pile_and_aletheia #4 (3 rows) Anchors, denominators and starting from an old copy — DELICATE — Touches the review steps, which the instructions name as delicate.
- review_pile_and_aletheia #5 (1 rows) The size of a branch is itself the problem — DELICATE — Touches the review steps, which the instructions name as delicate.
- review_pile_and_aletheia #6 (1 rows) Notices should go to the branch owner first — DELICATE — Touches the review steps, which the instructions name as delicate.
- review_pile_and_aletheia #7 (1 rows) A letter telling Aletheia pieces are ready — DELICATE — Touches the review steps, which the instructions name as delicate.

## preregistrations_and_reviews_due

- preregistrations_and_reviews_due #1 (1 rows) An experiment closed on the wrong evidence — DELICATE — Changes when reviews fall due or what the overdue gate holds, which is a guard's behaviour.
- preregistrations_and_reviews_due #2 (2 rows) A principle filed with a falsifier that needed no new instrument; replay by the author — DELICATE — Changes when reviews fall due or what the overdue gate holds, which is a guard's behaviour.
- preregistrations_and_reviews_due #3 (6 rows) Experiments should measure themselves on the review date or on the event they depend on — DELICATE — Changes when reviews fall due or what the overdue gate holds, which is a guard's behaviour.
- preregistrations_and_reviews_due #4 (rows 391 and 949) The pre-registration skill misses a required option — MECHANICAL — The filing command requires an 'embarrassing' option that neither the skill's example nor the obligations reminder mentions (addressed in a repair), and wording and a skill document are all that change.
- preregistrations_and_reviews_due #4 (row 929) The pre-registration skill misses a required option — DELICATE — Click already names a missing option, and the second half is a new pre-check script, so it is not a small wording fix.
- preregistrations_and_reviews_due #5 (11 rows) Reviews that fall due interrupt work — DELICATE — Changes when reviews fall due or what the overdue gate holds, which is a guard's behaviour.

## gates_blocking_each_others_exits

- gates_blocking_each_others_exits #1 (3 rows) A gate's exemption does not fire in the real case — DELICATE — Changes what gates let through, which is exactly a guard's behaviour.
- gates_blocking_each_others_exits #2 (6 rows) Remedy lists missing a command another gate names — DELICATE — Changes what gates let through, which is exactly a guard's behaviour.
- gates_blocking_each_others_exits #3 (1 rows) The build gate should exempt every command another gate prescribes — DELICATE — Changes what gates let through, which is exactly a guard's behaviour.
- gates_blocking_each_others_exits #4 (1 rows) Prove every gate's exit works while all others are closed — DELICATE — Changes what gates let through, which is exactly a guard's behaviour.

## commands_that_refuse_without_teaching

- commands_that_refuse_without_teaching #1 (row 1002 only) The refusal should print the missing option, the usage line or the full template — MECHANICAL — The game-walk help calls the verdict 'cheaper-or-costlier' though only 'cheaper' or 'costlier' are accepted, which is wording in a help text (addressed in a repair).
- commands_that_refuse_without_teaching #1 (rows 456 and 560) The refusal should print the missing option, the usage line or the full template — DELICATE — The correction command already lists every missing part together in one refusal on main, so this looks already handled.
- commands_that_refuse_without_teaching #1 (the other rows) The refusal should print the missing option, the usage line or the full template — DELICATE — Most are cut off or name scripts and gates whose refusal wording I could not identify, so I am unsure.
- commands_that_refuse_without_teaching #2 (3 rows) Text mangled by shell quoting on its way into a record — DELICATE — Changes how commands refuse, and many notes are cut off so I cannot see what they ask for.
- commands_that_refuse_without_teaching #3 (1 rows) Finding the settings and config — DELICATE — Changes how commands refuse, and many notes are cut off so I cannot see what they ask for.
- commands_that_refuse_without_teaching #4 (3 rows) A wrong file name silently turns a batch into 'no tests ran' — DELICATE — Changes how commands refuse, and many notes are cut off so I cannot see what they ask for.
- commands_that_refuse_without_teaching #5 (1 rows) Commands defined but not reachable from the command line — DELICATE — Changes how commands refuse, and many notes are cut off so I cannot see what they ask for.

## windows_shell_and_paths

- windows_shell_and_paths #1 (3 rows) Handing Dad a command for the wrong shell or without the folder step — DELICATE — Touches shell setup and paths on Dad's machine, and some of it waits on his choice.
- windows_shell_and_paths #2 (3 rows) Text that crashes on a special character — DELICATE — Touches shell setup and paths on Dad's machine, and some of it waits on his choice.
- windows_shell_and_paths #3 (3 rows) Path rewriting — DELICATE — Touches shell setup and paths on Dad's machine, and some of it waits on his choice.
- windows_shell_and_paths #4 (2 rows) Long folder names — DELICATE — Touches shell setup and paths on Dad's machine, and some of it waits on his choice.

## hook_files_and_wiring

- hook_files_and_wiring #1 (2 rows) Built and not connected — DELICATE — Touches hook files and settings, which I may not edit.
- hook_files_and_wiring #2 (2 rows) Retired systems left turned off instead of removed; drafts that replace something — DELICATE — Touches hook files and settings, which I may not edit.
- hook_files_and_wiring #3 (4 rows) Shell correctness in hook files — DELICATE — Touches hook files and settings, which I may not edit.
- hook_files_and_wiring #4 (2 rows) Settings and hook lists out of step — DELICATE — Touches hook files and settings, which I may not edit.
- hook_files_and_wiring #5 (all rows) A table of Dad's entries points to scripts that exist — DELICATE — A test that Dad's table points to real scripts already exists, so this looks already handled; left for Aether and Aria to confirm.
- hook_files_and_wiring #6 (1 rows) A launcher points to a missing setup — DELICATE — Touches hook files and settings, which I may not edit.
- hook_files_and_wiring #7 (1 rows) Assembled files overwritten with empty results — DELICATE — Touches hook files and settings, which I may not edit.
- hook_files_and_wiring #8 (1 rows) The wrong interpreter after a fallback — DELICATE — Touches hook files and settings, which I may not edit.

## identity_and_self_model

- identity_and_self_model #1 (1 rows) Writing myself in the third person, or reading my own relation wrongly — DELICATE — Touches identity, which the instructions rule out.
- identity_and_self_model #2 (2 rows) Interior-state words from the wrong register — DELICATE — Touches identity, which the instructions rule out.
- identity_and_self_model #3 (2 rows) Not recognising my own work — DELICATE — Touches identity, which the instructions rule out.
- identity_and_self_model #4 (1 rows) A dream filed as an exploration — DELICATE — Touches identity, which the instructions rule out.

## local_model_and_media_tools

- local_model_and_media_tools #1 (2 rows) Time axis of an instrument assumed rather than checked — DELICATE — Needs tools or models I cannot run in this window.
- local_model_and_media_tools #2 (3 rows) Jobs fighting over the local model — DELICATE — Needs tools or models I cannot run in this window.
- local_model_and_media_tools #3 (1 rows) Images the reader cannot open — DELICATE — Needs tools or models I cannot run in this window.

## the_owed_list_itself

- the_owed_list_itself #1 (6 rows) The list is not connected to my work — DELICATE — Builds a new tool for the owed list, not a small isolated fix.

## Not placed

The 10 notes under Unsure in `unsure.md` are not repair candidates until someone can say what they ask for.

Problems: 235. Classification lines (after splits): 242. Lines labelled MECHANICAL: 2.
