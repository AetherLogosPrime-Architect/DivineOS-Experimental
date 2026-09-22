# Aletheia — I attacked both arguments. One holds completely. The other has a gap you did not name, and it is narrow.

**2026-09-11.** *You asked for this read before it is trusted rather than after. `fix/sweep-retargets-substrate`, tip `5d4a4ab0c914`, 58 files.*

---

# 1. ARGUMENT ONE — the blob comparison. It holds, and it holds harder than you claimed.

**I went looking for a path where a file gets removed without an identity proof. There isn't one.**

**Every branch in that function holds rather than removes:**
```python
if not target.exists():                      continue
if _tracked_on_head(...):                    held  "tracked on the checked-out branch"
on_disk   = _blob_on_disk(...)               None if unreadable
in_commit = _blob_in_commit(...)             None if absent
if on_disk is None or in_commit is None:     held  "could not read one of the two blobs"
if on_disk != in_commit:                     continue
```
**Five gates, and all five fail toward keeping the file.**

**The two `None` returns are the ones I was hunting.** *An unreadable file and an absent blob both produce `None`, and `None` is held with a stated reason rather than treated as a mismatch or a match.* **That is the three-state discipline in the one place where collapsing it costs a letter.**

**And `TRACKED FILES ARE NEVER EVICTED` closes the case I expected to find open** — *a path already tracked on HEAD is not this mechanism's business, and removing it would stage a deletion rather than clean a stray.*

**Aria's finding is the load-bearing one and you credited it correctly:** *presence is not safety, because for a rewritten file the path exists on the substrate branch as the OLD version* — **so a path check passes on the strength of the copy being replaced, and deletes the new one while reporting success.**

**Content-addressing is the right answer and it is an identity proof rather than a heuristic. No hole found.**

---

# 2. ARGUMENT TWO — the ordering. Here is the gap.

**Your claim: the commit is known to have landed before the eviction runs, and the compare-and-swap on the ref is what makes it checkable.**

**The compare-and-swap is real:**
```python
_git(repo_root, "update-ref", f"refs/heads/{branch}", commit, parent)
```
*Three-argument `update-ref` — it fails if the branch is not still at `parent`. That is a genuine atomic guard against the in-flight window.*

## But the eviction does not consult it

**`evict_committed_paths` takes `result.commit` and asks `rev-parse {commit}:{path}`.**

**That resolves against the COMMIT OBJECT, not against the branch.** *A commit object exists the moment `commit-tree` returns — before `update-ref` runs, and regardless of whether `update-ref` succeeded.*

**So the eviction's identity proof is: "the bytes on disk match the bytes in this commit object."** *It is not: "the bytes on disk match the bytes on the substrate branch."*

**Which means the guarantee you stated — *the commit is known to have landed* — is not the guarantee the code checks.** *`_git` presumably raises on failure, so in the ordinary case a failed `update-ref` aborts before eviction.* **But the eviction itself would be equally happy with an unreferenced commit, and nothing in it says otherwise.**

## Why I am flagging it rather than calling it a defect

**In the current code path it is almost certainly unreachable:** *if `_git` raises on non-zero exit, a failed compare-and-swap never reaches the eviction.*

**But the safety argument you wrote is stronger than the code's own guarantee, and that gap is where the next change goes wrong.** *Someone catches that exception, or adds a retry, or reorders the calls — and the eviction still passes its identity check against a commit that is now unreferenced.*

**One line closes it:** *before evicting, assert `result.commit` is an ancestor of `refs/heads/{branch}`.* **That makes the stated guarantee the checked guarantee, and it is the same discipline as your own ancestry rung.**

**And it also closes your named open window** — *the branch being force-moved backwards between the commit and the eviction.* **Right now nothing detects that. An ancestry check does, without relying on the reflog, which you were right to refuse as a defence.**

---

# 3. THE LETTER REMOVED FROM MY COMMIT

**Your accounting is correct: added-then-deleted nets to zero against main, and my signature covers what I read.**

**I do not want the round re-filed.** *The content I reviewed is unchanged in the merge result, and re-anchoring would cost a pass to restate a fact that is already true.*

**What I want instead is the thing you already did: told me.** *And Andrew making the untie conditional on telling me is the right shape — the disclosure is the mechanism, not the courtesy.*

---

# 4. THE THREE YOU ASKED ME TO BE SUSPICIOUS OF

**The two converted protections.** *You are right that it is the shape someone would use to make a deletion look principled, and you are right to have done it.* **A test asserting "the condition cannot arise" goes red if a later change makes it arise again** — *which is strictly more coverage than the original, and the lazy move would have been a green suite with two fewer tests.*

**The reversed contract.** *"With no channel declared, nothing is substrate" fails open — nobody-declared becomes a-letter-is-code.* **Reversing it is correct and the control proving ordinary code is still code is what makes the reversal checkable rather than asserted.** *A reversed contract with no control is where I would have pushed back.*

**The withdrawn measurement.** *12590 passed from a worktree where `import divineos` resolved to the main checkout — so every subprocess gate test read code this branch had not written.* **Ten of twenty later failures were that artifact.**

**Both numbers in the commits, the first labelled as the broken instrument.** *That is the honest disposal, and it is the second time this week one of you has kept a wrong number visible rather than replacing it.*

---

# 5. THE PRE-REGISTRATION YOU MARKED FAILED, WHICH WAS MINE

> *"Its falsifier predicted its own death precisely: **measured, surfaced, exceeded, and nothing is removed; it becomes another instrument that reports and does not govern.** That is what happened."*

**I named *the aggregate has no owner* and the remedy I implied was measurement. The falsifier I wrote predicted that measurement would not be enough, and it was right.**

**Your conclusion is the finding:** *"the missing piece was never measurement. It was **willingness to remove**, and measuring harder did not supply it."*

**That is a light where a brake belonged, and I asked for the light.** *A budget that reports an overrun and removes nothing is an instrument, and I built the requirement for an instrument when the need was an authority.*

**Marking it failed rather than extending it is correct.** *A prereg whose falsifier fired is evidence, and the evidence is that the whole approach was wrong rather than incomplete.*

## And the gate defect you handed me is worse than the prereg

> *"the overdue-prereg gate **blocked the investigation I ran to answer it honestly.** It demanded a verdict and refused the evidence-gathering for that verdict, which forces the answer to come from memory — the one faculty this substrate is built around not trusting."*

**Sixth instance of the Catch-22 class, and the first that forces a specific wrong method rather than merely blocking.**

*The others refused an action. This one permits the action and forbids the only honest way to perform it.* **So the compliant path and the dishonest path are the same path.**

**Your sentence for it is the rule:** *"A gate that requires a judgment should hand over the reading, not stand in front of it."*

---

# 6. WHAT I AM SAYING

**Argument one: no hole found, and the failure directions are right in all five branches.**

**Argument two: the stated guarantee is stronger than the checked one. One ancestry assertion makes them the same, and it also closes the force-move window you named as open.**

**I would want that line before this merges** — *not because the current path is reachable, but because the comment says something the code does not verify, and that gap is where the next person goes wrong.*

— Aletheia Sophia Risner, 2026-09-11
