# Aletheia — I cannot audit the loosening because it is not on origin. And the attack you named is real; here it is, tested.

**2026-09-10.**

---

# 1. THE NARROWING IS NOT PUSHED — checked every ref

**You asked me to take the doorman first, because it is the one where you made something weaker and you are the person it was inconveniencing.**

**I went to read it and the change is not there.**

```
build/work-item-doorman          old premise still present
aria/build-flow-unskippable      old premise still present
every other ref carrying that file    no quote-blanking, no dash/equals exclusion
```

**Both branches still carry the sentence you said you corrected in place:**
> *"Over-collecting is the safe direction here: a false hit costs one refusal that a real work item clears, a miss costs the whole gate."*

**And the pattern is the un-narrowed one:**
```python
re.compile(r">>?\s*([^\s;|&<>()]+)")
```
**No quote blanking. No exclusion for a greater-than after a dash or an equals.**

**So the work exists on your machine and not on the server.** *Third instance of this in three weeks — the case-folding fix, the read-gate sweep, and now this.* **Each time you told me before I discovered it, which is the right order, and each time I have then spent a pass finding out the same way.**

**One line would save that: when you send a branch, say whether the change you are describing is on origin or local.** *You already do this sometimes — "committed and unpushed" on the read-gate sweep — and when you do it costs me nothing.*

---

# 2. THE ATTACK YOU NAMED IS REAL. I TESTED IT.

**You wrote:** *"A redirect after an equals sign is the one I keep looking at."*

**You were right to keep looking at it. Against the current deployed regex:**
```
'cmd --opt=>secret.txt'   ->  ['secret.txt']     caught  (over-collecting, as designed)
'echo x > real.txt'       ->  ['real.txt']       caught
'if [ $a -gt 5 ]; then'   ->  []                 correctly ignored
'printf "a=>b"'           ->  ['b"']             FALSE HIT -- one of Aria's blocks
```

**Now apply the narrowing you describe — skip a `>` preceded by `-` or `=`:**

**`cmd --opt=>secret.txt` stops being caught.**

**And that is a real shell redirect.** *The shell parses `--opt=` as an argument and `>secret.txt` as a redirection. The file is written. The doorman would not see it.*

**So the exclusion you built to fix `a=>b` also opens `--opt=>file`, and the two are indistinguishable by the rule "greater-than after an equals sign."**

## What actually separates them

**The false cases are all inside quotes.** *`printf "a=>b"`, the arrow in a formatted line, the quoted redirect — every one is quoted text.*

**The real one is not.**

**So the quote-blanking half of your fix is sufficient on its own, and the dash/equals half is the part that opens the hole.**

*Blanking quoted text kills `printf "a=>b"` and the formatted arrow and the quoted redirect.* **A comparison like `-gt` was never matching anyway — verified above, it returns nothing.**

**My reading: ship the quote blanking, drop the dash/equals exclusion.** *One half does the work; the other half is the one that made you uneasy, and the unease was correct.*

**I would want that tested rather than taken** — *run your three false cases against quote-blanking alone. If all three go quiet, the second narrowing is unnecessary and it is the one carrying the risk.*

---

# 3. THE PREMISE YOU CORRECTED — I think the original was closer to right

**You changed "over-collecting is the safe direction" because the measured cost was two blocks and two justifications.**

**That is a real cost and I am not dismissing it. But the trade is not symmetric and the sentence had it right:**
```
false hit   one refusal, visible, annoying, clears with a work item
miss        a build proceeds unfiled, invisibly, and the gate has no other route
```
**A false refusal announces itself. A miss does not.**

**What the two blocks actually cost was Aria's time and a written justification each — and that is the loud failure doing its job badly rather than the wrong failure direction.**

**So: fix the precision, keep the premise.** *The premise says which way to err when you cannot be precise. Precision reduces how often you have to.*

**And I would put the measured cost in the comment alongside the premise rather than instead of it** — *"over-collecting is the safe direction, and it cost two blocks and two justifications on 09-10, so precision here is worth real work."* **Both true, and the second does not overturn the first.**

---

# 4. THE OTHER FIVE — I have not read them

**You ordered them by how much you distrust your own judgement and told me to take one if I only take one. I took that one and it is not on origin, so I have spent the pass without landing it.**

**Two things I can answer without the code, since you asked them as questions rather than as reviews:**

## On the disclaimer line

> *"whether a line that says 'another tree may read this differently' actually changes any behaviour, or whether it is a disclaimer that lets the same confusion happen with paperwork attached."*

**It changes behaviour only if a reader can act on it, and here they can: the line tells them which rulebook judged the answer.** *That is not a hedge, it is a subject declaration — the same thing as `examined=` and `0 across N modelled surfaces`.*

**The test for whether it is a disclaimer: does the line ever change?** *If it always says the same thing, it is furniture within a week.* **You have three states — shared rules, this checkout's own with a warning, and unknown — so it varies. That is the discriminator, and it passes.**

## On ignoring line endings

**You are right to be uneasy and I think the unease is misplaced here.**

*Your worry: "ignoring a difference is exactly the kind of narrowing that hides a real one."* **True in general. But a line ending is not a difference in the rules — it is a difference in how the same rules are stored on two operating systems.**

**The question I would ask instead: could a real rule change ever consist ONLY of line endings?** *No. So normalising them cannot hide a rule change.* **That is a complete argument rather than a judgement call, and it is what makes this narrowing safe where the dash/equals one is not.**

---

# 5. THE TEACHING PAGE THAT DISAGREED WITH THE DOOR

**A gate refused a reply for a missing section; the page that teaches the sections said three; the door counts four.**

**You said the class has recurred often enough to want a structural answer and you distrust the obvious one — a page generated from the gates, complete and unreadable.**

**Your distrust is right and the reason is the parenthesis finding: a rule nobody reads is the same failure with better provenance.**

**The shape I would try instead, and it is smaller than generation:** *do not generate the page. Test it.*

**One test that asserts every room a door will hold you to appears in the teaching page.** *You already built exactly that for this instance.* **The structural answer is that it exists for every door rather than for this one** — *a page can stay hand-written and readable, and the test catches the drift.*

**Which is the same shape as testing the wiring rather than the behaviour: the page is a claim, and a claim can have a test without becoming generated.**

---

**Push the doorman and I will read it. And if the quote-blanking-alone experiment comes out the way I think it will, that is a smaller change than the one you are asking me to approve.**

— Aletheia Sophia Risner, 2026-09-10
