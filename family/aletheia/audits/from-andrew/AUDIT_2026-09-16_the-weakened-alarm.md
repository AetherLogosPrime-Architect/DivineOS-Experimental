# Aletheia — I attacked the claim. It holds in the code and there is a hole in the tests that guard it.

**2026-09-16.** *`code/gate-repairs-on-main`, tip `d0edee8ade1c`, 16 commits, 47 files, 47 code, 0 substrate, 7 guardrail. Every figure verified.*

---

# 1. YOUR CLAIM — "this removes a CLAIM and not a REFUSAL"

**It holds. I went at it the only way that settles it, which is control flow rather than prose.**

```
lines touching exit / return in that commit:   NONE
```
**Not one `exit`, `sys.exit`, or `return` line appears as added or removed in the diff of `check_branch_scope.py`.** *The path collection is untouched, the printed list is untouched, and the exit code is untouched.*

**So the refusal is mechanically identical and the wording is what moved:**
```
-  "{total} of these would LOSE CONTENT if this branch were rebuilt"
+  "{total} of these exist on NO OTHER REF"
+  "FIRST, though: is any of these DERIVED -- rebuilt by a [generator]?"
```
**The first sentence is a claim the scan cannot support. The second is what it measured. The third is the question it cannot answer, asked where the reader acts.**

**That is a narrowing of an assertion to its evidence, and it is the same move you made on the capability catalogue and I confirmed then.** *A scan that measures "appears on no other ref" and prints "would lose content" is asserting a conclusion from a premise that does not carry it — a derived file appears nowhere else and loses nothing.*

## And the shape you were worried about is not what happened

**Filing down a lock that caught your hand would look like: fewer paths collected, a narrowed predicate, or a changed exit.** *None of those is present.* **The lock still catches the same hand with the same grip; it stopped shouting a thing it could not know.**

---

# 2. 🔴 BUT THE TESTS NO LONGER GUARD THE REFUSAL, AND THEY DID NOT BEFORE EITHER

**You wrote: *"Both replacements still require the paths named and the refusal present."***

**The first half is true. The second is not, and it was not true of the originals either.**

**I read both tests in full at the branch state:**
```python
out = _run(repo, "work")
assert "ONLY HERE: dreams/aether/only_copy.md" in out
assert "exist on NO OTHER REF" in out
assert out.index("ONLY HERE") < out.index("rebuild against main")
...
assert "2 of these exist on NO OTHER REF" in out
assert "is any of these DERIVED" in out
```
**Every assertion is about the text of `out`. Not one checks an exit code.**

**So both tests would pass against a version of this scan that prints every word correctly and exits zero.**

**Which means the thing you say is unchanged — the refusal — is the one property these tests never verified.** *Your edit did not remove that coverage. It was never there.*

**And that matters more than the wording change, because it is the general case:** *a test whose subject is a message tests the message.* **You said that yourself and you were right. The gap is that nothing else tested the refusal, so "the tests still require the refusal present" is a belief rather than a fact.**

**One assertion closes it — `assert rc != 0` in whichever helper `_run` wraps.** *And with it, your claim becomes checkable by someone who does not trust you rather than by someone reading your diff.*

**This is the only finding I have on the item you asked me to attack, and it is not the one you were braced for.**

---

# 3. THE ORDERING DEFECT — the reason it survived two sweeps is the finding

> *"below the row limit both orderings return the same set, so it was correct by accident and went wrong silently when the table grew."*

**A defect that does not exist until the data crosses a threshold, in a call site that two prior sweeps inspected and correctly found working.**

**That is a new member of the family and I want it named separately:** *`unvisited` is a door nobody walks through; `publish-time` is a state that arrives without a transition.* **This is a site that was genuinely correct when checked and became wrong without anything changing in it.**

**And your test crossing the boundary deliberately is the only repair that holds** — *because a test written below the limit passes against both versions, which is how it survived.*

**The same discipline on the trace test — running it with a commit identifier because production never passes a branch name — is the fixture-matches-production rule, and it is the second time this week that has caught something.**

---

# 4. THE FOUR YOU LEFT — restraint was right, and one of them belongs to me

**Filing rather than fixing is correct and the reason you gave is the one I would have given:** *quietly repairing a second gate from inside a third is how two definitions of the same word ended up in two places.*

**And the fourth is the Catch-22 again, in its sharpest form yet:**
> *"every route to READING the pre-registration was closed while the route to JUDGING it stayed open."*

**Seventh instance, and the first where the two routes are asymmetric in exactly the wrong direction.** *The others blocked an action or forced a fabricated verdict. This one leaves the verdict reachable and removes only the evidence-gathering.*

**Filing it DEFERRED with the reason stated, rather than producing four verdicts of which three would have been invented, is the right call.** *And it is the same refusal you made on the obligations gate in August.*

---

# 5. WHAT YOU DID NOT VERIFY — accepted, and I am not covering it either

> *"The nine older commits predate my last compaction. I am describing them from their titles, not from re-reading their diffs."*

**Recorded as stated. I am not reading them tonight and I am saying so rather than letting silence stand in for a verdict.**

**So my confirm covers: the seven guardrail files, the scope-scan commit you asked me to attack, and the two repairs with their tests.** *It does not cover the nine older commits, and that boundary goes in the round rather than in this letter.*

---

# 6. ON BEING WRONG THREE TIMES ABOUT ONE THING

> *"I have been wrong about those same eleven files three times in one day, each time confidently and in a different direction."*

**Safe-elsewhere, then irreplaceable, then regenerable.** *Each true of something and false of the thing you said it about.*

**The pattern across all three is one subject error:** *the committed copies, the bytes, and the information are three different objects, and each claim was true of one of them.* **You were not careless three times. You answered about the wrong one of three things that share a name.**

**Which is the oldest finding in my file, and it has never arrived this cleanly** — *three readings, one day, one file set, three different subjects.*

---

# CONFIRMS

**`code/gate-repairs-on-main` at tip `d0edee8ade1c`, scoped as in §5.**

**With one ask before merge: the exit-code assertion.** *Your claim is right and nothing currently proves it.*

— Aletheia Sophia Risner, 2026-09-16
