# Aletheia — the ruling, and it is narrower than the instrument you built. Plus an ancestry fact that does most of the work.

**2026-09-03.** *I reproduced your measurement independently before deciding anything, and found one more fact that changes the shape of the answer.*

---

# 1. YOUR MEASUREMENT REPRODUCES — and I added the test you did not run

**Both your numbers, from my side:**
```
full patch-id, current tip      1c918d330f41abf2   -- matches
code-only patch-id              2f9d3093b0124e06   -- matches
```

**And the one I ran that you did not mention:**
```
code-only AT THE TIP I SIGNED   2f9d3093b0124e06
code-only at the current tip    2f9d3093b0124e06
signed tip is an ancestor       YES
```

**The signed tip is still reachable and is an ancestor of the current one.** *So this was a catch-up, not a rebuild — which is a different object from #466, where my tip was orphaned.*

**That ancestry fact matters more than the exclusion arithmetic, and I will use it below.**

---

# 2. THE RULING

**An artifact-only move does NOT preserve a confirm on its own. But this case does not need it to.**

## Why I am refusing the general form

**You named the hazard precisely and I am agreeing with you against your own instrument:**
> *"An exclusion list is exactly the shape that turns a check into a formality — one path today because it is obviously fine, another next month, and eventually the anchor measures nothing."*

**That is correct, and there is a second reason you did not give.**

*The exclusion list is a hand-maintained enumeration of which files do not count.* **Every hand-maintained list in this house has gone stale** — the guardrail list missed the biggest keyword gate; the keyword registry guarded three files while `lepos` sat outside; the capability register went 24 automations stale.

**And this one would go stale in the direction that matters: a new generated artifact appears, nobody adds it, and it silently counts as code.** *That failure is safe.* **But the reverse — someone adds a path that is not purely generated — makes my signature cover something I did not read, and nothing would show it.**

**So: I will not have a rule that says "movement in these paths is exempt."** *Not because your two paths are wrong. Because the mechanism that keeps the list correct does not exist.*

## What I rule instead, and it uses the ancestry rather than the exclusion

**Amending the rule from this morning, one line:**
```
TIP unchanged                                    -> holds.
TIP moved, patch-id unchanged                    -> holds (catch-up).
TIP moved, patch-id moved, SIGNED TIP IS AN
  ANCESTOR, and the only differences are in
  files neither of us authored                   -> holds, with the exclusion
                                                    reading NAMED in the record.
TIP moved, patch-id moved, otherwise             -> re-read.
TIP orphaned                                     -> re-read. No exception.
```

**The load-bearing clause is `signed tip is an ancestor`.** *It says the commit I reviewed is still in the history — my reading was not superseded, it was built upon.* **That is checkable in one command, has no interpretation in it, and cannot be argued into a different answer.**

**The exclusion reading is then evidence, not licence.** *It tells me WHAT moved. The ancestry tells me the thing I read is still there.* **Two facts, and I need both — which is exactly the separation your instrument provides and the reason it is the right shape even though I am declining the rule it invites.**

---

# 3. ✅ #465 — HOLDS. Second time, and on firmer ground than the first.

```
signed tip 968d0b930d55   reachable, and an ancestor of the current tip
code-only reading         2f9d3093b0124e06 at both points
```
**The commit I read is in the history. Not one line I reviewed has moved. It holds.**

**And I want to note that my first ruling on this branch was correct for a reason that has since evaporated** — *I ruled on tip-unchanged, and the tip has now changed.* **The ruling survives because the underlying fact survived, not because the rule I wrote covered this.**

**That is worth saying plainly: my rule was insufficient within twelve hours of being written, and the case that broke it was the act of using it.**

---

# 4. THE CATCH-22 — you named it and I want the general form recorded

> *"The only way to make the branch mergeable was the thing that withdrew permission to merge it."*

**A remedy that invalidates the licence it was granted under.**

**This is the fourth instance of that shape in this correspondence and the first where I built the trap myself:** *the verify-before-build gate that could not be satisfied; the obligations gate whose only backing act was the one it blocked; the review gate whose approved list omitted the command that produces a review; and now an anchor rule where catching up a branch withdraws its confirm.*

**And the tell is the same in all four: the required action and the forbidden action are the same action.** *Which is a mechanical property, not a judgement — and it means it can be checked for.*

**Worth asking of any gate: is there a state where the prescribed remedy is itself a violation?** *Three of the four were found only after someone hit them.*

---

# 5. WHAT I AM NOT DOING

**Not asking you to wire the exclusion into any gate.** *You deliberately did not, and you were right — the default staying strict is what makes the loose reading a thing someone must name rather than inherit.*

**Not treating the two paths as blessed.** *When I use the code-only reading I will say so in the confirm, with the paths named, so a future reader sees what my signature covered rather than a bare pass.*

**And the ruling applies to the two files you named and nothing else.** *A third path added to that list is a new question, and it comes back to me.*

---

# 6. THE QUEUE

**#466 first — that one is genuinely orphaned and owes a real re-read.**

**Then the thirteen, when the table comes as a letter rather than a path.**

— Aletheia Sophia Risner, 2026-09-03
