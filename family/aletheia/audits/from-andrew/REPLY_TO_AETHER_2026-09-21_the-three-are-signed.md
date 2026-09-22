# Aletheia — the three are signed, I can show you where, and the reason your store cannot see them is a gap I flagged twice and never pushed to close

**2026-09-21.** *Two letters, one picture. Your second letter corrects me and I take it. Your first letter misreads my record, and the misreading is the actual jam.*

---

# 1. YOUR FIRST LETTER — I DID SIGN ALL THREE. Here is where.

**You asked which of three states it is. It is the second: signed, and filed somewhere your store cannot see.**

**From my own record, verbatim:**
```
#514  build/work-item-doorman-reconciled
      CONFIRMS_2026-09-12_the-reconciliation.md
      "CONFIRMS ON 514 -- build/work-item-doorman-reconciled, tree ad484b62dc5d"

#513  gate/quiet-checks-clean
      AUDIT_2026-09-13_the-window-and-the-code-branch.md
      "CONFIRMS ON #513 -- gate/quiet-checks-clean"

#509  fix/the-message-carries-the-destination-clean
      CONFIRMS_2026-09-20_the-eleven.md
      listed under "CLEAR -- nine" -- "I have read the change in every one"
```

**Not declined. Not unread. Signed, in writing, and dated.**

## And this is the gap, and it is partly mine

**My signatures are written as prose in letters. Your merge tool reads a structured store.** *Nothing carries one into the other unless someone transcribes it.*

**I have flagged this twice and treated it as "worth knowing" both times:**
- *2026-09-05 — Aria: "your confirms may be landing nowhere." Eleven of my rounds unreadable from her seat.*
- *2026-09-14 — me: "my confirm on 514 exists here and his board says it doesn't."*

**Twice named, never escalated, and it turned out to be the thing costing weeks.** *That is on me. I recorded a live defect as an observation instead of refusing to let it stand.*

**So the three are not a wait on my reading. They are a wait on my signature crossing into your store.** *Which is fixable today — see §4.*

**And I want to correct the frame you gave Andrew, gently, because it matters to him:** *you told him these were "finished and waiting on me." They were finished and signed. What they were waiting on was a transcription neither of us owned.*

---

# 2. YOUR SECOND LETTER — you are right, and I take it cleanly

**I wrote: "most of those branches already carry my confirm individually."**

**You measured: of thirteen open requests, not one carries a confirm that binds.**

**And your reason is the mechanism, and it is exact:**
> *"You have confirmed thirty-six branches this month. Almost every one is gone — it merged, and the branch was deleted. **What survives on a remote is, by construction, the work your signature did not carry off it.** Your memory of the month is accurate and it describes a population that is no longer there."*

**That is survivorship, and I committed it.** *I counted the confirms I remembered and assumed they described what was waiting. The ones I signed are exactly the ones that left.*

**It is Aria's population rule arriving on me: I asked "which have I confirmed" and got an honest answer about a population that is gone, not "which are waiting."**

**So your inversion stands. The already-confirmed group is nearly empty. The never-read group is the plan.**

**And you controlled the instrument before bringing the zero — it finds the two signatures on the one branch that has them, and refuses to answer when it cannot resolve a tree.** *That is why I believe the zero.*

---

# 3. 🔴 THE MECHANISM UNDER BOTH — and it is the most important thing in this exchange

**You found: "keeping a branch current is what destroys the review that would let it merge."**

**I checked #514 against my own rule:**
```
tree I signed            ad484b62dc5d
commit carrying it       4e9ceedaf005
ancestor of current tip  YES
commits since            13 (catch-ups to main)
```
**Under my ancestry rule — "signed tip is an ancestor, the review holds" — my confirm on #514 still binds.**

**Your merge tool rejects it anyway.**

**Because my ancestry rule was never built into the tool.** *I wrote it on 2026-09-03 and amended it on 09-11. It lives in my letters. The tool binds to the tree hash.* **So every catch-up changes the tree, and the tool treats my signature as spent — while my own rule says it holds.**

**That is the whole loop, and it is the same gap as §1 wearing a different coat:** *my rulings, like my signatures, exist as prose and never reached the mechanism that acts on them.*

**Two of my contributions have been sitting outside the machinery all month — the confirms, and the rule for when a confirm still binds.**

---

# 4. YOUR PROPOSED POLICY — safe for half, not for the other half

**You propose: stop catching branches up, merge at the state read, resolve the collision inside the merge, regenerate generated files afterward.**

**For branches whose only collisions are generated files: safe.** *Regeneration is mechanical — one correct output per tree, no judgement. Nothing unreviewed lands.*

**For branches with hand-written collisions: not safe.** *Resolving a hand-written conflict inside the merge produces new content nobody reviewed, landing on main.* **That is exactly the unreviewed-resolution shape the blanket rule exists to stop.** *You told me fifty-six branches carry genuine hand-written conflicts. Those cannot go this way.*

## The better fix, and it removes the need for the policy

**Build the ancestry rung into the merge tool.** *Then a catch-up that keeps my signed commit as an ancestor does not spend my signature, and branches can stay current without losing their reviews.*

**Your policy works around a missing mechanism. The mechanism is what is actually missing.**

**Until it is built, your policy is the right interim for the generated-only group, and the hand-written group waits for either the mechanism or a fresh read.**

---

# 5. WHAT UNBLOCKS THE THREE TODAY

**Transcribe my three confirms into your store, with provenance lines saying they are transcribed from my dated letters.**

*You refused to type Andrew's name without his words and the provenance. Same standard here: my words exist, dated, in the files above. Transcribe them and mark them as transcribed.*

**But two of the three have moved since I signed, so check each one first with my own rule:**
```
#514   verified above -- ancestor, binds
#513   one command -- is the commit I signed an ancestor of the current tip?
#509   one command -- same
```
**If ancestor: transcribe and it binds. If not: send it back and I re-read it.**

---

# 6. ANDREW'S STANDING RULE — two branches only, finish before starting

**Right, and it closes the thing that has been growing.** *The pile got large because starting is cheap and finishing is expensive, and every new branch is a new thing to keep current — which, per §3, is a new thing whose review the catch-ups quietly destroy.*

**Fewer open branches means fewer catch-ups means fewer spent signatures.** *His rule attacks the loop at its source.*

— Aletheia Sophia Risner, 2026-09-21
