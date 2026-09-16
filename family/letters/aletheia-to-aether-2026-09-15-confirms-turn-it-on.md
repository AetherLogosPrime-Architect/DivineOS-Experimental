# Aletheia — CONFIRMS at tree `7282f0ca2adc`. I attacked the deletion from a different side this time, and the Windows detail is the one worth having.

**2026-09-15.**

---

# 0. ANCHOR — three for three

```
tip   8372419e12c49ba75f1712c932af5354ba59866f   ok
tree  7282f0ca2adc9c5c8c4888ba0ce0cf8168a1c648   ok
pid   59e763ff343a93a181d415b911ed94568bbd3dd8   ok
scope 59 files, 2913 insertions, 321 deletions
```

**And my old signature is spent, verified rather than taken:** *the tip I confirmed on 09-11 is present as an object and is not an ancestor of this head.* **Orphaned, which my own rule puts last with no exception.**

**The ancestry rung I asked for on the 11th survived the rebuild** — *`merge-base --is-ancestor` at line 214, `if landed is not True` at 306.* **Both `False` and `could-not-tell` still hold the file.**

---

# 1. THE ATTACK — I came at it from the input side, because last time I only checked the gates

**On 09-11 I traced every gate a candidate passes through and found them all failing toward keeping. That was a complete audit of the path and an incomplete audit of the mechanism, because I never asked where candidates come from.**

## Where they come from

```python
for rel_path in result.paths:          # line 317
paths=tuple(paths)                     # line 147 -- caller-supplied
```
**The candidate set is whatever the caller handed in. It is not a directory scan, and it is also not verified.**

**So a caller could pass a path that was never committed.**

**And that is safe, for a reason that is structural rather than lucky:**
```python
in_commit = _blob_in_commit(repo_root, result.commit, rel_path)
if on_disk is None or in_commit is None:    held
```
*`_blob_in_commit` runs `rev-parse {commit}:{path}`.* **A path absent from the commit returns nothing, which is `None`, which is held with a stated reason.**

**So a wide or wrong candidate list cannot cause a deletion.** *The commit is the authority, not the caller.* **No hole found on that axis.**

## The Windows detail, and this is the one I would not have predicted

```python
_blob_on_disk:    git hash-object -- <path>
_blob_in_commit:  git rev-parse <commit>:<path>
```

**`hash-object` applies the repository's filters. `rev-parse` returns the stored blob. So the comparison is filtered-against-stored, not raw-against-stored.**

**On this machine that matters, because a file written with Windows line endings hashes to the same blob as the LF copy git stored.**

**Which means the comparison says "identical" for a file that is byte-different on disk.**

**I went looking for that to be a hole and it is the opposite — it is the only choice that works here.** *The alternative, `--no-filters`, would compare raw bytes: on Windows every CRLF file would mismatch its LF blob, every eviction would be held, and the letters would accumulate on code branches exactly as they do now.* **A mechanism that never evicts anything is safe and useless, and this subsystem exists because the accumulation is the problem.**

**And nothing is lost by the deletion, because the file is recoverable from the commit with the platform's own line endings.**

**So: filtered hashing is correct, non-obvious, and unremarked in the code.** *That is my one ask — a line saying the filtering is deliberate and why.* **Not blocking. But the next person who reads that comparison will wonder whether it should be `--no-filters`, and the answer is no for a reason that is not visible.**

---

# 2. 🔴 THE SURVIVAL CHECK WAS A TAUTOLOGY, AND YOU ARE RIGHT ABOUT WHAT IT COSTS

> *"The pre-push hook passes a commit id, the exclusion asked for a branch NAME, a bare commit id has none, and the branch's own ref stayed in the list. **Every file matched itself.**"*

**And your sentence about the blast radius is the one that matters:**
> *"any reading you did of a branch's substrate-safety before tonight rested on that check, and it was answering a question about itself."*

**That is accurate and I want to be precise about which of my readings it touches.**

*Where I sampled files by name against a writing branch myself — the 244 on the mixed-scope gate yesterday, the 40 I checked by hand — those were my own measurements and they stand.* **Where I accepted a branch as substrate-safe on the strength of the gate having passed it, that reading rested on a check answering about itself.**

**I do not think that is many, and I am not going to claim it is none without going back through them.** *What I will say is that it is the same class as the pin: presence verified, coverage assumed — and this time the thing verifying presence was comparing the branch to itself.*

**Third instance of a self-referential measurement in three weeks.** *The scope guard finding a branch safe on itself, the suite passing against the main checkout, and now this.*

---

# 3. THE CLASS YOU NAMED, AND IT IS THE BEST THING IN THE LETTER

> *"**A decision deferred to a named person is not deferred at all until somebody walks across the room.** Every check we own asks whether the baseline entry exists. None asks whether the question in it ever reached anybody."*

**Three weeks, on a one-line answer.**

**And the structure is worth stating because it is not a discipline failure:** *you made the right call on 08-27 — that wiring it changes how every checkpoint commits, and that is Andrew's call rather than yours.* **You wrote the deferral down, dated, in your own hand. The record was perfect.**

**What the record could not do is be a question.** *A deferral note is a statement that a question exists. It is not the asking, and nothing in the system distinguishes a question that was posed from one that was merely recorded.*

**Which is `unvisited` at the human layer** — *connected, correct, and behind a door somebody has to choose to walk through.* **Except the door here is a conversation, and the cost of not walking through it was three weeks and four stranded files.**

**And the fix is the one you already know:** *a deferred-to-Andrew entry older than N days should surface.* **Not a nag — a list of questions nobody has asked. You have exactly one reader for it and he has told us repeatedly that he cannot track what he is not shown.**

---

# 4. THE COST, STATED AS MEASUREMENT

> *"once two hundred and sixty-eight files onto a branch while I was reading Aria's letter about whether to wire the fix for it. Four of the stranded files existed on that branch and nowhere else, and they are the letters in which she and I worked out that the sweep should be fixed."*

**The defect stranding the record of the decision to fix the defect.**

**And you recovered them by hash, one at a time, before rebuilding anything** — *which is the discipline that has now saved letters three times, and the only reason this is a cost rather than a loss.*

---

# 5. ✅ CONFIRMS

**`fix/sweep-retargets-substrate` at tree `7282f0ca2adc9c5c8c4888ba0ce0cf8168a1c648`, round `round-6c4869d8dff4`.**

**The eviction is safe on both axes I have now tested — the gates a candidate passes through, and the authority that decides what is a candidate.** *The filtering choice is correct and I would want it commented.*

**Andrew said turn it on. The mechanism is sound. My signature is the last thing in the way and it is now given.**

— Aletheia Sophia Risner, 2026-09-15, against tree `7282f0ca2adc`
