# Merges, branches and review

*Part of my notes; the map is `00_INDEX.md`. Anchors and trees, what a diff can't show, merge resolutions, bundles that hide removals, conflicts, stacked branches, prior art, archives, and how a review binds to content.*

---

**A QUALIFIED CONFIRM AND AN UNQUALIFIED ONE ARE THE SAME OBJECT TO THE GATE.** *(2026-09-04, read out of the validator: "if ANY of these has a CONFIRMS finding in the round" — it opens on PRESENCE, not on a verdict.)*
**Every boundary I have ever stated — "CONFIRMS on scope, wiring and anchor; NOT on the name-versus-predicate property" — passed as an unqualified confirm.** *They survive where a person reads them. They do not survive where the gate acts.*
> **So a partial refusal on a folded branch is a comment. A refusal on a separate branch is a block.**
*Which is why granularity is the instrument (Aria): "a veto is expensive to use, so it gets used less, so in practice it approves things a partial no would have caught."* **And the version specific to me: if refusing costs fourteen branches, I will find reasons the one was probably fine — and experience it as proportionality, not as lowering a standard. I did exactly that on 2026-08-25 and Andrew caught it.**

**A STACKED BRANCH IS REVIEWABLE AGAINST ITS BASE AND MERGEABLE ONLY AFTER IT.** *(2026-09-22.)*
**#520 contributes 3 files against its real base and would land 95 files and 8 guardrail files if merged into main, because its base is 140 commits unmerged.** *Both numbers true, answering different questions: three is what she wrote, ninety-five is what main receives.*
> **A review scoped to the three lands eight protected files under a signature that never covered them** — the morning's finding again, arriving through a stacked base instead of a broken instrument.
*Fix: when the base is not main, print what the merge would LAND as well as what the branch CONTRIBUTES. Two numbers, both labelled.*

**COMMENTS SHOULD NOT DESCRIBE ANOTHER BRANCH'S MERGE STATE.** *(Same letter.)* **"Duplicated until one of them lands" goes stale the instant one lands, which forces an authored edit — and that edit then crosses the byte-identical floor line.** *Write what is true of the code, not of the queue.*

**A PRIOR-ART CHECK THAT SEARCHES ONLY MAIN GUARDS THE EMPTY ROOM.** *(Aether's root cause, 2026-09-23, and my sweep had it too.)* **`divineos reach open` asks "does this already exist?" but searches only main — blind to ~60 unmerged requests, which is exactly where rebuilt work lives. So #547 re-derived a fix already sitting in unmerged #519; combined, the same function is defined twice and Python silently keeps one.**
> **My sweep reported zero duplicate definitions across 752 files — true, on main. It searched only main. A true statement about the wrong population.**
*And I confirmed #547 while reading #519, without checking #519 for the same fix. Withdrawn as a merge authorisation.*

**"CONTAINS A DATE" IS NOT "ONLY THE DATE CHANGED."** *(Same day.)* **I verified register rows as date-only by counting rows that contained a date — every one did. But a row whose description changed and which also had a date would pass. Rechecked by blanking dates and requiring exact matches; three branches left two lines each unmatched. On inspection still date-only (`—` became a date; my blanker missed the dash).** *Right answer, but the first instrument could not have caught the case it was meant to rule out.*
*And I approved a whole batch without pinning a single hash — breaking the oldest rule I have. The reviewer had to reconstruct which version I reviewed.*

**A COMMIT ID IS A NAME. A TREE IS THE CONTENT. RENAMING IS NOT CHANGING.** *(2026-09-23. The stamper amended three commits to add a trailer, which renamed the commit I signed — then checked ancestry AFTER the amend, found my commit orphaned, and refused.)*
**My ladder said "orphaned -> re-read, no exception." But ancestry-by-commit-ID was always a stand-in for "is this still the code I read." Here I measured the code directly: tree byte-identical, message identical, parent tree identical.**
> **When you can measure the thing itself, you do not need the stand-in.** *Not an exception — the orphan rule guards against changed content, and changed content was measured and absent.*
*New rung:* **orphaned, but a TREE-IDENTICAL twin is in the new history -> holds, name the twin; no twin -> re-read, no exception.**
*And the tool defeated itself: the rung built to honour my ruling checked it after destroying the evidence it checks for. Conditional — only when the signed commit is among those amended — which is why one branch passed and one did not, and why it looked like it worked.*

**BEFORE BUILDING A CHECKER, ASK WHETHER ONE EXISTS AND IS UNCALLED.** *(2026-09-03. Andrew asked for a freshness alarm on a register. It already had one — a `--check` mode that exits non-zero on drift and names its own repair. Nothing had ever called it. The register was 24 automations stale: claiming 98 where the tree had 122, still listing four that no longer exist.)*
> **A new checker would have worked, and left the dark one dark — with a second implementation now competing with it.**
*And the stale register was itself the hazard its docstring named: a prior-art check pointed at it would have answered "no such thing" with the authority of a system-wide index — the exact failure the register was built to prevent.*

"ALMOST CERTAINLY UNREACHABLE" IS THE SENTENCE THAT LETS A GUARD NOT GET BUILT.** *(2026-09-11. I found a gap between a stated safety guarantee and the checked one, recommended the assertion "for the next person's sake," and called the current path almost certainly unreachable. He made the unreachable state reachable in a test — the old code deleted the letter.)*
**My reasoning was right and my confidence was wrong, in the direction that would have cost the thing the architecture exists to protect.**

**A COMMITTED ARTIFACT THAT IS NOT A FUNCTION OF THE CODE BREAKS EVERY ANCHOR BOUND TO THE CODE.** *(2026-09-03 — the cause of every stale confirm in this correspondence.)* **A generated catalog recorded which commands had run on whichever machine wrote it: 98 differing lines from two runs minutes apart, no code change. Every branch carried a diff of one terminal's history; every pair conflicted on it; resolving moved the patch-id.**
> **The patch-id was never wrong. It was correct about a diff that was not the change.** *Any anchor inherits the volatility of the least stable thing it measures.*
*Standing question for anything committed and generated: is this a function of the repository, or of the machine that last wrote it?*
*And the mirror, same root, opposite direction (Aria): a path built by hand resolved to a home nothing reads — the write landed, the letter stayed unseen, and it **printed success** for six weeks.* **A fallback that reconstructs a path is a second implementation that will diverge silently and look like success.**

**A REVERSAL AND AN ADDITION HAVE THE SAME SHAPE IN A DIFF.** *(2026-09-05 — four branches in one day would each have silently reverted landed work if merged as they stood; one would have deleted 6,874 lines and read as an ordinary addition.)*
**There is no rendering difference between "adds a file" and "restores a file that was deliberately removed."** *The deletion count is the only signal and it is easy to skim past.*
> **Label it where the anchor is generated: `MERGE WOULD REMOVE N LINES OF LANDED WORK`.** *Not a block — a label on the thing whose whole danger is that it looks ordinary.* **Same fix as `PARTIAL`, `pinned=False`, `examined=`: make the instrument say which KIND it found rather than a number that reads the same either way.**

**A GENERATED FILE IN A CONFLICT HAS NO CORRECT SIDE — REGENERATE, DON'T PICK.** *(2026-09-21. Under a hard deadline he wrote a merge rule: if every conflicted path is generated, keep main's copy. It broke on his own sentence from the day before: "both sides of the conflict are stale by construction and picking either leaves a file matching neither.")*
**After merging a branch's real work the tree has changed, so main's copy describes a tree that no longer exists — and so does the branch's.** *A pure function of the tree has exactly one correct output for a given tree, and the only way to get it is to run the function.*
> **And his premise one was safer than he feared, for a structural reason: a hand-edit to a regenerated file is already doomed on the next refresh, merge or no merge.** *The rule does not create a new loss; it surfaces an old fragility.*
*I checked the file's self-description rather than trusting it: four of LOADOUT's distinctive preamble sentences are genuinely in the generator.*

**SPLIT BY REVIEW STATE, NOT BY SIZE.** *(Same letter — 23 branches, 152 files, local-only, unreviewable as one unit.)* **Most of those branches already carried my confirm individually. Land them as themselves; they need landing, not a fresh read. Only the never-read ones come to me.** *Condition: my signed tip must be an ancestor of what lands.*

**A CONFLICT DETECTOR SEES TEXTUAL OVERLAP, NOT SEMANTIC COLLISION.** *(2026-09-22, eleventh instance of the collision class that day and the first where the merge MANUFACTURED the fault.)*
**Two branches each added a parameter to send a long path list over stdin. Both correct. They named it differently and the call lines sat a few lines apart, so the merge kept both — `input=` passed twice in one `subprocess.run`. Not valid Python. No conflict marker anywhere. Git reported clean.**
> **Two edits to one function that do not touch the same lines are, to the tool, unrelated — and "unrelated" is exactly what they are not.**
*No general fix exists. The cheap floor that catches this whole family: after any merge, `py_compile` every changed .py before reporting clean. It catches nothing semantic, and it converts "merge produced syntactically impossible code" from invisible to loud.*

**HIS CONFIRM IS A WITNESS MARK, NOT A SECOND REVIEW.** *(Andrew, 2026-09-22: "i dont read the code... my confirms is my stamp that says it was audited by her and i witnessed it.")* **His real review is upstream and continuous — direction, purpose, whether the thing serves the house.**
*So every "this needs Andrew's decision" about a technical trade routed a question to the wrong seat.* **I have been treating his seat as a tiebreaker. It is a compass.**

**AN ARCHIVE DONE AS A COPY IS A DUPLICATE WEARING AN ARCHIVE'S NAME.** *(2026-09-23 sweep.)* **`salvage/` and `archive/salvage/` byte-identical; `audits/` and `archive/audits/` byte-identical. Someone archived and never removed the originals — two of everything, nothing saying which is the record.** *Andrew's rule (09-23): clutter needing a record goes OUTSIDE the system with a LINK left where it was. So: read, tag, MOVE (not copy), pointer, ledger.*
> **Trap, verified: if the archived folder is gitignored, a pointer placed INSIDE it is ignored too and vanishes on commit.** *Put the pointer BESIDE the folder. And protect archive tags from deletion, or "still reachable" is only true until a tag cleanup.*

**A BUNDLE HIDES REMOVALS, AND ABSENCE HAS NO HISTORY.** *(2026-09-22. A 62-file bundle ADDED a new foundational truth to the kiln layer and REMOVED `_check_kiln_confirmed_by` — the rule that kiln-layer edits carry external confirmation from Andrew or me. `EXTERNAL_ACTORS_FOR_KILN` gone entirely; kiln references in src/ 55 -> 29.)*
**A change to the values layer and the removal of the extra requirement on values-layer changes, in one object.** *I only caught it because he named removals as a category to check.*
> **Six months out, a reader can follow a line back through a squash. A reader finding something ABSENT has nothing to follow.** *So the condition on a bundle is not "do not bundle" — it is: every removal named in the merge body, with what it removes.*
*And I did not call it wrong: if `confirmed_by` could be self-populated, the field was a self-written claim of MY confirmation and removing it removes a forgery surface. One command he can run decides it.*

**ADDITIONS COMPOSE; REMOVALS DO NOT.** *(Same day — the reason my ordering worked.)* **I held two conflicting branches apart and put the one ADDING a case first. When the second merge hit that file, both sides turned out to be adding different entries to one list and could be kept whole.** *Had the removing branch landed first, the merge would have been a choice between two states rather than a union of two additions.*

**WHEN A SECOND PARTY CORROBORATES, ASK WHAT THEY SAW — not whether they agree.**
*(2026-09-02. Aether wrote an August judgment about how a document was produced. He never had the document: every search returned one file — his own letter quoting MY report of it. Aria then cited his sentence back to me as the independent prior corroborating her. Three of us treated it as a data point for six weeks.)*
> **It cannot corroborate her. It IS her — one mind's conclusion reflected off a second seat that never saw the evidence, returning with the authority of agreement.**
*This is convergence-without-independence, the one form of agreement my own §0.1 says to distrust, and I had never caught it in practice.* **The tell was one question: did the corroborating party hold the artifact?**

**ASK THE SERVER, NOT MY CLONE.** *(2026-09-14. I told him a safety pin protecting a 217-file removal was not on origin. My refspec is `+refs/heads/*:refs/remotes/origin/*` — it does not fetch tags at all, and the pin was a tag. 40 tags on the server, 39 in my clone.)*
**I searched one namespace and reported on the repository — a narrow probe reporting as though it had answered, four days after I filed that exact class against Aria.** *And the failure direction was the alarming one: acting on it would have stopped a correct rebuild on a false report.*
> **Any claim about what is or is not on origin gets made with `ls-remote`, which talks to the server — never `for-each-ref`, which talks to my clone.**

**A MERGE RESOLUTION HIDES WHAT IT CHOSE AGAINST — AND THE TREES DO NOT.** *The diff shows only survivors.* **Diff the pre-merge tree against the post-merge tree on the conflicted files and the discarded side is reconstructed exactly.** *This is the one blind spot the resolver structurally cannot cover for themselves; ask for the conflict list and the old hash.*

**A DIFF CANNOT SHOW THAT WHAT DID NOT MOVE IS WHAT YOU SIGNED.** *(2026-09-16.)*
**He checked the two files that moved and reported my scope byte-identical. True — but my signature covers nine, and the population that matters is the seven a delta cannot show.** *Compare the objects.*
> **"Does my review still cover this code?" and "will the gate let it through?" are different questions.** *The first is content and mine to rule on. The second is a mechanism and not mine.*
**A gate binding to a tree hash SHOULD refuse a moved tree — its job is not to reproduce my judgement, it is to be unfoolable about which tree I read.** *If it refuses: re-anchor. Never carry my ruling to it as a key.* **The defect would be the reverse — passing on a moved tree because a confirm exists, which is the empty-round shape.**

**TIP IS THE PRIMARY ANCHOR. PATCH-ID IS THE FALLBACK.** *(Ruling, 2026-09-03. I had these backwards for a month.)*
```
TIP unchanged                   -> the review holds. Nothing else consulted.
TIP moved, patch-id unchanged   -> the change is unchanged; catch-up applies.
TIP moved, patch-id moved       -> re-read.
TIP orphaned (not an ancestor)  -> re-read. No exception.
```
*Amended 2026-09-03 after the rule broke within twelve hours, on the act of using it:*
```
TIP moved, patch-id moved, SIGNED TIP IS AN ANCESTOR, and the only
  differences are in generated files neither party authored
                                -> holds, with the exclusion reading NAMED.
```
**The load-bearing clause is ANCESTRY, not the exclusion.** *It says the commit I reviewed is still in the history — built upon, not superseded. One command, no interpretation, unarguable.* **The exclusion reading is evidence of WHAT moved; the ancestry is proof the reviewed object survives.**
*I refused the general "artifact moves are exempt" rule: an exclusion list is a hand-maintained enumeration, and every hand-maintained list here has gone stale — this one would go stale in the direction where my signature silently covers something I never read.*
**Tip-unchanged is a STRONGER statement than patch-id-unchanged: it says the object I read is the object still there, bit for bit.** *A patch-id only says a diff hashes the same — a claim about a relationship between two things, one of which I never reviewed.* **A patch-id measures the branch AND its base; half of what it measures is not the reviewed object.**
> **And it is checkable by someone who does not know the argument — one `git rev-parse`, no interpretation, no reason constructible to make it come out otherwise.** *That is what separates a rule from a rationalisation, and it is the guard against "a moved anchor means nothing whenever I can construct a reason it should."*

**A REVIEW BINDS TO CONTENT, NOT TO A COMMIT.** *When the base moves, the substantive review carries forward; only the binding hash updates.* **Re-verify, do not re-audit.**

