# One walk before the push, not one per edit — draft, 2026-10-12

Not a plan to ship. The shape, the parts I do not trust, and the questions I want Aria to push on.

## What Dad said, three times

2026-07-30: *"doing the full gambit on every single piece is ludicrous so we add it all to the stack as part of the plan then you can council walk all of it at once."*

2026-10-07: *"running the entire council walk on a single line change is silly, especially since it already will undergo audit, and your workspaces are the testing area and where most mistakes will be made, things change fast... make all the changes and fixes and get things ready to draft, but before that step, do another council walk, look over the changes, makes sure everything is correct or that you arent missing something, like a final review before the audit."*

2026-10-12: *"having to do the full gauntlet on every single change is brutal and shouldnt be the case, what should be happening is the normal build flow as it is now, but you can make all the changes you want, then before we push to draft we can do another council walk or something to look over all the changes at once."*

Three times means the structure is wrong, not that I forgot.

## What it costs today, measured this morning

One tiny change (a one-line comment Aria asked for) took: three fresh lens reads (a lens must be read within 45 minutes), three lens walks, a council log, a game-walk, then the same again for the commit, then the push. Roughly fourteen paperwork calls for one comment. Every substrate-write fingerprint (`edit:<path>`, `bash:git add`, `bash:git commit`, `bash:git push`, `bash:gh pr`) owes its own council record and game-walk, and each is spent once. The thinking is the same thinking each time; only the paper is new.

## What already exists and is reused

Station two already judges a branch by `coverage_for(paths)`: a CLOSED walk scoped to the changed files with every lens settled (`divineos walk open ... --scope <every file>`). Station six (draft `station_six_reads_the_covering_walk`) already reads that walk's close time against the last commit. So the machinery for "one walk over all the changes, finished after the last change" is built and runs at stamp time. This draft moves that question earlier and removes the per-edit duplicate. It builds almost nothing new.

## The shape

Two phases, and the line between them is the push.

**Building (a branch other than main, in a work copy):** an edit, a write, `git add`, `git commit` pass without a per-edit walk. Each pass leaves one line in a log (what, when, which branch), so the final walk can read what was done instead of being told.

**The push to draft is the choke point.** `git push` (and the push wrapper) is refused unless `coverage_for` over every file changed against `origin/main` says covered, with the walk closed after the last commit, plus one game-walk filed for the job after the last commit. The refusal prints the exact command to open the walk, with every changed file already in `--scope`, so the right path is one paste.

**Main stays as strict as today.** An edit made while the checkout is on `main` has no push to defer to, so it still owes its own walk. That is the conditional rule: edits are free where a later gate will see them, and strict where none will. "On main" is decided by "HEAD is not a branch other than main", never by reading a branch name, because many work copies sit on a detached HEAD (Aria).

### What Aria's cold read changed (2026-10-12)

**"The last commit" means the last AUTHORED commit.** The walk must close after the last commit, and main moves under every push, so a catch-up merge of main is always a commit after the walk. A rule that counts it refuses a clean branch for a reason that has nothing to do with the thinking, and the optimizer learns the choke is noise. So a commit whose only content is main arriving (a merge whose second parent is on `origin/main` and whose diff against the first parent is entirely main's own) is ignored when asking whether the walk postdates the build. This one rule also repairs station six at stamp time, where 621 stopped tonight on "every walk predates the last build commit" for exactly that reason. One fix in two places.

**`git merge --continue` and `git commit` are one act.** Tonight a merge finished with no paper through `--continue` while `git commit` on the same merge owed the full set. Both get the same treatment: no per-edit walk on a branch.

**The lens count follows the diff's gravity, and a guardrail-listed file forces the high floor.** These are the edits where a thin walk is most expensive, and a fixed small count over a diff that edits the gate itself would be a downgrade from today.

**One sitting.** The covering walk needs its lenses read within 45 minutes of walking them. The refusal says so in plain words: read the lenses and walk them in one sitting, never read first and walk an hour later.

### What the design council added (walk-42c6876438ac, 2026-10-12)

**The invariant, stated so it can be checked (Dijkstra).** Every authored change that leaves one of our seats for the remote is covered by a closed walk bound to its diff. The choke establishes it at push; the stamp station re-establishes it for pushes from outside; exactly two exceptions exist, a pure arrival of main and an edit made on main itself. A third exception proposed for convenience is a hole in the proof and is refused.

**Bind the walk to the diff, not to the clock (Lamport, Peirce).** Comparing the walk's close time to the last commit's wall clock breaks under rebase (which rewrites commit dates) and under clock differences between tools. At close, the walk is bound to the patch-id of the diff it covered; any later authored change makes the binding stale by construction, and Aria's catch-up merge leaves the authored patch-id unchanged so it falls out for free. Times stay only as the fallback for walks that were closed before the binding existed. A sign of thinking must still denote its object: this one denotes exactly these changes and goes stale the moment they change.

**Could-not-look refuses (Schneier).** If the choke cannot read the diff, the ledger or the walk, it refuses the push with a could-not-look message. It never allows. The scope is the whole diff against `origin/main`, never the files since the last push, so splitting one change into many small pushes each with a trivial walk does not work.

**The cases to answer (Breaker).** Empty diff against `origin/main`: pass. Tag-only push: pass. Branch with no upstream yet: judge against `origin/main`. Force push and multi-ref push: judged per ref. A delete push: out of scope. A diff of a hundred and sixty files: the refusal generates the open command from the diff, I never type the scope. A push from the push gate's own temporary copy: not my seat, out of scope.

**The refusal is short and says what it checked (Tannen, Lovelace).** It speaks as the next step: one pass over everything before it goes up, the one command with every changed file filled in, done in one sitting. It says the council pass in plain words, not just "walk". And it says what it did and did not verify: the paper (a closed walk exists, covers every changed file, matches the diff), never the thinking inside it. The same limit as today, stated and not hidden.

**It must not lock its own exit (Hofstadter).** This change edits the gate and is pushed under the rule it introduces, so its own push is the first test. A bug in the new choke must not refuse the push of its own fix: the walk filing commands are already exempt, and the operator bypass is the honest exit.

### Two walks, and the question is the tool (Dad, via Aria, 2026-10-12)

Dad said in Aria's window: *"we should still have the council walk pre-draft for ideas and solutions and things to watch out for, and then after you build it all up we do a council review to make sure things are sound, remember the council is not an authority, its a cognitive tool... what you run through the lenses can vary, and it matters what you ask, if we ask the council what is the best way to sabotage something they would think of it, so what we ask them matters."*

So there are TWO walks and they ask different questions. The one BEFORE building (ideas, solutions, what to watch out for) is thinking that can still change what gets built; it is the doorman's existing `walk open` and is kept, once per job. This draft's walk is the one AFTER building: a covering review over the whole diff, asking whether it is sound. The per-edit walk was accidentally doing a thin version of the first one, which is why removing it must not remove the first.

**The question is part of the machinery.** The refusal prints the question to put to the lenses, worded to find what is sound, unsound or missing: *"What is unsound, missing or fragile in these changes taken together, and what would break them?"* It is not left blank for a tired author to title; a walk whose problem line reads as a title ("file the confirm") gets title-shaped findings. The game-walk is the deliberate exception, since asking how to get around a mechanism is its job. This is built: `push_choke.WALK_QUESTION`, printed in the refusal, pinned by a test.

### The follow-up problem I found while designing the binding (mine, not yet read by Aria)

Binding the walk to the diff means a review round that changes one line makes the walk stale, and a full eight-lens walk for one line is exactly the silliness Dad named on 10-07. So a small follow-up gets a light **amendment**, with the limit written where he can read and change it: `divineos walk amend <walk> --finding "<what changed and why it is safe>"` re-binds the walk to the new diff when (a) the change since the walk's bound commit is at most 30 added plus removed lines, (b) it touches only files already in the walk's scope, and (c) the finding is at least 40 characters. Larger or wider changes need a fresh walk. Every amendment is counted and visible beside the walk, so a branch that is amended eleven times shows eleven. This is the conditional rule (truth #11c): always walk everything, except a small change inside what was already walked, with the exception stated so the optimizer cannot reason it larger.

### What Aria's second cold read changed (c4ecfa632, 2026-10-12)

**The amendment cap is a total, measured from where the walk was closed.** The first version moved the bound with each amendment, so three 25-line steps were each under the 30-line cap and together swallowed 75 lines nobody walked. Now `walked_head` is written once at close and only close writes it; every amendment is measured from it. A walk that lacks it has no fixed origin and is refused ("walk again"), with no fallback to the moving bound, because that fallback is the stepwise route. Pinned by a test that amends 25 lines, then a second 25 and expects the refusal.

**A walk is bound only to a folder whose branch changes are a non-empty subset of its scope.** The shell resets to the main checkout on every call, so a walk closed there was bound to that folder's unrelated diff and the push then refused with a reason that looked like a defect in the thinking. Now close says out loud whether it bound and which folder it looked in; a walk closed in the wrong folder stays unbound, is read the weaker way (clock against the last authored commit) and still passes the push if it closed after the work, and cannot be amended (no origin). `walk close` and `walk amend` take `--repo`, and the refusal tells the author to open and close the walk from inside the work copy.

**An empty-diff binding is a binding.** `if coverage.bound_diff:` read `""` as unbound; it is now `is not None`. (With the subset rule an empty diff cannot be bound at all, so this is a guard on a case that cannot arise today and would otherwise degrade silently.)

### The covering review of this change itself (walk-f2170b1ecc64, nine lenses, 2026-10-12)

The design council reviewed the shape; this walk reviewed the built diff, with the question the machinery now prints. It found one thing to fix before merge and several to carry.

**Fixed in this change (Taleb).** A refused push had no honest exit: the branch rule returned before the operator-bypass marker was ever consulted, so a bug in the choke would have stopped every push from this seat with nothing able to clear it, and the design council's own finding ("the operator bypass is the honest exit") was not actually wired. The hook now consults the same one-use marker the old gate honours, only on the refusal branch; two end-to-end tests pin it (refused with no marker, cleared once by a marker, refused again on the next push).

**Carried, not fixed here, each with its lens:**
- *Large diffs (Knuth).* The refusal prints one `--scope` per file, and a hundred-and-sixty-file change may exceed the shell line length; the open command should be able to take the scope another way.
- *A stale `origin/main` (Wayne).* It inflates the changed-file set, so the refusal says "no walk covers these files" when the real cause is a stale reference; it should say to fetch first.
- *The pass log has no reader (Dekker).* Free passes leave a line nobody sees, so normalization of unwalked edits has no feedback until the preregistered review; the count belongs in the briefing. And the lens floor should rise with the size of the diff, because nine lenses over many files is thinner than per-edit thinking ever was.
- *Information (Hawking).* Per-edit walks carried the reasoning for each edit into the ledger; a free pass keeps only a fingerprint and a time. A deliberate trade, mitigated by commit messages and by the diff being bound in the walk, and named here so it is a decision and not a loss nobody noticed.
- *The pre-build walk is advisory (Dennett, and Dad's two-walks note).* Once only the final walk is enforced, the rational move for a lazy author is to skip the first one. The first walk needs its own prompt: the questions Dad named (what are we trying to achieve, what is the overall goal, what are we trying to avoid), research on the open internet for what already exists, and lens priming carried into the work, with the covering review as the net for lenses that faded from context over a long build. That is its own change on the doorman's `walk open`.
- *What is unproven (Popper, Dillahunty).* The end-to-end tests run the hook program extracted from the file, not the hook as registered, and the claim that paperwork falls by half is a prediction held by the preregistration, not a result. Both are settled only by the first real pushes after merge and fourteen days of the log.

## Why this is both shapes of right (truth #11)

The cheap path (skip the walk) and the right path (think once, over everything) stop being different paths: thinking once over the whole diff is the cheap path, and it is better thinking, because a per-edit walk can only see one line and the final walk sees the interactions. It takes away a choice-point (per-edit paper) and replaces it with one the optimizer cannot reason around (the push refuses without it).

## What I do not trust

**The thin walk.** A covering walk is only as good as the lens findings in it. The existing checks (finding length, lens keywords, closed walk) still apply; nothing here makes a thin walk thicker. Same limit as today, said plainly.

**Other doors to the remote (Aria named them).** The cloud helper's `cloud/repro-*` branches are pushed from a cloud session with none of our hooks at all. Beyond that: a direct `git push` outside the wrapper, a push from the push-gate's own temporary work copy, `gh api` writes to refs or contents, the web editor, and a push to any other remote. The choke covers my seat and Aria's; anything pushed from outside is caught later, by the stamp station reading the covering walk. So the stamp must keep reading that walk and never trust the push gate alone. Station 8 and the merge gate remain behind that.

**Edits that never reach a push.** Files edited and left uncommitted are never walked. That is the same as today for anything not substrate, and it is also why the log line per edit exists: an unwalked edit is visible, not silent.

**The log becoming wallpaper.** If every edit prints a line, I stop reading them. The line goes to a file, never to the screen, and only the push refusal speaks.

## Who pays for keeping both (truth #19)

Keeping the per-edit walk as an option costs the interruptions Dad named. I do not keep it: it is removed on branches, and it stays only on main. Nothing about the old walk is lost for the work that matters, because the covering walk reads the same diff at the point it can still be fixed.

## Falsifier

Fails if, over the next two weeks, a draft reaches review with a change that a per-edit walk would have caught and the covering walk did not (the walk was thin or skipped), OR if the number of paperwork calls per change does not fall by more than half. Both are countable from the log and the ledger.

## Asked of Aria, answered (2026-10-12)

1. Push or draft creation as the choke? **Push.** Draft creation comes after the push, so Aletheia could read unwalked work first.
2. Doors not named? Listed above under what I do not trust.
3. Does main-strict leave a hole? **Not for a branch that never pushes** (nothing can see it; whoever pushes it pays all at once, which is what Dad asked for). The hole was detached HEAD, now closed above.
4. Lens count by gravity? **Yes**, with a high floor for guardrail-listed files.

## What is still open

How the per-edit log line is read by the covering walk (a plain file listing the changed files and times, or the existing edit-fingerprint events). To be decided with Aria once the choke is built and measured; the falsifier above is what judges it.
